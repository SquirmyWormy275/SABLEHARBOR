"""Versioned person aliases over the existing conditional workforce model.

Only identity labels change. The retained WorkforceMixin executes its original
position events and allocation arithmetic. No original source or financial release
is written, and no actual employment, hire date or facility occupancy is inferred.
"""

import csv
import hashlib
import io
import json
from decimal import Decimal
from pathlib import Path

from enterprise.ccf.registry import ROOT
from enterprise.operations.model import OperatingModel

ROSTER = "docs/structured/enterprise_leadership_2026-09-13.json"
HISTORY = "docs/finance/evidence/supporting-schedules/source/workforce_positions_history.csv"


class WorkforceProjection(OperatingModel):
    """Execute workforce allocation only; do not issue accounting entries."""

    def event(self, *args, **kwargs):
        return None

    def post(self, *args, **kwargs):
        return None

    def cost(self, *args, **kwargs):
        return None


def build(repository=ROOT):
    root = Path(repository)
    roster = json.loads((root / ROSTER).read_text())
    aliases = {p["forecast_position_id"]: p for p in roster["people"]}
    if len(aliases) != len(roster["people"]):
        raise ValueError("Duplicate position alias")
    inputs = {
        p.stem: json.loads(p.read_text())
        for p in sorted((root / "enterprise/business/source").glob("*.json"))
    }
    operations = {
        p.stem: json.loads(p.read_text())
        for p in sorted((root / "enterprise/operations/source").glob("*.json"))
    }
    rows, totals, events = [], [], []
    retained = list(csv.DictReader(io.StringIO((root / HISTORY).read_text())))
    retained_index = {
        (r["position_id"], int(r["month_index"])): r for r in retained if r["scenario"] == "base"
    }
    matched = 0
    for scenario in inputs["policy"]["cases"]:
        model = WorkforceProjection(inputs, operations)
        model.scenario = scenario
        model.case = model.policy["cases"][scenario]
        baseline_people = {r["position_id"]: r["person_id"] for r in model.roster}
        for position in aliases:
            if position not in baseline_people or not baseline_people[position]:
                raise ValueError("Alias requires an existing occupied model position")
        for month in range(1, 61):
            model.month = month
            model.workforce()
            history = model.tables["workforce_positions_history"][-len(model.roster) :]
            total = sum(Decimal(r["expected_loaded_cost_usd"]) for r in history)
            assigned = sum(
                Decimal(r["loaded_cost_usd"])
                for r in model.tables["workforce_assignments"]
                if r["month_index"] == month
            )
            if assigned != total:
                raise ValueError("Original allocation does not reconcile")
            for r in history:
                if scenario == "base" and month <= 12:
                    original = retained_index[(r["position_id"], month)]
                    if any(str(r[key]) != original[key] for key in original):
                        raise ValueError(
                            "Workforce projection differs from retained 2027 source row"
                        )
                    matched += 1
                if r["position_id"] in aliases:
                    person = aliases[r["position_id"]]
                    applicable = (
                        r["occupied"] and r["person_id"] == baseline_people[r["position_id"]]
                    )
                    rows.append(
                        {
                            **r,
                            "source_model_person_id": r["person_id"],
                            "person_id": person["person_id"] if applicable else r["person_id"],
                            "alias_status": "EXISTING_MODEL_PERSON_ALIAS"
                            if applicable
                            else "ALIAS_NOT_APPLICABLE_TO_REPLACEMENT_OR_VACANCY",
                            "appointment_effective_from": roster["effective_from"],
                            "employment_start": None,
                            "workplace_assignment": None,
                            "source_acceptance": roster["repository_acceptance_status"],
                        }
                    )
            totals.append(
                {
                    "scenario": scenario,
                    "period": history[0]["period"],
                    "authorized_before": len(history),
                    "authorized_after": len(history),
                    "occupied_before": sum(r["occupied"] for r in history),
                    "occupied_after": sum(r["occupied"] for r in history),
                    "loaded_cost_before_usd": str(total),
                    "loaded_cost_after_usd": str(total),
                    "allocation_total_usd": str(assigned),
                    "incremental_alias_cost_usd": "0.0000",
                    "fact_state": "CONDITIONAL_FORECAST_NOT_ACTUAL_EMPLOYMENT",
                }
            )
        events.extend(model.tables["workforce_changes"])
    source_paths = [
        ROSTER,
        roster["canonical_source"],
        HISTORY,
        "enterprise/business/model.py",
        "enterprise/operations/model.py",
        "enterprise/operations/workforce.py",
        "enterprise/operations/advisory_policy.py",
    ]
    source_paths += [
        str(p.relative_to(root))
        for folder in ("enterprise/business/source", "enterprise/operations/source")
        for p in sorted((root / folder).glob("*.json"))
    ]
    return {
        "record_id": "SH-WORKFORCE-IDENTITY-20260913",
        "version": "1.0.0",
        "status": "DATED_FICTIONAL_ALIAS_PENDING_ACCEPTED_MERGE",
        "horizon": {"start": "2027-01-01", "end": "2031-12-31"},
        "source_sha256": {
            p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in source_paths
        },
        "aliases": [
            {"person_id": p["person_id"], "position_id": key} for key, p in aliases.items()
        ],
        "monthly_alias_rows": rows,
        "monthly_reconciliation": totals,
        "preserved_workforce_events": events,
        "validation": {
            "retained_2027_base_rows_matched": matched,
            "retained_rows": len(retained_index),
            "identity_alias_count": len(aliases),
            "incremental_positions": 0,
            "incremental_payroll_usd": "0",
            "actual_employment_and_occupancy": "NOT_ESTABLISHED",
        },
    }


def write(repository=ROOT):
    root = Path(repository)
    result = build(root)
    path = root / "enterprise/business/identity/2026-09-13/REGISTER.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    value = write()
    print(json.dumps(value["validation"], sort_keys=True))
