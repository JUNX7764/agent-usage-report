#!/usr/bin/env python3
"""Render report_data.json into a single-file HTML report with Swiss International style.

This script is part of the agent-usage-report Skill ("我用 Agent 干了啥").
It is a pure, deterministic template renderer: same JSON in, same HTML out.
The HTML is self-contained (no external assets) so it can be opened offline
and shared as one file.

Usage:
    python3 render_report.py report_data.json -o index.html
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Default emoji mapping (extracted from 19:08 HTML)
DEFAULT_EMOJI = {
    "Proma": "⚡",
    "Claude Code": "🤖",
    "Codex": "🧬",
    "Hermes": "🪽",
    "Antigravity": "🤖",
    "DscAiWork": "🤖",
    "Qoder": "🧩",
    "WorkBuddy": "🐧",
    "Gemini CLI": "♊",
    "LM Studio": "🤖",
    "Cursor": "🖱️",
    "Windsurf": "🛸",
    "Aider": "🧰",
    "Cline": "📮",
    "Copilot": "✨",
}


def get_css() -> str:
    """Generate CSS matching the 19:08 perfect version.
    
    Returns complete CSS extracted from reference HTML with:
    - Background: #f4f4f0 + radial-gradient grid pattern
    - Colors: blue #002fa7, yellow #e8ff3d, orange #ff5a1f
    - Fishbone timeline with spine + bones
    - All original styling preserved
    """
    return """*{margin:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{background:#f4f4f0;color:#111;font-family:"Helvetica Neue","PingFang SC","Microsoft YaHei",Arial,sans-serif;padding:56px clamp(24px,6vw,80px) 80px;background-image:radial-gradient(#c9c9c2 1px,transparent 1px);background-size:22px 22px}
.kicker{font-size:12px;letter-spacing:.32em;font-weight:700;color:#002fa7;text-transform:uppercase}
h1{font-size:clamp(40px,7vw,72px);font-weight:800;line-height:1.05;margin:16px 0 10px;letter-spacing:-.02em}
h1 mark{background:#e8ff3d;padding:0 .12em;box-shadow:4px 4px 0 #111}
.sub{font-size:14px;color:#555;margin-bottom:8px}
.section{margin-top:64px}
.sec-head{display:flex;align-items:baseline;gap:14px;border-top:3px solid #111;padding-top:12px;margin-bottom:22px}
.sec-head .no{font-size:12px;font-weight:800;color:#fff;background:#111;padding:3px 8px}
.sec-head h2{font-size:24px;font-weight:800;letter-spacing:.02em}
.sec-head .hint{margin-left:auto;font-size:12px;color:#888;letter-spacing:.08em}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-top:34px}
.stat{background:#fff;border:2px solid #111;padding:20px;box-shadow:6px 6px 0 rgba(17,17,17,.9);transition:transform .15s}
.stat:hover{transform:translate(-2px,-2px)}
.stat b{font-size:52px;font-weight:800;display:block;line-height:1}
.stat span{font-size:12px;color:#666;letter-spacing:.06em;display:block;margin-top:10px}
.stat.a b{color:#002fa7}
.stat.b{background:#e8ff3d}
.stat.c b{color:#ff5a1f}
.stat.text b{font-size:34px;line-height:1.15}
.funs{display:flex;flex-wrap:wrap;gap:12px}
.fun{display:flex;align-items:center;gap:10px;background:#fff;border:2px solid #111;padding:10px 16px;font-size:13.5px;font-weight:700}
.fun .em{font-size:20px}
.fun small{color:#777;font-weight:400}
.fun.hot{background:#ff5a1f;color:#fff}
.fun.hot small{color:#ffe3d6}
.fun.cool{background:#002fa7;color:#fff}
.fun.cool small{color:#cdd6ff}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px}
.card{background:#fff;border:2px solid #111;padding:22px;box-shadow:6px 6px 0 rgba(17,17,17,.9)}
.card .tag{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.12em;padding:4px 9px;color:#fff;background:#002fa7}
.card .tag.alt{background:#111}
.card .tag.hot{background:#ff5a1f}
.card h3{font-size:22px;margin:14px 0 8px;font-weight:800;display:flex;align-items:center;gap:10px}
.card h3 .em{font-size:26px}
.card p{font-size:13.5px;line-height:1.75;color:#444}
.meta-line{font-size:12px;color:#777;margin-top:8px;letter-spacing:.03em}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.chip{font-size:11px;font-weight:700;border:1.5px solid #111;padding:3px 8px;background:#f4f4f0}
.badge{display:inline-flex;align-items:center;gap:6px;margin-top:14px;border:2px solid #111;background:#e8ff3d;font-weight:800;font-size:12.5px;padding:7px 12px;letter-spacing:.04em}
.badge.rare{background:#ff5a1f;color:#fff}
.badge.epic{background:#002fa7;color:#fff}
.mile{margin-top:14px;border-top:2px solid #111}
.mile div{display:flex;gap:12px;align-items:baseline;font-size:12.5px;padding:7px 0;border-bottom:1px solid #ddd}
.mile b{font-weight:800;min-width:52px}
.mile span{color:#555}
.timeline{border-left:3px solid #111;margin-left:6px;padding-left:26px}
.timeline .t{position:relative;padding:10px 0}
.timeline .t:before{content:"";position:absolute;left:-33px;top:16px;width:12px;height:12px;background:#e8ff3d;border:2px solid #111}
.timeline .t:nth-child(3n+2):before{background:#002fa7}
.timeline .t:nth-child(3n):before{background:#ff5a1f}
.timeline .d{font-size:12px;font-weight:800;letter-spacing:.06em}
.timeline .p{font-size:11px;color:#888;margin-left:8px}
.timeline .x{font-size:14.5px;margin-top:2px;color:#222}
.timeline .mon{margin:20px 0 2px;font-size:13px;font-weight:900;letter-spacing:.12em;color:#002fa7}
.timeline .mon:first-child{margin-top:2px}
.story{background:#111;color:#f4f4f0;padding:36px 40px;box-shadow:8px 8px 0 #e8ff3d}
.story h3{font-size:28px;font-weight:800;margin-bottom:16px}
.story h3 mark{background:#e8ff3d;color:#111;padding:0 .15em}
.story p{font-size:15px;line-height:2;color:#d9d9d2;max-width:70ch}
.story p + p{margin-top:12px}
footer{margin-top:80px;border-top:2px solid #111;padding-top:18px;font-size:12px;color:#777;line-height:1.9}
footer b{color:#111}
.share-btn{position:fixed;top:18px;right:18px;z-index:99;background:#fff;border:2px solid #111;box-shadow:4px 4px 0 #111;font-family:inherit;font-size:12px;font-weight:800;letter-spacing:.18em;padding:10px 16px;cursor:pointer;transition:transform .12s}
.share-btn:hover{background:#002fa7;color:#fff;transform:translate(-2px,-2px)}
.share-pop{position:fixed;top:64px;right:18px;z-index:99;width:280px;background:#fff;border:2px solid #111;box-shadow:6px 6px 0 rgba(17,17,17,.9);display:none}
.share-pop.open{display:block}
.share-pop .opt{display:block;width:100%;text-align:left;border:0;border-bottom:1.5px solid #111;background:#fff;padding:13px 16px;font-family:inherit;font-size:13px;font-weight:700;cursor:pointer}
.share-pop .opt:hover{background:#e8ff3d}
.share-pop .opt small{display:block;font-weight:400;color:#777;margin-top:3px;font-size:11.5px}
.share-pop .note{padding:10px 16px;font-size:11px;color:#888;letter-spacing:.03em}
.share-toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#111;color:#e8ff3d;font-size:12.5px;font-weight:700;letter-spacing:.06em;padding:10px 18px;display:none;z-index:99}
.share-toast.show{display:block}
@media (max-width:720px){.story{padding:26px}.stat b{font-size:40px}.share-btn{top:12px;right:12px;padding:8px 12px}.share-pop{right:12px;left:12px;width:auto}}
"""


def esc(value: Any) -> str:
    """HTML-escape a value."""
    return html.escape(str(value if value is not None else ""), quote=True)


def agent_emoji(name: str, custom: Optional[str]) -> str:
    """Get emoji for an agent, using custom if provided, else default mapping."""
    if custom:
        return custom
    return DEFAULT_EMOJI.get(name, "◆")


def render(data: Dict[str, Any]) -> str:
    """Render report HTML matching the 19:08 perfect version.
    
    Args:
        data: Report data from build_report_data.py
        
    Returns:
        Complete HTML string
    """
    meta = data["meta"]
    stats = data["stats"]
    fun = data.get("fun_stats") or {}
    agents: List[Dict[str, Any]] = data.get("agents") or []
    projects: List[Dict[str, Any]] = data.get("projects") or []
    timeline: List[Dict[str, Any]] = data.get("timeline") or []
    narrative = data.get("narrative") or {}
    noun = str(meta.get("period_noun") or "本季")

    parts: List[str] = []
    parts.append("<!DOCTYPE html>\n<html lang=\"zh\"><head><meta charset=\"utf-8\">")
    parts.append("<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">")
    parts.append(f"<title>{esc(meta['owner'])} 的 Agent 战绩 · {esc(meta['period_label'])}</title>")
    parts.append(f"<style>{get_css()}</style></head><body>")

    # ---- header ----
    parts.append(f"<div class=\"kicker\">AGENT REPORT — {esc(meta['period_label'])}</div>")
    parts.append("<h1>我用 Agent <mark>干了啥</mark></h1>")
    parts.append(
        f"<div class=\"sub\">{esc(meta['owner'])} · {esc(meta['period_start'])} – {esc(meta['period_end'])} · 由 AI 回顾本机记录整理生成</div>"
    )

    # ---- big stats ----
    stat_cards = [
        ("a", esc(stats.get("agents_count", 0)), "召唤的 AI 干员"),
        ("b", esc(stats.get("sessions_total", 0) or "–"), "会话记录"),
        ("", esc(stats.get("projects_count", 0)), "参与的项目"),
    ]
    if stats.get("top_agent"):
        stat_cards.append(("text c", f"{agent_emoji(stats['top_agent'], None)} {esc(stats['top_agent'])}", f"{esc(noun)}最强搭档"))
    parts.append("<div class=\"stats\">")
    for cls, num, label in stat_cards:
        parts.append(f"<div class=\"stat {cls}\"><b>{num}</b><span>{label}</span></div>")
    parts.append("</div>")

    # ---- hidden achievements (fun stats) ----
    # 两类 tag：计数类用宽松阈值（偶尔一次不算战绩）；记录类无阈值，是个人纪录就亮。
    TH_NIGHT = 2        # 夜猫子：深夜会话 ≥2 次（一次是偶然，两次是习惯）
    TH_EARLY = 2        # 早起鸟：清晨会话 ≥2 次
    TH_WEEKEND = 1      # 周末加班：有就亮
    TH_STREAK = 2       # 连续并肩：≥2 天（1 天不叫连续）
    TH_BUSY_DAY = 3     # 单日爆发：单日 ≥3 次才不寒酸
    TH_GAP = 7          # 神隐：≥7 天没会话才值得说
    fun_items = []
    if fun.get("session_count"):
        if fun.get("night_sessions", 0) >= TH_NIGHT:
            fun_items.append(("hot", "🌙", f"夜猫子时刻 ×{fun['night_sessions']}", "23:00 后仍在和 Agent 并肩"))
        if fun.get("weekend_sessions", 0) >= TH_WEEKEND:
            fun_items.append(("cool", "🏖️", f"周末加班（自愿的）×{fun['weekend_sessions']}", "周六日也有会话记录"))
        if fun.get("early_sessions", 0) >= TH_EARLY:
            fun_items.append(("", "🌅", f"早起鸟 ×{fun['early_sessions']}", "早上 7 点前就开工"))
        # 记录类：无阈值
        if fun.get("busiest_month"):
            fun_items.append(("", "🔥", f"火力全开月：{fun['busiest_month']}", "会话最多的一个月"))
        if fun.get("longest_streak_days", 0) >= TH_STREAK:
            fun_items.append(("hot", "🔗", f"连续并肩 {fun['longest_streak_days']} 天", "每天都有 Agent 会话"))
        if fun.get("busiest_day_count", 0) >= TH_BUSY_DAY:
            day_label = fun["busiest_day"][5:].replace("-", "/")
            fun_items.append(("hot", "⚡", f"单日爆发：{day_label} ×{fun['busiest_day_count']}", "一天之内的会话峰值"))
        if (fun.get("period_months", 0) >= 2
                and fun.get("active_months") == fun.get("period_months")):
            fun_items.append(("cool", "📅", f"月度全勤 ×{fun['active_months']}", "周期里每个月都有会话"))
        fav_count = fun.get("favorite_hour_count", 0)
        if fav_count >= max(3, round(fun["session_count"] * 0.15)):
            fun_items.append(("", "⏰", f"固定搭子：{fun['favorite_hour']} 点档 ×{fav_count}", "最常呼叫 Agent 的小时段"))
        # 记录类：无阈值
        if fun.get("latest_clock"):
            fun_items.append(("", "🕯️", f"最晚收工 {fun['latest_clock']}", "跨夜算到凌晨也算当晚"))
        if fun.get("earliest_clock") and int(fun["earliest_clock"][:2]) < 8:
            fun_items.append(("", "🌤️", f"最早开工 {fun['earliest_clock']}", "别人还在睡"))
        if fun.get("longest_gap_days", 0) >= TH_GAP:
            fun_items.append(("", "🫥", f"神隐 {fun['longest_gap_days']} 天", "最长一次没找 Agent 的间隔"))
    if fun_items:
        parts.append("<div class=\"section\"><div class=\"sec-head\"><span class=\"no\">01</span><h2>隐藏战绩</h2><span class=\"hint\">HIDDEN ACHIEVEMENTS</span></div>")
        parts.append("<div class=\"funs\">")
        for cls, em, text, hint in fun_items:
            parts.append(f"<div class=\"fun {cls}\"><span class=\"em\">{em}</span>{esc(text)}&nbsp;<small>{esc(hint)}</small></div>")
        parts.append("</div></div>")

    # ---- agent roster ----
    if agents:
        parts.append("<div class=\"section\"><div class=\"sec-head\"><span class=\"no\">02</span><h2>AI 干员图鉴</h2><span class=\"hint\">AGENT ROSTER</span></div>")
        parts.append("<div class=\"grid\">")
        roster = sorted(agents, key=lambda a: (a.get("session_count") is None, -(a.get("session_count") or 0)))
        n = len(roster)
        tier1 = 1                 # 只有第 1 名是主力干将
        tier2 = max(1, (n + 1) // 2)  # 第 2 名到前一半：干员；其余：酱油仔
        for i, a in enumerate(roster):
            if i < tier1:
                tag, tag_cls = "主力干将", "hot"
            elif i < tier2:
                tag, tag_cls = "干员", ""
            else:
                tag, tag_cls = "酱油仔", "alt"
            lines = []
            if a.get("session_count") is not None:
                lines.append(f"会话 {esc(a['session_count'])} 次")
            if a.get("first_seen") and a.get("last_seen"):
                lines.append(f"活跃 {esc(a['first_seen'])} – {esc(a['last_seen'])}")
            elif a.get("first_seen"):
                lines.append(f"首见 {esc(a['first_seen'])}")
            parts.append("<div class=\"card\">")
            parts.append(f"<span class=\"tag {tag_cls}\">{tag}</span>")
            parts.append(f"<h3><span class=\"em\">{esc(agent_emoji(a['name'], a.get('emoji')))}</span>{esc(a['name'])}</h3>")
            if a.get("note"):
                parts.append(f"<p>{esc(a['note'])}</p>")
            if lines:
                parts.append(f"<div class=\"meta-line\">{' · '.join(lines)}</div>")
            parts.append("</div>")
        parts.append("</div></div>")

    # ---- achievement wall ----
    if projects:
        parts.append("<div class=\"section\"><div class=\"sec-head\"><span class=\"no\">03</span><h2>成就墙</h2><span class=\"hint\">ACHIEVEMENTS</span></div>")
        parts.append("<div class=\"grid\">")
        for i, p in enumerate(projects):
            parts.append("<div class=\"card\">")
            parts.append(f'<span class="tag {"alt" if i % 2 else ""}">{esc(noun)}成果</span>')
            parts.append(f"<h3>{esc(p['name'])}</h3>")
            if p.get("one_liner"):
                parts.append(f"<p>{esc(p['one_liner'])}</p>")
            if p.get("activity"):
                parts.append(f"<div class=\"meta-line\">活跃：{esc(p['activity'])}</div>")
            if p.get("ai_tools"):
                parts.append("<div class=\"chips\">" + "".join(
                    f"<span class=\"chip\">{esc(t)}</span>" for t in p["ai_tools"]
                ) + "</div>")
            for b in p.get("badges") or []:
                if isinstance(b, str):
                    level, badge_text = "", b
                else:
                    level = b.get("level") or ""
                    badge_text = str(b.get("text") or "")
                if badge_text:
                    parts.append(f"<span class=\"badge {esc(level)}\">{esc(badge_text)}</span>")
            if p.get("milestones"):
                parts.append("<div class=\"mile\">")
                for m in p["milestones"]:
                    parts.append(f"<div><b>{esc(m['date'][5:])}</b><span>{esc(m['text'])}</span></div>")
                parts.append("</div>")
            parts.append("</div>")
        parts.append("</div></div>")

    # ---- timeline (vertical, grouped by month) ----
    if timeline:
        parts.append(f"<div class=\"section\"><div class=\"sec-head\"><span class=\"no\">04</span><h2>{esc(noun)}时间线</h2><span class=\"hint\">TIMELINE</span></div>")
        parts.append("<div class=\"timeline\">")
        current_month = None
        for t in sorted(timeline, key=lambda x: x.get("date") or ""):
            month = (t.get("date") or "")[:7]
            if month and month != current_month:
                current_month = month
                parts.append(f"<div class=\"mon\">{esc(month)}</div>")
            parts.append("<div class=\"t\">")
            parts.append(f"<span class=\"d\">{esc(t['date'][5:])}</span><span class=\"p\">{esc(t['project'])}</span>")
            parts.append(f"<div class=\"x\">{esc(t['text'])}</div>")
            parts.append("</div>")
        parts.append("</div></div>")

    # ---- narrative ----
    if narrative.get("headline") or narrative.get("paragraphs"):
        parts.append("<div class=\"section\"><div class=\"story\">")
        if narrative.get("headline"):
            parts.append(f"<h3><mark>{esc(noun)}总结</mark> {esc(narrative['headline'])}</h3>")
        for p in narrative.get("paragraphs") or []:
            parts.append(f"<p>{esc(p)}</p>")
        parts.append("</div></div>")

    # ---- share (local-only: Web Share API / clipboard, zero network) ----
    share_meta = json.dumps({
        "owner": str(meta.get("owner", "")),
        "label": str(meta.get("period_label", "")),
        "agents": stats.get("agents_count", 0),
        "sessions": stats.get("sessions_total", 0),
        "projects": stats.get("projects_count", 0),
        "top": str(stats.get("top_agent") or ""),
    }, ensure_ascii=False).replace("</", "<\\/")  # never break out of <script>
    parts.append(
        '<button class="share-btn" id="shareBtn" type="button">SHARE ↗</button>'
        '<div class="share-pop" id="sharePop">'
        '<button class="opt" id="shareFile" type="button">分享这份报告文件<small>调起系统分享（微信 / AirDrop / 邮件），把整个 HTML 发出去</small></button>'
        '<button class="opt" id="shareText" type="button">复制分享文案<small>一段战报文字，直接粘贴到微信 / 朋友圈</small></button>'
        '<div class="note">文件不上传任何地方，分享动作只发生在你自己的设备上。</div>'
        '</div>'
        '<div class="share-toast" id="shareToast"></div>'
    )
    parts.append(
        "<script>(function(){"
        f"var META={share_meta};"
        "var btn=document.getElementById('shareBtn'),pop=document.getElementById('sharePop'),toast=document.getElementById('shareToast');"
        "function say(t){toast.textContent=t;toast.classList.add('show');setTimeout(function(){toast.classList.remove('show')},2200)}"
        "btn.addEventListener('click',function(){pop.classList.toggle('open')});"
        "document.addEventListener('click',function(e){if(!pop.contains(e.target)&&e.target!==btn)pop.classList.remove('open')});"
        "document.getElementById('shareText').addEventListener('click',function(){"
        "var t='我用 Agent 干了啥 · '+META.label+'：'+META.agents+' 个 AI 干员、'+META.sessions+' 次会话、'+META.projects+' 个项目'"
        "+(META.top?'，最强搭档 '+META.top:'')+'。—— 仅供个人回顾与分享娱乐';"
        "var done=function(){say('已复制，去粘贴吧')},fail=function(){say('复制失败，浏览器限制了剪贴板')};"
        "if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(done,fail)}else{fail()}"
        "pop.classList.remove('open')});"
        "document.getElementById('shareFile').addEventListener('click',function(){"
        "try{var blob=new Blob(['<!DOCTYPE html>\\n'+document.documentElement.outerHTML],{type:'text/html'});"
        "var f=new File([blob],META.owner+'_'+META.label+'_我用Agent干了啥.html',{type:'text/html'});"
        "if(navigator.canShare&&navigator.canShare({files:[f]})){navigator.share({files:[f],title:'我用 Agent 干了啥 · '+META.label}).then(function(){say('已调起系统分享')},function(){})}"
        "else{say('当前浏览器不支持文件分享，直接把 HTML 文件发给别人就行')}}"
        "catch(e){say('当前浏览器不支持文件分享，直接把 HTML 文件发给别人就行')}"
        "pop.classList.remove('open')});"
        "})();</script>"
    )

    # ---- footer ----
    parts.append("<footer>")
    parts.append(f"<b>关于本报告</b>：由 agent-usage-report Skill v{esc(meta.get('skill_version', ''))} 于 {esc(meta.get('generated_at', ''))} 回顾本机 AI 工具记录自动整理生成，仅供个人回顾与分享娱乐。")
    parts.append("<br>统计仅来自本机可见的会话与文件元数据；没被记录的使用不会出现在这里，出现的内容也不代表任何第三方评价。")
    parts.append("</footer></body></html>")
    return "\n".join(parts) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render report_data.json into a single-file HTML report.")
    parser.add_argument("input", type=Path, help="report_data.json produced by build_report_data.py.")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output HTML path (e.g. index.html).")
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    html_text = render(data)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_text, encoding="utf-8")
    print(f"OK: wrote {args.output} ({len(html_text)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
