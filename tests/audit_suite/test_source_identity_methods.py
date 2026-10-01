"""Genuine ordinary collection of neutral identity histories, never old evidence."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.fresh_sec003_procedure import CLOCK_ID, ProcedureError
from enterprise.audit_suite.source_identity_methods import (
    CONTRACT_PATH,
    History,
    examine,
    inspections,
    retained_inputs,
)
from enterprise.audit_suite.store import digest

REPO = Path(__file__).resolve().parents[2]
COMPANY, BRANCH = "NEUTRAL-IDENTITY", "LOCAL-ORIGINALS"


@pytest.fixture(scope="module")
def originals(tmp_path_factory):
    root = tmp_path_factory.mktemp("identity-originals")
    root.chmod(0o700)
    source_root = root / "company"
    source_root.mkdir(mode=0o700)
    source = CompanyStore(source_root)
    native = []

    def put(family, role, record, doc, at, *, version=1, raw=None):
        system = family + "." + role
        source.register_system(COMPANY, BRANCH, system, "neutral-source-owner")
        data = (
            raw
            if raw is not None
            else json.dumps({**doc, "neutral_engineering_fixture": True}).encode()
        )
        meta = source.append_version(
            COMPANY,
            BRANCH,
            system,
            record,
            expected_version=version - 1,
            command_id=f"original-{system}-{record}-{version}",
            event_at=at,
            available_at=at,
            content=data,
            provenance={
                "source_reference": "neutral company source, not audit results",
                "name": "original.txt" if raw is not None else "original.json",
                "content_type": "text/plain; charset=utf-8"
                if raw is not None
                else "application/json",
            },
        )
        native.append(meta)
        return {k: meta[k] for k in CLOCK_ID}

    movers = {}
    for person, month, excess in (("P014", "02", True), ("P015", "05", False)):
        cause = "MOVE-2027-" + person
        effective = f"2027-{month}-10T09:00:00Z"
        auth = {
            "approval_id": cause + "-APPROVAL",
            "approved_by": "neutral-approver",
            "approved_at": f"2027-{month}-09T09:00:00Z",
            "effective_at": effective,
            "add_right": "inventory-admin",
            "remove_right": "billing-admin",
            "add_site": "SITE-NEW",
            "remove_site": "SITE-OLD",
        }
        for version in (1, 2, 3):
            doc = {"cause_id": cause, "person_id": person, "role": "Local application duty"}
            if version == 2:
                doc["pending_transfer"] = {"approval_id": auth["approval_id"]}
            if version == 3:
                doc["transfer_authorization"] = auth
            put(
                "identity-history",
                "hr",
                cause + "-hr",
                doc,
                f"2027-{month}-{7 + version:02}T09:00:00Z",
                version=version,
            )
        accounts = {}
        for role, field, old, new in (
            ("directory", "groups", ["billing-admin"], ["inventory-admin"]),
            (
                "application",
                "rights",
                ["billing-admin"],
                ["inventory-admin"] + (["billing-admin"] if excess else []),
            ),
            ("site_access", "sites", ["SITE-OLD"], ["SITE-NEW"]),
        ):
            for version, value in ((1, old), (2, new)):
                doc = {
                    "cause_id": cause,
                    "person_id": person,
                    field: value,
                    "authorization_id": auth["approval_id"],
                }
                ref = put(
                    "identity-history",
                    role,
                    cause + "-" + role,
                    doc,
                    f"2027-{month}-{8 + version:02}T10:00:00Z",
                    version=version,
                )
                if role == "application":
                    accounts[version] = (ref, value)
        put(
            "identity-history",
            "access_review",
            cause + "-access_review",
            {
                "unapproved_remaining_rights": ["billing-admin"] if excess else [],
                "reviewed_by": "neutral-reviewer",
                "followup_status": "OPEN" if excess else "NONE",
            },
            f"2027-{month}-11T09:00:00Z",
        )
        movers[person] = accounts

    for quarter in range(1, 5):
        record = f"PRIV-2027-Q{quarter}"
        # Retrospective closing documents remain retrospective.
        at = "2028-01-02T09:00:00Z"
        supplied = [] if quarter == 1 else ["P015"]
        members = [
            {
                "person_id": p,
                "record": movers[p][2][0]["record"],
                "version": 2,
                "sha256": movers[p][2][0]["sha256"],
                "rights": movers[p][2][1],
            }
            for p in supplied
        ]
        pop = put(
            "identity-history",
            "review_population",
            record,
            {
                "declared_employee_ids": ["P014", "P015"],
                "members": members,
                "membership_sha256": digest(members),
            },
            at,
        )
        put(
            "identity-history",
            "review_decisions",
            record,
            {
                "population_sha256": pop["sha256"],
                "decisions": [
                    {
                        "person_id": p,
                        "observed_rights": movers[p][2][1],
                        "authorized_rights": ["inventory-admin"],
                        "remove_rights": [],
                        "removal_confirmation": None,
                    }
                    for p in supplied
                ],
            },
            at,
        )
        put(
            "identity-history",
            "review_reconciliation",
            record,
            {
                "population_sha256": pop["sha256"],
                "missing_person_ids": ["P014"],
            },
            at,
        )

    channels = [
        "directory_account",
        "application_account",
        "application_session",
        "api_token",
        "remote_session",
        "physical_badge",
    ]
    put(
        "lifecycle-history",
        "worker_requests",
        "REQUEST",
        {
            "subject_id": "NEUTRAL-FIXED-TERM",
            "request_id": "NEUTRAL-REQUEST",
            "approved": True,
            "sponsor_person_id": "neutral-sponsor",
            "proofing_check": "LOCAL_CORRELATION_ONLY",
            "recorded_at": "2027-03-01T09:00:00Z",
            "expires_at": "2027-03-03T09:00:00Z",
        },
        "2027-03-01T09:00:00Z",
    )
    put(
        "lifecycle-history",
        "identity_events",
        "CREATE",
        {
            "request_id": "NEUTRAL-REQUEST",
            "created_identity": "NEUTRAL-FIXED-TERM",
            "recorded_at": "2027-03-01T09:01:00Z",
        },
        "2027-03-01T09:01:00Z",
    )
    put(
        "lifecycle-history",
        "access_approvals",
        "APPROVAL",
        {
            "approved": True,
            "rights": ["read-only"],
            "reviewer_id": "neutral-approver",
            "provisioner_id": "neutral-provisioner",
            "recorded_at": "2027-03-01T09:02:00Z",
        },
        "2027-03-01T09:02:00Z",
    )
    put(
        "lifecycle-history",
        "access_approvals",
        "LOCAL-CATALOG",
        {
            "conflicting_rights": [["read-only", "destroy-data"]],
        },
        "2027-03-01T08:00:00Z",
    )
    put(
        "lifecycle-history",
        "identity_events",
        "PROVISION",
        {
            "entitlement_diff": {"after": ["read-only"]},
            "recorded_at": "2027-03-01T09:03:00Z",
        },
        "2027-03-01T09:03:00Z",
    )
    put(
        "lifecycle-history",
        "access_reconciliation",
        "CHECKPOINT",
        {
            "probes": {c: "ALLOW" if c == "application_session" else "DENY" for c in channels},
        },
        "2027-03-03T09:00:01Z",
    )
    put(
        "lifecycle-history",
        "revocation_events",
        "EXPIRY-REVOCATION",
        {
            "after": {c: c == "application_session" for c in channels},
        },
        "2027-03-03T09:00:01Z",
    )
    put(
        "lifecycle-history",
        "access_reconciliation",
        "FINAL-PROBES",
        {
            "probes": {c: "DENY" for c in channels},
            "recorded_at": "2027-03-03T09:03:00Z",
        },
        "2027-03-03T09:03:00Z",
    )

    put(
        "nonhuman-history",
        "identity_inventory",
        "IDENTITY",
        {
            "owner_id": "neutral-owner",
            "identity_id": "NEUTRAL-COPY-SERVICE",
            "permitted_operations": ["COPY"],
        },
        "2027-04-01T00:00:00Z",
    )
    for name, epoch, available in (("BASELINE", 1, "01"), ("REPAIRED", 2, "03")):
        payload = {"records": [{"id": "NEUTRAL-ROW", "right": "synthetic-data-only"}]}
        out = put(
            "nonhuman-history",
            "copied_dataset",
            name + "-OUTPUT",
            payload,
            f"2027-04-{available}T00:01:00Z",
        )
        n = next(m for m in native if m["record"] == name + "-OUTPUT")
        with source._db() as db:
            raw = db.execute(
                "SELECT content FROM versions WHERE record=?", (name + "-OUTPUT",)
            ).fetchone()[0]
        put(
            "nonhuman-history",
            "copy_attempts",
            name,
            {
                "status": "COPIED",
                "configured_version": epoch,
                "current_credential_version": epoch,
                "copied_bytes": len(raw),
                "input_sha256": n["sha256"],
                "output_sha256": n["sha256"],
                "output_ref": out,
            },
            f"2027-04-{available}T00:02:00Z",
        )
    put(
        "nonhuman-history",
        "copy_attempts",
        "STALE",
        {
            "status": "AUTHORIZATION_DENIED",
            "configured_version": 1,
            "current_credential_version": 2,
            "copied_bytes": 0,
            "output_ref": None,
        },
        "2027-04-02T00:02:00Z",
    )

    object_bytes = b"Neutral same-object ordinary original\n"
    for family, component in (("iam005-human", "human"), ("iam005-service", "service")):
        obj = put(
            family,
            "local_object",
            "LOCAL-IAM005-TRACE-OBJECT",
            {},
            "2027-05-01T00:00:00Z",
            raw=object_bytes,
        )
        for record, result in (("READ-01", "AUTHORIZED"), ("DENIED-01", "DENIED")):
            put(
                family,
                component + "_access",
                record,
                {
                    "read_bytes": len(object_bytes) if result == "AUTHORIZED" else 0,
                    "read_sha256": obj["sha256"] if result == "AUTHORIZED" else None,
                    "result": result,
                },
                "2027-05-01T00:15:00Z",
            )
        put(
            family,
            component + "_review",
            "REVIEW-01",
            {
                "review_timely": False,
                "review_due_at": "2027-05-01T01:30:00Z",
                "reviewer_id": "neutral-reviewer",
                "operator_id": "neutral-operator",
                "open_timing_exception_id": "NEUTRAL-OPEN-LATE",
            },
            "2027-05-01T02:00:00Z",
        )
    put(
        "iam005emergency",
        "emergency_authority",
        "APPROVE-EMERGENCY-EXERCISE-01",
        {
            "actor_person_or_inert_identity_id": "neutral-approver",
        },
        "2027-06-01T00:00:00Z",
    )
    put(
        "iam005emergency",
        "access_review",
        "REVIEW-ACCESS-01",
        {
            "actor_person_or_inert_identity_id": "neutral-approver",
        },
        "2027-06-02T00:00:00Z",
    )
    put(
        "iam005emergency",
        "exception_register",
        "NEUTRAL-EXCEPTION",
        {"decision": "OPEN"},
        "2027-06-02T00:00:00Z",
    )
    for person, relationship, title in (
        ("P014", "EMPLOYEE", "Mechanical Engineer"),
        ("P015", "EMPLOYEE", "Interaction Designer"),
        ("P008", "FORMER_EMPLOYEE", "Historical former employee"),
    ):
        put(
            "person-access-history",
            "affiliation_register",
            person,
            {
                "person_id": person,
                "relationship_kind": relationship,
                "included_in_service_boundary": relationship == "EMPLOYEE",
                "source_status": "current_employee"
                if relationship == "EMPLOYEE"
                else "former_employee",
                "source_titles": [{"title": title, "status": "RECORDED_NEUTRAL_TITLE"}],
            },
            "2027-01-01T00:15:00Z",
        )

    # The company source exists and contains genuine versions before an audit exists.
    engine = Engine(root / "audit", repository=REPO, company_root=source_root)
    operator = engine.store.provision("Neutral access operator", ["instructor"])
    auditor = engine.store.provision("Neutral independent performer", ["learner"])
    reviewer = engine.store.provision("Neutral reserved reviewer", ["reviewer"])
    state = engine.create(
        operator["id"],
        {
            "command_id": "neutral-identity-birth",
            "title": "Neutral collected identity investigation",
            "discipline": "IT",
            "mode": "CLEAN",
            "configuration": {"selections": []},
            "scope": {
                "programs": ["SOC2"],
                "report_type": "Type 2",
                "period_start": "2027-01-01",
                "period_end": "2027-12-31",
                "fieldwork_start": "2027-12-31",
                "timezone": "UTC",
                "boundaries": ["corporate"],
                "control_ids": ["SH-IAM-003"],
            },
        },
    )
    eid = state["id"]
    engine.store.grant(eid, auditor["id"], "learn")
    engine.store.grant(eid, reviewer["id"], "review")
    engine.company_bindings[eid] = {"company": COMPANY, "branch": BRANCH}

    def command(actor, kind, payload):
        state = engine.store.get(actor, eid)
        return engine.command(
            actor,
            eid,
            {
                "command_id": f"neutral-{state['revision']}-{kind}",
                "kind": kind,
                "expected_revision": state["revision"],
                "payload": payload,
            },
        )

    command(operator["id"], "company.activate", {})
    command(auditor["id"], "kickoff.start", {})
    command(
        auditor["id"], "clock.advance", {"mode": "TARGET_DATE", "target": "2028-01-15T09:00:00Z"}
    )
    for system in sorted({m["system"] for m in native}):
        source.grant(auditor["id"], eid, COMPANY, BRANCH, system)
    requested = command(
        auditor["id"],
        "pbc.create",
        {
            "title": "Selected originals",
            "purpose": "Inspect neutral operational originals",
            "control_id": "SH-IAM-003",
            "person_id": "AS-P007",
            "boundary_id": "corporate",
        },
    )
    rid = requested["requests"][-1]["id"]
    command(auditor["id"], "pbc.issue", {"request_id": rid})
    for metadata in native:
        command(
            auditor["id"],
            "company.collect",
            {
                "system_id": metadata["system"],
                "record_id": metadata["record"],
                "version": metadata["version"],
                "request_id": rid,
            },
        )
    state = engine.store.get(auditor["id"], eid)
    ids = [a["id"] for a in state["artifacts"]]
    records = retained_inputs(engine, auditor["id"], eid, ids)
    return {
        "engine": engine,
        "source": source,
        "auditor": auditor["id"],
        "operator": operator["id"],
        "reviewer": reviewer["id"],
        "engagement": eid,
        "artifact_ids": ids,
        "records": records,
        "as_of": state["simulated_at"],
    }


def test_recalculates_distinct_human_rights_quarters_expiry_bytes_and_independence(originals):
    actual = examine(originals["records"], as_of=originals["as_of"])
    groups = actual["groups"]
    assert all(g["state"] == "EXAMINED_SELECTED_ORIGINALS" for g in groups.values())
    movers = {m["person_id"]: m for m in groups["movers"]["result"]}
    assert movers["P014"]["exception"] is True and movers["P015"]["exception"] is False
    assert next(a for a in movers["P014"]["attributes"] if a["role"] == "application")[
        "excess"
    ] == ["billing-admin"]
    quarters = groups["quarters"]["result"]
    assert quarters[0]["expected_people"] == ["P014"]
    assert quarters[0]["missing_people"] == ["P014"]
    assert all(q["supplied_people"] == ["P015"] for q in quarters[1:])
    worker = groups["worker"]["result"]
    assert worker["checkpoint_active_channels"] == ["application_session"]
    assert worker["final_active_channels"] == [] and worker["correction_delay_seconds"] == 180
    assert worker["historical_expiry_failure_closed_by_later_correction"] is False
    attempts = groups["nonhuman"]["result"]["attempts"]
    assert any(a["status"] == "AUTHORIZATION_DENIED" and a["copied_bytes"] == 0 for a in attempts)
    assert all(a["output_original_matches"] for a in attempts)
    assert all(
        not r["timely"] and r["reviewer_distinct"] for r in groups["local"]["result"]["reviews"]
    )
    assert groups["emergency"]["result"]["self_review"] is True
    assert (
        groups["emergency"]["result"]["marker_establishes_actual_ephi_or_restored_permission_state"]
        is False
    )
    assert (
        groups["workforce"]["result"]["people"]["P014"]["titles"][0]["title"]
        == "Mechanical Engineer"
    )
    assert groups["workforce"]["result"]["people"]["P008"]["service_eligible"] is False


def test_exact30_task_inspections_preserve_four_implementation_failures_and_task_specific_traces(
    originals,
):
    result = inspections(originals["records"], as_of=originals["as_of"])
    contracts = json.loads(CONTRACT_PATH.read_bytes())
    assert [x["task_id"] for x in result] == contracts["selected_task_ids"]
    assert len(result) == 30 and len(contracts["remaining_B01_task_ids"]) == 22
    failures = [x for x in result if x["disposition"]["conclusion"] == "FAIL"]
    assert {x["task_id"].split("-corporate")[0] for x in failures} == {
        "TASK-SH-IAM-003",
        "TASK-SH-IAM-004",
        "TASK-SH-IAM-006",
        "TASK-SH-IAM-007",
    }
    assert sum(x["disposition"]["status"] == "COMPLETE" for x in result) == 13
    for task in result:
        assert task["observations"] and task["artifact_ids"]
        assert task["result"]["authored_task"]["authored_instruction"]
        assert all(x["facts"]["task_id"] == task["task_id"] for x in task["observations"])
        assert task["result"]["old_audit_outcomes_used"] is False
        assert task["unperformed"] and "NOT_RUN" not in task["disposition"].values()


def test_cached_document_cannot_replace_actual_retained_byte_observation(originals):
    records = deepcopy(originals["records"])
    for r in records:
        r["document"] = {"approved": False, "read_bytes": 999, "role": "Invented CEO"}
    assert examine(records, as_of=originals["as_of"]) == examine(
        originals["records"], as_of=originals["as_of"]
    )


@pytest.mark.parametrize(
    "field",
    [
        "source-version",
        "receipt-version",
        "receipt-bytes",
        "artifact-sha",
        "future-cutoff",
        "foreign-principal",
    ],
)
def test_intact_original_bytes_do_not_bypass_strict_receipt_identity_types_or_clocks(
    originals, field
):
    records = deepcopy(originals["records"])
    row = records[0]
    if field == "source-version":
        row["source"]["version"] = True
    elif field == "receipt-version":
        row["receipt"]["source"]["version"] = True
    elif field == "receipt-bytes":
        row["receipt"]["content_bytes"] = True
    elif field == "artifact-sha":
        row["artifact_sha256"] = "0" * 64
    elif field == "future-cutoff":
        row["receipt"]["simulated_as_of"] = "2028-02-01T00:00:00Z"
    else:
        row["receipt"]["principal_id"] = "another-performer"
    with pytest.raises(ProcedureError):
        examine(records, as_of=originals["as_of"])


def test_engine_wrapper_requires_actual_ordinary_auditor_and_existing_artifact_ids(originals):
    for actor in [originals["operator"], originals["reviewer"]]:
        with pytest.raises(ProcedureError, match="performer"):
            retained_inputs(
                originals["engine"], actor, originals["engagement"], originals["artifact_ids"]
            )
    with pytest.raises(ProcedureError, match="another workroom"):
        retained_inputs(
            originals["engine"],
            originals["auditor"],
            originals["engagement"],
            ["ART-does-not-exist"],
        )
    assert (
        retained_inputs(
            originals["engine"],
            originals["auditor"],
            originals["engagement"],
            originals["artifact_ids"],
        )
        == originals["records"]
    )


def test_native_role_transplant_and_missing_quarter_remain_unsupported_not_silently_substituted(
    originals,
):
    records = [
        r
        for r in deepcopy(originals["records"])
        if not (
            r["logical_system"] == "review_population" and r["source"]["record"] == "PRIV-2027-Q2"
        )
    ]
    actual = examine(records, as_of=originals["as_of"])
    assert actual["groups"]["quarters"]["result"][1]["state"] == "SUPPORT_UNAVAILABLE"
    # A similarly shaped body in a different native role is not a source substitute.
    row = next(r for r in records if r["logical_system"] == "review_population")
    row["source"]["system"] = "identity-history.meeting_note"
    row["receipt"]["source"]["system"] = row["source"]["system"]
    row["logical_system"] = "meeting_note"
    actual = examine(records, as_of=originals["as_of"])
    assert actual["groups"]["quarters"]["result"][0]["state"] == "SUPPORT_UNAVAILABLE"


def reseal_document(record, change):
    doc = json.loads(record["retained_bytes"])
    change(doc)
    raw = json.dumps(doc).encode()
    h = hashlib.sha256(raw).hexdigest()
    record.update(retained_bytes=raw, artifact_sha256=h)
    record["source"]["sha256"] = h
    record["receipt"]["source"]["sha256"] = h
    record["receipt"]["content_bytes"] = len(raw)


def test_boolean_partial_member_version_is_rejected_after_byte_and_membership_hash_repair(
    originals,
):
    records = deepcopy(originals["records"])
    target = next(
        r
        for r in records
        if r["logical_system"] == "review_population" and r["source"]["record"] == "PRIV-2027-Q2"
    )

    def change(doc):
        doc["members"][0]["version"] = True
        doc["membership_sha256"] = digest(doc["members"])

    reseal_document(target, change)
    with pytest.raises(ProcedureError, match="quarterly member version"):
        examine(records, as_of=originals["as_of"])


def test_missing_local_output_is_not_reconstructed_from_a_claimed_copy_hash(originals):
    records = [
        r
        for r in originals["records"]
        if not (
            r["logical_family"] == "nonhuman-history" and r["logical_system"] == "copied_dataset"
        )
    ]
    actual = examine(records, as_of=originals["as_of"])
    attempts = actual["groups"]["nonhuman"]["result"]["attempts"]
    copied = [a for a in attempts if a["status"] == "COPIED"]
    assert all(
        a["output_original_matches"] is False and a["output_join_state"] == "ORIGINAL_NOT_COLLECTED"
        for a in copied
    )


def test_future_native_reference_never_supplies_historical_authority(originals):
    records = deepcopy(originals["records"])
    target = next(r for r in records if r["logical_system"] == "access_review")
    later = next(
        r
        for r in records
        if r["logical_system"] == "review_population" and r["source"]["record"] == "PRIV-2027-Q4"
    )
    reseal_document(
        target, lambda doc: doc.update(dependency={k: later["source"][k] for k in CLOCK_ID})
    )
    actual = History(records, originals["as_of"])
    assert any(j["state"] == "SOURCE_UNAVAILABLE_AT_RECORDED_OCCURRENCE" for j in actual.joins)


def test_cross_branch_and_unregistered_reference_remain_explicit_without_extra_source_access(
    originals,
):
    records = deepcopy(originals["records"])
    row = records[0]
    ref = {**{k: row["source"][k] for k in CLOCK_ID}, "branch": "OTHER-BRANCH"}
    reseal_document(row, lambda d: d.update(dependency=ref))
    actual = History(records, originals["as_of"])
    assert actual.joins[0]["state"] == "OUTSIDE_COLLECTED_BRANCH_AUTHORITY"
    assert actual.joins[0]["to"] is None


def test_partial_selected_corpus_does_not_turn_absent_families_into_passes(originals):
    records = [r for r in originals["records"] if r["logical_family"] == "identity-history"]
    actual = inspections(records, as_of=originals["as_of"])
    task = next(x for x in actual if x["task_id"] == "TASK-SH-IAM-001-corporate-IMPLEMENTATION")
    assert task["disposition"] == {
        "status": "IN_PROGRESS",
        "conclusion": "LIMITATION",
        "rationale": task["disposition"]["rationale"],
    }
    assert task["result"]["missing_selected_inputs"] == ["workforce", "worker", "nonhuman"]
    mover = next(x for x in actual if x["task_id"] == "TASK-SH-IAM-003-corporate-IMPLEMENTATION")
    assert mover["disposition"]["conclusion"] == "FAIL"


def test_each_task_matches_review_contract_and_rejects_changed_authored_instruction(
    originals, tmp_path, monkeypatch
):
    from enterprise.audit_suite import source_identity_methods as methods

    contracts = methods.task_contracts()
    for task in inspections(originals["records"], as_of=originals["as_of"]):
        contract = contracts[task["task_id"]]
        assert task["performed"] == contract["performed"]
        assert task["unperformed"] == contract["unperformed"]
        assert {k: task["disposition"][k] for k in ("status", "conclusion")} in contract[
            "allowed_dispositions"
        ]
    changed = json.loads(CONTRACT_PATH.read_text())
    first = changed["selected_task_ids"][0]
    changed["tasks"][first]["authored_instruction"] = "Changed source instruction"
    path = tmp_path / "changed.json"
    path.write_text(json.dumps(changed))
    monkeypatch.setattr(methods, "CONTRACT_PATH", path)
    with pytest.raises(ProcedureError, match="contract pin"):
        inspections(originals["records"], as_of=originals["as_of"])


def test_restricted_dependency_witness_does_not_become_native_authority(originals):
    rows = deepcopy(originals["records"])
    row = rows[0]
    body = json.loads(row["retained_bytes"])
    body["restricted_dependency"] = {
        **{
            k: row["source"][k]
            for k in ("company", "branch", "system", "record", "version", "available_at")
        },
        "event_at": None,
        "status": "RESTRICTED_UNREGISTERED_DEPENDENCY",
        "custody_id": "NEUTRAL-RESTRICTED-WITNESS",
    }
    reseal_document(row, lambda d: d.update(body))
    actual = History(rows, originals["as_of"])
    assert actual.joins[0]["state"] == "RESTRICTED_UNREGISTERED_DEPENDENCY_NOT_NATIVE_AUTHORITY"
    assert actual.joins[0]["to"] is None
    body["restricted_dependency"]["version"] = True
    reseal_document(row, lambda d: d.update(body))
    with pytest.raises(ProcedureError, match="restricted dependency"):
        History(rows, originals["as_of"])
