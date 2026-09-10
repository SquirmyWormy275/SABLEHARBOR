#!/usr/bin/env python3
"""Export the approved organization chart publication and supporting records."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parents[1] / "tools/organization/export_charts.py"), run_name="__main__")
