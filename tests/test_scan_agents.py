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

    def test_deepseek_harness_detected_and_not_flagged_unknown(self):
        with TemporaryDirectory() as td:
            home = Path(td)
            session = home / ".dsh" / "sessions" / "--home-u-demo--" / "session-abc"
            session.mkdir(parents=True)
            (session / "session.jsonl.zstd").write_bytes(b"x")
            (home / ".dsh" / "storages").mkdir()
            (home / ".dsh" / "storages" / "workspace.json").write_text("{}")
            result = self._scan_with_home(home)

        entries = [a for a in result["agents_found"] if a["name"] == "DeepSeek Harness"]
        self.assertEqual(len(entries), 1, "DeepSeek Harness must appear exactly once")
        self.assertEqual(entries[0]["category"], "agent")
        unknown_paths = [c["path"] for c in result["unknown_data_dir_candidates"]]
        self.assertNotIn(str(home / ".dsh"), unknown_paths)

    def test_deepseek_harness_dsh_home_env_override(self):
        with TemporaryDirectory() as td:
            home = Path(td)
            custom = home / "custom-dsh-home"
            (custom / "sessions").mkdir(parents=True)
            with mock.patch.dict(os.environ, {"DSH_HOME": str(custom)}):
                result = self._scan_with_home(home)

        entries = [a for a in result["agents_found"] if a["name"] == "DeepSeek Harness"]
        self.assertEqual(len(entries), 1)
        self.assertIn(str(custom), entries[0]["paths"])

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

    def test_single_session_marker_is_enough_for_unknown_candidate(self):
        # 召回优先：只有 1 个标记（旧版要求 ≥2 会漏掉 .kimi 这类目录）
        with TemporaryDirectory() as td:
            home = Path(td)
            mystery = home / ".weakagent"
            (mystery / "sessions").mkdir(parents=True)
            result = self._scan_with_home(home)

        paths = [c["path"] for c in result["unknown_data_dir_candidates"]]
        self.assertIn(str(mystery), paths)

    def test_nested_session_marker_discovered_two_levels_deep(self):
        # 探针下探两层：sessions 埋在子目录里也能发现
        with TemporaryDirectory() as td:
            home = Path(td)
            mystery = home / ".deepagent"
            (mystery / "data" / "sessions").mkdir(parents=True)
            (mystery / "data" / "sessions" / "a.jsonl").write_text("{}")
            result = self._scan_with_home(home)

        paths = [c["path"] for c in result["unknown_data_dir_candidates"]]
        self.assertIn(str(mystery), paths)

    def test_chromium_profile_dirs_not_flagged(self):
        # Chromium/Electron 档案（Sessions+History+Cookies）不算 Agent 数据
        with TemporaryDirectory() as td:
            home = Path(td)
            appdata = home / "Library" / "Application Support"
            profile = appdata / "SomeBrowser"
            profile.mkdir(parents=True)
            (profile / "Sessions").mkdir()
            (profile / "Cookies").write_text("x")
            (profile / "Preferences").write_text("x")
            (profile / "History").write_text("x")
            (profile / "History-journal").write_text("x")
            (profile / "updater_history.jsonl").write_text("x")
            result = self._scan_with_home(home)

        paths = [c["path"] for c in result["unknown_data_dir_candidates"]]
        self.assertNotIn(str(profile), paths)

    def test_db_without_session_keyword_is_not_a_marker(self):
        # 任意应用的数据库（如 utmc_store.sqlite）不该被当成会话痕迹
        with TemporaryDirectory() as td:
            home = Path(td)
            appdata = home / "Library" / "Application Support"
            app = appdata / "SomeApp"
            app.mkdir(parents=True)
            (app / "utmc_store.sqlite").write_text("x")
            (app / "state.db").write_text("x")
            result = self._scan_with_home(home)

        paths = [c["path"] for c in result["unknown_data_dir_candidates"]]
        self.assertNotIn(str(app), paths)

    def test_system_noise_prefixes_and_dirs_skipped(self):
        with TemporaryDirectory() as td:
            home = Path(td)
            appdata = home / "Library" / "Application Support"
            for name in ("com.apple.akd", "Dock", "Quark"):
                d = appdata / name
                (d / "sessions").mkdir(parents=True)
            cache = home / ".cache"
            (cache / "sessions").mkdir(parents=True)
            result = self._scan_with_home(home)

        paths = [c["path"] for c in result["unknown_data_dir_candidates"]]
        for name in ("com.apple.akd", "Dock", "Quark"):
            self.assertNotIn(str(appdata / name), paths)
        self.assertNotIn(str(cache), paths)

    def test_unknown_candidates_carry_activity_for_ranking(self):
        # 认领清单带 file_count / newest_activity，便于按活跃度排序认领
        with TemporaryDirectory() as td:
            home = Path(td)
            mystery = home / ".activeagent"
            s = mystery / "sessions"
            s.mkdir(parents=True)
            (s / "a.jsonl").write_text("{}")
            result = self._scan_with_home(home)

        entry = next(
            c for c in result["unknown_data_dir_candidates"]
            if c["path"] == str(mystery)
        )
        self.assertIn("file_count", entry)
        self.assertIn("newest_activity", entry)
        self.assertGreaterEqual(entry["file_count"], 1)


if __name__ == "__main__":
    unittest.main()
