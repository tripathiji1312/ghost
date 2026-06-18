import ast

from ghost.init import CodeAnalyzer, add_parent_links, analyze_file


class TestCodeAnalyzer:
    def test_empty_module(self):
        tree = ast.parse("")
        analyzer = CodeAnalyzer()
        analyzer.visit(tree)
        assert analyzer.functions == []
        assert analyzer.classes == {}

    def test_detects_top_level_functions(self):
        source = """
def foo():
    pass

def bar(x, y):
    return x + y
"""
        tree = ast.parse(source)
        add_parent_links(tree)
        analyzer = CodeAnalyzer()
        analyzer.visit(tree)
        assert "foo()" in analyzer.functions
        assert "bar(x, y)" in analyzer.functions

    def test_ignores_nested_functions(self):
        source = """
def outer():
    def inner():
        pass
    return inner
"""
        tree = ast.parse(source)
        add_parent_links(tree)
        analyzer = CodeAnalyzer()
        analyzer.visit(tree)
        assert "outer()" in analyzer.functions
        assert "inner()" not in analyzer.functions

    def test_detects_classes_and_methods(self):
        source = """
class MyClass:
    def method_a(self):
        pass

    def method_b(self, arg):
        pass
"""
        tree = ast.parse(source)
        add_parent_links(tree)
        analyzer = CodeAnalyzer()
        analyzer.visit(tree)
        assert "MyClass" in analyzer.classes
        assert "method_a" in analyzer.classes["MyClass"]
        assert "method_b" in analyzer.classes["MyClass"]

    def test_empty_class_has_no_methods(self):
        source = """
class Empty:
    pass
"""
        tree = ast.parse(source)
        add_parent_links(tree)
        analyzer = CodeAnalyzer()
        analyzer.visit(tree)
        assert "Empty" in analyzer.classes
        assert analyzer.classes["Empty"] == []


class TestAnalyzeFile:
    def test_analyzes_valid_python(self, tmp_path):
        py_file = tmp_path / "module.py"
        py_file.write_text("""
def greet(name):
    return f"Hi {name}"

class Handler:
    def run(self):
        pass
""")
        functions, classes = analyze_file(str(py_file))
        assert functions is not None
        assert classes is not None
        assert "greet(name)" in functions
        assert "Handler" in classes

    def test_returns_none_on_syntax_error(self, tmp_path):
        py_file = tmp_path / "broken.py"
        py_file.write_text("def foo(:\n    pass\n")
        result = analyze_file(str(py_file))
        assert result is None
