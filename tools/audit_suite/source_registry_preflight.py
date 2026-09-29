"""Print a read-only paired source-registry census; never activate an audit."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from enterprise.audit_suite.company_federation import FederatedCompanyStore  # noqa: E402
from enterprise.audit_suite.source_registry_preflight import analyze, read_state  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "audit_a",
        "audit_b",
        "screen",
        "task_routes",
        "control_routes",
        "source_families",
        "registry_a",
        "registry_b",
    ):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    parser.add_argument("--profile-a", required=True)
    parser.add_argument("--profile-b", required=True)
    args = parser.parse_args()
    report = analyze(
        {"A": read_state(args.audit_a), "B": read_state(args.audit_b)},
        json.loads(args.screen.read_text())["rows"],
        json.loads(args.task_routes.read_text()),
        json.loads(args.control_routes.read_text()),
        json.loads(args.source_families.read_text()),
        {
            "A": FederatedCompanyStore(args.registry_a, args.profile_a),
            "B": FederatedCompanyStore(args.registry_b, args.profile_b),
        },
    )
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
