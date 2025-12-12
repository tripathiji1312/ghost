import os
import time
import logging
import ast
import json
import tomllib

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

def add_parent_links(tree):
    """Attach parent references to AST nodes for top-level function detection."""
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node


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


def walk_and_generate_json(base_dir):
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

                # Build readable summary string
                func_part = "Functions: " + ", ".join(functions) if functions else "Functions: None"

                class_parts = []
                for cls, methods in classes.items():
                    method_list = ", ".join(methods) if methods else "None"
                    class_parts.append(f"{cls} [Methods: {method_list}]")

                class_part = "Classes: " + "; ".join(class_parts) if class_parts else "Classes: None"

                result[file] = f"{func_part}; {class_part}"

    # Save JSON
    output_json = f"{base_dir}/.ghost/context.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    return result

def walk_and_delete_json(base_dir, file):
    output_json = f"{base_dir}/.ghost/context.json"
    if os.path.exists(output_json):
        with open(output_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        if file in data:
            del data[file]
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

def walk_and_modify_json(base_dir, file_path, file):
    conf = get_toml(base_dir)
    result = {}
    ignore_files = conf.get("scanner", {}).get("ignore_files", [])
    if file not in ignore_files:
        if file.endswith(".py"):
            # file_path = os.path.join(root, file)
            functions, classes = analyze_file(file_path)

            if functions is not None:

                # Build readable summary string
                func_part = "Functions: " + ", ".join(functions) if functions else "Functions: None"

                class_parts = []
                for cls, methods in classes.items():
                    method_list = ", ".join(methods) if methods else "None"
                    class_parts.append(f"{cls} [Methods: {method_list}]")

                class_part = "Classes: " + "; ".join(class_parts) if class_parts else "Classes: None"

                result[file] = f"{func_part}; {class_part}"
    output_json = f"{base_dir}/.ghost/context.json"
    walk_and_delete_json(base_dir, file)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    return result

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

    text = '''[project]
    name = "my-app"
    language = "python"
    
    [ai]
    provider = "ollama"  # or groq
    model = "llama3"
    
    [scanner]
    # The user tweaks these rules, NOT the file list itself
    ignore_dirs = ["venv", "node_modules", ".git", "__pycache__", "dist"]
    ignore_files = ["setup.py"]
    
    [tests]
    framework = "pytest"
    output_dir = "tests"'''

    path = os.getcwd()
    pathh = f"{path}/ghost.toml"
    with open(pathh, "w") as f:
        f.write(text)
    logging.info("ghost.toml file created at %s", path)
    os.mkdir(f"{path}/.ghost")
    logging.info(".ghost directory created at %s", f"{path}/.ghost")
    walk_and_generate_json(path)
    logging.info("Context JSON generated at %s", f"{path}/.ghost/context.json")

if __name__ == "__main__":
    main()