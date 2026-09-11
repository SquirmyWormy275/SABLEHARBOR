"""Reperform the three public reference scenarios and preserve every conclusion."""

import json
from pathlib import Path

from enterprise.ccf.registry import ROOT, validate
from enterprise.ccf.workflow import advance, close, collect, open_exception, remediate, review


def load(repository=ROOT):
    source = json.loads((Path(repository) / "enterprise/ccf/source/examples.json").read_text())
    if (
        source["schema_version"] != "0.1.0"
        or source["classification"] != "PUBLIC_SYNTHETIC_EXERCISE"
    ):
        raise ValueError("Unsupported exercise source")
    if set(source) != {"schema_version", "classification", "actors", "cases"}:
        raise ValueError("Unknown exercise source fields")
    for actor in source["actors"]:
        if set(actor) != {"id", "permissions", "boundaries", "effective_from", "effective_to"}:
            raise ValueError("Unknown actor fields")
        if not set(actor["permissions"]) <= {"prepare", "review", "approve"}:
            raise ValueError("Unknown actor permission")
    for case in source["cases"]:
        if set(case) != {
            "id",
            "kind",
            "boundary_id",
            "implementation_id",
            "period_start",
            "period_end",
            "scenario",
            "origin",
            "expected_ids",
            "tables",
            "negative_tables",
            "withheld_table",
        }:
            raise ValueError("Unknown exercise contract fields")
    ids = [r["id"] for r in source["actors"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate actor subject")
    ids = [r["id"] for r in source["cases"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate exercise ID")
    return source


def run(registry, repository=ROOT):
    validate(registry, repository)
    source = load(repository)
    implementations = {
        r["id"]: r["data"] for r in registry["records"] if r["kind"] == "implementation"
    }
    output = []
    for case in source["cases"]:
        implementation = implementations[case["implementation_id"]]
        if case["boundary_id"] not in implementation["boundary_ids"]:
            raise ValueError("Exercise outside local implementation boundary")
        actors = source["actors"]
        passing = collect(case, actors, "SYN-PREPARER", "2027-04-01")
        negative = collect(
            case, actors, "SYN-PREPARER", "2027-04-01", tables=case["negative_tables"]
        )
        missing = collect(
            case,
            actors,
            "SYN-PREPARER",
            "2027-04-01",
            attachments=set(case["tables"]) - {case["withheld_table"]},
        )
        reviewed = review(missing, actors, "SYN-REVIEWER", "2027-04-02")
        exception = open_exception(
            missing,
            actors,
            "SYN-REVIEWER",
            "2027-04-02",
            "2027-04-05",
            "Required attachment withheld in the public exercise",
            "Incomplete evidence prevents assessment",
            "Preserve scoped source rows and independent review; no effectiveness assertion",
        )
        expired = advance(exception, "2027-04-06")
        pending = remediate(
            expired, actors, "SYN-PREPARER", "2027-04-07", "SYN-RESTORE-ORIGINAL-ATTACHMENT"
        )
        retest = collect(case, actors, "SYN-PREPARER", "2027-04-08")
        try:
            close(pending, retest, actors, "SYN-PREPARER", "2027-04-09")
        except ValueError:
            self_review = "REJECTED"
        else:
            raise ValueError("Self review unexpectedly accepted")
        closed = close(pending, retest, actors, "SYN-REVIEWER", "2027-04-09")
        if (passing["outcome"], negative["outcome"], missing["outcome"], closed["state"]) != (
            "PASS",
            "FAIL",
            "NOT_RUN",
            "CLOSED",
        ):
            raise ValueError(f"Exercise does not demonstrate its required states: {case['id']}")
        output.append(
            dict(
                case_id=case["id"],
                passing=passing,
                negative=negative,
                missing=missing,
                review=reviewed,
                expired=expired,
                self_review=self_review,
                closed=closed,
            )
        )
    if {r["kind"] for r in source["cases"]} != {"finance", "identity", "recovery"}:
        raise ValueError("Required example coverage changed")
    return dict(
        classification="PUBLIC_SYNTHETIC_EXERCISE",
        operating_effectiveness="NOT_ASSERTED",
        cases=output,
    )
