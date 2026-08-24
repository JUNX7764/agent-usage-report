#!/usr/bin/env python3
"""Scan for installed AI agents on macOS, Linux, or Windows.

Auto-detects the platform and checks the correct paths for each known AI agent.
Outputs a JSON summary of found agents with their paths, sizes, and file counts.

Also provides project attribution classification for Git repositories to help
distinguish user-created projects from downloaded open-source projects.

Cross-platform: works on macOS, Linux, and Windows without modification.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Platform helpers
# ---------------------------------------------------------------------------


def _home() -> Path:
    return Path.home()


def _appdata() -> Path:
    """Return the roaming app-data directory."""
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", str(_home() / "AppData" / "Roaming")))
    return _home() / "Library" / "Application Support"


def _local_appdata() -> Path:
    """Return the local app-data directory."""
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", str(_home() / "AppData" / "Local")))
    return _home() / "Library" / "Application Support"


def _platform_label() -> str:
    return sys.platform  # 'darwin', 'win32', 'linux', ...


# ---------------------------------------------------------------------------
# Agent catalog: name -> list of candidate paths
# ---------------------------------------------------------------------------

def _agent_paths() -> dict[str, list[Path]]:
    home = _home()
    appdata = _appdata()
    local = _local_appdata()

    return {
        "Proma": [home / ".proma"],
        "Claude Code": [home / ".claude"],
        "Claude Desktop": [appdata / "Claude"],
        "Hermes": [home / ".hermes"],
        "Cursor": [home / ".cursor", appdata / "Cursor"],
        "Codex": [home / "Documents" / "Codex", home / ".codex"],
        "Windsurf": [home / ".windsurf", appdata / "Windsurf", home / ".codeium" / "windsurf"],
        "Aider": [home / ".aider", home / ".aider.chat.history.md"],
        "Cline": [
            appdata / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev",
            home / ".cline",
            home / ".vscode" / "extensions" / "saoudrizwan.claude-dev-*",
            home / ".cursor" / "extensions" / "saoudrizwan.claude-dev-*",
            home / ".vscode-oss" / "extensions" / "saoudrizwan.claude-dev-*",
        ],
        "Continue": [
            home / ".continue",
            home / ".vscode" / "extensions" / "continue.continue-*",
            home / ".cursor" / "extensions" / "continue.continue-*",
        ],
        "Ollama": [home / ".ollama"],
        "LM Studio": [appdata / "LM Studio", home / ".lmstudio"],
        # 国内 AI Agent
        "WorkBuddy": [appdata / "WorkBuddy", local / "WorkBuddy", home / ".workbuddy"],
        "TRAE": [appdata / "TRAE"],
        "Qoder": [appdata / "Qoder", local / "Qoder"],
        "悟空": [
            appdata / "Wukong",
            appdata / "DingTalk" / "Wukong",
        ],
        "千问办公": [appdata / "QianwenOffice"],
        "DscAiWork": [appdata / "DscAiWork", home / "DscAiWork"],
        # Code completion tools
        "Tabnine": [appdata / "TabNine"],
        "Codeium": [appdata / "Codeium", local / "Codeium"],
        "Supermaven": [
            home / ".vscode" / "extensions" / "supermaven*",
            home / ".cursor" / "extensions" / "supermaven*",
        ],
        "Amazon Q Developer": [home / ".aws" / "amazonq", appdata / "amazon-q"],
        # 国内编程 Agent (新增 4 个)
        "Kimi Code": [appdata / "Kimi Code", home / ".kimi-code"],
        "Kimi Work": [appdata / "Kimi Work"],
        "CodeBuddy": [appdata / "CodeBuddy"],
        "OMP": [appdata / "OMP"],
        # 国外编程 Agent (新增 16 个)
        "Gemini CLI": [home / ".gemini"],
        "Qwen Code": [home / ".qwen"],
        "Antigravity CLI": [home / ".antigravity", home / ".agy"],
        "DeepSeek Harness": (
            # $DSH_HOME 可重定向数据根；默认 ~/.dsh
            [Path(os.environ["DSH_HOME"])] if os.environ.get("DSH_HOME") else []
        ) + [home / ".dsh"],
        "OpenCode": [
            home / ".local" / "share" / "opencode",  # XDG data dir (sessions / opencode.db)
            home / ".opencode",  # binary + config dir
            appdata / "OpenCode",
            local / "opencode",
        ],
        "Alma": [appdata / "Alma"],
        "Pi": [appdata / "Pi"],
        "Grok Build": [appdata / "Grok Build"],
        "Copilot CLI": [home / ".copilot", home / ".github" / "copilot"],
        "Zed": [appdata / "Zed", home / ".config" / "zed"],
        "Warp": [appdata / "dev.warp.Warp-Stable"],
        "Augment": [home / ".augment"],
        "OpenClaw": [appdata / "OpenClaw"],
        "Bub": [appdata / "Bub"],
        "Cradle": [appdata / "Cradle"],
        "MiMo Code": [appdata / "MiMo Code", home / ".local" / "share" / "mimocode"],
        "Craft Agent": [appdata / "Craft Agent"],
        "Droid": [appdata / "Droid"],
        "ZCode": [appdata / "ZCode"],
        "Arkloop": [appdata / "Arkloop"],
        "OpticLM": [appdata / "OpticLM"],
        # 多智能体工具 (新增 5 个)
        "Raft": [appdata / "Raft"],
        "Lody": [appdata / "Lody"],
        "Multica": [appdata / "Multica"],
        "Cumora": [appdata / "Cumora"],
        "Paseo": [appdata / "Paseo"],
        # 笔记工具 (新增 4 个)
        "Obsidian": [appdata / "obsidian"],
        "Notion": [local / "Notion"],
        "Apple Notes": [home / "Library" / "Group Containers" / "group.com.apple.notes"] if sys.platform == "darwin" else [],
        "TiddlyWiki": [home / ".tiddlywiki"],
        # 其他工具 (新增 2 个)
        "Raycast": [appdata / "Raycast"] if sys.platform == "darwin" else [],
        "Cherry Studio": [appdata / "Cherry Studio"],
    }


WEB_AGENT_PROJECT_CONFIGS = {
    ".bolt/": "bolt.new",
    ".v0/": "v0.dev",
    ".replit/": "Replit",
    ".lovable/": "Lovable",
    ".gpt-engineer/": "Lovable (旧名 GPT Engineer)",
}

AI_PROJECT_CONFIG_PATTERNS = {
    ".claude/",
    ".cursor/",
    ".codex/",
    ".opencode/",
    ".dsh/",       # DeepSeek Harness 项目级配置
    ".dsh-home/",  # DeepSeek Harness 项目本地数据根
    ".ocx/",
    ".hermes/",
    ".aider*",
    ".continue/",
    ".cline/",
    ".windsurf/",
    ".windsurfrules",
    ".cursorrules",
    ".clinerules",
    ".workbuddy/",
    ".trae/",
    ".qoder/",
    ".qoderwork/",
    ".wukong/",
    ".qianwen/",
    ".dscaiwork/",
    ".codeium/",
    ".bolt/",
    ".v0/",
    ".replit/",
    ".lovable/",
    ".gpt-engineer/",
    # 新增编程 Agent 项目级信号
    ".kimi/",
    ".codebuddy/",
    ".omp/",
    ".openclaw/",
    ".alma/",
    ".pi/",
    ".grok/",
    ".bub/",
    ".cradle/",
    ".mimo/",
    ".craft/",
    ".droid/",
    ".zcode/",
    ".arkloop/",
    ".opticlm/",
    # 多智能体 / 笔记 / 其他
    ".raft/",
    ".lody/",
    ".multica/",
    ".cumora/",
    ".paseo/",
    ".tiddlywiki/",
    ".obsidian/",
    ".open-webui/",
    ".lobehub/",
    "AGENTS.md",
    "CLAUDE.md",
    ".github/copilot-instructions.md",
}


def scan_web_agents_from_projects(projects: list[str | os.PathLike]) -> dict[str, dict]:
    """Infer web-based agents from project config directories."""
    found: dict[str, dict] = {}
    for project_path in projects:
        project = Path(project_path)
        if not project.is_dir():
            continue
        for config_dir, agent_name in WEB_AGENT_PROJECT_CONFIGS.items():
            if (project / config_dir).exists():
                if agent_name not in found:
                    found[agent_name] = {"projects": [], "type": "web_inferred"}
                found[agent_name]["projects"].append(str(project))
    return found


# ---------------------------------------------------------------------------
# Scan logic
# ---------------------------------------------------------------------------

EXCLUDE_DIRS = {".git", "node_modules", ".venv", "__pycache__", "dist", "build"}
MAX_FILES_TO_COUNT = 50_000  # safety guard


def _count_files(path: Path) -> tuple[int, int]:
    """Return (file_count, total_size_bytes) for a directory, or (1, size) for a file."""
    if path.is_file():
        try:
            return 1, path.stat().st_size
        except OSError:
            return 1, 0

    count = 0
    total = 0
    try:
        for current, dirnames, filenames in os.walk(path, topdown=True, followlinks=False):
            # prune excluded and symlink dirs
            dirnames[:] = [
                d for d in dirnames
                if d not in EXCLUDE_DIRS and not (Path(current) / d).is_symlink()
            ]
            for name in filenames:
                fp = Path(current) / name
                if fp.is_symlink():
                    continue
                try:
                    total += fp.stat().st_size
                except OSError:
                    pass
                count += 1
                if count >= MAX_FILES_TO_COUNT:
                    return count, total
    except OSError:
        pass
    return count, total


def _glob_dirs(parent: Path, prefix: str) -> list[Path]:
    """Find directories under *parent* whose name starts with *prefix*."""
    if not parent.is_dir():
        return []
    result = []
    try:
        for entry in parent.iterdir():
            if entry.is_dir() and entry.name.startswith(prefix):
                result.append(entry)
    except OSError:
        pass
    return result


# ---------------------------------------------------------------------------
# Project attribution classification
# ---------------------------------------------------------------------------

def _run_git(repo: Path, *args: str) -> tuple[bool, str]:
    """Run a git command. Returns (success, output)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0, result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False, ""


def _get_commit_authors(repo: Path, user_identities: list[str]) -> tuple[int, int]:
    """Return (user_commits, total_commits) for the repo."""
    success, output = _run_git(repo, "rev-list", "--all", "--count")
    if not success or not output:
        return 0, 0
    try:
        total = int(output)
    except ValueError:
        return 0, 0

    if not user_identities or total == 0:
        return 0, total

    # Collect unique hashes that match at least one user identity
    matched_hashes: set[str] = set()
    for identity in user_identities:
        success, output = _run_git(
            repo, "rev-list", "--all", f"--author={identity}"
        )
        if success and output:
            matched_hashes.update(output.splitlines())

    return len(matched_hashes), total


def _check_remote_public(repo: Path) -> bool:
    """Check if any remote points to a public hosting service."""
    success, output = _run_git(repo, "remote", "-v")
    if not success:
        return False
    
    public_patterns = [
        r"github\.com",
        r"gitlab\.com",
        r"gitee\.com",
        r"bitbucket\.org",
        r"codeberg\.org",
    ]
    for pattern in public_patterns:
        if re.search(pattern, output, re.IGNORECASE):
            return True
    return False


def _check_license_opensource(repo: Path) -> bool:
    """Check if LICENSE file indicates open source."""
    license_patterns = [
        ("LICENSE", ["MIT", "Apache", "GPL", "BSD", "ISC", "MPL"]),
        ("LICENSE.md", ["MIT", "Apache", "GPL", "BSD", "ISC", "MPL"]),
        ("LICENSE.txt", ["MIT", "Apache", "GPL", "BSD", "ISC", "MPL"]),
        ("COPYING", ["GPL", "LGPL"]),
    ]
    
    for filename, keywords in license_patterns:
        license_file = repo / filename
        if license_file.is_file():
            try:
                content = license_file.read_text(encoding="utf-8", errors="ignore")[:2000]
                for keyword in keywords:
                    if keyword.upper() in content.upper():
                        return True
            except OSError:
                pass
    return False


def _check_readme_contributors(repo: Path) -> bool:
    """Check if README mentions multiple contributors."""
    readme_files = ["README.md", "README.rst", "README.txt", "README"]
    
    contributor_patterns = [
        r"(?i)contributors?\s*:?",
        r"(?i)maintained\s+by",
        r"(?i)authors?\s*:?",
        r"(?i)credits\s*:?",
    ]
    
    for filename in readme_files:
        readme = repo / filename
        if readme.is_file():
            try:
                content = readme.read_text(encoding="utf-8", errors="ignore")[:5000]
                for pattern in contributor_patterns:
                    if re.search(pattern, content):
                        # Check if there are multiple names/emails
                        email_count = len(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", content))
                        if email_count > 2:
                            return True
            except OSError:
                pass
    return False


def _check_package_author(repo: Path, user_identities: list[str]) -> str | None:
    """Check package.json or setup.py author field. Returns 'user'|'third_party'|None."""
    # Check package.json
    package_json = repo / "package.json"
    if package_json.is_file():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            author = data.get("author", "")
            if isinstance(author, dict):
                author = author.get("name", "") + " " + author.get("email", "")
            elif not isinstance(author, str):
                author = ""
            
            author_lower = author.lower()
            for identity in user_identities:
                if identity.lower() in author_lower:
                    return "user"
            if author.strip():
                return "third_party"
        except (json.JSONDecodeError, OSError):
            pass
    
    # Check setup.py
    setup_py = repo / "setup.py"
    if setup_py.is_file():
        try:
            content = setup_py.read_text(encoding="utf-8", errors="ignore")[:10000]
            author_match = re.search(r"author\s*=\s*['\"]([^'\"]+)['\"]", content)
            if author_match:
                author = author_match.group(1)
                author_lower = author.lower()
                for identity in user_identities:
                    if identity.lower() in author_lower:
                        return "user"
                return "third_party"
        except OSError:
            pass
    
    return None


def get_project_activity_period(project_path: Path) -> dict | None:
    """获取项目活跃时间（创建和最后修改）
    
    Returns:
        dict with keys: first_activity, last_activity, type ("git" or "filesystem")
        or None if unable to determine
    """
    git_repo = project_path / ".git"
    
    if git_repo.exists():
        try:
            # Git: 最早和最近的提交时间
            result = subprocess.run(
                ["git", "-C", str(project_path), "log", "--format=%ai", "--reverse"],
                capture_output=True, text=True, timeout=10
            )
            commits = [line for line in result.stdout.strip().split('\n') if line]
            if commits:
                # Parse ISO-8601 timestamp, removing timezone for simplicity
                first_commit = datetime.fromisoformat(commits[0].rsplit(' ', 1)[0])
                last_commit = datetime.fromisoformat(commits[-1].rsplit(' ', 1)[0])
                return {
                    "first_activity": first_commit,
                    "last_activity": last_commit,
                    "type": "git"
                }
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError, OSError):
            pass
    
    # 非 Git：文件系统时间
    try:
        stat = project_path.stat()
        # macOS/Windows: 创建时间; Linux: ctime is not creation time
        created = datetime.fromtimestamp(
            stat.st_birthtime if hasattr(stat, 'st_birthtime') else stat.st_ctime
        )
        # 最后修改时间
        modified = datetime.fromtimestamp(stat.st_mtime)
        
        return {
            "first_activity": created,
            "last_activity": modified,
            "type": "filesystem"
        }
    except (OSError, AttributeError):
        return None


def is_project_active_in_period(project_path: Path, start_date: datetime, end_date: datetime) -> bool | None:
    """判断项目在时间段内是否有活动
    
    Returns:
        True if active in period, False if not active, None if unable to determine
    """
    activity = get_project_activity_period(project_path)
    if not activity:
        return None  # 无法判断
    
    # 活动区间与目标区间有交集
    return (activity["last_activity"] >= start_date and 
            activity["first_activity"] <= end_date)


def classify_project_attribution(
    repo: Path, user_identities: list[str] | None = None
) -> dict:
    """Classify a Git project as created, downloaded, contributed, or uncertain.
    
    Args:
        repo: Path to Git repository
        user_identities: List of user name/email patterns to match against commits
    
    Returns:
        dict with keys: attribution, confidence, signals
        
    Attribution categories:
        - created: User created/owns this project
        - downloaded: Downloaded open-source project (user has minimal/no commits)
        - contributed: User contributed to open-source project (has some commits but <10%)
        - uncertain: Cannot determine automatically
    """
    if user_identities is None:
        user_identities = []
    
    if not (repo / ".git").exists():
        return {
            "attribution": "uncertain",
            "confidence": "low",
            "signals": ["not_a_git_repository"],
        }
    
    signals = []
    
    # Check commit authorship
    user_commits, total_commits = _get_commit_authors(repo, user_identities)
    if total_commits > 0:
        user_ratio = user_commits / total_commits
        signals.append(f"user_commits={user_commits}/{total_commits} ({user_ratio:.1%})")
    else:
        user_ratio = 0.0
        signals.append("no_commits_found")
    
    # Check if remote is public
    is_public_remote = _check_remote_public(repo)
    if is_public_remote:
        signals.append("public_remote")
    else:
        signals.append("no_public_remote")
    
    # Check LICENSE
    has_opensource_license = _check_license_opensource(repo)
    if has_opensource_license:
        signals.append("opensource_license")
    
    # Check README for contributors
    has_multiple_contributors = _check_readme_contributors(repo)
    if has_multiple_contributors:
        signals.append("multiple_contributors_in_readme")
    
    # Check package author
    package_author = _check_package_author(repo, user_identities)
    if package_author == "user":
        signals.append("package_author_matches_user")
    elif package_author == "third_party":
        signals.append("package_author_third_party")
    
    # Classification logic
    if user_commits == 0 and is_public_remote:
        return {
            "attribution": "downloaded",
            "confidence": "high",
            "signals": signals,
        }
    
    if user_ratio >= 0.5 or (user_commits > 5 and not is_public_remote):
        return {
            "attribution": "created",
            "confidence": "high" if user_ratio >= 0.8 else "medium",
            "signals": signals,
        }
    
    if 0 < user_ratio < 0.1 and is_public_remote:
        return {
            "attribution": "contributed",
            "confidence": "medium",
            "signals": signals,
        }
    
    if 0.1 <= user_ratio < 0.5 and (is_public_remote or has_opensource_license or has_multiple_contributors):
        return {
            "attribution": "contributed",
            "confidence": "medium",
            "signals": signals,
        }
    
    # Default to uncertain
    confidence = "low"
    if user_commits > 0:
        confidence = "medium"
    
    return {
        "attribution": "uncertain",
        "confidence": confidence,
        "signals": signals,
    }


# Agents that are not conversational AI agents (model runners, note tools,
# launchers, completion-only). They are still reported, but tagged so the
# downstream report never counts them as "AI 干员".
AGENT_CATEGORIES = {
    "Ollama": "local-model",
    "LM Studio": "local-model",
    "OMLX": "local-model",
    "Tabnine": "completion-tool",
    "Codeium": "completion-tool",
    "Supermaven": "completion-tool",
    "Obsidian": "note-tool",
    "Notion": "note-tool",
    "Apple Notes": "note-tool",
    "TiddlyWiki": "note-tool",
    "Raycast": "launcher",
}


def _category(name: str) -> str:
    return AGENT_CATEGORIES.get(name, "agent")


def _top_readable(path: Path) -> bool:
    """False when a directory exists but cannot be listed (macOS TCC / perms)."""
    try:
        with os.scandir(path) as it:
            next(it, None)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Runtime signals: catch agents the path catalog missed
# ---------------------------------------------------------------------------

# agent name -> known CLI binary / process-name tokens (lowercase)
RUNTIME_TOKENS = {
    "Proma": ["proma"],
    "Claude Code": ["claude"],
    "Hermes": ["hermes"],
    "Cursor": ["cursor"],
    "Codex": ["codex"],
    "Windsurf": ["windsurf"],
    "OpenCode": ["opencode"],
    "DeepSeek Harness": ["dsh"],
    "Gemini CLI": ["gemini"],
    "Qwen Code": ["qwen"],
    "Aider": ["aider"],
    "Copilot CLI": ["copilot"],
    "Ollama": ["ollama"],
    "LM Studio": ["lm-studio", "lm studio", "lms"],
    "Warp": ["warp"],
    "Zed": ["zed"],
    "TRAE": ["trae"],
    "Cherry Studio": ["cherrystudio", "cherry studio"],
    "CodeBuddy": ["codebuddy"],
    "Droid": ["droid"],
}

# Environment variables agents set inside their own sessions/terminals.
ENV_MARKERS = {
    "CLAUDECODE": "Claude Code",
    "CLAUDE_CODE_ENTRYPOINT": "Claude Code",
    "CURSOR_TRACE_ID": "Cursor",
}


def _detect_runtime_signals() -> dict:
    """Detect agents via PATH, running processes, and env markers.

    Heuristic and metadata-only. Catches agents whose data directories are
    missing from the path catalog — the classic silent-miss failure (e.g. the
    user is literally running this skill inside an agent we did not scan).
    """
    on_path: dict[str, list[str]] = {}
    for agent, tokens in RUNTIME_TOKENS.items():
        for token in tokens:
            resolved = shutil.which(token)
            if resolved:
                on_path.setdefault(agent, []).append(resolved)

    names: list[str] = []
    try:
        if sys.platform == "win32":
            out = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=10,
            ).stdout
            names = [
                line.split('","')[0].strip('"').lower()
                for line in out.splitlines() if line
            ]
        else:
            out = subprocess.run(
                ["ps", "-eo", "comm="], capture_output=True, text=True, timeout=10,
            ).stdout
            names = [
                os.path.basename(line.strip()).lower()
                for line in out.splitlines() if line.strip()
            ]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        names = []
    running: dict[str, list[str]] = {}
    for proc in sorted(set(names)):
        for agent, tokens in RUNTIME_TOKENS.items():
            if any(token in proc for token in tokens):
                running.setdefault(agent, []).append(proc)

    env_hits: dict[str, list[str]] = {}
    for var, agent in ENV_MARKERS.items():
        if os.environ.get(var):
            env_hits.setdefault(agent, []).append(var)
    if os.environ.get("TERM_PROGRAM") == "WarpTerminal":
        env_hits.setdefault("Warp", []).append("TERM_PROGRAM")

    detected = sorted(set(on_path) | set(running) | set(env_hits))
    return {
        "on_path": {k: sorted(set(v)) for k, v in sorted(on_path.items())},
        "running_processes": {k: sorted(set(v)) for k, v in sorted(running.items())},
        "env_markers": {k: sorted(set(v)) for k, v in sorted(env_hits.items())},
        "agents_detected_at_runtime": detected,
    }


# ---------------------------------------------------------------------------
# Heuristic discovery of unknown agent data directories
# ---------------------------------------------------------------------------

SESSION_DIR_MARKERS = {
    "session", "sessions", "history", "conversations", "chats", "storage",
}
SESSION_FILE_SUFFIXES = {".jsonl", ".db", ".sqlite", ".sqlite3"}
MAX_UNKNOWN_CANDIDATES = 30


def _looks_like_agent_data(path: Path) -> list[str]:
    """Return marker descriptions if a directory smells like agent session data.

    Metadata only: names and types, never content.
    """
    markers: list[str] = []
    try:
        with os.scandir(path) as it:
            entries = list(it)[:200]
    except OSError:
        return markers
    for e in entries:
        name = e.name.lower()
        if e.is_dir(follow_symlinks=False) and name in SESSION_DIR_MARKERS:
            markers.append(f"dir:{e.name}")
        elif e.is_file(follow_symlinks=False) and (
            Path(name).suffix in SESSION_FILE_SUFFIXES or name.startswith("history")
        ):
            markers.append(f"file:{e.name}")
        if len(markers) >= 3:
            break
    return markers


def _discover_unknown_candidates(known_paths: set[str]) -> list[dict]:
    """Scan common config roots for agent-looking dirs missing from the catalog."""
    home = _home()
    roots = [home, home / ".config", home / ".local" / "share", _appdata()]
    candidates: list[dict] = []
    seen: set[str] = set()
    for root in roots:
        try:
            with os.scandir(root) as it:
                entries = list(it)[:500]
        except OSError:
            continue
        for e in entries:
            if len(candidates) >= MAX_UNKNOWN_CANDIDATES:
                return candidates
            if not e.is_dir(follow_symlinks=False):
                continue
            # at home level only dotdirs are plausible agent data locations
            if root == home and not e.name.startswith("."):
                continue
            spath = str(Path(e.path))
            if spath in known_paths or spath in seen:
                continue
            markers = _looks_like_agent_data(Path(e.path))
            if len(markers) >= 2:
                seen.add(spath)
                candidates.append({"path": spath, "markers": markers})
    return candidates


def scan() -> dict:
    platform = _platform_label()
    found_by_name: dict[str, dict] = {}

    def _add(name: str, path: Path) -> None:
        entry = found_by_name.setdefault(name, {
            "name": name,
            "category": _category(name),
            "paths": [],
            "file_count": 0,
            "size_bytes": 0,
            "notes": [],
        })
        spath = str(path)
        if spath in entry["paths"]:
            return  # macOS: appdata == local, avoid duplicate candidates
        entry["paths"].append(spath)
        if path.is_dir() and not _top_readable(path):
            entry["notes"].append(f"exists_but_unreadable: {path}")
            return
        file_count, total_size = _count_files(path)
        entry["file_count"] += file_count
        entry["size_bytes"] += total_size
        if file_count >= MAX_FILES_TO_COUNT:
            entry["notes"].append("file_count_capped")

    for name, candidates in _agent_paths().items():
        for path in candidates:
            # Handle glob-style entries (e.g. saoudrizwan.claude-dev-*)
            if path.name.endswith("*"):
                for match in _glob_dirs(path.parent, path.name[:-1]):
                    _add(name, match)
                continue
            if path.exists():
                _add(name, path)

    # Also check for OMLX with glob pattern
    for search_dir in [_appdata(), _local_appdata()]:
        for match in _glob_dirs(search_dir, "OMLX"):
            if "OMLX" not in found_by_name:
                _add("OMLX", match)

    agents_found = list(found_by_name.values())
    for entry in agents_found:
        if entry["notes"]:
            entry["notes"] = sorted(set(entry["notes"]))
        else:
            entry.pop("notes")
    agents_not_found = [n for n in _agent_paths() if n not in found_by_name]

    runtime = _detect_runtime_signals()
    runtime_missing = [
        n for n in runtime["agents_detected_at_runtime"] if n not in found_by_name
    ]
    known_paths = {
        str(p)
        for candidates in _agent_paths().values()
        for p in candidates
        if not p.name.endswith("*")
    }
    unknown_candidates = _discover_unknown_candidates(known_paths)

    return {
        "schema_version": "1.1",
        "platform": platform,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "home_directory": str(_home()),
        "agents_found": agents_found,
        "agents_not_found": agents_not_found,
        "runtime_signals": runtime,
        "runtime_detected_but_no_data_dir": runtime_missing,
        "unknown_data_dir_candidates": unknown_candidates,
        "note": "File counts and sizes are approximate; entries are aggregated by agent name (multiple candidate paths merged into 'paths'). category != 'agent' means local-model/completion/note/launcher tool, not a conversational agent. 'runtime_detected_but_no_data_dir' lists agents seen on PATH / in processes / in env vars whose data dir was not found — always confirm those with the user. 'unknown_data_dir_candidates' are heuristic guesses for the user to claim. Content is not read in this phase.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan for installed AI agents (cross-platform)."
    )
    parser.add_argument("-o", "--output", type=Path, help="Output JSON file path.")
    args = parser.parse_args()

    result = scan()
    text = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        # Print friendly summary
        for agent in result["agents_found"]:
            file_count = agent.get("file_count", 0)
            if file_count > 1000:
                comment = "还挺能聊"
            elif file_count > 100:
                comment = "用得不少"
            else:
                comment = "也有记录"
            category = agent.get("category", "agent")
            suffix = "" if category == "agent" else f"（{category}，不算对话干员）"
            notes = agent.get("notes") or []
            warn = f" ⚠ {'; '.join(notes)}" if notes else ""
            print(f"找到 {agent['name']}（{file_count} 个文件）{suffix}... {comment}。{warn}")
        missing = result.get("runtime_detected_but_no_data_dir") or []
        if missing:
            print(
                "⚠ 这些 Agent 在 PATH/进程/环境变量里出现了，但没扫到数据目录："
                + ", ".join(missing)
                + " —— 请向用户确认数据位置后补扫。"
            )
        unknown = result.get("unknown_data_dir_candidates") or []
        if unknown:
            preview = "; ".join(c["path"] for c in unknown[:5])
            more = f" 等 {len(unknown)} 个" if len(unknown) > 5 else ""
            print(f"发现疑似 Agent 数据目录（不在已知清单，请让用户认领）：{preview}{more}")
        if result["agents_not_found"]:
            print(f"没找到: {', '.join(result['agents_not_found'])}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
