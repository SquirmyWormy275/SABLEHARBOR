"""Finite trusted-local source-edition operations before a fresh audit birth.

An explicit external source admission authorizes a new fictional edition. The
immutable seed is activated with every original field intact. Only a fixed set
of existing business APIs is callable; no audit Engine, Key, rubric or model is
an input or output. Real registration/import time remains separate from the
explicit simulated clocks. A checkpoint is an operation receipt, not an audit
outcome/evidence cache: resume replays normal idempotent source commands freshly.
"""

import fcntl
import inspect
import os
import stat
from contextlib import closing
from pathlib import Path

from . import company_backup_runtime as backup
from . import company_backup_use_probe as use
from . import company_operating_depth_runtime as depth
from . import company_operating_period as period
from . import company_policy_delivery_runtime as policy
from . import company_runtime_activation as activation
from .company_store import CompanyStore, CompanyStoreError, _id, _now, _time
from .inference import _json as decode
from .operating_source_bridge import encoded, sha
from .organization import snapshot

PLAN = "SH_EXPLICIT_FICTIONAL_OPERATING_SOURCE_EDITION_PLAN_V1"
ADMISSION = "SH_ROOT_OPERATING_SOURCE_EDITION_ADMISSION_V1"
QUALIFICATION = "FICTIONAL_LOCAL_SOURCE_EDITION_NOT_ENTERPRISE_OR_HUMAN_ACCEPTANCE"
MAX_PLAN = 4 * 1024 * 1024
MAX_STEPS = 256
CONCRETE_SHA = "f754b0af37c8c1c00dba8573ebaeb88bfa44fd3124419176a1488d2553a4c849"
PIN_FIELDS = {"path", "sha256"}
PATH_ARGUMENTS = {
    "root",
    "runtime",
    "runtime_root",
    "declaration_root",
    "destination",
    "source_root",
}

# This literal registry is the complete callable surface. No import or callback
# is supplied by a plan. Fields are also checked against these exact signatures.
OPERATIONS = {
    "REGISTER_CALENDAR": (depth.register_declaration, "company"),
    "PERIOD_CENSUS": (depth.person_period_joins, "company"),
    "IAM_FOLLOWUP": (depth.access_followup, "company"),
    "RETRY_PROBE": (depth.retry_probe, "company"),
    "POLICY_BIND": (depth.policy_binding, "company"),
    "RESTORE_RETURN": (depth.restore_return, "company"),
    "RESTORE_FAILURE": (depth.restore_failure, "company"),
    "PERIOD_DECLARE": (period.create_period, "period"),
    "POLICY_INITIALIZE": (policy.initialize_native, "initialize"),
    "POLICY_EXECUTE": (policy.execute, "runtime"),
    "BACKUP_INITIALIZE": (backup.initialize, "initialize"),
    "DATASET_COPY": (backup.append_dataset, "runtime"),
    "LEASE_RECORD": (backup.record_lease, "runtime"),
    "USE_CONTRACT": (use.record_use_contract, "runtime"),
    "BACKUP_RUN": (backup.run_backup, "runtime"),
    "RESTORE_RUN": (backup.run_restore, "runtime"),
    "USE_PROBE": (use.run_restore_use_probe, "runtime"),
}


def require(condition, message):
    if not condition:
        raise CompanyStoreError(message)


def keys(value, fields):
    require(type(value) is dict and set(value) == set(fields.split()), "Exact edition fields")


def checksum(value):
    require(
        type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value),
        "Literal SHA256 required",
    )


def identity(path, directory=False):
    path = Path(path)
    require(path.is_absolute() and ".." not in path.parts, "Literal absolute path required")
    require(not any(p.is_symlink() for p in (path, *path.parents)), "Edition path alias")
    info = path.lstat()
    require(
        (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
        and not info.st_mode & 0o077
        and (directory or info.st_nlink == 1),
        "Private ordinary edition input required",
    )
    return [
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
        info.st_mode,
        info.st_nlink,
    ]


def read_pin(reference, maximum=MAX_PLAN):
    keys(reference, "path sha256")
    checksum(reference["sha256"])
    path = Path(reference["path"])
    opening = identity(path)
    require(opening[2] <= maximum, "Edition input exceeds bound")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    require(len(raw) <= maximum and sha(raw) == reference["sha256"], "Edition input bytes differ")
    require(identity(path) == opening, "Edition input changed while consumed")
    body = decode(raw.decode("utf-8"))
    require(type(body) is dict, "Typed edition object required")
    return body, opening


def write_new(path, value):
    raw = encoded(value)
    require(len(raw) <= MAX_PLAN, "Bounded edition receipt required")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)
    return {"path": str(path), "sha256": sha(raw)}


def _code():
    from . import (
        company_backup_criterion,
        company_backup_monitor,
        company_lifecycle_activity,
        company_store,
        inference,
        operating_source_bridge,
        organization,
    )

    modules = (
        activation,
        depth,
        period,
        policy,
        backup,
        use,
        company_store,
        inference,
        company_lifecycle_activity,
        company_backup_criterion,
        company_backup_monitor,
        operating_source_bridge,
        organization,
    )
    paths = {Path(__file__), *(Path(module.__file__) for module in modules)}
    return {str(path): sha(path.read_bytes()) for path in sorted(paths)}


def _arguments(action):
    function, category = OPERATIONS[action]
    # Public copy/restore wrappers intentionally accept **kwargs. The admitted
    # surface here is the exact existing implementation signature, never a
    # caller-defined extension to it.
    params = inspect.signature(
        backup._run if action in {"BACKUP_RUN", "RESTORE_RUN"} else function
    ).parameters
    omitted = {"repository"}
    if category in {"company", "initialize", "period"}:
        omitted.add(next(iter(params)))
    if action in {"BACKUP_RUN", "RESTORE_RUN"}:
        omitted.add("operation")
    allowed = set(params) - omitted
    required = {
        k for k, v in params.items() if k not in omitted and v.default is inspect.Parameter.empty
    }
    if action == "RESTORE_RUN":
        allowed.remove("source_pin")
        allowed.add("backup_pin")
        required.remove("source_pin")
        required.add("backup_pin")
    if action == "DATASET_COPY":
        allowed.remove("content")
        allowed.add("source_content_pin")
        required.remove("content")
        required.add("source_content_pin")
    return allowed, required


def _refs(values, maximum=512):
    require(type(values) is list and len(values) <= maximum, "Bounded native source vector")
    for reference in values:
        depth.exact_pin(reference)
    require(len({encoded(r) for r in values}) == len(values), "Duplicate native source pin")


def _period_refs(values):
    _refs(values, 36)
    expected = {
        (role, f"2027-{month:02}")
        for role in ("denominator_snapshot", "monthly_reconciliation")
        for month in range(1, 13)
    } | {
        (role, f"2027-Q{quarter}")
        for role in ("periodic_review_population", "periodic_review_decisions", "review_followup")
        for quarter in range(1, 5)
    }
    require(
        len(values) == 36
        and {(r["system"].removeprefix("person-access-history."), r["record"]) for r in values}
        == expected,
        "Exact 24 monthly and 12 quarterly originals required",
    )


def _literal_refs(value):
    result = []
    stack = [(value, 0)]
    visited = 0
    while stack:
        current, nesting = stack.pop()
        visited += 1
        require(visited <= 4096 and nesting <= 64, "Bounded source argument structure")
        if type(current) is dict:
            if set(current) == depth.PIN:
                depth.exact_pin(current)
                result.append(current)
            else:
                stack.extend((item, nesting + 1) for item in current.values())
        elif type(current) is list:
            stack.extend((item, nesting + 1) for item in current)
    return result


def _validate_program(program, scopes, sources, finish_at):
    require(type(program) is list and 1 <= len(program) <= MAX_STEPS, "Finite source program")
    identifiers = set()
    prior_at = None
    runtime_ids = set()
    locations = {"company": None}
    prior_modes = {}
    for step in program:
        keys(step, "id mode action at arguments source_refs")
        _id(step["id"])
        require(
            step["id"] not in identifiers and step["mode"] in scopes, "Unique scoped source step"
        )
        require(_time(step["at"]) == step["at"] and step["at"] <= finish_at, "Literal step clock")
        require(prior_at is None or prior_at <= step["at"], "Source program clocks move backward")
        prior_at = step["at"]
        require(step["action"] in {*OPERATIONS, "APPEND_NATIVE"}, "Unsupported business operation")
        require(type(step["arguments"]) is dict, "Typed native operation arguments")
        pending = [step["arguments"]]
        while pending:
            value = pending.pop()
            if type(value) is dict:
                if "$result" in value:
                    keys(value, "$result")
                    keys(value["$result"], "step fields")
                    pointer = value["$result"]
                    require(
                        prior_modes.get(pointer["step"]) == step["mode"]
                        and type(pointer["fields"]) is list
                        and 1 <= len(pointer["fields"]) <= 4
                        and all(type(k) is str and k for k in pointer["fields"]),
                        "Result must be from an earlier same-branch source operation",
                    )
                elif "$edition_path" in value:
                    keys(value, "$edition_path")
                    name = value["$edition_path"]
                    require(
                        type(name) is str
                        and name in locations
                        and locations[name] in (None, step["mode"]),
                        "Source location must already belong to this edition branch",
                    )
                else:
                    for name, item in value.items():
                        if name in PATH_ARGUMENTS:
                            require(
                                type(item) is dict and set(item) == {"$edition_path"},
                                "Source paths use explicit edition-owned locations only",
                            )
                        pending.append(item)
            elif type(value) is list:
                pending.extend(value)
        _refs(step["source_refs"])
        require(
            all((r["company"], r["branch"]) == scopes[step["mode"]] for r in step["source_refs"]),
            "Foreign source step reference",
        )
        require(
            set(map(encoded, step["source_refs"])) <= sources[step["mode"]],
            "Source step names an unadmitted original",
        )
        require(
            set(map(encoded, _literal_refs(step["arguments"])))
            <= set(map(encoded, step["source_refs"])),
            "Literal operation source absent from step vector",
        )
        if step["action"] in {"POLICY_INITIALIZE", "BACKUP_INITIALIZE"}:
            runtime_ids.add(step["id"])
            locations["runtime:" + step["id"]] = step["mode"]
        if step["action"] == "PERIOD_DECLARE":
            locations["ledger:" + step["id"]] = step["mode"]
        if step["action"] == "APPEND_NATIVE":
            keys(step["arguments"], "system record owner_id body basis_refs")
            require(
                step["arguments"]["system"] in {"business_inventory", "service_criterion"},
                "Only independent calendar or local criterion may be authored",
            )
            _refs(step["arguments"]["basis_refs"])
            require(bool(step["arguments"]["basis_refs"]), "Native authority/scope basis required")
            require(
                set(map(encoded, step["arguments"]["basis_refs"])) <= sources[step["mode"]],
                "Unadmitted independent native authority basis",
            )
        else:
            allowed, required = _arguments(step["action"])
            require(
                required <= set(step["arguments"]) <= allowed,
                "Exact fixed native API argument fields",
            )
        identifiers.add(step["id"])
        prior_modes[step["id"]] = step["mode"]
    return runtime_ids


def preview(plan_pin, admission_pin, *, repository):
    """Validate the finite externally selected program; open no source/audit SQL."""
    plan, plan_stamp = read_pin(plan_pin)
    admission, admission_stamp = read_pin(admission_pin)
    keys(
        plan,
        "schema edition_id qualification capsule concrete_plan modes program finish_at "
        "fresh_audit_not_before source_unknowns",
    )
    require(
        plan["schema"] == PLAN and plan["qualification"] == QUALIFICATION, "Source edition schema"
    )
    _id(plan["edition_id"])
    concrete, concrete_stamp = read_pin(plan["concrete_plan"])
    require(
        plan["concrete_plan"]["sha256"] == CONCRETE_SHA
        and concrete["schema"] == "SH_NATIVE_OPERATING_DEPTH_CONCRETE_EDITION_PLAN_V1",
        "Selected source-edition plan differs",
    )
    keys(plan["capsule"], "path sha256")
    checksum(plan["capsule"]["sha256"])
    require(Path(plan["capsule"]["path"]).name == "MANIFEST.json", "Exact seed capsule manifest")
    _, capsule_stamp = read_pin(plan["capsule"])
    keys(
        admission,
        "schema status plan capsule concrete_plan code_pins source_review "
        "original_edition_preserved current_pipeline_complete actual_execution",
    )
    require(admission["schema"] == ADMISSION, "Root source admission schema")
    require(
        admission["status"]
        in {"APPROVED_OWN_NEW_SOURCE_MECHANISM_ONLY", "ROOT_APPROVED_SEPARATE_SOURCE_EDITION"},
        "Source admission pending",
    )
    require(
        admission["plan"] == plan_pin
        and admission["capsule"] == plan["capsule"]
        and admission["concrete_plan"] == plan["concrete_plan"],
        "Source admission pin binding",
    )
    require(
        admission["original_edition_preserved"] is True
        and type(admission["current_pipeline_complete"]) is bool
        and type(admission["actual_execution"]) is bool,
        "Explicit Root source boundary",
    )
    if admission["status"] == "ROOT_APPROVED_SEPARATE_SOURCE_EDITION":
        require(
            admission["current_pipeline_complete"] is True
            and admission["actual_execution"] is True,
            "Immutable predecessor pipeline incomplete",
        )
    else:
        require(
            admission["actual_execution"] is False, "OWN fixtures are not actual source authority"
        )
    require(admission["code_pins"] == _code(), "Source driver/helper origins differ")
    source_review, review_stamp = read_pin(admission["source_review"])
    require(
        source_review.get("source_only") is True
        and source_review.get("capsule") == plan["capsule"]
        and source_review.get("native_fields_preserved") is True,
        "Independent original-source admission required",
    )
    require(
        _time(plan["finish_at"]) == plan["finish_at"]
        and _time(plan["fresh_audit_not_before"]) == plan["fresh_audit_not_before"]
        and plan["finish_at"] < plan["fresh_audit_not_before"],
        "Fresh audit follows source operations",
    )
    require(type(plan["modes"]) is list and 1 <= len(plan["modes"]) <= 2, "Bounded source branches")
    scopes = {}
    sources = {}
    for mode in plan["modes"]:
        keys(
            mode,
            "mode company branch retained_period_refs original_input_refs historical_unperformed",
        )
        require(
            mode["mode"] in {"CLEAN", "MESSY"} and mode["mode"] not in scopes, "Exact branch label"
        )
        scopes[mode["mode"]] = (_id(mode["company"]), _id(mode["branch"]))
        _period_refs(mode["retained_period_refs"])
        _refs(mode["original_input_refs"])
        sources[mode["mode"]] = set(map(encoded, mode["original_input_refs"]))
        require(
            set(map(encoded, mode["retained_period_refs"]))
            <= set(map(encoded, mode["original_input_refs"])),
            "All36 original period records retained in source vector",
        )
        require(
            all(
                (r["company"], r["branch"]) == scopes[mode["mode"]]
                for r in mode["original_input_refs"]
            ),
            "Foreign branch baseline pin",
        )
        require(
            type(mode["historical_unperformed"]) is list
            and len(mode["historical_unperformed"]) <= 64,
            "Bounded explicit historical gaps",
        )
        for gap in mode["historical_unperformed"]:
            keys(gap, "id reason source_refs")
            _id(gap["id"])
            require(
                type(gap["reason"]) is str and 10 <= len(gap["reason"]) <= 2000,
                "Historical limitations must be explicit",
            )
            _refs(gap["source_refs"])
            require(
                set(map(encoded, gap["source_refs"])) <= sources[mode["mode"]],
                "Historical limitation requires admitted original references",
            )
    if admission["actual_execution"]:
        require(set(scopes) == {"CLEAN", "MESSY"}, "Actual edition requires both branches")
    require(
        type(plan["source_unknowns"]) is list
        and 1 <= len(plan["source_unknowns"]) <= 32
        and all(type(v) is str and 10 <= len(v) <= 2000 for v in plan["source_unknowns"]),
        "Unmodeled estate/human source limits required",
    )
    require(len(set(scopes.values())) == len(scopes), "Branches cannot alias one source context")
    runtime_ids = _validate_program(plan["program"], scopes, sources, plan["finish_at"])
    org = snapshot(repository, as_of="2027-01-01")
    require(len(org["canonical_people"]) == 52, "Locked52-person canon differs")
    return dict(
        plan=plan,
        admission=admission,
        scopes=scopes,
        runtime_ids=runtime_ids,
        pins=[
            (plan_pin, plan_stamp),
            (admission_pin, admission_stamp),
            (plan["concrete_plan"], concrete_stamp),
            (admission["source_review"], review_stamp),
            (plan["capsule"], capsule_stamp),
        ],
        code_pins=_code(),
        preview_sha256=sha(encoded(plan)),
        qualification=QUALIFICATION,
        audit_state_or_Key_created=False,
        canonical_source_pins={
            str(Path(repository) / name): value for name, value in org["source_sha256"].items()
        },
    )


def _close(prepared):
    for reference, opening in prepared["pins"]:
        _, current = read_pin(reference)
        require(current == opening, "Pinned source admission changed")
    require(_code() == prepared["code_pins"], "Source program origins changed")
    require(
        all(
            sha(Path(path).read_bytes()) == value
            for path, value in prepared["canonical_source_pins"].items()
        ),
        "Named canonical source definitions changed",
    )


def _seed_projection(prepared):
    """Fresh readonly seed comparison anchors resume to externally pinned originals."""
    capsule = Path(prepared["plan"]["capsule"]["path"]).parent
    path = capsule / "company/company.sqlite3"
    activation._sealed_sidecars(path)
    activation._manifest(
        capsule / "MANIFEST.json", prepared["plan"]["capsule"]["sha256"], path.parent
    )
    opening = identity(path)
    rows = []
    with closing(activation.sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = activation.sqlite3.Row
        db.execute("BEGIN")
        for row in db.execute(
            "SELECT * FROM versions ORDER BY company,branch,system,record,version"
        ):
            row = dict(row)
            raw = row.pop("content")
            require(type(raw) is bytes and sha(raw) == row["sha256"], "Original seed bytes differ")
            rows.append(
                {
                    "key": [row[k] for k in ("company", "branch", "system", "record", "version")],
                    "header_and_raw_sha256": sha(encoded({**row, "raw_sha256": sha(raw)})),
                }
            )
    activation._sealed_sidecars(path)
    require(identity(path) == opening, "Pinned seed changed during exact readonly comparison")
    return rows


def _root_descriptors(root):
    """Declare genuine independent physical source roots, never a merged source."""
    paths = [("ACTIVATED_SEED_AND_DEPTH_OPERATIONS", root / "company")]
    paths += [("PROSPECTIVE_PERIOD_LEDGER", p) for p in sorted((root / "ledgers").iterdir())]
    paths += [("NATIVE_BUSINESS_RUNTIME", p) for p in sorted((root / "runtimes").iterdir())]
    result = []
    for kind, path in paths:
        identity(path, directory=True)
        database = path / "company.sqlite3"
        activation._sealed_sidecars(database)
        opening = identity(database)
        raw_sha = sha(database.read_bytes())
        with closing(activation.sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as db:
            db.execute("BEGIN")
            systems = [
                list(r)
                for r in db.execute(
                    "SELECT company,branch,system,owner FROM systems ORDER BY company,branch,system"
                )
            ]
            count = db.execute("SELECT COUNT(*) FROM versions").fetchone()[0]
            authority_counts = {
                t: db.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
                for t in ("grants", "collections", "access_events")
            }
        require(all(v == 0 for v in authority_counts.values()), "Source root already audited")
        activation._sealed_sidecars(database)
        require(identity(database) == opening, "Source root changed during closing declaration")
        result.append(
            {
                "kind": kind,
                "path": str(path),
                "database": {
                    "path": str(database),
                    "sha256": raw_sha,
                    "bytes": opening[2],
                    "identity": opening,
                },
                "registered_systems_columns": list(activation.SYSTEM_FIELDS),
                "registered_systems": systems,
                "native_versions": count,
                "audit_authority_counts": authority_counts,
                "collection_api": "CompanyStore.discover/read_version/collect",
                "logical_aliases_or_retimestamping": False,
            }
        )
    return result


def _native_bytes(store, reference, at, scope):
    depth.exact_pin(reference)
    require((reference["company"], reference["branch"]) == scope, "Foreign exact source original")
    with store._db() as db:
        row = db.execute(
            "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
            "AND record=? AND version=?",
            tuple(reference[k] for k in ("company", "branch", "system", "record", "version")),
        ).fetchone()
        require(
            row is not None
            and row["event_at"] is not None
            and row["event_at"] <= at
            and row["available_at"] <= at,
            "Exact dated source original not yet available",
        )
        raw = row["content"]
        require(
            type(raw) is bytes
            and 0 < len(raw) <= 25 * 1024 * 1024
            and sha(raw) == row["sha256"] == reference["sha256"],
            "Original source bytes differ",
        )
        return raw


def _projection(store, only=None):
    """Fresh source bytes/header digests, never an outcome or source-content cache."""
    rows = []
    with store._db() as db:
        db.execute("BEGIN")
        require(
            all(
                db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] == 0
                for table in ("grants", "collections", "access_events")
            ),
            "Source edition must precede audit access/collection",
        )
        for row in db.execute(
            "SELECT * FROM versions ORDER BY company,branch,system,record,version"
        ):
            row = dict(row)
            raw = row.pop("content")
            require(
                type(raw) is bytes and sha(raw) == row["sha256"], "Stored native original changed"
            )
            key = tuple(row[k] for k in ("company", "branch", "system", "record", "version"))
            if only is not None and key not in only:
                continue
            rows.append(
                dict(
                    key=list(key),
                    header_and_raw_sha256=sha(encoded({**row, "raw_sha256": sha(raw)})),
                )
            )
    require(only is None or len(rows) == len(only), "Original baseline source removed")
    return rows


def _resolve(value, results, root):
    if type(value) is dict:
        if set(value) == {"$result"}:
            pointer = value["$result"]
            keys(pointer, "step fields")
            require(
                pointer["step"] in results
                and type(pointer["fields"]) is list
                and 1 <= len(pointer["fields"]) <= 4
                and all(type(k) is str for k in pointer["fields"]),
                "Earlier exact result pointer required",
            )
            result = results[pointer["step"]]
            for key in pointer["fields"]:
                require(type(result) is dict and key in result, "Unknown native result field")
                result = result[key]
            return result
        if set(value) == {"$edition_path"}:
            name = value["$edition_path"]
            require(
                type(name) is str
                and (name == "company" or name.startswith(("runtime:", "ledger:"))),
                "Existing edition-owned source location required",
            )
            if name != "company":
                _id(name.split(":", 1)[1])
            if name == "company":
                return str(root / "company")
            kind, identifier = name.split(":", 1)
            return str(root / ("runtimes" if kind == "runtime" else "ledgers") / identifier)
        return {k: _resolve(v, results, root) for k, v in value.items()}
    if type(value) is list:
        return [_resolve(v, results, root) for v in value]
    require(type(value) in (str, int, float, bool, type(None)), "Typed bounded source argument")
    return value


def _summary(value):
    if type(value) is bytes:
        return {"full_bytes_sha256": sha(value), "bytes": len(value)}
    if type(value) is dict:
        return {k: _summary(v) for k, v in value.items()}
    if type(value) in (list, tuple):
        return [_summary(v) for v in value]
    return value


def _append_native(store, step, arguments, prepared):
    mode = next(m for m in prepared["plan"]["modes"] if m["mode"] == step["mode"])
    scope = (mode["company"], mode["branch"])
    system, record, owner = (arguments[k] for k in ("system", "record", "owner_id"))
    _id(owner)
    require(
        record.startswith(prepared["plan"]["edition_id"] + "."),
        "New edition-specific source identity",
    )
    org = snapshot(prepared["repository"], as_of=step["at"][:10])
    require(
        owner in {p["person_id"] for p in org["proposed_people"]},
        "Existing named source persona required",
    )
    for reference in arguments["basis_refs"]:
        _native_bytes(store, reference, step["at"], scope)
    body = arguments["body"]
    require(type(body) is dict, "Typed independent source body")
    if system == "business_inventory":
        keys(body, "systems operating_depth_calendar whole_estate_claim")
        require(
            body["operating_depth_calendar"]["declared_at"] == step["at"],
            "Independent calendar clock",
        )
        require(
            type(body["whole_estate_claim"]) is str
            and "NOT_ESTABLISHED" in body["whole_estate_claim"],
            "Explicit unmodeled estate limitation required",
        )
    else:
        keys(
            body,
            "schema service_id dataset_id author_id reviewer_id approved_at "
            "max_age_seconds max_restore_seconds min_record_count qualification",
        )
        require(
            body["schema"] == "SH_LOCAL_SERVICE_RETURN_CRITERION_V1"
            and body["qualification"] == "LOCAL_SIMULATED_SERVICE_CRITERION_NOT_ENTERPRISE_BIA"
            and body["author_id"] == owner
            and body["approved_at"] == step["at"]
            and body["reviewer_id"] != owner,
            "Explicit prospective local service criterion",
        )
        require(
            body["reviewer_id"] in {p["person_id"] for p in org["proposed_people"]},
            "Existing distinct source reviewer persona required",
        )
        _id(body["service_id"])
        _id(body["dataset_id"])
        require(
            all(
                type(body[k]) is int and 1 <= body[k] <= 31536000
                for k in ("max_age_seconds", "max_restore_seconds", "min_record_count")
            ),
            "Explicit typed local criterion bounds required",
        )
    store.register_system(*scope, system, owner)
    row = store.append_version(
        *scope,
        system,
        record,
        expected_version=0,
        command_id="edition-" + sha(encoded([prepared["plan"]["edition_id"], step["id"]]))[:48],
        event_at=step["at"],
        available_at=step["at"],
        content=encoded(body),
        provenance={
            "source_reference": prepared["plan"]["edition_id"],
            "edition_plan_sha256": prepared["preview_sha256"],
            "original_basis_refs": arguments["basis_refs"],
            "simulated_new_edition_clock": step["at"],
            "actual_registration_not_original_import": True,
            "name": record + ".json",
            "qualification": QUALIFICATION,
            "content_type": "application/json",
        },
    )
    return {"native_pin": depth.pin(row), "actual_imported_at": row["imported_at"]}


def _invoke(step, prepared, store, root, results):
    scope = prepared["scopes"][step["mode"]]
    for reference in step["source_refs"]:
        _native_bytes(store, reference, step["at"], scope)
    arguments = _resolve(step["arguments"], results, root)
    if step["action"] == "APPEND_NATIVE":
        return _append_native(store, step, arguments, prepared)
    function, category = OPERATIONS[step["action"]]
    require(
        "repository" not in arguments and "store" not in arguments,
        "Trusted source arguments cannot be overridden",
    )
    signature = inspect.signature(function)
    if "repository" in signature.parameters:
        arguments["repository"] = prepared["repository"]
    for clock in ("event_at", "recorded_at", "attempted_at", "as_of"):
        if clock in arguments:
            require(
                _time(arguments[clock]) == step["at"], "Operation clock differs from source program"
            )
    if step["action"] == "DATASET_COPY":
        require("content" not in arguments, "Dataset bytes must come from an exact original")
        reference = arguments.pop("source_content_pin")
        require(reference in step["source_refs"], "Dataset copy input not admitted")
        arguments["content"] = _native_bytes(store, reference, step["at"], scope)
        require(
            arguments["expected_sha256"] == reference["sha256"], "Dataset byte copy pin differs"
        )
    for name in PATH_ARGUMENTS & set(arguments):
        path = Path(arguments[name])
        require(
            path.is_absolute()
            and path.is_relative_to(root)
            and not any(p.is_symlink() for p in (path, *path.parents)),
            "Foreign source runtime path",
        )
    if step["action"] == "POLICY_INITIALIZE":
        require(
            arguments["plan"]["declared_at"] == step["at"],
            "Prospective policy initialization clock",
        )
        require(
            (arguments["plan"]["company"], arguments["plan"]["branch"]) == scope,
            "Foreign policy scope",
        )
    if step["action"] == "PERIOD_DECLARE":
        require(
            arguments["plan"]["declared_at"] == step["at"]
            and (arguments["plan"]["company_id"], arguments["plan"]["branch_id"]) == scope,
            "Exact prospective period scope and clock",
        )
        require(
            arguments["plan"]["period_id"].startswith(prepared["plan"]["edition_id"] + "."),
            "New edition-specific due period required",
        )
    if step["action"] == "REGISTER_CALENDAR":
        require(
            arguments["runtime_id"].startswith(prepared["plan"]["edition_id"] + "."),
            "New edition-specific calendar required",
        )
    if category == "company":
        signature.bind(store, **arguments)
        result = function(store, **arguments)
    elif category == "period":
        # The normal prospective due ledger API requires an empty source store.
        # It is separate from the activated originals and runtime directories.
        path = root / "ledgers" / step["id"]
        if not path.exists():
            path.mkdir(mode=0o700)
        identity(path, directory=True)
        ledger = CompanyStore(path)
        with ledger._db() as db:
            count = db.execute("SELECT COUNT(*) FROM versions").fetchone()[0]
            if count:
                require(count == 1, "Changed prospective period ledger on resume")
                row = dict(db.execute("SELECT * FROM versions").fetchone())
                body = decode(row["content"])
                require(
                    row["system"] == period.SYSTEM
                    and row["record"] == arguments["plan"]["period_id"]
                    and row["version"] == 1
                    and row["event_at"] == row["available_at"] == step["at"]
                    and sha(row["content"]) == row["sha256"]
                    and encoded(body["plan"]) == encoded(period._plan(arguments["plan"])),
                    "Changed prospective period original on resume",
                )
                result = row
            else:
                result = function(ledger, **arguments)
    else:
        first = "destination" if category == "initialize" else next(iter(signature.parameters))
        if category == "initialize":
            require("destination" not in arguments, "Driver owns new runtime destination")
            arguments[first] = root / "runtimes" / step["id"]
            path = Path(arguments[first])
            if path.exists():
                # An initializer can commit before a checkpoint. Validate its exact
                # already-created plan/input binding, never replace or reinitialize it.
                config_path = path / "RUNTIME.json"
                cfg = decode(config_path.read_bytes())
                require(
                    encoded(cfg["plan"]) == encoded(arguments["plan"])
                    if "plan" in arguments
                    else cfg["declaration_ref"] == arguments["declaration_ref"],
                    "Changed initializer resume input",
                )
                if step["action"] == "POLICY_INITIALIZE":
                    declared, originals = policy._native_documents(
                        arguments["plan"], arguments["documents"]
                    )
                    require(
                        encoded(cfg["documents"]) == encoded(declared),
                        "Changed native policy initialization",
                    )
                    policy.inspect(
                        path,
                        expected_runtime_sha256=sha(config_path.read_bytes()),
                        as_of=prepared["plan"]["finish_at"],
                    )
                else:
                    require(
                        cfg["bindings"] == {b["occurrence_id"]: b for b in arguments["bindings"]}
                        and cfg["datasets"] == {d["id"]: d["format"] for d in arguments["datasets"]}
                        and cfg["service_id"] == arguments.get("service_id", "SVC-compute")
                        and cfg["declaration_location_sha256"]
                        == sha(str(Path(arguments["declaration_root"])).encode()),
                        "Changed backup initializer bindings on resume",
                    )
                    if "local_data_loss_criterion" in arguments:
                        from .company_backup_criterion import resolve

                        require(
                            cfg.get("local_data_loss_criterion")
                            == resolve(
                                arguments["local_data_loss_criterion"],
                                scope={
                                    "service_id": cfg["service_id"],
                                    "dataset_ids": sorted(cfg["datasets"]),
                                },
                                plan=cfg["plan"],
                                author=cfg["operator_id"],
                                reviewer=cfg["operating_reviewer_id"],
                                as_of=cfg["plan"]["declared_at"],
                            ),
                            "Changed backup criterion on resume",
                        )
                    else:
                        require(
                            "local_data_loss_criterion" not in cfg, "Unexpected backup criterion"
                        )
                    backup.reconcile(
                        path,
                        expected_runtime_sha256=sha(config_path.read_bytes()),
                        as_of=prepared["plan"]["finish_at"],
                    )
                    return {
                        "runtime_sha256": sha(config_path.read_bytes()),
                        "declaration_ref": cfg["declaration_ref"],
                        "source_versions": 1,
                        "operation_execution": "NOT_STARTED",
                        "audit_created": False,
                    }
                return {
                    "runtime_sha256": sha(config_path.read_bytes()),
                    "revision": 0,
                    "qualification": cfg["qualification"],
                    "selected_document_pin": policy._doc(cfg, cfg["documents"][0]["id"]),
                }
        signature.bind(**arguments)
        result = function(**arguments)
        if step["action"] == "POLICY_INITIALIZE":
            result = result | {
                "selected_document_pin": policy.inspect(
                    arguments["destination"],
                    expected_runtime_sha256=result["runtime_sha256"],
                    as_of=step["at"],
                )["report"]["selected_document_pin"]
            }
    if type(result) is dict and depth.PIN <= set(result):
        return {"native_pin": depth.pin(result), "actual_imported_at": result["imported_at"]}
    return _summary(result)


def execute(plan_pin, admission_pin, *, repository, destination):
    """Run/resume only a Root-pinned NEW source program; creates no audit or Key."""
    prepared = preview(plan_pin, admission_pin, repository=repository)
    prepared["repository"] = Path(repository)
    root = Path(destination)
    require(
        root.is_absolute() and ".." not in root.parts, "New absolute source-edition destination"
    )
    identity(root.parent, directory=True)
    if not root.exists():
        root.mkdir(mode=0o700)
        (root / "runtimes").mkdir(mode=0o700)
        (root / "ledgers").mkdir(mode=0o700)
        (root / "receipts").mkdir(mode=0o700)
        write_new(
            root / "EDITION_INPUT.json",
            {
                "plan": plan_pin,
                "admission": admission_pin,
                "preview_sha256": prepared["preview_sha256"],
                "real_started_at": _now(),
                "qualification": QUALIFICATION,
            },
        )
    identity(root, directory=True)
    initial = decode((root / "EDITION_INPUT.json").read_bytes())
    require(
        initial["plan"] == plan_pin
        and initial["admission"] == admission_pin
        and initial["preview_sha256"] == prepared["preview_sha256"],
        "Foreign edition resume",
    )
    lock_path = root / ".source-edition.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        require(
            identity(lock_path)
            == [
                os.fstat(fd).st_dev,
                os.fstat(fd).st_ino,
                os.fstat(fd).st_size,
                os.fstat(fd).st_mtime_ns,
                os.fstat(fd).st_ctime_ns,
                os.fstat(fd).st_mode,
                os.fstat(fd).st_nlink,
            ],
            "Source edition lock identity",
        )
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _close(prepared)
        if not (root / "company").exists():
            activation.activate(
                Path(prepared["plan"]["capsule"]["path"]).parent,
                root / "company",
                expected_manifest_sha256=prepared["plan"]["capsule"]["sha256"],
            )
        store = CompanyStore(root / "company")
        seed_path = root / "ORIGINAL_SEED_PROJECTION.json"
        if not seed_path.exists():
            require(
                not list((root / "receipts").iterdir()), "Uncheckpointed existing edition source"
            )
            write_new(
                seed_path,
                {
                    "originals": _projection(store),
                    "activation": {
                        "path": str(root / "company/ACTIVATION.json"),
                        "sha256": sha((root / "company/ACTIVATION.json").read_bytes()),
                    },
                },
            )
        baseline = decode(seed_path.read_bytes())
        require(
            baseline["originals"] == _seed_projection(prepared),
            "Resume baseline differs from independently pinned immutable seed",
        )
        activation_path = root / "company/ACTIVATION.json"
        identity(activation_path)
        activated = decode(activation_path.read_bytes())
        require(
            activated["capsule_manifest_sha256"] == prepared["plan"]["capsule"]["sha256"]
            and activated["capsule_root"] == str(Path(prepared["plan"]["capsule"]["path"]).parent)
            and activated["audit_created"] is False
            and activated["native_fields_preserved"] == list(activation.VERSION_FIELDS)
            and baseline["activation"]["sha256"] == sha(activation_path.read_bytes()),
            "Exact normal seed activation provenance required",
        )
        original_keys = {tuple(row["key"]) for row in baseline["originals"]}
        require(
            _projection(store, original_keys) == baseline["originals"],
            "Original native seed fields differ",
        )
        results = {}
        for index, step in enumerate(prepared["plan"]["program"]):
            _close(prepared)
            before = _projection(store, original_keys)
            require(
                before == baseline["originals"], "Original baseline changed before source operation"
            )
            receipt_path = root / "receipts" / f"{index:04d}-{step['id']}.json"
            if receipt_path.exists():
                old = decode(receipt_path.read_bytes())
                require(
                    old["step_sha256"] == sha(encoded(step)), "Changed source operation checkpoint"
                )
            try:
                result = _invoke(step, prepared, store, root, results)
                _close(prepared)
                require(
                    _projection(store, original_keys) == baseline["originals"],
                    "Operation altered original seed",
                )
                receipt = {
                    "step_id": step["id"],
                    "step_sha256": sha(encoded(step)),
                    "simulated_at": step["at"],
                    "result": result,
                    "qualification": QUALIFICATION,
                    "audit_task_credit": False,
                    "original_native_fields_unchanged": True,
                }
                if receipt_path.exists():
                    require(
                        encoded(old) == encoded(receipt), "Resumed native operation result differs"
                    )
                else:
                    write_new(receipt_path, receipt)
                results[step["id"]] = result
            except (CompanyStoreError, ValueError, TypeError, OSError) as error:
                attempts = sorted(root.glob("FAILURE-*.json"))
                write_new(
                    root / f"FAILURE-{len(attempts):04d}.json",
                    {
                        "failed_step": step["id"],
                        "error_type": type(error).__name__,
                        "message": str(error)[:500],
                        "real_recorded_at": _now(),
                        "preserve_prior_native_operations": True,
                        "no_audit_or_Key_created": True,
                    },
                )
                raise
        censuses = []
        for mode in prepared["plan"]["modes"]:
            view = depth.person_period_joins(
                store, references=mode["retained_period_refs"], as_of=prepared["plan"]["finish_at"]
            )
            censuses.append(
                {
                    "mode": mode["mode"],
                    "retained_original_count": 36,
                    "actual_source_census": view,
                    "historical_unperformed": mode["historical_unperformed"],
                }
            )
        calendars = []
        for step in prepared["plan"]["program"]:
            if step["action"] == "REGISTER_CALENDAR":
                reference = results[step["id"]]["native_pin"]
                calendars.append(
                    {
                        "registered_pin": reference,
                        "actual_declared_due_census": depth.inspect(
                            store, declaration_pin=reference, as_of=prepared["plan"]["finish_at"]
                        ),
                    }
                )
        _close(prepared)
        require(_seed_projection(prepared) == baseline["originals"], "Closing frozen seed differs")
        require(
            _projection(store, original_keys) == baseline["originals"],
            "Closing original seed differs",
        )
        completion = {
            "schema": "SH_FICTIONAL_OPERATING_SOURCE_EDITION_COMPLETION_V1",
            "edition_id": prepared["plan"]["edition_id"],
            "plan": plan_pin,
            "admission": admission_pin,
            "source_program_steps": len(results),
            "source_period_censuses": censuses,
            "registered_calendar_censuses": calendars,
            "fresh_audit_not_before": prepared["plan"]["fresh_audit_not_before"],
            "source_unknowns": prepared["plan"]["source_unknowns"],
            "qualification": QUALIFICATION,
            "audit_or_Key_created": False,
            "enterprise_or_human_acceptance": "NOT_ASSERTED",
            "all_original_native_fields_unchanged": True,
            "source_roots": _root_descriptors(root),
            "source_federation_or_new_audit_admission": "SEPARATELY_REQUIRED",
        }
        path = root / "SOURCE_EDITION_COMPLETION.json"
        if path.exists():
            require(
                encoded(decode(path.read_bytes())) == encoded(completion),
                "Closing edition receipt differs",
            )
            return {"path": str(path), "sha256": sha(path.read_bytes())}
        return write_new(path, completion)
    finally:
        os.close(fd)
