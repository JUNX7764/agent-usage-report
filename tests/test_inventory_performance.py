#!/usr/bin/env python3
"""Performance test for inventory.py optimization."""

import sys
import time
from pathlib import Path

# Add scripts to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from inventory import inventory, DEFAULT_EXCLUDES


def benchmark_inventory(root: Path, label: str) -> dict:
    """Run inventory and measure performance."""
    print(f"\n{'='*60}")
    print(f"Benchmarking: {label}")
    print(f"Root: {root}")
    print(f"{'='*60}")
    
    start = time.time()
    result = inventory(root)
    elapsed = time.time() - start
    
    print(f"✓ Completed in {elapsed:.2f}s")
    print(f"  Files scanned: {result['file_count']:,}")
    print(f"  Files skipped: {len(result['skipped']):,}")
    print(f"  Total size: {result['total_size_bytes'] / (1024**2):.2f} MB")
    print(f"  Excluded directories: {len(DEFAULT_EXCLUDES)}")
    
    # Show breakdown of skipped reasons
    skip_reasons = {}
    for item in result['skipped']:
        reason = item['reason']
        skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
    
    if skip_reasons:
        print(f"\n  Skip breakdown:")
        for reason, count in sorted(skip_reasons.items(), key=lambda x: -x[1]):
            print(f"    - {reason}: {count:,}")
    
    return {
        'elapsed': elapsed,
        'file_count': result['file_count'],
        'skipped_count': len(result['skipped']),
        'total_size': result['total_size_bytes'],
        'skip_reasons': skip_reasons,
    }


def main():
    """Run performance comparison."""
    print("Inventory Performance Test")
    print("=" * 60)
    
    # Test on current project
    project_root = Path(__file__).parent.parent.parent.parent
    print(f"\nTest root: {project_root}")
    
    if not project_root.exists():
        print("ERROR: Project root not found")
        return 1
    
    # Run benchmark
    stats = benchmark_inventory(project_root, "Optimized inventory.py")
    
    # Performance report
    print(f"\n{'='*60}")
    print("PERFORMANCE SUMMARY")
    print(f"{'='*60}")
    print(f"Scan time: {stats['elapsed']:.2f}s")
    print(f"Files processed: {stats['file_count']:,}")
    print(f"Items skipped: {stats['skipped_count']:,}")
    print(f"Data size: {stats['total_size'] / (1024**2):.2f} MB")
    
    if stats['elapsed'] > 180:  # 3 minutes
        print(f"\n⚠ WARNING: Scan took longer than 3 minutes")
    elif stats['elapsed'] < 60:  # 1 minute
        print(f"\n✓ EXCELLENT: Scan completed in under 1 minute")
    else:
        print(f"\n✓ GOOD: Scan completed in under 3 minutes")
    
    # Expected performance gain
    print(f"\nExpected improvement from optimization:")
    print(f"  Before: ~10 minutes (estimated)")
    print(f"  After: {stats['elapsed']:.2f}s")
    if stats['elapsed'] > 0:
        speedup = 600 / stats['elapsed']  # 10 min = 600s
        print(f"  Speedup: ~{speedup:.1f}x faster")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
