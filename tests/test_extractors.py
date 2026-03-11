"""Unit tests for agent_extractors symbol extraction functions."""
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from agent_extractors import extract_python, extract_ts_js, extract_c_like


class TestExtractPython(unittest.TestCase):
    SIMPLE = [
        "def hello():",
        "    pass",
        "",
        "def world(x: int) -> str:",
        "    return str(x)",
    ]

    def test_finds_two_functions(self):
        syms = extract_python(self.SIMPLE)
        names = [s["symbol"] for s in syms]
        self.assertIn("hello", names)
        self.assertIn("world", names)

    def test_kind_is_function(self):
        syms = extract_python(self.SIMPLE)
        for s in syms:
            self.assertEqual(s["kind"], "function")

    def test_line_numbers_are_ints(self):
        syms = extract_python(self.SIMPLE)
        for s in syms:
            self.assertIsInstance(s["start_line"], int)
            self.assertIsInstance(s["end_line"], int)

    def test_empty_input(self):
        self.assertEqual(extract_python([]), [])

    def test_nested_methods(self):
        lines = [
            "class Foo:",
            "    def bar(self):",
            "        pass",
            "    def baz(self):",
            "        return 1",
        ]
        syms = extract_python(lines)
        names = [s["symbol"] for s in syms]
        self.assertIn("bar", names)
        self.assertIn("baz", names)

    def test_no_false_positives_on_calls(self):
        lines = ["x = foo()", "y = bar(1, 2)"]
        syms = extract_python(lines)
        self.assertEqual(syms, [])


class TestExtractTsJs(unittest.TestCase):
    SIMPLE = [
        "function greet(name) {",
        "  return 'hi ' + name;",
        "}",
        "",
        "const arrowFn = (x) => {",
        "  return x * 2;",
        "};",
    ]

    def test_finds_function_declaration(self):
        syms = extract_ts_js(self.SIMPLE)
        names = [s["symbol"] for s in syms]
        self.assertIn("greet", names)

    def test_finds_arrow_function(self):
        syms = extract_ts_js(self.SIMPLE)
        names = [s["symbol"] for s in syms]
        self.assertIn("arrowFn", names)

    def test_empty_input(self):
        self.assertEqual(extract_ts_js([]), [])

    def test_ignores_control_flow(self):
        lines = [
            "if (x) {",
            "  doSomething();",
            "}",
            "for (let i = 0; i < 10; i++) {",
            "  process(i);",
            "}",
        ]
        syms = extract_ts_js(lines)
        self.assertEqual(syms, [])

    def test_method_style(self):
        lines = [
            "  processEvent(data) {",
            "    return data;",
            "  }",
        ]
        syms = extract_ts_js(lines)
        names = [s["symbol"] for s in syms]
        self.assertIn("processEvent", names)


class TestExtractCLike(unittest.TestCase):
    SIMPLE = [
        "int add(int a, int b) {",
        "    return a + b;",
        "}",
        "",
        "void do_thing(char *s) {",
        "    printf(s);",
        "}",
    ]

    def test_finds_two_functions(self):
        syms = extract_c_like(self.SIMPLE)
        names = [s["symbol"] for s in syms]
        self.assertIn("add", names)
        self.assertIn("do_thing", names)

    def test_kind_is_function(self):
        syms = extract_c_like(self.SIMPLE)
        for s in syms:
            self.assertEqual(s["kind"], "function")

    def test_empty_input(self):
        self.assertEqual(extract_c_like([]), [])

    def test_no_false_positive_on_declaration(self):
        # Function declaration (no body) should not match
        lines = ["int foo(int x);"]
        syms = extract_c_like(lines)
        self.assertEqual(syms, [])

    def test_pointer_return_type(self):
        lines = [
            "char* get_name(int id) {",
            "    return names[id];",
            "}",
        ]
        syms = extract_c_like(lines)
        names = [s["symbol"] for s in syms]
        self.assertIn("get_name", names)


if __name__ == "__main__":
    unittest.main()
