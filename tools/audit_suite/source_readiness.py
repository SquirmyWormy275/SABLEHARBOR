"""Operator-only explicit source inventory; inputs and populated reports stay private."""

import sys

if __name__ == "__main__" and sys.path:
    sys.path.pop(0)  # Avoid shadowing the standard-library operator module.

import argparse
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from enterprise.audit_suite.source_readiness import load_config, write_inventory  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = write_inventory(load_config(args.config), args.output)
    print(json.dumps({"output": str(args.output), "summary": result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
