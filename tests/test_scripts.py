from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


inventory_mod = load("inventory")
secret_mod = load("scan_secrets")
git_mod = load("collect_git_evidence")
build_mod = load("build_report_data")
render_mod = load("render_report")


def sample_input():
    return {
        "owner": "小朱",
        "period_start": "2026-04-01",
        "period_end": "2026-06-30",
        "agents": [
            {"name": "Proma", "session_count": 10, "first_seen": "2026-04-02", "last_seen": "2026-06-29"},
            {"name": "Cursor", "session_count": 3},
        ],
        "projects": [
            {
                "name": "周报自动化",
                "one_liner": "把每周汇总从 2 小时压到 10 分钟。",
                "ai_tools": ["Proma"],
                "badges": [{"text": "省时 90%"}],
                "milestones": [{"date": "2026-05-11", "text": "第一版上线"}],
            }
        ],
        "narrative": {"headline": "轻松回顾", "paragraphs": ["一段 <b>总结</b>。"]},
        "session_timestamps": [
            "2026-04-12T23:40:00",  # Sunday night
            "2026-04-13T09:10:00",
            "2026-04-14T10:00:00",
            "2026-04-18T15:00:00",  # Saturday
        ],
    }


class KeptScriptTests(unittest.TestCase):
    def test_inventory_hashes_files_and_does_not_follow_symlink_directory(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as outside:
            root = Path(td)
            (root / "a.txt").write_text("hello", encoding="utf-8")
            (Path(outside) / "secret.txt").write_text("outside", encoding="utf-8")
            try:
                import os
                os.symlink(outside, root / "linked")
            except OSError:
                self.skipTest("symlink unavailable")
            result = inventory_mod.inventory(root)
            self.assertEqual(result["file_count"], 1)
            self.assertEqual(result["files"][0]["relative_path"], "a.txt")
            self.assertEqual(len(result["files"][0]["sha256"]), 64)
            self.assertIn("symlink_directory_not_followed", {row["reason"] for row in result["skipped"]})

    def test_secret_scan_never_returns_full_value(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            secret = "sk-abcdefghijklmnopqrstuvwxyz123456"
            (root / "config.txt").write_text(f"api_key={secret}\n", encoding="utf-8")
            result = secret_mod.scan(root)
            serialized = json.dumps(result)
            self.assertGreater(result["finding_count"], 0)
            self.assertNotIn(secret, serialized)
            self.assertFalse(result["full_values_returned"])

    def test_git_collection_includes_representative_patch(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test User"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            (repo / "app.py").write_text("print('v1')\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "app.py"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "feat: add app"], check=True)
            result = git_mod.collect(repo, identities=["test@example.com"], representative_count=1)
            self.assertEqual(result["summary"]["commit_count"], 1)
            self.assertEqual(len(result["representative_commits"]), 1)
            self.assertIn("app.py", result["representative_commits"][0]["files"])


class BuildReportDataTests(unittest.TestCase):
    def test_period_label_quarter_and_custom(self):
        self.assertEqual(build_mod.period_label(date(2026, 4, 1), date(2026, 6, 30)), "2026Q2")
        self.assertEqual(build_mod.period_label(date(2026, 4, 15), date(2026, 6, 30)), "202604-202606")
        self.assertEqual(build_mod.period_label(date(2026, 1, 1), date(2026, 12, 31)), "202601-202612")

    def test_period_noun_matches_review_range(self):
        self.assertEqual(build_mod.period_noun(date(2026, 4, 1), date(2026, 6, 30)), "本季")
        self.assertEqual(build_mod.period_noun(date(2026, 5, 1), date(2026, 5, 31)), "本月")
        self.assertEqual(build_mod.period_noun(date(2026, 1, 1), date(2026, 12, 31)), "今年")
        self.assertEqual(build_mod.period_noun(date(2026, 4, 15), date(2026, 6, 30)), "这段时间")
        self.assertEqual(build_mod.period_noun(date(2025, 1, 1), date(2026, 6, 30)), "这段时间")

    def test_render_uses_period_noun_not_hardcoded_quarter(self):
        data = sample_input()
        data["period_start"] = "2026-05-01"
        data["period_end"] = "2026-05-31"
        report = build_mod.build(data)
        self.assertEqual(report["meta"]["period_noun"], "本月")
        html = render_mod.render(report)
        self.assertIn("本月总结", html)
        self.assertIn("本月最强搭档", html)
        self.assertIn("本月时间线", html)
        self.assertNotIn("本季总结", html)

    def test_build_computes_stats_and_fun_stats(self):
        result = build_mod.build(sample_input())
        self.assertEqual(result["meta"]["period_label"], "2026Q2")
        self.assertEqual(result["stats"]["agents_count"], 2)
        self.assertEqual(result["stats"]["sessions_total"], 13)
        self.assertEqual(result["stats"]["top_agent"], "Proma")
        fun = result["fun_stats"]
        self.assertEqual(fun["night_sessions"], 1)
        self.assertEqual(fun["weekend_sessions"], 2)
        self.assertEqual(fun["longest_streak_days"], 3)
        self.assertEqual(fun["busiest_month"], "2026-04")
        # timeline merged and sorted from milestones
        self.assertEqual(result["timeline"][0]["date"], "2026-05-11")

    def test_build_rejects_missing_fields_and_bad_values(self):
        with self.assertRaises(ValueError):
            build_mod.build({"period_start": "2026-04-01", "period_end": "2026-06-30"})
        with self.assertRaises(ValueError):
            build_mod.build({**sample_input(), "period_end": "2026-03-01"})
        with self.assertRaises(ValueError):
            build_mod.build({**sample_input(), "period_start": "not-a-date"})
        bad = sample_input()
        bad["agents"][0]["session_count"] = -1
        with self.assertRaises(ValueError):
            build_mod.build(bad)


class RenderReportTests(unittest.TestCase):
    def test_render_contains_sections_and_escapes_html(self):
        data = build_mod.build(sample_input())
        html_text = render_mod.render(data)
        for marker in ["我用 Agent", "隐藏战绩", "AI 干员图鉴", "成就墙", "本季时间线", "本季总结", "仅供个人回顾与分享娱乐"]:
            self.assertIn(marker, html_text)
        # narrative text must be escaped
        self.assertIn("&lt;b&gt;总结&lt;/b&gt;", html_text)
        self.assertNotIn("<b>总结</b>", html_text)
        self.assertIn("周报自动化", html_text)

    def test_render_badges_show_text_not_dict_repr(self):
        data = build_mod.build(sample_input())
        html_text = render_mod.render(data)
        self.assertIn("省时 90%", html_text)
        self.assertNotIn("{'text'", html_text)

    def test_roster_sorted_by_session_count_with_tiers(self):
        inp = sample_input()
        inp["agents"] = [
            {"name": "AgentA", "session_count": 100},
            {"name": "AgentB", "session_count": 50},
            {"name": "AgentC", "session_count": 10},
            {"name": "AgentD"},
        ]
        html_text = render_mod.render(build_mod.build(inp))
        # 按会话数降序，无会话数的排最后
        self.assertLess(html_text.find("会话 100 次"), html_text.find("会话 50 次"))
        self.assertLess(html_text.find("会话 50 次"), html_text.find("会话 10 次"))
        # 主力干将只有第 1 名；4 个干员：第 2 名为干员，其余为酱油仔
        self.assertEqual(html_text.count("主力干将"), 1)
        self.assertEqual(html_text.count("\u9171\u6cb9\u4ed4"), 2)

    def test_timeline_is_vertical_with_month_groups(self):
        data = build_mod.build(sample_input())
        html_text = render_mod.render(data)
        self.assertIn('class="timeline"', html_text)
        self.assertNotIn("fishbone", html_text)
        self.assertIn('class="mon">2026-05<', html_text)

    def test_render_omits_empty_sections(self):
        minimal = {
            "owner": "匿名",
            "period_start": "2026-04-15",
            "period_end": "2026-05-20",
            "agents": [],
            "projects": [],
        }
        data = build_mod.build(minimal)
        html_text = render_mod.render(data)
        self.assertNotIn("隐藏战绩", html_text)
        self.assertNotIn("AI 干员图鉴", html_text)
        self.assertNotIn("成就墙", html_text)
        self.assertIn("我用 Agent", html_text)


if __name__ == "__main__":
    unittest.main()
