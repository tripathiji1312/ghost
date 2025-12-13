import os
import logging
from groq import Groq
from openai import OpenAI
import re
import tomllib
import json
from datetime import datetime

class TestGenerator:
    def __init__(self, api_key="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"):
        self.client = Groq(
            api_key=api_key,
        )

    def get_test_code(self, source_code, source_path='.'):
        prompt = self.create_prompt(source_code, source_path)
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

    def create_prompt(self, source_code, source_path):
        conf = tomllib.load(open("ghost.toml", "rb"))
        framework = conf.get("tests", {}).get("framework", "pytest")
        context_source = f"{source_path}/.ghost/context.json"
        with open(context_source, "r") as f:
            global_context = json.load(f)
        now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        return f"""
        ROLE:
        You are a deterministic, automated QA agent specialized in Python test generation.

        PRIMARY OBJECTIVE:
        Generate a COMPLETE, EXECUTABLE Python test file using the specified testing framework: {framework}.

        The output must be immediately runnable without modification.

        ABSOLUTE OUTPUT CONSTRAINTS (NON-NEGOTIABLE):
        1. Output ONLY valid Python source code.
        2. Do NOT include Markdown, backticks, explanations, annotations, or conversational text.
        3. The output MUST be directly saveable as a .py file.
        4. The output MUST contain an explicit import of the testing framework:
           import {framework}
        5. Do NOT emit placeholder code, TODOs, or pseudocode.
        6. Do NOT modify, rewrite, or inline the source code under test.
        7. Do NOT reference files, modules, or symbols not present in GLOBAL CONTEXT.
        8. Tests MUST be deterministic, repeatable, and isolated.

        FILE HEADER (MANDATORY):
        The very first lines of the file MUST be a Python comment in EXACTLY this format:
        # Generated at: {now} | Source: {source_path}

        TEST CONSTRUCTION RULES:
        - Use the idiomatic style required by {framework}.
        - If {framework} supports fixtures, setup/teardown, or parameterization, use them where appropriate.
        - If {framework} requires class-based tests, use them correctly.
        - Follow naming conventions required for automatic test discovery by {framework}.
        - Assert behavior explicitly; never rely on implicit truthiness.
        - Validate return values, side effects, and raised exceptions.
        - Cover:
          • Standard / expected behavior
          • Edge cases
          • Error or failure paths (invalid input, exceptions)
        - Write separate tests for each public function or class.

        MOCKING & ISOLATION REQUIREMENTS:
        - Mock ALL external dependencies, including but not limited to:
          • File system access
          • Network or HTTP calls
          • Environment variables
          • Time, randomness, UUIDs
          • Subprocesses or OS interactions
        - Use the most appropriate mocking mechanism compatible with {framework}
          (e.g., monkeypatch, unittest.mock, fixtures, stubs).

        IMPORT RULES:
        - Import ONLY from:
          • Python standard library
          • {framework}
          • Modules listed in GLOBAL CONTEXT
        - Avoid wildcard imports.

        GLOBAL CONTEXT (AVAILABLE MODULES / FILES):
        {json.dumps(global_context, indent=2)}

        SOURCE CODE UNDER TEST:
        {source_code}

        FINAL ENFORCEMENT:
        Return ONLY raw Python code.
        Any additional text, formatting, or explanation makes the response invalid.
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