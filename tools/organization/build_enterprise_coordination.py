"""Publish current role/contact routes without private control answers."""

import json
from pathlib import Path
from enterprise.audit_suite.organization import snapshot

ROOT = Path(__file__).resolve().parents[2]


def build():
    value = snapshot(ROOT)
    return {
        "record_id": "SH-CONTROL-COORDINATION-20260913",
        "version": "1.0.0",
        "effective_from": "2026-09-13",
        "status": value["repository_acceptance_status"],
        "decision": "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md",
        "authority": "docs/governance/ENTERPRISE_COORDINATION_2026-09-13.md",
        "scope_limit": "Enterprise contact routes; local operating boundary and period require explicit binding",
        "source_sha256": value["source_sha256"],
        "assignments": value["control_assignments"],
    }


if __name__ == "__main__":
    path = ROOT / "docs/structured/enterprise_control_coordination_2026-09-13.json"
    path.write_text(json.dumps(build(), indent=2) + "\n")
    print("Published 166 public role/contact routes; no private evidence or answers")
