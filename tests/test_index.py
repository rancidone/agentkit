"""Unit tests for agent-index internal functions."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import pathlib
import sqlite3
import sys
import tempfile
import time
import types
import unittest

REPO_ROOT = pathlib.Path(__file__).parent.parent

# Load agent-index as a module (extensionless script — use SourceFileLoader directly)
_loader = importlib.machinery.SourceFileLoader("agent_index", str(REPO_ROOT / "agent-index"))
_mod = types.ModuleType("agent_index")
_loader.exec_module(_mod)

_tokenize = _mod._tokenize
_score_candidates = _mod._score_candidates
parse_tasks_from_todo = _mod.parse_tasks_from_todo
open_db = _mod.open_db
db_path = _mod.db_path


def _make_index_db(tmp_dir: str, repo: str) -> sqlite3.Connection:
    """Create a minimal index DB for testing _score_candidates."""
    conn = open_db(db_path(repo))
    # Insert test file rows
    now = time.time()
    files = [
        (repo, "agent-telemetry", "code", ".py", 0, 1000, now, now),
        (repo, "src/api/routes.py", "api", ".py", 0, 500, now, now),
        (repo, "src/views/App.svelte", "view", ".svelte", 0, 300, now, now),
        (repo, "tests/test_ingest.py", "test", ".py", 1, 200, now, now),
        (repo, "agentkit_common.py", "code", ".py", 0, 2000, now, now),
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO files(repo, path, role, ext, is_test, size, mtime, updated_at) VALUES (?,?,?,?,?,?,?,?)",
        files,
    )
    conn.commit()
    return conn


class TestTokenize(unittest.TestCase):
    def test_basic_split(self):
        tokens = _tokenize("add retry logic")
        self.assertIn("add", tokens)
        self.assertIn("retry", tokens)
        self.assertIn("logic", tokens)

    def test_filters_short_tokens(self):
        tokens = _tokenize("do it now")
        # "do", "it" len<=2 filtered; "now" len=3 kept
        self.assertNotIn("do", tokens)
        self.assertNotIn("it", tokens)
        self.assertIn("now", tokens)

    def test_deduplication(self):
        tokens = _tokenize("retry retry retry")
        self.assertEqual(tokens.count("retry"), 1)

    def test_lowercase(self):
        tokens = _tokenize("Add Retry Logic")
        self.assertIn("add", tokens)
        self.assertIn("retry", tokens)

    def test_synonym_expansion_sse(self):
        tokens = _tokenize("handle sse events")
        # "sse" should expand to ["events", "event", "routes_events", "live"]
        self.assertIn("events", tokens)
        self.assertIn("live", tokens)

    def test_synonym_expansion_endpoint(self):
        tokens = _tokenize("add endpoint handler")
        self.assertIn("route", tokens)
        self.assertIn("api", tokens)

    def test_normalizes_backticks(self):
        tokens = _tokenize("add `retry` to `ingest`")
        self.assertIn("retry", tokens)
        self.assertIn("ingest", tokens)
        self.assertNotIn("`retry`", tokens)

    def test_normalizes_slashes(self):
        tokens = _tokenize("src/api/routes handler")
        self.assertIn("src", tokens)
        self.assertIn("api", tokens)

    def test_empty_string(self):
        tokens = _tokenize("")
        self.assertEqual(tokens, [])

    def test_repo_synonyms_merged(self):
        cfg = {"context": {"synonyms": {"cache": ["redis", "memcache"]}}}
        tokens = _tokenize("invalidate cache", cfg)
        self.assertIn("redis", tokens)
        self.assertIn("memcache", tokens)

    def test_repo_synonyms_override_builtin(self):
        # Repo can override built-in synonym mapping
        cfg = {"context": {"synonyms": {"sse": ["custom_event"]}}}
        tokens = _tokenize("handle sse stream", cfg)
        self.assertIn("custom_event", tokens)

    def test_no_cfg_uses_builtin_only(self):
        tokens = _tokenize("handle sse", None)
        self.assertIn("live", tokens)  # built-in synonym still present

    def test_empty_synonyms_cfg(self):
        cfg = {"context": {"synonyms": {}}}
        tokens = _tokenize("handle sse", cfg)
        self.assertIn("live", tokens)  # built-in still works


class TestScoreCandidates(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Set AGENTKIT_STATE_DIR so DB goes to our temp dir
        os.environ["AGENTKIT_STATE_DIR"] = self.tmp
        self.repo = self.tmp + "/testrepo"
        os.makedirs(self.repo, exist_ok=True)
        _make_index_db(self.tmp, self.repo)

    def tearDown(self):
        del os.environ["AGENTKIT_STATE_DIR"]

    def test_token_match_raises_score(self):
        # "telemetry" appears in "agent-telemetry" path
        results = _score_candidates(self.repo, "fix telemetry ingest", 10)
        paths = [r[1] for r in results]
        self.assertIn("agent-telemetry", paths)

    def test_results_sorted_by_score_desc(self):
        results = _score_candidates(self.repo, "fix telemetry ingest", 10)
        scores = [r[0] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_limit_respected(self):
        results = _score_candidates(self.repo, "anything routes api", 2)
        self.assertLessEqual(len(results), 2)

    def test_returns_tuples_of_5(self):
        # Returns (score, path, role, is_test, debug_dict)
        results = _score_candidates(self.repo, "routes endpoint", 10)
        for r in results:
            self.assertEqual(len(r), 5)
            self.assertIsInstance(r[4], dict)
            self.assertIn("path_score", r[4])

    def test_fallback_when_no_match(self):
        # A task with no token matches falls back to api/view/model/test files
        results = _score_candidates(self.repo, "zzz yyy xxx", 10)
        # Should still return something (fallback)
        self.assertGreater(len(results), 0)

    def test_debug_has_all_fields(self):
        results = _score_candidates(self.repo, "fix telemetry ingest", 10)
        for score, path, role, is_test, debug in results:
            self.assertIn("path_score", debug)
            self.assertIn("content_score", debug)
            self.assertIn("symbol_score", debug)

    def test_content_grep_boosts_keyword_match(self):
        # Write a file with a unique keyword that won't be in the path
        unique_file = os.path.join(self.repo, "utils.py")
        with open(unique_file, "w") as f:
            f.write("# xyzretrylogicxyz\n" * 10)
        # Insert it into the DB
        conn = open_db(db_path(self.repo))
        now = time.time()
        conn.execute(
            "INSERT OR REPLACE INTO files(repo,path,role,ext,is_test,size,mtime,updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (self.repo, "utils.py", "code", ".py", 0, 100, now, now),
        )
        conn.commit()
        results = _score_candidates(self.repo, "xyzretrylogicxyz", 10)
        paths = [r[1] for r in results]
        # Should find utils.py via content grep even though keyword not in path
        self.assertIn("utils.py", paths)
        # content_score should be > 0 for utils.py
        for score, path, role, is_test, debug in results:
            if path == "utils.py":
                self.assertGreater(debug["content_score"], 0)


class TestParseTasksFromTodo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _write_todo(self, content: str) -> str:
        path = os.path.join(self.tmp, "TODO.md")
        with open(path, "w") as f:
            f.write(content)
        return self.tmp

    def test_basic_parsing(self):
        repo = self._write_todo(
            "# TODO\n\n## Phase 1: Test\n\n- [ ] task one\n- [x] task two\n"
        )
        tasks = parse_tasks_from_todo(repo)
        self.assertEqual(len(tasks), 2)

    def test_undone_task(self):
        repo = self._write_todo("# TODO\n\n## Phase 1\n\n- [ ] do something\n")
        tasks = parse_tasks_from_todo(repo)
        self.assertEqual(tasks[0]["is_done"], 0)

    def test_done_task(self):
        repo = self._write_todo("# TODO\n\n## Phase 1\n\n- [x] already done\n")
        tasks = parse_tasks_from_todo(repo)
        self.assertEqual(tasks[0]["is_done"], 1)

    def test_task_text_extracted(self):
        repo = self._write_todo("# TODO\n\n## Phase 1\n\n- [ ] write the tests\n")
        tasks = parse_tasks_from_todo(repo)
        self.assertEqual(tasks[0]["text"], "write the tests")

    def test_phase_lowercased_and_dashed(self):
        repo = self._write_todo(
            "# TODO\n\n## Phase 1: Automated Test Suite\n\n- [ ] task\n"
        )
        tasks = parse_tasks_from_todo(repo)
        self.assertEqual(tasks[0]["phase"], "phase-1:-automated-test-suite")

    def test_task_id_format(self):
        repo = self._write_todo("# TODO\n\n## Phase 1\n\n- [ ] task\n")
        tasks = parse_tasks_from_todo(repo)
        task_id = tasks[0]["task_id"]
        # Should be "{phase}-L{line_number}"
        self.assertRegex(task_id, r"phase-1-L\d+")

    def test_no_todo_file(self):
        empty_dir = tempfile.mkdtemp()
        tasks = parse_tasks_from_todo(empty_dir)
        self.assertEqual(tasks, [])

    def test_multiple_phases(self):
        repo = self._write_todo(
            "# TODO\n\n## Phase 1\n\n- [ ] task a\n\n## Phase 2\n\n- [ ] task b\n"
        )
        tasks = parse_tasks_from_todo(repo)
        phases = {t["phase"] for t in tasks}
        self.assertIn("phase-1", phases)
        self.assertIn("phase-2", phases)

    def test_unphased_tasks(self):
        repo = self._write_todo("# TODO\n\n- [ ] orphan task\n")
        tasks = parse_tasks_from_todo(repo)
        self.assertEqual(tasks[0]["phase"], "unphased")

    def test_line_number_is_correct(self):
        repo = self._write_todo("# TODO\n\n## Phase 1\n\n- [ ] task\n")
        tasks = parse_tasks_from_todo(repo)
        # Line 5 in 1-indexed
        self.assertEqual(tasks[0]["line_no"], 5)


if __name__ == "__main__":
    unittest.main()
