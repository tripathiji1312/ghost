from ghost.chat import TestGenerator


class TestCleanLlmResponse:
    def setup_method(self):
        self.generator = TestGenerator()

    def test_removes_python_markdown(self):
        raw = "```python\nprint('hello')\n```"
        cleaned = self.generator.clean_llm_response(raw)
        assert cleaned == "print('hello')"

    def test_strips_whitespace(self):
        raw = "\n  \nprint('hello')\n  \n"
        cleaned = self.generator.clean_llm_response(raw)
        assert cleaned == "print('hello')"

    def test_handles_already_clean_code(self):
        raw = "def foo():\n    pass"
        cleaned = self.generator.clean_llm_response(raw)
        assert cleaned == raw

    def test_removes_empty_backticks(self):
        raw = "some text ``` ``` more"
        cleaned = self.generator.clean_llm_response(raw)
        assert "some text" not in cleaned or cleaned == raw.strip()

    def test_only_returns_code_block(self):
        raw = "Here is the code:\n```python\ndef foo():\n    pass\n```\nThat's it."
        cleaned = self.generator.clean_llm_response(raw)
        assert cleaned == "def foo():\n    pass"
        assert "Here is the code" not in cleaned

    def test_handles_empty_string(self):
        assert self.generator.clean_llm_response("") == ""

    def test_handles_only_whitespace(self):
        assert self.generator.clean_llm_response("   \n  \n  ") == ""


class TestConsultTheJudge:
    def setup_method(self):
        self.generator = TestGenerator()

    def test_raises_when_context_missing(self, tmp_path):
        import pytest

        with pytest.raises(FileNotFoundError):
            self.generator.consult_the_judge(
                "", str(tmp_path), "test.py", str(tmp_path / "nonexistent.py"), {}
            )

    def test_raises_when_test_file_missing(self, tmp_path):
        import json

        import pytest

        ghost_dir = tmp_path / ".ghost"
        ghost_dir.mkdir()
        (ghost_dir / "context.json").write_text(
            json.dumps({"test.py": "Functions: foo; Classes: None"})
        )
        with pytest.raises(FileNotFoundError):
            self.generator.consult_the_judge(
                "", str(tmp_path), "test.py", str(tmp_path / "nonexistent.py"), {}
            )
