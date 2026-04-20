#!/usr/bin/env python3
"""Backward-compatible launcher for comprehensive API tests.

The test runner now lives in scripts/testing/run_comprehensive_tests.py.
This wrapper preserves existing commands and CI invocations.
"""

from pathlib import Path
import runpy


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    target = root / "scripts" / "testing" / "run_comprehensive_tests.py"
    runpy.run_path(str(target), run_name="__main__")
