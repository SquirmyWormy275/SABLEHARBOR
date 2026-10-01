"""Neutral retained bytes exercise recovery without marker/enterprise credit."""

import copy
import json
from datetime import UTC, datetime, timedelta

import pytest

from enterprise.audit_suite.collected_byte_recovery_method import (
    JSON_PREDICATE,
    CollectionContext,
    examine_restore,
    reference,
    sha,
)
from enterprise.audit_suite.company_store import _json, _time
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError


def row(system, record, day, document, *, version=1):
    raw = json.dumps(document, sort_keys=True).encode()
    imported = (datetime.now(UTC) - timedelta(seconds=2)).isoformat()
    collected = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    source = {
        "company": "NEUTRAL-COMPANY",
        "branch": "ALPHA",
        "system": system,
        "record": record,
        "version": version,
        "event_at": _time(day),
        "available_at": _time(day),
        "imported_at": _time(imported),
        "sha256": sha(raw),
        "origin": "AUTHORED_TRAINING_SOURCE",
        "provenance": {
            "source_reference": "neutral-retained-original",
            "name": "original.json",
            "content_type": "application/json",
        },
    }
    return {
        "source": source,
        "content": raw,
        "artifact_id": "ART-" + system + "-" + record + str(version),
        "artifact_sha256": sha(raw),
        "receipt": {
            "source": source,
            "principal_id": "AUDITOR",
            "engagement_id": "ENG-NEUTRAL",
            "collected_at": _time(collected),
            "simulated_as_of": _time("2028-01-03T09:00:00Z"),
            "command_id": "COL-" + system + record,
            "content_bytes": len(raw),
        },
    }


def fixture(*, old_configuration=None):
    ctx = CollectionContext(
        "NEUTRAL-COMPANY", "ALPHA", "ENG-NEUTRAL", "AUDITOR", "2028-01-03T09:00:00Z"
    )
    plan = {
        "period_id": "LOCAL-RECOVERY-FEB2027-NEUTRAL",
        "period_start": "2027-02-04T00:00:00Z",
        "period_end_exclusive": "2027-02-08T00:00:00Z",
    }
    period = row(
        "period-history.operating_period_ledger", "PERIOD", "2027-02-04T00:00:00Z", {"plan": plan}
    )
    runtime = row(
        "backup-runtime-history.runtime_definition",
        "RUNTIME",
        "2027-02-04T01:00:00Z",
        {
            "plan": plan,
            "declaration_original_sha256": period["source"]["sha256"],
            "runtime_id": "NEUTRAL-LOCAL-BYTE-RUNTIME",
            "service_id": "LOCAL-CONFIGURATION-ONLY",
            "qualification": "LOCAL_BYTE_BACKUP_RUNTIME_NOT_DEPLOYMENT_OR_BIA_ACCEPTANCE",
            "datasets": {"CONFIG-BYTES": "/original/archive/not-opened/config.json"},
            "bindings": {
                "B1": {
                    "dataset_id": "CONFIG-BYTES",
                    "occurrence_id": "BACKUP-1",
                    "operation": "BACKUP",
                },
                "R1": {
                    "dataset_id": "CONFIG-BYTES",
                    "occurrence_id": "RESTORE-1",
                    "operation": "RESTORE",
                },
            },
        },
    )
    credential = row(
        "backup-runtime-history.credential_event",
        "LEASE",
        "2027-02-04T02:00:00Z",
        {
            "enabled": True,
            "principal_id": "LOCAL-OPERATOR",
            "valid_from": "2027-02-04T00:00:00Z",
            "expires_at": "2027-02-08T00:00:00Z",
            "authority": "DECLARED_LOCAL_BYTE_OPERATION_ONLY",
        },
    )
    old = (
        {"attempts": 2, "timeout_ms": 100, "max_total_ms": 200}
        if old_configuration is None
        else old_configuration
    )
    current = {"attempts": 3, "timeout_ms": 100, "max_total_ms": 300}
    captured = row(
        "backup-runtime-history.source_dataset", "CONFIG-BYTES", "2027-02-05T00:01:00Z", old
    )
    backup_object = row("backup-runtime-history.backup_object", "B1", "2027-02-05T01:00:00Z", old)
    comparison = row(
        "backup-runtime-history.source_dataset",
        "CONFIG-BYTES",
        "2027-02-06T00:02:00Z",
        current,
        version=2,
    )
    producer_runtime = row(
        "configuration-runtime-history.configuration_runtime",
        "EXPORT-RUNTIME",
        "2027-02-04T03:00:00Z",
        {"runtime_id": "NEUTRAL-CONFIGURATION-RUNTIME", "executes_in_auditor_method": False},
    )
    producer_runtime["source"]["provenance"]["operational_metadata"] = {
        "revision": 1,
        "operator_id": "LOCAL-OPERATOR",
        "authority": "DECLARED_LOCAL_CONFIGURATION_EXPORT_ONLY",
    }
    producer_exports = [
        row(
            "configuration-runtime-history.configuration_export",
            "CONFIG-BYTES",
            "2027-02-05T00:00:00Z",
            old,
        ),
        row(
            "configuration-runtime-history.configuration_export",
            "CONFIG-BYTES",
            "2027-02-06T00:01:00Z",
            current,
            version=2,
        ),
    ]
    for consumer, exported in zip((captured, comparison), producer_exports, strict=True):
        exported["source"]["provenance"]["operational_metadata"] = {
            "operation": "EXPORT",
            "exported_at": exported["source"]["event_at"],
            "operator_id": "LOCAL-OPERATOR",
            "authority": "DECLARED_LOCAL_CONFIGURATION_EXPORT_ONLY",
        }
        pair = {
            "original": {**reference(exported["source"]), "publication_id": "NEUTRAL-PUBLICATION"},
            "definition": reference(producer_runtime["source"]),
        }
        original_pair = {"original": exported["source"], "definition": producer_runtime["source"]}
        consumer["source"]["provenance"]["operational_metadata"] = {
            "source_admission": {
                "consumed_at": consumer["source"]["event_at"],
                "consumer_runtime_id": "NEUTRAL-LOCAL-BYTE-RUNTIME",
                "consumer_runtime_sha256": runtime["source"]["sha256"],
                "dataset_id": "CONFIG-BYTES",
                "source_store_id": "NEUTRAL-ORIGINAL-CONFIGURATION-STORE",
                "source_location_sha256": sha(b"NEUTRAL-ORIGINAL-LOCATION-NOT-OPENED"),
                "identity_basis": "EXPLICIT_NEUTRAL_ENGINEERING_METADATA",
                "qualification": "LOCAL_CONFIGURATION_ADMISSION_ONLY",
                "execution_source_sha256": {
                    "neutral_original_executor.py": sha(b"NEUTRAL-ORIGINAL-EXECUTOR-NOT-EXECUTED"),
                },
                "source_pin": reference(exported["source"]),
                "source_definition_pin": reference(producer_runtime["source"]),
                "metadata": pair["original"],
                "definition_metadata": pair["definition"],
                "original_metadata_sha256": sha(_json(original_pair).encode()),
                "original_metadata_digest_basis": (
                    "EXACT_PRIVATE_ORIGINAL_EXPORT_AND_RUNTIME_METADATA_WITH_ORIGINAL_PROVENANCE"
                ),
                "projected_metadata_sha256": sha(_json(pair).encode()),
                "projected_metadata_digest_basis": "PUBLISHED_REFERENCE_HEADER_PAIR_ONLY",
            }
        }
    restored = row("backup-runtime-history.restored_dataset", "R1", "2027-02-06T01:10:00Z", old)
    backup = row(
        "backup-runtime-history.backup_job",
        "B1",
        "2027-02-05T01:00:00Z",
        {
            "runtime_id": "NEUTRAL-LOCAL-BYTE-RUNTIME",
            "dataset_id": "CONFIG-BYTES",
            "occurrence_id": "BACKUP-1",
            "operation": "BACKUP",
            "performed_by": "LOCAL-OPERATOR",
            "business_attempted_at": "2027-02-05T01:00:00Z",
            "source_pin": reference(captured["source"]),
            "object_pin": reference(backup_object["source"]),
            "lease_pin": reference(credential["source"]),
        },
    )
    restore = row(
        "backup-runtime-history.restore_job",
        "R1",
        "2027-02-06T01:10:00Z",
        {
            "runtime_id": "NEUTRAL-LOCAL-BYTE-RUNTIME",
            "dataset_id": "CONFIG-BYTES",
            "occurrence_id": "RESTORE-1",
            "operation": "RESTORE",
            "performed_by": "LOCAL-OPERATOR",
            "business_attempted_at": "2027-02-06T01:10:00Z",
            "actual_elapsed_seconds": 0.012,
            "duration_basis": "REAL_ORIGINAL_LOCAL_COPY_TIME_NOT_BUSINESS_COMPLETION",
            "status": "RECORDED_LOCAL_COPY",
            "checkpoint_age_seconds": 87000.0,
            "byte_copy_matches_selected_backup": True,
            "comparison_bytes_equal": True,
            "qualification": "LOCAL_CONFIGURATION_BYTES_ONLY",
            "source_pin": reference(backup_object["source"]),
            "object_pin": reference(restored["source"]),
            "lease_pin": reference(credential["source"]),
            "comparison_source_pin": reference(comparison["source"]),
            "copy_path": "/archive/path/never-opened",
        },
    )
    rows = [
        period,
        runtime,
        credential,
        captured,
        backup_object,
        comparison,
        restored,
        backup,
        restore,
        producer_runtime,
        *producer_exports,
    ]
    return rows, {
        "context": ctx,
        "restore_ref": reference(restore["source"]),
        "runtime_ref": reference(runtime["source"]),
        "period_ref": reference(period["source"]),
    }


def test_actual_isolated_backup_copy_and_typed_json_read_keep_business_and_real_time_distinct(
    tmp_path,
):
    tmp_path.chmod(0o700)
    rows, kw = fixture()
    result = examine_restore(rows, scratch=tmp_path / "new-restore", **kw)
    assert result["real_isolated_byte_restore_performed"]
    assert result["independent_byte_checks"]["auditor_restore_equals_selected_backup"]
    assert result["independent_byte_checks"]["backup_equals_its_captured_source"]
    assert not result["independent_byte_checks"]["company_restore_equals_selected_comparison"]
    assert result["company_operation_attribution"]["source_reported_comparison_match"]
    assert result["typed_json_usability"]["minimum_single_attempt_budget"]
    assert result["attributable_local_age"]["backup_checkpoint_age_seconds"] == 87000
    assert result["attributable_local_age"]["configuration_capture_event_age_seconds"] == 90540
    assert not result["attributable_local_age"]["application_or_ephi_data_as_of_established"]
    assert result["auditor_execution"]["elapsed_ns"] >= 0
    assert not result["historical_august_marker_restore_reperformed"]
    assert not result["accepted_business_rto_rpo_established"]
    assert result["conclusion"] == "LIMITATION" and not result["full_task_credit"]
    admission = result["configuration_admission_observations"]["captured_configuration"]
    assert admission["consumer_bytes_equal_collected_export"]
    assert admission["projected_header_pair_digest_independently_verified"]
    assert not admission["original_archive_metadata_independently_authenticated"]
    assert not admission["archive_digest_relabelled_as_projected_metadata_digest"]


def test_producer_admission_needs_collected_originals_not_equal_digest_aliases(tmp_path):
    tmp_path.chmod(0o700)
    rows, kw = fixture()
    rows = [
        item
        for item in rows
        if item["source"]["system"] != "configuration-runtime-history.configuration_export"
    ]
    result = examine_restore(rows, scratch=tmp_path / "missing-export", **kw)
    assert result["status"] == "SUPPORT_UNAVAILABLE"
    assert "captured_configuration.producer_export" in result["missing_exact_originals"]
    assert not (tmp_path / "missing-export").exists()


def test_original_archive_digest_cannot_replace_projected_published_header_pair_digest(tmp_path):
    tmp_path.chmod(0o700)
    rows, kw = fixture()
    captured = next(
        item
        for item in rows
        if item["source"]["system"].endswith(".source_dataset") and item["source"]["version"] == 1
    )
    admission = captured["source"]["provenance"]["operational_metadata"]["source_admission"]
    admission["projected_metadata_sha256"] = admission["original_metadata_sha256"]
    with pytest.raises(ProcedureError, match="header-pair digest"):
        examine_restore(rows, scratch=tmp_path / "bad-digest-basis", **kw)
    assert not (tmp_path / "bad-digest-basis").exists()


@pytest.mark.parametrize("change", ["restricted", "different_collected_version"])
def test_resealed_admission_header_keeps_restricted_and_distinct_targets_separate(tmp_path, change):
    tmp_path.chmod(0o700)
    rows, kw = fixture()
    captured = next(
        item
        for item in rows
        if item["source"]["system"].endswith(".source_dataset") and item["source"]["version"] == 1
    )
    admission = captured["source"]["provenance"]["operational_metadata"]["source_admission"]
    if change == "restricted":
        admission["metadata"] = {
            "custody_id": "UPSTREAM-" + "a" * 24,
            "status": "RESTRICTED_CROSS_BRANCH_DEPENDENCY",
        }
    else:
        other = next(
            item
            for item in rows
            if item["source"]["system"].endswith(".configuration_export")
            and item["source"]["version"] == 2
        )
        admission["metadata"] = reference(other["source"])
    admission["projected_metadata_sha256"] = sha(
        _json(
            {"original": admission["metadata"], "definition": admission["definition_metadata"]}
        ).encode()
    )
    target = tmp_path / "no-alias"
    if change == "restricted":
        result = examine_restore(rows, scratch=target, **kw)
        assert result["status"] == "SUPPORT_UNAVAILABLE"
        assert "captured_configuration.producer_export" in result["missing_exact_originals"]
    else:
        with pytest.raises(ProcedureError, match="different originals"):
            examine_restore(rows, scratch=target, **kw)
    assert not target.exists()


def test_missing_backup_original_is_unavailable_support_never_reconstructed_from_digest_flags(
    tmp_path,
):
    tmp_path.chmod(0o700)
    rows, kw = fixture()
    rows = [r for r in rows if not r["source"]["system"].endswith(".backup_object")]
    target = tmp_path / "must-not-be-created"
    result = examine_restore(rows, scratch=target, **kw)
    assert result["status"] == "SUPPORT_UNAVAILABLE"
    assert "backup_object" in result["missing_exact_originals"]
    assert not result["real_isolated_byte_restore_performed"] and not target.exists()


@pytest.mark.parametrize(
    "configuration",
    [
        {"attempts": True, "timeout_ms": 100, "max_total_ms": 200},
        {"attempts": 2, "timeout_ms": 100, "max_total_ms": 50},
    ],
)
def test_intact_recovered_bytes_do_not_establish_typed_configuration_usability(
    tmp_path, configuration
):
    tmp_path.chmod(0o700)
    rows, kw = fixture(old_configuration=configuration)
    result = examine_restore(rows, scratch=tmp_path / "bounded-restore", **kw)
    assert result["real_isolated_byte_restore_performed"]
    assert result["independent_byte_checks"]["backup_equals_its_captured_source"]
    assert not result["typed_json_usability"]["minimum_single_attempt_budget"]
    assert not result["typed_json_usability"]["application_workflow_usability_established"]
    assert not result["full_task_credit"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("engagement_id", "ENG-OTHER"),
        ("principal_id", "REVIEWER"),
        ("simulated_as_of", _time("2028-01-04T09:00:00Z")),
    ],
)
def test_foreign_or_future_collection_cannot_supply_retained_byte_inputs(tmp_path, field, value):
    tmp_path.chmod(0o700)
    rows, kw = fixture()
    rows[0]["receipt"][field] = value
    with pytest.raises(ProcedureError, match="custody"):
        examine_restore(rows, scratch=tmp_path / "bad", **kw)
    assert not (tmp_path / "bad").exists()


def test_changed_exact_version_digest_rejects_instead_of_latest_or_equal_byte_alias_fallback(
    tmp_path,
):
    tmp_path.chmod(0o700)
    rows, kw = fixture()
    kw["restore_ref"]["sha256"] = "0" * 64
    with pytest.raises(ProcedureError, match="pointer"):
        examine_restore(rows, scratch=tmp_path / "bad", **kw)


@pytest.mark.parametrize("mutation", ["boolean_version", "missing_available_clock"])
def test_incomplete_or_boolean_native_reference_is_not_an_exact_version(tmp_path, mutation):
    tmp_path.chmod(0o700)
    rows, kw = fixture()
    if mutation == "boolean_version":
        kw["restore_ref"]["version"] = True
    else:
        del kw["restore_ref"]["available_at"]
    with pytest.raises(ProcedureError, match="Exact native"):
        examine_restore(rows, scratch=tmp_path / "bad", **kw)
    assert not (tmp_path / "bad").exists()


def test_presealed_predicate_does_not_admit_source_executable_instructions_or_archived_copy_path(
    tmp_path,
):
    tmp_path.chmod(0o700)
    rows, kw = fixture()
    predicate = copy.deepcopy(JSON_PREDICATE)
    predicate["executes_source_code"] = True
    with pytest.raises(ProcedureError, match="presealed"):
        examine_restore(rows, scratch=tmp_path / "bad", predicate=predicate, **kw)
    assert not (tmp_path / "bad").exists()


def test_existing_scratch_cannot_be_overwritten_by_selected_restoration(tmp_path):
    tmp_path.chmod(0o700)
    rows, kw = fixture()
    target = tmp_path / "existing"
    target.mkdir(mode=0o700)
    (target / "retained.txt").write_text("preserved")
    with pytest.raises(ProcedureError, match="New private"):
        examine_restore(rows, scratch=target, **kw)
    assert (target / "retained.txt").read_text() == "preserved"


def test_retained_input_bridge_uses_actual_engine_collection_and_bound_clock(tmp_path):
    from pathlib import Path

    from enterprise.audit_suite.collected_byte_recovery_method import retained_inputs
    from enterprise.audit_suite.company_store import CompanyStore
    from enterprise.audit_suite.engine import Engine

    tmp_path.chmod(0o700)
    company = tmp_path / "neutral-company"
    company.mkdir(mode=0o700)
    native = CompanyStore(company)
    native.register_system(
        "NEUTRAL-COMPANY", "ALPHA", "backup-runtime-history.backup_object", "LOCAL-OWNER"
    )
    raw = b'{"attempts":2,"timeout_ms":100,"max_total_ms":200}'
    native.append_version(
        "NEUTRAL-COMPANY",
        "ALPHA",
        "backup-runtime-history.backup_object",
        "B1",
        expected_version=0,
        command_id="neutral-byte-original",
        event_at="2027-02-05T01:00:00Z",
        available_at="2027-02-05T01:00:00Z",
        content=raw,
        provenance={
            "source_reference": "neutral-engineering-original",
            "name": "config.json",
            "content_type": "application/json",
        },
    )
    engine = Engine(
        tmp_path / "audit", repository=Path(__file__).resolve().parents[2], company_root=company
    )
    operator = engine.store.provision("Neutral operator", ["instructor"])["id"]
    auditor = engine.store.provision("Neutral auditor", ["learner"])["id"]
    state = engine.create(
        operator,
        {
            "command_id": "neutral-create",
            "title": "Neutral retained input bridge",
            "discipline": "IT",
            "mode": "CLEAN",
            "configuration": {"selections": []},
            "scope": {
                "programs": ["SOC2"],
                "report_type": "Type 2",
                "period_start": "2027-01-01",
                "period_end": "2027-12-31",
                "fieldwork_start": "2027-02-07",
                "timezone": "UTC",
                "boundaries": ["corporate"],
                "control_ids": ["SH-BCM-003"],
            },
        },
    )
    engagement = state["id"]
    engine.store.grant(engagement, auditor, "learn")
    engine.company_bindings[engagement] = {"company": "NEUTRAL-COMPANY", "branch": "ALPHA"}

    def command(actor, kind, payload):
        current = engine.store.get(actor, engagement)
        return engine.command(
            actor,
            engagement,
            {
                "command_id": f"bridge-{current['revision']}",
                "kind": kind,
                "expected_revision": current["revision"],
                "payload": payload,
            },
        )

    command(operator, "company.activate", {})
    command(auditor, "kickoff.start", {})
    native.grant(
        auditor, engagement, "NEUTRAL-COMPANY", "ALPHA", "backup-runtime-history.backup_object"
    )
    state = command(
        auditor,
        "pbc.create",
        {
            "title": "Selected original",
            "purpose": "Byte test",
            "control_id": "SH-BCM-003",
            "person_id": "AS-P007",
            "boundary_id": "corporate",
        },
    )
    request_id = state["requests"][-1]["id"]
    command(auditor, "pbc.issue", {"request_id": request_id})
    state = command(
        auditor,
        "company.collect",
        {
            "request_id": request_id,
            "system_id": "backup-runtime-history.backup_object",
            "record_id": "B1",
            "version": 1,
        },
    )
    artifact_id = state["artifacts"][0]["id"]
    rows, context = retained_inputs(engine, auditor, engagement, [artifact_id])
    assert rows[0]["content"] == raw and context.simulated_at == state["simulated_at"]
    assert context.branch == "ALPHA" and rows[0]["receipt"]["engagement_id"] == engagement
    with pytest.raises(ProcedureError, match="actually collected|Distinct actually"):
        retained_inputs(engine, auditor, engagement, [artifact_id, artifact_id])


def ordinary_inputs(tmp_path, originals):
    """Author only neutral native bytes; retrieve every version via real commands."""
    from pathlib import Path

    from enterprise.audit_suite.collected_byte_recovery_method import retained_inputs
    from enterprise.audit_suite.company_store import CompanyStore
    from enterprise.audit_suite.engine import Engine

    company = tmp_path / "native-company"
    company.mkdir(mode=0o700)
    store = CompanyStore(company)
    for system in sorted({r["source"]["system"] for r in originals}):
        store.register_system("NEUTRAL-COMPANY", "ALPHA", system, "NEUTRAL-SOURCE-OWNER")
    for index, item in enumerate(originals):
        source = item["source"]
        store.append_version(
            "NEUTRAL-COMPANY",
            "ALPHA",
            source["system"],
            source["record"],
            expected_version=source["version"] - 1,
            command_id="neutral-original-" + str(index),
            event_at=source["event_at"],
            available_at=source["available_at"],
            content=item["content"],
            provenance=source["provenance"],
        )
    engine = Engine(
        tmp_path / "actual-neutral-audit",
        repository=Path(__file__).resolve().parents[2],
        company_root=company,
    )
    operator = engine.store.provision("Neutral access operator", ["instructor"])["id"]
    auditor = engine.store.provision("Neutral performer", ["learner"])["id"]
    reviewer = engine.store.provision("Reserved neutral reviewer", ["reviewer"])["id"]
    assert len({operator, auditor, reviewer}) == 3
    state = engine.create(
        operator,
        {
            "command_id": "neutral-recovery-create",
            "title": "Neutral ordinary recovery inputs",
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
                "control_ids": ["SH-BCM-003"],
            },
        },
    )
    engagement = state["id"]
    engine.store.grant(engagement, auditor, "learn")
    engine.store.grant(engagement, reviewer, "review")
    engine.company_bindings[engagement] = {"company": "NEUTRAL-COMPANY", "branch": "ALPHA"}

    def command(actor, kind, payload):
        before = engine.store.get(actor, engagement)
        return engine.command(
            actor,
            engagement,
            {
                "command_id": "neutral-recovery-" + str(before["revision"]),
                "expected_revision": before["revision"],
                "kind": kind,
                "payload": payload,
            },
        )

    command(operator, "company.activate", {})
    command(auditor, "kickoff.start", {})
    command(
        auditor,
        "clock.advance",
        {
            "mode": "TARGET_DATE",
            "target": "2028-01-03T09:00:00Z",
        },
    )
    for system in sorted({r["source"]["system"] for r in originals}):
        store.grant(auditor, engagement, "NEUTRAL-COMPANY", "ALPHA", system)
    state = command(
        auditor,
        "pbc.create",
        {
            "title": "Neutral actual originals",
            "purpose": "Bounded byte test",
            "control_id": "SH-BCM-003",
            "person_id": "AS-P007",
            "boundary_id": "corporate",
        },
    )
    request = state["requests"][-1]["id"]
    command(auditor, "pbc.issue", {"request_id": request})
    for item in originals:
        source = item["source"]
        state = command(
            auditor,
            "company.collect",
            {
                "request_id": request,
                "system_id": source["system"],
                "record_id": source["record"],
                "version": source["version"],
            },
        )
    actual, context = retained_inputs(
        engine,
        auditor,
        engagement,
        [a["id"] for a in state["artifacts"]],
    )
    assert len(actual) == len(originals) and not state["reviews"]
    return actual, context


@pytest.mark.parametrize(
    "role,wrong_system",
    [
        ("restore_ref", "backup-runtime-history.meeting_note"),
        ("runtime_ref", "backup-runtime-history.support_note"),
        ("period_ref", "period-history.policy_note"),
    ],
)
def test_actual_collected_body_identical_record_cannot_impersonate_native_operating_role(
    tmp_path, role, wrong_system
):
    tmp_path.chmod(0o700)
    rows, kw = fixture()
    target = next(r for r in rows if reference(r["source"]) == kw[role])
    target["source"]["system"] = wrong_system
    actual, context = ordinary_inputs(tmp_path, rows)
    selected = next(r for r in actual if r["source"]["system"] == wrong_system)
    kw[role], kw["context"] = reference(selected["source"]), context
    scratch = tmp_path / "must-not-restore"
    with pytest.raises(ProcedureError, match="actual native operating role"):
        examine_restore(actual, scratch=scratch, **kw)
    assert not scratch.exists()


@pytest.mark.parametrize("role", ["runtime_ref", "period_ref"])
def test_actual_collected_retrospective_runtime_or_period_is_explicit_support_limitation(
    tmp_path, role
):
    tmp_path.chmod(0o700)
    rows, kw = fixture()
    target = next(r for r in rows if reference(r["source"]) == kw[role])
    target["source"]["event_at"] = _time("2027-03-20T00:00:00Z")
    target["source"]["available_at"] = _time("2027-03-20T00:01:00Z")
    actual, context = ordinary_inputs(tmp_path, rows)
    selected = next(r for r in actual if r["source"]["system"] == target["source"]["system"])
    kw[role], kw["context"] = reference(selected["source"]), context
    scratch = tmp_path / "no-retrospective-cure"
    result = examine_restore(actual, scratch=scratch, **kw)
    assert result["status"] == "SUPPORT_UNAVAILABLE"
    assert {
        gap["required_at_company_operation"]
        for gap in result["contemporaneous_support_limitations"]
    } == {
        "backup",
        "restore",
    }
    assert not result["real_isolated_byte_restore_performed"] and not scratch.exists()


def test_actual_ordinary_collected_originals_perform_only_the_bounded_byte_copy(tmp_path):
    tmp_path.chmod(0o700)
    rows, kw = fixture()
    actual, kw["context"] = ordinary_inputs(tmp_path, rows)
    result = examine_restore(actual, scratch=tmp_path / "actual-auditor-copy", **kw)
    assert result["real_isolated_byte_restore_performed"]
    assert result["independent_byte_checks"]["auditor_restore_equals_selected_backup"]
    assert not result["independent_byte_checks"]["company_restore_equals_selected_comparison"]
    assert not result["full_task_credit"]


@pytest.mark.parametrize("producer_role", ["configuration_runtime", "configuration_export"])
def test_actual_late_producer_with_resealed_declared_admission_cannot_support_consumption(
    tmp_path, producer_role
):
    tmp_path.chmod(0o700)
    rows, kw = fixture()
    producer = next(
        r
        for r in rows
        if r["source"]["system"] == "configuration-runtime-history." + producer_role
        and (producer_role == "configuration_runtime" or r["source"]["version"] == 2)
    )
    old_reference = reference(producer["source"])
    producer["source"]["event_at"] = _time("2027-03-20T00:00:00Z")
    producer["source"]["available_at"] = _time("2027-03-20T00:01:00Z")
    for consumer in rows:
        admission = (
            consumer["source"]["provenance"].get("operational_metadata", {}).get("source_admission")
        )
        if not admission:
            continue
        for field in ("source_pin", "source_definition_pin", "metadata", "definition_metadata"):
            header = admission[field]
            if all(header[k] == old_reference[k] for k in old_reference):
                admission[field] = {**header, **reference(producer["source"])}
        pair = {"original": admission["metadata"], "definition": admission["definition_metadata"]}
        admission["projected_metadata_sha256"] = sha(_json(pair).encode())
    actual, kw["context"] = ordinary_inputs(tmp_path, rows)
    scratch = tmp_path / "must-not-use-late-producer"
    result = examine_restore(actual, scratch=scratch, **kw)
    assert result["status"] == "SUPPORT_UNAVAILABLE"
    assert any(
        gap["basis"] == "PRODUCER_NOT_CONTEMPORANEOUSLY_AVAILABLE_AT_CONSUMPTION"
        for gap in result["contemporaneous_support_limitations"]
    )
    assert not result["real_isolated_byte_restore_performed"] and not scratch.exists()
