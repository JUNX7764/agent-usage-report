#!/usr/bin/env python3
"""Create a read-only file inventory for one authorized root."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable, Optional

# Common noise directories that should be skipped to improve performance
DEFAULT_EXCLUDES = {
    # Version control
    ".git", ".svn", ".hg",
    # Python
    "venv", ".venv", "env", ".env", "__pycache__", ".pytest_cache",
    ".tox", ".mypy_cache", ".ruff_cache", "eggs", ".eggs",
    "dist", "build", ".eggs",
    # Node.js
    "node_modules", ".next", ".nuxt", "out", ".output", ".cache",
    # Rust/Java
    "target",
    # Go/PHP
    "vendor",
    # IDE/Editors
    ".vscode", ".idea", ".vs",
    # Coverage
    "coverage", ".coverage", "htmlcov", ".nyc_output",
    # macOS
    ".DS_Store",
    # Temporary
    "tmp", "temp", ".tmp",
}

# Glob patterns for additional filtering (applied to relative paths)
EXCLUDE_PATTERNS = [
    "*.pyc",
    "*.pyo",
    "*.so",
    "*.dylib",
    "*.dll",
    "*.egg-info/*",
    ".DS_Store",
]

# Regex patterns for extracting dates from filenames
DATE_PATTERNS = [
    (r"(\d{4})(\d{2})(\d{2})", "%Y%m%d"),           # 20260608
    (r"(\d{4})-(\d{2})-(\d{2})", "%Y-%m-%d"),       # 2026-06-08
    (r"(\d{4})\.(\d{2})\.(\d{2})", "%Y.%m.%d"),    # 2026.06.08
    (r"(\d{4})_(\d{2})_(\d{2})", "%Y_%m_%d"),       # 2026_06_08
    (r"(\d{4})(\d{2})", "%Y%m"),                     # 202606
]


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def extract_date_from_filename(filename: str) -> Optional[str]:
    """Extract date string from filename using common patterns.
    
    Returns ISO-8601 date string (YYYY-MM-DD) if found, else None.
    Examples:
        "20260608-report.docx" -> "2026-06-08"
        "report-2026-06-08.pdf" -> "2026-06-08"
        "summary_20260608.txt" -> "2026-06-08"
    """
    for pattern, fmt in DATE_PATTERNS:
        match = re.search(pattern, filename)
        if match:
            try:
                # Reconstruct date parts
                groups = match.groups()
                if len(groups) == 3:  # Year, month, day
                    year, month, day = groups
                    # Basic validation
                    y, m, d = int(year), int(month), int(day)
                    if 1900 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31:
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                elif len(groups) == 2:  # Year, month only
                    year, month = groups
                    y, m = int(year), int(month)
                    if 1900 <= y <= 2100 and 1 <= m <= 12:
                        return f"{year}-{month.zfill(2)}"
            except (ValueError, IndexError):
                continue
    return None


def extract_birth_date(path: Path) -> Optional[str]:
    """Extract filesystem creation/birth date if available.
    
    On macOS, st_birthtime is available; on Windows, os.path.getctime
    is a reasonable fallback. On Linux, many filesystems do not expose
    a stable creation time; this function returns None in that case.
    
    Returns ISO-8601 date string (YYYY-MM-DD) or None.
    """
    try:
        stat = path.stat()
        birth_ts = None
        if hasattr(stat, "st_birthtime"):
            birth_ts = stat.st_birthtime
        elif os.name == "nt":
            birth_ts = os.path.getctime(path)
        if birth_ts:
            from datetime import datetime, timezone
            dt = datetime.fromtimestamp(birth_ts, tz=timezone.utc)
            dt_local = dt.astimezone()
            return dt_local.strftime("%Y-%m-%d")
    except (OSError, AttributeError, ValueError):
        pass
    return None


def extract_extracted_date(path: Path) -> tuple[Optional[str], Optional[str]]:
    """Return (date, source) where source is 'filename' or 'filesystem_birth'.
    
    Priority:
    1. Date embedded in the filename (most reliable internal evidence).
    2. Filesystem creation/birth time (if accessible on the platform).
    """
    filename_date = extract_date_from_filename(path.name)
    if filename_date:
        return filename_date, "filename"
    
    birth_date = extract_birth_date(path)
    if birth_date:
        return birth_date, "filesystem_birth"
    
    return None, None


def should_exclude_file(rel_path: str, patterns: list[str]) -> bool:
    """Check if a file should be excluded based on glob patterns."""
    for pattern in patterns:
        if fnmatch(rel_path, pattern):
            return True
    return False


def inventory(root: Path, excludes: Iterable[str] = ()) -> dict:
    root = root.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"not a directory: {root}")

    excluded = DEFAULT_EXCLUDES | set(excludes)
    files: list[dict] = []
    skipped: list[dict] = []
    total_size = 0

    for current, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept_dirs = []
        for name in sorted(dirnames):
            child = current_path / name
            rel = child.relative_to(root).as_posix()
            if name in excluded:
                skipped.append({"relative_path": rel, "reason": "excluded_directory"})
            elif child.is_symlink():
                skipped.append({"relative_path": rel, "reason": "symlink_directory_not_followed"})
            else:
                kept_dirs.append(name)
        dirnames[:] = kept_dirs

        for name in sorted(filenames):
            path = current_path / name
            rel = path.relative_to(root).as_posix()
            
            # Check against exclude patterns
            if should_exclude_file(rel, EXCLUDE_PATTERNS):
                skipped.append({"relative_path": rel, "reason": "excluded_by_pattern"})
                continue
            
            if path.is_symlink():
                skipped.append({"relative_path": rel, "reason": "symlink_file_not_read"})
                continue
            if not path.is_file():
                skipped.append({"relative_path": rel, "reason": "not_regular_file"})
                continue
            stat = path.stat()
            total_size += stat.st_size
            
            # Extract date from filename or filesystem birth time if accessible
            extracted_date, date_source = extract_extracted_date(path)
            
            file_info = {
                "relative_path": rel,
                "size_bytes": stat.st_size,
                "suffix": path.suffix.lower(),
                "sha256": sha256_file(path),
            }
            
            if extracted_date:
                file_info["extracted_date"] = extracted_date
                file_info["extracted_date_source"] = date_source
            
            files.append(file_info)

    return {
        "schema_version": "1.0",
        "root": str(root),
        "source_read_only": True,
        "file_count": len(files),
        "total_size_bytes": total_size,
        "files": files,
        "skipped": skipped,
        "note": (
            "Filesystem mtime is intentionally not treated as evidence time. "
            "extracted_date comes from filename or filesystem birth time when available."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--exclude", action="append", default=[])
    args = parser.parse_args()

    # Print friendly progress message
    root_name = args.root.name if args.root.name else args.root
    if args.output:
        print(f"正在翻「{root_name}」...", end=" ", flush=True)
    
    result = inventory(args.root, args.exclude)
    
    if args.output:
        print("✓ 文件清单完成")
    
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
