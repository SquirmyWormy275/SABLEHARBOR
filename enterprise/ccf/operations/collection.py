"""Reviewable census/intake packets and durable, restart-safe scheduled collection."""

import argparse
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from enterprise.ccf.registry import canonical, digest

from .connectors import collect
from .testing import instant, nonempty


def prepare_packets(
    evidence_config, census_config, excluded_ids, exclusion_rationale, captured_at, expires_at
):
    if (
        evidence_config.get("purpose", "evidence") != "evidence"
        or census_config.get("purpose") != "census"
    ):
        raise ValueError("Separate evidence and census connectors required")
    if evidence_config["source_system"] != census_config["source_system"]:
        raise ValueError("Source system mismatch")
    if instant(captured_at) >= instant(expires_at) or instant(captured_at) < instant(
        evidence_config["scope"]["period_end"]
    ):
        raise ValueError("Invalid collection chronology")
    # This attestation is a reviewer input, never inferred from two paths or exports.
    independence = nonempty(census_config["independence_basis"])
    evidence, census = collect(evidence_config), collect(census_config)
    ep, cp = evidence["provenance"], census["provenance"]
    if ep["locator"] == cp["locator"] and ep["query"] == cp["query"]:
        raise ValueError("Census requires a separately identified extraction")
    ids = [r["id"] for r in census["records"]]
    excluded = set(excluded_ids)
    if len(excluded) != len(excluded_ids) or not excluded <= set(ids):
        raise ValueError("Exclusions must be distinct census IDs")
    if excluded:
        nonempty(exclusion_rationale)
    expected = sorted(set(ids) - excluded)
    observed = {r["id"] for r in evidence["records"]}
    raw_census = canonical(ids)
    reconciliation = dict(
        missing_ids=sorted(set(expected) - observed),
        unexpected_ids=sorted(observed - set(expected)),
        source_count=len(ids),
        excluded_count=len(excluded),
        expected_count=len(expected),
        observed_count=len(observed),
    )
    reconciled = (
        bool(expected)
        and not reconciliation["missing_ids"]
        and not reconciliation["unexpected_ids"]
    )
    population = dict(
        expected_ids=expected,
        excluded_ids=sorted(excluded),
        source_count=len(ids),
        source_system=cp["source_system"],
        query=cp["query"],
        census_json=raw_census,
        source_export_sha256=hashlib.sha256(raw_census.encode()).hexdigest(),
        captured_at=captured_at,
        exclusion_rationale=exclusion_rationale,
        reconciliation=canonical(reconciliation),
        criteria_review="",
        independence_basis=independence,
    )
    intake = dict(
        raw_json=canonical(evidence["records"]),
        source_system=ep["source_system"],
        extraction_query=ep["query"],
        transformation_version=ep["transformation_version"],
        captured_at=captured_at,
        expires_at=expires_at,
        manual_tests={},
    )
    return dict(
        schema_version=1,
        status="DRAFT_REQUIRES_INDEPENDENT_POPULATION_REVIEW",
        test_outcome="NOT_RUN",
        ready_for_review=reconciled,
        population=population,
        intake=intake,
        reconciliation=reconciliation,
        provenance=dict(evidence=ep, census=cp),
        required_review=[
            "Validate census independence against source-system extraction authority; distinct paths alone do not establish independence",
            "Review scope, exclusions and criteria; populate criteria_review before independent population registration",
            "Prepare and independently review applicable manual criteria; collection does not run or approve control tests",
        ],
    )


def _private_write(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(canonical(value))
        handle.flush()
        os.fsync(handle.fileno())


def run_job(config, state_path, output_dir, at=None):
    """Run a due schedule slot once; failed collection remains retryable.

    Uses an immediate transaction to serialize workers. A committed artifact is
    retained by content hash. Crash-created orphan files are validated on retry.
    Run from an external scheduler; this function deliberately does not sleep.
    """
    now = instant(at or datetime.now(timezone.utc).isoformat())
    start = instant(config["schedule_start"])
    interval = config["interval_seconds"]
    if type(interval) is not int or interval < 60:
        raise ValueError("Schedule interval must be integer >= 60 seconds")
    if now < start:
        return dict(status="NOT_DUE", ready_for_review=False)
    key = nonempty(config["id"])
    slot = int((now - start).total_seconds()) // interval
    state_path, output_dir = Path(state_path), Path(output_dir)
    if state_path.is_symlink() or (
        state_path.exists() and (not state_path.is_file() or state_path.stat().st_mode & 0o077)
    ):
        raise ValueError("Scheduler database must be private and regular")
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    if output_dir.is_symlink() or output_dir.stat().st_mode & 0o077:
        raise ValueError("Artifact directory must be private")
    if not state_path.exists():
        fd = os.open(state_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
    db = sqlite3.connect(state_path, timeout=60)
    db.execute(
        "CREATE TABLE IF NOT EXISTS runs (job TEXT, slot INTEGER, config_hash TEXT, artifact TEXT, artifact_hash TEXT, PRIMARY KEY(job,slot))"
    )
    try:
        db.execute("BEGIN IMMEDIATE")
        prior = db.execute(
            "SELECT config_hash,artifact,artifact_hash FROM runs WHERE job=? AND slot=?",
            (key, slot),
        ).fetchone()
        config_hash = digest(config)
        if prior:
            if prior[0] != config_hash:
                raise ValueError(
                    "Job configuration changed within completed slot; use a new job ID"
                )
            path = output_dir / prior[1]
            if (
                path.is_symlink()
                or not path.is_file()
                or path.stat().st_mode & 0o077
                or hashlib.sha256(path.read_bytes()).hexdigest() != prior[2]
            ):
                raise ValueError("Committed collection artifact missing or altered")
            return dict(
                status="ALREADY_COLLECTED",
                slot=slot,
                artifact=str(path),
                ready_for_review=json.loads(path.read_text())["ready_for_review"],
            )
        packet = prepare_packets(
            config["evidence"],
            config["census"],
            config.get("excluded_ids", []),
            config.get("exclusion_rationale", ""),
            now.isoformat(),
            config["expires_at"],
        )
        packet["schedule"] = dict(job=key, slot=slot, config_digest=config_hash)
        content_hash = hashlib.sha256(canonical(packet).encode()).hexdigest()
        filename = content_hash + ".json"
        path = output_dir / filename
        if path.exists():
            if (
                path.is_symlink()
                or not path.is_file()
                or path.stat().st_mode & 0o077
                or hashlib.sha256(path.read_bytes()).hexdigest() != content_hash
            ):
                raise ValueError("Collection artifact collision")
        else:
            _private_write(path, packet)
        if not packet["ready_for_review"]:
            # Keep the private attempted packet, but leave this schedule slot retryable.
            return dict(
                status="RECONCILIATION_FAILED",
                slot=slot,
                artifact=str(path),
                ready_for_review=False,
                retryable=True,
            )
        db.execute(
            "INSERT INTO runs VALUES (?,?,?,?,?)", (key, slot, config_hash, filename, content_hash)
        )
        db.commit()
        return dict(
            status="COLLECTED",
            slot=slot,
            artifact=str(path),
            ready_for_review=packet["ready_for_review"],
        )
    finally:
        db.close()


def config_template(evidence_path, census_path, scope):
    """Explicit placeholders; caller must supply independently sourced census facts."""
    return dict(
        id="reference-collection",
        schedule_start="2026-09-10T10:00:00+00:00",
        interval_seconds=3600,
        expires_at="2026-10-01T00:00:00+00:00",
        excluded_ids=[],
        exclusion_rationale="",
        evidence=dict(
            type="local_json",
            purpose="evidence",
            path=str(evidence_path),
            source_system="DEMO-SOURCE",
            query="DEMO event export",
            scope=scope,
        ),
        census=dict(
            type="local_json",
            purpose="census",
            path=str(census_path),
            source_system="DEMO-SOURCE",
            query="DEMO separate authoritative roster export",
            independence_basis="SYNTHETIC demonstration only; reviewer must establish actual independence",
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_job(json.loads(args.config.read_text()), args.state, args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
