
# Contributing to Ghost

Thank you for your interest in contributing to Ghost! We welcome contributions from the community, whether it's fixing bugs, adding new AI providers, improving the documentation, or suggesting new features.

This document outlines the process for setting up your development environment and submitting contributions.

## Development Setup

Ghost uses **[uv](https://github.com/astral-sh/uv)** for fast package management and dependency resolution. Please ensure you have Python 3.10+ installed.

### 1. Fork and Clone
Fork the repository to your GitHub account, then clone it locally:

```bash
git clone https://github.com/YOUR_USERNAME/ghost.git
cd ghost
```

### 2. Set Up Environment (Using uv)
We recommend using `uv` to create a virtual environment and install dependencies in editable mode.

```bash
# Create virtual environment
uv venv

# Activate it (Linux/macOS)
source .venv/bin/activate
# Activate it (Windows)
# .venv\Scripts\activate

# Install dependencies + dev tools (black, ruff, mypy)
uv pip install -e ".[dev]"
```

### 3. Configure Environment Variables
To test the AI capabilities locally, you need to set up your API keys. Copy the example environment file (if available) or create a new one:

```bash
touch .env
```

Add your keys to `.env`:
```env
GROQ_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
# OLLAMA does not require a key
```

---

## 💻 Development Workflow

### Project Structure
*   `ghost/`: Source code package.
    *   `main.py`: Entry point and file watcher logic.
    *   `chat.py`: LLM interaction and prompt engineering.
    *   `providers.py`: API client implementations.
    *   `init.py`: AST analysis and context generation.
*   `tests/`: Unit tests for Ghost itself.

### Running Ghost Locally
Since you installed in editable mode (`-e`), changes you make to the code are reflected immediately.

```bash
# Initialize a dummy config in the current folder for testing
ghost init

# Run the watcher
ghost watch
```

### Code Style & Linting
We enforce strict code style to maintain quality. Please run these commands before pushing:

**Formatting (Black & Isort):**
```bash
black ghost tests
isort ghost tests
```

**Linting (Ruff):**
```bash
ruff check .
```

---

## Testing

Please ensure all tests pass before submitting a Pull Request.

```bash
pytest
```

If you are adding a new feature, please include a unit test covering the logic. If you are adding a new AI provider, please test the integration thoroughly.

---

## 📝 Pull Request Guidelines

1.  **Create a Branch:** Create a new branch for your specific feature or fix.
    ```bash
    git checkout -b feature/add-new-provider
    # or
    git checkout -b fix/watcher-debounce-bug
    ```
2.  **Commit Messages:** We prefer semantic commit messages:
    *   `feat: Add support for DeepSeek model`
    *   `fix: Resolve import error in generated tests`
    *   `docs: Update installation guide`
    *   `refactor: Improve prompt engineering logic`
3.  **Submit PR:** Push your branch to your fork and open a Pull Request against the `main` branch of the Ghost repository.
4.  **Description:** Provide a clear description of what changed and why. If it fixes an issue, link the issue number.

---

## Reporting Issues

If you encounter a bug, please open an Issue on GitHub with:
1.  Your OS (Linux, macOS, Windows).
2.  Which AI provider you were using (Ollama, Groq, etc.).
3.  The stack trace or error message.
4.  Steps to reproduce the error.

---

## ️ License

By contributing to Ghost, you agree that your contributions will be licensed under the MIT License.