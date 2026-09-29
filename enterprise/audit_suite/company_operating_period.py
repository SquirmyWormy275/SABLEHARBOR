"""Explicit local due ledger and retained execution assertions, independent of audits.

This module does not execute business operations or establish population sufficiency.
"""

import fcntl
import os
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

from .company_lifecycle_activity import FIELDS, LifecycleSourceRef, read_inputs
from .company_store import CompanyStoreError, _id, _time
from .inference import _json as strict_json
from .operating_source_bridge import encoded, sha
from .organization import snapshot

SYSTEM = "operating_period_ledger"
QUALIFICATION = "LOCAL_DECLARED_INVENTORY_AND_SCHEDULE_NOT_ENTERPRISE_COMPLETENESS"
PLAN_FIELDS = {
    "period_id",
    "company_id",
    "branch_id",
    "owner_id",
    "control_ids",
    "period_start",
    "period_end_exclusive",
    "declared_at",
    "inventory",
    "local_basis",
    "schedule",
}
SLOT_FIELDS = {
    "id",
    "inventory_ids",
    "control_id",
    "due_at",
    "window_start",
    "window_end_exclusive",
    "depends_on",
}


def _require(value, message):
    if not value:
        raise CompanyStoreError(message)


def _ids(values, minimum=1, maximum=64):
    _require(
        isinstance(values, list) and minimum <= len(values) <= maximum, "Bounded ID list required"
    )
    for value in values:
        _id(value)
    _require(len(set(values)) == len(values), "Distinct IDs required")
    return set(values)


def _text(value):
    _require(
        isinstance(value, str) and 1 <= len(value.strip()) <= 4000, "Bounded explicit text required"
    )


def _hash(value):
    _require(
        isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value),
        "Exact lowercase SHA256 required",
    )


def _plan(value):
    _require(isinstance(value, dict) and set(value) == PLAN_FIELDS, "Exact period plan required")
    p = deepcopy(value)
    for k in ("period_id", "company_id", "branch_id", "owner_id"):
        _id(p[k])
    controls = _ids(p["control_ids"])
    _text(p["local_basis"])
    for k in ("period_start", "period_end_exclusive", "declared_at"):
        p[k] = _time(p[k])
    _require(
        p["declared_at"] <= p["period_start"] < p["period_end_exclusive"],
        "Schedule declaration must precede its positive operating period",
    )
    _require(
        isinstance(p["inventory"], list) and 1 <= len(p["inventory"]) <= 64,
        "One to64 explicitly declared inventory items required",
    )
    inventory = []
    for item in p["inventory"]:
        _require(
            isinstance(item, dict) and set(item) == {"id", "description"},
            "Exact inventory item required",
        )
        _id(item["id"])
        _text(item["description"])
        inventory.append(item["id"])
    _ids(inventory)
    _require(
        isinstance(p["schedule"], list) and 1 <= len(p["schedule"]) <= 512,
        "One to512 explicit occurrences required",
    )
    previous = {}
    for slot in p["schedule"]:
        _require(isinstance(slot, dict) and set(slot) == SLOT_FIELDS, "Exact occurrence required")
        _id(slot["id"])
        _require(
            slot["id"] not in previous and slot["id"] != p["period_id"],
            "Distinct occurrence ID required",
        )
        _require(
            _ids(slot["inventory_ids"]) <= set(inventory), "Occurrence has undeclared inventory"
        )
        _id(slot["control_id"])
        _require(slot["control_id"] in controls, "Occurrence has undeclared control")
        dependencies = _ids(slot["depends_on"], minimum=0)
        _require(
            dependencies <= previous.keys(),
            "Dependencies must identify earlier explicit occurrences",
        )
        for k in ("window_start", "window_end_exclusive", "due_at"):
            slot[k] = _time(slot[k])
        _require(
            p["period_start"]
            <= slot["window_start"]
            < slot["window_end_exclusive"]
            <= p["period_end_exclusive"],
            "Occurrence window must fit the declared half-open period",
        )
        _require(
            slot["window_start"] <= slot["due_at"] <= slot["window_end_exclusive"],
            "Due instant must fall within occurrence window or its exclusive boundary",
        )
        _require(
            all(previous[d]["due_at"] <= slot["due_at"] for d in dependencies),
            "Dependency due order is inverted",
        )
        previous[slot["id"]] = slot
    return p


def _body(row):
    _require(sha(row["content"]) == row["sha256"], "Ledger original hash mismatch")
    try:
        value = strict_json(row["content"].decode("utf-8"))
    except (ValueError, UnicodeError) as error:
        raise CompanyStoreError("Malformed ledger JSON") from error
    _require(isinstance(value, dict), "Malformed ledger original")
    return value


def _load(store, period_id, db=None):
    _id(period_id)
    if db is None:
        with store._db() as connection:
            return _load(store, period_id, connection)
    rows = db.execute(
        "SELECT * FROM versions WHERE system=? AND record=? LIMIT 3", (SYSTEM, period_id)
    ).fetchall()
    _require(len(rows) == 1, "Exact immutable period declaration required")
    row = dict(rows[0])
    body = _body(row)
    _require(body.get("kind") == "PERIOD_DECLARATION", "Not a period declaration")
    plan = _plan(body["plan"])
    _require(
        (row["company"], row["branch"]) == (plan["company_id"], plan["branch_id"]),
        "Period routing mismatch",
    )
    return plan, row


def _module_pins(repository):
    """Selected maintained source files, not loaded-binary or full dependency attestation."""
    paths = (
        "enterprise/ccf/assurance/design_data/control_procedures.json",
        "enterprise/audit_suite/company_operating_period.py",
        "enterprise/audit_suite/company_lifecycle_activity.py",
        "enterprise/audit_suite/company_store.py",
        "enterprise/audit_suite/inference.py",
    )
    return {relative: sha((repository / relative).read_bytes()) for relative in paths}


def _create_period(store, *, repository, plan):
    """Initialize one new empty company ledger; no source operations or grants."""
    p = _plan(plan)
    module_pins = _module_pins(Path(repository))
    org = snapshot(Path(repository), as_of=p["period_start"][:10])
    assignments = {a["control_id"]: a for a in org["control_assignments"]}
    _require(set(p["control_ids"]) <= assignments.keys(), "Canonical control IDs required")
    owners = {assignments[c]["primary_person_id"] for c in p["control_ids"]}
    _require(p["owner_id"] in owners, "Existing scoped owner identity required")
    pins = dict(org["source_sha256"])
    pins.update(module_pins)
    with store._db() as db:
        _require(
            all(
                db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
                for table in ("versions", "systems", "grants", "collections", "access_events")
            ),
            "New empty private company store required",
        )
    _require(
        _module_pins(Path(repository)) == module_pins,
        "Maintained source changed before declaration",
    )
    store.register_system(p["company_id"], p["branch_id"], SYSTEM, p["owner_id"])
    return store.append_version(
        p["company_id"],
        p["branch_id"],
        SYSTEM,
        p["period_id"],
        expected_version=0,
        command_id="period-" + sha(encoded(p))[:48],
        event_at=p["declared_at"],
        available_at=p["declared_at"],
        content=encoded(
            {
                "kind": "PERIOD_DECLARATION",
                "plan": p,
                "source_sha256": pins,
                "qualification": QUALIFICATION,
            }
        ),
        provenance={"source_reference": p["period_id"], "qualification": QUALIFICATION},
    )


def _sources(groups, plan, recorded_at):
    _require(
        isinstance(groups, list) and 1 <= len(groups) <= 4,
        "One to4 explicit source groups required",
    )
    retained, labels, identities, locations = [], set(), set(), set()
    for group in groups:
        _require(
            isinstance(group, dict)
            and set(group)
            == {
                "source_store_id",
                "root",
                "refs",
                "expected_metadata_sha256",
            },
            "Exact source group required",
        )
        _id(group["source_store_id"])
        _require(group["source_store_id"] not in labels, "Distinct source labels required")
        labels.add(group["source_store_id"])
        _hash(group["expected_metadata_sha256"])
        _require(isinstance(group["root"], (str, Path)), "Explicit source root required")
        source_path = Path(group["root"])
        _require(
            source_path.is_absolute()
            and source_path == source_path.resolve()
            and ".." not in source_path.parts,
            "Canonical absolute source root required",
        )
        location = str(source_path)
        _require(location not in locations, "Duplicate physical source root")
        locations.add(location)
        _require(isinstance(group["refs"], list), "Exact native reference list required")
        refs = []
        for ref in group["refs"]:
            _require(
                isinstance(ref, dict) and set(ref) == set(FIELDS),
                "Exact native six fields required",
            )
            _require(
                (ref["company"], ref["branch"]) == (plan["company_id"], plan["branch_id"]),
                "Cross-company or cross-branch support forbidden",
            )
            for field in FIELDS[:4]:
                _id(ref[field])
            _hash(ref["sha256"])
            _require(
                type(ref["version"]) is int and ref["version"] > 0, "Exact source version required"
            )
            identity = (group["source_store_id"], *(ref[k] for k in FIELDS[:-1]))
            _require(identity not in identities, "Duplicate source member")
            identities.add(identity)
            refs.append(LifecycleSourceRef(**ref))
        rows, pin = read_inputs(group["root"], tuple(refs))
        _require(pin == group["expected_metadata_sha256"], "Selected metadata pin mismatch")
        _require(
            all(
                r["event_at"] is not None
                and _time(r["event_at"]) <= recorded_at
                and _time(r["available_at"]) <= recorded_at
                for r in rows
            ),
            "Future or undated execution support is unavailable",
        )
        retained.append(
            {
                "source_store_id": group["source_store_id"],
                "source_location_sha256": sha(location.encode("utf-8")),
                "metadata_sha256": pin,
                "records": [{k: v for k, v in row.items() if k != "content"} for row in rows],
            }
        )
    return retained


def _record_occurrence(
    store,
    *,
    period_id,
    occurrence_id,
    expected_version,
    command_id,
    recorded_at,
    disposition,
    sources,
    reason,
    predecessor_refs,
):
    """Append a source-backed operator assertion or explicit skip, not a business execution."""
    sources, predecessor_refs = deepcopy(sources), deepcopy(predecessor_refs)
    plan, declaration = _load(store, period_id)
    _id(occurrence_id)
    _id(command_id)
    _require(
        type(expected_version) is int and 0 <= expected_version < 32,
        "Expected version must be between zero and31",
    )
    _require(disposition in ("EXECUTED", "SKIPPED"), "Explicit occurrence disposition required")
    _text(reason)
    when = _time(recorded_at)
    slot = next((s for s in plan["schedule"] if s["id"] == occurrence_id), None)
    _require(slot is not None, "Undeclared occurrence")
    _require(when >= slot["window_start"], "Occurrence cannot be recorded before its window")
    _require(isinstance(predecessor_refs, list), "Exact predecessor list required")
    if disposition == "SKIPPED":
        _require(predecessor_refs == [], "Skipped occurrence must not claim executed predecessors")
    predecessors, names = [], set()
    with store._db() as db:
        prior = db.execute("SELECT * FROM versions WHERE command_id=?", (command_id,)).fetchone()
        current = db.execute(
            "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
            "AND record=? ORDER BY version DESC LIMIT 1",
            (plan["company_id"], plan["branch_id"], SYSTEM, occurrence_id),
        ).fetchone()
        _require(
            prior is not None or (current["version"] if current else 0) == expected_version,
            "Stale occurrence version",
        )
        if current and prior is None:
            _require(
                when >= current["available_at"],
                "Occurrence correction cannot move backward in time",
            )
        for ref in predecessor_refs:
            _require(
                isinstance(ref, dict) and set(ref) == {"occurrence_id", "version", "sha256"},
                "Exact predecessor pin required",
            )
            _id(ref["occurrence_id"])
            _hash(ref["sha256"])
            _require(
                type(ref["version"]) is int and ref["version"] > 0,
                "Exact predecessor version required",
            )
            _require(ref["occurrence_id"] not in names, "Duplicate predecessor")
            names.add(ref["occurrence_id"])
            row = db.execute(
                "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                "AND record=? AND version=?",
                (
                    plan["company_id"],
                    plan["branch_id"],
                    SYSTEM,
                    ref["occurrence_id"],
                    ref["version"],
                ),
            ).fetchone()
            _require(
                row is not None and row["sha256"] == ref["sha256"], "Missing or changed predecessor"
            )
            latest = db.execute(
                "SELECT MAX(version) FROM versions WHERE company=? AND branch=? "
                "AND system=? AND record=?",
                (plan["company_id"], plan["branch_id"], SYSTEM, ref["occurrence_id"]),
            ).fetchone()[0]
            _require(
                prior is not None or latest == ref["version"],
                "Stale predecessor pin; explicit reinspection required",
            )
            body = _body(row)
            _require(
                body.get("period_id") == period_id
                and body.get("disposition") == "EXECUTED"
                and row["available_at"] <= when,
                "Unexecuted or future predecessor",
            )
            predecessors.append(deepcopy(ref))
    _require(
        disposition == "SKIPPED" or names == set(slot["depends_on"]),
        "Every declared dependency needs its exact prior receipt",
    )
    if disposition == "EXECUTED":
        for group in sources:
            if isinstance(group, dict) and isinstance(group.get("root"), (str, Path)):
                source_root = Path(group["root"]).absolute()
                ledger_root = store.path.parent.absolute()
                _require(
                    source_root != ledger_root
                    and source_root not in ledger_root.parents
                    and ledger_root not in source_root.parents,
                    "Source and ledger roots must be separate",
                )
        retained = _sources(sources, plan, when)
    else:
        _require(sources == [], "Skipped occurrence cannot claim execution support")
        retained = []
    body = {
        "kind": "OCCURRENCE_ASSERTION",
        "period_id": period_id,
        "occurrence_id": occurrence_id,
        "declaration_sha256": declaration["sha256"],
        "disposition": disposition,
        "recorded_at": when,
        "reason": reason,
        "sources": retained,
        "predecessor_refs": predecessors,
        "declared_dependency_ids": slot["depends_on"],
        "predecessor_execution": "EXACT_ASSERTION_PINS"
        if disposition == "EXECUTED"
        else "NOT_ASSERTED",
        "qualification": QUALIFICATION,
        "execution_basis": "OPERATOR_ASSERTION_WITH_PINNED_SOURCE_NOT_OPERATION_EXECUTED_BY_LEDGER",
        "recording_timeliness": "AFTER_DUE" if when > slot["due_at"] else "BY_DUE",
    }
    if disposition == "EXECUTED":
        _require(
            _sources(sources, plan, when) == retained, "Source changed during occurrence capture"
        )
    return store.append_version(
        plan["company_id"],
        plan["branch_id"],
        SYSTEM,
        occurrence_id,
        expected_version=expected_version,
        command_id=command_id,
        event_at=when,
        available_at=when,
        content=encoded(body),
        provenance={"source_reference": period_id, "qualification": QUALIFICATION},
    )


def report_period(store, *, period_id, as_of):
    """Read one explicit period; upstream roots are not rediscovered."""
    when = _time(as_of)
    with store._db() as db:
        if not db.in_transaction:
            db.execute("BEGIN")
        plan, declaration = _load(store, period_id, db)
        _require(when >= plan["declared_at"], "Period declaration is not yet available")
        size = db.execute(
            "SELECT COALESCE(SUM(length(content)),0) FROM versions WHERE system=?", (SYSTEM,)
        ).fetchone()[0]
        _require(size <= 64 * 1024 * 1024, "Ledger report exceeds64MiB bound")
        rows = db.execute(
            "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
            "AND available_at<=? ORDER BY record,version",
            (plan["company_id"], plan["branch_id"], SYSTEM, when),
        ).fetchall()
    by_id = {}
    for row in rows:
        body = _body(row)
        if body.get("kind") == "OCCURRENCE_ASSERTION":
            _require(
                body["period_id"] == period_id
                and body["declaration_sha256"] == declaration["sha256"],
                "Occurrence declaration mismatch",
            )
            by_id.setdefault(row["record"], []).append(
                {
                    "version": row["version"],
                    "sha256": row["sha256"],
                    **body,
                }
            )
    occurrences = []
    for slot in plan["schedule"]:
        history = by_id.get(slot["id"], [])
        latest = history[-1] if history else None
        occurrences.append(
            {
                "schedule": slot,
                "is_due": when >= slot["due_at"],
                "state": (
                    "SOURCE_ASSERTION_RECORDED"
                    if latest["disposition"] == "EXECUTED"
                    else "SKIP_RECORDED"
                )
                if latest
                else ("MISSING_DUE_OCCURRENCE" if when >= slot["due_at"] else "NOT_YET_DUE"),
                "history": history,
            }
        )
    return {
        "period_id": period_id,
        "as_of": when,
        "declaration_sha256": declaration["sha256"],
        "qualification": QUALIFICATION,
        "declared_inventory": plan["inventory"],
        "occurrences": occurrences,
        "due_count": sum(o["is_due"] for o in occurrences),
        "missing_due_count": sum(o["state"] == "MISSING_DUE_OCCURRENCE" for o in occurrences),
        "operation_execution": "NOT_PERFORMED_BY_LEDGER",
        "whole_company_year": "NOT_ESTABLISHED",
        "population_acceptance": "NOT_PERFORMED",
        "source_validation": "RETAINED_PINS_NOT_CURRENT_UPSTREAM_REVALIDATION",
    }


@contextmanager
def _writer(store):
    """Serialize this maintained ledger API; not a global lock over upstream stores."""
    fd = os.open(store.path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise CompanyStoreError("Operating period writer is busy; inspect and retry") from error
        opened, current = os.fstat(fd), store.path.stat()
        _require(
            (opened.st_dev, opened.st_ino) == (current.st_dev, current.st_ino),
            "Ledger identity changed before write",
        )
        yield
    finally:
        os.close(fd)


def create_period(store, *, repository, plan):
    """Create the declaration in one new empty private ledger."""
    with _writer(store):
        return _create_period(store, repository=repository, plan=plan)


def record_occurrence(
    store,
    *,
    period_id,
    occurrence_id,
    expected_version,
    command_id,
    recorded_at,
    disposition,
    sources,
    reason,
    predecessor_refs,
):
    """Retain an explicit assertion or skip under the maintained ledger writer lock."""
    with _writer(store):
        return _record_occurrence(
            store,
            period_id=period_id,
            occurrence_id=occurrence_id,
            expected_version=expected_version,
            command_id=command_id,
            recorded_at=recorded_at,
            disposition=disposition,
            sources=sources,
            reason=reason,
            predecessor_refs=predecessor_refs,
        )
