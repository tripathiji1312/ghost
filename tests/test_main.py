from ghost.main import CheckPath, ReadFile, getFileNameFromPath


class TestGetFileNameFromPath:
    def test_simple_filename(self):
        assert getFileNameFromPath("/path/to/file.py") == "file.py"

    def test_windows_path(self):
        assert getFileNameFromPath("C:\\Users\\test\\file.py") == "file.py"

    def test_mixed_separators(self):
        assert getFileNameFromPath("/path/to\\file.py") == "file.py"

    def test_just_filename(self):
        assert getFileNameFromPath("file.py") == "file.py"

    def test_current_dir(self):
        assert getFileNameFromPath("./file.py") == "file.py"


class TestCheckPath:
    def test_accepts_python_file(self):
        assert CheckPath("app.py", "/project/app.py") is True

    def test_rejects_tests_directory(self):
        assert CheckPath("test_app.py", "/project/tests/test_app.py") is False

    def test_rejects_test_in_filename(self):
        assert CheckPath("test_app.py", "/project/src/test_app.py") is False

    def test_rejects_tmp_in_filename(self):
        assert CheckPath("tmp_file.py", "/project/src/tmp_file.py") is False

    def test_rejects_git_file(self):
        assert CheckPath(".gitconfig", "/project/.gitconfig") is False

    def test_rejects_log_file(self):
        assert CheckPath("output.log", "/project/output.log") is False

    def test_rejects_non_python(self):
        assert CheckPath("readme.md", "/project/readme.md") is False

    def test_rejects_temp_suffix(self):
        assert CheckPath("app.py", "/project/app.py~") is False

    def test_empty_full_path(self):
        assert CheckPath("main.py") is True

    def test_rejects_test_dir_in_path(self):
        assert CheckPath("utils.py", "/project/tests/utils.py") is False

    def test_rejects_pycache(self):
        # This is handled in on_modified separately, but CheckPath doesn't reject pycache
        assert CheckPath("module.py", "/project/__pycache__/module.py") is True


class TestReadFile:
    def test_reads_existing_file(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")
        assert ReadFile(str(test_file)) == "hello world"

    def test_returns_none_for_missing_file(self):
        assert ReadFile("/nonexistent/file.py") is None

    def test_returns_none_for_directory(self, tmp_path):
        assert ReadFile(str(tmp_path)) is None

    def test_handles_utf8(self, tmp_path):
        test_file = tmp_path / "hello.py"
        test_file.write_bytes("def hello():\n    return '😊'\n".encode("utf-8"))
        result = ReadFile(str(test_file))
        assert result is not None
        assert "😊" in result
