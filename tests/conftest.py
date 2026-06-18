import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_project() -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)
        ghost_dir = project / ".ghost"
        ghost_dir.mkdir(parents=True, exist_ok=True)
        yield project


@pytest.fixture
def ghost_config_content() -> str:
    return """
[project]
name = "test-project"
language = "python"

[ai]
provider = "ollama"
model = "llama3.2"
rate_limit_rpm = 999

[scanner]
ignore_dirs = [".venv", "__pycache__"]
ignore_files = ["setup.py"]

[tests]
framework = "pytest"
output_dir = "tests"
auto_heal = true
max_heal_attempts = 3
use_judge = true

[watcher]
debounce_seconds = 2
patterns = ["*.py"]
"""


@pytest.fixture
def temp_project_with_config(temp_project: Path, ghost_config_content: str) -> Path:
    config_path = temp_project / "ghost.toml"
    config_path.write_text(ghost_config_content)
    return temp_project


@pytest.fixture
def sample_python_source() -> str:
    return """
def hello(name: str) -> str:
    return f"Hello, {name}!"


def add(a: int, b: int) -> int:
    return a + b


class Calculator:
    def multiply(self, x: int, y: int) -> int:
        return x * y
"""


@pytest.fixture
def mock_env_api_key() -> Generator[None, None, None]:
    old = os.environ.get("GROQ_API_KEY")
    os.environ["GROQ_API_KEY"] = "test-key-12345"
    yield
    if old:
        os.environ["GROQ_API_KEY"] = old
    else:
        os.environ.pop("GROQ_API_KEY", None)
