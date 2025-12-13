import subprocess
import os

def run_test(test_file_path):
    my_env = os.environ.copy()
    my_env['SOHINIPATH'] = os.getcwd()
    result = subprocess.run(
        ["pytest", test_file_path],
        capture_output=True,  # Grab the logs
        text=True,  # Return string, not bytes
        env=my_env  # Inject the path fix
    )
    return result.returncode, result.stdout, result.stderr


def get_project_tree(root_path, ignore_dirs=None):
    if ignore_dirs is None:
        ignore_dirs = {'.git', '__pycache__', 'venv', 'node_modules', '.ghost', '.pytest_cache', '.idea', '.venv'}

    tree_str = "PROJECT STRUCTURE:\n"

    for root, dirs, files in os.walk(root_path):
        # 1. Modify dirs in-place to skip ignored folders
        dirs[:] = [d for d in dirs if d not in ignore_dirs]

        # 2. Calculate depth for indentation
        level = root.replace(root_path, '').count(os.sep)
        indent = ' ' * 4 * level

        # 3. Add the folder name
        folder_name = os.path.basename(root)
        if folder_name:
            tree_str += f"{indent}{folder_name}/\n"

        # 4. Add files
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            if f.endswith('.py'):  # Only show relevant files to save tokens
                tree_str += f"{subindent}{f}\n"

    return tree_str
def main():
    return_code, stdout, stderr = run_test("app/test_testing.py")
    print(f"Return Code: {return_code}")
    print(f"STDOUT: {stdout}")
    print(f"STDERR: {stderr}")
    print(get_project_tree("."))

if __name__ == "__main__":
    main()