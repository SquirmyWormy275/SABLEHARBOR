"""Trusted local, read-only source inventory. This is not a learner endpoint or audit verdict."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import stat
import subprocess
import tempfile
from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .company_store import _json as company_json
from .private_publication import publish
from .store import digest

SCHEMA = "SOURCE_READINESS_INVENTORY_V1"
IDENTITY = ("company", "branch", "system", "record", "version", "sha256")
DOCUMENTARY = {"MIGRATED_SYNTHETIC_HISTORY", "REPOSITORY_SYNTHETIC_DOCUMENT"}
QUALIFIERS = (
    "classification",
    "operational_fact_status",
    "custody_status",
    "custody_basis",
    "qualification",
    "forecast_status",
    "model_version",
    "event_time_state",
    "availability_basis",
    "source_authority",
    "source_scenario",
    "policy_basis",
    "provider_decision_state",
    "scope_mapping",
    "assignment_status",
)
PERIODS = (
    "source_period_start",
    "source_period_end",
    "period_start",
    "period_end",
    "period_end_exclusive",
)
LIMITATIONS = [
    (
        "Explicit source references do not establish procedure execution, population "
        "completeness, period coverage or effectiveness."
    ),
    (
        "Authored activity/reference sources are qualified exercises, not asserted "
        "actual company operations or independent corroboration."
    ),
    (
        "Stores and branches remain separate; database snapshots have different "
        "capture intervals and are not globally atomic."
    ),
    (
        "Historical collection receipts do not establish current grants, business "
        "accuracy or professional independence."
    ),
    (
        "Additional engagement work is separately identified and never credited to "
        "the target engagement."
    ),
    (
        "Only explicitly selected systems, branches and engagements are inventoried; "
        "unselected sources were not searched."
    ),
]


def _now():
    return datetime.now(UTC).isoformat()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _private(value, *, directory=False):
    path = Path(value)
    _require(path.is_absolute() and ".." not in path.parts, "Canonical absolute path required")
    _require(not any(p.is_symlink() for p in (path, *path.parents)), "Path aliases forbidden")
    st = path.stat()
    _require(stat.S_ISDIR(st.st_mode) if directory else stat.S_ISREG(st.st_mode), "Wrong path type")
    _require(not st.st_mode & 0o077, "Private path permissions required")
    if not directory:
        _require(st.st_nlink == 1, "Hard-linked input forbidden")
    return path


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def _json(raw):
    return json.loads(
        raw,
        object_pairs_hook=_pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")),
    )


def load_config(path):
    path = _private(path)
    _require(path.stat().st_size <= 1024 * 1024, "Configuration too large")
    return _json(path.read_bytes())


def _text(value):
    return isinstance(value, str) and 0 < len(value) <= 256


def _validate(config):
    _require(
        isinstance(config, dict) and set(config) == {"target", "audits", "sources"},
        "Exact config fields required",
    )
    audits = [config["target"], *config["audits"]] if isinstance(config["audits"], list) else []
    _require(1 <= len(audits) <= 32, "Select 1–32 audit snapshots")
    seen = set()
    for item in audits:
        _require(
            isinstance(item, dict) and set(item) == {"root", "engagement_id"},
            "Exact audit selector required",
        )
        _require(_text(item["engagement_id"]), "Invalid engagement ID")
        _private(item["root"], directory=True)
        key = (item["root"], item["engagement_id"])
        _require(key not in seen, "Duplicate audit selector")
        seen.add(key)
    sources = config["sources"]
    _require(isinstance(sources, list) and 1 <= len(sources) <= 64, "Select 1–64 source components")
    ids, routes = set(), set()
    for item in sources:
        _require(
            isinstance(item, dict)
            and set(item) == {"id", "root", "company", "branch", "systems", "category"},
            "Exact source selector required",
        )
        _require(
            all(_text(item[k]) for k in ("id", "company", "branch", "category")),
            "Invalid source label",
        )
        _require(item["id"] not in ids, "Duplicate source ID")
        ids.add(item["id"])
        _private(item["root"], directory=True)
        systems = item["systems"]
        _require(
            isinstance(systems, list)
            and 1 <= len(systems) <= 512
            and all(_text(x) for x in systems),
            "Explicit system list required",
        )
        _require(len(set(systems)) == len(systems), "Duplicate system selector")
        for system in systems:
            route = (item["root"], item["company"], item["branch"], system)
            _require(route not in routes, "Duplicate physical source route")
            routes.add(route)
    return audits


@contextmanager
def _snapshot(root, filename):
    root = _private(root, directory=True)
    path = _private(root / filename)
    before = path.stat()
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        yield db
        after = _private(path).stat()
        _require(
            (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino),
            "Input replaced during capture",
        )
    finally:
        db.close()


def _references(obj, location):
    refs = []
    for key in ("control_id", "control_reference", "control_ids", "control_references"):
        if key not in obj:
            continue
        value = obj[key]
        values = [value] if isinstance(value, str) else value
        _require(
            isinstance(values, list) and all(_text(x) for x in values),
            "Malformed typed control references",
        )
        refs.extend({"control_id": x, "locator": f"{location}.{key}"} for x in values)
    return refs


def _audit(selector):
    started = _now()
    with _snapshot(selector["root"], "engagements.sqlite3") as db:
        row = db.execute(
            "SELECT revision,state FROM engagements WHERE id=?", (selector["engagement_id"],)
        ).fetchone()
        _require(row is not None, "Explicit engagement not found")
        state = _json(row["state"])
        _require(
            state["id"] == selector["engagement_id"] and state["revision"] == row["revision"],
            "Audit snapshot identity mismatch",
        )
        previous, count, last_state = "", 0, None
        for event in db.execute(
            "SELECT * FROM events WHERE engagement=? ORDER BY revision", (state["id"],)
        ):
            command, event_state = _json(event["command"]), _json(event["state"])
            envelope = {
                "actor": event["actor"],
                "recorded_at": event["recorded_at"],
                "previous_hash": event["previous_hash"],
                "state": event_state,
                "command": command,
                "command_id": event["command_id"],
            }
            _require(
                event["revision"] == count
                and event["previous_hash"] == previous
                and event["hash"] == digest(envelope)
                and event["request_hash"] == digest(command),
                "Audit history integrity failure",
            )
            _require(
                event_state["id"] == state["id"] and event_state["revision"] == count,
                "Audit event identity mismatch",
            )
            previous, last_state = event["hash"], event_state
            count += 1
        _require(
            count == state["revision"] + 1 and last_state == state, "Audit state/history mismatch"
        )
    return state, {
        **selector,
        "started_at": started,
        "completed_at": _now(),
        "revision": state["revision"],
        "simulated_at": state.get("simulated_at"),
        "snapshot_sha256": digest(state),
        "history_head": previous,
        "history_events": count,
    }


def _classification(origin, provenance):
    if origin == "REPOSITORY_SYNTHETIC_DOCUMENT":
        return "DOCUMENTARY_NOT_OPERATING_FACT"
    if provenance.get("classification") in DOCUMENTARY | {"LEGACY_SYNTHETIC_DOCUMENTARY_SOURCE"}:
        return "DOCUMENTARY_NOT_OPERATING_FACT"
    if origin == "MIGRATED_SYNTHETIC_HISTORY":
        return "MIGRATED_REFERENCE_NOT_OPERATING_FACT"
    if origin == "AUTHORED_TRAINING_SOURCE":
        return "AUTHORED_ACTIVITY_OR_REFERENCE_NOT_OPERATING_FACT"
    return "UNCLASSIFIED_NOT_OPERATING_FACT"


def _source(selector, engagement_ids):
    started = _now()
    records, systems, logical, receipts = [], [], [], []
    metadata_by_identity = {}
    with _snapshot(selector["root"], "company.sqlite3") as db:
        for system in sorted(selector["systems"]):
            key = (selector["company"], selector["branch"], system)
            registered = db.execute(
                "SELECT owner FROM systems WHERE company=? AND branch=? AND system=?", key
            ).fetchone()
            _require(registered is not None, "Explicit source system not registered")
            count = 0
            for row in db.execute(
                (
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? ORDER BY "
                    "record,version"
                ),
                key,
            ):
                raw = row["content"]
                _require(
                    hashlib.sha256(raw).hexdigest() == row["sha256"],
                    "Native source integrity failure",
                )
                _require(len(raw) <= 64 * 1024 * 1024, "Native source exceeds inventory bound")
                provenance = _json(row["provenance"])
                _require(isinstance(provenance, dict), "Invalid provenance")
                native = {}
                try:
                    candidate = _json(raw)
                    if isinstance(candidate, dict):
                        native = candidate
                except (ValueError, UnicodeError):
                    pass  # Binary/document originals: only typed provenance is read.
                identity = {k: row[k] for k in IDENTITY}
                metadata_by_identity[tuple(identity.values())] = {
                    **identity,
                    "event_at": row["event_at"],
                    "available_at": row["available_at"],
                    "imported_at": row["imported_at"],
                    "origin": row["origin"],
                    "provenance": provenance,
                }
                records.append(
                    {
                        "component_id": selector["id"],
                        **identity,
                        "origin": row["origin"],
                        "classification": _classification(row["origin"], provenance),
                        "event_at": row["event_at"],
                        "available_at": row["available_at"],
                        "bytes": len(raw),
                        "explicit_control_references": _references(provenance, "provenance")
                        + _references(native, "native"),
                        "qualifiers": {
                            f"{loc}.{k}": obj[k]
                            for loc, obj in (("provenance", provenance), ("native", native))
                            for k in QUALIFIERS
                            if k in obj
                        },
                        "declared_period_fields": {
                            f"{loc}.{k}": obj[k]
                            for loc, obj in (("provenance", provenance), ("native", native))
                            for k in PERIODS
                            if k in obj
                        },
                        "boundary_id": native.get("boundary_id"),
                        "verified_collections": [],
                    }
                )
                logical.append({k: row[k] for k in row.keys() if k != "content"})
                count += 1
                _require(len(records) <= 100000, "Source row bound exceeded")
            systems.append({"system": system, "owner": registered["owner"], "versions": count})
        membership = {tuple(r[k] for k in IDENTITY): r for r in records}
        # SQL selects only configured engagement IDs, never exports other receipt bodies.
        for eid in sorted(engagement_ids):
            query = (
                "SELECT command_id,input_digest,receipt FROM collections "
                "WHERE json_extract(receipt,'$.engagement_id')=? ORDER BY command_id"
            )
            for row in db.execute(query, (eid,)):
                receipt = _json(row["receipt"])
                source = receipt["source"]
                record = membership.get(tuple(source.get(k) for k in IDENTITY))
                if record is None:
                    selected = (
                        source.get("company") == selector["company"]
                        and source.get("branch") == selector["branch"]
                        and source.get("system") in selector["systems"]
                    )
                    _require(not selected, "Collection refers to absent or changed source")
                    continue
                _require(
                    source == metadata_by_identity[tuple(source[k] for k in IDENTITY)],
                    "Collection native metadata mismatch",
                )
                expected = hashlib.sha256(
                    company_json(
                        [
                            receipt["principal_id"],
                            eid,
                            [source[k] for k in IDENTITY[:4]],
                            source["version"],
                            receipt["simulated_as_of"],
                        ]
                    ).encode()
                ).hexdigest()
                _require(
                    row["command_id"] == receipt["command_id"] and expected == row["input_digest"],
                    "Collection receipt integrity failure",
                )
                _require(
                    receipt["content_bytes"] == record["bytes"]
                    and source["available_at"] == record["available_at"],
                    "Collection source mismatch",
                )
                _require(
                    datetime.fromisoformat(receipt["simulated_as_of"])
                    >= datetime.fromisoformat(record["available_at"]),
                    "Collection precedes source availability",
                )
                pin = {
                    "engagement_id": eid,
                    "command_id": receipt["command_id"],
                    "receipt_sha256": digest(receipt),
                    "collected_at": receipt["collected_at"],
                    "simulated_as_of": receipt["simulated_as_of"],
                }
                record["verified_collections"].append(pin)
                receipts.append(receipt)
    return records, {
        **selector,
        "started_at": started,
        "completed_at": _now(),
        "systems": systems,
        "versions": len(records),
        "unique_source_records": len({tuple(r[k] for k in IDENTITY[:4]) for r in records}),
        "membership_sha256": digest(logical),
        "selected_receipts_sha256": digest(receipts),
        "selected_receipts": len(receipts),
        "snapshot_isolation": "ONE_DATABASE_READ_TRANSACTION",
    }


def inventory(config):
    """Read explicit stores without changing permissions, schemas or source records."""
    config = _json(json.dumps(config))
    selectors = _validate(config)
    captured = [_audit(x) for x in selectors]
    target = captured[0][0]
    controls = target["controls"]
    _require(
        isinstance(controls, list) and len({c["id"] for c in controls}) == len(controls),
        "Invalid scoped controls",
    )
    records, source_pins = [], []
    for selector in config["sources"]:
        rows, pin = _source(selector, {x["engagement_id"] for x in selectors})
        records.extend(rows)
        source_pins.append(pin)
    work, retained, unmatched = [], [], []
    for selector, (state, _pin) in zip(selectors, captured, strict=True):
        for kind in ("tasks", "workpapers", "reviews", "populations", "selections"):
            for item in state.get(kind, []):
                work.append(
                    {
                        "audit_root": selector["root"],
                        "engagement_id": state["id"],
                        "revision": state["revision"],
                        "kind": kind,
                        "id": item["id"],
                        "status": item.get("status"),
                        "control_references": _references(item, kind),
                        "record_sha256": digest(item),
                    }
                )
        for artifact in state.get("artifacts", []):
            source = artifact.get("source", {})
            if source.get("kind") != "COLLECTED_COMPANY_SOURCE":
                continue
            receipt = source["receipt"]
            native_receipt = receipt.get("upstream_receipt", receipt)
            identity = native_receipt["source"]
            matches = [
                r
                for r in records
                if all(r[k] == identity.get(k) for k in IDENTITY)
                and any(
                    c["receipt_sha256"] == digest(native_receipt)
                    and c["engagement_id"] == state["id"]
                    for c in r["verified_collections"]
                )
            ]
            if not matches:
                unmatched.append(
                    {
                        "engagement_id": state["id"],
                        "artifact_id": artifact["id"],
                        "status": "NO_SELECTED_NATIVE_RECEIPT_MATCH_NOT_VERIFIED",
                    }
                )
                continue
            sha = artifact["sha256"]
            _require(
                isinstance(sha, str) and re.fullmatch("[a-f0-9]{64}", sha),
                "Invalid retained artifact hash",
            )
            artifact_root = _private(Path(selector["root"]) / "artifacts", directory=True)
            path = _private(artifact_root / sha)
            raw = path.read_bytes()
            _require(
                len(raw) == artifact["bytes"]
                and hashlib.sha256(raw).hexdigest() == sha == identity["sha256"],
                "Retained original integrity failure",
            )
            retained.append(
                {
                    "engagement_id": state["id"],
                    "audit_root": selector["root"],
                    "artifact_id": artifact["id"],
                    "sha256": sha,
                    "receipt_sha256": digest(native_receipt),
                    "component_candidates": [r["component_id"] for r in matches],
                    "identity_ambiguity": len(matches) != 1,
                }
            )
    for record in records:
        boundary = record["boundary_id"]
        cutoff = target.get("simulated_at")
        record["target_time_visibility"] = (
            "UNKNOWN_NO_TARGET_CLOCK"
            if not cutoff
            else "AVAILABLE_BY_TARGET_CLOCK"
            if datetime.fromisoformat(record["available_at"]) <= datetime.fromisoformat(cutoff)
            else "FUTURE_TO_TARGET_CLOCK"
        )
        record["boundary_applicability"] = (
            "NOT_RECORDED"
            if not boundary
            else "EXPLICIT_SCOPE_MATCH"
            if boundary in target["scope"].get("boundaries", [])
            else "EXPLICIT_DIFFERENT_BOUNDARY"
        )
    rows = []
    scoped_ids = {c["id"] for c in controls}
    for control in sorted(controls, key=lambda c: c["id"]):
        linked = [
            r
            for r in records
            if control["id"] in {x["control_id"] for x in r["explicit_control_references"]}
        ]
        rows.append(
            {
                "control": control,
                "linked_source_versions": [
                    {"component_id": r["component_id"], **{k: r[k] for k in IDENTITY}}
                    for r in linked
                ],
                "source_classification_counts": dict(Counter(r["classification"] for r in linked)),
                "controls_activity_reference_gap": (
                    "NO_AUTHORED_ACTIVITY_REFERENCE_IN_SELECTED_SOURCES"
                    if not any(
                        r["classification"] == "AUTHORED_ACTIVITY_OR_REFERENCE_NOT_OPERATING_FACT"
                        for r in linked
                    )
                    else "ACTIVITY_REFERENCE_PRESENT_SUFFICIENCY_NOT_ASSESSED"
                ),
                "reference_status": "EXPLICIT_REFERENCES_PRESENT"
                if linked
                else "NO_EXPLICIT_REFERENCE_IN_SELECTED_SOURCES",
                "procedure_and_period_sufficiency": "NOT_ASSESSED",
            }
        )
    return {
        "schema": SCHEMA,
        "config_sha256": digest(config),
        "scope": target["scope"],
        "audit_snapshots": [p for _, p in captured],
        "source_snapshots": source_pins,
        "snapshot_isolation": "PER_DATABASE_NOT_GLOBAL",
        "controls": rows,
        "source_versions": records,
        "recorded_work": work,
        "verified_retained_originals": retained,
        "unmatched_collection_artifacts": unmatched,
        "summary": {
            "scoped_controls": len(controls),
            "controls_with_explicit_references": sum(
                bool(r["linked_source_versions"]) for r in rows
            ),
            "controls_by_source_classification": {
                classification: sum(
                    row["source_classification_counts"].get(classification, 0) > 0 for row in rows
                )
                for classification in sorted({r["classification"] for r in records})
            },
            "source_versions": len(records),
            "source_classification_counts": dict(Counter(r["classification"] for r in records)),
            "verified_retained_originals": len(retained),
            "unmatched_collection_artifacts": len(unmatched),
            "unmapped_source_versions": sum(
                not any(x["control_id"] in scoped_ids for x in r["explicit_control_references"])
                for r in records
            ),
        },
        "limitations": LIMITATIONS,
    }


def write_inventory(config, destination):
    """Durably publish a new private report; never overwrite prior inventories."""
    _validate(config)
    destination = Path(destination)
    _require(
        destination.is_absolute() and ".." not in destination.parts, "Absolute output required"
    )
    _private(destination.parent, directory=True)
    _require(not destination.exists() and not destination.is_symlink(), "New destination required")
    roots = [Path(x["root"]) for x in [config["target"], *config["audits"], *config["sources"]]]
    _require(
        not any(destination == r or destination.is_relative_to(r) for r in roots),
        "Output inside input forbidden",
    )
    report = inventory(config)
    stage = Path(tempfile.mkdtemp(prefix=".source-readiness-", dir=destination.parent))
    try:
        text = io.StringIO()
        writer = csv.writer(text)
        writer.writerow(["control_id", "source_versions", "reference_status", "sufficiency"])
        for row in report["controls"]:
            writer.writerow(
                [
                    row["control"]["id"],
                    len(row["linked_source_versions"]),
                    row["reference_status"],
                    "NOT_ASSESSED",
                ]
            )
        payloads = {
            "MATRIX.json": json.dumps(report, indent=2) + "\n",
            "MATRIX.csv": text.getvalue(),
            "CONFIG.json": json.dumps(config, indent=2) + "\n",
        }
        for name, value in payloads.items():
            path = stage / name
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(value)
        manifest = {
            "schema": SCHEMA,
            "module_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "code_pins": {
                name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                for name in (
                    "source_readiness.py",
                    "store.py",
                    "company_store.py",
                    "private_publication.py",
                )
            },
            "git_revision": subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            ).stdout.strip(),
            "files": {
                name: hashlib.sha256((stage / name).read_bytes()).hexdigest() for name in payloads
            },
            "summary": report["summary"],
            "snapshot_isolation": report["snapshot_isolation"],
        }
        fd = os.open(stage / "MANIFEST.json", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(manifest, f, indent=2)
        publish(stage, destination)
        return manifest
    finally:
        shutil.rmtree(stage)
