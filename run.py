#!/usr/bin/env python3
"""Entry point for PyInstaller executable."""

import sys
from pathlib import Path

# Add src directory to Python path to enable imports
src_path = Path(__file__).parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

from electricity_outage_checker.cli import main

if __name__ == "__main__":
    main()
