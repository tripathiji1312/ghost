import os
import subprocess
import sys
from typing import Optional, Set


def run_test(test_file_path: str, source_path: str) -> tuple[int, str, str]:
    python_exe = sys.executable
    my_env = os.environ.copy()
    my_env["PYTHONPATH"] = source_path
    result = subprocess.run(
        [python_exe, "-m", "pytest", test_file_path],
        capture_output=True,
        text=True,
        env=my_env,
    )
    return result.returncode, result.stdout, result.stderr


def get_project_tree(root_path: str, ignore_dirs: Optional[Set[str]] = None) -> str:
    if ignore_dirs is None:
        ignore_dirs = {
            ".git",
            "__pycache__",
            "venv",
            "node_modules",
            ".ghost",
            ".pytest_cache",
            ".idea",
            ".venv",
        }

    tree_str = "PROJECT STRUCTURE:\n"

    for root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        level = root.replace(root_path, "").count(os.sep)
        indent = " " * 4 * level
        folder_name = os.path.basename(root)
        if folder_name:
            tree_str += f"{indent}{folder_name}/\n"
        subindent = " " * 4 * (level + 1)
        for f in files:
            if f.endswith(".py"):
                tree_str += f"{subindent}{f}\n"

    return tree_str


def classify_error(stderr: str, stdout: str) -> str:
    full_log = stderr + stdout

    if "IndentationError" in full_log:
        return "SYNTAX"
    if "ModuleNotFoundError" in full_log:
        return "SYNTAX"
    if "ImportError" in full_log:
        return "SYNTAX"

    if "AttributeError" in full_log:
        return "RUNTIME"

    if "AssertionError" in full_log:
        return "LOGIC"

    return "UNKNOWN"
