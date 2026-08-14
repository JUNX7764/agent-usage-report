"""Regression tests for scan_agents.py.

Covers the failure modes that caused silent agent misses in the wild:
- multiple candidate paths must aggregate into ONE entry per agent
- non-conversational tools must carry a non-'agent' category
- existing-but-unreadable dirs must surface an explicit note
- glob extension dirs must be discovered
- runtime signals / heuristic unknown-dir discovery must be present
"""

from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


scan_mod = load("scan_agents")


class ScanAgentsTests(unittest.TestCase):
    def _scan_with_home(self, home: Path):
        appdata = home / "Library" / "Application Support"
        with mock.patch.object(scan_mod, "_home", lambda: home), \
             mock.patch.object(scan_mod, "_appdata", lambda: appdata), \
             mock.patch.object(scan_mod, "_local_appdata", lambda: appdata):
            return scan_mod.scan()

    def test_multiple_candidate_paths_aggregate_into_one_entry(self):
        with TemporaryDirectory() as td:
            home = Path(td)
            (home / ".cursor").mkdir()
            (home / ".cursor" / "a.json").write_text("{}")
            cur_app = home / "Library" / "Application Support" / "Cursor"
            cur_app.mkdir(parents=True)
            (cur_app / "b.json").write_text("{}")

            result = self._scan_with_home(home)

        cursor_entries = [a for a in result["agents_found"] if a["name"] == "Cursor"]
        self.assertEqual(len(cursor_entries), 1, "Cursor must appear exactly once")
        entry = cursor_entries[0]
        self.assertEqual(len(entry["paths"]), 2)
        self.assertEqual(entry["file_count"], 2)
        self.assertEqual(entry["category"], "agent")

    def test_non_conversational_tools_are_categorized(self):
        with TemporaryDirectory() as td:
            home = Path(td)
            (home / ".ollama").mkdir()
            (home / ".ollama" / "model.bin").write_text("x")
            result = self._scan_with_home(home)

        ollama = [a for a in result["agents_found"] if a["name"] == "Ollama"]
        self.assertEqual(len(ollama), 1)
        self.assertEqual(ollama[0]["category"], "local-model")

    def test_unreadable_directory_gets_explicit_note(self):
        with TemporaryDirectory() as td:
            home = Path(td)
            claude = home / ".claude"
            claude.mkdir()
            os.chmod(claude, 0o000)
            try:
                result = self._scan_with_home(home)
            finally:
                os.chmod(claude, 0o755)

        entries = [a for a in result["agents_found"] if a["name"] == "Claude Code"]
        self.assertEqual(len(entries), 1)
        notes = entries[0].get("notes") or []
        self.assertTrue(
            any("unreadable" in n for n in notes),
            f"expected an unreadable note, got: {notes}",
        )

    def test_glob_extension_dirs_are_discovered(self):
        with TemporaryDirectory() as td:
            home = Path(td)
            ext = home / ".vscode" / "extensions" / "saoudrizwan.claude-dev-3.0.0"
            ext.mkdir(parents=True)
            (ext / "package.json").write_text("{}")
            result = self._scan_with_home(home)

        cline = [a for a in result["agents_found"] if a["name"] == "Cline"]
        self.assertEqual(len(cline), 1)
        self.assertTrue(any("saoudrizwan.claude-dev" in p for p in cline[0]["paths"]))

    def test_runtime_signals_and_heuristics_present_in_output(self):
        with TemporaryDirectory() as td:
            home = Path(td)
            result = self._scan_with_home(home)

        self.assertIn("runtime_signals", result)
        signals = result["runtime_signals"]
        for key in ("on_path", "running_processes", "env_markers", "agents_detected_at_runtime"):
            self.assertIn(key, signals)
        self.assertIn("runtime_detected_but_no_data_dir", result)
        self.assertIn("unknown_data_dir_candidates", result)

    def test_env_marker_promotes_agent_to_runtime_detected(self):
        with TemporaryDirectory() as td:
            home = Path(td)
            with mock.patch.dict(os.environ, {"CLAUDECODE": "1"}):
                result = self._scan_with_home(home)

        self.assertIn("Claude Code", result["runtime_signals"]["agents_detected_at_runtime"])
        # .claude does not exist in the fake home -> must surface as missing
        self.assertIn("Claude Code", result["runtime_detected_but_no_data_dir"])

    def test_heuristic_finds_unknown_agent_looking_dir(self):
        with TemporaryDirectory() as td:
            home = Path(td)
            mystery = home / ".brandnewagent"
            (mystery / "sessions").mkdir(parents=True)
            (mystery / "state.db").write_text("x")
            result = self._scan_with_home(home)

        paths = [c["path"] for c in result["unknown_data_dir_candidates"]]
        self.assertIn(str(mystery), paths)

    def test_known_catalog_dirs_not_reported_as_unknown(self):
        with TemporaryDirectory() as td:
            home = Path(td)
            known = home / ".claude"
            (known / "sessions").mkdir(parents=True)
            (known / "state.db").write_text("x")
            result = self._scan_with_home(home)

        paths = [c["path"] for c in result["unknown_data_dir_candidates"]]
        self.assertNotIn(str(known), paths)
        found_names = [a["name"] for a in result["agents_found"]]
        self.assertIn("Claude Code", found_names)


if __name__ == "__main__":
    unittest.main()
