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
        "Hermes": [home / ".hermes"],
        "Cursor": [home / ".cursor", appdata / "Cursor"],
        "Codex": [home / "Documents" / "Codex", home / ".codex"],
        "Windsurf": [home / ".windsurf", appdata / "Windsurf"],
        "Aider": [home / ".aider", home / ".aider.chat.history.md"],
        "Cline": [
            appdata / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev",
            home / ".cline",
            home / ".vscode" / "extensions" / "saoudrizwan.claude-dev-*",
        ],
        "Continue": [
            home / ".continue",
            home / ".vscode" / "extensions" / "continue.continue-*",
        ],
        "Ollama": [home / ".ollama"],
        "LM Studio": [appdata / "LM Studio"],
        # 国内 AI Agent
        "WorkBuddy": [appdata / "WorkBuddy", local / "WorkBuddy"],
        "TRAE": [appdata / "TRAE"],
        "Qoder": [appdata / "Qoder", local / "Qoder"],
        "悟空": [
            appdata / "Wukong",
            appdata / "DingTalk" / "Wukong",
        ],
        "千问办公": [appdata / "QianwenOffice"],
        # Code completion tools
        "Tabnine": [appdata / "TabNine"],
        "Codeium": [appdata / "Codeium", local / "Codeium"],
        "Supermaven": [home / ".vscode" / "extensions" / "supermaven*"],
        "Amazon Q Developer": [home / ".aws"],
        # 国内编程 Agent (新增 4 个)
        "Kimi Code": [appdata / "Kimi Code"],
        "Kimi Work": [appdata / "Kimi Work"],
        "CodeBuddy": [appdata / "CodeBuddy"],
        "OMP": [appdata / "OMP"],
        # 国外编程 Agent (新增 16 个)
        "Gemini CLI": [home / ".gemini"],
        "Antigravity CLI": [home / ".antigravity", home / ".agy"],
        "OpenCode": [appdata / "OpenCode"],
        "Alma": [appdata / "Alma"],
        "Pi": [appdata / "Pi"],
        "Grok Build": [appdata / "Grok Build"],
        "Copilot CLI": [home / ".github" / "copilot"],
        "OpenClaw": [appdata / "OpenClaw"],
        "Bub": [appdata / "Bub"],
        "Cradle": [appdata / "Cradle"],
        "MiMo Code": [appdata / "MiMo Code"],
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


def scan() -> dict:
    platform = _platform_label()
    agents_found = []
    agents_not_found = []

    for name, candidates in _agent_paths().items():
        found = False
        for path in candidates:
            # Handle glob-style entries (e.g. OMLX*)
            if path.name.endswith("*"):
                real_parent = path.parent
                prefix = path.name[:-1]
                for match in _glob_dirs(real_parent, prefix):
                    file_count, total_size = _count_files(match)
                    agents_found.append({
                        "name": name,
                        "path": str(match),
                        "file_count": file_count,
                        "size_bytes": total_size,
                        "note": "file_count_capped" if file_count >= MAX_FILES_TO_COUNT else None,
                    })
                    found = True
                continue

            if path.exists():
                file_count, total_size = _count_files(path)
                agents_found.append({
                    "name": name,
                    "path": str(path),
                    "file_count": file_count,
                    "size_bytes": total_size,
                    "note": "file_count_capped" if file_count >= MAX_FILES_TO_COUNT else None,
                })
                found = True

        if not found:
            agents_not_found.append(name)

    # Also check for OMLX with glob pattern
    omlx_prefix = "OMLX"
    for search_dir in [_appdata(), _local_appdata()]:
        for match in _glob_dirs(search_dir, omlx_prefix):
            if "OMLX" not in [a["name"] for a in agents_found]:
                file_count, total_size = _count_files(match)
                agents_found.append({
                    "name": "OMLX",
                    "path": str(match),
                    "file_count": file_count,
                    "size_bytes": total_size,
                })

    return {
        "schema_version": "1.0",
        "platform": platform,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "home_directory": str(_home()),
        "agents_found": agents_found,
        "agents_not_found": [n for n in agents_not_found if n != "OMLX"],
        "note": "File counts and sizes are approximate. Content is not read in this phase.",
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
            print(f"找到 {agent['name']}（{file_count} 个文件）... {comment}。")
        if result["agents_not_found"]:
            print(f"没找到: {', '.join(result['agents_not_found'])}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
