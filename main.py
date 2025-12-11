import time
import logging
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

# Utility function to extract file name from path
def getFileNameFromPath(path: str) -> str:
    # Extracts the file name from a given path
    parts = path.replace("\\", "/").split("/")
    return parts[-1]

# Function to check if the path should be logged
def CheckPath(file: str) -> bool:
    # Placeholder for path validation logic
    if 'test' in file.lower() or 'tmp' in file.lower():
        logging.error("Ignoring test or tmp file: %s", file)
        return False
    if file.startswith('.git') or file.endswith('.log'):
        logging.error("Ignoring file: %s", file)
        return False
    if '.py' not in file:
        logging.error("Ignoring non-Python file: %s", file)
        return False
    return True

def main():
    # Logging Configuration
    # Define custom logging format with colors
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

    
    path_to_watch = input("Enter the directory path to monitor (default is current directory): ") or "."
    # Watchdog Event Handler
    class MyEventHandler(FileSystemEventHandler):
        def on_created(self, event: FileSystemEvent) -> None: #When a file is created
            file = getFileNameFromPath(event.src_path)
            if CheckPath(file):
                logging.info("File created: %s", file)
        def on_deleted(self, event: FileSystemEvent) -> None: #When a file is deleted
            file = getFileNameFromPath(event.src_path)
            if CheckPath(file):
                logging.info("File deleted: %s", file)
        def on_modified(self, event: FileSystemEvent) -> None: #When a file is modified
            file = getFileNameFromPath(event.src_path)
            if CheckPath(file):
                logging.info("File modified: %s", file)

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
if __name__ == "__main__":
    main()