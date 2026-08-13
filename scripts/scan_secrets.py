#!/usr/bin/env python3
"""Scan authorized local text files for likely secrets without echoing values."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Iterable

MAX_FILE_BYTES = 2 * 1024 * 1024
PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "openai_like_key": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\bgh[opusr]_[A-Za-z0-9]{20,}\b"),
    "generic_secret_assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|token|password|passwd|secret)\b\s*[:=]\s*['\"]?([^\s'\"]{8,})"
    ),
}
BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".doc", ".docx",
    ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".gz", ".mp3", ".mp4",
    ".mov", ".avi", ".sqlite", ".db", ".pyc",
}
DEFAULT_EXCLUDES = {".git", "node_modules", ".venv", "__pycache__"}


def iter_text_files(root: Path, excludes: Iterable[str] = ()):
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
            yield path


def scan(root: Path, excludes: Iterable[str] = ()) -> dict:
    root = root.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"not a directory: {root}")
    findings = []
    scanned = 0
    for path in iter_text_files(root, excludes):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        scanned += 1
        for line_number, line in enumerate(text.splitlines(), start=1):
            for kind, pattern in PATTERNS.items():
                for match in pattern.finditer(line):
                    value = match.group(1) if match.lastindex else match.group(0)
                    findings.append(
                        {
                            "relative_path": path.relative_to(root).as_posix(),
                            "line": line_number,
                            "kind": kind,
                            "redacted": f"<redacted:{len(value)} chars>",
                        }
                    )
    return {
        "schema_version": "1.0",
        "root": str(root),
        "scanned_text_files": scanned,
        "finding_count": len(findings),
        "findings": findings,
        "full_values_returned": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--fail-on-findings", action="store_true")
    args = parser.parse_args()
    
    # Print friendly progress message
    if args.output:
        print("  ✓ 密钥检查完成", end="", flush=True)
    
    result = scan(args.root, args.exclude)
    
    if args.output and result["finding_count"] > 0:
        print(f"（找到 {result['finding_count']} 处敏感信息，已脱敏）")
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
