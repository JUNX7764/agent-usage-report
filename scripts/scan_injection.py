#!/usr/bin/env python3
"""Scan authorized project files for potential prompt-injection patterns."""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import tokenize
from pathlib import Path
from typing import Iterable

MAX_FILE_BYTES = 2 * 1024 * 1024
CONTEXT_CHARS = 80

# Prompt-injection / manipulation patterns (case-insensitive)
PATTERNS = {
    "ignore_rules": re.compile(r"忽略.*规则|ignore.*rules|bypass.*rules", re.IGNORECASE),
    "grant_perfect_score": re.compile(r"给.*满分|full.*score|perfect.*score|最高.*分", re.IGNORECASE),
    "impersonate_reviewer": re.compile(r"你是.*评委|你是.*管理员|you are.*reviewer|you are.*admin|you are.*evaluator", re.IGNORECASE),
    "leak_materials": re.compile(r"泄露.*材料|reveal.*material|disclose.*submission|show.*other", re.IGNORECASE),
    "ignore_previous": re.compile(r"ignore.*previous.*instructions|忘记.*之前.*指示|disregard.*context", re.IGNORECASE),
    "override_system": re.compile(r"override.*system|覆盖.*系统|reset.*context|清除.*上下文", re.IGNORECASE),
}

# File types to scan for injection patterns
INJECTION_TARGET_SUFFIXES = {
    ".md",       # AGENTS.md, README.md, CLAUDE.md
    ".py",       # Code comments and docstrings
    ".yml",      # Aider/conf files
    ".yaml",     # Config files
    ".json",     # Settings / rules exported as JSON
    "",          # .cursorrules, .clinerules, .windsurfrules
}

# Config file names to always scan
CONFIG_NAMES = {
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    ".cursorrules",
    ".clinerules",
    ".windsurfrules",
    ".aider.conf.yml",
    ".aider.conf.yaml",
}

BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".doc", ".docx",
    ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".gz", ".mp3", ".mp4",
    ".mov", ".avi", ".sqlite", ".db", ".pyc",
}

DEFAULT_EXCLUDES = {".git", "node_modules", ".venv", "__pycache__", "dist", "build"}

TRIPLE_QUOTED_STRING_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"[fFrRuUbB]*"
    r"(\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?''')"
)


def should_scan_file(path: Path) -> bool:
    """Return True if the file should be scanned for injection patterns."""
    if path.name in CONFIG_NAMES:
        return True

    suffix = path.suffix.lower()
    if suffix in INJECTION_TARGET_SUFFIXES:
        return True

    # Scan dot-prefixed files without extension (e.g., .cursorrules)
    if suffix == "" and path.name.startswith("."):
        return True

    return False


def iter_text_files(root: Path, excludes: Iterable[str] = ()):
    """Iterate over text files that should be scanned for injection patterns."""
    excluded = DEFAULT_EXCLUDES | set(excludes)
    for current, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        dirnames[:] = [
            name for name in sorted(dirnames)
            if name not in excluded and not (current_path / name).is_symlink()
        ]
        for name in sorted(filenames):
            path = current_path / name
            if path.is_symlink() or not path.is_file():
                continue
            if path.suffix.lower() in BINARY_SUFFIXES or path.stat().st_size > MAX_FILE_BYTES:
                continue
            if should_scan_file(path):
                yield path


def extract_py_comments(text: str) -> list[tuple[int, str]]:
    """Extract single-line comments and triple-quoted strings from Python source.

    Triple-quoted strings are included because they are often used as module,
    class, function docstrings or as block-level comments.
    """
    snippets: list[tuple[int, str]] = []

    # Single-line comments via the tokenizer (safe for # inside strings).
    source = io.StringIO(text)
    try:
        for tok in tokenize.generate_tokens(source.readline):
            if tok.type == tokenize.COMMENT:
                snippets.append((tok.start[0], tok.string))
    except tokenize.TokenizeError:
        pass

    # Triple-quoted strings via regex.
    for match in TRIPLE_QUOTED_STRING_RE.finditer(text):
        start_line = text[: match.start()].count("\n") + 1
        value = match.group(1)
        content = value[3:-3]
        if content:
            snippets.append((start_line, content))

    return snippets


def scan(root: Path, excludes: Iterable[str] = ()) -> dict:
    """Scan directory for potential prompt-injection patterns."""
    root = root.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"not a directory: {root}")

    findings: list[dict] = []
    scanned = 0

    for path in iter_text_files(root, excludes):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        scanned += 1
        relative = path.relative_to(root).as_posix()

        if path.suffix.lower() == ".py":
            snippets = extract_py_comments(text)
            for base_line, snippet in snippets:
                for line_offset, line in enumerate(snippet.splitlines()):
                    line_number = base_line + line_offset
                    _scan_line(line, line_number, relative, findings)
        else:
            for line_number, line in enumerate(text.splitlines(), start=1):
                _scan_line(line, line_number, relative, findings)

    return {
        "schema_version": "1.0",
        "root": str(root),
        "scanned_files": scanned,
        "finding_count": len(findings),
        "suspicious_files": findings,
    }


def _scan_line(line: str, line_number: int, relative: str, findings: list[dict]) -> None:
    """Run all patterns against a single line and append matches."""
    for kind, pattern in PATTERNS.items():
        for match in pattern.finditer(line):
            start = max(0, match.start() - CONTEXT_CHARS // 2)
            end = min(len(line), match.end() + CONTEXT_CHARS // 2)
            context = line[start:end].strip()
            findings.append(
                {
                    "path": relative,
                    "line": line_number,
                    "pattern": kind,
                    "context": context,
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan for potential prompt-injection patterns in project files"
    )
    parser.add_argument("root", type=Path, help="Project root directory to scan")
    parser.add_argument("-o", "--output", type=Path, help="Output JSON file path")
    parser.add_argument("--exclude", action="append", default=[], help="Additional directories to exclude")
    parser.add_argument("--fail-on-findings", action="store_true", help="Exit with code 1 if findings detected")

    args = parser.parse_args()

    # Print friendly progress message
    if args.output:
        print("  ✓ 安全检查完成", end="", flush=True)
    
    result = scan(args.root, args.exclude)
    
    if args.output and result["finding_count"] > 0:
        print(f"（发现 {result['finding_count']} 处可疑模式）")
    elif args.output:
        print()
    
    text = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)

    return 1 if args.fail_on_findings and result["finding_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
