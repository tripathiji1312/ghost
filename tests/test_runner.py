from ghost.runner import classify_error, get_project_tree


class TestClassifyError:
    def test_syntax_indentation_error(self):
        assert (
            classify_error(
                '  File "test.py", line 1\n    IndentationError: unexpected indent\n', ""
            )
            == "SYNTAX"
        )

    def test_syntax_module_not_found(self):
        assert classify_error("ModuleNotFoundError: No module named 'foo'\n", "") == "SYNTAX"

    def test_syntax_import_error(self):
        assert classify_error("ImportError: cannot import name 'bar'\n", "") == "SYNTAX"

    def test_runtime_attribute_error(self):
        assert (
            classify_error("AttributeError: 'NoneType' object has no attribute 'foo'\n", "")
            == "RUNTIME"
        )

    def test_logic_assertion_error(self):
        assert classify_error("AssertionError: assert 1 == 2\n", "") == "LOGIC"

    def test_unknown_error(self):
        assert classify_error("TypeError: unsupported operand type(s)\n", "") == "UNKNOWN"

    def test_empty_logs(self):
        assert classify_error("", "") == "UNKNOWN"

    def test_stdout_contains_error(self):
        assert classify_error("", "ModuleNotFoundError: No module named 'bar'") == "SYNTAX"

    def test_stderr_and_stdout_combined(self):
        assert classify_error("some output\n", "IndentationError: unexpected indent\n") == "SYNTAX"


class TestGetProjectTree:
    def test_empty_directory(self, tmp_path):
        result = get_project_tree(str(tmp_path))
        assert result.startswith("PROJECT STRUCTURE:\n")

    def test_ignores_venv(self, tmp_path):
        (tmp_path / ".venv").mkdir()
        (tmp_path / "main.py").write_text("# test")
        result = get_project_tree(str(tmp_path))
        assert ".venv/" not in result
        assert "main.py" in result

    def test_ignores_git(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / "main.py").write_text("# test")
        result = get_project_tree(str(tmp_path))
        assert ".git/" not in result
        assert "main.py" in result

    def test_only_shows_py_files(self, tmp_path):
        (tmp_path / "main.py").write_text("# test")
        (tmp_path / "data.json").write_text("{}")
        (tmp_path / "notes.md").write_text("# Notes")
        result = get_project_tree(str(tmp_path))
        assert "main.py" in result
        assert "data.json" not in result
        assert "notes.md" not in result

    def test_custom_ignore_dirs(self, tmp_path):
        (tmp_path / "build").mkdir()
        (tmp_path / "build/output.py").write_text("# built")
        result = get_project_tree(str(tmp_path), ignore_dirs={"build"})
        assert "build/" not in result
