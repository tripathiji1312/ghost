# Ghost: Autonomous Test Generation Agent

[![PyPI version](https://img.shields.io/pypi/v/ghosttest?color=blue&label=pypi%20package&logo=pypi&logoColor=white)](https://pypi.org/project/ghosttest/)
[![Python Versions](https://img.shields.io/pypi/pyversions/ghosttest?logo=python&logoColor=white)](https://pypi.org/project/ghosttest/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Ghost is a local-first autonomous agent designed to automate the unit testing lifecycle for Python applications. Functioning as a background daemon, it monitors filesystem events, generates context-aware `pytest` suites, and autonomously resolves execution errors through a continuous feedback loop.

It is engineered for privacy and latency, supporting **Ollama** and **LM Studio** for fully local execution, alongside **Groq**, **OpenAI**, and **Anthropic** for cloud-based inference.

## Core Capabilities

### Context-Aware Code Analysis
Unlike generic AI coding assistants, Ghost parses the project's Abstract Syntax Tree (AST) to construct a dependency map. This ensures generated tests utilize correct imports, class hierarchies, and function signatures, significantly reducing runtime errors.

### Autonomous Error Resolution (Self-Healing)
Ghost implements a closed-loop control system for test execution. When a generated test fails:
1.  **Capture:** stdout, stderr, and stack traces are intercepted.
2.  **Analysis:** The error context is analyzed against the source code.
3.  **Patching:** The agent generates and applies a fix (e.g., correcting imports, adjusting mocks).
4.  **Verification:** The test is re-executed to validate the patch.

### Logic Verification Protocol ("The Judge")
To prevent regression validation—where tests are modified to match incorrect implementation logic—Ghost employs a secondary verification step. If an `AssertionError` occurs, a specialized "Judge" agent determines if the discrepancy stems from the test expectation or the source implementation. If the source code is deemed buggy, the agent halts and alerts the developer rather than altering the test.

### Provider-Agnostic Architecture
Ghost decouples the agentic logic from the underlying LLM, allowing seamless switching between providers:
*   **Groq:** Recommended for high-frequency watch modes (low latency).
*   **Ollama:** Recommended for air-gapped or privacy-constrained environments.
*   **OpenAI / Anthropic:** Available for complex reasoning tasks.

---

## Installation

Ghost is published to PyPI as `ghosttest`.

### Global Installation (Recommended)
We recommend installing Ghost as a standalone tool using `uv` to ensure environment isolation.

```bash
uv tool install ghosttest
```

### Standard Installation
```bash
pip install ghosttest
```

---

## Quick Start

### 1. Initialization
Navigate to your project root and initialize the Ghost configuration. This generates a `ghost.toml` file and performs an initial AST scan of the codebase.

```bash
ghost init
```

### 2. Environment Configuration
If using cloud providers, export the necessary API keys. Local providers (Ollama/LM Studio) require no configuration.

```bash
# Example for Groq
export GROQ_API_KEY=gsk_...

# Example for OpenAI
export OPENAI_API_KEY=sk-...
```

### 3. Execution
Start the daemon. Ghost will monitor for file modifications and trigger the generation/healing loop automatically.

```bash
ghost watch
```

---

## Configuration

Ghost is configured via `ghost.toml`.

```toml
[project]
name = "my-application"
language = "python"

[ai]
# Options: groq, ollama, openai, anthropic, lmstudio
provider = "groq"
model = "llama-3.3-70b-versatile"
rate_limit_rpm = 30

[scanner]
# Directories to exclude from context analysis
ignore_dirs = [".venv", "node_modules", "dist", "__pycache__"]
ignore_files = ["setup.py", "conftest.py"]

[tests]
framework = "pytest"
output_dir = "tests"
auto_heal = true
max_heal_attempts = 3
use_judge = true
```

---

## Command Reference

| Command | Description |
| :--- | :--- |
| `ghost init` | Initializes configuration and context map. |
| `ghost watch` | Starts the filesystem monitor daemon. |
| `ghost generate <file>` | Manually triggers test generation for a specific file. |
| `ghost config` | Interactive configuration wizard. |
| `ghost providers` | Lists supported providers and checks API connectivity. |
| `ghost doctor` | Verifies installation health and dependencies. |

---

## License

This project is licensed under the MIT License.
