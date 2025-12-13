"""
Ghost - AI-Powered Test Generation & Healing

A powerful CLI tool that automatically generates, runs, and heals
Python tests using AI.

Features:
- Multi-provider support (Groq, OpenAI, Anthropic, Ollama, etc.)
- Automatic test generation from source code
- Self-healing tests that fix themselves
- File watching for continuous test generation
- Beautiful CLI with animations

Usage:
    ghost init              # Initialize in current directory
    ghost watch             # Watch for file changes
    ghost generate app.py   # Generate tests for a file
    ghost providers         # List available AI providers

For more information, visit: https://github.com/ghosttest/ghost
"""

__version__ = "0.2.0"
__author__ = "Ghost Team"

from .cli import main
from .config import GhostConfig, get_config
from .providers import get_provider, list_available_providers
from .console import Console, GhostSpinner

__all__ = [
    "main",
    "GhostConfig",
    "get_config",
    "get_provider",
    "list_available_providers",
    "Console",
    "GhostSpinner",
    "__version__",
]
