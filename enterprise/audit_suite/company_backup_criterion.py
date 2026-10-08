"""Exact prospective local simulation criterion; never enterprise risk acceptance."""

from datetime import datetime, timedelta
from pathlib import Path

from .company_backup_runtime import database, exact_pin, native, private, require
from .company_store import _time
from .inference import _json as decode
from .operating_source_bridge import encoded, sha

FIELDS = ("company", "branch", "system", "record", "version", "sha256")
MAX_CONTENT = 32768
MAX_METADATA = 16384
SYSTEM = "local_backup_risk_decisions"


def resolve(dependency, *, scope, plan, author, reviewer, as_of):
    require(
        isinstance(dependency, dict) and set(dependency) == {"root", "native", "metadata_sha256"},
        "Exact local criterion dependency required",
    )
    require(isinstance(dependency["root"], str), "Typed criterion root required")
    root = private(Path(dependency["root"]), True)
    require(
        str(root) == dependency["root"] and root.is_absolute(),
        "Exact private criterion root required",
    )
    ref = dependency["native"]
    exact_pin(ref)
    require(
        ref["company"] == plan["company_id"]
        and ref["branch"] == plan["branch_id"]
        and ref["system"] == SYSTEM,
        "Criterion company/branch/system differs",
    )
    pin = dependency["metadata_sha256"]
    require(
        isinstance(pin, str) and len(pin) == 64 and all(c in "0123456789abcdef" for c in pin),
        "Exact criterion metadata digest required",
    )
    where = " AND ".join(k + "=?" for k in FIELDS[:-1])
    metadata = (
        "company",
        "branch",
        "system",
        "record",
        "version",
        "sha256",
        "event_at",
        "available_at",
        "imported_at",
        "origin",
        "provenance",
        "command_id",
        "input_digest",
    )
    expression = "+".join("COALESCE(length(CAST(" + k + " AS BLOB)),0)" for k in metadata)
    with database(root) as db:
        sizes = db.execute(
            "SELECT length(content)," + expression + " FROM versions WHERE " + where,
            tuple(ref[k] for k in FIELDS[:-1]),
        ).fetchone()
        require(
            sizes is not None
            and type(sizes[0]) is int
            and sizes[0] <= MAX_CONTENT
            and type(sizes[1]) is int
            and sizes[1] <= MAX_METADATA,
            "Bounded criterion content and metadata required",
        )
        owner = db.execute(
            "SELECT owner FROM systems WHERE company=? AND branch=? AND system=? AND owner=?",
            (ref["company"], ref["branch"], ref["system"], author),
        ).fetchone()
        require(owner is not None, "Criterion registered author custody differs")
        row = dict(native(db, ref, as_of))
    require(row["origin"] == "AUTHORED_TRAINING_SOURCE", "Authored local criterion origin required")
    raw = row.pop("content")
    require(sha(encoded(row)) == pin, "Criterion native metadata changed")
    body = decode(raw)
    validate(body, scope=scope, plan=plan, author=author, reviewer=reviewer)
    require(
        row["event_at"] == body["approved_at"]
        and row["event_at"] <= row["available_at"] <= plan["declared_at"]
        and row["available_at"] <= as_of,
        "Criterion approval must be available before declaration",
    )
    return {
        "dependency": dependency,
        "criterion": body,
        "qualification": "APPROVED_LOCAL_SIMULATION_RULE_ONLY_NOT_ENTERPRISE_ACCEPTANCE",
    }


def seconds(a, b):
    return (datetime.fromisoformat(a) - datetime.fromisoformat(b)).total_seconds()


def validate(body, *, scope, plan, author, reviewer):
    keys = {
        "format",
        "status",
        "scope",
        "author_id",
        "reviewer_id",
        "approved_at",
        "effective_from",
        "effective_to_exclusive",
        "max_age_seconds",
        "checkpoint_interval_seconds",
        "publication_allowance_seconds",
        "retention",
        "isolation",
        "rationale",
    }
    require(isinstance(body, dict) and set(body) == keys, "Exact backup criterion schema required")
    require(
        body["format"] == "LOCAL_BACKUP_DATA_LOSS_CRITERION_V1"
        and body["status"] == "LOCAL_SIMULATION_RULE_APPROVED",
        "Approved local rule required",
    )
    require(encoded(body["scope"]) == encoded(scope), "Criterion exact backup scope differs")
    require(
        body["author_id"] == author and body["reviewer_id"] == reviewer and author != reviewer,
        "Distinct scoped author/reviewer required",
    )
    for key in ["approved_at", "effective_from", "effective_to_exclusive"]:
        require(
            isinstance(body[key], str) and _time(body[key]) == body[key],
            "Canonical criterion time required",
        )
    require(
        body["approved_at"] <= plan["declared_at"]
        and body["approved_at"] <= body["effective_from"] <= plan["period_start"]
        and body["effective_to_exclusive"] >= plan["period_end_exclusive"],
        "Criterion effective chronology differs",
    )
    for key in ["max_age_seconds", "checkpoint_interval_seconds", "publication_allowance_seconds"]:
        require(
            type(body[key]) is int and 1 <= body[key] <= 366 * 86400,
            "Bounded integer criterion required",
        )
    interval, delay, maximum = (
        body[k]
        for k in ["checkpoint_interval_seconds", "publication_allowance_seconds", "max_age_seconds"]
    )
    require(
        interval + delay <= maximum, "Planned interval plus publication allowance exceeds criterion"
    )
    require(
        body["retention"] == "RETAIN_ALL_LOCAL_EXERCISE_ORIGINALS_NO_DELETION"
        and body["isolation"] == "PRIVATE_LOCAL_STORE_NOT_PRODUCTION_ISOLATION",
        "Exact local retention/isolation qualification required",
    )
    require(
        isinstance(body["rationale"], str)
        and body["rationale"].strip()
        and len(body["rationale"]) <= 2000,
        "Bounded authored rationale required",
    )
    for dataset in scope["dataset_ids"]:
        slots = sorted(
            [
                s
                for s in plan["schedule"]
                if s["control_id"] == "SH-BCM-002" and s["inventory_ids"] == [dataset]
            ],
            key=lambda s: s["window_start"],
        )
        require(
            slots and slots[0]["window_start"] == plan["period_start"],
            "Explicit initial checkpoint required",
        )
        require(
            all(
                seconds(b["window_start"], a["window_start"]) == interval
                for a, b in zip(slots, slots[1:], strict=False)
            ),
            "Declared checkpoint cadence differs",
        )
        require(
            all(seconds(s["due_at"], s["window_start"]) == delay for s in slots),
            "Declared publication allowance differs",
        )
        require(
            0 < seconds(plan["period_end_exclusive"], slots[-1]["window_start"]) <= interval,
            "Last checkpoint does not cover period end",
        )


def check(cfg, as_of):
    selected = cfg.get("local_data_loss_criterion")
    if selected is None:
        return
    for name in [
        "company_backup_criterion.py",
        "company_backup_runtime.py",
        "company_backup_monitor.py",
    ]:
        require(
            sha(Path(__file__).with_name(name).read_bytes())
            == cfg["source_sha256"].get("enterprise/audit_suite/" + name),
            "Criterion implementation changed",
        )
    value = resolve(
        selected["dependency"],
        scope={"service_id": cfg["service_id"], "dataset_ids": sorted(cfg["datasets"])},
        plan=cfg["plan"],
        author=cfg["operator_id"],
        reviewer=cfg["operating_reviewer_id"],
        as_of=as_of,
    )
    require(encoded(value) == encoded(selected), "Bound local criterion changed")


def age_intervals(points, *, start, end, maximum):
    """Freshest available checkpoint; later publication of old data cannot regress it."""
    events = sorted(points, key=lambda p: (p["published_at"], p["checkpoint_at"]))
    cursor, checkpoint = start, None
    intervals = []
    for p in events:
        require(p["checkpoint_at"] <= p["published_at"], "Checkpoint published before creation")
        if p["published_at"] > end:
            continue
        if p["published_at"] >= start:
            if cursor < p["published_at"]:
                age = None if checkpoint is None else seconds(p["published_at"], checkpoint)
                intervals.append(
                    {
                        "from": cursor,
                        "to": p["published_at"],
                        "checkpoint_at": checkpoint,
                        "maximum_age_seconds": age,
                        "status": "UNESTABLISHED"
                        if age is None
                        else ("BREACH" if age > maximum else "WITHIN_LOCAL_CRITERION"),
                    }
                )
            cursor = p["published_at"]
        checkpoint = max(checkpoint, p["checkpoint_at"]) if checkpoint else p["checkpoint_at"]
    if cursor < end:
        age = None if checkpoint is None else seconds(end, checkpoint)
        intervals.append(
            {
                "from": cursor,
                "to": end,
                "checkpoint_at": checkpoint,
                "maximum_age_seconds": age,
                "status": "UNESTABLISHED"
                if age is None
                else ("BREACH" if age > maximum else "WITHIN_LOCAL_CRITERION"),
            }
        )
    for interval in intervals:
        interval["breach_after"] = (
            (
                datetime.fromisoformat(interval["checkpoint_at"]) + timedelta(seconds=maximum)
            ).isoformat(timespec="microseconds")
            if interval["status"] == "BREACH"
            else None
        )
    return intervals


def _proof_snapshot(db, cfg):
    """Bound before materialization, then stream exact inspected native bytes/metadata."""
    from hashlib import sha256

    from . import company_backup_runtime as backup

    metadata = "+".join(
        "coalesce(length(CAST(" + key + " AS BLOB)),0)"
        for key in [
            "company",
            "branch",
            "system",
            "record",
            "version",
            "sha256",
            "event_at",
            "available_at",
            "imported_at",
            "provenance",
            "origin",
            "command_id",
            "input_digest",
        ]
    )
    bounds = db.execute(
        "SELECT count(*),coalesce(sum(length(content)),0),coalesce(max("
        + metadata
        + "),0),sum(CASE WHEN typeof(version)!='integer' THEN 1 ELSE 0 END),"
        "coalesce(max(length(content)),0),"
        "coalesce(max(CASE WHEN system='backup_job' THEN length(content) ELSE 0 END),0) "
        "FROM versions WHERE system IN "
        "('backup_job','source_dataset','backup_object','runtime_definition')"
    ).fetchone()
    require(
        bounds[0] <= 4096
        and bounds[1] <= 64 * 1024 * 1024
        and bounds[2] <= 16384
        and not bounds[3]
        and bounds[4] <= 16 * 1024 * 1024
        and bounds[5] <= 32768,
        "Bounded native copy proof required",
    )
    digest = sha256()
    for row in db.execute(
        "SELECT * FROM versions WHERE system IN "
        "('backup_job','source_dataset','backup_object','runtime_definition') "
        "ORDER BY company,branch,system,record,version"
    ):
        value = dict(row)
        raw = value.pop("content")
        require(isinstance(raw, bytes) and sha(raw) == value["sha256"], "Native proof bytes differ")
        require(
            value["company"] == cfg["plan"]["company_id"]
            and value["branch"] == cfg["plan"]["branch_id"]
            and type(value["version"]) is int
            and value["version"] >= 1
            and value["origin"] == "AUTHORED_TRAINING_SOURCE",
            "Native proof identity/origin differs",
        )
        for key in ["event_at", "available_at", "imported_at"]:
            require(
                isinstance(value[key], str) and _time(value[key]) == value[key],
                "Canonical native proof time required",
            )
        require(value["event_at"] == value["available_at"], "Runtime native availability differs")
        provenance = decode(value["provenance"])
        expected = {
            "source_reference": cfg["plan"]["period_id"],
            "classification": backup.QUALIFICATION,
            "control_ids": ["SH-BCM-002", "SH-BCM-003"],
            "declaration": cfg["declaration_ref"],
            "runtime_id": cfg["runtime_id"],
        }
        if "source_admission" in provenance and value["system"] == "source_dataset":
            expected["source_admission"] = provenance["source_admission"]
        if "name" in provenance or "content_type" in provenance:
            dataset_id = (
                value["record"]
                if value["system"] == "source_dataset"
                else cfg["bindings"][value["record"]]["dataset_id"]
                if value["system"] in {"backup_object", "restored_dataset"}
                else None
            )
            json_native = dataset_id is None or cfg["datasets"][dataset_id] == "JSON_RECORDS"
            expected.update(
                name=value["record"] + (".json" if json_native else ".bin"),
                content_type="application/json" if json_native else "application/octet-stream",
            )
        require(encoded(provenance) == encoded(expected), "Native proof provenance differs")
        key = [value[k] for k in ["company", "branch", "system", "record"]]
        require(
            value["input_digest"]
            == sha(
                backup._json(
                    [
                        key,
                        value["version"] - 1,
                        value["event_at"],
                        value["available_at"],
                        value["origin"],
                        provenance,
                        value["sha256"],
                    ]
                ).encode()
            ),
            "Native proof input digest differs",
        )
        data = encoded({**value, "content_bytes": len(raw)})
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def _checkpoint(source, cfg, runtime_sha256):
    """Admission republishes bytes; it must never rejuvenate their producer checkpoint."""
    dependency = decode(source["provenance"]).get("source_admission")
    if dependency is None:
        return source["event_at"], "DIRECT_AUTHORED_CHECKPOINT", None
    keys = {
        "source_store_id",
        "source_location_sha256",
        "source_definition_pin",
        "source_pin",
        "metadata",
        "definition_metadata",
        "metadata_sha256",
        "identity_basis",
        "dataset_id",
        "consumer_runtime_sha256",
        "consumer_runtime_id",
        "consumed_at",
        "qualification",
        "execution_source_sha256",
    }
    require(
        isinstance(dependency, dict) and set(dependency) == keys,
        "Exact retained admission dependency required",
    )
    exact_pin(dependency["source_pin"])
    exact_pin(dependency["source_definition_pin"])
    metadata, definition = dependency["metadata"], dependency["definition_metadata"]
    fields = {*FIELDS, "event_at", "available_at", "origin", "provenance"}
    require(
        isinstance(metadata, dict)
        and set(metadata) == fields
        and isinstance(definition, dict)
        and set(definition) == fields,
        "Exact retained producer metadata required",
    )
    require(
        encoded({k: metadata[k] for k in FIELDS}) == encoded(dependency["source_pin"])
        and encoded({k: definition[k] for k in FIELDS})
        == encoded(dependency["source_definition_pin"])
        and metadata["sha256"] == source["sha256"]
        and sha(encoded({"original": metadata, "definition": definition}))
        == dependency["metadata_sha256"],
        "Retained producer byte/metadata binding differs",
    )
    require(
        dependency["consumer_runtime_sha256"] == runtime_sha256
        and dependency["consumer_runtime_id"] == cfg["runtime_id"]
        and dependency["dataset_id"] == source["record"]
        and dependency["consumed_at"] == source["event_at"],
        "Retained admission consumer linkage differs",
    )
    for key in ["event_at", "available_at"]:
        require(
            isinstance(metadata[key], str) and _time(metadata[key]) == metadata[key],
            "Canonical producer checkpoint time required",
        )
    require(
        metadata["event_at"] <= metadata["available_at"] <= source["event_at"],
        "Producer checkpoint chronology differs",
    )
    return (
        metadata["event_at"],
        "RETAINED_ADMISSION_PRODUCER_CHECKPOINT_NOT_FRESH_UPSTREAM_READ",
        dependency["source_pin"],
    )


def evaluate(runtime, *, expected_runtime_sha256, as_of):
    """Re-read successful local copies; no application or enterprise recovery claim."""
    from . import company_backup_runtime as backup

    root = private(Path(runtime), True)
    cfg = backup._config(root, expected_runtime_sha256)
    at = _time(as_of)
    require("local_data_loss_criterion" in cfg, "Explicit local criterion required")
    check(cfg, at)
    body = cfg["local_data_loss_criterion"]["criterion"]
    require(
        cfg["plan"]["period_start"] <= at <= cfg["plan"]["period_end_exclusive"],
        "Evaluation cutoff outside declared period",
    )
    points = {name: [] for name in cfg["datasets"]}
    copy_pins = {}
    failed = []
    late = []
    with database(root) as db:
        initial_proof = _proof_snapshot(db, cfg)
        backup._bound_config(db, cfg, expected_runtime_sha256)
        initial_state = tuple(db.execute("SELECT * FROM backup_runtime_state").fetchone())
        for row in db.execute(
            "SELECT * FROM versions WHERE company=? AND branch=? "
            "AND system='backup_job' AND available_at<=? ORDER BY available_at,record,version",
            (cfg["plan"]["company_id"], cfg["plan"]["branch_id"], at),
        ):
            require(sha(row["content"]) == row["sha256"], "Job bytes changed")
            job = decode(row["content"])
            binding = cfg["bindings"].get(row["record"])
            require(
                binding is not None
                and binding["operation"] == "BACKUP"
                and job["dataset_id"] == binding["dataset_id"]
                and job["occurrence_id"] == row["record"]
                and job["runtime_id"] == cfg["runtime_id"]
                and job["business_attempted_at"] == row["event_at"]
                and row["event_at"] <= row["available_at"],
                "Job identity/chronology differs",
            )
            if job["status"] == "FAILED":
                failed.append({"occurrence_id": row["record"], "job_sha256": row["sha256"]})
                continue
            require(
                job["status"] == "COMPLETED" and job["error_code"] is None,
                "Successful local copy required",
            )
            require(
                type(job["copied_bytes"]) is int
                and job["copied_bytes"] >= 0
                and type(job["actual_elapsed_seconds"]) in (int, float)
                and job["actual_elapsed_seconds"] >= 0,
                "Actual local copy result required",
            )
            source = native(db, job["source_pin"], at)
            obj = native(db, job["object_pin"], at)
            require(
                source["system"] == "source_dataset"
                and source["record"] == binding["dataset_id"]
                and obj["system"] == "backup_object"
                and obj["record"] == row["record"]
                and all(
                    r["company"] == cfg["plan"]["company_id"]
                    and r["branch"] == cfg["plan"]["branch_id"]
                    for r in [source, obj]
                ),
                "Exact local copy/source identity required",
            )
            require(
                obj["event_at"] == obj["available_at"] == row["available_at"],
                "Object publication differs from successful job",
            )
            path = root / job["copy_path"]
            require(
                path.resolve().is_relative_to((root / "attempts").resolve()),
                "Owned copy path required",
            )
            raw = backup.checked_bytes(path)
            require(
                raw == obj["content"] == source["content"] and len(raw) == job["copied_bytes"],
                "Successful copied bytes differ from exact source/object",
            )
            if cfg["datasets"][binding["dataset_id"]] == "JSON_RECORDS":
                backup._records(raw)
            copy_pins[str(path)] = sha(raw)
            checkpoint, checkpoint_basis, producer_pin = _checkpoint(
                source, cfg, expected_runtime_sha256
            )
            require(
                checkpoint is not None and source["available_at"] <= row["available_at"],
                "Checkpoint chronology unavailable",
            )
            point = {
                "occurrence_id": row["record"],
                "checkpoint_at": checkpoint,
                "checkpoint_basis": checkpoint_basis,
                "producer_pin": producer_pin,
                "published_at": row["available_at"],
                "source_pin": job["source_pin"],
                "object_pin": job["object_pin"],
                "job_sha256": row["sha256"],
                "job_pin": backup.pin(row),
                "job_metadata_sha256": sha(
                    encoded({k: row[k] for k in row.keys() if k != "content"})
                ),
                "verification": (
                    "EXACT_BYTES_AND_JSON_RECORDS_PARSE"
                    if cfg["datasets"][binding["dataset_id"]] == "JSON_RECORDS"
                    else "EXACT_BYTES_ONLY"
                ),
            }
            points[binding["dataset_id"]].append(point)
            if seconds(point["published_at"], checkpoint) > body["publication_allowance_seconds"]:
                late.append(point)
    result = {}
    for dataset, selected in points.items():
        intervals = age_intervals(
            selected, start=cfg["plan"]["period_start"], end=at, maximum=body["max_age_seconds"]
        )
        completed = {p["occurrence_id"] for p in selected}
        result[dataset] = {
            "points": selected,
            "intervals": intervals,
            "unestablished_intervals": [i for i in intervals if i["status"] == "UNESTABLISHED"],
            "age_breach_intervals": [i for i in intervals if i["status"] == "BREACH"],
            "due_without_success": [
                s["id"]
                for s in cfg["plan"]["schedule"]
                if s["control_id"] == "SH-BCM-002"
                and s["inventory_ids"] == [dataset]
                and s["due_at"] <= at
                and s["id"] not in completed
            ],
        }
    require(
        all(sha(backup.checked_bytes(Path(p))) == value for p, value in copy_pins.items()),
        "Copy changed during evaluation",
    )
    with database(root) as db:
        require(_proof_snapshot(db, cfg) == initial_proof, "Native proof changed during evaluation")
        backup._bound_config(db, cfg, expected_runtime_sha256)
        require(
            tuple(db.execute("SELECT * FROM backup_runtime_state").fetchone()) == initial_state,
            "Runtime advanced during evaluation",
        )
    check(cfg, at)
    require(
        backup._config(root, expected_runtime_sha256) == cfg, "Definition changed during evaluation"
    )
    return {
        "datasets": result,
        "failed_attempts": failed,
        "publication_allowance_violations": late,
        "as_of": at,
        "whole_period_effectiveness": "NOT_ASSESSED",
        "qualification": (
            "LOGICAL_LOCAL_CHECKPOINT_AGE_AND_BYTE_PARSE_PROOF_"
            "NOT_APPLICATION_RECOVERY_OR_ENTERPRISE_RPO"
        ),
    }
