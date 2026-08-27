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
        "owner": "\u5c0f\u6731",
        "period_start": "2026-04-01",
        "period_end": "2026-06-30",
        "agents": [
            {"name": "Proma", "session_count": 10, "first_seen": "2026-04-02", "last_seen": "2026-06-29"},
            {"name": "Cursor", "session_count": 3},
        ],
        "projects": [
            {
                "name": "\u5468\u62a5\u81ea\u52a8\u5316",
                "one_liner": "\u628a\u6bcf\u5468\u6c47\u603b\u4ece 2 \u5c0f\u65f6\u538b\u5230 10 \u5206\u949f\u3002",
                "ai_tools": ["Proma"],
                "badges": [{"text": "\u7701\u65f6 90%"}],
                "milestones": [{"date": "2026-05-11", "text": "\u7b2c\u4e00\u7248\u4e0a\u7ebf"}],
            }
        ],
        "narrative": {"headline": "\u8f7b\u677e\u56de\u987e", "paragraphs": ["\u4e00\u6bb5 <b>\u603b\u7ed3</b>\u3002"]},
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
            sample_value = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
            (root / "config.txt").write_text(f"api_key={sample_value}\n", encoding="utf-8")
            result = secret_mod.scan(root)
            serialized = json.dumps(result)
            self.assertGreater(result["finding_count"], 0)
            self.assertNotIn(sample_value, serialized)
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

    def test_style_warnings_flag_ai_tone(self):
        data = sample_input()
        data["narrative"] = {
            "headline": "\u643a\u624b\u5171\u8fdb",
            "paragraphs": ["\u5728 Proma \u7684\u534f\u52a9\u4e0b\uff0c\u6211\u6210\u529f\u5b8c\u6210\u4e86\u5de5\u5177\u5f00\u53d1\uff0c\u5b9e\u73b0\u4e86\u5b8c\u6574\u95ed\u73af\u3002"],
        }
        data["agents"][0]["note"] = "Proma \u5728\u672c\u5b63\u5ea6\u4e3a\u7528\u6237\u63d0\u4f9b\u4e86\u6df1\u5ea6\u534f\u4f5c\u652f\u6301\u3002"
        result = build_mod.build(data)
        warnings = result.get("style_warnings") or []
        self.assertTrue(warnings, "AI-tone copy must be flagged")
        joined = "\n".join(warnings)
        self.assertIn("\u534f\u52a9", joined)
        self.assertIn("\u95ed\u73af", joined)

    def test_style_warnings_clean_for_human_tone(self):
        result = build_mod.build(sample_input())
        self.assertIsNone(result.get("style_warnings"))

    def test_period_noun_matches_review_range(self):
        self.assertEqual(build_mod.period_noun(date(2026, 4, 1), date(2026, 6, 30)), "\u672c\u5b63")
        self.assertEqual(build_mod.period_noun(date(2026, 5, 1), date(2026, 5, 31)), "\u672c\u6708")
        self.assertEqual(build_mod.period_noun(date(2026, 1, 1), date(2026, 12, 31)), "\u4eca\u5e74")
        self.assertEqual(build_mod.period_noun(date(2026, 4, 15), date(2026, 6, 30)), "\u8fd9\u6bb5\u65f6\u95f4")
        self.assertEqual(build_mod.period_noun(date(2025, 1, 1), date(2026, 6, 30)), "\u8fd9\u6bb5\u65f6\u95f4")

    def test_render_uses_period_noun_not_hardcoded_quarter(self):
        data = sample_input()
        data["period_start"] = "2026-05-01"
        data["period_end"] = "2026-05-31"
        report = build_mod.build(data)
        self.assertEqual(report["meta"]["period_noun"], "\u672c\u6708")
        html = render_mod.render(report)
        self.assertIn("\u672c\u6708\u603b\u7ed3", html)
        self.assertIn("\u672c\u6708\u6700\u5f3a\u642d\u6863", html)
        self.assertIn("\u672c\u6708\u65f6\u95f4\u7ebf", html)
        self.assertNotIn("\u672c\u5b63\u603b\u7ed3", html)

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
        for marker in ["\u6211\u7528 Agent", "\u9690\u85cf\u6218\u7ee9", "AI \u5e72\u5458\u56fe\u9274", "\u6210\u5c31\u5899", "\u672c\u5b63\u65f6\u95f4\u7ebf", "\u672c\u5b63\u603b\u7ed3", "\u4ec5\u4f9b\u4e2a\u4eba\u56de\u987e\u4e0e\u5206\u4eab\u5a31\u4e50"]:
            self.assertIn(marker, html_text)
        # narrative text must be escaped
        self.assertIn("&lt;b&gt;\u603b\u7ed3&lt;/b&gt;", html_text)
        self.assertNotIn("<b>\u603b\u7ed3</b>", html_text)
        self.assertIn("\u5468\u62a5\u81ea\u52a8\u5316", html_text)

    def test_skill_version_follows_skill_md_frontmatter(self):
        head = (ROOT / "SKILL.md").read_text(encoding="utf-8").splitlines()[:20]
        expected = next(
            line.split(":", 1)[1].strip().strip('"')
            for line in head if line.strip().startswith("version:")
        )
        self.assertEqual(build_mod.skill_version(), expected)
        result = build_mod.build(sample_input())
        self.assertEqual(result["meta"]["skill_version"], expected)
        self.assertNotEqual(expected, "0.1.1")

    def test_fun_stats_compute_record_fields(self):
        result = build_mod.build(sample_input())
        fun = result["fun_stats"]
        self.assertEqual(fun["busiest_day"], "2026-04-12")
        self.assertEqual(fun["busiest_day_count"], 1)
        self.assertEqual(fun["favorite_hour_count"], 1)
        self.assertEqual(fun["active_months"], 1)
        self.assertEqual(fun["period_months"], 3)
        self.assertEqual(fun["latest_clock"], "23:40")
        self.assertEqual(fun["earliest_clock"], "09:10")
        self.assertEqual(fun["longest_gap_days"], 3)  # 4/15-4/17 \u65e0\u4f1a\u8bdd

    def test_fun_tags_loose_thresholds_and_records(self):
        html = render_mod.render(build_mod.build(sample_input()))
        # \u8bb0\u5f55\u7c7b\u65e0\u9608\u503c\uff1a\u76f4\u63a5\u5448\u73b0
        self.assertIn("\u706b\u529b\u5168\u5f00\u6708\uff1a2026-04", html)
        self.assertIn("\u6700\u665a\u6536\u5de5 23:40", html)
        # \u5bbd\u677e\u9608\u503c\u8fbe\u6807
        self.assertIn("\u5468\u672b\u52a0\u73ed\uff08\u81ea\u613f\u7684\uff09\u00d72", html)
        self.assertIn("\u8fde\u7eed\u5e76\u80a9 3 \u5929", html)
        # \u672a\u8fbe\u9608\u503c\uff1a\u4e0d\u5448\u73b0
        self.assertNotIn("\u591c\u732b\u5b50", html)      # \u4ec5 1 \u6b21 < \u9608\u503c 2
        self.assertNotIn("\u5355\u65e5\u7206\u53d1", html)    # \u5cf0\u503c 1 \u6b21 < \u9608\u503c 3
        self.assertNotIn("\u795e\u9690", html)        # \u95f4\u9694 3 \u5929 < \u9608\u503c 7
        self.assertNotIn("\u6700\u65e9\u5f00\u5de5", html)    # 09:10 \u4e0d\u591f\u65e9
        self.assertNotIn("\u6708\u5ea6\u5168\u52e4", html)    # \u53ea\u6709 1 \u4e2a\u6708\u6709\u4f1a\u8bdd
        self.assertNotIn("\u56fa\u5b9a\u642d\u5b50", html)

    def test_fun_tags_all_present_when_data_rich(self):
        report = build_mod.build(sample_input())
        report["fun_stats"].update({
            "session_count": 100,
            "night_sessions": 5,
            "early_sessions": 3,
            "busiest_day": "2026-05-22",
            "busiest_day_count": 12,
            "favorite_hour": 21,
            "favorite_hour_count": 30,
            "active_months": 3,
            "period_months": 3,
            "earliest_clock": "06:12",
            "longest_gap_days": 9,
        })
        html = render_mod.render(report)
        for tag in ("\u591c\u732b\u5b50\u65f6\u523b \u00d75", "\u65e9\u8d77\u9e1f \u00d73", "\u5355\u65e5\u7206\u53d1\uff1a05/22 \u00d712", "\u6708\u5ea6\u5168\u52e4 \u00d73",
                    "\u56fa\u5b9a\u642d\u5b50\uff1a21 \u70b9\u6863 \u00d730", "\u6700\u65e9\u5f00\u5de5 06:12", "\u795e\u9690 9 \u5929"):
            self.assertIn(tag, html)

    def test_render_contains_share_button_and_meta(self):
        report = build_mod.build(sample_input())
        html = render_mod.render(report)
        self.assertIn('id="shareBtn"', html)
        self.assertIn('id="shareText"', html)
        self.assertIn('id="shareFile"', html)
        # share metadata is embedded with real stats
        self.assertIn('"sessions": 13', html)
        self.assertIn('"top": "Proma"', html)
        # local-only: no network endpoint in the share script
        self.assertNotIn("fetch(", html)
        self.assertNotIn("XMLHttpRequest", html)

    def test_share_inline_script_has_no_raw_newline(self):
        # \u5185\u8054 JS \u91cc\u82e5\u6df7\u5165\u539f\u59cb\u6362\u884c\uff08\u5982 Python \n \u6cc4\u8fdb JS \u5b57\u7b26\u4e32\uff09\u4f1a\u76f4\u63a5\u8bed\u6cd5\u9519\u8bef\uff0c
        # \u6574\u4e2a share \u811a\u672c\u5757\u5931\u6548\u3001SHARE \u6309\u94ae\u5b8c\u5168\u65e0\u54cd\u5e94
        html_text = render_mod.render(build_mod.build(sample_input()))
        script = html_text.split("<script>")[1].split("</script>")[0]
        self.assertNotIn("\n", script)

    def test_render_badges_show_text_not_dict_repr(self):
        data = build_mod.build(sample_input())
        html_text = render_mod.render(data)
        self.assertIn("\u7701\u65f6 90%", html_text)
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
        # \u6309\u4f1a\u8bdd\u6570\u964d\u5e8f\uff0c\u65e0\u4f1a\u8bdd\u6570\u7684\u6392\u6700\u540e
        self.assertLess(html_text.find("\u4f1a\u8bdd 100 \u6b21"), html_text.find("\u4f1a\u8bdd 50 \u6b21"))
        self.assertLess(html_text.find("\u4f1a\u8bdd 50 \u6b21"), html_text.find("\u4f1a\u8bdd 10 \u6b21"))
        # \u4e3b\u529b\u5e72\u5c06\u53ea\u6709\u7b2c 1 \u540d\uff1b4 \u4e2a\u5e72\u5458\uff1a\u7b2c 2 \u540d\u4e3a\u5e72\u5458\uff0c\u5176\u4f59\u4e3a\u9171\u6cb9\u4ed4
        self.assertEqual(html_text.count("\u4e3b\u529b\u5e72\u5c06"), 1)
        self.assertEqual(html_text.count("\u9171\u6cb9\u4ed4"), 2)

    def test_timeline_is_vertical_with_month_groups(self):
        data = build_mod.build(sample_input())
        html_text = render_mod.render(data)
        self.assertIn('class="timeline"', html_text)
        self.assertNotIn("fishbone", html_text)
        self.assertIn('class="mon">2026-05<', html_text)

    def test_timeline_falls_back_to_monthly_session_counts(self):
        # \u6ca1\u586b milestones \u65f6\uff0c\u7528\u771f\u5b9e\u4f1a\u8bdd\u65f6\u95f4\u6233\u6309\u6708\u8ba1\u6570\uff0c\u65f6\u95f4\u7ebf\u4e0d\u5e94\u6574\u5757\u6d88\u5931
        inp = sample_input()
        for p in inp["projects"]:
            p.pop("milestones", None)
        data = build_mod.build(inp)
        self.assertTrue(data["timeline"])
        self.assertTrue(all(t["project"] == "" for t in data["timeline"]))
        html_text = render_mod.render(data)
        self.assertIn('class="timeline"', html_text)
        self.assertIn("\u5e76\u80a9\u4f5c\u6218", html_text)

    def test_share_text_fallback_night_variant(self):
        # sample_input \u7684 4 \u6761\u65f6\u95f4\u6233\u542b 1 \u6b21\u6df1\u591c\uff081/4 > 0.2\uff09\u2192 \u6df1\u591c\u578b\u9aa8\u67b6
        data = build_mod.build(sample_input())
        text = data["share_text"]
        self.assertIn("\u534a\u591c", text)
        self.assertIn("\u66ff\u6211\u5377", text)
        self.assertIn("\u6700\u957f\u8fde\u7eed 3 \u5929\u6ca1\u65ad\u8fc7", text)
        html_text = render_mod.render(data)
        self.assertIn(text, html_text)

    def test_share_text_fallback_sprint_variant(self):
        inp = sample_input()
        inp["session_timestamps"] = [
            f"2026-04-{day:02d}T10:00:00" for day in range(1, 16)
        ]  # \u8fde\u7eed 15 \u5929 \u2192 \u51b2\u523a\u578b
        data = build_mod.build(inp)
        self.assertIn("\u5e72\u4e86\u7968\u5927\u7684", data["share_text"])

    def test_share_text_fallback_daily_variant(self):
        inp = sample_input()
        inp["session_timestamps"] = ["2026-04-10T14:00:00", "2026-05-20T16:00:00"]
        data = build_mod.build(inp)
        self.assertIn("\u7a33\u5b9a\u8f93\u51fa", data["share_text"])

    def test_share_text_agent_written_passes_through(self):
        inp = sample_input()
        custom = "\u8fd9\u5b63\u5ea6\u8ddf AI \u6df7\u719f\u4e86\uff0c374 \u6b21\u4f1a\u8bdd\u91cc\u6709\u4e00\u534a\u662f\u534a\u591c\u804a\u7684\uff0c\u503c\u4e86\u3002"
        inp["narrative"]["share_text"] = custom
        data = build_mod.build(inp)
        self.assertEqual(data["share_text"], custom)
        self.assertIn(custom, render_mod.render(data))

    def test_share_text_too_long_and_ai_tone_warn(self):
        inp = sample_input()
        inp["narrative"]["share_text"] = "\u8d4b\u80fd" * 100  # 200 \u5b57 + AI \u8154
        data = build_mod.build(inp)
        warnings = "\n".join(data.get("style_warnings") or [])
        self.assertIn("share_text", warnings)
        self.assertIn("\u8d4b\u80fd", warnings)

    def test_render_omits_empty_sections(self):
        minimal = {
            "owner": "\u533f\u540d",
            "period_start": "2026-04-15",
            "period_end": "2026-05-20",
            "agents": [],
            "projects": [],
        }
        data = build_mod.build(minimal)
        html_text = render_mod.render(data)
        self.assertNotIn("\u9690\u85cf\u6218\u7ee9", html_text)
        self.assertNotIn("AI \u5e72\u5458\u56fe\u9274", html_text)
        self.assertNotIn("\u6210\u5c31\u5899", html_text)
        self.assertIn("\u6211\u7528 Agent", html_text)


if __name__ == "__main__":
    unittest.main()
