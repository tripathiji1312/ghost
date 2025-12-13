import os
import time
import logging
from time import sleep
from pathlib import Path
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from chat import TestGenerator
import init as ghost_init_module
import argparse
from console import Console, GhostSpinner, SpinnerStyle, Colors, Icons, countdown
from config import get_config, GhostConfig
from runner import *


# Utility function to extract file name from path
def getFileNameFromPath(path: str) -> str:
    # Extracts the file name from a given path
    parts = path.replace("\\", "/").split("/")
    return parts[-1]

def logging_setup():
    class CustomFormatter(logging.Formatter):
        grey = "\x1b[38;20m"
        yellow = "\x1b[33;20m"
        red = "\x1b[31;20m"
        bold_red = "\x1b[31;1m"
        reset = "\x1b[0m"
        format_str = "%(asctime)s - %(levelname)s - %(message)s"

        FORMATS = {
            logging.DEBUG: grey + format_str + reset,
            logging.INFO: grey + format_str + reset,
            logging.WARNING: yellow + format_str + reset,
            logging.ERROR: red + format_str + reset,
            logging.CRITICAL: bold_red + format_str + reset
        }

        def format(self, record):
            log_fmt = self.FORMATS.get(record.levelno)
            formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
            return formatter.format(record)

    # Set up logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # Capture INFO and above

    # Create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(CustomFormatter())
    logger.addHandler(ch)

# Function to check if the path should be logged
def CheckPath(file: str, full_path: str = "") -> bool:
    # Placeholder for path validation logic

    # Check if path is in tests directory (check full path, not just filename)
    if full_path:
        normalized_path = full_path.replace("\\", "/")
        if '/tests/' in normalized_path or normalized_path.endswith('/tests'):
            logging.debug("Ignoring file in tests directory: %s", file)
            return False
    if full_path.endswith(".py~"):
        logging.debug("Ignoring temporary file: %s", file)
        return False
    if "/tests/" in full_path:
        logging.debug("Ignoring file in tests directory: %s", file)
        return False
    if 'test' in file.lower() or 'tmp' in file.lower():
        logging.debug("Ignoring test or tmp file: %s", file)
        return False
    if file.startswith('.git') or file.endswith('.log'):
        logging.debug("Ignoring file: %s", file)
        return False
    if '.py' not in file:
        logging.debug("Ignoring non-Python file: %s", file)
        return False
    return True

# Reading File
count = 0
def check_test(file_path: str, source_path: str, file: str) -> bool:
    global count
    print(f"File: {file}, file_path: {file_path}, source_path: {source_path}")
    spinner1 = GhostSpinner("Running tests", style=SpinnerStyle.DOTS, color=Colors.CYAN)
    while count < 3:
        count += 1
        print(f"Count: {count}")
        spinner1.start()
        folder_path = "/".join(str(source_path).replace("\\", "/").split("/")[:])
        folder_path = f"{folder_path}/tests"
        test_file_path = f"{folder_path}/test_{getFileNameFromPath(file_path)}"
        cont = ReadFile(test_file_path)
        return_code, stdout, stderr = run_test(test_file_path, source_path)
        errors = {"return_code": return_code, "stderr": stderr, "stdout": stdout}
        error_type = classify_error(stderr, stdout)
        curr_path = str(source_path)
        spinner1.stop()
        try:

            if error_type == "SYNTAX" and error_type != "UNKNOWN":
                Console.warning(f"Syntax errors detected in {test_file_path}")
                countdown(5, "Preparing to heal")

                spinner2 = GhostSpinner("Healing test file", style=SpinnerStyle.DOTS2, color=Colors.MAGENTA)
                spinner2.start()
                config = get_config(Path(source_path) if source_path else None)
                generator = TestGenerator(config=config)
                code = generator.get_test_code(cont, curr_path, file, True, test_file_path, errors)
                WriteTest(file_path, code, source_path)
                spinner2.stop(message="Test healed successfully")
            elif error_type == "LOGIC":
                Console.judging(file)
                spinner3 = GhostSpinner("Consulting the judge", style=SpinnerStyle.DOTS, color=Colors.YELLOW)
                spinner3.start()
                countdown(5, "Analyzing code")

                config = get_config(Path(source_path) if source_path else None)
                judge = TestGenerator(config=config)
                result = judge.consult_the_judge(cont, curr_path, file, test_file_path, errors)
                spinner3.stop(message="Judge verdict received")

                Console.verdict(result == "BUG_IN_CODE")

                if result == "BUG_IN_CODE":
                    countdown(5, "Preparing fix")
                    spinner4 = GhostSpinner("Fixing tests", style=SpinnerStyle.DOTS2, color=Colors.MAGENTA)
                    spinner4.start()
                    generator = TestGenerator(config=config)
                    code = generator.get_test_code(cont, curr_path, file, True, test_file_path, errors)
                    WriteTest(file_path, code, source_path)
                    spinner4.stop(message="Tests fixed successfully")
                elif result == "FIX_TEST":
                    Console.newline()
                    Console.error("BUG DETECTED IN SOURCE CODE!", prefix="CRITICAL")
                    Console.info("The test found a discrepancy, but the AI believes the code is at fault.")
                    Console.warning("Ghost will NOT update the test to match buggy code.")
                    Console.newline()
                    break

            else:
                Console.error(f"No known bug found!")
                break

        except Exception as e:
            Console.error(f"Error consulting the judge: {e}")
            return False



    return True


def make_tests(file_path, content, source_path="", file="") -> None:
    print(f"File: {file}, file_path: {file_path}, source_path: {source_path}")
    Console.generating(file)
    spinner = GhostSpinner("Generating tests", style=SpinnerStyle.DOTS, color=Colors.CYAN)
    spinner.start()
    curr_path = str(source_path)
    flag = False
    try:
        # Load config from the source path to ensure .env is loaded
        config = get_config(Path(source_path) if source_path else None)
        generator = TestGenerator(config=config)
        code = generator.get_test_code(content, curr_path, file)
        WriteTest(file_path, code, source_path)
        flag = True
        spinner.stop(message=f"Tests generated for {file}")
    except Exception as e:
        spinner.fail(message=f"Failed to generate tests: {e}")
    finally:
        countdown(2, "Cooldown")
    if not flag:
        return
    check_test(file_path, source_path, file)

def ReadFile(file_path: str) -> None:
    if not os.path.isfile(file_path):
        return None

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except (FileNotFoundError, PermissionError, OSError):
        return None

# Write Test File
def WriteTest(file_path: str, test_code: str, source_path: str) -> str | None:
    folder_path = "/".join(str(source_path).replace("\\", "/").split("/")[:])
    folder_path = f"{folder_path}/tests"
    if os.path.exists(folder_path) == False:
        os.makedirs(folder_path)

    test_file_path = f"{folder_path}/test_{getFileNameFromPath(file_path)}"
    with open(test_file_path, 'w') as test_file:
        test_file.write(test_code)
    Console.success(f"Test file written: {test_file_path}")

# Watchdog Event Handler
def start_watching(path_to_watch):
    # Load .env from the project directory
    from pathlib import Path
    from dotenv import load_dotenv
    project_path = Path(path_to_watch).resolve()
    env_file = project_path / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)
    
    # Debounce mechanism to prevent duplicate events
    last_processed = {}
    currently_processing = set()  # Track files being processed
    DEBOUNCE_SECONDS = 15  # Ignore events for the same file within this window (increased for rate limiting)
    
    class MyEventHandler(FileSystemEventHandler):
        def _should_process(self, file_path):
            """Check if we should process this file (debouncing)."""
            # Skip if file is currently being processed
            if file_path in currently_processing:
                return False
            current_time = time.time()
            if file_path in last_processed:
                if current_time - last_processed[file_path] < DEBOUNCE_SECONDS:
                    return False
            return True
        
        def _mark_processing_start(self, file_path):
            """Mark file as being processed."""
            currently_processing.add(file_path)
        
        def _mark_processing_done(self, file_path):
            """Mark file processing as complete and update timestamp."""
            currently_processing.discard(file_path)
            last_processed[file_path] = time.time()
        
        def on_created(self, event: FileSystemEvent) -> None: #When a file is created
            pathhh = str(event.src_path)
            if pathhh.endswith("~"):
                event.src_path = pathhh[:-1]
            file = getFileNameFromPath(str(event.src_path))
            if file.endswith("~"):
                file = file[:-1]
            if CheckPath(file, str(event.src_path)):
                Console.file_changed(file, "created")

        def on_deleted(self, event: FileSystemEvent) -> None: #When a file is deleted
            pathhh = str(event.src_path)
            if pathhh.endswith("~"):
                event.src_path = pathhh[:-1]
            file = getFileNameFromPath(str(event.src_path))
            if file.endswith("~"):
                file = file[:-1]
            if CheckPath(file, str(event.src_path)):
                Console.file_changed(file, "deleted")
                ghost_init_module.walk_and_delete_json(path_to_watch, file)

        def on_modified(self, event: FileSystemEvent) -> None: #When a file is modified
            pathhh = str(event.src_path)
            if "__pycache__" in pathhh or pathhh.endswith(".pyc"):
                return
            if not pathhh.endswith("~"):

                file = getFileNameFromPath(str(event.src_path))
                # file_bad = getFileNameFromPath(pathhh)
                if CheckPath(file, str(event.src_path)) and self._should_process(str(event.src_path)):
                    self._mark_processing_start(str(event.src_path))
                    try:
                        Console.file_changed(file, "modified")
                        content = ReadFile(str(event.src_path))
                        # logging.info("File content:\n%s", content)
                        result = ghost_init_module.walk_and_modify_json(path_to_watch, str(event.src_path), file)
                        # Skip test generation if file has syntax errors
                        if result is not None:
                            # Pass: file_path (the modified file), content, source_path (project root), filename
                            make_tests(str(event.src_path), content, str(path_to_watch), file)
                    finally:
                        self._mark_processing_done(str(event.src_path))

    event_handler = MyEventHandler()
    observer = Observer()
    observer.schedule(event_handler, path=path_to_watch, recursive=True)
    observer.start()
    Console.success(f"Monitoring started: {path_to_watch}")
    Console.info("Press Ctrl+C to stop monitoring")
    Console.newline()
    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()

def main():
    logging_setup()
    
    # Show beautiful banner
    Console.banner()

    parser = argparse.ArgumentParser(
        description="GhostTest: AI QA Agent"
    )

    # Optional init flag (no subcommands)
    parser.add_argument(
        "--init",
        action="store_true",
        help="Initialize Ghost in the target directory"
    )

    # Optional path (default: current working directory)
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="Target path (default: current directory)"
    )

    args = parser.parse_args()

    target_path = args.path.resolve()

    if args.init:
        try:
            Console.info(f"Initializing Ghost in {target_path}")
            ghost_init_module.ghost_init(target_path)
            Console.success("Ghost initialized successfully!")
            return
        except Exception as e:
            Console.error(f"Error initializing Ghost: {e}")
            return

    ghost_file = target_path / "ghost.toml"

    if not ghost_file.exists():
        Console.warning("ghost.toml not found. Initializing with defaults...")
        ghost_init_module.ghost_init(target_path)

    Console.section("Starting File Watcher")
    start_watching(target_path)


if __name__ == "__main__":
    main()
