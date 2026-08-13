#!/usr/bin/env python3
"""Collect read-only Git evidence for an authorized local repository; no scoring."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

NOISE_PARTS = {
    "node_modules", "vendor", "dist", "build", "coverage", ".venv", "__pycache__",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
}


def git(repo: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git command failed")
    return proc.stdout


def sanitize_remote(value: str) -> str:
    value = value.strip()
    if "://" not in value:
        return value
    parts = urlsplit(value)
    host = parts.hostname or ""
    if parts.port:
        host += f":{parts.port}"
    return urlunsplit((parts.scheme, host, parts.path, parts.query, ""))


def is_noise(path: str) -> bool:
    parts = set(Path(path).parts)
    return bool(parts & NOISE_PARTS) or Path(path).name in NOISE_PARTS


def classify(subject: str, paths: list[str]) -> list[str]:
    text = (subject + " " + " ".join(paths)).lower()
    classes = []
    rules = {
        "test": ("test", "spec", "pytest", "unittest"),
        "documentation": ("doc", "readme", ".md"),
        "bug_fix": ("fix", "bug", "hotfix", "修复"),
        "refactor": ("refactor", "cleanup", "重构"),
        "performance": ("perf", "performance", "optimiz", "性能"),
        "stability": ("retry", "timeout", "fallback", "error", "稳定", "异常"),
        "feature": ("feat", "feature", "add", "implement", "新增", "实现"),
        "configuration": ("config", "yaml", "toml", "docker", "ci", "workflow"),
    }
    for label, tokens in rules.items():
        if any(token in text for token in tokens):
            classes.append(label)
    return classes or ["unclassified"]


def parse_log(repo: Path, since: str, until: str, max_commits: int) -> list[dict]:
    fmt = "%H%x1f%aN%x1f%aE%x1f%aI%x1f%cN%x1f%cE%x1f%cI%x1f%P%x1f%s%x1e"
    args = ["log", "--all", "--use-mailmap", f"--format={fmt}", f"--max-count={max_commits}"]
    if since:
        args.append(f"--since={since}")
    if until:
        args.append(f"--until={until}")
    raw = git(repo, *args)
    commits = []
    for record in raw.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        fields = record.split("\x1f")
        if len(fields) != 9:
            continue
        commits.append(
            dict(zip(
                ["hash", "author_name", "author_email", "author_date", "committer_name",
                 "committer_email", "committer_date", "parents", "subject"], fields
            ))
        )
    return commits


def identity_match(commit: dict, identities: list[str]) -> bool:
    if not identities:
        return True
    haystack = "\n".join(
        [commit["author_name"], commit["author_email"], commit["committer_name"], commit["committer_email"]]
    ).casefold()
    return any(identity.casefold() in haystack for identity in identities)


def enrich(repo: Path, commit: dict) -> dict:
    raw = git(repo, "show", "--numstat", "--format=", "--no-renames", commit["hash"])
    files = []
    additions = deletions = 0
    for line in raw.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        added_s, deleted_s, path = parts
        binary = added_s == "-" or deleted_s == "-"
        added = 0 if binary else int(added_s)
        deleted = 0 if binary else int(deleted_s)
        additions += added
        deletions += deleted
        files.append(
            {
                "path": path,
                "additions": added,
                "deletions": deleted,
                "binary": binary,
                "noise": is_noise(path),
            }
        )
    meaningful = [row for row in files if not row["noise"]]
    commit["parent_count"] = len(commit["parents"].split()) if commit["parents"] else 0
    commit["is_merge"] = commit["parent_count"] > 1
    commit["is_revert_subject"] = commit["subject"].lower().startswith("revert")
    commit["files"] = files
    commit["file_count"] = len(files)
    commit["additions"] = additions
    commit["deletions"] = deletions
    commit["meaningful_churn"] = sum(row["additions"] + row["deletions"] for row in meaningful)
    commit["modules"] = sorted({Path(row["path"]).parts[0] for row in meaningful if Path(row["path"]).parts})
    commit["work_types"] = classify(commit["subject"], [row["path"] for row in meaningful])
    return commit


def choose_representatives(commits: list[dict], count: int) -> list[dict]:
    if not commits:
        return []
    ranked = sorted(commits, key=lambda row: (row["meaningful_churn"], row["file_count"]), reverse=True)
    chosen = {row["hash"]: row for row in ranked[: max(1, count // 2)]}
    chronological = sorted(commits, key=lambda row: row["author_date"])
    if count > 1:
        for index in range(count):
            position = round(index * (len(chronological) - 1) / (count - 1))
            row = chronological[position]
            chosen.setdefault(row["hash"], row)
            if len(chosen) >= count:
                break
    return list(chosen.values())[:count]


def collect(repo: Path, since: str = "", until: str = "", identities: list[str] | None = None,
            max_commits: int = 2000, representative_count: int = 8,
            patch_chars: int = 20000) -> dict:
    identities = identities or []
    repo = Path(git(repo, "rev-parse", "--show-toplevel").strip()).resolve()
    shallow = git(repo, "rev-parse", "--is-shallow-repository").strip() == "true"
    commits = [row for row in parse_log(repo, since, until, max_commits) if identity_match(row, identities)]
    enriched = [enrich(repo, row) for row in commits]
    representatives = choose_representatives(enriched, representative_count)
    rep_rows = []
    for row in representatives:
        patch = git(repo, "show", "--format=fuller", "--no-ext-diff", "--unified=3", row["hash"])
        rep_rows.append(
            {
                "hash": row["hash"],
                "subject": row["subject"],
                "author_date": row["author_date"],
                "files": [item["path"] for item in row["files"] if not item["noise"]],
                "work_types": row["work_types"],
                "patch": patch[:patch_chars],
                "patch_truncated": len(patch) > patch_chars,
            }
        )

    remotes = []
    for line in git(repo, "remote", "-v", check=False).splitlines():
        parts = re.split(r"\s+", line.strip())
        if len(parts) >= 2:
            remotes.append({"name": parts[0], "url": sanitize_remote(parts[1])})

    module_counts = Counter(module for row in enriched for module in row["modules"])
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": str(repo),
        "remotes": remotes,
        "scope": {"since": since or None, "until": until or None, "identities": identities, "all_refs": True},
        "history_limits": {"shallow_repository": shallow, "max_commits": max_commits, "returned_commits": len(enriched)},
        "summary": {
            "commit_count": len(enriched),
            "merge_count": sum(row["is_merge"] for row in enriched),
            "revert_subject_count": sum(row["is_revert_subject"] for row in enriched),
            "module_commit_counts": dict(module_counts.most_common()),
        },
        "commits": enriched,
        "representative_commits": rep_rows,
        "interpretation_limits": [
            "activity volume is not contribution value",
            "Git alone does not prove business impact or external use",
            "squash, migration, shared identities and missing refs may limit attribution",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--since", default="")
    parser.add_argument("--until", default="")
    parser.add_argument("--identity", action="append", default=[])
    parser.add_argument("--max-commits", type=int, default=2000)
    parser.add_argument("--representative-count", type=int, default=8)
    parser.add_argument("--patch-chars", type=int, default=20000)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()
    result = collect(
        args.repo, args.since, args.until, args.identity,
        args.max_commits, args.representative_count, args.patch_chars,
    )
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
