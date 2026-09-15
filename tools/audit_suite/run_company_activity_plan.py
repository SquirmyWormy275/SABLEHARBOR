"""Run a new private, explicitly ordered company activity plan; never creates an audit."""

import argparse
import json
from pathlib import Path

from enterprise.audit_suite.company_activity_plan import run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args(argv)
    result = run(args.plan, args.destination, repository=args.repository)
    print(
        json.dumps({"status": result["status"], "counts": result["counts"], "audit_created": False})
    )
    return 0 if result["status"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
