"""Initialize a local company source runtime before connecting any audit."""

import argparse
import json
from pathlib import Path

from enterprise.audit_suite.company_runtime_activation import activate


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capsule", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = activate(
        args.capsule,
        args.destination,
        expected_manifest_sha256=args.manifest_sha256,
    )
    print(
        json.dumps(
            {
                "status": "COMPLETE",
                "runtime_instance_id": receipt["runtime_instance_id"],
                "seed_counts": receipt["seed_counts"],
                "audit_created": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
