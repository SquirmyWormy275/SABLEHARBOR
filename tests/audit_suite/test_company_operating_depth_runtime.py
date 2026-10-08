"""Owned pre-audit native operations, independent due joins and honest limitations."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from enterprise.audit_suite import company_backup_runtime as backup
from enterprise.audit_suite import company_backup_use_probe as use
from enterprise.audit_suite import company_operating_depth_runtime as depth
from enterprise.audit_suite import company_policy_delivery_runtime as policy
from enterprise.audit_suite.company_operating_period import create_period
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError, _time
from enterprise.audit_suite.operating_source_bridge import encoded, sha

MAIN = Path(__file__).resolve().parents[2]
EARLY = _time("2027-01-01T00:00:00Z")
START = _time("2027-04-01T00:00:00Z")
END = _time("2027-05-01T00:00:00Z")
AT = _time("2027-04-06T00:00:00Z")


def original(store, system, record, body, at=EARLY, owner="AS-P007", branch="depth-owned"):
    if system == "depth_definition":
        # Fixture-only migration to the literal registered definition identity.
        # Former source/proofs remain in their untouched predecessor worktree.
        system = "operating_depth_definition"
        body = deepcopy(body)
        body["runtime_id"] = record
    store.register_system("SH", branch, system, owner)
    return depth.pin(
        store.append_version(
            "SH",
            branch,
            system,
            record,
            expected_version=0,
            command_id="INPUT-" + sha(encoded([branch, system, record]))[:40],
            event_at=at,
            available_at=at,
            content=encoded(body),
            provenance={
                "source_reference": "own-native-business-source",
                "content_type": "application/json",
                "name": record + ".json",
            },
        )
    )


def setup_declaration(
    store,
    kind,
    *,
    branch="depth-owned",
    start=START,
    end=END,
    declared=EARLY,
    recorded=AT,
    retained=None,
    system="corporate-application",
    release=None,
    inventory_extra=None,
):
    item = dict(
        id="LOCAL",
        system_id=system,
        kind=kind,
        operating_from=start,
        operating_to_exclusive=end,
        commissioning_ref=release,
    )
    calendar = dict(
        declared_at=declared,
        period_start=start,
        period_end_exclusive=end,
        cadence_days=30,
        due_offset_days=5,
        items=[item],
        exclusions=[],
    )
    inventory = {
        "systems": [{"system": system, "owner": "AS-P007", **(inventory_extra or {})}],
        "operating_depth_calendar": calendar,
        "whole_estate_claim": "NOT_ESTABLISHED_OUTSIDE_DECLARED_NATIVE_SYSTEMS",
    }
    inv = original(
        store, "business_inventory", "INDEPENDENT-SYSTEMS", inventory, at=declared, branch=branch
    )
    definition = dict(
        schema=depth.DECLARATION,
        runtime_id="DEPTH",
        company="SH",
        branch=branch,
        recorded_at=recorded,
        inventory_scope="EXPLICIT_COMPANY_BUSINESS_INVENTORY_NOT_SELECTED_AUDIT_ARTIFACTS",
        business_inventory_ref=inv,
        retained_period_refs=retained or [],
        local_basis="Explicit local business system and cadence; no forecast workers.",
        **calendar,
    )
    declaration = original(
        store, "depth_definition", "DEPTH", definition, at=recorded, branch=branch
    )
    return declaration, definition


@pytest.fixture
def iam(tmp_path):
    root = tmp_path / "business"
    root.mkdir(mode=0o700)
    store = CompanyStore(root)
    state = dict(
        account_id="P014:application",
        subject_id="P014",
        channel="application",
        rights=["billing-admin", "inventory-admin"],
        active=True,
        starts=EARLY,
        ends=_time("2028-01-01T00:00:00Z"),
        credential_epoch=1,
        review_anchor="P014",
    )
    account = original(
        store,
        "account_application",
        "P014:application",
        {"schema": "SH_COMPANY_PERSON_ACCESS_RECORD_V1", "state": state},
    )
    members = [
        dict(
            subject_id="P014",
            relationship_kind="EMPLOYEE",
            accounts=[{"source": account, "state": state}],
        )
    ]
    population = original(
        store,
        "periodic_review_population",
        "2027-Q1",
        dict(
            schema="SH_COMPANY_PERSON_ACCESS_RECORD_V1",
            members=members,
            period_start=EARLY,
            period_end_exclusive=START,
            membership_sha256=sha(encoded(members)),
            exported_by="AS-P007",
        ),
        at=_time("2027-04-02T00:00:00Z"),
    )
    decisions = original(
        store,
        "periodic_review_decisions",
        "2027-Q1",
        dict(
            schema="SH_COMPANY_PERSON_ACCESS_RECORD_V1",
            population=population,
            population_sha256=sha(encoded(members)),
            reviewed_by="AS-P009",
            missing_subject_ids=[],
            decisions=[
                dict(
                    subject_id="P014",
                    observed_rights=state["rights"],
                    remove_rights=["billing-admin"],
                    decision="REMOVAL_REQUESTED",
                )
            ],
        ),
        at=_time("2027-04-03T00:00:00Z"),
        owner="AS-P009",
    )
    declaration, definition = setup_declaration(store, "IAM", retained=[population, decisions])
    return store, declaration, definition, population, decisions, account


def access_args(iam, **changes):
    _, declaration, _, population, decisions, account = iam
    return (
        dict(
            declaration_pin=declaration,
            slot_id="LOCAL:0",
            population_pin=population,
            decisions_pin=decisions,
            account_pins=[account],
            actor_id="AS-P007",
            reviewer_id="AS-P009",
            permission_mapping={"P014:application": {"billing-admin": "billing-admin"}},
            command_id="FOLLOWUP",
            expected_version=0,
            event_at=AT,
        )
        | changes
    )


def test_owned_retained_quarter_followup_retest_and_normal_collection(iam):
    store, declaration, _, population, decisions, account = iam
    before = depth.declare(store, repository=MAIN, declaration_pin=declaration, as_of=AT)
    assert before["canonical_person_count"] == 52
    assert depth.inspect(store, declaration_pin=declaration, as_of=AT)["missing_due"] == 1
    old = {}
    with store._db() as db:
        for reference in (population, decisions, account):
            row, _ = depth.selected(db, reference, AT)
            old[encoded(reference)] = row["content"]
    result = depth.access_followup(store, **access_args(iam))
    source_before_replay = store.path.read_bytes()
    assert depth.access_followup(store, **access_args(iam)) == result
    assert store.path.read_bytes() == source_before_replay
    census = depth.inspect(store, declaration_pin=declaration, as_of=AT)
    item = census["slots"][0]
    assert item["state"] == "REQUESTED_LOCAL_REMOVALS_VERIFIED"
    observation = item["history"][-1]["observation"]
    assert observation["after_states"]["P014:application"]["rights"] == ["inventory-admin"]
    assert observation["results"][0]["verification"]["removed_permission_probes"] == {
        "billing-admin": "DENY"
    }
    assert observation["all_rights_authorized"] == "NOT_ESTABLISHED_BY_REMOVAL_ONLY"
    # Only after business operation is complete does this own engagement receive source access.
    store.grant("OWN-AUDITOR", "OWN-AUDIT-AFTER-OPERATIONS", "SH", "depth-owned", depth.SYSTEM)
    read = store.read_version(
        "OWN-AUDITOR",
        "OWN-AUDIT-AFTER-OPERATIONS",
        "SH",
        "depth-owned",
        depth.SYSTEM,
        result["record"],
        version=1,
        as_of=AT,
    )
    collection = store.collect(
        "OWN-AUDITOR",
        "OWN-AUDIT-AFTER-OPERATIONS",
        "SH",
        "depth-owned",
        depth.SYSTEM,
        result["record"],
        version=1,
        as_of=AT,
        command_id="OWN-COLLECT",
    )
    assert sha(read["content"]) == collection["source"]["sha256"] == result["sha256"]
    with store._db() as db:
        assert all(
            depth.selected(db, ref, AT)[0]["content"] == old[encoded(ref)]
            for ref in (population, decisions, account)
        )


def test_unresolved_mapping_then_exact_retry_retains_both_versions(iam):
    store, declaration, *_ = iam
    first = depth.access_followup(
        store, **access_args(iam, permission_mapping={"P014:application": {}})
    )
    assert (
        depth.inspect(store, declaration_pin=declaration, as_of=AT)["slots"][0]["state"]
        == "OPEN_UNRESOLVED_SCOPE_OR_PERMISSION"
    )
    second = depth.access_followup(
        store, **access_args(iam, expected_version=1, command_id="CORRECTION")
    )
    assert second["version"] == 2 and first["sha256"] != second["sha256"]
    assert (
        len(depth.inspect(store, declaration_pin=declaration, as_of=AT)["slots"][0]["history"]) == 2
    )


@pytest.mark.parametrize(
    "change",
    ["boolversion", "foreign", "digest", "missing", "actor", "sameactor", "broaden", "lateinput"],
)
def test_exact_native_custody_and_authority_refusals(iam, change):
    store = iam[0]
    args = deepcopy(access_args(iam))
    if change == "boolversion":
        args["account_pins"][0]["version"] = True
    elif change == "foreign":
        args["account_pins"][0]["branch"] = "other"
    elif change == "digest":
        args["account_pins"][0]["sha256"] = "0" * 64
    elif change == "missing":
        args["account_pins"] = []
    elif change == "actor":
        args["actor_id"] = "P015"
    elif change == "sameactor":
        args["reviewer_id"] = args["actor_id"]
    elif change == "broaden":
        args["permission_mapping"]["P014:application"] = {"billing-admin": "inventory-admin"}
    else:
        args["event_at"] = _time("2027-04-01T00:00:00Z")
    before = store.path.read_bytes()
    with pytest.raises(CompanyStoreError):
        depth.access_followup(store, **args)
    assert store.path.read_bytes() == before


def test_calendar_is_native_independent_and_keeps_unknown_estate(iam):
    store, declaration, definition, *_ = iam
    view = depth.declare(store, repository=MAIN, declaration_pin=declaration, as_of=AT)
    assert view["enterprise_completeness_established"] is False
    bad = deepcopy(definition)
    bad["cadence_days"] = 10
    badref = original(store, "depth_definition", "WRONG-CADENCE", bad, at=AT)
    with pytest.raises(CompanyStoreError, match="independently"):
        depth.declare(store, repository=MAIN, declaration_pin=badref, as_of=AT)


def test_normal_native_declaration_registration_and_later_binding_is_not_timely_execution(iam):
    store, _, definition, *_ = iam
    args = dict(
        repository=MAIN,
        business_inventory_pin=definition["business_inventory_ref"],
        retained_period_refs=definition["retained_period_refs"],
        runtime_id="REGISTERED-DEPTH",
        actor_id="AS-P007",
        recorded_at=AT,
        command_id="REGISTER-INDEPENDENT-CALENDAR",
    )
    row = depth.register_declaration(store, **args)
    assert row["system"] == "operating_depth_definition"
    before = store.path.read_bytes()
    assert depth.register_declaration(store, **args) == row
    assert store.path.read_bytes() == before
    view = depth.declare(store, repository=MAIN, declaration_pin=depth.pin(row), as_of=AT)
    assert view["canonical_person_count"] == 52 and len(view["schedule"]) == 1
    # New Jan2028 binding cannot make a 2027 operation occur on time or erase the old gap.
    later = depth.register_declaration(
        store,
        **(
            args
            | {
                "runtime_id": "LATER-BINDING",
                "recorded_at": "2028-01-16T13:00:00Z",
                "command_id": "JANUARY-LATER-BINDING",
            }
        ),
    )
    before = store.path.read_bytes()
    with pytest.raises(CompanyStoreError, match="outside exact native operating window"):
        depth.access_followup(
            store,
            **(
                access_args(iam)
                | {
                    "declaration_pin": depth.pin(later),
                    "event_at": "2028-01-16T13:00:00Z",
                    "command_id": "NO-RETROACTIVE-CURE",
                }
            ),
        )
    assert store.path.read_bytes() == before


@pytest.mark.parametrize("change", ["wrongactor", "beforeoriginal"])
def test_native_declaration_registration_refuses_without_new_record(iam, change):
    store, _, definition, *_ = iam
    before = store.path.read_bytes()
    with pytest.raises(CompanyStoreError):
        depth.register_declaration(
            store,
            repository=MAIN,
            business_inventory_pin=definition["business_inventory_ref"],
            retained_period_refs=definition["retained_period_refs"],
            runtime_id="REFUSED",
            actor_id="AS-P009" if change == "wrongactor" else "AS-P007",
            recorded_at=EARLY if change == "beforeoriginal" else AT,
            command_id="REFUSE-" + change,
        )
    assert store.path.read_bytes() == before


@pytest.mark.parametrize(
    "change", ["none", "wrongdependencyclock", "wrongdependencyrole", "booleanconfig", "exceeded"]
)
def test_exact_existing_retry_configuration_and_no_full_suite_claim(tmp_path, change):
    root = tmp_path / "business"
    root.mkdir(mode=0o700)
    store = CompanyStore(root)
    values = dict(timeout_ms=40, attempts=3, max_total_ms=125)
    if change == "booleanconfig":
        values["attempts"] = True
    elif change == "exceeded":
        values["max_total_ms"] = 100
    config = original(
        store,
        "configurations",
        "CONFIG-CORRECTED",
        dict(configuration=values, configuration_sha256=sha(encoded(values))),
        owner="P005",
    )
    package = {"format": "LOCAL_CONFIG_PACKAGE_V1", "configuration": values}
    dependency = dict(
        system_id=config["system"],
        record_id=config["record"],
        version=1,
        sha256=config["sha256"],
        available_at=EARLY,
    )
    if change == "wrongdependencyclock":
        dependency["available_at"] = "2027-01-02T00:00:00Z"
    elif change == "wrongdependencyrole":
        dependency["system_id"] = "foreign.configurations"
    build = original(
        store,
        "builds",
        "BUILD-CORRECTED",
        dict(
            package=package,
            package_sha256=sha(encoded(package)),
            source=dependency,
        ),
        owner="P005",
    )
    test = original(
        store,
        "tests",
        "TEST-CORRECTED",
        dict(
            artifact=dict(
                system_id=build["system"],
                record_id=build["record"],
                version=1,
                sha256=build["sha256"],
                available_at=EARLY,
            )
        ),
        owner="P005",
    )
    declaration, _ = setup_declaration(store, "RETRY")
    args = dict(
        declaration_pin=declaration,
        slot_id="LOCAL:0",
        configuration_pin=config,
        build_pin=build,
        test_pin=test,
        actor_id="P005",
        command_id="EXECUTED-RETRY",
        event_at=AT,
    )
    if change in {"wrongdependencyclock", "wrongdependencyrole", "booleanconfig"}:
        before = store.path.read_bytes()
        with pytest.raises(CompanyStoreError):
            depth.retry_probe(store, **args)
        assert store.path.read_bytes() == before
        return
    depth.retry_probe(store, **args)
    observation = depth.inspect(store, declaration_pin=declaration, as_of=AT)["slots"][0][
        "history"
    ][0]["observation"]
    assert observation["status"] == (
        "FAIL_LOCAL_RETRY_CRITERION" if change == "exceeded" else "PASS_LOCAL_RETRY_CRITERION"
    )
    assert observation["calculation"]["calculated_total_timeout_ms"] == 120
    assert observation["security_privacy_pipeline_tests"] == "NOT_EXECUTED_BY_THIS_MODEL"


def test_policy_exact_mailbox_receipts_preserve_missing_recipient_and_lateness(tmp_path):
    document_path = "docs/governance/CORPORATE_DOCUMENT_STANDARD_v0.1.md"
    raw = (MAIN / document_path).read_bytes()
    pstart = _time("2027-01-01T09:00:00Z")
    pend = _time("2027-02-01T09:00:00Z")
    pat = _time("2027-01-07T09:00:00Z")
    policy_root = tmp_path / "policy"
    initial = policy.initialize(
        policy_root,
        repository=MAIN,
        plan=dict(
            runtime_id="OWN-POL",
            company="SH",
            branch="depth-owned",
            owner_id="AS-P005",
            cycle_id="OWN-JAN",
            declared_at=pstart,
            due_at=_time("2027-01-06T09:00:00Z"),
            recipients=["AS-P007", "AS-P008"],
            local_basis="Owned simulated source before audit",
        ),
        documents=[
            dict(
                id="STANDARD-V1",
                path=document_path,
                sha256=sha(raw),
                source_metadata_lines=["**Status:** APPROVED DESIGN STANDARD"],
            )
        ],
    )
    runtime_sha = initial["runtime_sha256"]
    view = policy.inspect(policy_root, expected_runtime_sha256=runtime_sha, as_of=pat)
    doc = view["report"]["selected_document_pin"]
    for revision, operation, actor in [(0, "DELIVER", "AS-P005"), (1, "READ_RETURN", "AS-P007")]:
        policy.execute(
            policy_root,
            expected_runtime_sha256=runtime_sha,
            expected_revision=revision,
            command_id="OWN-" + operation,
            actor_id=actor,
            operation=operation,
            event_at=pat,
            rationale="Exact owned native delivery and actual byte return",
            parameters=dict(recipient_id="AS-P007", document_pin=doc),
        )
    root = tmp_path / "business"
    root.mkdir(mode=0o700)
    store = CompanyStore(root)
    declaration, _ = setup_declaration(
        store,
        "POLICY",
        start=pstart,
        end=pend,
        recorded=pat,
        inventory_extra=dict(recipients=["AS-P007", "AS-P008"], document_sha256=sha(raw)),
    )
    depth.policy_binding(
        store,
        declaration_pin=declaration,
        slot_id="LOCAL:0",
        runtime_root=policy_root,
        runtime_sha256=runtime_sha,
        actor_id="AS-P005",
        command_id="BIND-DOCUMENT",
        event_at=pat,
    )
    report = depth.inspect(store, declaration_pin=declaration, as_of=pat)["slots"][0]["history"][0][
        "observation"
    ]
    assert report["all_recipients_delivered"] is False
    assert report["all_recipients_read_return"] is False
    assert report["recorded_policy_report"]["recipients"][0]["late"] is True
    assert report["recorded_policy_report"]["recipients"][1]["delivery_status"] == "MISSING_DUE"
    assert report["human_acknowledgment"] == "NOT_ESTABLISHED"


def test_existing_release_window_excludes_early_due_without_new_commissioning(tmp_path):
    root = tmp_path / "business"
    root.mkdir(mode=0o700)
    store = CompanyStore(root)
    released = _time("2027-04-20T00:00:00Z")
    release = original(
        store,
        "site_release",
        "RL-BOISE",
        dict(fictional_in_universe_operating_release=True, status="OPERATING_RECOVERY_SIMULATED"),
        at=released,
    )
    declaration, body = setup_declaration(store, "RESTORE", release=release)
    # Independent schedule explicitly binds the actual commissioned operating window.
    body["items"][0]["operating_from"] = released
    with store._db() as db:
        _, invbody = depth.selected(db, body["business_inventory_ref"], AT)
    invbody["operating_depth_calendar"]["items"][0]["operating_from"] = released
    newinv = original(store, "business_inventory", "COMMISSIONED-WINDOW", invbody)
    body["business_inventory_ref"] = newinv
    body["recorded_at"] = _time("2027-04-21T00:00:00Z")
    current = original(
        store, "depth_definition", "COMMISSIONED-DEPTH", body, at=body["recorded_at"]
    )
    view = depth.inspect(store, declaration_pin=current, as_of=body["recorded_at"])
    assert view["slots"][0]["state"] == "EXCLUDED_OPERATING_WINDOW"
    assert view["expected_due"] == view["missing_due"] == 0


def test_real_restore_return_capacity_and_age_criterion(tmp_path):
    ledger = tmp_path / "ledger"
    ledger.mkdir(mode=0o700)
    source_ledger = CompanyStore(ledger)
    plan = dict(
        period_id="OWN-RECOVERY",
        company_id="SH",
        branch_id="local-backup",
        owner_id="AS-P007",
        control_ids=["SH-BCM-002", "SH-BCM-003"],
        period_start=_time("2027-01-01T00:00:00Z"),
        period_end_exclusive=_time("2027-02-01T00:00:00Z"),
        declared_at=_time("2026-12-31T00:00:00Z"),
        inventory=[dict(id="DATA", description="Owned JSON business dataset")],
        local_basis="Two independent due copy/restore occurrences, no enterprise BIA",
        schedule=[
            dict(
                id=ident,
                inventory_ids=["DATA"],
                control_id=control,
                due_at=_time(due),
                window_start=_time("2027-01-01T00:00:00Z"),
                window_end_exclusive=_time("2027-01-03T00:00:00Z"),
                depends_on=[],
            )
            for ident, control, due in [
                ("B1", "SH-BCM-002", "2027-01-01T10:00:00Z"),
                ("R1", "SH-BCM-003", "2027-01-02T11:00:00Z"),
            ]
        ],
    )
    declaration = create_period(source_ledger, repository=MAIN, plan=plan)
    root = tmp_path / "backup"
    initial = backup.initialize(
        root,
        repository=MAIN,
        declaration_root=ledger,
        declaration_ref=backup.pin(declaration),
        bindings=[
            dict(occurrence_id=id, dataset_id="DATA", operation=op)
            for id, op in [("B1", "BACKUP"), ("R1", "RESTORE")]
        ],
        datasets=[dict(id="DATA", format="JSON_RECORDS")],
    )
    runtime_sha = initial["runtime_sha256"]

    def call(fn, revision, command, **kwargs):
        return fn(
            root,
            expected_runtime_sha256=runtime_sha,
            expected_revision=revision,
            command_id=command,
            **kwargs,
        )

    content = encoded({"records": [{"id": "ONE", "value": 1}, {"id": "TWO", "value": 2}]})
    data = call(
        backup.append_dataset,
        0,
        "DATA",
        dataset_id="DATA",
        content=content,
        expected_sha256=sha(content),
        event_at="2027-01-01T08:00:00Z",
    )["source_pin"]
    lease = call(
        backup.record_lease,
        1,
        "BACKUP-LEASE",
        operation="BACKUP_WRITE",
        enabled=True,
        valid_from="2027-01-01T00:00:00Z",
        expires_at="2027-01-03T00:00:00Z",
        event_at="2027-01-01T09:00:00Z",
    )["lease_pin"]
    restore_lease = call(
        backup.record_lease,
        2,
        "RESTORE-LEASE",
        operation="RESTORE_READ",
        enabled=True,
        valid_from="2027-01-01T00:00:00Z",
        expires_at="2027-01-03T00:00:00Z",
        event_at="2027-01-01T09:01:00Z",
    )["lease_pin"]
    use_contract = call(
        use.record_use_contract,
        3,
        "USE-CONTRACT",
        occurrence_id="R1",
        source_pin=data,
        reader=dict(kind="JSON_RECORD_FIELD_EQUALS", record_id="ONE", field="value", expected=1),
        rationale="Read actual record ONE through restored native business data",
        event_at="2027-01-01T09:02:00Z",
    )["contract_pin"]
    copied = call(
        backup.run_backup,
        4,
        "BACKUP",
        occurrence_id="B1",
        source_pin=data,
        lease_pin=lease,
        attempted_at="2027-01-01T10:00:00Z",
        rationale="Actual owned byte copy",
    )
    restored = call(
        backup.run_restore,
        5,
        "RESTORE",
        occurrence_id="R1",
        backup_pin=copied["object_pin"],
        comparison_source_pin=data,
        lease_pin=restore_lease,
        attempted_at="2027-01-02T11:00:00Z",
        rationale="Actual owned restored byte copy",
    )
    probe = call(
        use.run_restore_use_probe,
        6,
        "USE-PROBE",
        contract_pin=use_contract,
        restore_job_pin=restored["job_pin"],
        restored_dataset_pin=restored["object_pin"],
        event_at="2027-01-02T11:01:00Z",
    )["probe_pin"]
    business_root = tmp_path / "business"
    business_root.mkdir(mode=0o700)
    business = CompanyStore(business_root)
    release = original(
        business,
        "site_release",
        "RL-OWNED",
        dict(fictional_in_universe_operating_release=True, status="OPERATING_RECOVERY_SIMULATED"),
        at=EARLY,
        branch="local-backup",
    )
    criterion = original(
        business,
        "service_criterion",
        "RETURN-CRITERION",
        dict(
            schema="SH_LOCAL_SERVICE_RETURN_CRITERION_V1",
            service_id="SVC-compute",
            dataset_id="DATA",
            author_id="AS-P007",
            reviewer_id="AS-P008",
            approved_at=EARLY,
            max_age_seconds=200000,
            max_restore_seconds=10,
            min_record_count=2,
            qualification="LOCAL_SIMULATED_SERVICE_CRITERION_NOT_ENTERPRISE_BIA",
        ),
        branch="local-backup",
    )
    now = _time("2027-01-07T00:00:00Z")
    depth_decl, _ = setup_declaration(
        business,
        "RESTORE",
        branch="local-backup",
        start=EARLY,
        end=_time("2027-02-01T00:00:00Z"),
        declared=_time("2026-12-31T00:00:00Z"),
        recorded=now,
        system="SVC-compute",
        release=release,
    )
    args = dict(
        declaration_pin=depth_decl,
        slot_id="LOCAL:0",
        runtime_root=root,
        runtime_sha256=runtime_sha,
        criterion_pin=criterion,
        probe_pin=probe,
        actor_id="AS-P007",
        command_id="NATIVE-SERVICE-RETURN",
        event_at=now,
    )
    result = depth.restore_return(business, **args)
    with business._db() as db:
        _, body = depth.selected(db, depth.pin(result), now)
    observation = body["observation"]
    assert observation["status"] == "PASS_LOCAL_SERVICE_RETURN_CRITERION"
    assert observation["parsed_record_count"] == 2
    assert observation["enterprise_BIA_or_application_acceptance"] is False
    assert observation["review_performed"] is False
    disabled = call(
        backup.record_lease,
        7,
        "DISABLED-RESTORE",
        operation="RESTORE_READ",
        enabled=False,
        valid_from="2027-01-01T00:00:00Z",
        expires_at="2027-01-10T00:00:00Z",
        event_at="2027-01-03T00:00:00Z",
        previous_pin=restore_lease,
    )["lease_pin"]
    failed = call(
        backup.run_restore,
        8,
        "FAILED-RESTORE",
        occurrence_id="R1",
        backup_pin=copied["object_pin"],
        comparison_source_pin=data,
        lease_pin=disabled,
        prior_attempt_pin=restored["job_pin"],
        attempted_at="2027-01-04T00:00:00Z",
        rationale="Own causal disabled-lease failure remains a failed attempt",
    )
    assert failed["status"] == "FAILED" and failed["object_pin"] is None
    failure_args = dict(
        declaration_pin=depth_decl,
        slot_id="LOCAL:0",
        runtime_root=root,
        runtime_sha256=runtime_sha,
        job_pin=failed["job_pin"],
        actor_id="AS-P007",
        command_id="BIND-FAILED-RETURN",
        event_at=now,
        expected_version=1,
    )
    depth.restore_failure(business, **failure_args)
    history = depth.inspect(business, declaration_pin=depth_decl, as_of=now)["slots"][0]["history"]
    assert [h["observation"]["status"] for h in history] == [
        "PASS_LOCAL_SERVICE_RETURN_CRITERION",
        "FAIL_LOCAL_RESTORE_NO_RETURN",
    ]
    assert history[-1]["observation"]["error_code"] == "LOCAL_LEASE_UNAVAILABLE"
    before = business.path.read_bytes()
    with pytest.raises(CompanyStoreError, match="failed zero-return"):
        depth.restore_failure(
            business,
            **(
                failure_args
                | {
                    "job_pin": restored["job_pin"],
                    "command_id": "MUST-NOT-RELABEL-COMPLETED",
                    "expected_version": 2,
                }
            ),
        )
    assert business.path.read_bytes() == before
    with backup.database(root) as db:
        restored_body = backup.native(db, restored["job_pin"])
        path = root / depth.decode(restored_body["content"])["copy_path"]
    original_bytes = path.read_bytes()
    path.write_bytes(b"X" * len(original_bytes))
    before = business.path.read_bytes()
    with pytest.raises(CompanyStoreError):
        depth.restore_return(business, **(args | {"command_id": "MUTATED-COPY"}))
    assert business.path.read_bytes() == before


@pytest.fixture(params=["policy_document", "supplementalops.policy_document"])
def native_policy(tmp_path, request):
    root = tmp_path / "native-originals"
    root.mkdir(mode=0o700)
    source = CompanyStore(root)
    raw = (
        b"November controlled policy edition2\n"
        b"Status: modeled policy bytes, no human acknowledgment\n"
    )
    ref = original(
        source,
        request.param,
        "NOVEMBER-V2",
        {"text": raw.decode()},
        at=_time("2027-10-30T00:00:00Z"),
        owner="AS-P005",
    )
    # Whole native bytes, rather than an inferred scalar/string/body hash, are delivered.
    with source._db() as db:
        native_bytes = depth.selected(db, ref, _time("2027-11-01T09:00:00Z"))[0]["content"]
    declaration = dict(id="NOVEMBER-V2", source_root=str(root), source_pin=ref)
    plan = dict(
        runtime_id="OWN-NATIVE-NOVEMBER",
        company="SH",
        branch="depth-owned",
        owner_id="AS-P005",
        cycle_id="NOVEMBER-EXACT",
        declared_at="2027-11-01T09:00:00Z",
        due_at="2027-11-02T09:00:00Z",
        recipients=["AS-P007", "AS-P008"],
        local_basis="Owned November exact native document delivery binding before audit",
    )
    return source, native_bytes, declaration, plan


def test_native_policy_bytes_before_delivery_and_later_exact_collection(native_policy, tmp_path):
    source, raw, declaration, plan = native_policy
    before = source.path.read_bytes()
    root = tmp_path / "native-policy"
    initial = policy.initialize_native(root, repository=MAIN, plan=plan, documents=[declaration])
    sha_cfg = initial["runtime_sha256"]
    at = "2027-11-01T10:00:00Z"
    view = policy.inspect(root, expected_runtime_sha256=sha_cfg, as_of=at)
    document = view["report"]["selected_document_pin"]
    for revision, op, actor in [(0, "DELIVER", "AS-P005"), (1, "READ_RETURN", "AS-P007")]:
        result = policy.execute(
            root,
            expected_runtime_sha256=sha_cfg,
            expected_revision=revision,
            command_id="NATIVE-" + op,
            actor_id=actor,
            operation=op,
            event_at=at,
            rationale="Return exact retained native November document bytes",
            parameters=dict(recipient_id="AS-P007", document_pin=document),
        )
    assert result["content"] == raw and source.path.read_bytes() == before
    with backup.database(root) as db:
        row = backup.native(db, document)
        assert row["content"] == raw
        provenance = depth.decode(row["provenance"])
        assert provenance["native_document_source"] == declaration["source_pin"]
        assert provenance["copied_native_bytes_not_new_policy_approval"] is True
        assert row["origin"] == "AUTHORED_TRAINING_SOURCE"
    store = CompanyStore(root)
    store.grant("OWN-AUDITOR", "LATER-OWN-AUDIT", "SH", "depth-owned", "policy_document")
    receipt = store.collect(
        "OWN-AUDITOR",
        "LATER-OWN-AUDIT",
        "SH",
        "depth-owned",
        "policy_document",
        "NOVEMBER-V2",
        version=1,
        as_of=at,
        command_id="OWN-NATIVE-POLICY-COLLECT",
    )
    assert receipt["source"]["sha256"] == sha(raw)


@pytest.mark.parametrize("change", ["role", "branch", "version", "hash", "availability"])
def test_native_policy_admission_refuses_wrong_original_without_output(
    native_policy, tmp_path, change
):
    source, _, declaration, plan = native_policy
    declared = deepcopy(declaration)
    if change == "role":
        declared["source_pin"]["system"] = "distribution_timestamp"
    elif change == "branch":
        declared["source_pin"]["branch"] = "other"
    elif change == "version":
        declared["source_pin"]["version"] = True
    elif change == "hash":
        declared["source_pin"]["sha256"] = "0" * 64
    else:
        plan["declared_at"] = "2027-10-01T00:00:00Z"
    before = source.path.read_bytes()
    output = tmp_path / "refused-policy"
    with pytest.raises(CompanyStoreError):
        policy.initialize_native(output, repository=MAIN, plan=plan, documents=[declared])
    assert not output.exists() and source.path.read_bytes() == before


@pytest.fixture
def full_period(tmp_path):
    """Only 36 tiny native joins; no second workforce/account roster."""
    root = tmp_path / "original-periods"
    root.mkdir(mode=0o700)
    store = CompanyStore(root)
    refs, rows = [], {}
    schema = "SH_COMPANY_PERSON_ACCESS_RECORD_V1"
    for month in range(1, 13):
        record = f"2027-{month:02}"
        cutoff = datetime(
            2028 if month == 12 else 2027, 1 if month == 12 else month + 1, 1, tzinfo=UTC
        )
        at = _time(cutoff.isoformat())
        denominator = dict(
            schema=schema,
            cutoff_exclusive=at,
            registered_subject_ids=[],
            accounts=[],
            worker_and_account_counts_are_identical=False,
        )
        census = original(store, "denominator_snapshot", record, denominator, at=at)
        recon = original(
            store,
            "monthly_reconciliation",
            record,
            dict(
                schema=schema,
                denominator=census,
                expected_subject_ids=[],
                account_population_sha256=sha(encoded([])),
                missing_account_subject_ids=[],
                unmatched_review_subject_ids=[],
            ),
            at=_time((cutoff + timedelta(minutes=5)).isoformat()),
            owner="AS-P009",
        )
        refs.extend([census, recon])
        rows[("denominator_snapshot", record)] = denominator
        if month % 3:
            continue
        record = f"2027-Q{month // 3}"
        population = dict(
            schema=schema, denominator=census, members=[], membership_sha256=sha(encoded([]))
        )
        pop = original(
            store,
            "periodic_review_population",
            record,
            population,
            at=_time((cutoff + timedelta(hours=1)).isoformat()),
        )
        decision = dict(
            schema=schema,
            population=pop,
            population_sha256=sha(encoded([])),
            decisions=[],
            missing_subject_ids=[],
            wider_estate_reviewed=False,
            review_status="REGISTERED_SCOPE_REVIEW_RECORDED",
        )
        dec = original(
            store,
            "periodic_review_decisions",
            record,
            decision,
            at=_time((cutoff + timedelta(minutes=70)).isoformat()),
            owner="AS-P009",
        )
        followup = dict(
            schema=schema,
            review=dec,
            population_sha256=sha(encoded([])),
            person_mapping_work=[],
            removal_work=[],
            historical_reviews_replaced=False,
            status="NO_ACTION_REQUIRED_FOR_REGISTERED_SCOPE",
        )
        follow = original(
            store,
            "review_followup",
            record,
            followup,
            at=_time((cutoff + timedelta(minutes=75)).isoformat()),
            owner="AS-P009",
        )
        refs.extend([pop, dec, follow])
        rows[("periodic_review_decisions", record)] = decision
    return store, refs, rows


def test_all_existing_period_joins_preserved_without_new_population(full_period):
    store, refs, _ = full_period
    before = store.path.read_bytes()
    at = "2028-01-16T13:00:00Z"
    view = depth.person_period_joins(store, references=refs, as_of=at)
    assert len(view["monthly"]) == 12 and len(view["quarterly"]) == 4
    assert view["complete_registered_2027_period_join"] is True
    assert view["new_population_or_quarter_review_authored"] is False
    assert view["unnamed_other_estate"] == "NOT_ESTABLISHED_BY_REGISTERED_PERSON_SOURCE"
    subset = depth.person_period_joins(store, references=refs[1:], as_of=at)
    assert subset["complete_registered_2027_period_join"] is False
    assert {"role": "denominator_snapshot", "record": "2027-01"} in subset["missing_original_joins"]
    assert store.path.read_bytes() == before


@pytest.mark.parametrize(
    "change", ["boolversion", "foreign", "digest", "movedcutoff", "promotedscope"]
)
def test_existing_period_join_refusals(full_period, change):
    store, refs, rows = full_period
    selected = deepcopy(refs)
    if change == "boolversion":
        selected[0]["version"] = True
    elif change == "foreign":
        selected[-1]["branch"] = "other"
    elif change == "digest":
        selected[0]["sha256"] = "0" * 64
    elif change == "movedcutoff":
        body = deepcopy(rows[("denominator_snapshot", "2027-01")])
        body["cutoff_exclusive"] = "2027-02-02T00:00:00Z"
        row = store.append_version(
            "SH",
            "depth-owned",
            "denominator_snapshot",
            "2027-01",
            expected_version=1,
            command_id="MOVED-CUTOFF",
            event_at="2027-02-01T00:00:00Z",
            available_at="2027-02-01T00:00:00Z",
            content=encoded(body),
            provenance={"source_reference": "OWN-counter"},
        )
        selected[0] = depth.pin(row)
    else:
        body = deepcopy(rows[("periodic_review_decisions", "2027-Q4")])
        body["wider_estate_reviewed"] = True
        row = store.append_version(
            "SH",
            "depth-owned",
            "periodic_review_decisions",
            "2027-Q4",
            expected_version=1,
            command_id="PROMOTED-SCOPE",
            event_at="2028-01-02T00:00:00Z",
            available_at="2028-01-02T00:00:00Z",
            content=encoded(body),
            provenance={"source_reference": "OWN-counter"},
        )
        selected[-2] = depth.pin(row)
    before = store.path.read_bytes()
    with pytest.raises(CompanyStoreError):
        depth.person_period_joins(store, references=selected, as_of="2028-01-16T13:00:00Z")
    assert store.path.read_bytes() == before
