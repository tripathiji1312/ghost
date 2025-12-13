# 👻 Ghost

**AI-Powered Test Generation & Healing for Python**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Ghost automatically generates, runs, and **heals** your Python tests using AI. Just write your code - Ghost handles the tests.

```
   ▄████  ██░ ██  ▒█████    ██████ ▄▄▄█████▓
  ██▒ ▀█▒▓██░ ██▒▒██▒  ██▒▒██    ▒ ▓  ██▒ ▓▒
 ▒██░▄▄▄░▒██▀▀██░▒██░  ██▒░ ▓██▄   ▒ ▓██░ ▒░
 ░▓█  ██▓░▓█ ░██ ▒██   ██░  ▒   ██▒░ ▓██▓ ░ 
 ░▒▓███▀▒░▓█▒░██▓░ ████▓▒░▒██████▒▒  ▒██▒ ░ 
```

---

## ✨ Features

- 🤖 **Multi-Provider AI** - Works with Groq, OpenAI, Anthropic, Ollama (local), and more
- 🔄 **Self-Healing Tests** - Automatically fixes failing tests
- 👁️ **File Watcher** - Generates tests as you code
- ⚖️ **AI Judge** - Determines if bugs are in code or tests
- 🎨 **Beautiful CLI** - Stunning terminal output with animations
- ⚡ **Rate Limiting** - Smart handling of API limits

---

## 🚀 Quick Start

### Installation

```bash
# Install with pip
pip install ghosttest

# Or with uv (recommended)
uv pip install ghosttest
```

### Setup

```bash
# Initialize Ghost in your project
ghost init

# Or specify a directory
ghost init ./myproject
```

### Usage

```bash
# Watch for changes and auto-generate tests
ghost watch

# Generate tests for a specific file
ghost generate app.py

# View available AI providers
ghost providers

# Check installation health
ghost doctor
```

---

## 🤖 Supported AI Providers

| Provider | Type | Free Tier | Speed | Setup |
|----------|------|-----------|-------|-------|
| **Ollama** | Local | ✅ Unlimited | Fast | `ollama serve` |
| **Groq** | Cloud | ✅ 30 RPM | ⚡ Ultra-fast | `GROQ_API_KEY` |
| **OpenAI** | Cloud | ❌ Paid | Fast | `OPENAI_API_KEY` |
| **Anthropic** | Cloud | ❌ Paid | Fast | `ANTHROPIC_API_KEY` |
| **OpenRouter** | Cloud | Pay-per-use | Varies | `OPENROUTER_API_KEY` |
| **LM Studio** | Local | ✅ Unlimited | Varies | Start app |

### Setting up Ollama (Free & Local)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start the server
ollama serve

# Pull a coding model
ollama pull llama3.2
# or for better code generation:
ollama pull deepseek-coder-v2
ollama pull qwen2.5-coder

# Initialize Ghost with Ollama
ghost init -p ollama
```

### Setting up Groq (Free Cloud)

```bash
# Get your free API key from https://console.groq.com
export GROQ_API_KEY="your-key-here"

# Initialize Ghost with Groq
ghost init -p groq
```

---

## 📖 Commands

### `ghost init [PATH]`

Initialize Ghost in a directory. Creates `ghost.toml` config and `.ghost/` directory.

```bash
ghost init                    # Current directory
ghost init ./myproject        # Specific directory
ghost init -p ollama          # Use Ollama (local)
ghost init -p groq -m llama-3.3-70b  # Groq with specific model
```

### `ghost watch [PATH]`

Watch for file changes and automatically generate tests.

```bash
ghost watch              # Watch current directory
ghost watch ./src        # Watch specific directory
ghost watch -V           # Verbose mode
```

### `ghost generate <FILE>`

Generate tests for a specific Python file.

```bash
ghost generate app.py
ghost generate src/utils.py -o tests/test_utils.py
ghost generate app.py --force  # Overwrite existing
```

### `ghost config`

View or modify Ghost configuration.

```bash
ghost config --show               # Show current config
ghost config --set-provider openai
ghost config --set-model gpt-4o-mini
```

### `ghost providers`

List available AI providers and their status.

```bash
ghost providers          # List all
ghost providers --check  # Check connectivity
```

### `ghost doctor`

Check Ghost installation and dependencies.

```bash
ghost doctor
```

---

## ⚙️ Configuration

Ghost uses a `ghost.toml` file for project configuration:

```toml
[project]
name = "my-app"
language = "python"

[ai]
provider = "ollama"           # groq, openai, ollama, anthropic, openrouter
model = "llama3.2"           # Model to use
rate_limit_rpm = 30          # Requests per minute

[scanner]
ignore_dirs = [".venv", "node_modules", ".git", "__pycache__", "tests"]
ignore_files = ["setup.py", "conftest.py"]

[tests]
framework = "pytest"         # pytest or unittest
output_dir = "tests"
auto_heal = true             # Auto-fix failing tests
max_heal_attempts = 3
use_judge = true             # Use AI judge for test failures

[watcher]
debounce_seconds = 15        # Ignore rapid consecutive saves
```

### Environment Variables

```bash
# API Keys (set based on your provider)
export GROQ_API_KEY="your-groq-key"
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
export OPENROUTER_API_KEY="your-openrouter-key"

# Custom endpoints
export OLLAMA_HOST="http://localhost:11434"
export GHOST_BASE_URL="https://your-custom-endpoint.com/v1"
```

---

## 🏗️ How It Works

1. **File Watcher** monitors your Python files for changes
2. **Code Analyzer** extracts functions, classes, and structure
3. **AI Generator** creates comprehensive tests with:
   - Happy path tests
   - Edge cases
   - Error handling
   - Mocked dependencies
4. **Test Runner** executes the generated tests
5. **AI Judge** analyzes failures to determine root cause
6. **Self-Healer** automatically fixes test issues

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Your Code  │────▶│   Ghost AI   │────▶│   Tests     │
└─────────────┘     └──────────────┘     └─────────────┘
       │                   │                    │
       │            ┌──────┴──────┐            │
       │            ▼             ▼            │
       │     ┌──────────┐  ┌──────────┐       │
       │     │ Generate │  │   Heal   │◀──────┘
       │     └──────────┘  └──────────┘
       │                         │
       └─────────────────────────┘
```

---

## 🎨 Beautiful CLI

Ghost features a stunning terminal interface:

```
   ▄████  ██░ ██  ▒█████    ██████ ▄▄▄█████▓
  ...
  AI-Powered Test Generation & Healing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  👻 Ghost Demo
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▸ Status Messages
───────────────────
✔ Operation completed successfully
✖ Something went wrong  
⚠ Proceed with caution
ℹ Here's some information

🪄 Generating tests for example.py
⠋ Processing files (3.0s)
✔ Tests generated for example.py
⚖️ Consulting judge for: example.py
🔨 Verdict: Test needs fixing
```

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

<p align="center">
  Made with 👻 by the Ghost Team
</p>
