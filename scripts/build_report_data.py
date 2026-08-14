#!/usr/bin/env python3
"""Aggregate raw discovery inputs into a normalized report_data.json.

This script is part of the agent-usage-report Skill ("我用 Agent 干了啥").
It performs ONLY deterministic computation and validation:

- validates the curated input assembled by the Agent (owner, period, agents,
  projects, narrative, optional session timestamps);
- derives the period label (e.g. 2026Q2 or 202604-202606);
- computes headline stats (agent count, project count, session total, top agent);
- computes fun stats from optional session timestamps (night owl / weekend
  warrior / busiest month / longest streak), purely from timestamps.

It never reads agent sessions or project content itself; the Agent supplies
the curated facts. It never scores, ranks against others, or makes any
evaluative judgment.

Usage:
    python3 build_report_data.py report_input.json -o report_data.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "1.0"
SKILL_NAME = "agent-usage-report"
SKILL_VERSION = "0.1.1"


# Icon mapping removed - using default emoji in render_report.py


def parse_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} 必须是 YYYY-MM-DD 格式的日期，收到: {value!r}")


def parse_timestamp(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        raise ValueError(f"session_timestamps 中的时间戳无法解析: {value!r}")


def period_label(start: date, end: date) -> str:
    """Derive YYYYQn when the range matches a calendar quarter, else YYYYMM-YYYYMM."""
    quarters = [(1, 3, "Q1"), (4, 6, "Q2"), (7, 9, "Q3"), (10, 12, "Q4")]
    if start.year == end.year:
        for first, last, tag in quarters:
            if (start.month, start.day) == (first, 1) and (end.month, end.day) == (last, _last_day(end.year, last)):
                return f"{start.year}{tag}"
    return f"{start.strftime('%Y%m')}-{end.strftime('%Y%m')}"


def _last_day(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - date(year, month, 1)).days


def period_noun(start: date, end: date) -> str:
    """Human noun for the reviewed range: 本月 / 本季 / 今年 / 这段时间.

    Used for section titles (e.g. 「本季总结」) so a monthly or yearly review
    never shows a hardcoded 「本季」.
    """
    if (
        start.year == end.year
        and start.month == end.month
        and start.day == 1
        and end.day == _last_day(end.year, end.month)
    ):
        return "本月"
    if period_label(start, end).endswith(("Q1", "Q2", "Q3", "Q4")):
        return "本季"
    if (start.month, start.day) == (1, 1) and (end.month, end.day) == (12, 31) and start.year == end.year:
        return "今年"
    return "这段时间"


def generate_agent_tags(agent: Dict[str, Any], all_timestamps: List[datetime]) -> List[str]:
    """Generate fun tags for an agent based on usage patterns (text only, no emoji)."""
    tags = []
    session_count = agent.get("session_count") or 0
    
    # Frequency-based tags
    if session_count > 200:
        tags.append("劳模")
    elif session_count >= 100:
        tags.append("常驻")
    elif session_count < 50 and session_count > 0:
        tags.append("偶尔串场")
    
    # Active days check for "一日游"
    if agent.get("first_seen") and agent.get("last_seen"):
        try:
            first = parse_date(agent["first_seen"], "first_seen")
            last = parse_date(agent["last_seen"], "last_seen")
            days = (last - first).days + 1
            if days <= 2:
                tags.append("一日游")
        except ValueError:
            pass
    
    # Time-based tags (only if agent has own session_timestamps)
    agent_timestamps = agent.get("session_timestamps") or []
    if agent_timestamps:
        night = sum(1 for ts in agent_timestamps if ts.hour >= 23 or ts.hour < 5)
        morning = sum(1 for ts in agent_timestamps if 5 <= ts.hour < 7)
        late_night = sum(1 for ts in agent_timestamps if 2 <= ts.hour < 5)
        total = len(agent_timestamps)
        
        if total > 0:
            if night / total > 0.3:
                tags.append("夜猫子搭档")
            if morning / total > 0.3:
                tags.append("晨间咖啡伴侣")
            if late_night > 0:
                tags.append("深夜救场王")
    
    # Project-based tags (based on note keywords)
    note = (agent.get("note") or "").lower()
    if any(kw in note for kw in ["修复", "debug", "fix", "bug"]):
        tags.append("修Bug专家")
    if any(kw in note for kw in ["readme", "文档", "documentation"]):
        tags.append("文档担当")
    if "连续" in note or "冲刺" in note:
        tags.append("冲刺助攻")
    
    return tags


def generate_project_badges(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate achievement badges for a project based on activity patterns (text only, no emoji)."""
    badges = []
    session_count = project.get("session_count") or 0
    active_days = project.get("active_days") or 0
    ai_tools = project.get("ai_tools") or []
    
    # Speed-based badges
    if active_days == 1:
        badges.append({"text": "速通成就", "level": "epic"})
    elif active_days <= 3:
        badges.append({"text": "疾跑模式", "level": "rare"})
    elif active_days > 30:
        badges.append({"text": "慢工出细活", "level": ""})
    
    # Intensity-based badges
    if session_count > 0 and active_days > 0:
        density = session_count / active_days
        if density > 20:
            badges.append({"text": "火力全开", "level": "epic"})
        elif active_days >= 7 and density >= 1:
            badges.append({"text": "持久战", "level": "rare"})
        elif session_count < 20 and active_days <= 3:
            badges.append({"text": "狙击手", "level": ""})
    
    # Feature-based badges
    if len(ai_tools) >= 3:
        badges.append({"text": "AI接力赛", "level": "epic"})
    
    # Note-based badges
    note = (project.get("note") or "").lower()
    one_liner = (project.get("one_liner") or "").lower()
    combined = note + " " + one_liner
    
    if any(kw in combined for kw in ["文档", "knowledge", "笔记", "整理"]):
        if session_count >= 10:
            badges.append({"text": "知识积累", "level": ""})
    
    if any(kw in combined for kw in ["图片", "ppt", "报告", "可视化", "生图"]):
        badges.append({"text": "视觉产出", "level": ""})
    
    return badges


def compute_fun_stats(timestamps: List[datetime]) -> Dict[str, Any]:
    stats: Dict[str, Any] = {
        "session_count": len(timestamps),
        "night_sessions": 0,
        "early_sessions": 0,
        "weekend_sessions": 0,
        "busiest_month": None,
        "longest_streak_days": 0,
        "earliest": None,
        "latest": None,
        "monthly_rhythm": {},
    }
    if not timestamps:
        return stats

    month_counts: Dict[str, int] = {}
    days: set = set()
    for ts in timestamps:
        if ts.hour >= 23 or ts.hour < 5:
            stats["night_sessions"] += 1
        if 5 <= ts.hour < 7:
            stats["early_sessions"] += 1
        if ts.weekday() >= 5:
            stats["weekend_sessions"] += 1
        month_key = ts.strftime("%Y-%m")
        month_counts[month_key] = month_counts.get(month_key, 0) + 1
        days.add(ts.date())

    stats["busiest_month"] = max(month_counts.items(), key=lambda kv: kv[1])[0]
    stats["earliest"] = min(timestamps).isoformat()
    stats["latest"] = max(timestamps).isoformat()
    
    # monthly_rhythm: 每月会话分布
    stats["monthly_rhythm"] = dict(sorted(month_counts.items()))

    streak = best = 0
    prev: Optional[date] = None
    for day in sorted(days):
        streak = streak + 1 if prev is not None and (day - prev).days == 1 else 1
        best = max(best, streak)
        prev = day
    stats["longest_streak_days"] = best
    return stats


# AI 腔禁用词（写作指南第三章的确定性兜底）
# 命中不阻断构建，但会在输出里带 style_warnings，终端也会警告——
# 文案风格的最后一道不靠模型自觉的关卡。
AI_TONE_PHRASES = [
    "协助", "赋能", "闭环", "抓手", "打磨", "落地", "深度协作", "多轮迭代",
    "成功完成", "圆满", "卓越", "收获满满", "期待下", "充分", "显著提升",
    "有效提升", "全面推进", "稳步推进", "高质量", "取得了", "实现了",
]


def check_writing_style(data: Dict[str, Any]) -> List[str]:
    """Scan narrative + agent notes for AI-tone phrases. Returns warnings."""
    texts: List[tuple[str, str]] = []
    narrative = data.get("narrative") or {}
    if narrative.get("headline"):
        texts.append(("narrative.headline", str(narrative["headline"])))
    for i, p in enumerate(narrative.get("paragraphs") or []):
        texts.append((f"narrative.paragraphs[{i}]", str(p)))
    for agent in data.get("agents") or []:
        note = (agent or {}).get("note")
        if note:
            texts.append((f"agents[{agent.get('name', '?')}].note", str(note)))

    warnings: List[str] = []
    for location, text in texts:
        hits = [phrase for phrase in AI_TONE_PHRASES if phrase in text]
        if hits:
            warnings.append(f"{location} 含 AI 腔用词: {'、'.join(hits)}")
    return warnings


def build(data: Dict[str, Any]) -> Dict[str, Any]:
    missing = [k for k in ("owner", "period_start", "period_end") if not data.get(k)]
    if missing:
        raise ValueError(f"缺少必填字段: {', '.join(missing)}")

    start = parse_date(data["period_start"], "period_start")
    end = parse_date(data["period_end"], "period_end")
    if end < start:
        raise ValueError("period_end 不能早于 period_start")

    agents = data.get("agents") or []
    if not isinstance(agents, list):
        raise ValueError("agents 必须是数组")
    normalized_agents = []
    for row in agents:
        name = (row or {}).get("name")
        if not name:
            raise ValueError("agents 中每一项都必须有 name")
        session_count = row.get("session_count")
        if session_count is not None and (not isinstance(session_count, int) or session_count < 0):
            raise ValueError(f"agent {name} 的 session_count 必须是非负整数")
        agent_data = {
            "name": str(name),
            "emoji": row.get("emoji"),
            "session_count": session_count,
            "first_seen": row.get("first_seen"),
            "last_seen": row.get("last_seen"),
            "note": row.get("note"),
            "_raw": row,  # Keep raw data for tag generation later
        }
        normalized_agents.append(agent_data)

    projects = data.get("projects") or []
    if not isinstance(projects, list):
        raise ValueError("projects 必须是数组")
    normalized_projects = []
    for row in projects:
        name = (row or {}).get("name")
        if not name:
            raise ValueError("projects 中每一项都必须有 name")
        milestones = row.get("milestones") or []
        for m in milestones:
            parse_date(m["date"], f"project {name} 的 milestone.date")
        session_count = row.get("session_count")
        if session_count is not None and (not isinstance(session_count, int) or session_count < 0):
            raise ValueError(f"project {name} 的 session_count 必须是非负整数")
        active_days = row.get("active_days")
        if active_days is not None and (not isinstance(active_days, int) or active_days <= 0):
            raise ValueError(f"project {name} 的 active_days 必须是正整数")
        
        # Merge existing badges with auto-generated badges
        existing_badges = [
            {"text": str(b.get("text", "")) if isinstance(b, dict) else str(b),
             "level": (b.get("level") if isinstance(b, dict) else None)}
            for b in (row.get("badges") or [])
        ]
        auto_badges = generate_project_badges(row)
        
        normalized_projects.append({
            "name": str(name),
            "one_liner": row.get("one_liner"),
            "ai_tools": list(row.get("ai_tools") or []),
            "activity": row.get("activity"),
            "session_count": session_count,
            "active_days": active_days,
            "milestones": [
                {"date": m["date"], "text": str(m.get("text", ""))} for m in milestones
            ],
            "badges": existing_badges + auto_badges,
        })

    narrative = data.get("narrative") or {}
    paragraphs = narrative.get("paragraphs") or []

    timestamps = []
    for raw in data.get("session_timestamps") or []:
        timestamps.append(parse_timestamp(str(raw)))

    # Generate tags for agents now that timestamps are available
    for agent_data in normalized_agents:
        agent_data["tags"] = generate_agent_tags(agent_data["_raw"], timestamps)
        del agent_data["_raw"]  # Remove temporary raw data

    sessions_total = sum(a["session_count"] or 0 for a in normalized_agents)
    top_agent = None
    if any(a["session_count"] for a in normalized_agents):
        top_agent = max(
            (a for a in normalized_agents if a["session_count"]),
            key=lambda a: a["session_count"],
        )["name"]

    timeline = []
    for proj in normalized_projects:
        for m in proj["milestones"]:
            timeline.append({"date": m["date"], "project": proj["name"], "text": m["text"]})
    timeline.sort(key=lambda t: t["date"])

    fun = compute_fun_stats(timestamps)

    # 计算新增统计字段
    # project_density: 单项目密度（会话数/活跃天数）
    project_density = None
    if normalized_projects:
        densities = []
        for p in normalized_projects:
            if p.get("session_count") and p.get("active_days"):
                densities.append({
                    "project": p["name"],
                    "density": round(p["session_count"] / p["active_days"], 1),
                    "sessions": p["session_count"],
                    "days": p["active_days"],
                })
        if densities:
            project_density = max(densities, key=lambda d: d["density"])

    # agent_combo: 多Agent接力（项目使用了多个Agent）
    agent_combo = []
    for p in normalized_projects:
        if len(p.get("ai_tools") or []) >= 2:
            agent_combo.append({
                "project": p["name"],
                "agents": p["ai_tools"],
                "count": len(p["ai_tools"]),
            })
    agent_combo.sort(key=lambda x: x["count"], reverse=True)

    # top_dedication: Agent在单项目的占比
    top_dedication = None
    if normalized_agents and normalized_projects:
        dedications = []
        for agent in normalized_agents:
            if not agent.get("session_count"):
                continue
            for proj in normalized_projects:
                if agent["name"] in (proj.get("ai_tools") or []) and proj.get("session_count"):
                    ratio = round(proj["session_count"] / agent["session_count"] * 100, 1)
                    dedications.append({
                        "agent": agent["name"],
                        "project": proj["name"],
                        "ratio": ratio,
                        "project_sessions": proj["session_count"],
                        "agent_sessions": agent["session_count"],
                    })
        if dedications:
            top_dedication = max(dedications, key=lambda d: d["ratio"])

    result = {
        "schema_version": SCHEMA_VERSION,
        "meta": {
            "skill": SKILL_NAME,
            "skill_version": SKILL_VERSION,
            "owner": str(data["owner"]),
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "period_label": period_label(start, end),
            "period_noun": period_noun(start, end),
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            
        },
        "stats": {
            "agents_count": len(normalized_agents),
            "projects_count": len(normalized_projects),
            "sessions_total": sessions_total,
            "top_agent": top_agent,
            "project_density": project_density,
            "agent_combo": agent_combo,
            "top_dedication": top_dedication,
        },
        "fun_stats": fun,
        "agents": normalized_agents,
        "projects": normalized_projects,
        "timeline": timeline,
        "narrative": {
            "headline": narrative.get("headline"),
            "paragraphs": [str(p) for p in paragraphs],
        },
    }

    style_warnings = check_writing_style(data)
    if style_warnings:
        result["style_warnings"] = style_warnings
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate curated discovery data into report_data.json.")
    parser.add_argument("input", type=Path, help="report_input.json assembled by the Agent.")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output report_data.json path.")
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    result = build(data)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: wrote {args.output} (agents={result['stats']['agents_count']}, projects={result['stats']['projects_count']})")
    for warning in result.get("style_warnings") or []:
        print(f"⚠ 风格警告：{warning}", file=sys.stderr)
    if result.get("style_warnings"):
        print(
            "⚠ narrative/评语命中 AI 腔用词，请按 narrative-writing-guide.md 重写后再跑一遍本脚本。",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
