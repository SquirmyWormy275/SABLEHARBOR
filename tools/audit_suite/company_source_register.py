"""Create a private, read-only selected-source ownership and migration register."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from enterprise.audit_suite.company_source_register import write_register  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = write_register(
        args.config, args.output, repository=Path(__file__).resolve().parents[2]
    )
    print(json.dumps({"schema": result["schema"], "register_version": result["register_version"]}))


if __name__ == "__main__":
    main()
