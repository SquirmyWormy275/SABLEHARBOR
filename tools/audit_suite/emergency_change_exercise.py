"""Trusted local operator entry point for a new private SH-ENG-005 source pair."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from enterprise.audit_suite.company_emergency_change_activity import (  # noqa: E402
    EmergencyRecipe,
    generate_pair,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    expected = {"company", "clean_branch", "messy_branch", "exercise_id", "start_at", "local_rule"}
    if set(config) != expected:
        parser.error("Exact EmergencyRecipe fields required")
    repository = Path(__file__).resolve().parents[2]
    result = generate_pair(args.output, repository=repository, recipe=EmergencyRecipe(**config))
    print(
        json.dumps(
            {
                "status": result["status"],
                "record_count": result["record_count"],
                "audit_task_credit": result["audit_task_credit"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
