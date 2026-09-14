"""Build a new protected instructor-key archive; never imports into a company store."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from enterprise.audit_suite.instructor_key import build_archive


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--definitions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build_archive(args.definitions, args.output), indent=2))


if __name__ == "__main__":
    main()
