"""Small source-first operations and genuine ordinary collections, no stored audit answers."""

import copy
import json
from pathlib import Path

import pytest

from enterprise.audit_suite import company_backup_use_probe as use_probe
from enterprise.audit_suite import company_policy_delivery_runtime as policy
from enterprise.audit_suite import source_native_operating_methods as methods
from enterprise.audit_suite.company_access_remediation_activity import LocalEntitlements
from enterprise.audit_suite.company_source_edition import publish_edition
from enterprise.audit_suite.company_store import CompanyStore, _time
from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.source_continuity_methods import examine as continuity
from enterprise.audit_suite.source_governance_methods import examine as governance
from enterprise.audit_suite.source_workforce_methods import inspections as workforce
from tests.audit_suite.test_company_backup_runtime import call
from tests.audit_suite.test_company_backup_runtime import runtime as backup_fixture
from tests.audit_suite.test_company_backup_use_probe import _restored

ROOT = Path(__file__).resolve().parents[2]
AS_OF = "2028-01-18T09:00:00Z"


def append(store, system, record, body, at, *, version=1):
    store.register_system("SH", "OWN", system, "AS-P005")
    return store.append_version(
        "SH",
        "OWN",
        system,
        record,
        expected_version=version - 1,
        command_id=system + "-" + record + "-" + str(version),
        event_at=at,
        available_at=at,
        content=methods.encoded(body),
        provenance={
            "source_reference": record,
            "name": methods.sha((system + record).encode()) + ".json",
            "content_type": "application/json",
        },
    )


def ref(row):
    return {k: row[k] for k in methods.PIN}


def definition(store, kind, start, end, *, refs=None, systems=None, release=None):
    scope = store.scope if hasattr(store, "scope") else ("SH", "OWN")
    # The test store's selected scope is explicit; no role aliases are created.
    company, branch = scope
    runtime_id = "OWN-" + kind
    item = {
        "id": kind,
        "system_id": kind + "-LOCAL",
        "kind": kind,
        "operating_from": _time(start),
        "operating_to_exclusive": _time("2028-01-19T00:00:00Z"),
        "commissioning_ref": release,
    }
    calendar = {
        "declared_at": _time(start),
        "period_start": _time(start),
        "period_end_exclusive": _time(end),
        "cadence_days": 1,
        "due_offset_days": 1,
        "items": [item],
        "exclusions": [],
    }
    body = {
        "schema": "SH_COMPANY_NATIVE_OPERATING_DEPTH_DECLARATION_V1",
        "runtime_id": runtime_id,
        "company": company,
        "branch": branch,
        "recorded_at": _time(start),
        "inventory_scope": "EXPLICIT_COMPANY_BUSINESS_INVENTORY_NOT_SELECTED_AUDIT_ARTIFACTS",
        **calendar,
        "retained_period_refs": refs or [],
        "local_basis": "Owned selected local mechanics only",
    }

    def add(system, record, value):
        store.register_system(company, branch, system, "AS-P005")
        return store.append_version(
            company,
            branch,
            system,
            record,
            expected_version=0,
            command_id="OWN-" + system + kind,
            event_at=start,
            available_at=start,
            content=methods.encoded(value),
            provenance={
                "source_reference": record,
                "name": record + ".json",
                "content_type": "application/json",
            },
        )

    inventory = add(
        "business_inventory",
        "INV-" + kind,
        {
            "systems": systems or [{"system": item["system_id"]}],
            "operating_depth_calendar": calendar,
        },
    )
    body["business_inventory_ref"] = ref(inventory)
    declared = add("operating_depth_definition", runtime_id, body)
    return body, ref(declared), methods.schedule(body)[0]


def observe(store, definition_body, declaration_pin, slot, observation, at, *, version=1):
    company, branch = definition_body["company"], definition_body["branch"]
    system = "operating_depth_followthrough"
    record = definition_body["runtime_id"] + ":" + slot["slot_id"]
    body = {
        "schema": "SH_NATIVE_OPERATING_DEPTH_OBSERVATION_V1",
        "kind": slot["kind"],
        "declaration_pin": declaration_pin,
        "slot": slot,
        "recorded_at": _time(at),
        "observation": observation,
        "qualification": methods.QUALIFICATION,
        "professional_acceptance": "NOT_ASSERTED",
    }
    store.register_system(company, branch, system, "AS-P005")
    return store.append_version(
        company,
        branch,
        system,
        record,
        expected_version=version - 1,
        command_id="OWN-OBS-" + slot["kind"] + str(version),
        event_at=at,
        available_at=at,
        content=methods.encoded(body),
        provenance={
            "source_reference": definition_body["runtime_id"],
            "name": methods.sha(record.encode()) + ".json",
            "content_type": "application/json",
        },
    )


def collect(root, target):
    """Operations exist before a normal audit birth. All originals use actual PBC/COL."""
    store = CompanyStore(root)
    with store._db() as db:
        natives = [
            dict(r) for r in db.execute("SELECT * FROM versions ORDER BY system,record,version")
        ]
    scope = {k: natives[0][k] for k in ("company", "branch")}
    engine = Engine(target, repository=ROOT, company_root=root)
    operator = engine.store.provision("Owned operator", ["instructor"])["id"]
    auditor = engine.store.provision("Owned performer", ["learner"])["id"]
    state = engine.create(
        operator,
        {
            "command_id": "OWN-BIRTH",
            "title": "Owned native examinations",
            "discipline": "IT",
            "mode": "CLEAN",
            "configuration": {"selections": []},
            "scope": {
                "programs": ["SOC2"],
                "report_type": "Type 2",
                "period_start": "2027-01-01",
                "period_end": "2027-12-31",
                "fieldwork_start": "2028-01-18",
                "timezone": "UTC",
                "boundaries": ["corporate"],
                "control_ids": ["SH-POL-001"],
            },
        },
    )
    engagement = state["id"]
    engine.store.grant(engagement, auditor, "learn")
    engine.company_bindings[engagement] = scope

    def command(actor, kind, payload):
        current = engine.store.get(actor, engagement)
        return engine.command(
            actor,
            engagement,
            {
                "command_id": "OWN-CMD-" + str(current["revision"]),
                "expected_revision": current["revision"],
                "kind": kind,
                "payload": payload,
            },
        )

    command(operator, "company.activate", {})
    command(auditor, "kickoff.start", {})
    command(auditor, "clock.advance", {"mode": "TARGET_DATE", "target": AS_OF})
    for system in {n["system"] for n in natives}:
        store.grant(auditor, engagement, scope["company"], scope["branch"], system)
    state = command(
        auditor,
        "pbc.create",
        {
            "title": "Owned selected native originals",
            "purpose": "Exact retained local attributes",
            "control_id": "SH-POL-001",
            "person_id": "AS-P007",
            "boundary_id": "corporate",
        },
    )
    request = state["requests"][-1]["id"]
    command(auditor, "pbc.issue", {"request_id": request})
    for native in natives:
        command(
            auditor,
            "company.collect",
            {
                "request_id": request,
                "system_id": native["system"],
                "record_id": native["record"],
                "version": native["version"],
            },
        )
    state = engine.store.get(auditor, engagement)
    rows = methods.retained_inputs(
        engine, auditor, engagement, [a["id"] for a in state["artifacts"]]
    )
    assert len(rows) == len(natives) and not state["workpapers"] and not state["findings"]
    return rows, engine, auditor, engagement


@pytest.fixture(scope="module")
def policy_rows(tmp_path_factory):
    base = tmp_path_factory.mktemp("native-policy")
    base.chmod(0o700)
    root = base / "source"
    plan = {
        "runtime_id": "OWN-POLICY",
        "company": "SH",
        "branch": "OWN",
        "owner_id": "AS-P005",
        "cycle_id": "OWN-2027",
        "declared_at": "2027-01-01T09:00:00Z",
        "due_at": "2027-01-02T09:00:00Z",
        "recipients": ["AS-P007", "AS-P008"],
        "local_basis": "Owned bounded actual copy and read",
    }
    document = "docs/governance/CORPORATE_DOCUMENT_STANDARD_v0.1.md"
    initialized = policy.initialize(
        root,
        repository=ROOT,
        plan=plan,
        documents=[
            {
                "id": "OWN-DOC",
                "path": document,
                "sha256": methods.sha((ROOT / document).read_bytes()),
                "source_metadata_lines": ["**Status:** APPROVED DESIGN STANDARD"],
            }
        ],
    )
    store = CompanyStore(root)
    depth_root = base / "depth-source"
    depth_root.mkdir(mode=0o700)
    depth = CompanyStore(depth_root)
    body, declaration_pin, slot = definition(
        depth,
        "POLICY",
        plan["declared_at"],
        plan["due_at"],
        systems=[
            {
                "system": "POLICY-LOCAL",
                "recipients": plan["recipients"],
                "document_sha256": methods.sha((ROOT / document).read_bytes()),
            }
        ],
    )

    def binding(at):
        view = policy.inspect(root, expected_runtime_sha256=initialized["runtime_sha256"], as_of=at)
        with store._db() as db:
            rows = [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM versions WHERE system='policy_operation' ORDER BY record"
                )
            ]
        refs = [view["report"]["selected_document_pin"]] + [ref(r) for r in rows]
        report = view["report"]
        return {
            "performed_by": "AS-P005",
            "runtime_root": "/not-opened/private-runtime",
            "runtime_sha256": initialized["runtime_sha256"],
            "native_refs": refs,
            "recorded_policy_report": report,
            "policy_state_basis": "FRESH_VERIFIED_NATIVE_OPERATION_PREFIX_AT_EXACT_CUTOFF",
            "status": "EXACT_LOCAL_DOCUMENT_DELIVERY_READ_RECEIPTS_BOUND",
            "human_acknowledgment": "NOT_ESTABLISHED",
            "all_recipients_delivered": all(
                r["delivery_status"] == "DELIVERED_CURRENT_VERSION" for r in report["recipients"]
            ),
            "all_recipients_read_return": all(
                r["read_return_current_delivery"] for r in report["recipients"]
            ),
        }

    observe(depth, body, declaration_pin, slot, binding(plan["due_at"]), plan["due_at"])
    document_pin = policy.inspect(
        root, expected_runtime_sha256=initialized["runtime_sha256"], as_of=plan["due_at"]
    )["report"]["selected_document_pin"]
    for revision, operation in enumerate(("DELIVER", "READ_RETURN")):
        policy.execute(
            root,
            expected_runtime_sha256=initialized["runtime_sha256"],
            expected_revision=revision,
            command_id="OWN-" + operation,
            actor_id="AS-P005" if operation == "DELIVER" else "AS-P007",
            operation=operation,
            event_at="2027-01-03T09:00:00Z",
            rationale="Owned local history, never human acknowledgment",
            parameters={"recipient_id": "AS-P007", "document_pin": document_pin},
        )
    observe(
        depth,
        body,
        declaration_pin,
        slot,
        binding("2027-01-03T09:00:00Z"),
        "2027-01-03T09:00:00Z",
        version=2,
    )
    components = []
    for index, selected in enumerate((root, depth_root)):
        source = CompanyStore(selected)
        with source._db() as db:
            counts = [
                db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
                for table in ("systems", "versions")
            ]
        components.append(
            {
                "id": "OWN-COMPONENT-" + str(index),
                "database": {
                    "path": str(source.path),
                    "sha256": methods.sha(source.path.read_bytes()),
                },
                "systems": counts[0],
                "versions": counts[1],
            }
        )
    publish_edition(components, base / "published")
    return collect(base / "published/company", base / "audit")


@pytest.fixture(scope="module")
def iam_rows(tmp_path_factory):
    base = tmp_path_factory.mktemp("native-iam")
    base.chmod(0o700)
    root = base / "source"
    root.mkdir(mode=0o700)
    store = CompanyStore(root)
    state = {
        "account_id": "OWN-ACCOUNT",
        "subject_id": "AS-P015",
        "channel": "application_account",
        "rights": ["read", "billing-admin"],
        "active": True,
        "starts": _time("2027-01-01T00:00:00Z"),
        "ends": _time("2028-01-19T00:00:00Z"),
        "credential_epoch": 1,
        "review_anchor": "OWN-Q1",
    }
    account = append(
        store,
        "person-access-history.account_application",
        "OWN-ACCOUNT",
        {"schema": "SH_COMPANY_PERSON_ACCESS_RECORD_V1", "state": state},
        "2027-01-01T00:00:00Z",
    )
    embedded = {
        **ref(account),
        "event_at": account["event_at"],
        "available_at": account["available_at"],
    }
    members = [{"subject_id": "AS-P015", "accounts": [{"source": embedded, "state": state}]}]
    population = {
        "schema": "SH_COMPANY_PERSON_ACCESS_RECORD_V1",
        "period_start": _time("2027-01-01T00:00:00Z"),
        "period_end_exclusive": _time("2027-04-01T00:00:00Z"),
        "members": members,
        "membership_sha256": methods.sha(methods.encoded(members)),
        "exported_by": "AS-P005",
    }
    pop = append(
        store,
        "person-access-history.periodic_review_population",
        "2027-Q1",
        population,
        "2027-04-01T01:00:00Z",
    )
    decisions = {
        "schema": "SH_COMPANY_PERSON_ACCESS_RECORD_V1",
        "population": {
            **ref(pop),
            "event_at": pop["event_at"],
            "available_at": pop["available_at"],
        },
        "population_sha256": population["membership_sha256"],
        "reviewed_by": "AS-P007",
        "decisions": [
            {
                "subject_id": "AS-P015",
                "observed_rights": sorted(state["rights"]),
                "remove_rights": ["billing-admin"],
            }
        ],
        "missing_subject_ids": ["AS-P014"],
    }
    dec = append(
        store,
        "person-access-history.periodic_review_decisions",
        "2027-Q1",
        decisions,
        "2027-04-01T02:00:00Z",
    )
    body, declaration_pin, slot = definition(
        store, "IAM", "2027-01-01T00:00:00Z", "2027-01-02T00:00:00Z", refs=[]
    )
    # Retained period references are later attached in a separately recorded declaration,
    # just as the prospective calendar precedes the real quarterly original availability.
    body["retained_period_refs"] = [ref(pop), ref(dec)]
    body["recorded_at"] = _time("2027-04-01T03:00:00Z")
    declared = append(
        store,
        "operating_depth_definition",
        body["runtime_id"],
        body,
        body["recorded_at"],
        version=2,
    )
    declaration_pin = ref(declared)
    before = {state["account_id"]: copy.deepcopy(state)}
    local = LocalEntitlements("AS-P015", "AS-P005", "AS-P007", state["rights"], ["billing-admin"])
    execution = local.execute(
        "AS-P005", "AS-P015", ["billing-admin"], {"billing-admin": "billing-admin"}
    )
    after = copy.deepcopy(before)
    after[state["account_id"]]["rights"] = sorted(local.rights)
    verification = {
        "observed_rights": sorted(local.rights),
        "expected_rights": ["read"],
        "removed_permission_probes": {"billing-admin": "DENY"},
        "verified_by": "AS-P007",
        "verification_basis": "LOCAL_RIGHT_SET_NOT_CREDENTIAL_OR_LIFETIME_PROBE",
    }
    obs = {
        "population_pin": ref(pop),
        "decisions_pin": ref(dec),
        "original_accounts": {state["account_id"]: ref(account)},
        "before_states": before,
        "after_states": after,
        "results": [
            {
                "account_id": state["account_id"],
                "execution": execution,
                "verification": verification,
            }
        ],
        "missing_subject_ids": ["AS-P014"],
        "performed_by": "AS-P005",
        "verified_by": "AS-P007",
        "status": "OPEN_UNRESOLVED_SCOPE_OR_PERMISSION",
        "all_rights_authorized": "NOT_ESTABLISHED_BY_REMOVAL_ONLY",
        "old_population_or_review_replaced": False,
    }
    observe(store, body, declaration_pin, slot, obs, "2027-04-02T01:00:00Z")
    return collect(root, base / "audit")


@pytest.fixture(scope="module")
def restore_rows(tmp_path_factory):
    base = tmp_path_factory.mktemp("native-restore")
    base.chmod(0o700)
    rt = backup_fixture.__wrapped__(base)
    from enterprise.audit_suite import company_backup_runtime as backup

    # A new normal runtime declares BYTES; the earlier fixture/config is not rewritten.
    with rt[2]._db() as db:
        declared = dict(db.execute("SELECT * FROM versions").fetchone())
    initialized = backup.initialize(
        base / "bytes-runtime",
        repository=ROOT,
        declaration_root=base / "ledger",
        declaration_ref=backup.pin(declared),
        bindings=rt[3],
        datasets=[{"id": "DATA", "format": "BYTES"}, {"id": "OTHER", "format": "BYTES"}],
    )
    rt = (base / "bytes-runtime", initialized["runtime_sha256"], rt[2], rt[3])
    contract, restored, revision = _restored(rt)
    result = call(
        rt,
        use_probe.run_restore_use_probe,
        revision,
        "OWN-PROBE",
        contract_pin=contract["contract_pin"],
        restore_job_pin=restored["job_pin"],
        restored_dataset_pin=restored["object_pin"],
        event_at="2027-01-02T11:01:00Z",
    )
    call(
        rt,
        backup.append_dataset,
        revision + 1,
        "OWN-OPAQUE",
        dataset_id="OTHER",
        content=b"OWN opaque workload\x00",
        expected_sha256=methods.sha(b"OWN opaque workload\x00"),
        event_at="2027-01-03T00:00:00Z",
    )
    cfg = json.loads((rt[0] / "RUNTIME.json").read_bytes())
    store = CompanyStore(rt[0])
    store.scope = (cfg["plan"]["company_id"], cfg["plan"]["branch_id"])
    company, branch = store.scope

    def add(system, record, value, at):
        store.register_system(company, branch, system, cfg["operator_id"])
        return store.append_version(
            company,
            branch,
            system,
            record,
            expected_version=0,
            command_id="OWN-" + system,
            event_at=at,
            available_at=at,
            content=methods.encoded(value),
            provenance={
                "source_reference": record,
                "name": record + ".json",
                "content_type": "application/json",
            },
        )

    release = add(
        "transition.site_release",
        "OWN-RELEASE",
        {"fictional_in_universe_operating_release": True, "status": "OPERATING_RECOVERY_SIMULATED"},
        "2027-01-01T00:00:00Z",
    )
    body, declaration_pin, slot = definition(
        store, "RESTORE", "2027-01-01T00:00:00Z", "2027-01-03T00:00:00Z", release=ref(release)
    )
    criterion = {
        "schema": "SH_LOCAL_SERVICE_RETURN_CRITERION_V1",
        "service_id": "RESTORE-LOCAL",
        "dataset_id": "DATA",
        "author_id": cfg["operator_id"],
        "reviewer_id": cfg["operating_reviewer_id"],
        "approved_at": _time("2027-01-01T09:01:30Z"),
        "max_age_seconds": 31536000,
        "max_restore_seconds": 31536000,
        "min_record_count": 2,
        "qualification": "LOCAL_SIMULATED_SERVICE_CRITERION_NOT_ENTERPRISE_BIA",
    }
    criterion_pin = ref(
        add("service_criterion", "OWN-CRITERION", criterion, criterion["approved_at"])
    )
    with store._db() as db:
        native_probe = json.loads(
            db.execute("SELECT content FROM versions WHERE system='restore_use_probe'").fetchone()[
                0
            ]
        )
        job = json.loads(
            db.execute(
                "SELECT content FROM versions WHERE system='restore_job' AND record='R1'"
            ).fetchone()[0]
        )
    obs = {
        "performed_by": cfg["operator_id"],
        "recorded_review_contact": cfg["operating_reviewer_id"],
        "criterion_pin": criterion_pin,
        "native_refs": [
            result["probe_pin"],
            native_probe["contract_pin"],
            native_probe["restore_job_pin"],
            native_probe["restored_dataset_pin"],
            native_probe["source_pin"],
        ],
        "copy_sha256": native_probe["copy_sha256"],
        "read_status": native_probe["read_status"],
        "actual": native_probe["actual"],
        "actual_elapsed_seconds": job["actual_elapsed_seconds"],
        "checkpoint_age_seconds": job["checkpoint_age_seconds"],
        "parsed_record_count": 1,
        "status": "FAIL_LOCAL_SERVICE_RETURN_CRITERION",
        "review_performed": False,
        "enterprise_BIA_or_application_acceptance": False,
    }
    observe(store, body, declaration_pin, slot, obs, "2027-01-02T11:02:00Z")
    return collect(rt[0], base / "audit")


def actual_observations(rows):
    return [
        o for o in methods.examine(rows, as_of=AS_OF) if o["id"].startswith("NATIVE-OPERATING/")
    ]


def test_policy_due_missing_is_not_cured_by_later_real_delivery_read(policy_rows):
    rows = policy_rows[0]
    observations = actual_observations(rows)
    early, late = observations
    assert (
        sum(
            r["delivery_status"] == "MISSING_DUE"
            for r in early["facts"]["tested_local_attributes"]["rederived_native_policy_report"][
                "recipients"
            ]
        )
        == 2
    )
    assert (
        sum(
            r["delivery_status"] == "MISSING_DUE"
            for r in late["facts"]["tested_local_attributes"]["rederived_native_policy_report"][
                "recipients"
            ]
        )
        == 1
    )
    assert early["status"] == late["status"] == "EXCEPTION_RECORDED"
    assert late["facts"]["past_due"] and not late["facts"]["full_clause_performed"]
    outputs = governance(rows, as_of=AS_OF)
    assert len(outputs) == 62 and all(
        o["disposition"]["conclusion"] in {"FAIL", "LIMITATION"} for o in outputs
    )
    assert any(o["result"].get("native_operating_attributes") for o in outputs)


def test_iam_real_right_removal_keeps_original_missing_person_and_period(iam_rows):
    observation = actual_observations(iam_rows[0])[0]
    facts = observation["facts"]["tested_local_attributes"]
    assert (
        facts["missing_subject_ids"] == ["AS-P014"] and facts["requested_permissions_removed"] == 1
    )
    assert (
        facts["quarter_original"] == "2027-Q1"
        and not facts["whole_period_effectiveness_established"]
    )
    assert observation["status"] == "EXCEPTION_RECORDED"
    outputs = workforce(iam_rows[0], as_of=AS_OF)
    assert len(outputs) == 52 and any(
        o["result"].get("native_operating_attributes") for o in outputs
    )


def test_genuine_copy_and_parsed_return_can_still_fail_local_capacity(restore_rows, tmp_path):
    observations = actual_observations(restore_rows[0])
    facts = observations[0]["facts"]["tested_local_attributes"]
    assert facts["read_status"] == "READ" and facts["actual"] == 1
    assert facts["parsed_record_count"] == 1 and facts["min_record_count"] == 2
    assert facts["rederived_source_status"] == "FAIL_LOCAL_SERVICE_RETURN_CRITERION"
    assert (
        observations[0]["status"] == "EXCEPTION_RECORDED"
        and not facts["enterprise_BIA_or_application_acceptance"]
    )
    quarantined = observations[0]["facts"]["quarantined_original_examination"]
    assert {q["artifact_intake"]["name"].split(".")[-1] for q in quarantined} == {"bin"}
    assert len(quarantined) == 3 and all(
        q["artifact_intake"]["status"] == "QUARANTINED"
        and q["warning"] == methods.UNSUPPORTED_INTAKE
        and q["artifact_reclassified_or_ingestion_accepted"] is False
        for q in quarantined
    )
    outputs = continuity(restore_rows[0], as_of=AS_OF, scratch_root=tmp_path)
    assert len(outputs) == 20 and all(o["disposition"]["conclusion"] != "PASS" for o in outputs)


def test_real_backup_opaque_source_is_ordinary_collected_without_generic_typing(restore_rows):
    rows = restore_rows[0]
    row = next(
        r
        for r in rows
        if r["source"]["system"] == "source_dataset" and r["source"]["record"] == "OTHER"
    )
    original = methods.Originals(rows, AS_OF).resolve({k: row["source"][k] for k in methods.PIN})
    assert original["content"] == b"OWN opaque workload\x00" and original["document"] is None
    assert (
        original["mime"] == "application/octet-stream"
        and row["source"]["provenance"]["name"] == "OTHER.bin"
    )
    from enterprise.audit_suite.collected_byte_recovery_method import retained_inputs
    from enterprise.audit_suite.source_library_audit import typed_content

    with pytest.raises(ProcedureError):
        typed_content({**row["source"], "content": original["content"]})
    _, engine, auditor, engagement = restore_rows
    before = engine.store.get(auditor, engagement)
    artifact = next(a for a in before["artifacts"] if a["id"] == row["artifact_id"])
    assert artifact["status"] == "QUARANTINED"
    assert artifact["quarantine_reason"] == methods.UNSUPPORTED_INTAKE
    with pytest.raises(ProcedureError):
        retained_inputs(engine, auditor, engagement, [row["artifact_id"]])
    assert engine.store.get(auditor, engagement) == before


@pytest.mark.parametrize("change", ["other_reason", "wrong_role", "wrong_mime", "wrong_name"])
def test_binary_examination_refuses_other_quarantine_or_physical_input(restore_rows, change):
    rows = copy.deepcopy(restore_rows[0])
    row = next(r for r in rows if r["source"]["system"] == "source_dataset")
    if change == "other_reason":
        row["artifact_intake"]["quarantine_reason"] = "Executable content detected"
    elif change == "wrong_role":
        row["source"]["system"] = "business_inventory"
    elif change == "wrong_mime":
        row["artifact_intake"]["mime"] = "application/json"
    else:
        row["artifact_intake"]["name"] = "unsafe:source.bin"
    with pytest.raises(ProcedureError):
        methods.examine(rows, as_of=AS_OF)


@pytest.mark.parametrize("change", ["declared_pass", "omitted_refs", "unknown_field"])
def test_resealed_policy_observation_does_not_replace_reperformance(policy_rows, change):
    rows = copy.deepcopy(policy_rows[0])
    row = next(
        r
        for r in rows
        if r["source"]["system"] == "operating_depth_followthrough" and r["source"]["version"] == 2
    )
    body = json.loads(row["retained_bytes"])
    if change == "declared_pass":
        body["observation"]["status"] = "PASS"
    elif change == "omitted_refs":
        body["observation"]["native_refs"].pop()
    else:
        body["observation"]["additional_approval"] = True
    raw = methods.encoded(body)
    row["retained_bytes"] = raw
    row["source"]["sha256"] = row["artifact_sha256"] = methods.sha(raw)
    row["receipt"]["content_bytes"] = len(raw)
    with pytest.raises(ProcedureError):
        methods.examine(rows, as_of=AS_OF)


def test_helper_does_not_follow_source_paths_or_execute_source_sql(
    policy_rows, restore_rows, monkeypatch
):
    import sqlite3

    def forbidden(*args, **kwargs):
        raise AssertionError("Pure retained examination attempted external IO")

    monkeypatch.setattr(sqlite3, "connect", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    assert actual_observations(policy_rows[0]) and actual_observations(restore_rows[0])


@pytest.mark.parametrize(
    "change",
    [
        "bytes",
        "hash",
        "receipt_bool",
        "scope",
        "principal",
        "event_after_availability",
        "future_collection",
        "count_bool",
        "artifact_id",
        "duplicate_artifact",
    ],
)
def test_native_custody_refusals(policy_rows, change):
    rows = copy.deepcopy(policy_rows[0])
    r = rows[0]
    if change == "bytes":
        r["retained_bytes"] += b" "
    elif change == "hash":
        r["artifact_sha256"] = "0" * 64
    elif change == "receipt_bool":
        r["receipt"]["source"]["version"] = True
    elif change == "scope":
        r["source"]["branch"] = "FOREIGN"
    elif change == "principal":
        r["receipt"]["principal_id"] = "OTHER"
    elif change == "event_after_availability":
        r["source"]["event_at"] = _time("2028-01-19T00:00:00Z")
    elif change == "future_collection":
        r["receipt"]["simulated_as_of"] = _time("2028-01-19T00:00:00Z")
    elif change == "count_bool":
        r["receipt"]["content_bytes"] = True
    elif change == "artifact_id":
        r["artifact_id"] = ""
    else:
        rows[1]["artifact_id"] = r["artifact_id"]
    with pytest.raises(ProcedureError):
        methods.examine(rows, as_of=AS_OF)


def test_missing_operation_is_unavailable_not_a_replayed_success(policy_rows):
    rows = [
        r
        for r in policy_rows[0]
        if not (r["source"]["system"] == "policy_operation" and r["source"]["record"] == "OP-1")
    ]
    with pytest.raises(ProcedureError):
        methods.examine(rows, as_of=AS_OF)
    rows = [r for r in policy_rows[0] if r["source"]["system"] != "policy_document"]
    assert all(o["status"] == "SUPPORT_UNAVAILABLE" for o in actual_observations(rows))


def test_uncollected_slot_is_not_claimed_as_actual_source_absence(policy_rows):
    rows = [r for r in policy_rows[0] if r["source"]["system"] != "operating_depth_followthrough"]
    census = next(
        o for o in methods.examine(rows, as_of=AS_OF) if o["id"].startswith("NATIVE-CALENDAR/")
    )
    assert census["status"] == "SUPPORT_UNAVAILABLE"
    slot = census["facts"]["selected_declared_slot_census"][0]
    assert (
        slot["selected_support"] == "FOLLOWTHROUGH_NOT_COLLECTED"
        and not slot["actual_source_absence_established"]
    )


def test_current_performer_reader_refuses_another_actor_and_revoked_source(policy_rows):
    rows, engine, auditor, engagement = policy_rows
    other = engine.store.provision("Other learner", ["learner"])["id"]
    engine.store.grant(engagement, other, "learn")
    with pytest.raises(ProcedureError):
        methods.retained_inputs(engine, other, engagement, [r["artifact_id"] for r in rows])
    company, branch, system = (rows[0]["source"][k] for k in ("company", "branch", "system"))
    engine.company_store.grant(auditor, engagement, company, branch, system, active=False)
    state = engine.store.get(auditor, engagement)
    from enterprise.audit_suite.store import DomainError

    with pytest.raises(DomainError):
        engine.command(
            auditor,
            engagement,
            {
                "command_id": "OWN-DENIED",
                "expected_revision": state["revision"],
                "kind": "company.collect",
                "payload": {
                    "request_id": state["requests"][0]["id"],
                    "system_id": system,
                    "record_id": rows[0]["source"]["record"],
                    "version": 1,
                },
            },
        )
    assert engine.store.get(auditor, engagement)["revision"] == state["revision"]
