from ghost.providers import (
    ModelConfig,
    ProviderType,
    get_provider,
    list_available_providers,
)


class TestProviderType:
    def test_enum_values(self):
        assert ProviderType.GROQ.value == "groq"
        assert ProviderType.OPENAI.value == "openai"
        assert ProviderType.OLLAMA.value == "ollama"
        assert ProviderType.LM_STUDIO.value == "lmstudio"
        assert ProviderType.ANTHROPIC.value == "anthropic"
        assert ProviderType.OPENROUTER.value == "openrouter"
        assert ProviderType.CUSTOM.value == "custom"


class TestModelConfig:
    def test_default_values(self):
        model = ModelConfig(name="test-model", provider=ProviderType.GROQ)
        assert model.name == "test-model"
        assert model.provider == ProviderType.GROQ
        assert model.context_length == 8192
        assert model.supports_streaming is True
        assert model.rate_limit_rpm == 30
        assert model.description == ""


class TestGetProvider:
    def test_groq_provider(self):
        provider = get_provider("groq", api_key="test-key")
        assert provider.__class__.__name__ == "GroqProvider"

    def test_openai_provider(self):
        provider = get_provider("openai", api_key="test-key")
        assert provider.__class__.__name__ == "OpenAIProvider"

    def test_ollama_provider(self):
        provider = get_provider("ollama")
        assert provider.__class__.__name__ == "OllamaProvider"

    def test_lmstudio_provider(self):
        provider = get_provider("lmstudio")
        assert provider.__class__.__name__ == "LMStudioProvider"

    def test_openrouter_provider(self):
        provider = get_provider("openrouter", api_key="test-key")
        assert provider.__class__.__name__ == "OpenRouterProvider"

    def test_anthropic_provider(self):
        provider = get_provider("anthropic", api_key="test-key")
        assert provider.__class__.__name__ == "AnthropicProvider"

    def test_custom_provider(self):
        provider = get_provider("custom", api_key="test-key", base_url="http://localhost:8080/v1")
        assert provider.__class__.__name__ == "CustomProvider"

    def test_unknown_provider_raises(self):
        import pytest

        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("nonexistent")

    def test_local_providers_strip_api_key(self):
        provider = get_provider("ollama", api_key="should-be-ignored")
        assert provider.api_key is None


class TestListAvailableProviders:
    def test_returns_dict(self):
        status = list_available_providers()
        assert isinstance(status, dict)
        assert "ollama" in status
        assert "groq" in status
        assert "openai" in status
        assert "anthropic" in status
        assert "openrouter" in status
        assert "lmstudio" in status

    def test_providers_are_bool(self):
        status = list_available_providers()
        for key, value in status.items():
            assert isinstance(value, bool), f"{key} is not bool"
