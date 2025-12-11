import time
import logging
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

def main():
    # Logging Configuration
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    path_to_watch = input("Enter the directory path to monitor (default is current directory): ") or "."
    # Watchdog Event Handler
    class MyEventHandler(FileSystemEventHandler):
        def on_created(self, event: FileSystemEvent) -> None: #When a file is created
            logging.info("File created: %s", event.src_path)
        def on_deleted(self, event: FileSystemEvent) -> None: #When a file is deleted
            logging.info("File deleted: %s", event.src_path)
        def on_modified(self, event: FileSystemEvent) -> None: #When a file is modified
            if event is not None and event.src_path != path_to_watch and event.is_directory != "./.git":
                logging.info("File modified: %s", event.src_path)

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