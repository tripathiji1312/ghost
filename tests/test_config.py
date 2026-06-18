from ghost.config import GhostConfig, get_config


class TestGhostConfig:
    def test_default_config(self):
        config = GhostConfig()
        assert config.project_name == "my-project"
        assert config.language == "python"
        assert config.ai.provider == "ollama"
        assert config.ai.model == "llama3.2"
        assert config.ai.rate_limit_rpm == 30
        assert config.tests.framework == "pytest"
        assert config.tests.output_dir == "tests"
        assert config.tests.auto_heal is True
        assert config.tests.max_heal_attempts == 3
        assert config.tests.use_judge is True
        assert config.watcher.debounce_seconds == 15
        assert config.watcher.patterns == ["*.py"]

    def test_from_dict_full(self):
        data = {
            "project": {"name": "myapp", "language": "python"},
            "ai": {"provider": "groq", "model": "llama-3.3-70b-versatile", "rate_limit_rpm": 30},
            "scanner": {"ignore_dirs": [".venv"], "ignore_files": ["setup.py"]},
            "tests": {
                "framework": "pytest",
                "output_dir": "tests",
                "auto_heal": True,
                "max_heal_attempts": 5,
            },
            "watcher": {"debounce_seconds": 10, "patterns": ["*.py"]},
        }
        config = GhostConfig.from_dict(data)
        assert config.project_name == "myapp"
        assert config.ai.provider == "groq"
        assert config.ai.model == "llama-3.3-70b-versatile"
        assert config.ai.rate_limit_rpm == 30
        assert config.tests.max_heal_attempts == 5
        assert config.watcher.debounce_seconds == 10

    def test_from_dict_partial(self):
        data = {"ai": {"provider": "openai"}}
        config = GhostConfig.from_dict(data)
        assert config.ai.provider == "openai"
        assert config.ai.model == "llama3.2"
        assert config.project_name == "my-project"

    def test_get_config_returns_defaults_when_no_project(self):
        config = get_config(None)
        assert isinstance(config, GhostConfig)

    def test_get_config_loads_from_toml(self, temp_project_with_config):
        config = get_config(temp_project_with_config)
        assert config.project_name == "test-project"
        assert config.ai.provider == "ollama"
        assert config.ai.model == "llama3.2"
        assert config.watcher.debounce_seconds == 2
        assert config.tests.auto_heal is True

    def test_ai_config_serialization(self):
        from dataclasses import fields

        from ghost.config import AIConfig

        ai = AIConfig(provider="groq", model="mixtral", rate_limit_rpm=60)
        assert ai.provider == "groq"
        assert ai.model == "mixtral"
        assert ai.rate_limit_rpm == 60
        assert ai.base_url is None

        field_names = {f.name for f in fields(AIConfig)}
        assert "provider" in field_names
        assert "api_key" in field_names
        assert "max_retries" in field_names
