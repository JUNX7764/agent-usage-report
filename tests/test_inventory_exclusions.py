#!/usr/bin/env python3
"""Unit tests for inventory.py exclusion logic."""

import unittest
from pathlib import Path
import tempfile
import shutil
import sys

# Add scripts to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from inventory import inventory, should_exclude_file, EXCLUDE_PATTERNS


class TestInventoryExclusions(unittest.TestCase):
    """Test that exclusion logic works correctly."""
    
    def setUp(self):
        """Create temporary test directory structure."""
        self.test_dir = Path(tempfile.mkdtemp())
        
        # Create important files that should NOT be excluded
        (self.test_dir / "README.md").write_text("readme")
        (self.test_dir / "AGENTS.md").write_text("agents")
        (self.test_dir / "package.json").write_text("{}")
        (self.test_dir / "requirements.txt").write_text("pytest")
        (self.test_dir / "main.py").write_text("print('hello')")
        
        # Create noise directories with files that SHOULD be excluded
        (self.test_dir / "node_modules").mkdir()
        (self.test_dir / "node_modules" / "package.json").write_text("{}")
        
        (self.test_dir / ".venv").mkdir()
        (self.test_dir / ".venv" / "lib.py").write_text("lib")
        
        (self.test_dir / "__pycache__").mkdir()
        (self.test_dir / "__pycache__" / "main.cpython-311.pyc").write_text("bytecode")
        
        (self.test_dir / ".next").mkdir()
        (self.test_dir / ".next" / "build.js").write_text("build")
        
        (self.test_dir / "dist").mkdir()
        (self.test_dir / "dist" / "bundle.js").write_text("bundle")
        
        # Create nested structure
        src_dir = self.test_dir / "src"
        src_dir.mkdir()
        (src_dir / "index.js").write_text("code")
        (src_dir / "utils.py").write_text("utils")
        
        # Create files that should be excluded by pattern
        (self.test_dir / "test.pyc").write_text("bytecode")
        (self.test_dir / ".DS_Store").write_text("macos")
    
    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.test_dir)
    
    def test_important_files_not_excluded(self):
        """Verify that important project files are NOT excluded."""
        result = inventory(self.test_dir)
        
        scanned_paths = {f["relative_path"] for f in result["files"]}
        
        # These must be present
        self.assertIn("README.md", scanned_paths)
        self.assertIn("AGENTS.md", scanned_paths)
        self.assertIn("package.json", scanned_paths)
        self.assertIn("requirements.txt", scanned_paths)
        self.assertIn("main.py", scanned_paths)
        self.assertIn("src/index.js", scanned_paths)
        self.assertIn("src/utils.py", scanned_paths)
    
    def test_noise_directories_excluded(self):
        """Verify that noise directories are excluded."""
        result = inventory(self.test_dir)
        
        scanned_paths = {f["relative_path"] for f in result["files"]}
        
        # These should NOT be present
        self.assertNotIn("node_modules/package.json", scanned_paths)
        self.assertNotIn(".venv/lib.py", scanned_paths)
        self.assertNotIn("__pycache__/main.cpython-311.pyc", scanned_paths)
        self.assertNotIn(".next/build.js", scanned_paths)
        self.assertNotIn("dist/bundle.js", scanned_paths)
    
    def test_pattern_exclusions(self):
        """Verify that file patterns are excluded."""
        result = inventory(self.test_dir)
        
        scanned_paths = {f["relative_path"] for f in result["files"]}
        
        # Pattern-based exclusions
        self.assertNotIn("test.pyc", scanned_paths)
        self.assertNotIn(".DS_Store", scanned_paths)
    
    def test_should_exclude_file_function(self):
        """Test the pattern matching function directly."""
        # Should match
        self.assertTrue(should_exclude_file("test.pyc", EXCLUDE_PATTERNS))
        self.assertTrue(should_exclude_file(".DS_Store", EXCLUDE_PATTERNS))
        self.assertTrue(should_exclude_file("foo.egg-info/PKG-INFO", EXCLUDE_PATTERNS))
        
        # Should NOT match
        self.assertFalse(should_exclude_file("README.md", EXCLUDE_PATTERNS))
        self.assertFalse(should_exclude_file("main.py", EXCLUDE_PATTERNS))
        self.assertFalse(should_exclude_file("src/index.js", EXCLUDE_PATTERNS))
    
    def test_skip_reasons_recorded(self):
        """Verify that skip reasons are properly recorded."""
        result = inventory(self.test_dir)
        
        skip_reasons = {item["reason"] for item in result["skipped"]}
        
        # Should have these skip reasons
        self.assertIn("excluded_directory", skip_reasons)
        self.assertIn("excluded_by_pattern", skip_reasons)
    
    def test_file_count_accuracy(self):
        """Verify file count matches actual scanned files."""
        result = inventory(self.test_dir)
        
        # Should scan exactly 7 important files
        # README.md, AGENTS.md, package.json, requirements.txt, main.py, 
        # src/index.js, src/utils.py
        self.assertEqual(result["file_count"], 7)


if __name__ == "__main__":
    unittest.main()
