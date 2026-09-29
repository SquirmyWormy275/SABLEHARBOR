"""Fixed local dataset validation, exact joins and correction; no source acceptance."""

import os
import tempfile
from collections import Counter
from copy import deepcopy
from pathlib import Path

from .company_backup_runtime import checked_bytes, database, exact_pin, native, private, require
from .company_disposal_runtime import _preflight
from .company_store import CompanyStore, CompanyStoreError, _id, _json, _now, _time
from .inference import _json as decode
from .operating_source_bridge import encoded, sha
from .organization import snapshot
from .private_publication import publish

QUALIFICATION = "LOCAL_NONPERSONAL_DATA_RULES_NOT_BUSINESS_TRUTH_OR_SOURCE_ACCEPTANCE"
CONTROLS = ["SH-DAT-001", "SH-DAT-004", "SH-REC-001", "SH-REC-002", "SH-REC-003"]
SYSTEMS = (
    "quality_definition",
    "quality_reference",
    "quality_raw",
    "quality_derived",
    "quality_aggregate",
    "quality_operation",
)
FIELDS = ("company", "branch", "system", "record", "version", "sha256")
ROW_FIELDS = {"record_id", "entity_id", "units", "observed_at"}
MAX_COMMANDS = 64
LIMIT = 256 * 1024
NATIVE_LIMITS = {
    **dict.fromkeys(("company", "branch", "system", "record", "command_id", "origin"), 128),
    **dict.fromkeys(("event_at", "available_at", "imported_at", "sha256", "input_digest"), 64),
    "version": 16,
    "content": LIMIT,
    "provenance": 16 * 1024,
}


def _code():
    names = (
        "company_data_quality_runtime.py",
        "company_backup_runtime.py",
        "company_disposal_runtime.py",
        "company_operating_period.py",
        "company_store.py",
        "inference.py",
        "operating_source_bridge.py",
        "organization.py",
        "private_publication.py",
    )
    pins = {n: sha(Path(__file__).with_name(n).read_bytes()) for n in names}
    pins["enterprise/ccf/registry.py"] = sha(
        (Path(__file__).parents[1] / "ccf/registry.py").read_bytes()
    )
    return pins


def _keys(value, keys):
    require(
        isinstance(value, dict) and set(value) == set(keys.split()), "Exact typed fields required"
    )


def _stamp(value):
    try:
        return _time(value)
    except (OverflowError, ValueError, TypeError) as exc:
        raise CompanyStoreError("Bounded explicit offset timestamp required") from exc


def _rows(raw):
    require(isinstance(raw, bytes) and 0 < len(raw) <= 65536, "Bounded raw fixture bytes required")
    try:
        rows = decode(raw)
    except (ValueError, RecursionError) as exc:
        raise CompanyStoreError("Unambiguous finite source JSON required") from exc
    require(
        isinstance(rows, list) and 1 <= len(rows) <= 128 and all(isinstance(r, dict) for r in rows),
        "One to128 explicit source row objects required",
    )
    return rows


def _plan(plan):
    _keys(
        plan,
        "runtime_id company branch dataset_id owner_id declared_at input_at event_window "
        "expected_record_ids reference_rows maximum_units local_rule_basis",
    )
    for key in ("runtime_id", "company", "branch", "dataset_id", "owner_id"):
        _id(plan[key])
    declared, at = _stamp(plan["declared_at"]), _stamp(plan["input_at"])
    _keys(plan["event_window"], "start end")
    start, end = (_stamp(plan["event_window"][k]) for k in ("start", "end"))
    require(
        declared <= start < end and declared <= at,
        "Explicit independently declared query window required",
    )
    ids = plan["expected_record_ids"]
    require(
        isinstance(ids, list) and 1 <= len(ids) <= 128,
        "Bounded independently expected IDs required",
    )
    for ident in ids:
        _id(ident)
    require(len(set(ids)) == len(ids), "Unique independently expected IDs required")
    refs = plan["reference_rows"]
    require(
        isinstance(refs, list) and 1 <= len(refs) <= 32,
        "Bounded independent reference inventory required",
    )
    for row in refs:
        _keys(row, "entity_id category")
        _id(row["entity_id"])
        _id(row["category"])
    require(len({r["entity_id"] for r in refs}) == len(refs), "Unique reference join keys required")
    require(
        type(plan["maximum_units"]) is int and 1 <= plan["maximum_units"] <= 1000000,
        "Exact bounded integer units rule required",
    )
    require(
        isinstance(plan["local_rule_basis"], str)
        and 1 <= len(plan["local_rule_basis"].strip()) <= 2000,
        "Explicit local rule basis required",
    )
    return plan | {
        "declared_at": declared,
        "input_at": at,
        "event_window": {"start": start, "end": end},
    }


def _provenance(cfg):
    return {
        "control_ids": CONTROLS,
        "classification": "DECLARED_NONPERSONAL_LOCAL_FIXTURE_NOT_ACCEPTED_POLICY",
        "runtime_sha256": sha(encoded(cfg)),
        "dataset_id": cfg["plan"]["dataset_id"],
        "qualification": QUALIFICATION,
    }


def _pin(cfg, system, record, version, raw):
    return dict(
        zip(
            FIELDS,
            (cfg["plan"]["company"], cfg["plan"]["branch"], system, record, version, sha(raw)),
            strict=True,
        )
    )


def _metadata(cfg, system, record, version, raw, at, imported):
    ref = _pin(cfg, system, record, version, raw)
    key = [ref[k] for k in FIELDS[:4]]
    provenance = _provenance(cfg)
    return ref | {
        "event_at": at,
        "available_at": at,
        "imported_at": imported,
        "origin": "AUTHORED_TRAINING_SOURCE",
        "provenance": _json(provenance),
        "command_id": "DQ-" + sha(encoded([key, version])),
        "input_digest": sha(
            _json(
                [key, version - 1, at, at, "AUTHORED_TRAINING_SOURCE", provenance, ref["sha256"]]
            ).encode()
        ),
    }


def _bounds(db):
    _preflight(
        db, "systems", dict.fromkeys(("company", "branch", "system", "owner"), 128), len(SYSTEMS)
    )
    _preflight(db, "versions", NATIVE_LIMITS, 3 + 3 * MAX_COMMANDS)
    _preflight(
        db,
        "quality_commands",
        {"revision": 16, "command_id": 128, "digest": 64, "receipt": LIMIT},
        MAX_COMMANDS,
    )
    _preflight(db, "quality_state", {"id": 16, "revision": 16, "body": LIMIT}, 1)


def _insert(db, cfg, system, record, version, raw, at, imported):
    require(isinstance(raw, bytes) and 0 < len(raw) <= LIMIT, "Bounded original bytes required")
    m = _metadata(cfg, system, record, version, raw, at, imported)
    db.execute(
        "INSERT INTO versions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        tuple(m[k] for k in FIELDS[:5])
        + (
            at,
            at,
            imported,
            m["origin"],
            m["provenance"],
            raw,
            m["sha256"],
            m["command_id"],
            m["input_digest"],
        ),
    )
    _preflight(db, "versions", NATIVE_LIMITS, 3 + 3 * MAX_COMMANDS)
    return {k: m[k] for k in FIELDS}


def _verify(db, cfg, system, record, version, raw, at, imported):
    expected = _metadata(cfg, system, record, version, raw, at, imported)
    row = native(db, {k: expected[k] for k in FIELDS})
    require(
        row["content"] == raw
        and all(type(row[k]) is type(v) and row[k] == v for k, v in expected.items()),
        "Exact native bytes, metadata or command association differ",
    )
    return {k: expected[k] for k in FIELDS}


def _config(root, expected):
    raw = checked_bytes(Path(root) / "RUNTIME.json", LIMIT)
    require(sha(raw) == expected, "Exact runtime definition pin required")
    cfg = decode(raw)
    require(
        cfg.get("format") == "LOCAL_DATA_QUALITY_RUNTIME_V1" and cfg["code_pins"] == _code(),
        "Maintained runtime definition/code changed",
    )
    return cfg


def initialize(destination, *, repository, plan, raw_records):
    """Declare independent local rules and retain provided nonpersonal fixture bytes."""
    destination, repository = Path(destination), Path(repository)
    private(destination.parent, True)
    require(
        destination.is_absolute()
        and destination == destination.resolve()
        and not destination.exists(),
        "New canonical private runtime required",
    )
    plan = _plan(decode(encoded(plan)))
    rows = _rows(raw_records)
    org = snapshot(repository, as_of=plan["declared_at"][:10])
    owners = {
        a["control_id"]: a["primary_person_id"]
        for a in org["control_assignments"]
        if a["control_id"] in CONTROLS
    }
    require(
        set(owners) == set(CONTROLS) and set(owners.values()) == {plan["owner_id"]},
        "All scoped declared steward assignments required",
    )
    cfg = {
        "format": "LOCAL_DATA_QUALITY_RUNTIME_V1",
        "plan": plan,
        "code_pins": _code(),
        "initial_raw_sha256": sha(raw_records),
        "initial_raw_rows": len(rows),
        "imported_at": _now(),
        "organization_source_sha256": org["source_sha256"],
        "qualification": QUALIFICATION,
        "denominator_scope": "EXPECTED_RECORD_IDS_IN_EVENT_WINDOW_ONLY",
        "stewardship": "EXPLICIT_LOCAL_ASSIGNMENT_NOT_CLASSIFICATION_POLICY_ACCEPTANCE",
    }
    raw_cfg = encoded(cfg)
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix="quality-stage-") as folder:
        stage = Path(folder)
        store = CompanyStore(stage)
        for system in SYSTEMS:
            store.register_system(plan["company"], plan["branch"], system, plan["owner_id"])
        with (stage / "RUNTIME.json").open("xb") as f:
            os.chmod(stage / "RUNTIME.json", 0o600)
            f.write(raw_cfg)
            f.flush()
            os.fsync(f.fileno())
        with database(stage, True) as db:
            db.execute(
                "CREATE TABLE quality_commands(revision INTEGER UNIQUE, "
                "command_id TEXT PRIMARY KEY, digest TEXT, receipt BLOB)"
            )
            db.execute(
                "CREATE TABLE quality_state(id INTEGER PRIMARY KEY, revision INTEGER, body BLOB)"
            )
            for action in ("UPDATE", "DELETE"):
                db.execute(
                    f"CREATE TRIGGER quality_no_{action.lower()} BEFORE {action} "
                    "ON quality_commands "
                    "BEGIN SELECT RAISE(ABORT,'Immutable quality command'); END"
                )
            _insert(
                db,
                cfg,
                "quality_definition",
                plan["runtime_id"],
                1,
                raw_cfg,
                plan["declared_at"],
                cfg["imported_at"],
            )
            _insert(
                db,
                cfg,
                "quality_reference",
                "REFERENCE",
                1,
                encoded(plan["reference_rows"]),
                plan["declared_at"],
                cfg["imported_at"],
            )
            initial_pin = _insert(
                db,
                cfg,
                "quality_raw",
                plan["dataset_id"],
                1,
                raw_records,
                plan["input_at"],
                cfg["imported_at"],
            )
            state = {
                "input_pin": initial_pin,
                "event_at": plan["input_at"],
                "imported_at": cfg["imported_at"],
                "last_transform": None,
            }
            db.execute("INSERT INTO quality_state VALUES(1,0,?)", (encoded(state),))
            _bounds(db)
        require(
            _code() == cfg["code_pins"]
            and all(
                sha((repository / p).read_bytes()) == h for p, h in org["source_sha256"].items()
            ),
            "Initialization source/code changed before publication",
        )
        publish(stage, destination)
    return {
        "runtime_sha256": sha(raw_cfg),
        "revision": 0,
        "input_pin": initial_pin,
        "qualification": QUALIFICATION,
    }


def _transform(cfg, rows, at):
    plan = cfg["plan"]
    start, end = (plan["event_window"][k] for k in ("start", "end"))
    require(end <= at, "Query window has not closed at operator event time")
    expected = set(plan["expected_record_ids"])
    reference = {r["entity_id"]: r["category"] for r in plan["reference_rows"]}
    candidates, failures, exclusions = [], [], []
    for i, row in enumerate(rows):
        reasons = []
        if set(row) != ROW_FIELDS:
            reasons.append("ROW_SCHEMA")
        for key in ("record_id", "entity_id"):
            try:
                _id(row.get(key))
            except CompanyStoreError:
                reasons.append("INVALID_" + key.upper())
        try:
            event = _stamp(row.get("observed_at"))
        except CompanyStoreError:
            event = None
            reasons.append("INVALID_EVENT_TIME")
        if not reasons and event is not None and (event < start or event >= end) and event <= at:
            exclusions.append(
                {
                    "index": i,
                    "row_sha256": sha(encoded(row)),
                    "reason": "OUTSIDE_DECLARED_EVENT_WINDOW",
                    "record_id": row["record_id"],
                }
            )
            continue
        if event is not None and event > at:
            reasons.append("FUTURE_EVENT")
        candidates.append((i, row, event, reasons))
    counts = Counter(
        row.get("record_id") for _, row, _, _ in candidates if isinstance(row.get("record_id"), str)
    )
    normalized = []
    seen = set()
    for i, row, event, reasons in candidates:
        ident = row.get("record_id")
        if isinstance(ident, str):
            if event is not None and start <= event < end:
                seen.add(ident)
            if ident not in expected:
                reasons.append("UNEXPECTED_IN_WINDOW_RECORD")
            if counts[ident] > 1:
                reasons.append("DUPLICATE_RECORD_ID")
        entity = row.get("entity_id")
        if not isinstance(entity, str) or entity not in reference:
            reasons.append("REFERENCE_ENTITY_MISMATCH")
        units = row.get("units")
        if type(units) is not int or not 0 <= units <= plan["maximum_units"]:
            reasons.append("INVALID_INTEGER_UNITS")
        if reasons:
            failures.append(
                {"index": i, "row_sha256": sha(encoded(row)), "reasons": sorted(set(reasons))}
            )
        else:
            normalized.append(
                {
                    "record_id": ident,
                    "entity_id": entity,
                    "category": reference[entity],
                    "units": units,
                    "observed_at": event,
                    "source_index": i,
                    "source_row_sha256": sha(encoded(row)),
                }
            )
    missing = sorted(expected - seen)
    missing_usable = sorted(expected - {r["record_id"] for r in normalized})
    status = (
        "PARTIAL_UNRELIABLE" if failures or missing else "LOCAL_RULES_PASSED_NOT_SOURCE_ACCEPTANCE"
    )
    groups = [
        {
            "category": cat,
            "accepted_rows": sum(r["category"] == cat for r in normalized),
            "accepted_units": sum(r["units"] for r in normalized if r["category"] == cat),
        }
        for cat in sorted(set(reference.values()))
    ]
    report = {
        "status": status,
        "input_rows": len(rows),
        "accepted_rows": len(normalized),
        "failed_rows": len(failures),
        "intentional_exclusions": len(exclusions),
        "expected_in_window_records": len(expected),
        "missing_expected_in_window_ids": missing,
        "missing_usable_expected_ids": missing_usable,
        "failures": failures,
        "exclusions": exclusions,
        "query": deepcopy(plan["event_window"]),
        "timezone": "UTC",
        "qualification": QUALIFICATION,
        "source_acceptance": "NOT_ESTABLISHED",
    }
    require(
        len(rows) == len(normalized) + len(failures) + len(exclusions), "Row reconciliation failed"
    )
    derived = {
        "status": status,
        "records": normalized,
        "query": report["query"],
        "qualification": QUALIFICATION,
    }
    aggregate = {
        "status": status,
        "groups": groups,
        "accepted_rows_only_total": sum(r["units"] for r in normalized),
        "missing_usable_expected_ids": missing_usable,
        "qualification": QUALIFICATION,
    }
    return report, derived, aggregate


def _apply(cfg, state, raw, request, revision, command, imported):
    _keys(request, "expected_revision actor_id operation event_at rationale parameters")
    require(
        type(request["expected_revision"]) is int
        and request["expected_revision"] == revision
        and request["actor_id"] == cfg["plan"]["owner_id"],
        "Exact local operator and CAS required",
    )
    at = _stamp(request["event_at"])
    require(
        at == request["event_at"]
        and at >= state["event_at"]
        and _stamp(imported) == imported
        and imported >= state["imported_at"],
        "Local event/import chronology differs",
    )
    require(
        isinstance(request["rationale"], str) and 1 <= len(request["rationale"].strip()) <= 2000,
        "Explicit local source rationale required",
    )
    args = request["parameters"]
    require(isinstance(args, dict), "Typed operation parameters required")
    exact_pin(args.get("input_pin"))
    require(
        encoded(args["input_pin"]) == encoded(state["input_pin"]),
        "Exact current raw source pin required",
    )
    rows = _rows(raw)
    after = deepcopy(state)
    after.update(event_at=at, imported_at=imported)
    products = []
    if request["operation"] == "TRANSFORM":
        _keys(args, "input_pin")
        report, derived, aggregate = _transform(cfg, rows, at)
        products = [
            ("quality_derived", f"TRANSFORM-{revision + 1}", 1, encoded(derived)),
            ("quality_aggregate", f"TRANSFORM-{revision + 1}", 1, encoded(aggregate)),
        ]
        observation = {
            "input_pin": state["input_pin"],
            "reference_pin": _pin(
                cfg, "quality_reference", "REFERENCE", 1, encoded(cfg["plan"]["reference_rows"])
            ),
            "definition_pin": _pin(
                cfg, "quality_definition", cfg["plan"]["runtime_id"], 1, encoded(cfg)
            ),
            "report": report,
        }
        after["last_transform"] = {
            "command_id": command,
            "input_pin": state["input_pin"],
            "observation_sha256": sha(encoded(observation)),
        }
    elif request["operation"] == "CORRECT":
        _keys(args, "input_pin replacements")
        changes = args["replacements"]
        require(
            isinstance(changes, list) and 1 <= len(changes) <= 16,
            "Bounded explicit row replacements required",
        )
        used = set()
        lineage = []
        for change in changes:
            _keys(change, "index before_row_sha256 replacement")
            index = change["index"]
            require(
                type(index) is int and 0 <= index < len(rows) and index not in used,
                "Exact distinct raw row index required",
            )
            require(
                change["before_row_sha256"] == sha(encoded(rows[index]))
                and isinstance(change["replacement"], dict),
                "Exact before-row hash and replacement object required",
            )
            used.add(index)
            after_row = sha(encoded(change["replacement"]))
            require(after_row != change["before_row_sha256"], "Explicit changed row required")
            lineage.append(
                {
                    "index": index,
                    "before_row_sha256": change["before_row_sha256"],
                    "after_row_sha256": after_row,
                }
            )
            rows[index] = deepcopy(change["replacement"])
        successor = encoded(rows)
        _rows(successor)
        products = [
            ("quality_raw", cfg["plan"]["dataset_id"], state["input_pin"]["version"] + 1, successor)
        ]
        after["input_pin"] = _pin(cfg, *products[0])
        after["last_transform"] = None
        observation = {
            "prior_input_pin": state["input_pin"],
            "corrected_input_pin": after["input_pin"],
            "row_lineage": lineage,
            "row_count_preserved": len(rows),
            "quality_requires_new_transform": True,
            "serialization": "CANONICAL_JSON_UNCHANGED_ROW_VALUES_PRESERVED_FORMATTING_MAY_CHANGE",
            "approval": "LOCAL_OPERATOR_ASSERTION_NOT_MANAGER_ACCEPTANCE",
        }
        raw = successor
    else:
        raise CompanyStoreError("Only TRANSFORM or CORRECT is supported")
    return after, raw, products, observation


def _history(db, cfg):
    _bounds(db)
    systems = db.execute("SELECT company,branch,system,owner FROM systems").fetchall()
    require(
        {tuple(r) for r in systems}
        == {
            (cfg["plan"]["company"], cfg["plan"]["branch"], s, cfg["plan"]["owner_id"])
            for s in SYSTEMS
        },
        "Exact owner systems required",
    )
    p = cfg["plan"]
    _verify(
        db,
        cfg,
        "quality_definition",
        p["runtime_id"],
        1,
        encoded(cfg),
        p["declared_at"],
        cfg["imported_at"],
    )
    _verify(
        db,
        cfg,
        "quality_reference",
        "REFERENCE",
        1,
        encoded(p["reference_rows"]),
        p["declared_at"],
        cfg["imported_at"],
    )
    initial_ref = dict(
        zip(
            FIELDS,
            (
                p["company"],
                p["branch"],
                "quality_raw",
                p["dataset_id"],
                1,
                cfg["initial_raw_sha256"],
            ),
            strict=True,
        )
    )
    raw = native(db, initial_ref)["content"]
    require(len(_rows(raw)) == cfg["initial_raw_rows"], "Initial row count differs")
    _verify(db, cfg, "quality_raw", p["dataset_id"], 1, raw, p["input_at"], cfg["imported_at"])
    state = {
        "input_pin": initial_ref,
        "event_at": p["input_at"],
        "imported_at": cfg["imported_at"],
        "last_transform": None,
    }
    receipts = {}
    commands = db.execute("SELECT * FROM quality_commands ORDER BY revision").fetchall()
    expected_count = 3
    for revision, row in enumerate(commands):
        receipt = decode(row["receipt"])
        _keys(
            receipt,
            "revision command_id request request_sha256 prior_state_sha256 state_sha256 "
            "event_at imported_at observation outputs runtime_sha256 qualification operation_pin",
        )
        require(
            type(receipt["revision"]) is int
            and receipt["revision"] == revision + 1 == row["revision"]
            and receipt["command_id"] == row["command_id"]
            and receipt["request_sha256"] == row["digest"] == sha(encoded(receipt["request"]))
            and receipt["prior_state_sha256"] == sha(encoded(state))
            and receipt["runtime_sha256"] == sha(encoded(cfg))
            and receipt["qualification"] == QUALIFICATION,
            "Exact retained command envelope differs",
        )
        _id(row["command_id"])
        after, raw, products, observation = _apply(
            cfg, state, raw, receipt["request"], revision, row["command_id"], receipt["imported_at"]
        )
        refs = [
            _verify(db, cfg, *product, receipt["event_at"], receipt["imported_at"])
            for product in products
        ]
        require(
            receipt["event_at"] == after["event_at"]
            and encoded(receipt["outputs"]) == encoded(refs)
            and encoded(receipt["observation"]) == encoded(observation)
            and receipt["state_sha256"] == sha(encoded(after)),
            "Recomputed transformation/correction differs",
        )
        body = {k: v for k, v in receipt.items() if k != "operation_pin"}
        op = _verify(
            db,
            cfg,
            "quality_operation",
            f"OP-{revision + 1}",
            1,
            encoded(body),
            receipt["event_at"],
            receipt["imported_at"],
        )
        require(encoded(op) == encoded(receipt["operation_pin"]), "Operation pin differs")
        state = after
        expected_count += len(products) + 1
        receipts[row["command_id"]] = receipt
    current = db.execute("SELECT * FROM quality_state").fetchall()
    require(
        len(current) == 1
        and current[0]["id"] == 1
        and current[0]["revision"] == len(commands)
        and encoded(decode(current[0]["body"])) == encoded(state)
        and db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == expected_count,
        "Current state or original count differs from replayed operations",
    )
    return len(commands), state, raw, receipts


def execute(
    root,
    *,
    expected_runtime_sha256,
    expected_revision,
    command_id,
    actor_id,
    operation,
    event_at,
    rationale,
    parameters,
):
    require(
        type(expected_revision) is int and 0 <= expected_revision <= MAX_COMMANDS,
        "Exact bounded revision required",
    )
    _id(command_id)
    _id(actor_id)
    cfg = _config(root, expected_runtime_sha256)
    require(actor_id == cfg["plan"]["owner_id"], "Exact configured local operator required")
    request = {
        "expected_revision": expected_revision,
        "actor_id": actor_id,
        "operation": operation,
        "event_at": _stamp(event_at),
        "rationale": rationale,
        "parameters": decode(encoded(parameters)),
    }
    require(len(encoded(request)) <= 65536, "Bounded explicit command required")
    with database(Path(root), True) as db:
        revision, state, raw, receipts = _history(db, cfg)
        if command_id in receipts:
            require(
                encoded(receipts[command_id]["request"]) == encoded(request),
                "Changed exact replay envelope",
            )
            require(_config(root, expected_runtime_sha256) == cfg, "Runtime changed during replay")
            return receipts[command_id]
        require(
            revision == expected_revision and revision < MAX_COMMANDS,
            "Revision conflict or runtime command limit",
        )
        imported = _now()
        after, raw, products, observation = _apply(
            cfg, state, raw, request, revision, command_id, imported
        )
        outputs = [
            _insert(db, cfg, *product, request["event_at"], imported) for product in products
        ]
        body = {
            "revision": revision + 1,
            "command_id": command_id,
            "request": request,
            "request_sha256": sha(encoded(request)),
            "prior_state_sha256": sha(encoded(state)),
            "state_sha256": sha(encoded(after)),
            "event_at": request["event_at"],
            "imported_at": imported,
            "observation": observation,
            "outputs": outputs,
            "runtime_sha256": expected_runtime_sha256,
            "qualification": QUALIFICATION,
        }
        op = _insert(
            db,
            cfg,
            "quality_operation",
            f"OP-{revision + 1}",
            1,
            encoded(body),
            request["event_at"],
            imported,
        )
        receipt = body | {"operation_pin": op}
        db.execute(
            "INSERT INTO quality_commands VALUES(?,?,?,?)",
            (revision + 1, command_id, body["request_sha256"], encoded(receipt)),
        )
        db.execute(
            "UPDATE quality_state SET revision=?,body=? WHERE id=1", (revision + 1, encoded(after))
        )
        _bounds(db)
        require(_config(root, expected_runtime_sha256) == cfg, "Runtime changed before commit")
    return receipt


def inspect(root, *, expected_runtime_sha256, as_of):
    cfg = _config(root, expected_runtime_sha256)
    with database(Path(root)) as db:
        revision, state, _, _ = _history(db, cfg)
        require(_stamp(as_of) >= state["event_at"], "Current state unavailable at requested cutoff")
        require(_config(root, expected_runtime_sha256) == cfg, "Runtime changed during inspection")
    return {"revision": revision, "state": state, "qualification": QUALIFICATION}
