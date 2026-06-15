import os
import time
import logging
import ast
import json
import tomllib
from pathlib import Path
from console import Console, GhostSpinner, SpinnerStyle, Colors 
from write_policy import WriteGuard

class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.functions = []
        self.classes = {}

    def visit_FunctionDef(self, node):
        # Only collect top-level functions (not inside classes)
        if isinstance(node.parent, ast.Module):
            args = [arg.arg for arg in node.args.args]
            signature = f"{node.name}({', '.join(args)})"
            self.functions.append(signature)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(item.name)
        self.classes[node.name] = methods
        self.generic_visit(node)

def get_toml(path):
    path = f"{path}/ghost.toml"
    with open(path, "rb") as f:
        config = tomllib.load(f)
    return config

# ANALYSIS
def add_parent_links(tree):
    """Attach parent references to AST nodes for top-level function detection."""
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node

# ANALYSIS
def analyze_file(path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None  # skip invalid files

    add_parent_links(tree)

    analyzer = CodeAnalyzer()
    analyzer.visit(tree)

    return analyzer.functions, analyzer.classes

# GENERATION
def walk_and_generate_json(base_dir):
    guard = WriteGuard(Path(base_dir) / ".ghost")
    result = {}
    conf = get_toml(base_dir)
    ignore_dirs = conf.get("scanner", {}).get("ignore_dirs", [])
    ignore_files = conf.get("scanner", {}).get("ignore_files", [])
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            if file in ignore_files:
                continue
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                functions, classes = analyze_file(file_path)

                if functions is None:
                    continue

                func_part = "Functions: " + ", ".join(functions) if functions else "Functions: None"

                class_parts = []
                for cls, methods in classes.items():
                    method_list = ", ".join(methods) if methods else "None"
                    class_parts.append(f"{cls} [Methods: {method_list}]")

                class_part = "Classes: " + "; ".join(class_parts) if class_parts else "Classes: None"

                result[file] = f"{func_part}; {class_part}"

    guard.write_text(Path(base_dir) / ".ghost" / "context.json", json.dumps(result, indent=4))

    return result

# DELETION
import os
import json

def walk_and_delete_json(base_dir, filename):
    guard = WriteGuard(Path(base_dir) / ".ghost")
    output_json = os.path.join(base_dir, ".ghost", "context.json")

    if not os.path.exists(output_json):
        return False

    try:
        with open(output_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return False

    if filename not in data:
        return False

    del data[filename]

    guard.write_text(Path(output_json), json.dumps(data, indent=4))

    return True


# MODIFICATION
def walk_and_modify_json(base_dir, file_path, file):
    guard = WriteGuard(Path(base_dir) / ".ghost")
    conf = get_toml(base_dir)
    result = {}
    ignore_files = conf.get("scanner", {}).get("ignore_files", [])
    root = os.path.dirname(base_dir)
    if file not in ignore_files:
        if file.endswith(".py"):
            analysis_result = analyze_file(file_path)

            if analysis_result is None:
                logging.warning("Skipping file with syntax errors: %s", file)
                return None

            functions, classes = analysis_result

            if functions or classes:
                func_part = "Functions: " + ", ".join(functions) if functions else "Functions: None"

                class_parts = []
                for cls, methods in classes.items():
                    method_list = ", ".join(methods) if methods else "None"
                    class_parts.append(f"{cls} [Methods: {method_list}]")

                class_part = "Classes: " + "; ".join(class_parts) if class_parts else "Classes: None"

                result[file] = f"{func_part}; {class_part}"
    output_json = f"{base_dir}/.ghost/context.json"
    with open(output_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    if file in result:
        data[file] = result[file]
    walk_and_delete_json(base_dir, file)
    guard.write_text(Path(output_json), json.dumps(data, indent=4))

    return result

# INITIALIZATION
def ghost_init(path = os.getcwd()):
    spinner = GhostSpinner("Initializing Ghost", style=SpinnerStyle.DOTS, color=Colors.MAGENTA)
    spinner.start()
    try:
        project_root = Path(path)
        guard = WriteGuard(project_root, allow_project_root_files=True, project_root=project_root)
        ghost_guard = WriteGuard(project_root / ".ghost")

        pathh = project_root / "ghost.toml"
        text = '''[project]
name = "my-app"
language = "python"

[ai]
provider = "ollama"  # Options: groq, openai, ollama, anthropic, openrouter
model = "llama3.2"

# Rate limiting (requests per minute)
rate_limit_rpm = 30

[scanner]
ignore_dirs = [".venv", "venv", "node_modules", ".git", "__pycache__", "dist", ".ghost", "tests"]
ignore_files = ["setup.py", "conftest.py"]

[tests]
framework = "pytest"
output_dir = "tests"
auto_heal = true
max_heal_attempts = 3

[watcher]
debounce_seconds = 15
'''
        guard.write_text(pathh, text)
        Console.success(f"Created ghost.toml")

        ghost_dir = project_root / ".ghost"
        if not ghost_dir.exists():
            ghost_guard.mkdir(ghost_dir)
            Console.success(f"Created .ghost/ directory")

        walk_and_generate_json(path)
        Console.success(f"Generated context.json")
        spinner.stop(message="Ghost initialized successfully")
    except Exception as e:
        spinner.fail(f"Initialization failed: {e}")
        raise

    Console.info("Run 'ghost watch' to start monitoring")

def main():
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

 # INITIALIZATION
    ghost_init()

if __name__ == "__main__":
    main()