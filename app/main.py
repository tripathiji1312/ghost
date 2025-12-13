import os
import time
import logging
from time import sleep
from pathlib import Path

from openai import api_key
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from chat import TestGenerator
import init
import argparse
from spinner import Spinner
from config import API_KEY
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
def make_tests(file_path, content, source_path="", file="") -> None:
    print("Starting to generate test for ", file)
    spinner = Spinner("Generating Tests....")
    spinner.start()
    curr_path = os.getcwd()
    try:
        generator = TestGenerator(API_KEY)
        code = generator.get_test_code(content, curr_path)
        WriteTest(file_path, code, source_path)
    except Exception as e:
        print("Error generating tests:", e)
    finally:
        spinner.stop()
        sleep(2)
# Read File
def ReadFile(file_path: str) -> str:
    with open(file_path, 'r') as file:
        content = file.read()
    return content

# Write Test File
def WriteTest(file_path: str, test_code: str, source_path: str) -> None:
    folder_path = "/".join(str(file_path).replace("\\", "/").split("/")[:])
    folder_path = f"{folder_path}/tests"
    if os.path.exists(folder_path) == False:
        os.makedirs(folder_path)

    test_file_path = f"{folder_path}/test_{getFileNameFromPath(source_path)}"
    with open(test_file_path, 'w') as test_file:
        test_file.write(test_code)
    logging.info("Test file written to: %s", test_file_path)

# Watchdog Event Handler
def start_watching(path_to_watch):
    # Debounce mechanism to prevent duplicate events
    last_processed = {}
    currently_processing = set()  # Track files being processed
    DEBOUNCE_SECONDS = 5  # Ignore events for the same file within this window
    
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
            pathhh = event.src_path
            if pathhh.endswith("~"):
                event.src_path = pathhh[:-1]
            file = getFileNameFromPath(event.src_path)
            if file.endswith("~"):
                file = file[:-1]
            if CheckPath(file, event.src_path):
                logging.info("File created: %s", file)

        def on_deleted(self, event: FileSystemEvent) -> None: #When a file is deleted
            pathhh = event.src_path
            if pathhh.endswith("~"):
                event.src_path = pathhh[:-1]
            file = getFileNameFromPath(event.src_path)
            if file.endswith("~"):
                file = file[:-1]
            if CheckPath(file, event.src_path):
                logging.info("File deleted: %s", file)
                init.walk_and_delete_json(path_to_watch, file)

        def on_modified(self, event: FileSystemEvent) -> None: #When a file is modified
            pathhh = event.src_path
            if not pathhh.endswith("~"):

                file = getFileNameFromPath(event.src_path)
                # file_bad = getFileNameFromPath(pathhh)
                if CheckPath(file, event.src_path) and self._should_process(event.src_path):
                    self._mark_processing_start(event.src_path)
                    try:
                        logging.info("File modified: %s", file)
                        content = ReadFile(event.src_path)
                        # logging.info("File content:\n%s", content)
                        init.walk_and_modify_json(path_to_watch, event.src_path, file)
                        make_tests(path_to_watch, content, event.src_path, file)
                    finally:
                        self._mark_processing_done(event.src_path)

    event_handler = MyEventHandler()
    observer = Observer()
    observer.schedule(event_handler, path=path_to_watch, recursive=True)
    observer.start()
    logging.info("Monitoring started for Path = %s.", path_to_watch)
    logging.info("Press Ctrl+C to stop monitoring.")
    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()

def main():
    logging_setup()

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
            init.ghost_init(target_path)
            return
        except Exception as e:
            print(f"Error initializing Ghost: {e}")
            return

    ghost_file = target_path / "ghost.toml"

    if not ghost_file.exists():
        print("⚠️  Warning: ghost.toml not found. Initializing with defaults.")
        init.ghost_init(target_path)

    start_watching(target_path)


if __name__ == "__main__":
    main()
