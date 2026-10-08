"""Bounded local document distribution; no human acknowledgment or policy acceptance."""

import os
import tempfile
from copy import deepcopy
from pathlib import Path

from .company_backup_runtime import checked_bytes, database, exact_pin, native, private, require
from .company_disposal_runtime import _preflight
from .company_repository_documents import _source
from .company_store import CompanyStore, CompanyStoreError, _id, _json, _now, _time
from .inference import _json as decode
from .operating_source_bridge import encoded, sha
from .organization import snapshot
from .private_publication import publish

QUALIFICATION = "LOCAL_MAILBOX_DELIVERY_AND_SIMULATED_ASSERTION_NOT_HUMAN_ACKNOWLEDGMENT"
CONTROLS = ["SH-POL-001"]
SYSTEMS = ("policy_definition", "policy_document", "policy_operation")
FIELDS = ("company", "branch", "system", "record", "version", "sha256")
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
        "company_policy_delivery_runtime.py",
        "company_backup_runtime.py",
        "company_disposal_runtime.py",
        "company_operating_period.py",
        "company_repository_documents.py",
        "company_store.py",
        "inference.py",
        "operating_source_bridge.py",
        "organization.py",
        "private_publication.py",
        "source_library_audit.py",
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


def _plan(plan):
    _keys(
        plan,
        "runtime_id company branch owner_id cycle_id declared_at due_at recipients local_basis",
    )
    for key in ("runtime_id", "company", "branch", "owner_id", "cycle_id"):
        _id(plan[key])
    start, due = _stamp(plan["declared_at"]), _stamp(plan["due_at"])
    require(start < due, "Independent future local due time required")
    ids = plan["recipients"]
    require(
        isinstance(ids, list) and 1 <= len(ids) <= 32,
        "Bounded explicit recipient inventory required",
    )
    for ident in ids:
        _id(ident)
    require(len(set(ids)) == len(ids), "Distinct recipient IDs required")
    require(
        isinstance(plan["local_basis"], str) and 1 <= len(plan["local_basis"].strip()) <= 2000,
        "Explicit local distribution basis required",
    )
    return plan | {"declared_at": start, "due_at": due}


def _documents(repository, documents):
    require(
        isinstance(documents, list) and 1 <= len(documents) <= 4,
        "One to four explicitly admitted documents required",
    )
    result, originals = [], []
    for d in documents:
        _keys(d, "id path sha256 source_metadata_lines")
        _id(d["id"])
        require(
            isinstance(d["path"], str) and len(d["path"]) <= 300,
            "Bounded canonical document path required",
        )
        # Source admission checks committed canonical bytes, never an arbitrary generated pack.
        target = repository / d["path"]
        require(
            target.is_file() and target.stat().st_size <= LIMIT,
            "Bounded documentary source required",
        )
        raw, blob = _source(repository, d["path"])
        require(
            len(raw) <= LIMIT and sha(raw) == d["sha256"], "Exact committed source SHA required"
        )
        lines = d["source_metadata_lines"]
        require(
            isinstance(lines, list) and 1 <= len(lines) <= 8,
            "Explicit literal source metadata required",
        )
        actual = raw.decode("utf-8").splitlines()
        for line in lines:
            require(
                isinstance(line, str) and 1 <= len(line) <= 400 and line in actual,
                "Metadata must be an exact retained source line",
            )
        result.append(
            d
            | {
                "git_blob": blob,
                "byte_count": len(raw),
                "authority": "LITERAL_SOURCE_METADATA_NOT_NEW_APPROVAL",
            }
        )
        originals.append(raw)
    require(
        len({r["id"] for r in result}) == len(result), "Distinct admitted document IDs required"
    )
    return result, originals


def _provenance(cfg):
    return {
        "control_ids": CONTROLS,
        "runtime_sha256": sha(encoded(cfg)),
        "cycle_id": cfg["plan"]["cycle_id"],
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
    provenance.update(
        source_reference=cfg["plan"]["runtime_id"],
        runtime_id=cfg["plan"]["runtime_id"],
        name=record + ".json",
        content_type="application/json",
    )
    native_document = (
        next((d for d in cfg["documents"] if d["id"] == record and "source_pin" in d), None)
        if system == "policy_document"
        else None
    )
    if native_document:
        provenance.update(
            native_document_source=native_document["source_pin"],
            original_native_header=native_document["source_header"],
            copied_native_bytes_not_new_policy_approval=True,
        )
        original_provenance = decode(native_document["source_header"]["provenance"])
        provenance.update(
            name=original_provenance["name"], content_type=original_provenance["content_type"]
        )
    elif system == "policy_document":
        document = next(d for d in cfg["documents"] if d["id"] == record)
        path = Path(document["path"])
        require(path.suffix in {".md", ".txt", ".json"}, "Known committed document format required")
        provenance.update(
            name=record + (".json" if path.suffix == ".json" else ".txt"),
            content_type="application/json" if path.suffix == ".json" else "text/plain",
            committed_document_path=document["path"],
            original_committed_name=path.name,
            name_scope="NEW_NATIVE_TRANSPORT_FILENAME_ORIGINAL_COMMITTED_PATH_RETAINED",
        )
    from .source_library_audit import ProcedureError, typed_content

    try:
        typed_content({"provenance": provenance, "content": raw, "sha256": sha(raw)})
    except ProcedureError as error:
        raise CompanyStoreError("Exact typed policy metadata/body required") from error
    origin = (
        "REPOSITORY_SYNTHETIC_DOCUMENT"
        if system == "policy_document" and native_document is None
        else "AUTHORED_TRAINING_SOURCE"
    )
    return ref | {
        "event_at": at,
        "available_at": at,
        "imported_at": imported,
        "origin": origin,
        "provenance": _json(provenance),
        "command_id": "POL-" + sha(encoded([key, version])),
        "input_digest": sha(
            _json([key, version - 1, at, at, origin, provenance, ref["sha256"]]).encode()
        ),
    }


def _bounds(db):
    _preflight(
        db, "systems", dict.fromkeys(("company", "branch", "system", "owner"), 128), len(SYSTEMS)
    )
    _preflight(db, "versions", NATIVE_LIMITS, 5 + MAX_COMMANDS)
    _preflight(
        db,
        "policy_commands",
        {"revision": 16, "command_id": 128, "digest": 64, "receipt": LIMIT},
        MAX_COMMANDS,
    )
    _preflight(db, "policy_state", {"id": 16, "revision": 16, "body": LIMIT}, 1)


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
    _preflight(db, "versions", NATIVE_LIMITS, 5 + MAX_COMMANDS)
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
        cfg.get("format") == "LOCAL_POLICY_DELIVERY_RUNTIME_V1" and cfg["code_pins"] == _code(),
        "Maintained runtime definition/code changed",
    )
    if "document_admission" in cfg:
        require(
            cfg["document_admission"] == "EXPLICIT_NATIVE_POLICY_DOCUMENT_BYTES_V1",
            "Unknown native document admission",
        )
        declarations = [
            {k: d[k] for k in ("id", "source_root", "source_pin")} for d in cfg["documents"]
        ]
        current, _ = _native_documents(cfg["plan"], declarations)
        require(
            encoded(current) == encoded(cfg["documents"]),
            "Original native document bytes/header changed",
        )
    return cfg


def _initial(cfg):
    return {
        "event_at": cfg["plan"]["declared_at"],
        "imported_at": cfg["imported_at"],
        "selected_document_id": cfg["documents"][0]["id"],
        "withdrawn": False,
        "deliveries": {},
        "reads": {},
        "assertions": {},
    }


def _native_documents(plan, documents):
    """Exact native policy bytes, with original clock/provenance retained separately.

    This admits a policy_document role only. A recipient timestamp, metadata row,
    unrelated source role or a boolean assertion is never a document-byte basis.
    """
    require(
        isinstance(documents, list) and 1 <= len(documents) <= 4,
        "One to four exact native documents required",
    )
    result, originals = [], []
    for declaration in documents:
        _keys(declaration, "id source_root source_pin")
        _id(declaration["id"])
        exact_pin(declaration["source_pin"])
        ref = declaration["source_pin"]
        require(
            (ref["company"], ref["branch"]) == (plan["company"], plan["branch"])
            and ref["system"] in {"policy_document", "supplementalops.policy_document"},
            "Exact same-branch native policy-document role",
        )
        root = private(Path(declaration["source_root"]), True)
        with database(root) as db:
            row = native(db, ref, plan["declared_at"])
            require(
                row["event_at"] is not None and len(row["content"]) <= LIMIT,
                "Known dated bounded native document required",
            )
            raw = row["content"]
            from .source_library_audit import ProcedureError, typed_content

            try:
                typed_content({**row, "provenance": decode(row["provenance"])})
            except ProcedureError as error:
                raise CompanyStoreError(
                    "Exact typed native policy source metadata/body required"
                ) from error
            try:
                raw.decode("utf-8")
            except UnicodeError as error:
                raise CompanyStoreError("Native policy text must be UTF-8") from error
            header = {
                k: row[k]
                for k in (
                    *FIELDS,
                    "event_at",
                    "available_at",
                    "imported_at",
                    "origin",
                    "provenance",
                )
            }
            require(
                row["origin"]
                in {
                    "AUTHORED_TRAINING_SOURCE",
                    "MIGRATED_SYNTHETIC_HISTORY",
                    "REPOSITORY_SYNTHETIC_DOCUMENT",
                },
                "Explicit native synthetic document origin required",
            )
        result.append(
            {
                "id": declaration["id"],
                "sha256": ref["sha256"],
                "byte_count": len(raw),
                "source_root": str(root),
                "source_pin": ref,
                "source_header": header,
                "authority": "EXACT_NATIVE_DOCUMENT_BYTES_NOT_NEW_POLICY_APPROVAL",
            }
        )
        originals.append(raw)
    require(len({d["id"] for d in result}) == len(result), "Distinct native document IDs required")
    return result, originals


def initialize(destination, *, repository, plan, documents):
    """Unchanged default: admit committed repository documentary originals."""
    return _initialize(
        destination, repository=repository, plan=plan, documents=documents, native_documents=False
    )


def initialize_native(destination, *, repository, plan, documents):
    """Opt-in exact native document-byte admission; no source/audit/grant writes."""
    return _initialize(
        destination, repository=repository, plan=plan, documents=documents, native_documents=True
    )


def _initialize(destination, *, repository, plan, documents, native_documents):
    destination, repository = Path(destination), Path(repository)
    private(destination.parent, True)
    require(
        destination.is_absolute()
        and destination == destination.resolve()
        and not destination.exists(),
        "New canonical private runtime required",
    )
    plan = _plan(decode(encoded(plan)))
    original_declarations = decode(encoded(documents))
    documents, originals = (
        _native_documents(plan, original_declarations)
        if native_documents
        else _documents(repository, original_declarations)
    )
    org = snapshot(repository, as_of=plan["declared_at"][:10])
    assignment = [a for a in org["control_assignments"] if a["control_id"] == "SH-POL-001"]
    require(
        len(assignment) == 1 and assignment[0]["primary_person_id"] == plan["owner_id"],
        "Exact scoped local owner required; assignment is not policy approval",
    )
    people = {r["person_id"] for r in org["proposed_people"]}
    require(set(plan["recipients"]) <= people, "Explicit existing persona recipients required")
    cfg = {
        "format": "LOCAL_POLICY_DELIVERY_RUNTIME_V1",
        "plan": plan,
        "documents": documents,
        "code_pins": _code(),
        "imported_at": _now(),
        "organization_source_sha256": org["source_sha256"],
        "qualification": QUALIFICATION,
        "inventory_scope": "ONLY_DECLARED_PERSONA_MAILBOXES_NOT_WORKFORCE_COMPLETENESS",
    }
    if native_documents:
        cfg["document_admission"] = "EXPLICIT_NATIVE_POLICY_DOCUMENT_BYTES_V1"
    raw_cfg = encoded(cfg)
    require(len(raw_cfg) <= LIMIT, "Bounded runtime definition required")
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix="policy-stage-") as folder:
        stage = Path(folder)
        store = CompanyStore(stage)
        for system in SYSTEMS:
            store.register_system(plan["company"], plan["branch"], system, plan["owner_id"])
        (stage / "attempts").mkdir(mode=0o700)
        with (stage / "RUNTIME.json").open("xb") as f:
            os.chmod(stage / "RUNTIME.json", 0o600)
            f.write(raw_cfg)
            f.flush()
            os.fsync(f.fileno())
        with database(stage, True) as db:
            db.execute(
                "CREATE TABLE policy_commands(revision INTEGER UNIQUE, "
                "command_id TEXT PRIMARY KEY, digest TEXT, receipt BLOB)"
            )
            db.execute(
                "CREATE TABLE policy_state(id INTEGER PRIMARY KEY, revision INTEGER, body BLOB)"
            )
            for action in ("UPDATE", "DELETE"):
                db.execute(
                    f"CREATE TRIGGER policy_no_{action.lower()} BEFORE {action} "
                    "ON policy_commands BEGIN SELECT RAISE(ABORT,'Immutable policy command'); END"
                )
            _insert(
                db,
                cfg,
                "policy_definition",
                plan["runtime_id"],
                1,
                raw_cfg,
                plan["declared_at"],
                cfg["imported_at"],
            )
            for d, raw in zip(documents, originals, strict=True):
                _insert(
                    db,
                    cfg,
                    "policy_document",
                    d["id"],
                    1,
                    raw,
                    plan["declared_at"],
                    cfg["imported_at"],
                )
            db.execute("INSERT INTO policy_state VALUES(1,0,?)", (encoded(_initial(cfg)),))
            _bounds(db)
        require(
            _code() == cfg["code_pins"]
            and all(
                sha((repository / p).read_bytes()) == h for p, h in org["source_sha256"].items()
            ),
            "Initialization source/code changed before publication",
        )
        if native_documents:
            closing_documents, closing_raw = _native_documents(plan, original_declarations)
            require(
                encoded(closing_documents) == encoded(documents) and closing_raw == originals,
                "Native document bytes/clock/identity changed before publication",
            )
        else:
            for d, original in zip(documents, originals, strict=True):
                current, blob = _source(repository, d["path"])
                require(
                    current == original and blob == d["git_blob"],
                    "Document changed before publication",
                )
        publish(stage, destination)
    return {"runtime_sha256": sha(raw_cfg), "revision": 0, "qualification": QUALIFICATION}


def _doc(cfg, ident):
    matches = [d for d in cfg["documents"] if d["id"] == ident]
    require(len(matches) == 1, "Exact admitted document required")
    d = matches[0]
    return dict(
        zip(
            FIELDS,
            (
                cfg["plan"]["company"],
                cfg["plan"]["branch"],
                "policy_document",
                ident,
                1,
                d["sha256"],
            ),
            strict=True,
        )
    )


def _file(root, command, raw, retained=None):
    """Verify only generated, private command-owned mailbox paths; replacements fail closed."""
    path = Path(root) / "attempts" / sha(command.encode()) / "copied.bin"
    before = private(path).stat()
    data = checked_bytes(path, LIMIT)
    after = private(path).stat()
    fingerprint = {
        "device": before.st_dev,
        "inode": before.st_ino,
        "byte_count": len(data),
        "sha256": sha(data),
    }
    require(
        (before.st_dev, before.st_ino, before.st_ctime_ns)
        == (after.st_dev, after.st_ino, after.st_ctime_ns)
        and data == raw,
        "Mailbox original changed",
    )
    if retained is not None:
        require(encoded(fingerprint) == encoded(retained), "Mailbox identity or exact bytes differ")
    return fingerprint


def _attempt_names(root):
    parent = private(Path(root) / "attempts", True)
    entries = []
    with os.scandir(parent) as scan:
        for entry in scan:
            require(len(entries) < MAX_COMMANDS * 2, "Attempt inventory exceeds inspection bound")
            name = entry.name
            require(
                len(name) == 64 and all(c in "0123456789abcdef" for c in name),
                "Unknown owned attempt name",
            )
            private(parent / name, True)
            entries.append(name)
    return entries


def _mailbox_copy(root, command, raw, intent):
    """Durable intent and anchored private copy; orphan attempts are never adopted."""
    require(len(_attempt_names(root)) < MAX_COMMANDS * 2, "Attempt inventory limit")
    parent = private(Path(root) / "attempts", True)
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    folder_fd = None
    name = sha(command.encode())
    try:
        opened = os.fstat(parent_fd)
        require(
            opened.st_uid == os.getuid() and not opened.st_mode & 0o077,
            "Private copy parent required",
        )
        require(
            (opened.st_dev, opened.st_ino) == (parent.stat().st_dev, parent.stat().st_ino),
            "Copy parent changed",
        )
        try:
            os.mkdir(name, 0o700, dir_fd=parent_fd)
        except FileExistsError as exc:
            raise CompanyStoreError(
                "Uncommitted attempt exists; inspect and use an explicit new command"
            ) from exc
        folder_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)

        def write(name, content):
            fd = os.open(
                name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=folder_fd
            )
            with os.fdopen(fd, "wb") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())

        write("INTENT.json", encoded(intent))
        os.fsync(folder_fd)
        os.fsync(parent_fd)  # Intent durable before copied bytes.
        write("copied.bin", raw)
        os.fsync(folder_fd)
        os.fsync(parent_fd)
        current = private(parent, True).stat()
        folder = private(parent / name, True).stat()
        require(
            (opened.st_dev, opened.st_ino) == (current.st_dev, current.st_ino)
            and (folder.st_dev, folder.st_ino)
            == (os.fstat(folder_fd).st_dev, os.fstat(folder_fd).st_ino),
            "Copy directory changed",
        )
        return _file(root, command, raw)
    finally:
        if folder_fd is not None:
            os.close(folder_fd)
        os.close(parent_fd)


def _report(cfg, state, at):
    rows = []
    for recipient in cfg["plan"]["recipients"]:
        delivered = state["deliveries"].get(recipient)
        current = (
            delivered is not None and delivered["document_id"] == state["selected_document_id"]
        )
        read = state["reads"].get(recipient)
        assertion = state["assertions"].get(recipient)
        status = (
            "WITHDRAWN"
            if state["withdrawn"]
            else (
                "DELIVERED_CURRENT_VERSION"
                if current
                else (
                    "PRIOR_VERSION_ONLY"
                    if delivered
                    else ("MISSING_DUE" if at >= cfg["plan"]["due_at"] else "NOT_YET_DUE")
                )
            )
        )
        rows.append(
            {
                "recipient_id": recipient,
                "delivery_status": status,
                "delivery": delivered,
                "late": bool(current and delivered["event_at"] > cfg["plan"]["due_at"]),
                "read_return_current_delivery": bool(
                    current and read and read["delivery_command"] == delivered["command_id"]
                ),
                "simulated_assertion_current_delivery": bool(
                    current
                    and assertion
                    and assertion["delivery_command"] == delivered["command_id"]
                ),
                "human_acknowledgment": "NOT_ESTABLISHED",
            }
        )
    return {
        "as_of": at,
        "declared_recipient_count": len(rows),
        "recipients": rows,
        "selected_document_pin": _doc(cfg, state["selected_document_id"]),
        "withdrawn": state["withdrawn"],
        "qualification": QUALIFICATION,
    }


def _apply(cfg, state, request, revision, command, imported, fact):
    _keys(request, "expected_revision actor_id operation event_at rationale parameters")
    require(
        type(request["expected_revision"]) is int and request["expected_revision"] == revision,
        "Exact CAS required",
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
        "Explicit local rationale required",
    )
    op, args, actor = request["operation"], request["parameters"], request["actor_id"]
    require(isinstance(op, str), "Typed operation required")
    require(
        actor == cfg["plan"]["owner_id"]
        if op not in {"READ_RETURN", "RECIPIENT_ASSERTION"}
        else actor in cfg["plan"]["recipients"],
        "Exact declared local actor required; no authenticated-human inference",
    )
    after = deepcopy(state)
    after.update(event_at=at, imported_at=imported)
    if op in {"DELIVER", "READ_RETURN", "RECIPIENT_ASSERTION"}:
        _keys(
            args,
            "recipient_id document_pin"
            + (" read_command_id statement" if op == "RECIPIENT_ASSERTION" else ""),
        )
        recipient = args["recipient_id"]
        require(
            isinstance(recipient, str) and recipient in cfg["plan"]["recipients"],
            "Declared recipient required",
        )
        exact_pin(args["document_pin"])
        require(
            encoded(args["document_pin"]) == encoded(_doc(cfg, state["selected_document_id"]))
            and not state["withdrawn"],
            "Active exact selected document required",
        )
        if op == "DELIVER":
            _keys(fact, "device inode byte_count sha256")
            require(
                all(
                    type(fact[k]) is int and fact[k] >= 0 for k in ("device", "inode", "byte_count")
                )
                and fact["sha256"] == args["document_pin"]["sha256"],
                "Exact mailbox identity required",
            )
            observation = {
                "command_id": command,
                "document_id": state["selected_document_id"],
                "recipient_id": recipient,
                "event_at": at,
                "file": fact,
                "document_pin": args["document_pin"],
            }
            after["deliveries"][recipient] = observation
        else:
            require(
                fact is None and actor == recipient,
                "Only named simulated recipient may assert/read",
            )
            delivery = state["deliveries"].get(recipient)
            require(
                delivery is not None and delivery["document_id"] == state["selected_document_id"],
                "Current exact delivery required",
            )
            observation = {
                "command_id": command,
                "delivery_command": delivery["command_id"],
                "event_at": at,
                "document_pin": args["document_pin"],
                "returned_sha256": args["document_pin"]["sha256"],
                "actor_basis": "EXPLICIT_SIMULATED_ACTOR_ASSERTION_NOT_AUTHENTICATED_HUMAN",
            }
            if op == "READ_RETURN":
                after["reads"][recipient] = observation
            else:
                read = state["reads"].get(recipient)
                require(
                    read is not None
                    and read["delivery_command"] == delivery["command_id"]
                    and read["command_id"] == args["read_command_id"],
                    "Exact current retained read-return required",
                )
                require(
                    isinstance(args["statement"], str)
                    and 1 <= len(args["statement"].strip()) <= 1000,
                    "Bounded simulated assertion required",
                )
                observation.update(
                    statement=args["statement"],
                    read_command_id=args["read_command_id"],
                    human_acknowledgment="NOT_ESTABLISHED",
                )
                after["assertions"][recipient] = observation
    elif op == "SELECT_DOCUMENT":
        _keys(args, "previous_document_pin document_pin")
        require(fact is None, "No file fact allowed")
        for key in args:
            exact_pin(args[key])
        require(
            encoded(args["previous_document_pin"])
            == encoded(_doc(cfg, state["selected_document_id"])),
            "Current document pin required",
        )
        selected = [
            d
            for d in cfg["documents"]
            if encoded(_doc(cfg, d["id"])) == encoded(args["document_pin"])
        ]
        require(
            len(selected) == 1 and selected[0]["id"] != state["selected_document_id"],
            "Different explicitly admitted document required",
        )
        after.update(selected_document_id=selected[0]["id"], withdrawn=False)
        observation = {
            "previous_document_pin": args["previous_document_pin"],
            "document_pin": args["document_pin"],
            "authority": "LOCAL_DISTRIBUTION_SELECTION_NOT_POLICY_APPROVAL",
        }
    elif op == "LOCAL_WITHDRAW":
        _keys(args, "document_pin")
        exact_pin(args["document_pin"])
        require(
            fact is None
            and encoded(args["document_pin"]) == encoded(_doc(cfg, state["selected_document_id"]))
            and not state["withdrawn"],
            "Active current local selection required",
        )
        after["withdrawn"] = True
        observation = {
            "document_pin": args["document_pin"],
            "status": "LOCAL_DISTRIBUTION_WITHDRAWN_NOT_POLICY_REPEAL",
        }
    elif op == "RECONCILE":
        _keys(args, "")
        require(fact is None, "No file fact allowed")
        observation = _report(cfg, state, at)
    else:
        raise CompanyStoreError("Unsupported bounded policy operation")
    return after, observation


def _history(root, db, cfg):
    _bounds(db)
    p = cfg["plan"]
    systems = db.execute("SELECT company,branch,system,owner FROM systems").fetchall()
    require(
        {tuple(r) for r in systems}
        == {(p["company"], p["branch"], s, p["owner_id"]) for s in SYSTEMS},
        "Exact owner systems required",
    )
    _verify(
        db,
        cfg,
        "policy_definition",
        p["runtime_id"],
        1,
        encoded(cfg),
        p["declared_at"],
        cfg["imported_at"],
    )
    documents = {}
    for d in cfg["documents"]:
        raw = native(db, _doc(cfg, d["id"]))["content"]
        require(len(raw) == d["byte_count"], "Document count differs")
        _verify(db, cfg, "policy_document", d["id"], 1, raw, p["declared_at"], cfg["imported_at"])
        documents[d["id"]] = raw
    state = _initial(cfg)
    receipts = {}
    commands = db.execute("SELECT * FROM policy_commands ORDER BY revision").fetchall()
    for revision, row in enumerate(commands):
        receipt = decode(row["receipt"])
        _keys(
            receipt,
            "revision command_id request request_sha256 prior_state_sha256 state_sha256 "
            "event_at imported_at observation file_fact runtime_sha256 qualification operation_pin",
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
        after, observation = _apply(
            cfg,
            state,
            receipt["request"],
            revision,
            row["command_id"],
            receipt["imported_at"],
            receipt["file_fact"],
        )
        if receipt["request"]["operation"] == "DELIVER":
            _file(
                root, row["command_id"], documents[observation["document_id"]], receipt["file_fact"]
            )
            intent = decode(
                checked_bytes(
                    Path(root) / "attempts" / sha(row["command_id"].encode()) / "INTENT.json", 65536
                )
            )
            require(
                encoded(intent)
                == encoded(
                    {
                        "status": "INTENT_ONLY_NOT_DELIVERY",
                        "command_id": row["command_id"],
                        "request_sha256": receipt["request_sha256"],
                        "runtime_sha256": sha(encoded(cfg)),
                        "document_pin": receipt["request"]["parameters"]["document_pin"],
                    }
                ),
                "Retained copy intent differs",
            )
        require(
            encoded(observation) == encoded(receipt["observation"])
            and receipt["state_sha256"] == sha(encoded(after))
            and receipt["event_at"] == after["event_at"],
            "Recomputed operation differs",
        )
        body = {k: v for k, v in receipt.items() if k != "operation_pin"}
        op = _verify(
            db,
            cfg,
            "policy_operation",
            f"OP-{revision + 1}",
            1,
            encoded(body),
            receipt["event_at"],
            receipt["imported_at"],
        )
        require(encoded(op) == encoded(receipt["operation_pin"]), "Operation pin differs")
        state = after
        receipts[row["command_id"]] = receipt
    current = db.execute("SELECT * FROM policy_state").fetchall()
    require(
        len(current) == 1
        and current[0]["id"] == 1
        and current[0]["revision"] == len(commands)
        and encoded(decode(current[0]["body"])) == encoded(state)
        and db.execute("SELECT COUNT(*) FROM versions").fetchone()[0]
        == 1 + len(documents) + len(commands),
        "Current state or original count differs from replayed operations",
    )
    return len(commands), state, documents, receipts


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
    """Commit a local operation; READ_RETURN additionally returns verified original bytes."""
    require(
        type(expected_revision) is int and 0 <= expected_revision <= MAX_COMMANDS,
        "Exact bounded revision required",
    )
    _id(command_id)
    _id(actor_id)
    cfg = _config(root, expected_runtime_sha256)
    request = {
        "expected_revision": expected_revision,
        "actor_id": actor_id,
        "operation": operation,
        "event_at": _stamp(event_at),
        "rationale": rationale,
        "parameters": decode(encoded(parameters)),
    }
    require(len(encoded(request)) <= 65536, "Bounded command required")
    with database(Path(root), True) as db:
        revision, state, documents, receipts = _history(root, db, cfg)
        if command_id in receipts:
            receipt = receipts[command_id]
            require(
                encoded(receipt["request"]) == encoded(request), "Changed exact replay envelope"
            )
            # Historical receipts remain immutable; revoked reads cannot return bytes again.
            if operation == "READ_RETURN":
                require(
                    not state["withdrawn"]
                    and encoded(parameters["document_pin"])
                    == encoded(_doc(cfg, state["selected_document_id"])),
                    "Historical read bytes unavailable after local withdrawal/version change",
                )
            require(_config(root, expected_runtime_sha256) == cfg, "Runtime changed during replay")
            result = {"receipt": receipt}
            if operation == "READ_RETURN":
                result["content"] = documents[state["selected_document_id"]]
            return result
        require(
            revision == expected_revision and revision < MAX_COMMANDS,
            "Revision conflict or command limit",
        )
        imported = _now()
        fact = None
        if operation == "DELIVER":
            # Validate all authority, timestamp, scope and parameters before any filesystem write.
            proposed = {
                "device": 0,
                "inode": 0,
                "byte_count": len(documents[state["selected_document_id"]]),
                "sha256": _doc(cfg, state["selected_document_id"])["sha256"],
            }
            _apply(cfg, state, request, revision, command_id, imported, proposed)
            fact = _mailbox_copy(
                root,
                command_id,
                documents[state["selected_document_id"]],
                {
                    "status": "INTENT_ONLY_NOT_DELIVERY",
                    "command_id": command_id,
                    "request_sha256": sha(encoded(request)),
                    "runtime_sha256": expected_runtime_sha256,
                    "document_pin": request["parameters"]["document_pin"],
                },
            )
        after, observation = _apply(cfg, state, request, revision, command_id, imported, fact)
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
            "file_fact": fact,
            "runtime_sha256": expected_runtime_sha256,
            "qualification": QUALIFICATION,
        }
        op = _insert(
            db,
            cfg,
            "policy_operation",
            f"OP-{revision + 1}",
            1,
            encoded(body),
            request["event_at"],
            imported,
        )
        receipt = body | {"operation_pin": op}
        db.execute(
            "INSERT INTO policy_commands VALUES(?,?,?,?)",
            (revision + 1, command_id, body["request_sha256"], encoded(receipt)),
        )
        db.execute(
            "UPDATE policy_state SET revision=?,body=? WHERE id=1", (revision + 1, encoded(after))
        )
        _bounds(db)
        # Re-read every current native/file/receipt under the same transaction before commit.
        _history(root, db, cfg)
        require(_config(root, expected_runtime_sha256) == cfg, "Runtime changed before commit")
    result = {"receipt": receipt}
    if operation == "READ_RETURN":
        result["content"] = documents[state["selected_document_id"]]
    return result


def inspect(root, *, expected_runtime_sha256, as_of):
    cfg = _config(root, expected_runtime_sha256)
    with database(Path(root)) as db:
        revision, state, _, receipts = _history(root, db, cfg)
        at = _stamp(as_of)
        require(at >= state["event_at"], "Current state unavailable at requested cutoff")
        parent = private(Path(root) / "attempts", True)
        # A bounded inventory of owned paths. Orphan bytes are never treated as delivered.
        entries = _attempt_names(root)
        committed = {
            sha(c.encode()) for c, r in receipts.items() if r["request"]["operation"] == "DELIVER"
        }
        orphans = []
        for name in sorted(set(entries) - committed):
            require(
                len(name) == 64 and all(c in "0123456789abcdef" for c in name),
                "Unknown owned attempt name",
            )
            private(parent / name, True)
            orphans.append({"attempt_id": name, "status": "UNCOMMITTED_ATTEMPT_NOT_DELIVERY"})
        require(_config(root, expected_runtime_sha256) == cfg, "Runtime changed during inspection")
    return {
        "revision": revision,
        "state": state,
        "report": _report(cfg, state, at),
        "uncommitted_attempts": orphans,
        "qualification": QUALIFICATION,
    }


def inspect_at(root, *, expected_runtime_sha256, as_of):
    """Freshly derive an exact historical prefix of the verified native operations.

    This does not relax inspect's current-state cutoff guard. All current
    native originals, mailbox bytes, receipts and current state are reverified
    before a past prefix is derived; cached observation text is never trusted.
    """
    require(type(as_of) is str, "Explicit historical policy cutoff required")
    at = _stamp(as_of)
    cfg = _config(root, expected_runtime_sha256)
    require(at >= cfg["plan"]["declared_at"], "Policy runtime unavailable at cutoff")
    with database(Path(root)) as db:
        _, _, _, receipts = _history(root, db, cfg)
        state = _initial(cfg)
        prefix_revision = 0
        for command, receipt in receipts.items():
            if receipt["event_at"] > at:
                break
            after, observation = _apply(
                cfg,
                state,
                receipt["request"],
                prefix_revision,
                command,
                receipt["imported_at"],
                receipt["file_fact"],
            )
            require(
                sha(encoded(after)) == receipt["state_sha256"]
                and encoded(observation) == encoded(receipt["observation"]),
                "Recomputed historical native policy prefix differs",
            )
            state = after
            prefix_revision += 1
        native(db, _doc(cfg, state["selected_document_id"]), at)
        require(
            _config(root, expected_runtime_sha256) == cfg, "Runtime changed during prefix replay"
        )
    return {
        "revision": prefix_revision,
        "state": state,
        "report": _report(cfg, state, at),
        "state_basis": "FRESH_VERIFIED_NATIVE_OPERATION_PREFIX_AT_EXACT_CUTOFF",
        "qualification": QUALIFICATION,
    }
