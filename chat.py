import os
import logging
from groq import Groq
from openai import OpenAI
import re

class TestGenerator:
    def __init__(self, api_key="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"):
        self.client = Groq(
            api_key=api_key,
        )

    def get_test_code(self, source_code):
        prompt = self.create_prompt(source_code)
        chat_completion = self.client.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": "You are a code generator. Output only code."
                    },
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            model="openai/gpt-oss-120b",
        )

        code = chat_completion.choices[0].message.content
        cleaned_code = self.clean_llm_response(code)
        return cleaned_code

    def create_prompt(self, source_code):
        return f"""
        You are an automated QA Agent. Your job is to write a Pytest unit test for the provided Python code.
        
        STRICT RULES:
        1. Output ONLY the raw Python code. 
        2. Do NOT use Markdown backticks (```).
        3. Do NOT add explanations or conversational text.
        4. Must include 'import pytest'.
        5. Mock external dependencies if necessary.
        
        INPUT CODE:
        {source_code}
        """

    def clean_llm_response(self, raw_text):
        """
        Removes markdown backticks, conversational filler, and extracts just the Python code.
        """
        # Pattern to find code inside ```python ... ``` blocks
        pattern = r"```python(.*?)```"
        match = re.search(pattern, raw_text, re.DOTALL)
        
        if match:
            # Return the content inside the backticks
            return match.group(1).strip()
        
        # Fallback: If no backticks, it might be raw code already.
        # Just strip whitespace and return.
        return raw_text.strip()

def main():
    # Example source code to generate tests for
    source_code = """
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

# Reading File
def ReadFile(file_path: str) -> str:
    with open(file_path, 'r') as file:
        content = file.read()
    return content

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
                content = ReadFile(event.src_path)
                logging.info("File content:\n%s", content)
        def on_deleted(self, event: FileSystemEvent) -> None: #When a file is deleted
            file = getFileNameFromPath(event.src_path)
            if CheckPath(file):
                logging.info("File deleted: %s", file)
        def on_modified(self, event: FileSystemEvent) -> None: #When a file is modified
            file = getFileNameFromPath(event.src_path)
            if CheckPath(file):
                logging.info("File modified: %s", file)
                content = ReadFile(event.src_path)
                logging.info("File content:\n%s", content)

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
    """
    generator = TestGenerator()
    print(generator.get_test_code(source_code))

if __name__ == "__main__":
    main()