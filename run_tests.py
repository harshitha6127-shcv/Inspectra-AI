"""
run_tests.py - Test Runner for Defect Detection Test Suite (Prompt 15)
======================================================================
Can be executed directly via:
    pytest -v
or:
    python3 run_tests.py
"""

import sys
import os

# Set up paths
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")
TESTS_DIR = os.path.join(ROOT_DIR, "tests")

for p in [ROOT_DIR, SRC_DIR, TESTS_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

print("=" * 72)
print("  VISION-BASED DEFECT DETECTION — AUTOMATED TEST SUITE (Prompt 15)")
print("  Target modules: src/preprocessing.py, src/severity.py, src/pipeline.py, src/app.py")
print("=" * 72)

try:
    import pytest
    print("\nRunning test suite using pytest...\n")
    ret_code = pytest.main(["-v", "tests"])
    sys.exit(ret_code)
except ImportError:
    print("\n[NOTE] 'pytest' package not found in current Python environment.")
    print("Running tests via Python's built-in 'unittest' discovery...\n")
    import unittest
    loader = unittest.TestLoader()
    suite = loader.discover("tests", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
