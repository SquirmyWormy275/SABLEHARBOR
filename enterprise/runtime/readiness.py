"""Validated diligence register. Missing external evidence remains a typed gate."""

import json
from pathlib import Path


def load():
    data = json.loads(Path(__file__).with_name("readiness.json").read_text())
    if (
        set(data) != {"version", "as_of", "sources", "gates"}
        or data["version"] != "1.0.0"
    ):
        raise ValueError("Invalid readiness register schema")
    known = set()
    for source in data["sources"]:
        fields = {
            "id",
            "publisher",
            "title",
            "url",
            "retrieved_on",
            "published_on",
            "facility_scope",
            "claim",
            "field_references",
            "evidence_class",
            "conflicts",
            "limitations",
            "refresh_owner",
        }
        if (
            set(source) != fields
            or not source["url"].startswith("https://")
            or not source["field_references"]
        ):
            raise ValueError("Invalid field-level reference")
        if source["id"] in known:
            raise ValueError("Duplicate source")
        known.add(source["id"])
        if source["evidence_class"] != "PUBLIC_REFERENCE_NOT_ACCEPTED_EVIDENCE":
            raise ValueError("Public source cannot assert accepted assurance")
    known = set()
    for gate in data["gates"]:
        fields = {
            "id",
            "owner",
            "scope",
            "state",
            "required_evidence",
            "evidence_refs",
            "operating_effectiveness",
            "next_review",
        }
        if set(gate) != fields or any(
            not gate[k] for k in ("owner", "scope", "required_evidence", "next_review")
        ):
            raise ValueError("Incomplete readiness gate")
        if gate["id"] in known:
            raise ValueError("Duplicate gate")
        known.add(gate["id"])
        if (
            gate["state"] != "BLOCKED_EVIDENCE_NOT_OBTAINED"
            or gate["evidence_refs"]
            or gate["operating_effectiveness"] != "NOT_ASSERTED"
        ):
            raise ValueError(
                "No external acceptance is evidenced in this register version"
            )
    return data
