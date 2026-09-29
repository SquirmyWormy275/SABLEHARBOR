"""Explicit instructor-authored assessment history; never automatic grades or disclosure."""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .bound_instructor import read_binding
from .instructor_comparison import compare
from .instructor_key_views import fields, integer, pin, require, text
from .personal_views import PersonalViews
from .store import DomainError, canonical, digest, identifier
from .workspace_context import _basis

DIMENSIONS = ("discovery", "evidence", "testing", "judgment", "documentation", "follow-through")
QUALIFICATION = "INSTRUCTOR_AUTHORED_UNVALIDATED_NO_AGGREGATE_GRADE_SHARED_STATE_NOT_SUBMISSION"
MAX_DOCUMENTS = 256
RELATIONS = {
    "artifact": "EXACT_RETAINED_METADATA_LINK_NOT_BYTE_REREAD",
    "request": "CONTROL_ASSOCIATION_ONLY",
    "task": "CONTROL_ASSOCIATION_ONLY",
    "population": "EXPLICIT_SOURCE_LINK",
    "selection": "RECORDED_POPULATION_LINK",
    "workpaper": {"EXACT_RECORDED_WORKPAPER_VERSION", "EXACT_AUTHORED_TASK_WORKPAPER_VERSION"},
    "review": "RECORDED_WORKPAPER_REVIEW_LINK",
    "sample_execution": "EXACT_RECORDED_ITEM_OR_AUTHORED_TASK_LINK",
    "finding": "DIRECT_RECORDED_FINDING_EVIDENCE_ID",
    "remediation": "DIRECT_RECORDED_REMEDIATION_EVIDENCE_ID",
}
ZERO = "0" * 64
PIN_FIELDS = (
    "key_pin",
    "rubric_sha256",
    "inventory_sha256",
    "audited_actor_id",
    "learner_revision",
    "selected_state_sha256",
    "selected_history_sha256",
    "selected_history_tip_sha256",
    "bound_revision",
)
AUTHORED_FIELDS = (
    "title",
    "issue_ids",
    "expectation_ids",
    "dimensions",
    "alternatives",
    "overrides",
    "defects",
)


def ids(value, maximum=32):
    require(isinstance(value, list) and len(value) <= maximum, "Bounded explicit IDs required")
    for item in value:
        text(item, 128, True)
    require(len(set(value)) == len(value), "Duplicate explicit ID")
    return value


def authored(value):
    fields(value, AUTHORED_FIELDS)
    text(value["title"], 200, True)
    require(bool(ids(value["issue_ids"], 10)), "Explicit selected issues required")
    ids(value["expectation_ids"], 10)
    dimensions = value["dimensions"]
    require(
        isinstance(dimensions, list) and len(dimensions) == 6,
        "Six explicit qualitative dimensions required",
    )
    selected = set()
    for dimension in dimensions:
        fields(dimension, ("dimension", "assessment", "rationale", "reference_ids"))
        require(
            isinstance(dimension["dimension"], str)
            and dimension["dimension"] in DIMENSIONS
            and dimension["dimension"] not in selected,
            "Each dimension exactly once required",
        )
        selected.add(dimension["dimension"])
        text(dimension["assessment"], 2000, True)
        text(dimension["rationale"], 4000, True)
        ids(dimension["reference_ids"])
    shapes = {
        "alternatives": ("expectation_id", "description", "rationale", "reference_ids"),
        "overrides": (
            "expectation_id",
            "prior_interpretation",
            "replacement",
            "rationale",
            "reference_ids",
        ),
        "defects": ("issue_id", "description", "impact", "rationale", "reference_ids"),
    }
    for family, keys in shapes.items():
        require(
            isinstance(value[family], list) and len(value[family]) <= 8,
            "Assessment annotation limit",
        )
        for item in value[family]:
            fields(item, keys)
            target = "issue_id" if family == "defects" else "expectation_id"
            require(
                item[target] in value["issue_ids" if family == "defects" else "expectation_ids"],
                "Annotation requires selected authored target",
            )
            ids(item["reference_ids"])
            for key in keys:
                if key not in {target, "reference_ids"}:
                    text(item[key], 4000 if key == "rationale" else 2000, True)
    references = {
        r
        for family in ("dimensions", "alternatives", "overrides", "defects")
        for item in value[family]
        for r in item["reference_ids"]
    }
    require(len(references) <= 32, "Selected evidence reference limit")
    return references


def references(inventory):
    result = {}

    def add(kind, row, relation, expectation, content=None):
        reference = {
            "kind": kind,
            "record_id": row["id"],
            "version": row.get("version", row.get("workpaper_version")),
            "inventory_sha256": digest(row),
            "content_sha256": content,
            "relation": relation,
        }
        key = "REF-" + digest(reference)
        if key not in result:
            result[key] = {"id": key, **reference, "expectation_ids": []}
        if expectation not in result[key]["expectation_ids"]:
            result[key]["expectation_ids"].append(expectation)

    source_rows = {row["source_id"]: row for row in inventory["sources"]}
    for expectation in inventory["expectations"]:
        eid = expectation["expectation_id"]
        for source in expectation["source_ids"]:
            for row in source_rows[source]["exact_retained_artifacts"]:
                add(
                    "artifact",
                    row,
                    "EXACT_RETAINED_METADATA_LINK_NOT_BYTE_REREAD",
                    eid,
                    row["sha256"],
                )
        for kind, collection, relation in (
            (
                "request",
                expectation["control_associated_records_only"]["requests"],
                "CONTROL_ASSOCIATION_ONLY",
            ),
            (
                "task",
                expectation["control_associated_records_only"]["tasks"],
                "CONTROL_ASSOCIATION_ONLY",
            ),
            ("population", expectation["source_linked_populations"], "EXPLICIT_SOURCE_LINK"),
            ("selection", expectation["population_linked_selections"], "RECORDED_POPULATION_LINK"),
            (
                "workpaper",
                expectation["source_linked_workpaper_versions"],
                "EXACT_RECORDED_WORKPAPER_VERSION",
            ),
            (
                "workpaper",
                expectation.get("task_linked_workpaper_versions", []),
                "EXACT_AUTHORED_TASK_WORKPAPER_VERSION",
            ),
            ("review", expectation["workpaper_version_reviews"], "RECORDED_WORKPAPER_REVIEW_LINK"),
            (
                "sample_execution",
                expectation.get("recorded_sample_executions", []),
                RELATIONS["sample_execution"],
            ),
            ("finding", expectation.get("recorded_findings", []), RELATIONS["finding"]),
            ("remediation", expectation.get("recorded_remediations", []), RELATIONS["remediation"]),
        ):
            for row in collection:
                add(kind, row, relation, eid, row.get("version_sha256", row.get("record_sha256")))
    require(len(result) <= 4096, "Assessment reference inventory limit")
    return list(result.values())


def validate_document(document):
    fields(
        document,
        (
            "schema",
            "id",
            "version",
            "actor_id",
            "engagement_id",
            "recorded_at",
            "predecessor",
            "pins",
            "authored",
            "selected_issues",
            "selected_expectations",
            "references",
            "qualification",
        ),
    )
    require(
        document["schema"] == "INSTRUCTOR_AUTHORED_ASSESSMENT_V1"
        and document["qualification"] == QUALIFICATION,
        "Assessment schema or qualification differs",
    )
    for key in ("id", "actor_id", "engagement_id"):
        text(document[key], 128, True)
    integer(document["version"], MAX_DOCUMENTS)
    require(
        document["version"] > 0
        and datetime.fromisoformat(document["recorded_at"]).tzinfo is not None,
        "Assessment version/time required",
    )
    fields(document["pins"], PIN_FIELDS)
    for key in PIN_FIELDS:
        if key in {"learner_revision", "bound_revision"}:
            integer(document["pins"][key])
        elif key == "audited_actor_id":
            text(document["pins"][key], 128, True)
        else:
            pin(document["pins"][key])
    if document["predecessor"] is not None:
        fields(document["predecessor"], ("id", "sha256"))
        text(document["predecessor"]["id"], 128, True)
        pin(document["predecessor"]["sha256"])
    wanted = authored(document["authored"])
    require(
        isinstance(document["references"], list) and len(document["references"]) == len(wanted),
        "Assessment reference closure differs",
    )
    seen = set()
    for ref in document["references"]:
        fields(
            ref,
            (
                "id",
                "kind",
                "record_id",
                "version",
                "inventory_sha256",
                "content_sha256",
                "relation",
                "expectation_ids",
            ),
        )
        require(ref["id"] in wanted and ref["id"] not in seen, "Selected reference differs")
        seen.add(ref["id"])
        require(
            ref["kind"] in RELATIONS,
            "Unsupported assessment reference",
        )
        allowed = RELATIONS[ref["kind"]]
        require(
            ref["relation"] in (allowed if isinstance(allowed, set) else {allowed}),
            "Assessment reference relation differs",
        )
        text(ref["record_id"], 128, True)
        pin(ref["inventory_sha256"])
        if ref["kind"] in {"sample_execution", "finding", "remediation"}:
            pin(ref["content_sha256"])
        if ref["kind"] == "sample_execution":
            integer(ref["version"])
            require(ref["version"] > 0, "Recorded execution revision required")
        if ref["content_sha256"] is not None:
            pin(ref["content_sha256"])
        if ref["version"] is not None:
            integer(ref["version"])
        require(bool(ids(ref["expectation_ids"], 2000)), "Reference expectation required")
        require(
            set(ref["expectation_ids"]) <= set(document["authored"]["expectation_ids"]),
            "Unselected reference expectation",
        )
        base = {
            k: ref[k]
            for k in (
                "kind",
                "record_id",
                "version",
                "inventory_sha256",
                "content_sha256",
                "relation",
            )
        }
        require(ref["id"] == "REF-" + digest(base), "Reference digest differs")
    require(
        isinstance(document["selected_issues"], list)
        and isinstance(document["selected_expectations"], list),
        "Selected rubric lists required",
    )
    require(
        [r["id"] for r in document["selected_issues"]] == document["authored"]["issue_ids"]
        and [r["id"] for r in document["selected_expectations"]]
        == document["authored"]["expectation_ids"],
        "Selected rubric identities differ",
    )
    for issue in document["selected_issues"]:
        fields(issue, ("id", "control_ids", "claim", "uncertainty"))
        ids(issue["control_ids"], 100)
        text(issue["claim"], 16000, True)
        text(issue["uncertainty"], 16000, True)
    for expectation in document["selected_expectations"]:
        fields(expectation, ("id", "issue_ids", "procedure", "acceptable_alternatives"))
        ids(expectation["issue_ids"], 10)
        require(
            set(expectation["issue_ids"]) <= set(document["authored"]["issue_ids"]),
            "Expectation issue closure differs",
        )
        text(expectation["procedure"], 16000, True)
        require(
            isinstance(expectation["acceptable_alternatives"], list)
            and len(expectation["acceptable_alternatives"]) <= 100,
            "Bounded authored alternatives required",
        )
        for alternative in expectation["acceptable_alternatives"]:
            text(alternative, 16000, True)
    require(len(canonical(document).encode()) <= 256 * 1024, "Assessment document byte limit")
    return document


def validate_archive(value):
    try:
        fields(value, ("schema", "restoration", "documents"))
        require(
            value["schema"] == "PRIVATE_INSTRUCTOR_ASSESSMENTS_V1"
            and value["restoration"] == "INERT_ONLY_NO_ACTIVE_REHYDRATION",
            "Unsupported assessment archive",
        )
        require(
            isinstance(value["documents"], list)
            and len(value["documents"]) <= MAX_DOCUMENTS
            and len(canonical(value).encode()) <= 32 * 1024 * 1024,
            "Assessment archive limit",
        )
        previous, seen, children, commands = ZERO, {}, set(), set()
        for number, row in enumerate(value["documents"], 1):
            fields(row, ("seq", "body", "sha256"))
            body = json.loads(row["body"])
            fields(
                body,
                (
                    "document",
                    "saved_engagement_revision",
                    "basis_sha256",
                    "command_id",
                    "request_sha256",
                    "previous_sha256",
                ),
            )
            require(
                type(row["seq"]) is int
                and row["seq"] == number
                and canonical(body) == row["body"]
                and digest(body) == row["sha256"]
                and body["previous_sha256"] == previous,
                "Assessment history differs",
            )
            doc = validate_document(body["document"])
            integer(body["saved_engagement_revision"])
            pin(body["basis_sha256"])
            pin(body["request_sha256"])
            text(body["command_id"], 128, True)
            require(
                doc["id"] not in seen
                and doc["pins"]["learner_revision"] <= body["saved_engagement_revision"],
                "Assessment identity/history differs",
            )
            parent = doc["predecessor"]
            if parent:
                require(
                    parent["id"] in seen and parent["id"] not in children,
                    "Assessment predecessor unavailable or superseded",
                )
                old = seen[parent["id"]]
                require(
                    digest(old) == parent["sha256"]
                    and all(old[k] == doc[k] for k in ("actor_id", "engagement_id"))
                    and doc["version"] == old["version"] + 1,
                    "Assessment correction lineage differs",
                )
                children.add(parent["id"])
            else:
                require(doc["version"] == 1, "Initial assessment version differs")
            command = (doc["actor_id"], doc["engagement_id"], body["command_id"])
            require(command not in commands, "Duplicate assessment command")
            commands.add(command)
            seen[doc["id"]] = doc
            previous = row["sha256"]
        return value
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as error:
        raise DomainError("Invalid private assessment archive") from error


class InstructorAssessments:
    def __init__(self, private_root, engine, bindings):
        self.root, self.engine, self.bindings = Path(private_root), engine, bindings
        self.path = self.root / "assessments.sqlite3"
        PersonalViews._private(self.root, True)
        if not self.path.exists():
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            os.close(fd)
        with self._db(False) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS documents(seq INTEGER PRIMARY KEY,body TEXT,sha256 TEXT);
                CREATE TRIGGER IF NOT EXISTS assessment_no_update BEFORE UPDATE ON documents
                BEGIN SELECT RAISE(ABORT,'Immutable assessment'); END;
                CREATE TRIGGER IF NOT EXISTS assessment_no_delete BEFORE DELETE ON documents
                BEGIN SELECT RAISE(ABORT,'Immutable assessment'); END;""")

    @contextmanager
    def _db(self, check=True):
        root_pin = PersonalViews._private(self.root, True)
        file_pin = PersonalViews._private(self.path)
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute("BEGIN IMMEDIATE")
            if check:
                self._snapshot(db)
            yield db
            require(
                PersonalViews._private(self.root, True) == root_pin
                and PersonalViews._private(self.path) == file_pin,
                "Assessment store changed",
                409,
            )
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _snapshot(db):
        size, count = db.execute(
            "SELECT coalesce(sum(length(CAST(body AS BLOB))),0),count(*) FROM documents"
        ).fetchone()
        require(size <= 16 * 1024 * 1024 and count <= MAX_DOCUMENTS, "Assessment storage limit")
        return validate_archive(
            {
                "schema": "PRIVATE_INSTRUCTOR_ASSESSMENTS_V1",
                "restoration": "INERT_ONLY_NO_ACTIVE_REHYDRATION",
                "documents": [
                    dict(row) for row in db.execute("SELECT * FROM documents ORDER BY seq")
                ],
            }
        )

    def _state(self, actor, eid):
        require(
            self.engine.store.membership(actor, eid) == "instruct",
            "Scoped instructor required",
            403,
        )
        return self.engine.store.get(actor, eid)

    def _context(self, actor, eid):
        state = self._state(actor, eid)
        key, error = None, None
        try:
            bound = read_binding(self.engine, {"id": actor}, eid, self.bindings)
            key = bound["binding"]["manifest_sha256"]
        except (DomainError, OSError, ValueError, KeyError) as exc:
            if isinstance(exc, DomainError) and exc.status == 403:
                raise
            error = "KEY_UNAVAILABLE"
        return {
            "state": state,
            "key": key,
            "error": error,
            "basis": digest({"actor_id": actor, "engagement_id": eid, **_basis(state)}),
        }

    def _finish(self, actor, eid, context):
        current = self._context(actor, eid)
        require(
            current["key"] == context["key"]
            and current["error"] == context["error"]
            and current["basis"] == context["basis"]
            and digest(current["state"]) == digest(context["state"]),
            "Assessment context changed",
            409,
        )

    def options(self, actor, eid, revision):
        state = self._state(actor, eid)
        integer(revision)
        bound = read_binding(self.engine, {"id": actor}, eid, self.bindings)
        snapshot = bound["snapshot"]
        require(
            len(snapshot["authored"]["issues"]) <= 2000
            and len(snapshot["authored"]["expectations"]) <= 2000,
            "Assessment rubric limit",
        )
        inventory = compare(self.engine, {"id": actor}, eid, self.bindings, revision=revision)
        require(
            inventory["status"] == "DETERMINISTIC_LINK_INVENTORY_ONLY",
            "Selected assessment context unavailable",
            409,
        )
        require(
            inventory["binding_manifest_sha256"] == bound["binding"]["manifest_sha256"]
            and inventory["current_revision"] == state["revision"],
            "Assessment context changed",
            409,
        )
        require(
            len(canonical(inventory).encode()) <= 8 * 1024 * 1024, "Assessment inventory byte limit"
        )
        data = {
            "engagement_id": eid,
            "current_engagement_revision": state["revision"],
            "learner_revision": revision,
            "key_pin": inventory["binding_manifest_sha256"],
            "rubric_sha256": digest(snapshot["authored"]),
            "inventory_sha256": digest(
                {k: v for k, v in inventory.items() if k != "current_revision"}
            ),
            "issues": [
                {k: row[k] for k in ("id", "claim", "control_ids", "uncertainty")}
                for row in snapshot["authored"]["issues"]
            ],
            "expectations": [
                {k: row[k] for k in ("id", "issue_ids", "procedure", "acceptable_alternatives")}
                for row in snapshot["authored"]["expectations"]
            ],
            "references": references(inventory),
            "qualification": QUALIFICATION,
        }
        data.update(
            {
                k: inventory[k]
                for k in (
                    "audited_actor_id",
                    "bound_revision",
                    "selected_state_sha256",
                    "selected_history_sha256",
                    "selected_history_tip_sha256",
                )
            }
        )
        self._finish(
            actor,
            eid,
            {
                "state": state,
                "key": data["key_pin"],
                "error": None,
                "basis": digest({"actor_id": actor, "engagement_id": eid, **_basis(state)}),
            },
        )
        return data

    @staticmethod
    def _owned(db, actor, eid):
        return [
            json.loads(row[0])
            for row in db.execute("SELECT body FROM documents ORDER BY seq")
            if (
                lambda body: (
                    body["document"]["actor_id"] == actor
                    and body["document"]["engagement_id"] == eid
                )
            )(json.loads(row[0]))
        ]

    def _dto(self, body, context, *, detail=False, leaf=True):
        doc = body["document"]
        status = context["error"] or (
            "KEY_CHANGED"
            if context["key"] != doc["pins"]["key_pin"]
            else "CONTEXT_CHANGED"
            if context["basis"] != body["basis_sha256"]
            else "CURRENT"
        )
        visible = status == "CURRENT"
        result = {
            "id": doc["id"],
            "engagement_id": doc["engagement_id"],
            "version": doc["version"],
            "sha256": digest(doc),
            "predecessor": doc["predecessor"],
            "saved_engagement_revision": body["saved_engagement_revision"],
            "current_engagement_revision": context["state"]["revision"],
            "learner_revision": doc["pins"]["learner_revision"],
            "context_status": status,
            "personal_content_visible": visible,
            "correction_allowed": visible and leaf,
            "backup_status": "INERT_ARCHIVE_ONLY",
        }
        if visible:
            result["title"] = doc["authored"]["title"]
            if detail:
                result["document"] = doc
        return result

    def listing(self, actor, eid):
        context = self._context(actor, eid)
        with self._db() as db:
            rows = self._owned(db, actor, eid)
            parents = {
                row["document"]["predecessor"]["id"]
                for row in rows
                if row["document"]["predecessor"]
            }
            result = [
                self._dto(row, context, leaf=row["document"]["id"] not in parents) for row in rows
            ]
            self._finish(actor, eid, context)
        return {
            "engagement_id": eid,
            "current_engagement_revision": context["state"]["revision"],
            "assessments": result,
        }

    def read(self, actor, eid, assessment_id):
        context = self._context(actor, eid)
        with self._db() as db:
            rows = self._owned(db, actor, eid)
            row = next((row for row in rows if row["document"]["id"] == assessment_id), None)
            require(row is not None, "Assessment unavailable", 404)
            result = self._dto(
                row,
                context,
                detail=True,
                leaf=not any(
                    r["document"]["predecessor"]
                    and r["document"]["predecessor"]["id"] == assessment_id
                    for r in rows
                ),
            )
            if result["personal_content_visible"]:
                checked = self.options(actor, eid, row["document"]["pins"]["learner_revision"])
                require(
                    all(checked[k] == v for k, v in row["document"]["pins"].items()),
                    "Historical assessment pins changed",
                    409,
                )
            self._finish(actor, eid, context)
            return result

    def save(self, actor, eid, payload):
        fields(
            payload,
            (
                "expected_engagement_revision",
                "learner_revision",
                "key_pin",
                "rubric_sha256",
                "inventory_sha256",
                *AUTHORED_FIELDS,
                "predecessor",
                "command_id",
            ),
        )
        p = json.loads(canonical(payload))
        integer(p["expected_engagement_revision"])
        integer(p["learner_revision"])
        text(p["command_id"], 128, True)
        for key in ("key_pin", "rubric_sha256", "inventory_sha256"):
            pin(p[key])
        user = {k: p[k] for k in AUTHORED_FIELDS}
        selected_refs = authored(user)
        context = self._context(actor, eid)
        checked = self.options(actor, eid, p["learner_revision"])
        require(
            all(checked[k] == p[k] for k in ("key_pin", "rubric_sha256", "inventory_sha256")),
            "Assessment input pins changed",
            409,
        )
        with self._db() as db:
            rows = self._owned(db, actor, eid)
            replay = next((row for row in rows if row["command_id"] == p["command_id"]), None)
            if replay:
                require(
                    replay["request_sha256"] == digest(p), "Assessment command payload differs", 409
                )
                result = self._dto(
                    replay,
                    context,
                    detail=True,
                    leaf=not any(
                        r["document"]["predecessor"]
                        and r["document"]["predecessor"]["id"] == replay["document"]["id"]
                        for r in rows
                    ),
                )
                self._finish(actor, eid, context)
                return result
            require(
                context["state"]["revision"]
                == p["expected_engagement_revision"]
                == checked["current_engagement_revision"],
                "Assessment engagement revision conflict",
                409,
            )
            issues = {r["id"]: r for r in checked["issues"]}
            expectations = {r["id"]: r for r in checked["expectations"]}
            require(
                all(i in issues for i in user["issue_ids"])
                and all(i in expectations for i in user["expectation_ids"]),
                "Selected rubric item unavailable",
            )
            require(
                all(
                    set(expectations[i]["issue_ids"]) <= set(user["issue_ids"])
                    for i in user["expectation_ids"]
                ),
                "Explicit expectation issue closure required",
            )
            refs = {r["id"]: r for r in checked["references"]}
            require(
                all(
                    r in refs and set(refs[r]["expectation_ids"]) & set(user["expectation_ids"])
                    for r in selected_refs
                ),
                "Selected evidence reference outside authored scope",
            )
            version = 1
            if p["predecessor"] is not None:
                fields(p["predecessor"], ("id", "sha256"))
                parent = next(
                    (r["document"] for r in rows if r["document"]["id"] == p["predecessor"]["id"]),
                    None,
                )
                require(
                    parent is not None
                    and digest(parent) == p["predecessor"]["sha256"]
                    and not any(
                        r["document"]["predecessor"]
                        and r["document"]["predecessor"]["id"] == parent["id"]
                        for r in rows
                    ),
                    "Correction predecessor unavailable or superseded",
                    409,
                )
                version = parent["version"] + 1
            document = {
                "schema": "INSTRUCTOR_AUTHORED_ASSESSMENT_V1",
                "id": identifier("ASSESSMENT"),
                "version": version,
                "actor_id": actor,
                "engagement_id": eid,
                "recorded_at": datetime.now(UTC).isoformat(),
                "predecessor": p["predecessor"],
                "pins": {k: checked[k] for k in PIN_FIELDS},
                "authored": user,
                "selected_issues": [issues[i] for i in user["issue_ids"]],
                "selected_expectations": [expectations[i] for i in user["expectation_ids"]],
                "references": [
                    {
                        **refs[r],
                        "expectation_ids": [
                            i for i in refs[r]["expectation_ids"] if i in user["expectation_ids"]
                        ],
                    }
                    for r in sorted(selected_refs)
                ],
                "qualification": QUALIFICATION,
            }
            validate_document(document)
            last = db.execute(
                "SELECT seq,sha256 FROM documents ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            seq = last["seq"] + 1 if last else 1
            body = {
                "document": document,
                "saved_engagement_revision": context["state"]["revision"],
                "basis_sha256": context["basis"],
                "command_id": p["command_id"],
                "request_sha256": digest(p),
                "previous_sha256": last["sha256"] if last else ZERO,
            }
            require(seq <= MAX_DOCUMENTS, "Assessment history limit", 409)
            db.execute("INSERT INTO documents VALUES(?,?,?)", (seq, canonical(body), digest(body)))
            self._snapshot(db)
            self._finish(actor, eid, context)
            return self._dto(body, context, detail=True)

    def snapshot(self):
        with self._db() as db:
            return self._snapshot(db)
