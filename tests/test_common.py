"""Unit tests for agentkit_common helper functions."""
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from agentkit_common import (
    detect_runner,
    infer_role,
    parse_isoish_timestamp,
    repo_id,
    should_skip,
    validate_repo_config,
)


class TestShouldSkip(unittest.TestCase):
    def test_skips_node_modules(self):
        self.assertTrue(should_skip("node_modules/foo.js", {"node_modules"}))

    def test_skips_nested_path(self):
        self.assertTrue(should_skip("src/node_modules/bar.ts", {"node_modules"}))

    def test_does_not_skip_unrelated(self):
        self.assertFalse(should_skip("src/main.py", {"node_modules", ".git"}))

    def test_skips_dotgit(self):
        self.assertTrue(should_skip(".git/config", {".git"}))

    def test_normalizes_backslash(self):
        self.assertTrue(should_skip("node_modules\\foo.js", {"node_modules"}))

    def test_strips_leading_dotslash(self):
        self.assertTrue(should_skip("./node_modules/foo.js", {"node_modules"}))

    def test_empty_excludes(self):
        self.assertFalse(should_skip("anything.py", set()))

    def test_multi_segment_exclude(self):
        self.assertTrue(should_skip(".claude/worktrees/abc/file.py", {".claude/worktrees"}))


class TestInferRole(unittest.TestCase):
    def test_markdown_is_docs(self):
        self.assertEqual(infer_role("README.md"), "docs")

    def test_txt_is_docs(self):
        self.assertEqual(infer_role("notes.txt"), "docs")

    def test_rst_is_docs(self):
        self.assertEqual(infer_role("docs/api.rst"), "docs")

    def test_test_py_suffix(self):
        # Files ending with _test.py match the _test.py suffix rule
        self.assertEqual(infer_role("something_test.py"), "test")

    def test_tests_dir(self):
        self.assertEqual(infer_role("tests/test_main.py"), "test")

    def test_json_is_config(self):
        self.assertEqual(infer_role("config.json"), "config")

    def test_yaml_is_config(self):
        self.assertEqual(infer_role("docker-compose.yml"), "config")

    def test_api_path(self):
        self.assertEqual(infer_role("src/api/routes.py"), "api")

    def test_python_file_is_code(self):
        self.assertEqual(infer_role("src/main.py"), "code")

    def test_ts_is_code(self):
        self.assertEqual(infer_role("src/utils.ts"), "code")

    def test_c_is_code(self):
        self.assertEqual(infer_role("src/parser.c"), "code")

    def test_svelte_is_view(self):
        self.assertEqual(infer_role("src/App.svelte"), "view")

    def test_unknown_is_asset(self):
        self.assertEqual(infer_role("logo.png"), "asset")


class TestRepoId(unittest.TestCase):
    def test_returns_16_chars(self):
        rid = repo_id("/home/user/project")
        self.assertEqual(len(rid), 16)

    def test_is_hex(self):
        rid = repo_id("/home/user/project")
        int(rid, 16)  # should not raise

    def test_deterministic(self):
        self.assertEqual(repo_id("/foo/bar"), repo_id("/foo/bar"))

    def test_different_paths_differ(self):
        self.assertNotEqual(repo_id("/foo/bar"), repo_id("/foo/baz"))


class TestParseIsoishTimestamp(unittest.TestCase):
    def test_z_suffix(self):
        ts = parse_isoish_timestamp("2026-03-08T16:46:48.716Z")
        self.assertIsNotNone(ts)
        self.assertIsInstance(ts, float)
        self.assertGreater(ts, 0)

    def test_offset_format(self):
        ts = parse_isoish_timestamp("2026-01-01T00:00:00+00:00")
        self.assertIsNotNone(ts)
        self.assertIsInstance(ts, float)

    def test_none_input(self):
        self.assertIsNone(parse_isoish_timestamp(None))

    def test_empty_string(self):
        self.assertIsNone(parse_isoish_timestamp(""))

    def test_invalid_string(self):
        self.assertIsNone(parse_isoish_timestamp("not-a-timestamp"))

    def test_z_and_offset_match(self):
        ts_z = parse_isoish_timestamp("2026-03-08T16:46:48Z")
        ts_off = parse_isoish_timestamp("2026-03-08T16:46:48+00:00")
        self.assertAlmostEqual(ts_z, ts_off, places=0)


class TestValidateRepoConfig(unittest.TestCase):
    def test_valid_empty_config(self):
        errors = validate_repo_config({})
        self.assertEqual(errors, [])

    def test_non_dict_root(self):
        errors = validate_repo_config([])
        self.assertEqual(len(errors), 1)
        self.assertIn("root must be", errors[0])

    def test_index_section_wrong_type(self):
        errors = validate_repo_config({"index": "wrong"})
        self.assertGreater(len(errors), 0)
        self.assertIn("index", errors[0])

    def test_extract_section_wrong_type(self):
        errors = validate_repo_config({"extract": 42})
        self.assertGreater(len(errors), 0)
        self.assertIn("extract", errors[0])

    def test_extract_enabled_wrong_type(self):
        errors = validate_repo_config({"extract": {"enabled": "yes"}})
        self.assertGreater(len(errors), 0)
        self.assertIn("enabled", errors[0])

    def test_context_section_valid(self):
        cfg = {
            "context": {
                "max_snippets_total": 20,
                "prefer_symbol_blocks": True,
                "synonyms": {"sse": ["events"]},
            }
        }
        errors = validate_repo_config(cfg)
        self.assertEqual(errors, [])

    def test_context_max_snippets_wrong_type(self):
        errors = validate_repo_config({"context": {"max_snippets_total": "twenty"}})
        self.assertGreater(len(errors), 0)
        self.assertIn("max_snippets_total", errors[0])

    def test_unknown_keys_not_errors(self):
        # Unknown keys in unknown sections should not produce errors
        errors = validate_repo_config({"custom_section": {"foo": "bar"}})
        self.assertEqual(errors, [])

    def test_allow_custom_adapters_bool(self):
        errors = validate_repo_config({"extract": {"allow_custom_adapters": True}})
        self.assertEqual(errors, [])

    def test_allow_custom_adapters_wrong_type(self):
        errors = validate_repo_config({"extract": {"allow_custom_adapters": "yes"}})
        self.assertGreater(len(errors), 0)


class TestDetectRunner(unittest.TestCase):
    def test_override_all(self):
        self.assertEqual(detect_runner({"AGENTKIT_TELEMETRY_SCOPE": "all"}), "all")

    def test_override_codex(self):
        self.assertEqual(detect_runner({"AGENTKIT_RUNNER": "codex"}), "codex")

    def test_detects_codex_from_env_prefix(self):
        self.assertEqual(detect_runner({"CODEX_CI": "1"}), "codex")

    def test_detects_claude_from_marker(self):
        self.assertEqual(detect_runner({"CLAUDE_CODE": "1"}), "claude")

    def test_defaults_to_all(self):
        self.assertEqual(detect_runner({}), "all")


class TestAdapterTrustGate(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
        from agent_extractors import load_adapters
        self.load_adapters = load_adapters

    def test_builtin_adapter_loads_without_flag(self):
        cfg = {"extract": {"adapters": [{"type": "builtin", "name": "esp-idf-http-routes"}]}}
        adapters = self.load_adapters(".", cfg, allow_custom=False)
        self.assertEqual(len(adapters), 1)

    def test_python_adapter_blocked_by_default(self, capsys=None):
        cfg = {"extract": {"adapters": [{"type": "python", "name": "my-adapter", "file": "/nonexistent.py"}]}}
        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            adapters = self.load_adapters(".", cfg, allow_custom=False)
            stderr_output = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr
        self.assertEqual(len(adapters), 0)
        self.assertIn("allow_custom_adapters", stderr_output)

    def test_python_adapter_allowed_with_flag(self):
        import tempfile
        # Create a minimal valid adapter file
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("def extract(path, rel_path, ext, lines, text, config):\n    return []\n")
            adapter_file = f.name
        try:
            cfg = {"extract": {"adapters": [{"type": "python", "name": "t", "file": adapter_file}]}}
            adapters = self.load_adapters(".", cfg, allow_custom=True)
            self.assertEqual(len(adapters), 1)
        finally:
            import os
            os.unlink(adapter_file)

    def test_python_adapter_allowed_via_config(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("def extract(path, rel_path, ext, lines, text, config):\n    return []\n")
            adapter_file = f.name
        try:
            cfg = {
                "extract": {
                    "allow_custom_adapters": True,
                    "adapters": [{"type": "python", "name": "t", "file": adapter_file}],
                }
            }
            adapters = self.load_adapters(".", cfg, allow_custom=False)
            self.assertEqual(len(adapters), 1)
        finally:
            import os
            os.unlink(adapter_file)


if __name__ == "__main__":
    unittest.main()
