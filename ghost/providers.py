"""
Ghost AI Providers - Multi-provider support for LLM APIs.

Supports:
- Groq (cloud)
- OpenAI (cloud)
- Anthropic/Claude (cloud)
- Ollama (local)
- OpenRouter (cloud - access to many models)
- LM Studio (local)
- Any OpenAI-compatible API
"""

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List
import logging

from console import Console, GhostSpinner, SpinnerStyle, Colors, countdown
from rate_limiter import RateLimiter, call_with_retry


class ProviderType(Enum):
    """Supported AI providers."""
    GROQ = "groq"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    LM_STUDIO = "lmstudio"
    CUSTOM = "custom"  # Any OpenAI-compatible endpoint


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    name: str
    provider: ProviderType
    context_length: int = 8192
    supports_streaming: bool = True
    rate_limit_rpm: int = 30  # Requests per minute
    description: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# POPULAR MODELS REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

POPULAR_MODELS: Dict[str, ModelConfig] = {
    # Groq models (fast inference)
    "llama-3.3-70b": ModelConfig("llama-3.3-70b-versatile", ProviderType.GROQ, 131072, True, 30, "Fast Llama 3.3 70B on Groq"),
    "llama-3.1-8b": ModelConfig("llama-3.1-8b-instant", ProviderType.GROQ, 131072, True, 30, "Fast Llama 3.1 8B on Groq"),
    "mixtral-8x7b": ModelConfig("mixtral-8x7b-32768", ProviderType.GROQ, 32768, True, 30, "Mixtral MoE on Groq"),
    "gemma2-9b": ModelConfig("gemma2-9b-it", ProviderType.GROQ, 8192, True, 30, "Google Gemma 2 9B on Groq"),
    
    # OpenAI models
    "gpt-4o": ModelConfig("gpt-4o", ProviderType.OPENAI, 128000, True, 500, "GPT-4o - Latest OpenAI flagship"),
    "gpt-4o-mini": ModelConfig("gpt-4o-mini", ProviderType.OPENAI, 128000, True, 500, "GPT-4o Mini - Fast & cheap"),
    "gpt-4-turbo": ModelConfig("gpt-4-turbo", ProviderType.OPENAI, 128000, True, 500, "GPT-4 Turbo"),
    "gpt-3.5-turbo": ModelConfig("gpt-3.5-turbo", ProviderType.OPENAI, 16385, True, 3500, "GPT-3.5 Turbo - Fast"),
    
    # Anthropic models
    "claude-3.5-sonnet": ModelConfig("claude-3-5-sonnet-20241022", ProviderType.ANTHROPIC, 200000, True, 50, "Claude 3.5 Sonnet - Best for coding"),
    "claude-3-haiku": ModelConfig("claude-3-haiku-20240307", ProviderType.ANTHROPIC, 200000, True, 50, "Claude 3 Haiku - Fast"),
    
    # Ollama local models
    "ollama/llama3.2": ModelConfig("llama3.2", ProviderType.OLLAMA, 131072, True, 999, "Llama 3.2 (Local)"),
    "ollama/codellama": ModelConfig("codellama", ProviderType.OLLAMA, 16384, True, 999, "CodeLlama (Local)"),
    "ollama/deepseek-coder": ModelConfig("deepseek-coder-v2", ProviderType.OLLAMA, 128000, True, 999, "DeepSeek Coder V2 (Local)"),
    "ollama/qwen2.5-coder": ModelConfig("qwen2.5-coder", ProviderType.OLLAMA, 32768, True, 999, "Qwen 2.5 Coder (Local)"),
    "ollama/mistral": ModelConfig("mistral", ProviderType.OLLAMA, 32768, True, 999, "Mistral 7B (Local)"),
    
    # OpenRouter (access many models)
    "openrouter/auto": ModelConfig("openrouter/auto", ProviderType.OPENROUTER, 128000, True, 60, "Auto-select best model"),
}

# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDER MODELS LIST (for CLI)
# ═══════════════════════════════════════════════════════════════════════════════

PROVIDER_MODELS: Dict[str, List[str]] = {
    'groq': [
        'llama-3.3-70b-versatile',
        'llama-3.1-8b-instant',
        'mixtral-8x7b-32768',
        'gemma2-9b-it',
        'llama-guard-3-8b',
    ],
    'openai': [
        'gpt-4o',
        'gpt-4o-mini',
        'gpt-4-turbo',
        'gpt-3.5-turbo',
        'o1-preview',
        'o1-mini',
    ],
    'anthropic': [
        'claude-3-5-sonnet-20241022',
        'claude-3-opus-20240229',
        'claude-3-haiku-20240307',
    ],
    'ollama': [
        'llama3.2',
        'llama3.1',
        'codellama',
        'deepseek-coder-v2',
        'qwen2.5-coder',
        'mistral',
        'phi3',
    ],
    'openrouter': [
        'openrouter/auto',
        'anthropic/claude-3.5-sonnet',
        'openai/gpt-4o',
        'google/gemini-pro',
        'meta-llama/llama-3.1-70b-instruct',
    ],
    'lmstudio': [
        'local-model',  # LM Studio uses whatever model is loaded
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# BASE PROVIDER CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class BaseProvider(ABC):
    """Abstract base class for AI providers."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url
        self._client = None
    
    @abstractmethod
    def _create_client(self):
        """Create the API client."""
        pass
    
    @property
    def client(self):
        """Lazy-load the client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    @abstractmethod
    @call_with_retry(max_retries=5, base_delay=2.0)
    def chat(self, messages: List[Dict[str, str]], model: str, temperature: float = 0.1) -> str:
        """Send a chat completion request."""
        pass
    
    @abstractmethod
    def list_models(self) -> List[str]:
        """List available models."""
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# GROQ PROVIDER
# ═══════════════════════════════════════════════════════════════════════════════

class GroqProvider(BaseProvider):
    """Groq API provider - Ultra-fast inference."""
    
    ENV_KEY = "GROQ_API_KEY"
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or os.environ.get(self.ENV_KEY))
        if not self.api_key:
            raise ValueError(f"Groq API key required. Set {self.ENV_KEY} or pass api_key.")
    
    def _create_client(self):
        from groq import Groq
        return Groq(api_key=self.api_key)
    
    @call_with_retry(max_retries=5, base_delay=2.0)
    def chat(self, messages: List[Dict[str, str]], model: str = "llama-3.3-70b-versatile", temperature: float = 0.1) -> str:
        RateLimiter.wait()
        response = self.client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temperature,
        )
        return response.choices[0].message.content
    
    def list_models(self) -> List[str]:
        return ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"]


# ═══════════════════════════════════════════════════════════════════════════════
# OPENAI PROVIDER
# ═══════════════════════════════════════════════════════════════════════════════

class OpenAIProvider(BaseProvider):
    """OpenAI API provider."""
    
    ENV_KEY = "OPENAI_API_KEY"
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(api_key or os.environ.get(self.ENV_KEY), base_url)
        if not self.api_key:
            raise ValueError(f"OpenAI API key required. Set {self.ENV_KEY} or pass api_key.")
    
    def _create_client(self):
        from openai import OpenAI
        return OpenAI(api_key=self.api_key, base_url=self.base_url)
    
    @call_with_retry(max_retries=5, base_delay=2.0)
    def chat(self, messages: List[Dict[str, str]], model: str = "gpt-4o-mini", temperature: float = 0.1) -> str:
        RateLimiter.wait()
        response = self.client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temperature,
        )
        return response.choices[0].message.content
    
    def list_models(self) -> List[str]:
        return ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]


# ═══════════════════════════════════════════════════════════════════════════════
# ANTHROPIC PROVIDER
# ═══════════════════════════════════════════════════════════════════════════════

class AnthropicProvider(BaseProvider):
    """Anthropic/Claude API provider."""
    
    ENV_KEY = "ANTHROPIC_API_KEY"
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or os.environ.get(self.ENV_KEY))
        if not self.api_key:
            raise ValueError(f"Anthropic API key required. Set {self.ENV_KEY} or pass api_key.")
    
    def _create_client(self):
        try:
            import anthropic
            return anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("Please install anthropic: pip install anthropic")
    
    @call_with_retry(max_retries=5, base_delay=2.0)
    def chat(self, messages: List[Dict[str, str]], model: str = "claude-3-5-sonnet-20241022", temperature: float = 0.1) -> str:
        RateLimiter.wait()
        # Convert messages to Anthropic format
        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                chat_messages.append(msg)
        
        response = self.client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_msg,
            messages=chat_messages,
            temperature=temperature,
        )
        return response.content[0].text
    
    def list_models(self) -> List[str]:
        return ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307", "claude-3-opus-20240229"]


# ═══════════════════════════════════════════════════════════════════════════════
# OLLAMA PROVIDER (LOCAL)
# ═══════════════════════════════════════════════════════════════════════════════

class OllamaProvider(BaseProvider):
    """Ollama local LLM provider."""
    
    DEFAULT_URL = "http://localhost:11434"
    
    def __init__(self, base_url: Optional[str] = None):
        super().__init__(None, base_url or os.environ.get("OLLAMA_HOST", self.DEFAULT_URL))
    
    def _create_client(self):
        from openai import OpenAI
        return OpenAI(
            api_key="ollama",  # Ollama doesn't need a real key
            base_url=f"{self.base_url}/v1"
        )
    
    @call_with_retry(max_retries=3, base_delay=1.0)
    def chat(self, messages: List[Dict[str, str]], model: str = "llama3.2", temperature: float = 0.1) -> str:
        # No rate limiting needed for local models
        response = self.client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temperature,
        )
        return response.choices[0].message.content
    
    def list_models(self) -> List[str]:
        """List locally available Ollama models."""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [m["name"] for m in models]
        except Exception:
            pass
        return ["llama3.2", "codellama", "mistral", "deepseek-coder-v2"]
    
    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False


# ═══════════════════════════════════════════════════════════════════════════════
# LM STUDIO PROVIDER (LOCAL)
# ═══════════════════════════════════════════════════════════════════════════════

class LMStudioProvider(BaseProvider):
    """LM Studio local LLM provider."""
    
    DEFAULT_URL = "http://localhost:1234/v1"
    
    def __init__(self, base_url: Optional[str] = None):
        super().__init__(None, base_url or os.environ.get("LM_STUDIO_URL", self.DEFAULT_URL))
    
    def _create_client(self):
        from openai import OpenAI
        return OpenAI(
            api_key="lm-studio",
            base_url=self.base_url
        )
    
    @call_with_retry(max_retries=3, base_delay=1.0)
    def chat(self, messages: List[Dict[str, str]], model: str = "local-model", temperature: float = 0.1) -> str:
        response = self.client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temperature,
        )
        return response.choices[0].message.content
    
    def list_models(self) -> List[str]:
        return ["local-model"]  # LM Studio serves whatever is loaded
    
    def is_available(self) -> bool:
        """Check if LM Studio is running."""
        try:
            import requests
            response = requests.get(f"{self.base_url}/models", timeout=2)
            return response.status_code == 200
        except Exception:
            return False


# ═══════════════════════════════════════════════════════════════════════════════
# OPENROUTER PROVIDER
# ═══════════════════════════════════════════════════════════════════════════════

class OpenRouterProvider(BaseProvider):
    """OpenRouter API provider - Access to many models."""
    
    ENV_KEY = "OPENROUTER_API_KEY"
    BASE_URL = "https://openrouter.ai/api/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or os.environ.get(self.ENV_KEY), self.BASE_URL)
        if not self.api_key:
            raise ValueError(f"OpenRouter API key required. Set {self.ENV_KEY} or pass api_key.")
    
    def _create_client(self):
        from openai import OpenAI
        return OpenAI(
            api_key=self.api_key,
            base_url=self.BASE_URL,
            default_headers={
                "HTTP-Referer": "https://github.com/ghost-test",
                "X-Title": "Ghost Test Generator"
            }
        )
    
    @call_with_retry(max_retries=5, base_delay=2.0)
    def chat(self, messages: List[Dict[str, str]], model: str = "openrouter/auto", temperature: float = 0.1) -> str:
        RateLimiter.wait()
        response = self.client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temperature,
        )
        return response.choices[0].message.content
    
    def list_models(self) -> List[str]:
        return [
            "openrouter/auto",
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o",
            "google/gemini-pro-1.5",
            "meta-llama/llama-3.1-70b-instruct"
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOM OPENAI-COMPATIBLE PROVIDER
# ═══════════════════════════════════════════════════════════════════════════════

class CustomProvider(BaseProvider):
    """Custom OpenAI-compatible API provider."""
    
    def __init__(self, api_key: str, base_url: str):
        super().__init__(api_key, base_url)
        if not self.base_url:
            raise ValueError("Base URL required for custom provider.")
    
    def _create_client(self):
        from openai import OpenAI
        return OpenAI(api_key=self.api_key or "none", base_url=self.base_url)
    
    @call_with_retry(max_retries=5, base_delay=2.0)
    def chat(self, messages: List[Dict[str, str]], model: str, temperature: float = 0.1) -> str:
        RateLimiter.wait()
        response = self.client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temperature,
        )
        return response.choices[0].message.content
    
    def list_models(self) -> List[str]:
        return []  # Unknown for custom providers


# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDER FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

def get_provider(provider_type: str, **kwargs) -> BaseProvider:
    """
    Factory function to create a provider instance.
    
    Args:
        provider_type: One of 'groq', 'openai', 'anthropic', 'ollama', 'lmstudio', 'openrouter', 'custom'
        **kwargs: Provider-specific arguments (api_key, base_url, etc.)
    
    Returns:
        A provider instance ready to use.
    """
    providers = {
        "groq": GroqProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "ollama": OllamaProvider,
        "lmstudio": LMStudioProvider,
        "openrouter": OpenRouterProvider,
        "custom": CustomProvider,
    }
    
    # Local providers that don't need API keys
    local_providers = {"ollama", "lmstudio"}
    
    provider_type = provider_type.lower()
    
    if provider_type not in providers:
        raise ValueError(f"Unknown provider: {provider_type}. Available: {list(providers.keys())}")
    
    # Remove api_key for local providers (they don't accept it)
    if provider_type in local_providers:
        kwargs.pop('api_key', None)
    
    return providers[provider_type](**kwargs)


def auto_detect_provider() -> Optional[BaseProvider]:
    """
    Automatically detect and return an available provider.
    Checks in order: Ollama (local), LM Studio (local), then cloud providers.
    """
    # Check local providers first (free!)
    Console.info("Auto-detecting available AI providers...")
    
    try:
        ollama = OllamaProvider()
        if ollama.is_available():
            Console.success("Found Ollama running locally")
            return ollama
    except Exception:
        pass
    
    try:
        lmstudio = LMStudioProvider()
        if lmstudio.is_available():
            Console.success("Found LM Studio running locally")
            return lmstudio
    except Exception:
        pass
    
    # Check cloud providers
    env_providers = [
        ("GROQ_API_KEY", "groq", GroqProvider),
        ("OPENAI_API_KEY", "openai", OpenAIProvider),
        ("ANTHROPIC_API_KEY", "anthropic", AnthropicProvider),
        ("OPENROUTER_API_KEY", "openrouter", OpenRouterProvider),
    ]
    
    for env_key, name, provider_class in env_providers:
        if os.environ.get(env_key):
            try:
                provider = provider_class()
                Console.success(f"Found {name.upper()} API key")
                return provider
            except Exception:
                pass
    
    return None


def list_available_providers() -> Dict[str, bool]:
    """List all providers and their availability status."""
    status = {}
    
    # Local providers
    try:
        ollama = OllamaProvider()
        status["ollama"] = ollama.is_available()
    except Exception:
        status["ollama"] = False
    
    try:
        lmstudio = LMStudioProvider()
        status["lmstudio"] = lmstudio.is_available()
    except Exception:
        status["lmstudio"] = False
    
    # Cloud providers (check env vars)
    status["groq"] = bool(os.environ.get("GROQ_API_KEY"))
    status["openai"] = bool(os.environ.get("OPENAI_API_KEY"))
    status["anthropic"] = bool(os.environ.get("ANTHROPIC_API_KEY"))
    status["openrouter"] = bool(os.environ.get("OPENROUTER_API_KEY"))
    
    return status
