"""Examine retained native operating originals, without opening source runtimes.

Physical roles are literal. Source operations remain documentary local history;
these supplementary examinations never close a whole authored control clause.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from copy import deepcopy
from datetime import UTC, datetime, timedelta

from . import company_backup_use_probe as use_probe
from . import company_operating_period as period
from . import company_policy_delivery_runtime as policy
from .company_change_activity import evaluate
from .company_store import _json, _time
from .fresh_sec003_procedure import ProcedureError, require
from .source_library_audit import safe_name, typed_content

FLAT_ROLES = frozenset(
    "backup_job backup_object business_inventory credential_event failure_ticket "
    "operating_depth_definition operating_depth_followthrough operating_period_ledger "
    "policy_definition policy_document policy_operation restore_job restore_use_contract "
    "restore_use_probe restored_dataset runtime_definition service_criterion source_dataset".split()
)
PIN = frozenset("company branch system record version sha256".split())
QUALIFICATION = "FICTIONAL_DECLARED_NATIVE_OPERATIONS_NOT_ENTERPRISE_OR_PROFESSIONAL_ACCEPTANCE"
MAX_ROWS, MAX_BYTES = 8192, 64 * 1024 * 1024
OPAQUE_ROLES = frozenset({"source_dataset", "backup_object", "restored_dataset"})
UNSUPPORTED_INTAKE = "Unsupported file type; retained without preview"


def encoded(value):
    return _json(value).encode("utf-8")


def sha(value):
    return hashlib.sha256(value).hexdigest()


def exact(value, fields, label):
    require(type(value) is dict and set(value) == set(fields.split()), label)


def native_pin(value):
    require(type(value) is dict and set(value) == PIN, "Exact native operating pin required")
    require(
        all(type(value[k]) is str and value[k] for k in PIN - {"version"})
        and type(value["version"]) is int
        and value["version"] > 0
        and len(value["sha256"]) == 64
        and all(c in "0123456789abcdef" for c in value["sha256"]),
        "Typed native operating identity and SHA required",
    )
    return value


def pin(row):
    return {k: row["source"][k] for k in PIN}


def identity(value):
    return tuple(value[k] for k in ("company", "branch", "system", "record", "version"))


def partition(records):
    """Leave old dotted inputs untouched; never assign a flat record a dotted role."""
    legacy, native = [], []
    for row in records:
        system = row["source"]["system"]
        if "." in system:
            legacy.append(row)
        else:
            require(system in FLAT_ROLES, "Unknown native operating physical role")
            require(
                "logical_family" not in row and "logical_system" not in row,
                "Flat native operating originals must not carry logical aliases",
            )
            native.append(row)
    return legacy, native


class MissingOriginal(Exception):
    pass


def intake(row, raw):
    """Keep the unchanged intake decision; narrowly examine its unsupported .bin case."""
    metadata = row.get("artifact_intake")
    exact(
        metadata,
        "name mime status quarantine_reason origin sha256 bytes",
        "Exact actual artifact intake metadata required",
    )
    source = row["source"]
    provenance = source["provenance"]
    require(
        type(metadata["name"]) is str
        and metadata["name"] == provenance.get("name", provenance.get("filename"))
        and metadata["origin"] == "COLLECTED_COMPANY_SOURCE"
        and metadata["sha256"] == row["artifact_sha256"] == sha(raw)
        and type(metadata["bytes"]) is int
        and metadata["bytes"] == len(raw),
        "Actual artifact intake name, origin or bytes differ",
    )
    safe_name(metadata["name"])
    if metadata["status"] == "QUARANTINED":
        require(
            source["system"] in OPAQUE_ROLES
            and metadata["name"].endswith(".bin")
            and metadata["mime"] == provenance.get("content_type") == "application/octet-stream"
            and metadata["quarantine_reason"] == UNSUPPORTED_INTAKE,
            "Quarantined native original is outside the exact unsupported .bin examination",
        )
        return True
    require(
        metadata["status"] == "AVAILABLE" and metadata["quarantine_reason"] is None,
        "Available original with unchanged intake decision required",
    )
    return False


class Originals:
    """The caller supplies actual Engine-retained rows and the engagement cutoff."""

    def __init__(self, records, as_of):
        self.as_of = _time(as_of)
        require(0 < len(records) <= MAX_ROWS, "Bounded collected native originals required")
        self.rows, self.used = {}, {}
        first = records[0]
        scope = (first["source"]["company"], first["source"]["branch"])
        performer = (first["receipt"]["engagement_id"], first["receipt"]["principal_id"])
        total, artifacts = 0, set()
        for supplied in records:
            row = dict(supplied)
            source, receipt = row["source"], row["receipt"]
            raw = row.get("content", row.get("retained_bytes"))
            total += len(raw) if type(raw) is bytes else MAX_BYTES + 1
            require(total <= MAX_BYTES, "Bounded retained native payload exceeded")
            native_pin({k: source[k] for k in PIN})
            require(
                "." in source["system"] or source["system"] in FLAT_ROLES,
                "Unknown native operating physical role",
            )
            require(
                type(row.get("artifact_id")) is str
                and row["artifact_id"]
                and row["artifact_id"] not in artifacts
                and type(raw) is bytes
                and raw
                and (source["company"], source["branch"]) == scope
                and encoded(receipt["source"]) == encoded(source)
                and (receipt["engagement_id"], receipt["principal_id"]) == performer
                and all(
                    type(receipt[k]) is str and receipt[k]
                    for k in (
                        "engagement_id",
                        "principal_id",
                        "command_id",
                        "simulated_as_of",
                        "collected_at",
                    )
                )
                and sha(raw) == source["sha256"] == row["artifact_sha256"]
                and type(receipt["content_bytes"]) is int
                and receipt["content_bytes"] == len(raw)
                and source["event_at"] is not None
                and _time(source["event_at"])
                <= _time(source["available_at"])
                <= _time(receipt["simulated_as_of"])
                <= self.as_of
                and _time(source["imported_at"])
                <= _time(receipt["collected_at"])
                <= _time(datetime.now(UTC).isoformat()),
                "Ordinary retained native scope, bytes, receipt or clocks differ",
            )
            key = identity(source)
            artifacts.add(row["artifact_id"])
            require(key not in self.rows, "Duplicate retained exact native original")
            row["content"] = raw
            if intake(row, raw):
                row["document"], row["mime"] = None, "application/octet-stream"
            else:
                row["document"], row["mime"] = typed_content({**source, "content": raw})
                require(
                    row["mime"] == row["artifact_intake"]["mime"],
                    "Actual artifact intake MIME differs from typed original",
                )
            self.rows[key] = row

    def resolve(self, reference, *, at=None, systems=None, clocks=False):
        require(type(reference) is dict, "Typed retained native reference required")
        allowed = (
            PIN,
            PIN | {"event_at", "available_at"},
            PIN | {"event_at", "available_at", "imported_at"},
        )
        require(
            set(reference) in allowed if clocks else set(reference) == PIN,
            "Exact retained native reference fields required",
        )
        core = {k: reference[k] for k in PIN}
        native_pin(core)
        row = self.rows.get(identity(core))
        if row is None:
            raise MissingOriginal(core)
        require(encoded(pin(row)) == encoded(core), "Retained native reference SHA differs")
        require(
            systems is None or core["system"] in systems, "Wrong native operating physical role"
        )
        cutoff = self.as_of if at is None else _time(at)
        require(
            _time(row["source"]["event_at"]) <= cutoff
            and _time(row["source"]["available_at"]) <= cutoff,
            "Retained native input unavailable at operating cutoff",
        )
        for k in set(reference) - PIN:
            require(
                type(reference[k]) is str and _time(reference[k]) == _time(row["source"][k]),
                "Embedded native clock differs",
            )
        self.used[identity(core)] = row
        return row

    def object(self, reference, **kwargs):
        row = self.resolve(reference, **kwargs)
        require(type(row["document"]) is dict, "Typed retained native JSON object required")
        return row, row["document"]


def schedule(definition):
    offset = set(definition) & {"due_offset_days", "due_offset_seconds"}
    require(len(offset) == 1, "One exact native due offset required")
    key = next(iter(offset))
    cadence, value = definition["cadence_days"], definition[key]
    require(
        type(cadence) is int and 1 <= cadence <= 366 and type(value) is int and value > 0,
        "Typed native cadence required",
    )
    seconds = value * 86400 if key == "due_offset_days" else value
    require(seconds <= cadence * 86400, "Native due offset exceeds cadence")
    start = datetime.fromisoformat(_time(definition["period_start"]))
    stop = datetime.fromisoformat(_time(definition["period_end_exclusive"]))
    require(start < stop, "Native operating period required")
    slots = []
    ordinal = 0
    while start < stop:
        end = min(start + timedelta(days=cadence), stop)
        due = min(start + timedelta(seconds=seconds), end)
        for item in definition["items"]:
            expected = (
                datetime.fromisoformat(_time(item["operating_from"]))
                < due
                <= datetime.fromisoformat(_time(item["operating_to_exclusive"]))
            )
            slots.append(
                {
                    "slot_id": item["id"] + ":" + str(ordinal),
                    "item_id": item["id"],
                    "kind": item["kind"],
                    "window_start": start.isoformat(timespec="microseconds"),
                    "window_end_exclusive": end.isoformat(timespec="microseconds"),
                    "due_at": due.isoformat(timespec="microseconds"),
                    "expected": expected,
                    "exclusion": None if expected else "OUTSIDE_EXACT_NATIVE_OPERATING_WINDOW",
                }
            )
        require(len(slots) <= 512, "Bounded native operating schedule required")
        ordinal += 1
        start = end
    return slots


def declaration(history, reference):
    row, body = history.object(reference, systems={"operating_depth_definition"})
    offsets = set(body) & {"due_offset_days", "due_offset_seconds"}
    require(len(offsets) == 1, "Exact declared native due offset required")
    offset = next(iter(offsets))
    exact(
        body,
        "schema runtime_id company branch declared_at recorded_at period_start "
        "period_end_exclusive inventory_scope business_inventory_ref cadence_days "
        + offset
        + " items exclusions retained_period_refs local_basis",
        "Exact native operating declaration fields required",
    )
    require(
        body["schema"] == "SH_COMPANY_NATIVE_OPERATING_DEPTH_DECLARATION_V1"
        and row["source"]["record"] == body["runtime_id"]
        and (body["company"], body["branch"]) == (row["source"]["company"], row["source"]["branch"])
        and body["inventory_scope"]
        == "EXPLICIT_COMPANY_BUSINESS_INVENTORY_NOT_SELECTED_AUDIT_ARTIFACTS"
        and _time(body["declared_at"])
        <= _time(body["period_start"])
        < _time(body["period_end_exclusive"])
        and _time(body["declared_at"])
        <= _time(body["recorded_at"])
        == _time(row["source"]["event_at"]),
        "Native declaration identity, scope or chronology differs",
    )
    _, inventory = history.object(
        body["business_inventory_ref"], at=body["declared_at"], systems={"business_inventory"}
    )
    calendar = {
        k: body[k]
        for k in (
            "declared_at",
            "period_start",
            "period_end_exclusive",
            "cadence_days",
            offset,
            "items",
            "exclusions",
        )
    }
    require(
        encoded(inventory.get("operating_depth_calendar")) == encoded(calendar),
        "Declaration differs from independent native calendar",
    )
    systems = inventory.get("systems")
    require(
        type(systems) is list
        and 1 <= len(systems) <= 128
        and all(type(s) is dict and type(s.get("system")) is str for s in systems),
        "Bounded independent native business systems required",
    )
    names = [s["system"] for s in systems]
    require(len(set(names)) == len(names), "Ambiguous native inventory systems")
    require(
        type(body["items"]) is list
        and 1 <= len(body["items"]) <= 128
        and type(body["exclusions"]) is list
        and len(body["exclusions"]) <= 128,
        "Bounded exact native calendar items required",
    )
    item_ids, covered = set(), set()
    for item in body["items"]:
        exact(
            item,
            "id system_id kind operating_from operating_to_exclusive commissioning_ref",
            "Exact native operating item required",
        )
        require(
            type(item["id"]) is str
            and item["id"] not in item_ids
            and item["system_id"] in names
            and item["kind"] in {"IAM", "POLICY", "RETRY", "RESTORE"}
            and _time(item["operating_from"]) < _time(item["operating_to_exclusive"]),
            "Native operating item identity/window differs",
        )
        item_ids.add(item["id"])
        covered.add(item["system_id"])
        if item["kind"] == "RESTORE":
            release, released = history.object(
                item["commissioning_ref"], systems={"site_release", "transition.site_release"}
            )
            require(
                released.get("fictional_in_universe_operating_release") is True
                and released.get("status")
                in {
                    "OPERATING_PRIMARY_SIMULATED",
                    "OPERATING_RECOVERY_SIMULATED",
                    "OPERATING_RECOVERY_WITH_OPEN_EXCEPTION_SIMULATED",
                }
                and _time(release["source"]["event_at"]) == _time(item["operating_from"]),
                "Exact commissioned native operating release required",
            )
        else:
            require(item["commissioning_ref"] is None, "Unexpected native commissioning role")
    excluded = set()
    for exclusion in body["exclusions"]:
        exact(exclusion, "system_id reason source_ref", "Exact native exclusion required")
        require(
            exclusion["system_id"] in names
            and exclusion["system_id"] not in excluded
            and type(exclusion["reason"]) is str
            and len(exclusion["reason"]) >= 10,
            "Native excluded scope differs",
        )
        # Supporting exclusions intentionally have no invented physical-role restriction.
        history.resolve(exclusion["source_ref"], at=body["declared_at"])
        excluded.add(exclusion["system_id"])
    require(
        not covered & excluded and covered | excluded == set(names),
        "Independent native business scope is not fully accounted for",
    )
    require(
        type(body["retained_period_refs"]) is list and len(body["retained_period_refs"]) <= 64,
        "Bounded retained period originals required",
    )
    seen = set()
    for ref in body["retained_period_refs"]:
        original, document = history.object(ref)
        require(
            document.get("schema") == "SH_COMPANY_PERSON_ACCESS_RECORD_V1"
            and identity(ref) not in seen,
            "Exact original retained period join required",
        )
        seen.add(identity(ref))
    return row, body, inventory, schedule(body)


def policy_history(history, runtime_sha256, at):
    matches = [
        r
        for r in history.rows.values()
        if r["source"]["system"] == "policy_definition" and r["source"]["sha256"] == runtime_sha256
    ]
    if not matches:
        raise MissingOriginal({"policy_definition_sha256": runtime_sha256})
    require(len(matches) == 1, "Ambiguous retained policy definition")
    row, cfg = history.object(pin(matches[0]), systems={"policy_definition"})
    fields = set(
        (
            "format plan documents code_pins imported_at organization_source_sha256 "
            "qualification inventory_scope"
        ).split()
    )
    require(
        set(cfg) in (fields, fields | {"document_admission"}),
        "Exact retained native policy definition fields required",
    )
    require(
        cfg.get("format") == "LOCAL_POLICY_DELIVERY_RUNTIME_V1"
        and cfg.get("qualification") == policy.QUALIFICATION
        and row["source"]["record"] == cfg["plan"]["runtime_id"],
        "Exact retained policy definition identity required",
    )
    require(
        encoded(policy._plan(deepcopy(cfg["plan"]))) == encoded(cfg["plan"])
        and (cfg["plan"]["company"], cfg["plan"]["branch"])
        == (row["source"]["company"], row["source"]["branch"])
        and cfg["inventory_scope"] == "ONLY_DECLARED_PERSONA_MAILBOXES_NOT_WORKFORCE_COMPLETENESS"
        and cfg["imported_at"] == row["source"]["imported_at"]
        and type(cfg["documents"]) is list
        and 1 <= len(cfg["documents"]) <= 4
        and len({d["id"] for d in cfg["documents"]}) == len(cfg["documents"]),
        "Native policy plan, scope, import or document inventory differs",
    )
    documents = {}
    for document in cfg["documents"]:
        ref = policy._doc(cfg, document["id"])
        retained = history.resolve(ref, at=cfg["plan"]["declared_at"], systems={"policy_document"})
        require(
            len(retained["content"]) == document["byte_count"],
            "Retained policy document byte count differs",
        )
        if "source_pin" in document:
            exact(
                document,
                "id sha256 byte_count source_root source_pin source_header authority",
                "Exact retained native policy-document transport required",
            )
            require(
                cfg.get("document_admission") == "EXPLICIT_NATIVE_POLICY_DOCUMENT_BYTES_V1"
                and document["authority"] == "EXACT_NATIVE_DOCUMENT_BYTES_NOT_NEW_POLICY_APPROVAL",
                "Native document transport authority differs",
            )
            original = history.resolve(
                document["source_pin"],
                at=cfg["plan"]["declared_at"],
                systems={"policy_document", "supplementalops.policy_document"},
            )
            require(
                original["content"] == retained["content"],
                "Retained native policy transport differs from original bytes",
            )
            header = document["source_header"]
            exact(
                header,
                "company branch system record version sha256 event_at available_at "
                "imported_at origin provenance",
                "Exact original native policy header required",
            )
            require(
                encoded({k: v for k, v in header.items() if k != "provenance"})
                == encoded({k: original["source"][k] for k in header if k != "provenance"})
                and type(header["provenance"]) is str
                and encoded(json.loads(header["provenance"]))
                == encoded(original["source"]["provenance"]),
                "Native document original header differs from retained custody",
            )
        else:
            exact(
                document,
                "id path sha256 source_metadata_lines git_blob byte_count authority",
                "Exact retained repository policy-document declaration required",
            )
            require(
                document["authority"] == "LITERAL_SOURCE_METADATA_NOT_NEW_APPROVAL"
                and type(document["source_metadata_lines"]) is list
                and 1 <= len(document["source_metadata_lines"]) <= 8
                and all(
                    type(line) is str and line in retained["content"].decode("utf-8").splitlines()
                    for line in document["source_metadata_lines"]
                ),
                "Literal held policy document metadata differs",
            )
        documents[document["id"]] = retained
    rows = [
        r
        for r in history.rows.values()
        if r["source"]["system"] == "policy_operation"
        and type(r["document"]) is dict
        and r["document"].get("runtime_sha256") == runtime_sha256
    ]
    rows.sort(key=lambda r: r["document"]["revision"])
    current, prefix = policy._initial(cfg), policy._initial(cfg)
    prefix_rows = []
    for number, operation in enumerate(rows, 1):
        native, body = history.object(pin(operation), systems={"policy_operation"})
        exact(
            body,
            "revision command_id request request_sha256 prior_state_sha256 state_sha256 "
            "event_at imported_at observation file_fact runtime_sha256 qualification",
            "Exact retained native policy operation required",
        )
        require(
            type(body["revision"]) is int
            and body["revision"] == number
            and native["source"]["record"] == f"OP-{number}"
            and native["source"]["version"] == 1
            and body["qualification"] == policy.QUALIFICATION
            and body["request_sha256"] == sha(encoded(body["request"]))
            and body["prior_state_sha256"] == sha(encoded(current))
            and _time(body["event_at"]) == _time(native["source"]["event_at"])
            and _time(body["imported_at"]) == _time(native["source"]["imported_at"]),
            "Retained policy operation chain/header differs",
        )
        after, observed = policy._apply(
            cfg,
            current,
            body["request"],
            number - 1,
            body["command_id"],
            body["imported_at"],
            body["file_fact"],
        )
        require(
            body["state_sha256"] == sha(encoded(after))
            and encoded(body["observation"]) == encoded(observed),
            "Retained policy transition or observation differs",
        )
        if body["request"]["operation"] == "DELIVER":
            ref = body["request"]["parameters"]["document_pin"]
            document = history.resolve(ref, at=body["event_at"], systems={"policy_document"})
            require(
                body["file_fact"]["byte_count"] == len(document["content"]),
                "Recorded mailbox byte count differs from retained document",
            )
        current = after
        if _time(body["event_at"]) <= _time(at):
            require(
                _time(native["source"]["available_at"]) <= _time(at),
                "Policy operation unavailable at historical cutoff",
            )
            prefix, prefix_rows = deepcopy(after), prefix_rows + [native]
    return cfg, policy._report(cfg, prefix, _time(at)), prefix_rows, prefix


def policy_binding(history, row, body, definition, inventory):
    observed, at = body["observation"], body["recorded_at"]
    exact(
        observed,
        "performed_by runtime_root runtime_sha256 native_refs recorded_policy_report "
        "policy_state_basis status human_acknowledgment "
        "all_recipients_delivered all_recipients_read_return",
        "Exact retained policy binding fields required",
    )
    cfg, report, operations, state = policy_history(history, observed["runtime_sha256"], at)
    item = next(i for i in definition["items"] if i["id"] == body["slot"]["item_id"])
    system = next(s for s in inventory["systems"] if s["system"] == item["system_id"])
    require(
        system.get("recipients") == cfg["plan"]["recipients"]
        and system.get("document_sha256") == report["selected_document_pin"]["sha256"]
        and cfg["plan"]["due_at"] == body["slot"]["due_at"]
        and observed["performed_by"] == cfg["plan"]["owner_id"]
        and encoded(report) == encoded(observed["recorded_policy_report"])
        and observed["status"] == "EXACT_LOCAL_DOCUMENT_DELIVERY_READ_RECEIPTS_BOUND"
        and observed["human_acknowledgment"] == "NOT_ESTABLISHED"
        and observed["policy_state_basis"]
        == "FRESH_VERIFIED_NATIVE_OPERATION_PREFIX_AT_EXACT_CUTOFF",
        "Policy binding differs from retained native recipient/document/due facts",
    )
    refs = [report["selected_document_pin"]] + [
        pin(r)
        for r in operations
        if r["document"]["request"]["operation"] in {"DELIVER", "READ_RETURN"}
    ]
    require(
        encoded(refs) == encoded(observed["native_refs"]),
        "Policy binding omitted/substituted retained native operation originals",
    )
    delivered = all(
        r["delivery_status"] == "DELIVERED_CURRENT_VERSION" for r in report["recipients"]
    )
    read = all(r["read_return_current_delivery"] for r in report["recipients"])
    require(
        type(observed["all_recipients_delivered"]) is bool
        and type(observed["all_recipients_read_return"]) is bool
        and observed["all_recipients_delivered"] == delivered
        and observed["all_recipients_read_return"] == read,
        "Recorded native policy coverage differs",
    )
    return {
        "rederived_native_policy_report": report,
        "historical_policy_state_sha256": sha(encoded(state)),
        "all_declared_recipients_delivered": delivered,
        "all_declared_read_returns": read,
        "complete_current_runtime_or_mailbox_inventory_established": False,
        "mailbox_files_reopened_by_audit": False,
        "human_acknowledgment": "NOT_ESTABLISHED",
    }, any(r["delivery_status"] == "MISSING_DUE" or r["late"] for r in report["recipients"])


def iam_followup(history, row, body, definition, inventory):
    del inventory
    obs, at = body["observation"], body["recorded_at"]
    exact(
        obs,
        "population_pin decisions_pin original_accounts before_states after_states results "
        "missing_subject_ids performed_by verified_by status "
        "all_rights_authorized old_population_or_review_replaced",
        "Exact retained local removal observation required",
    )
    require(
        all(type(obs[k]) is str and obs[k] for k in ("performed_by", "verified_by"))
        and obs["performed_by"] != obs["verified_by"]
        and obs["old_population_or_review_replaced"] is False
        and obs["all_rights_authorized"] == "NOT_ESTABLISHED_BY_REMOVAL_ONLY",
        "Removal-only scope or recorded actors differ",
    )
    for ref in (obs["population_pin"], obs["decisions_pin"]):
        require(
            encoded(ref) in {encoded(p) for p in definition["retained_period_refs"]},
            "Quarter originals outside exact declared source scope",
        )
    pop_row, pop = history.object(
        obs["population_pin"],
        at=at,
        systems={"person-access-history.periodic_review_population", "periodic_review_population"},
    )
    dec_row, decision = history.object(
        obs["decisions_pin"],
        at=at,
        systems={"person-access-history.periodic_review_decisions", "periodic_review_decisions"},
    )
    require(
        pop["schema"] == decision["schema"] == "SH_COMPANY_PERSON_ACCESS_RECORD_V1"
        and pop_row["source"]["record"] == dec_row["source"]["record"]
        and pop.get("membership_sha256")
        == decision.get("population_sha256")
        == sha(encoded(pop["members"]))
        and pop["exported_by"] == obs["performed_by"]
        and decision["reviewed_by"] == obs["verified_by"],
        "Exact native quarterly membership, actors or digest differs",
    )
    target = history.resolve(decision["population"], at=dec_row["source"]["event_at"], clocks=True)
    require(
        encoded(pin(target)) == encoded(obs["population_pin"]), "Decision names another population"
    )
    cutoff = _time(pop["period_end_exclusive"])
    quarter = pop_row["source"]["record"]
    require(
        re.fullmatch(r"2027-Q[1-4]", quarter) is not None,
        "Exact retained 2027 quarterly review record required",
    )
    month = (int(quarter[-1]) - 1) * 3 + 1
    start = datetime(2027, month, 1, tzinfo=UTC)
    end = (
        datetime(2028, 1, 1, tzinfo=UTC)
        if month == 10
        else datetime(2027, month + 3, 1, tzinfo=UTC)
    )
    require(
        _time(pop["period_start"]) == _time(start.isoformat()) and cutoff == _time(end.isoformat()),
        "Exact full-quarter native window required",
    )
    require(
        cutoff
        <= _time(pop_row["source"]["event_at"])
        <= _time(dec_row["source"]["event_at"])
        <= _time(at),
        "Review/late-followthrough chronology differs",
    )
    require(
        type(pop["members"]) is list
        and len(pop["members"]) <= 512
        and type(decision["decisions"]) is list,
        "Bounded native quarterly members required",
    )
    members = {m["subject_id"]: m for m in pop["members"]}
    decisions = {d["subject_id"]: d for d in decision["decisions"]}
    require(
        len(members) == len(pop["members"])
        and len(decisions) == len(decision["decisions"])
        and set(members) == set(decisions),
        "Ambiguous quarterly native subject decision",
    )
    original, originals = {}, {}
    for subject, member in members.items():
        require(type(member["accounts"]) is list, "Typed native account vector required")
        for account in member["accounts"]:
            exact(account, "source state", "Exact native member account required")
            target, native = history.object(
                account["source"],
                at=cutoff,
                clocks=True,
                systems={
                    prefix + role
                    for prefix in ("", "person-access-history.")
                    for role in (
                        "account_directory",
                        "account_application",
                        "account_local_account",
                        "account_remote_access",
                        "account_api_token",
                        "account_application_session",
                        "account_legacy_application",
                    )
                },
            )
            state = native.get("state")
            exact(
                state,
                "account_id subject_id channel rights active starts ends "
                "credential_epoch review_anchor",
                "Exact retained native account state required",
            )
            require(
                encoded(state) == encoded(account["state"])
                and state["subject_id"] == subject
                and state["account_id"] not in original
                and state["active"] is True
                and type(state["credential_epoch"]) is int
                and state["credential_epoch"] > 0
                and _time(target["source"]["available_at"]) < cutoff
                and _time(state["starts"]) < cutoff <= _time(state["ends"])
                and type(state["rights"]) is list
                and len(state["rights"]) <= 32
                and all(type(v) is str and v for v in state["rights"])
                and len(set(state["rights"])) == len(state["rights"]),
                "Original quarterly account state/identity differs",
            )
            original[state["account_id"]] = state
            originals[state["account_id"]] = pin(target)
    require(
        encoded(originals) == encoded(obs["original_accounts"])
        and type(obs["before_states"]) is dict
        and type(obs["after_states"]) is dict
        and set(obs["before_states"]) == set(obs["after_states"]) == set(original),
        "Native followthrough replaced or omitted original accounts",
    )
    prior = [
        r
        for r in history.rows.values()
        if r["source"]["system"] == "operating_depth_followthrough"
        and r["source"]["record"] == row["source"]["record"]
        and r["source"]["version"] == row["source"]["version"] - 1
    ]
    if row["source"]["version"] > 1:
        if not prior:
            raise MissingOriginal({"previous_followthrough_version": row["source"]["version"] - 1})
        require(len(prior) == 1, "Ambiguous prior native followthrough")
        previous, document = history.object(
            pin(prior[0]), at=at, systems={"operating_depth_followthrough"}
        )
        require(
            encoded(document["declaration_pin"]) == encoded(body["declaration_pin"])
            and document["kind"] == "IAM"
            and encoded(document["observation"]["population_pin"]) == encoded(obs["population_pin"])
            and encoded(document["observation"]["decisions_pin"]) == encoded(obs["decisions_pin"])
            and encoded(document["observation"]["original_accounts"]) == encoded(originals)
            and encoded(document["observation"]["after_states"]) == encoded(obs["before_states"]),
            "Native resume changed the preceding removal state",
        )
    else:
        require(
            encoded(original) == encoded(obs["before_states"]),
            "Initial local followthrough substituted quarterly before-state",
        )
    results = {r["account_id"]: r for r in obs["results"]}
    require(
        len(results) == len(obs["results"]) and set(results) == set(original),
        "Complete exact local removal/retest result vector required",
    )
    unresolved, removed = False, 0
    for account, native in original.items():
        before, after = obs["before_states"][account], obs["after_states"][account]
        unchanged = {k: v for k, v in native.items() if k != "rights"}
        require(
            encoded({k: v for k, v in before.items() if k != "rights"}) == encoded(unchanged)
            and encoded({k: v for k, v in after.items() if k != "rights"}) == encoded(unchanged),
            "Followthrough changed account identity/lifetime/channel",
        )
        d = decisions[native["subject_id"]]
        require(
            all(
                type(v) is list
                and len(v) <= 32
                and all(type(r) is str and r for r in v)
                and len(set(v)) == len(v)
                for v in (
                    before["rights"],
                    after["rights"],
                    d["remove_rights"],
                    d["observed_rights"],
                )
            ),
            "Typed distinct native permission names required",
        )
        observed_rights = sorted(
            {
                right
                for a in members[native["subject_id"]]["accounts"]
                for right in a["state"]["rights"]
            }
        )
        require(
            d["observed_rights"] == observed_rights
            and type(d["remove_rights"]) is list
            and set(d["remove_rights"]) <= set(observed_rights)
            and set(before["rights"]) <= set(native["rights"])
            and set(native["rights"]) - set(before["rights"]) <= set(d["remove_rights"]),
            "Unrequested or broader native removal",
        )
        requested = sorted(set(d["remove_rights"]) & set(before["rights"]))
        execution, verification = results[account]["execution"], results[account]["verification"]
        remaining = execution["unresolved_permissions"]
        require(
            type(remaining) is list
            and len(set(remaining)) == len(remaining)
            and set(remaining) <= set(requested),
            "Unresolved native permission vector differs",
        )
        # The real local executor applies the entire exact set only when every
        # permission resolves. One unresolved permission leaves all rights intact.
        expected = sorted(before["rights"] if remaining else set(before["rights"]) - set(requested))
        require(
            after["rights"] == expected
            and verification["observed_rights"] == expected
            and verification["expected_rights"] == sorted(set(before["rights"]) - set(requested))
            and verification["verified_by"] == obs["verified_by"]
            and verification["removed_permission_probes"]
            == {r: "ALLOW" if r in expected else "DENY" for r in requested},
            "Recorded native removal/retest does not match actual local right sets",
        )
        if requested:
            exact(
                execution,
                "before_rights after_rights removed_rights unresolved_permissions status",
                "Exact executed local removal result required",
            )
            require(
                execution["before_rights"] == sorted(before["rights"])
                and execution["after_rights"] == expected
                and execution["removed_rights"] == sorted(set(before["rights"]) - set(expected))
                and execution["status"]
                == ("UNRESOLVED_PERMISSION_MAPPING" if remaining else "APPLIED_OR_ALREADY_ABSENT"),
                "Recorded removal execution differs from all-or-none resolver",
            )
            require(
                verification.get("verification_basis")
                == "LOCAL_RIGHT_SET_NOT_CREDENTIAL_OR_LIFETIME_PROBE",
                "Native removal verification basis differs",
            )
        else:
            exact(execution, "status unresolved_permissions", "Exact no-removal result required")
            require(
                execution["status"] == "NO_REMAINING_REQUESTED_REMOVAL" and not remaining,
                "No-removal result differs",
            )
        unresolved = unresolved or bool(remaining)
        removed += len(set(before["rights"]) - set(expected))
    require(
        encoded(obs["missing_subject_ids"]) == encoded(decision["missing_subject_ids"]),
        "Original missing subjects were silently cured",
    )
    unresolved = unresolved or bool(obs["missing_subject_ids"])
    expected_status = (
        "OPEN_UNRESOLVED_SCOPE_OR_PERMISSION" if unresolved else "REQUESTED_LOCAL_REMOVALS_VERIFIED"
    )
    require(obs["status"] == expected_status, "Native local followthrough status differs")
    return {
        "quarter_original": pop_row["source"]["record"],
        "account_count": len(original),
        "requested_permissions_removed": removed,
        "missing_subject_ids": obs["missing_subject_ids"],
        "rederived_source_status": expected_status,
        "performed_at": at,
        "original_period_end_exclusive": cutoff,
        "source_review_versions_replaced": False,
        "whole_period_effectiveness_established": False,
        "credential_session_lifetime_or_all_rights_authorization_retested": False,
    }, unresolved


def restore_return(history, row, body, definition, inventory):
    del inventory
    obs, at = body["observation"], body["recorded_at"]
    if obs.get("status") == "FAIL_LOCAL_RESTORE_NO_RETURN":
        exact(
            obs,
            "performed_by job_pin source_attempted_at error_code returned_bytes status "
            "completed_copy_or_read_or_BIA_claim",
            "Exact native failed-return binding required",
        )
        job_row, job = history.object(obs["job_pin"], at=at, systems={"restore_job"})
        require(
            job["operation"] == "RESTORE"
            and job["status"] == "FAILED"
            and job["object_pin"] is None
            and type(job["copied_bytes"]) is int
            and job["copied_bytes"] == 0
            and job["actual_elapsed_seconds"] is None
            and type(job["error_code"]) is str
            and job["error_code"]
            and obs["error_code"] == job["error_code"]
            and obs["performed_by"] == job["performed_by"]
            and type(obs["returned_bytes"]) is int
            and obs["returned_bytes"] == 0
            and obs["completed_copy_or_read_or_BIA_claim"] is False
            and _time(obs["source_attempted_at"])
            == _time(job["business_attempted_at"])
            == _time(job_row["source"]["event_at"])
            <= _time(at),
            "Failed restore differs from exact retained zero-return attempt",
        )
        return {
            "rederived_source_status": "FAIL_LOCAL_RESTORE_NO_RETURN",
            "source_attempted_at": obs["source_attempted_at"],
            "error_code": job["error_code"],
            "missing_occurrence": False,
            "returned_bytes": 0,
            "completed_copy_or_read_or_BIA_claim": False,
        }, True
    exact(
        obs,
        "performed_by recorded_review_contact criterion_pin native_refs "
        "copy_sha256 read_status actual "
        "actual_elapsed_seconds checkpoint_age_seconds parsed_record_count status review_performed "
        "enterprise_BIA_or_application_acceptance",
        "Exact native local service-return binding required",
    )
    criterion_row, criterion = history.object(
        obs["criterion_pin"], at=at, systems={"service_criterion"}
    )
    exact(
        criterion,
        "schema service_id dataset_id author_id reviewer_id approved_at max_age_seconds "
        "max_restore_seconds min_record_count qualification",
        "Exact local service criterion required",
    )
    item = next(i for i in definition["items"] if i["id"] == body["slot"]["item_id"])
    require(
        criterion["schema"] == "SH_LOCAL_SERVICE_RETURN_CRITERION_V1"
        and criterion["qualification"] == "LOCAL_SIMULATED_SERVICE_CRITERION_NOT_ENTERPRISE_BIA"
        and criterion["service_id"] == item["system_id"]
        and criterion["author_id"]
        == obs["performed_by"]
        != criterion["reviewer_id"]
        == obs["recorded_review_contact"]
        and _time(criterion["approved_at"]) == _time(criterion_row["source"]["event_at"])
        and all(
            type(criterion[k]) is int and 1 <= criterion[k] <= 31536000
            for k in ("max_age_seconds", "max_restore_seconds", "min_record_count")
        ),
        "Native criterion role, service, actor, clock or bound differs",
    )
    refs = obs["native_refs"]
    require(
        type(refs) is list and len(refs) == 5, "Five exact restore-use native originals required"
    )
    probe_row, probe = history.object(refs[0], at=at, systems={"restore_use_probe"})
    exact(
        probe,
        "contract_pin restore_job_pin restored_dataset_pin source_pin "
        "copy_sha256 reader read_status "
        "actual status performed_by recorded_review_contact review_performed qualification "
        "not_application_or_data_usability_acceptance",
        "Exact native parsed-use probe required",
    )
    expected_refs = [
        refs[0],
        probe["contract_pin"],
        probe["restore_job_pin"],
        probe["restored_dataset_pin"],
        probe["source_pin"],
    ]
    require(encoded(refs) == encoded(expected_refs), "Restore binding substituted native originals")
    contract_row, contract = history.object(refs[1], at=at, systems={"restore_use_contract"})
    job_row, job = history.object(refs[2], at=at, systems={"restore_job"})
    restored = history.resolve(refs[3], at=at, systems={"restored_dataset"})
    source = history.resolve(refs[4], at=job_row["source"]["event_at"], systems={"source_dataset"})
    exact(
        contract,
        "occurrence_id dataset_id source_pin reader rationale authored_by recorded_review_contact "
        "review_performed authority qualification",
        "Exact native prospective use contract required",
    )
    require(
        contract["qualification"] == probe["qualification"] == use_probe.QUALIFICATION
        and contract["authority"]
        == "TRUSTED_LOCAL_OPERATOR_AND_DISTINCT_CONTACT_NOT_CORPORATE_APPROVAL"
        and contract["review_performed"]
        is probe["review_performed"]
        is obs["review_performed"]
        is False
        and probe["not_application_or_data_usability_acceptance"] is True
        and obs["enterprise_BIA_or_application_acceptance"] is False
        and contract["authored_by"]
        == probe["performed_by"]
        == job["performed_by"]
        == obs["performed_by"]
        and contract["recorded_review_contact"]
        == probe["recorded_review_contact"]
        == criterion["reviewer_id"]
        and criterion["dataset_id"]
        == contract["dataset_id"]
        == job["dataset_id"]
        == source["source"]["record"]
        and contract["occurrence_id"]
        == job["occurrence_id"]
        == job_row["source"]["record"]
        == restored["source"]["record"]
        == probe_row["source"]["record"]
        == contract_row["source"]["record"]
        and job["operation"] == "RESTORE"
        and job["status"] == "COMPLETED"
        and encoded(job["object_pin"]) == encoded(refs[3])
        and encoded(contract["source_pin"])
        == encoded(job["comparison_source_pin"])
        == encoded(refs[4])
        and _time(criterion_row["source"]["available_at"])
        <= _time(contract_row["source"]["event_at"])
        < _time(job_row["source"]["event_at"])
        < _time(probe_row["source"]["event_at"])
        <= _time(at)
        and restored["source"]["event_at"] == job_row["source"]["event_at"]
        and _time(job["business_attempted_at"]) == _time(job_row["source"]["event_at"]),
        "Restore-use prospective chronology, identity or local authority differs",
    )
    # Reperform only on retained bytes. Stored copy_path/runtime paths are never followed.
    reader = use_probe._reader(contract["reader"])
    require(encoded(reader) == encoded(probe["reader"]), "Probe changed prospective parsed reader")
    raw = restored["content"]
    require(
        sha(raw) == probe["copy_sha256"] == obs["copy_sha256"]
        and type(job["copied_bytes"]) is int
        and job["copied_bytes"] == len(raw),
        "Retained restored-byte SHA or count differs",
    )
    backup_object = history.resolve(
        job["source_pin"], at=job["business_attempted_at"], systems={"backup_object"}
    )
    require(
        raw == backup_object["content"]
        and job["byte_copy_matches_selected_backup"] is True
        and job["comparison_bytes_equal"] is (raw == source["content"]),
        "Recorded restore-copy equality differs from retained originals",
    )
    jobs = [
        r
        for r in history.rows.values()
        if r["source"]["system"] == "backup_job"
        and type(r["document"]) is dict
        and encoded(r["document"].get("object_pin")) == encoded(pin(backup_object))
    ]
    if not jobs:
        raise MissingOriginal({"producing_backup_job_for": pin(backup_object)})
    require(len(jobs) == 1, "Ambiguous retained completed backup job")
    backup_row, backed = history.object(
        pin(jobs[0]), at=job["business_attempted_at"], systems={"backup_job"}
    )
    captured = history.resolve(
        backed["source_pin"], at=backup_row["source"]["event_at"], systems={"source_dataset"}
    )
    require(
        backed["status"] == "COMPLETED"
        and backed["operation"] == "BACKUP"
        and captured["content"] == backup_object["content"]
        and backup_object["source"]["event_at"] == backup_row["source"]["event_at"],
        "Backup checkpoint lineage differs from retained bytes",
    )
    age, elapsed = job["checkpoint_age_seconds"], job["actual_elapsed_seconds"]
    require(
        all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in (age, elapsed))
        and age
        == (
            datetime.fromisoformat(_time(job["business_attempted_at"]))
            - datetime.fromisoformat(_time(captured["source"]["event_at"]))
        ).total_seconds(),
        "Native checkpoint age or recorded measured duration differs",
    )
    read_status, actual = use_probe._actual(raw, reader)
    parsed = json.loads(raw)
    capacity = (
        len(parsed["records"])
        if type(parsed) is dict and type(parsed.get("records")) is list
        else 0
    )
    parsed_pass = read_status == "READ" and encoded(actual) == encoded(reader["expected"])
    require(
        read_status == probe["read_status"] == obs["read_status"]
        and encoded(actual) == encoded(probe["actual"]) == encoded(obs["actual"])
        and probe["status"]
        == ("PASS_LOCAL_PARSED_READ" if parsed_pass else "FAIL_LOCAL_PARSED_READ")
        and encoded(age) == encoded(obs["checkpoint_age_seconds"])
        and encoded(elapsed) == encoded(obs["actual_elapsed_seconds"])
        and type(obs["parsed_record_count"]) is int
        and obs["parsed_record_count"] == capacity,
        "Parsed restore-use/capacity/duration observation differs",
    )
    passed = (
        parsed_pass
        and age <= criterion["max_age_seconds"]
        and elapsed <= criterion["max_restore_seconds"]
        and capacity >= criterion["min_record_count"]
    )
    status = (
        "PASS_LOCAL_SERVICE_RETURN_CRITERION" if passed else "FAIL_LOCAL_SERVICE_RETURN_CRITERION"
    )
    require(
        obs["status"] == status, "Recorded local service-return status contradicts retained facts"
    )
    return {
        "rederived_source_status": status,
        "parsed_record_count": capacity,
        "min_record_count": criterion["min_record_count"],
        "read_status": read_status,
        "actual": actual,
        "checkpoint_age_seconds": age,
        "recorded_copy_elapsed_seconds": elapsed,
        "duration_remeasured_by_auditor": False,
        "copy_path_opened_by_auditor": False,
        "review_performed": False,
        "enterprise_BIA_or_application_acceptance": False,
    }, not passed


def retry_probe(history, row, body, definition, inventory):
    del row, definition, inventory
    obs, at = body["observation"], body["recorded_at"]
    exact(
        obs,
        "configuration_pin build_pin original_test_pin performed_by executed_scope calculation "
        "status security_privacy_pipeline_tests corrected_originals_replaced",
        "Exact native retry observation required",
    )
    config_row, config = history.object(
        obs["configuration_pin"], at=at, systems={"change-history.configurations"}
    )
    build_row, build = history.object(obs["build_pin"], at=at, systems={"change-history.builds"})
    test_row, test = history.object(
        obs["original_test_pin"], at=at, systems={"change-history.tests"}
    )
    require(
        config["configuration_sha256"] == sha(encoded(config["configuration"]))
        and encoded(build["package"]["configuration"]) == encoded(config["configuration"])
        and build["package_sha256"] == sha(encoded(build["package"])),
        "Retry native config/build digest differs",
    )
    for value, target, dependent in (
        (build["source"], config_row, build_row),
        (test["artifact"], build_row, test_row),
    ):
        fields = {"system_id", "record_id", "version", "sha256", "available_at"}
        require(
            type(value) is dict
            and set(value) in (fields, fields | {"company_id", "branch_id", "event_at"})
            and type(value["version"]) is int
            and value["version"] == target["source"]["version"]
            and value["record_id"] == target["source"]["record"]
            and value["sha256"] == target["source"]["sha256"]
            and value["system_id"]
            in {
                target["source"]["system"],
                target["source"]["system"].removeprefix("change-history."),
            }
            and _time(value["available_at"])
            == _time(target["source"]["available_at"])
            <= _time(dependent["source"]["event_at"]),
            "Exact retained retry dependency differs",
        )
        if set(value) != fields:
            require(
                value["system_id"] == target["source"]["system"]
                and value["company_id"] == target["source"]["company"]
                and value["branch_id"] == target["source"]["branch"]
                and _time(value["event_at"]) == _time(target["source"]["event_at"]),
                "Native retry source scope or clock differs",
            )
    result = evaluate(config["configuration"])
    status = (
        "PASS_LOCAL_RETRY_CRITERION"
        if result["within_local_limit"]
        else "FAIL_LOCAL_RETRY_CRITERION"
    )
    require(
        encoded(obs["calculation"]) == encoded(result)
        and obs["status"] == status
        and obs["executed_scope"] == "LOCAL_POSITIVE_INTEGER_SCHEMA_AND_COMBINED_RETRY_LIMIT"
        and obs["security_privacy_pipeline_tests"] == "NOT_EXECUTED_BY_THIS_MODEL"
        and obs["corrected_originals_replaced"] is False,
        "Retained local retry calculation/scope differs",
    )
    return {
        "recalculation": result,
        "rederived_source_status": status,
        "security_privacy_pipeline_tests": "NOT_EXECUTED_BY_THIS_MODEL",
        "corrected_originals_replaced": False,
    }, not result["within_local_limit"]


def examine(records, *, as_of):
    """Pure supplementary facts; missing selected originals never become local success."""
    history = Originals(records, as_of)
    outputs = []
    for candidate in history.rows.values():
        if candidate["source"]["system"] != "operating_depth_followthrough":
            continue
        history.used = {}
        try:
            row, body = history.object(pin(candidate), systems={"operating_depth_followthrough"})
            exact(
                body,
                "schema kind declaration_pin slot recorded_at observation "
                "qualification professional_acceptance",
                "Exact retained operating observation required",
            )
            require(
                body["schema"] == "SH_NATIVE_OPERATING_DEPTH_OBSERVATION_V1"
                and body["qualification"] == QUALIFICATION
                and body["professional_acceptance"] == "NOT_ASSERTED"
                and body["kind"] in {"IAM", "POLICY", "RESTORE", "RETRY"}
                and _time(body["recorded_at"]) == _time(row["source"]["event_at"]),
                "Native observation schema, kind or clock differs",
            )
            _, definition, inventory, slots = declaration(history, body["declaration_pin"])
            selected = [s for s in slots if encoded(s) == encoded(body["slot"])]
            item = next(i for i in definition["items"] if i["id"] == body["slot"]["item_id"])
            require(
                len(selected) == 1
                and selected[0]["expected"] is True
                and selected[0]["kind"] == body["kind"]
                and row["source"]["record"]
                == definition["runtime_id"] + ":" + body["slot"]["slot_id"]
                and _time(definition["recorded_at"]) <= _time(body["recorded_at"])
                and _time(body["slot"]["window_start"]) <= _time(body["recorded_at"])
                and _time(item["operating_from"])
                <= _time(body["recorded_at"])
                < _time(item["operating_to_exclusive"]),
                "Native followthrough differs from exact prospective calendar/slot",
            )
            handler = {
                "IAM": iam_followup,
                "POLICY": policy_binding,
                "RESTORE": restore_return,
                "RETRY": retry_probe,
            }[body["kind"]]
            facts, exception = handler(history, row, body, definition, inventory)
            facts = {
                "tested_local_attributes": facts,
                "slot": body["slot"],
                "performed_at": body["recorded_at"],
                "past_due": _time(body["recorded_at"]) > _time(body["slot"]["due_at"]),
                "prospective_scope_and_exclusions": {
                    "items": definition["items"],
                    "exclusions": definition["exclusions"],
                },
                "full_clause_performed": False,
                "full_period_effectiveness_established": False,
                "enterprise_population_complete": False,
                "professional_acceptance": "NOT_ASSERTED",
                "source_runtime_or_mailbox_or_original_copy_opened": False,
            }
            status = "EXCEPTION_RECORDED" if exception or facts["past_due"] else "OBSERVED"
        except MissingOriginal as error:
            facts, status = (
                {
                    "missing_selected_original": str(error),
                    "full_clause_performed": False,
                    "professional_acceptance": "NOT_ASSERTED",
                },
                "SUPPORT_UNAVAILABLE",
            )
        except (KeyError, TypeError, ValueError, StopIteration) as error:
            raise ProcedureError("Malformed retained native operating fields") from error
        evidence = [
            {
                "artifact_id": r["artifact_id"],
                "sha256": r["artifact_sha256"],
                "locator": "$; exact native identity, original fields and "
                "retained-byte recalculation",
            }
            for r in history.used.values()
        ]
        facts["quarantined_original_examination"] = [
            {
                "artifact_id": r["artifact_id"],
                "artifact_intake": deepcopy(r["artifact_intake"]),
                "warning": r["artifact_intake"]["quarantine_reason"],
                "examination_scope": "BOUNDED_HELD_BYTES_SHA_EQUALITY_AND_DECLARED_JSON_READ_ONLY",
                "artifact_reclassified_or_ingestion_accepted": False,
            }
            for r in history.used.values()
            if r["artifact_intake"]["status"] == "QUARANTINED"
        ]
        for start in range(0, len(evidence), 20):
            outputs.append(
                {
                    "id": "NATIVE-OPERATING/"
                    + "/".join(map(str, identity(row["source"])))
                    + f"/{start // 20 + 1}",
                    "kind": body["kind"],
                    "status": status,
                    "facts": {
                        **facts,
                        "complete_citation_count": len(evidence),
                        "custody_part": start // 20 + 1,
                    },
                    "evidence": evidence[start : start + 20],
                }
            )
    for candidate in history.rows.values():
        if candidate["source"]["system"] != "operating_depth_definition":
            continue
        history.used = {}
        try:
            row, definition, inventory, slots = declaration(history, pin(candidate))
        except MissingOriginal:
            continue  # The followthrough result already names exact missing support.
        for kind in sorted({s["kind"] for s in slots}):
            census = []
            for slot in (s for s in slots if s["kind"] == kind):
                held = [
                    r
                    for r in history.rows.values()
                    if r["source"]["system"] == "operating_depth_followthrough"
                    and type(r["document"]) is dict
                    and encoded(r["document"].get("declaration_pin")) == encoded(pin(row))
                    and encoded(r["document"].get("slot")) == encoded(slot)
                ]
                held.sort(key=lambda r: r["source"]["version"])
                for r in held:
                    history.resolve(pin(r))
                census.append(
                    {
                        "slot": slot,
                        "due": _time(slot["due_at"]) <= history.as_of,
                        "selected_versions": [
                            {
                                "native": pin(r),
                                "recorded_at": r["document"]["recorded_at"],
                                "recorded_status": r["document"]["observation"]["status"],
                                "late": _time(r["document"]["recorded_at"]) > _time(slot["due_at"]),
                            }
                            for r in held
                        ],
                        "selected_support": "COLLECTED_FOLLOWTHROUGH"
                        if held
                        else "FOLLOWTHROUGH_NOT_COLLECTED",
                        "actual_source_absence_established": False,
                    }
                )
            citations = [
                {
                    "artifact_id": r["artifact_id"],
                    "sha256": r["artifact_sha256"],
                    "locator": "$; exact declared calendar and selected followthrough versions",
                }
                for r in history.used.values()
            ]
            for start in range(0, len(citations), 20):
                outputs.append(
                    {
                        "id": "NATIVE-CALENDAR/"
                        + definition["runtime_id"]
                        + "/"
                        + kind
                        + f"/{start // 20 + 1}",
                        "kind": kind,
                        "status": "SUPPORT_UNAVAILABLE",
                        "facts": {
                            "selected_declared_slot_census": census,
                            "complete_native_operation_inventory_established": False,
                            "later_success_cures_earlier_missing_or_late": False,
                            "full_clause_performed": False,
                            "professional_acceptance": "NOT_ASSERTED",
                        },
                        "evidence": citations[start : start + 20],
                    }
                )
    for candidate in history.rows.values():
        if candidate["source"]["system"] != "operating_period_ledger":
            continue
        history.used = {}
        row, body = history.object(pin(candidate), systems={"operating_period_ledger"})
        require(
            body.get("kind") in {"PERIOD_DECLARATION", "OCCURRENCE_ASSERTION"},
            "Unknown retained native period kind",
        )
        if body["kind"] == "PERIOD_DECLARATION":
            exact(
                body,
                "kind plan source_sha256 qualification",
                "Exact native period declaration required",
            )
            plan = period._plan(deepcopy(body["plan"]))
            require(
                encoded(plan) == encoded(body["plan"])
                and plan["period_id"] == row["source"]["record"]
                and (plan["company_id"], plan["branch_id"])
                == (row["source"]["company"], row["source"]["branch"])
                and _time(plan["declared_at"]) == _time(row["source"]["event_at"])
                and body["qualification"] == period.QUALIFICATION,
                "Retained period plan, scope or clock differs",
            )
            facts = {
                "declared_period_plan": plan,
                "control_ids": plan["control_ids"],
                "operator_assertion_is_business_execution": False,
                "full_period_effectiveness_established": False,
                "professional_acceptance": "NOT_ASSERTED",
            }
        else:
            # A recorded assertion is documentary. It is not a substitute for the
            # retained execution originals examined above or by the legacy methods.
            facts = {
                "native_operator_assertion": body,
                "operator_assertion_is_business_execution": False,
                "control_ids": [],
                "full_period_effectiveness_established": False,
                "professional_acceptance": "NOT_ASSERTED",
            }
        outputs.append(
            {
                "id": "NATIVE-PERIOD/" + "/".join(map(str, identity(row["source"]))),
                "kind": "PERIOD",
                "status": "OBSERVED",
                "facts": facts,
                "evidence": [
                    {
                        "artifact_id": row["artifact_id"],
                        "sha256": row["artifact_sha256"],
                        "locator": "$; exact declared local period plan, not inferred operations",
                    }
                ],
            }
        )
    return outputs


def add_observations(inspections, observations, controls, *, contracts):
    """Append local facts to existing task contracts; no local PASS closes a clause."""
    for inspected in inspections:
        task_id = inspected["task_id"]
        require(task_id in contracts, "Exact declared native task contract required")
        contract = contracts[task_id]
        require(
            set(contract) == {"performed", "unperformed", "allowed_dispositions"}
            and all(inspected[key] == contract[key] for key in ("performed", "unperformed"))
            and {key: inspected["disposition"][key] for key in ("status", "conclusion")}
            in contract["allowed_dispositions"],
            "Native facts must start from an exact accepted method disposition",
        )
        matches = [
            o
            for o in observations
            if any(
                task_id.startswith("TASK-" + c + "-corporate-")
                for c in (
                    set(controls.get(o["kind"], ()))
                    & set(o["facts"].get("control_ids", controls.get(o["kind"], ())))
                )
            )
        ]
        if not matches:
            continue
        additions = [{k: deepcopy(v) for k, v in o.items() if k != "kind"} for o in matches]
        inspected["observations"].extend(additions)
        inspected["artifact_ids"] = list(
            dict.fromkeys(
                [
                    *inspected["artifact_ids"],
                    *(e["artifact_id"] for o in additions for e in o["evidence"]),
                ]
            )
        )
        inspected["result"]["native_operating_attributes"] = additions
        if any(o["status"] == "EXCEPTION_RECORDED" for o in additions) and not task_id.endswith(
            "-TOD"
        ) and {
            "status": inspected["disposition"]["status"], "conclusion": "FAIL"
        } in contract["allowed_dispositions"]:
            inspected["disposition"]["conclusion"] = "FAIL"
        inspected["disposition"]["rationale"] += (
            " Retained native operating facts remain local; broader clauses stay unfinished."
        )
    return inspections


def unsupported_tasks(tasks, contracts):
    return [
        {
            "task_id": t["task_id"],
            "artifact_ids": [],
            "observations": [],
            "performed": contracts[t["task_id"]]["performed"],
            "unperformed": contracts[t["task_id"]]["unperformed"],
            "result": {
                "authored_task": t,
                "legacy_method_support": "SUPPORT_UNAVAILABLE",
                "full_clause_performed": False,
                "professional_acceptance": "NOT_ASSERTED",
            },
            "disposition": {
                "status": "IN_PROGRESS",
                "conclusion": "LIMITATION",
                "rationale": "Legacy originals unavailable; broader authored clauses "
                "remain unperformed.",
            },
        }
        for t in tasks
    ]


def retained_inputs(engine, auditor, engagement, artifact_ids):
    """The workforce reader's existing list interface, with literal flat custody."""
    from . import source_identity_methods as identity_methods

    state = engine.store.get(auditor, engagement)
    available = {a["id"]: a for a in state["artifacts"]}
    require(
        type(artifact_ids) is list
        and artifact_ids
        and len(set(artifact_ids)) == len(artifact_ids)
        and all(type(a) is str and a in available for a in artifact_ids),
        "Distinct actually collected IDs required",
    )
    if all("." in available[a]["source"]["receipt"]["source"]["system"] for a in artifact_ids):
        return identity_methods.retained_inputs(engine, auditor, engagement, artifact_ids)
    bound = identity_methods.binding(engine, state)
    require(
        state.get("company_source_binding") == bound
        and state.get("evidence_acquisition") == "COMPANY_SOURCE_COLLECTION",
        "Activated bound company-source workroom required",
    )
    with engine.store.connect() as db:
        principal = db.execute("SELECT roles FROM principals WHERE id=?", (auditor,)).fetchone()
        member = db.execute(
            "SELECT permission FROM members WHERE principal=? AND engagement=?",
            (auditor, engagement),
        ).fetchone()
        require(
            principal is not None
            and json.loads(principal[0]) == ["learner"]
            and member is not None
            and member[0] == "learn",
            "Actual independent audit performer required",
        )
    rows = []
    for aid in artifact_ids:
        artifact = available[aid]
        require(
            artifact["status"] in {"AVAILABLE", "QUARANTINED"}
            and artifact["source"].get("kind") == "COLLECTED_COMPANY_SOURCE",
            "Ordinary collected native original with explicit intake decision required",
        )
        receipt = artifact["source"]["receipt"]
        source = receipt["source"]
        require(
            receipt["engagement_id"] == engagement
            and receipt["principal_id"] == auditor
            and all(source[k] == bound[k] for k in bound),
            "Actual receipt branch/performer differs",
        )
        identity_methods.private_file(engine.artifacts.root / artifact["sha256"])
        raw = engine.artifacts.read(artifact)
        with engine.company_store._db() as db:
            saved = db.execute(
                "SELECT receipt FROM collections WHERE command_id=?", (receipt["command_id"],)
            ).fetchone()
            require(
                saved is not None and encoded(json.loads(saved[0])) == encoded(receipt),
                "Actual ordinary collection journal differs",
            )
        row = {
            "source": source,
            "receipt": receipt,
            "artifact_id": aid,
            "artifact_sha256": artifact["sha256"],
            "retained_bytes": raw,
            "content_type": source["provenance"].get("content_type"),
            "artifact_intake": {
                k: deepcopy(artifact[k])
                for k in (
                    "name",
                    "mime",
                    "status",
                    "quarantine_reason",
                    "origin",
                    "sha256",
                    "bytes",
                )
            },
        }
        if "." in source["system"]:
            row["logical_family"], row["logical_system"] = source["system"].split(".", 1)
        rows.append(row)
    partition(rows)
    Originals(rows, state["simulated_at"])
    require(
        engine.store.get(auditor, engagement)["revision"] == state["revision"],
        "Engagement changed during original read",
    )
    return rows
