"""
Ghost Configuration - Load and manage Ghost settings.

Supports loading from:
1. ghost.toml (project configuration)
2. Environment variables
3. Default values
"""

import os
import tomllib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AIConfig:
    """AI provider configuration."""
    provider: str = "ollama"
    model: str = "llama3.2"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    rate_limit_rpm: int = 30
    temperature: float = 0.1
    max_retries: int = 5


@dataclass
class ScannerConfig:
    """File scanner configuration."""
    ignore_dirs: List[str] = field(default_factory=lambda: [
        ".venv", "venv", "node_modules", ".git", "__pycache__",
        "dist", "build", ".ghost", "tests", ".tox", ".pytest_cache"
    ])
    ignore_files: List[str] = field(default_factory=lambda: [
        "setup.py", "conftest.py", "__init__.py"
    ])


@dataclass
class TestConfig:
    """Test generation configuration."""
    framework: str = "pytest"
    output_dir: str = "tests"
    auto_heal: bool = True
    max_heal_attempts: int = 3
    use_judge: bool = True


@dataclass
class WatcherConfig:
    """File watcher configuration."""
    debounce_seconds: int = 15
    patterns: List[str] = field(default_factory=lambda: ["*.py"])


@dataclass
class GhostConfig:
    """Complete Ghost configuration."""
    project_name: str = "my-project"
    language: str = "python"
    ai: AIConfig = field(default_factory=AIConfig)
    scanner: ScannerConfig = field(default_factory=ScannerConfig)
    tests: TestConfig = field(default_factory=TestConfig)
    watcher: WatcherConfig = field(default_factory=WatcherConfig)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GhostConfig":
        """Create config from dictionary (parsed TOML)."""
        project = data.get("project", {})
        ai_data = data.get("ai", {})
        scanner_data = data.get("scanner", {})
        test_data = data.get("tests", {})
        watcher_data = data.get("watcher", {})
        
        return cls(
            project_name=project.get("name", "my-project"),
            language=project.get("language", "python"),
            ai=AIConfig(
                provider=ai_data.get("provider", "ollama"),
                model=ai_data.get("model", "llama3.2"),
                api_key=ai_data.get("api_key"),
                base_url=ai_data.get("base_url"),
                rate_limit_rpm=ai_data.get("rate_limit_rpm", 30),
                temperature=ai_data.get("temperature", 0.1),
                max_retries=ai_data.get("max_retries", 5),
            ),
            scanner=ScannerConfig(
                ignore_dirs=scanner_data.get("ignore_dirs", ScannerConfig().ignore_dirs),
                ignore_files=scanner_data.get("ignore_files", ScannerConfig().ignore_files),
            ),
            tests=TestConfig(
                framework=test_data.get("framework", "pytest"),
                output_dir=test_data.get("output_dir", "tests"),
                auto_heal=test_data.get("auto_heal", True),
                max_heal_attempts=test_data.get("max_heal_attempts", 3),
                use_judge=test_data.get("use_judge", True),
            ),
            watcher=WatcherConfig(
                debounce_seconds=watcher_data.get("debounce_seconds", 15),
                patterns=watcher_data.get("patterns", ["*.py"]),
            ),
        )


def get_config(project_path: Optional[Path] = None) -> GhostConfig:
    """
    Load Ghost configuration from ghost.toml.
    
    Args:
        project_path: Path to the project root. If None, searches from CWD.
    
    Returns:
        GhostConfig instance with all settings.
    """
    if project_path is None:
        project_path = find_project_root()
    
    if project_path is None:
        # Return defaults if no project found
        return GhostConfig()
    
    project_path = Path(project_path)
    
    # Load .env from project directory
    env_file = project_path / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)
    
    config_path = project_path / "ghost.toml"
    
    if not config_path.exists():
        return GhostConfig()
    
    with open(config_path, "rb") as f:
        data = tomllib.load(f)
    
    config = GhostConfig.from_dict(data)
    
    # Override with environment variables
    config = _apply_env_overrides(config)
    
    return config


def find_project_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """Find the project root by looking for ghost.toml."""
    if start_path is None:
        start_path = Path.cwd()
    
    current = start_path.resolve()
    
    while current != current.parent:
        if (current / "ghost.toml").exists():
            return current
        current = current.parent
    
    return None


def _apply_env_overrides(config: GhostConfig) -> GhostConfig:
    """Apply environment variable overrides to config."""
    
    # API key overrides based on provider
    env_keys = {
        "groq": "GROQ_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }
    
    provider = config.ai.provider.lower()
    if provider in env_keys:
        env_key = env_keys[provider]
        api_key = os.environ.get(env_key)
        if api_key:
            config.ai.api_key = api_key
    
    # Also check for generic API key
    if not config.ai.api_key:
        config.ai.api_key = os.environ.get("GHOST_API_KEY")
    
    # Base URL override
    base_url = os.environ.get("GHOST_BASE_URL")
    if base_url:
        config.ai.base_url = base_url
    
    # Ollama host override
    if provider == "ollama":
        ollama_host = os.environ.get("OLLAMA_HOST")
        if ollama_host:
            config.ai.base_url = ollama_host
    
    return config


def get_api_key(provider: str = None) -> Optional[str]:
    """Get API key for a specific provider from environment."""
    env_keys = {
        "groq": ["GROQ_API_KEY", "GROQ_API_KEY3"],  # Support legacy key name
        "openai": ["OPENAI_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY"],
        "openrouter": ["OPENROUTER_API_KEY"],
    }
    
    if provider:
        provider = provider.lower()
        keys = env_keys.get(provider, [])
        
        for key in keys:
            value = os.environ.get(key)
            if value:
                return value
    
    # Try all keys if no provider specified
    for keys_list in env_keys.values():
        for key in keys_list:
            value = os.environ.get(key)
            if value:
                return value
    
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# LEGACY SUPPORT - For backwards compatibility
# ═══════════════════════════════════════════════════════════════════════════════

API_KEY = get_api_key() or os.environ.get("GROQ_API_KEY3", "")
