"""Unit tests for agentkit_common helper functions."""
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from agentkit_common import should_skip, infer_role, repo_id, parse_isoish_timestamp


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


if __name__ == "__main__":
    unittest.main()
