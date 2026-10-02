"""Neutral originals precede audit creation and are ordinarily collected."""

import copy
import hashlib
import json

import pytest
from test_collected_byte_recovery_method import ordinary_inputs, reseal_document, row

from enterprise.audit_suite.collected_byte_recovery_method import reference
from enterprise.audit_suite.collected_security_history import History
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.source_security_configuration_methods import (
    addressable,
    approvals,
    component_lifecycle,
    configuration,
    contracts,
    examine,
    integrity_movement,
    logging,
    permission_checks,
    physical_conditions,
    task_plan,
)


def native(family, role, record, at, detail, *, fields=None, version=1):
    return row(
        family + "." + role,
        record,
        at,
        {
            "schema": "NEUTRAL-B02-NATIVE-ORIGINAL",
            "detail": detail,
            **(fields or {}),
        },
        version=version,
    )


def collect(tmp_path, originals):
    tmp_path.chmod(0o700)
    actual, context = ordinary_inputs(tmp_path, originals)
    for item in actual:
        item["retained_bytes"] = item["content"]
        item["content_type"] = item["source"]["provenance"]["content_type"]
        item["logical_family"], item["logical_system"] = item["source"]["system"].split(".", 1)
    return actual, context.simulated_at


def documentary_original(system, record, at, document, content_type="application/json"):
    item = row(system, record, at, document)
    if content_type != "application/json":
        raw = document.encode("utf-8")
        item["content"] = raw
        item["source"]["sha256"] = item["artifact_sha256"] = hashlib.sha256(raw).hexdigest()
        item["source"]["provenance"].update(content_type=content_type, name="original.txt")
        item["receipt"]["content_bytes"] = len(raw)
    return item


@pytest.mark.parametrize(
    "content_type", ["application/json", "text/plain", "text/plain; charset=utf-8"]
)
def test_actual_list_and_text_desired_originals_never_supply_structured_configuration(
    tmp_path, content_type
):
    cfg = {"configuration": {"attempts": 2, "timeout_ms": 100, "max_total_ms": 200}}
    document = [{"detail": cfg}] if content_type == "application/json" else json.dumps(cfg)
    unsupported = documentary_original(
        "configuration-history.configuration_desired",
        "RAW-DESIRED",
        "2027-02-01T00:00:00Z",
        document,
        content_type,
    )
    inventory = native(
        "configuration-history",
        "configuration_inventory",
        "ACTUAL",
        "2027-02-01T00:01:00Z",
        cfg,
    )
    drift = native(
        "configuration-history",
        "configuration_drift",
        "CONSUMER",
        "2027-02-02T00:00:00Z",
        {"matches_approved_desired": True},
        fields={
            "source_records": {
                "configuration_inventory": reference(inventory["source"]),
                "configuration_desired": reference(unsupported["source"]),
            }
        },
    )
    actual, clock = collect(tmp_path, [unsupported, inventory, drift])
    # A cached object must never substitute for the ordinary original bytes.
    for held in actual:
        held["document"] = {"detail": cfg}
    history = History(actual, as_of=clock)
    retained = next(r for r in history.rows if r["source"]["record"] == "RAW-DESIRED")
    assert retained["document"] == document
    assert history.select("configuration-history", {"configuration_desired"}) == []
    fact = configuration(history)["embedded_drift_comparisons"][0]
    assert (
        fact["desired_original_status"] == "ORIGINAL_FORMAT_UNSUPPORTED_FOR_STRUCTURED_ATTRIBUTES"
    )
    assert "equal_embedded_configuration" not in fact and "actual_retry" not in fact
    assert any(j["status"] == fact["desired_original_status"] for j in history.joins)
    scratch = tmp_path / "never-created-by-data-only-examination"
    outputs = examine(actual, as_of=clock, scratch_root=scratch)
    assert len(outputs) == 38 and not scratch.exists()
    output = task(outputs, "CFG-002", "TOE")
    assert (
        output["result"]["retained_format_limitations"][0]["structured_attribute_examination"]
        == "UNPERFORMED"
    )
    assert retained["artifact_id"] in output["artifact_ids"]
    raw_observation = next(
        o
        for o in output["observations"]
        if o["id"].startswith("NATIVE-OCCURRENCE-")
        and o["facts"]["source"]["record"] == "RAW-DESIRED"
    )
    assert raw_observation["status"] == "SUPPORT_UNAVAILABLE"
    assert raw_observation["facts"]["task_specific_attributes_supported"] is False
    assert (
        reference(unsupported["source"])
        not in output["result"]["selected_native_population_before_selection"]
    )


def test_actual_list_copy_versions_are_preserved_and_do_not_stop_other_38_tasks(tmp_path):
    originals = original_history()
    before = []
    for version, body in ((1, [{"value": 1}]), (2, [{"value": 99}]), (3, [{"value": 1}])):
        item = row(
            "integrity.test_copy",
            "COPY-01",
            f"2027-06-0{version}T00:00:00Z",
            body,
            version=version,
        )
        originals.append(item)
        before.append(item["source"]["sha256"])
    actual, clock = collect(tmp_path, originals)
    history = History(actual, as_of=clock)
    copies = [r for r in history.rows if r["source"]["system"] == "integrity.test_copy"]
    assert [r["source"]["sha256"] for r in copies] == before
    assert before[0] == before[2] != before[1]
    assert len(copies) == 3 and history.select("integrity", {"test_copy"}) == []
    outputs = examine(actual, as_of=clock, scratch_root=tmp_path / "not-opened")
    assert len(outputs) == 38
    citing = [o for o in outputs if o["result"]["retained_format_limitations"]]
    assert citing and all(len(o["result"]["retained_format_limitations"]) == 3 for o in citing)
    for output in citing:
        assert {r["artifact_id"] for r in copies} <= set(output["artifact_ids"])
        assert not any(
            r["system"] == "integrity.test_copy"
            for r in output["result"]["selected_native_population_before_selection"]
        )
    assert task(outputs, "SEC-003", "CHECK-SOC2:CC7.1")["result"]["examined_attributes"][
        "accepted_pure_selected_inventory_scan_baseline_reperformance"
    ]["omitted_scan_assets"] == ["OPS"]


@pytest.mark.parametrize(
    "mutation", ["bytes", "version_bool", "content_bytes_bool", "future_receipt", "role"]
)
def test_nonobject_original_still_requires_exact_custody(tmp_path, mutation):
    actual, clock = collect(
        tmp_path, [row("integrity.test_copy", "COPY-01", "2027-06-01T00:00:00Z", [{"value": 1}])]
    )
    held = actual[0]
    if mutation == "bytes":
        held["retained_bytes"] += b" "
    elif mutation == "version_bool":
        held["source"]["version"] = True
    elif mutation == "content_bytes_bool":
        held["receipt"]["content_bytes"] = True
    elif mutation == "future_receipt":
        held["receipt"]["simulated_as_of"] = "2029-01-01T00:00:00Z"
    else:
        held["logical_system"] = "security_approval"
    with pytest.raises(ProcedureError):
        History(actual, as_of=clock)


def test_later_list_inventory_does_not_revive_earlier_structured_lag_policy(tmp_path):
    policy = native(
        "logging-history",
        "source_inventory",
        "POLICY",
        "2027-05-01T00:00:00Z",
        {"required_sources": [{"source_id": "LOCAL"}], "local_max_ingestion_lag_seconds": 5},
    )
    newer = row(
        "logging-history.source_inventory",
        "POLICY",
        "2027-05-02T00:00:00Z",
        [{"local_max_ingestion_lag_seconds": 100}],
        version=2,
    )
    event = {"sequence": 1, "source_event_at": "2027-05-03T00:00:00Z"}
    originals = [
        policy,
        newer,
        native(
            "logging-history",
            "publisher_events",
            "PUBLISHER",
            "2027-05-03T00:00:00Z",
            {},
            fields={"local_source_id": "LOCAL", "event": event},
        ),
        native(
            "logging-history",
            "ingestion_journal",
            "INGESTION",
            "2027-05-03T00:00:09Z",
            {},
            fields={
                "local_source_id": "LOCAL",
                "event": event,
                "received_at": "2027-05-03T00:00:09Z",
                "ingestion_lag_seconds": 9,
            },
        ),
        native(
            "logging-history",
            "publisher_checkpoints",
            "CHECKPOINT",
            "2027-05-03T00:00:10Z",
            {},
            fields={"local_source_id": "LOCAL", "sequences": [1]},
        ),
    ]
    actual, clock = collect(tmp_path, originals)
    history = History(actual, as_of=clock)
    checkpoint = logging(history)["checkpoint_populations_before_selection"][0]
    lag = checkpoint["lag_observations"][0]
    assert checkpoint["effective_inventory_originals"] == []
    assert lag["effective_local_lag_limit_seconds"] is None
    assert lag["exceeds_effective_lag_limit"] is None
    assert checkpoint["lag_limit_status"] == "EFFECTIVE_LOCAL_LIMIT_UNAVAILABLE"
    limitations = history.format_limitations({"logging-history"})
    assert len(limitations) == 1 and limitations[0]["source"]["version"] == 2


@pytest.mark.parametrize("other_scope", ["NONE", "FOREIGN", "AMBIGUOUS"])
def test_effective_lag_policy_version_at_checkpoint_preserves_breach_and_explicit_ambiguity(
    tmp_path, other_scope
):
    originals = []
    for version, limit, at in (
        (1, 5, "2027-05-01T00:00:00Z"),
        (2, 6, "2027-05-02T00:00:00Z"),
    ):
        originals.append(
            native(
                "logging-history",
                "source_inventory",
                "LAG-POLICY",
                at,
                {
                    "required_sources": [{"source_id": "LOCAL"}],
                    "local_max_ingestion_lag_seconds": limit,
                },
                version=version,
            )
        )
    if other_scope != "NONE":
        originals.append(
            native(
                "logging-history",
                "source_inventory",
                "OTHER-POLICY",
                "2027-05-02T01:00:00Z",
                {
                    "required_sources": [
                        {"source_id": "FOREIGN" if other_scope == "FOREIGN" else "LOCAL"}
                    ],
                    "local_max_ingestion_lag_seconds": 100,
                },
            )
        )
    event = {
        "sequence": 1,
        "source_event_at": "2027-05-03T00:00:00Z",
        "authorization_decision": "DENY",
    }
    originals.append(
        native(
            "logging-history",
            "publisher_events",
            "PUBLISHER",
            "2027-05-03T00:00:00Z",
            {},
            fields={"local_source_id": "LOCAL", "event": event},
        )
    )
    originals.append(
        native(
            "logging-history",
            "ingestion_journal",
            "INGESTION",
            "2027-05-03T00:00:09Z",
            {},
            fields={
                "local_source_id": "LOCAL",
                "event": event,
                "received_at": "2027-05-03T00:00:09Z",
                "ingestion_lag_seconds": 9,
            },
        )
    )
    originals.append(
        native(
            "logging-history",
            "publisher_checkpoints",
            "CHECKPOINT",
            "2027-05-03T00:00:10Z",
            {},
            fields={"local_source_id": "LOCAL", "sequences": [1]},
        )
    )
    actual, clock = collect(tmp_path, originals)
    result = logging(History(actual, as_of=clock))
    checkpoint = result["checkpoint_populations_before_selection"][0]
    lag = checkpoint["lag_observations"][0]
    assert lag["calculated_ingestion_lag_seconds"] == 9 and lag["claim_agrees"] is True
    assert len(checkpoint["retained_inventory_versions_not_overwritten"]) == (
        2 if other_scope == "NONE" else 3
    )
    if other_scope == "AMBIGUOUS":
        assert lag["effective_local_lag_limit_seconds"] is None
        assert lag["exceeds_effective_lag_limit"] is None
        assert checkpoint["lag_limit_status"] == "AMBIGUOUS_EFFECTIVE_LOCAL_DECLARATIONS"
    else:
        assert lag["effective_local_lag_limit_seconds"] == 6
        assert lag["exceeds_effective_lag_limit"] is True and result["exceptions"]
        assert checkpoint["effective_inventory_originals"][0]["version"] == 2
        assert len(checkpoint["effective_inventory_originals"]) == 1


def original_history():
    rows = []

    def add(family, role, record, at, d, **kwargs):
        r = native(family, role, record, at, d, **kwargs)
        rows.append(r)
        return r

    # A bad recorded configuration and a later correction are separate originals.
    actual = add(
        "configuration-history",
        "configuration_inventory",
        "LOCAL-TARGET",
        "2027-02-01T09:00:00Z",
        {
            "asset_id": "LOCAL-TARGET",
            "owner_id": "OWNER",
            "configuration": {"attempts": 3, "timeout_ms": 100, "max_total_ms": 200},
        },
    )
    desired = add(
        "configuration-history",
        "configuration_desired",
        "DESIRED",
        "2027-02-01T10:00:00Z",
        {"configuration": {"attempts": 2, "timeout_ms": 100, "max_total_ms": 200}},
    )
    add(
        "configuration-history",
        "configuration_drift",
        "DRIFT",
        "2027-02-02T09:00:00Z",
        {"matches_approved_desired": True},
        fields={
            "source_records": {
                "configuration_inventory": reference(actual["source"]),
                "configuration_desired": reference(desired["source"]),
            }
        },
    )
    corrected = add(
        "configuration-history",
        "configuration_inventory",
        "LOCAL-TARGET",
        "2027-02-03T09:00:00Z",
        {
            "asset_id": "LOCAL-TARGET",
            "owner_id": "OWNER",
            "configuration": {"attempts": 2, "timeout_ms": 100, "max_total_ms": 200},
        },
        version=2,
    )

    good_export = row(
        "configuration-runtime-history.configuration_export",
        "EXPORTED-BYTES",
        "2027-02-06T09:00:00Z",
        {"attempts": 2, "timeout_ms": 100, "max_total_ms": 200},
        version=2,
    )
    runtime = add(
        "configuration-runtime-history",
        "configuration_runtime",
        "LOCAL-RUNTIME",
        "2027-02-01T08:00:00Z",
        {},
        fields={"approved_sha256": good_export["source"]["sha256"]},
    )
    bad_export = row(
        "configuration-runtime-history.configuration_export",
        "EXPORTED-BYTES",
        "2027-02-05T09:00:00Z",
        {"attempts": 3, "timeout_ms": 100, "max_total_ms": 200},
    )
    for exported in (bad_export, good_export):
        exported["source"]["provenance"]["operational_metadata"] = {
            "target_id": "LOCAL-RUNTIME",
            "runtime_sha256": runtime["source"]["sha256"],
            "exported_at": exported["source"]["event_at"],
        }
        rows.append(exported)
    add(
        "configuration-history",
        "configuration_drift",
        "DRIFT",
        "2027-02-04T09:00:00Z",
        {"matches_approved_desired": True},
        fields={
            "source_records": {
                "configuration_inventory": reference(corrected["source"]),
                "configuration_desired": reference(desired["source"]),
            }
        },
        version=2,
    )

    # Independent component discovery precedes ownership/mapping, then refreshes.
    common = {"exercise_id": "SELECTED-TWO-COMPONENTS"}
    add(
        "sec001component",
        "component_inventory",
        "COMPONENT-CENSUS",
        "2027-03-01T09:00:00Z",
        {"component_ids": ["EDGE", "UNSUPPORTED"]},
        fields=common,
    )
    add(
        "sec001component",
        "ownership",
        "OWNERS",
        "2027-03-02T09:00:00Z",
        {"owner_ids": {"EDGE": "TECH"}},
        fields=common,
    )
    add(
        "sec001component",
        "control_mapping",
        "MAPPING",
        "2027-03-03T09:00:00Z",
        {"mapped_component_ids": ["EDGE"]},
        fields=common,
    )
    add(
        "sec001component",
        "challenge",
        "CHALLENGE",
        "2027-03-04T09:00:00Z",
        {"component_id": "UNSUPPORTED", "deployment_allowed": False},
        fields=common,
    )
    add(
        "sec001component",
        "component_inventory",
        "COMPONENT-CENSUS",
        "2027-03-05T09:00:00Z",
        {"component_ids": ["EDGE", "UNSUPPORTED"]},
        fields=common,
        version=2,
    )

    # Publisher census is independent of the incomplete first collector.
    add(
        "logging-history",
        "source_inventory",
        "REQUIRED-SOURCES",
        "2027-04-01T09:00:00Z",
        {
            "required_sources": [{"source_id": "LOCAL"}],
            "required_detections": ["DENY"],
            "local_max_ingestion_lag_seconds": 120,
        },
    )
    events = [
        {
            "sequence": i,
            "source_event_at": f"2027-04-02T09:00:0{i}Z",
            "authorization_decision": "DENY",
            "event_sha256": str(i) * 64,
        }
        for i in (1, 2)
    ]
    for i, e in enumerate(events, 1):
        add(
            "logging-history",
            "publisher_events",
            f"EVENT-{i}",
            f"2027-04-02T09:00:0{i}Z",
            {},
            fields={"local_source_id": "LOCAL", "event": e},
        )
    add(
        "logging-history",
        "ingestion_journal",
        "INGEST-1",
        "2027-04-02T09:00:11Z",
        {},
        fields={
            "local_source_id": "LOCAL",
            "event": events[0],
            "received_at": "2027-04-02T09:00:11Z",
            "ingestion_lag_seconds": 10,
        },
    )
    add(
        "logging-history",
        "publisher_checkpoints",
        "CHECKPOINT-INITIAL",
        "2027-04-02T10:00:00Z",
        {},
        fields={"local_source_id": "LOCAL", "sequences": [1, 2]},
    )
    add(
        "logging-history",
        "ingestion_journal",
        "INGEST-2",
        "2027-04-02T10:00:12Z",
        {},
        fields={
            "local_source_id": "LOCAL",
            "event": events[1],
            "received_at": "2027-04-02T10:00:12Z",
            "ingestion_lag_seconds": 3610,
        },
    )
    add(
        "logging-history",
        "publisher_checkpoints",
        "CHECKPOINT-LATER",
        "2027-04-02T11:00:00Z",
        {},
        fields={"local_source_id": "LOCAL", "sequences": [1, 2]},
    )

    # Prior decisions and actual implementation claims remain scope-separated.
    assessment = {
        k: "Neutral local model assessment"
        for k in (
            "size_complexity_capability",
            "infrastructure",
            "cost",
            "probability_and_criticality",
        )
    }
    add(
        "supplementalops",
        "risk_decision",
        "ADDRESSABLE",
        "2027-05-01T09:00:00Z",
        {
            "specification": "164.312(c)(2)",
            "assessment": {},
            "reasoned_treatment": "",
            "decision": "IMPLEMENT_IN_LOCAL_MODEL",
        },
    )
    decision = add(
        "supplementalops",
        "risk_decision",
        "ADDRESSABLE",
        "2027-05-02T09:00:00Z",
        {
            "specification": "164.312(c)(2)",
            "assessment": assessment,
            "reasoned_treatment": "Implement a bounded integrity setting on synthetic local bytes.",
            "decision": "IMPLEMENT_IN_LOCAL_MODEL",
        },
        version=2,
    )
    add(
        "supplementalops",
        "security_configuration",
        "SETTING",
        "2027-05-03T09:00:00Z",
        {
            "specification": "164.312(c)(2)",
            "approved_values": {"enabled": True},
            "observed_values": {"enabled": True},
            "applied_at": "2027-05-03T08:00:00Z",
            "implementation_decision_original": reference(decision["source"]),
            "activation_scope": "LOCAL_MODEL_ONLY",
        },
    )
    policy = add(
        "supplementalops",
        "identity_permission",
        "PERMISSION",
        "2027-06-01T09:00:00Z",
        {
            "model_policy": {
                "issuer": "NEUTRAL",
                "audience": "LOCAL",
                "principals": {
                    "HUMAN": {
                        "kind": "HUMAN",
                        "resources": ["LOCAL"],
                        "operations": ["read"],
                        "privilege_eligible": True,
                    }
                },
                "privilege_approvals": {},
            }
        },
    )
    operation = add(
        "supplementalops",
        "access_operation",
        "ACCESS",
        "2027-06-02T09:00:00Z",
        {
            "evaluated_at": "2027-06-02T08:00:00Z",
            "decision": "ALLOW",
            "request": {
                "issuer": "NEUTRAL",
                "audience": "LOCAL",
                "principal": "HUMAN",
                "resource": "LOCAL",
                "operation": "read",
                "expires_at": "2027-06-03T09:00:00Z",
                "mfa": False,
                "privileged": False,
            },
            "native_dependencies": [reference(policy["source"])],
        },
    )
    add(
        "supplementalops",
        "incident_intake",
        "INCIDENT",
        "2027-06-03T09:00:00Z",
        {
            "security_incident_definition_includes_attempts": True,
            "intake_type": "ATTEMPTED_UNAUTHORIZED_ACCESS",
            "triage": "Preserve attempted denial.",
            "response": "Investigate the synthetic request.",
            "native_dependencies": [reference(operation["source"])],
        },
    )
    add(
        "supplementalops",
        "workstation_inventory",
        "ASSIGNMENTS",
        "2027-07-01T09:00:00Z",
        {"resources": [{"asset_id": "LOCAL-TARGET", "serial": "SYNTHETIC-SERIAL"}]},
    )
    add(
        "supplementalops",
        "media_movement",
        "MOVE",
        "2027-07-02T09:00:00Z",
        {
            "asset_ids": ["LOCAL-TARGET"],
            "preserved_sha256": "c" * 64,
            "preserved_fixture": "/not-opened/marker.bin",
        },
    )
    add(
        "supplementalops",
        "integrity_operation",
        "ALTERATION-AUTHORITY",
        "2027-07-03T09:00:00Z",
        {
            "permitted_action": "Synthetic alteration",
            "expected_source_sha256": "c" * 64,
            "expected_authenticator": "d" * 64,
        },
    )

    # Two site conditions are recomputed from dated records, not a company PASS.
    add(
        "physicalsite",
        "site_zoning",
        "BOISE-ZONE",
        "2027-08-01T09:00:00Z",
        {"site": "BOISE", "zone": "CAGE", "entry_rule": "Escorted authorized visitors"},
    )
    add(
        "physicalsite",
        "badge_lifecycle",
        "BADGE",
        "2027-08-02T09:00:00Z",
        {"status": "ACTIVE", "site": "BOISE"},
    )
    add(
        "physicalsite",
        "badge_lifecycle",
        "REVOKE",
        "2027-08-04T09:00:00Z",
        {"badge": "BADGE", "controller_state": "ACTIVE", "effective_at": "2027-08-03T09:00:00Z"},
    )
    add(
        "physicalsite",
        "visitor_access",
        "VISITOR",
        "2027-08-05T09:00:00Z",
        {"valid_until": "2027-08-05T12:00:00Z", "zone": "CAGE"},
    )
    add(
        "physicalsite",
        "visitor_access",
        "ENTRY",
        "2027-08-06T09:00:00Z",
        {"authorization": "VISITOR", "controller_entry": "ALLOWED", "escort": "NONE"},
    )
    add(
        "physicalsite",
        "environment_monitor",
        "POINT",
        "2027-08-01T09:00:00Z",
        {"threshold_c": 30, "sample_interval_minutes": 5},
    )
    add(
        "physicalsite",
        "environment_monitor",
        "ALARM",
        "2027-08-07T09:00:00Z",
        {"point": "POINT", "observed_c": 33, "state": "ALARM"},
    )
    add(
        "physicalsite",
        "environment_monitor",
        "RECHECK",
        "2027-08-08T09:00:00Z",
        {"point": "POINT", "observed_c": 25, "local_alarm_cleared": True},
    )

    # Selected security calculations are fed only newly collected native bytes.
    model = "LOCAL_POLICY_AND_DATA_MODEL_ONLY; NO_LIVE_EXECUTION"
    tech = add(
        "sec005operated",
        "security_approval",
        "APPROVE-TECH-01",
        "2027-09-01T09:00:00Z",
        {},
        fields={"actor_id": "TECH", "operation_basis": model},
    )
    sec = add(
        "sec005operated",
        "security_approval",
        "APPROVE-SEC-01",
        "2027-09-02T09:00:00Z",
        {},
        fields={
            "actor_id": "SECURITY",
            "operation_basis": model,
            "source_refs": {"APPROVE-TECH-01": reference(tech["source"])},
        },
    )
    inv = add(
        "sec005operated",
        "security_inventory",
        "INVENTORY-SELECTED-01",
        "2027-09-03T09:00:00Z",
        {},
        fields={
            "operation_basis": model,
            "assets": [{"id": "EDGE"}, {"id": "OPS"}],
            "logical_interfaces": [{"id": "EGRESS"}],
        },
    )
    base = add(
        "sec005operated",
        "security_baseline",
        "BASELINE-01",
        "2027-09-04T09:00:00Z",
        {},
        fields={
            "operation_basis": model,
            "agent_required_asset_ids": ["EDGE", "OPS"],
            "selected_asset_ids": ["EDGE", "OPS"],
            "approved_rule_intents": ["RULE"],
        },
    )
    add(
        "sec005operated",
        "security_application",
        "APPLY-BASELINE-01",
        "2027-09-05T09:00:00Z",
        {},
        fields={
            "operation_basis": model,
            "actor_id": "OPERATOR",
            "applied_rule_intents": ["RULE"],
            "agent_covered_asset_ids": ["EDGE", "OPS"],
            "source_refs": {
                "APPROVE-SEC-01": reference(sec["source"]),
                "BASELINE-01": reference(base["source"]),
            },
        },
    )
    for name, day in [("PROBE-1", 6), ("PROBE-2", 7)]:
        add(
            "sec005operated",
            "security_probe",
            name,
            f"2027-10-{day:02}T09:00:00Z",
            {},
            fields={"operation_basis": model, "decision": "LOCAL_POLICY_MODEL_DENY"},
        )
    add(
        "sec005operated",
        "security_monitor",
        "MONITOR",
        "2027-10-08T09:00:00Z",
        {},
        fields={
            "operation_basis": model,
            "publisher_probe_record_ids": ["PROBE-1"],
            "received_probe_record_ids": ["PROBE-1"],
            "observed_agent_asset_ids": ["EDGE"],
        },
    )
    add(
        "sec005operated",
        "security_reconciliation",
        "REVIEW",
        "2027-10-09T09:00:00Z",
        {},
        fields={
            "operation_basis": model,
            "reviewed_probe_record_ids": ["PROBE-1"],
            "recorded_result": "COMPANY_SELECTED_PASS",
        },
    )
    for role, name, at, d in [
        (
            "vulnerability_inventory",
            "CENSUS-OCT-01",
            "2027-10-01",
            {"observed_asset_ids": ["EDGE"], "observed_count": 2},
        ),
        (
            "vulnerability_baseline",
            "BASELINE-OCT-01",
            "2027-10-02",
            {"covered_asset_ids": ["EDGE"]},
        ),
        (
            "vulnerability_schedule",
            "SCHEDULE-OCT-01",
            "2027-10-03",
            {"scheduled_asset_ids": ["EDGE"], "reported_asset_count": 2},
        ),
        (
            "vulnerability_advisory",
            "ADV-SH-SIM-2027-01",
            "2027-10-04",
            {"advisory": {"affected_asset_id": "EDGE"}},
        ),
        (
            "vulnerability_scan",
            "SCAN-OCT-01",
            "2027-10-05",
            {"observed_asset_ids": ["EDGE"], "finding_asset_ids": [], "reported_count": 2},
        ),
        ("vulnerability_reconciliation", "RECON-OCT-01", "2027-10-06", {}),
        (
            "vulnerability_scan",
            "DETECTION",
            "2027-11-01",
            {"observed_asset_ids": ["EDGE", "OPS"], "finding_asset_ids": ["EDGE"]},
        ),
        ("vulnerability_triage", "TRIAGE", "2027-11-02", {"asset_id": "EDGE"}),
        ("vulnerability_approval", "APPROVAL", "2027-11-03", {"asset_id": "EDGE"}),
        ("vulnerability_remediation", "FIX", "2027-11-04", {"asset_id": "EDGE"}),
        (
            "vulnerability_scan",
            "RETEST",
            "2027-11-05",
            {"observed_asset_ids": ["EDGE", "OPS"], "finding_asset_ids": []},
        ),
    ]:
        add(
            "sec003vuln",
            role,
            name,
            at + "T09:00:00Z",
            d,
            fields={
                "operation_basis": model,
                "actor_id": "SOURCE_REVIEWER",
                "upstream_native_refs_available_at_event": {
                    "inventory": reference(inv["source"]),
                    "baseline": reference(base["source"]),
                },
            },
        )
    return rows


def task(outputs, control, clause):
    return next(r for r in outputs if r["task_id"] == f"TASK-SH-{control}-corporate-{clause}")


def test_all_38_exact_inspections_use_actual_collected_originals_and_distinct_facets(tmp_path):
    rows, clock = collect(tmp_path, original_history())
    scratch = tmp_path / "must-not-be-created"
    outputs = examine(rows, as_of=clock, scratch_root=scratch)
    assert len(outputs) == len(contracts()) == 38
    assert [r["task_id"] for r in outputs] == [t["task_id"] for t in task_plan()]
    assert (
        len({json.dumps(r["result"]["examined_attributes"], sort_keys=True) for r in outputs}) == 38
    )
    assert all(r["disposition"]["conclusion"] in {"FAIL", "LIMITATION"} for r in outputs)
    assert not scratch.exists()
    cfg = task(outputs, "CFG-002", "TOE")["result"]["examined_attributes"][
        "dated_drift_and_export_occurrences"
    ]
    assert [c["equal_embedded_configuration"] for c in cfg["embedded_drift_comparisons"]] == [
        False,
        True,
    ]
    assert cfg["exceptions"][0]["actual_retry"]["within_local_limit"] is False
    assert [
        e["retry_reperformance"]["within_local_limit"]
        for e in cfg["actual_raw_export_reperformance"]
    ] == [False, True]
    assert all(not e["actual_target_opened"] for e in cfg["actual_raw_export_reperformance"])
    sec3 = task(outputs, "SEC-003", "CHECK-SOC2:CC7.1")["result"]["examined_attributes"][
        "accepted_pure_selected_inventory_scan_baseline_reperformance"
    ]
    assert sec3["omitted_scan_assets"] == ["OPS"]
    assert sec3["causal_discrepancy"]["disposition"] == "UNEXPLAINED_FALSE_CLEAN"
    assert not sec3["actual_scanner_execution"]
    sec5 = task(outputs, "SEC-005", "TOE")["result"]["examined_attributes"][
        "dated_publisher_monitor_review_and_exception_history"
    ]
    assert sec5["monitor_reconciliations"][0]["unreceived_publisher_ids"] == ["PROBE-2"]
    assert sec5["company_review_reconciliations"][0]["unreviewed_publisher_ids"] == ["PROBE-2"]
    assert not sec5["actual_packets_or_executable_execution"]
    intake = task(outputs, "SEC-006", "CHECK-SOC2:CC7.3")["result"]["examined_attributes"][
        "original_impact_attempted_access_and_response_attributes"
    ]
    assert (
        intake["dated_intakes"][0]["bounded_rule_reperformance"]
        == "ATTEMPT_INCLUDED_BY_DECLARED_LOCAL_INTAKE_RULE"
    )
    assert not intake["dated_intakes"][0]["enterprise_severity_classification_reperformed"]
    for output in outputs:
        assert output["performed"] == contracts()[output["task_id"]]["performed"]
        assert set(output["artifact_ids"]) <= {r["artifact_id"] for r in rows}
        assert all(o["evidence"] for o in output["observations"])
        for label in ("EXACT-TASK-ATTRIBUTES", "EXACT-NATIVE-SUPPORT"):
            parts = [
                o
                for o in output["observations"]
                if o["id"] == label or o["id"].startswith(label + "-CITE-")
            ]
            if not parts:
                continue
            group = parts[0]["facts"]["citation_group"]
            assert [p["id"] for p in parts] == group["all_citation_part_ids"]
            assert len(parts) == group["citation_part_count"]
            assert {e["artifact_id"] for p in parts for e in p["evidence"]} == set(
                output["artifact_ids"]
            )
            assert all(len(p["evidence"]) <= 20 and len(p["id"]) <= 128 for p in parts)
            assert all(
                p["facts"]["citation_group"]["aggregate_observation_id"] == label for p in parts
            )


def test_historical_component_gap_and_logging_gap_remain_after_later_repair(tmp_path):
    rows, clock = collect(tmp_path, original_history())
    history = History(rows, as_of=clock)
    comp = component_lifecycle(history)
    assert comp["populations"][0]["unowned"] == ["EDGE", "UNSUPPORTED"]
    assert comp["populations"][1]["unowned"] == ["UNSUPPORTED"]
    logged = logging(history)["checkpoint_populations_before_selection"]
    assert [p["unreceived_publisher_sequences"] for p in logged] == [[2], []]
    assert logged[1]["lag_observations"][1]["calculated_ingestion_lag_seconds"] == 3610
    assert logged[1]["lag_observations"][1]["exceeds_effective_lag_limit"]
    assert not logged[1]["full_period_or_clock_synchronization_tested"]
    authority = approvals(history)["application_authority_attributes"][0]
    assert authority["distinct_named_approvers"] and authority["operator_distinct_from_approvers"]
    assert {s["record"] for s in authority["exact_prior_approval_originals"]} == {
        "APPROVE-TECH-01",
        "APPROVE-SEC-01",
    }
    sites = physical_conditions(history)
    assert len(sites["exceptions"]) == 3
    assert [
        p["recorded_threshold_breach"] for p in sites["environmental_threshold_occurrences"]
    ] == [True, False]
    assert not sites["provider_perimeter_and_full_site_population_established"]


def test_missing_addressable_assessment_does_not_become_valid_from_later_setting(tmp_path):
    rows, clock = collect(tmp_path, original_history())
    result = addressable(History(rows, as_of=clock))
    case = next(
        c
        for c in result["authored_baseline_22_specification_census"]
        if c["specification"] == "164.312(c)(2)"
    )
    assert [r["specific_reasoning_present"] for r in case["decision_versions"]] == [False, True]
    assert not case["decision_versions"][0]["exact_implemented_setting_versions"]
    assert case["decision_versions"][1]["exact_implemented_setting_versions"][0][
        "approved_observed_equal"
    ]
    assert (
        len(result["missing_specifications"]) == 21
        and not result["actual_legal_applicability_accepted"]
    )


@pytest.mark.parametrize(
    "malformation", ["version_bool", "bytes_bool", "future_receipt", "native_role"]
)
def test_actual_receipt_role_and_clock_are_not_replaced_by_cached_documents(tmp_path, malformation):
    originals = [
        native(
            "configuration-history",
            "configuration_inventory",
            "INV",
            "2027-02-01T09:00:00Z",
            {"asset_id": "LOCAL"},
        )
    ]
    rows, clock = collect(tmp_path, originals)
    row0 = rows[0]
    row0["document"] = {"attacker_cached_valid_result": True}
    if malformation == "version_bool":
        row0["source"]["version"] = True
    elif malformation == "bytes_bool":
        row0["receipt"]["content_bytes"] = True
    elif malformation == "future_receipt":
        row0["receipt"]["simulated_as_of"] = "2029-01-01T09:00:00Z"
    else:
        row0["logical_system"] = "configuration_desired"
    with pytest.raises(ProcedureError):
        History(rows, as_of=clock)


@pytest.mark.parametrize("late", [False, True])
def test_wrong_native_role_or_late_original_cannot_supply_config_desired(tmp_path, late):
    original = native(
        "configuration-history",
        "configuration_desired" if late else "meeting_note",
        "DESIRED",
        "2027-02-05T09:00:00Z" if late else "2027-02-01T09:00:00Z",
        {"configuration": {"attempts": 2, "timeout_ms": 10, "max_total_ms": 20}},
    )
    drift = native(
        "configuration-history",
        "configuration_drift",
        "DRIFT",
        "2027-02-03T09:00:00Z",
        {},
        fields={"source_records": {"configuration_desired": reference(original["source"])}},
    )
    rows, clock = collect(tmp_path, [original, drift])
    result = task(examine(rows, as_of=clock, scratch_root=tmp_path / "unused"), "CFG-002", "TOE")[
        "result"
    ]["examined_attributes"]["dated_drift_and_export_occurrences"]
    assert result["embedded_drift_comparisons"][0]["desired_original_status"] == (
        "ORIGINAL_UNAVAILABLE_AT_COMPANY_OCCURRENCE" if late else "ACTUAL_NATIVE_ROLE_DIFFERS"
    )


def test_future_recorded_access_evaluation_is_unperformed_before_policy_arithmetic(tmp_path):
    originals = original_history()
    operation = next(
        r for r in originals if r["source"]["system"] == "supplementalops.access_operation"
    )
    body = json.loads(operation["content"])
    body["detail"]["evaluated_at"] = "2028-01-02T09:00:00Z"
    reseal_document(operation, body)
    # Delete its dependent intake: retaining its old exact hash would be a different test.
    originals = [r for r in originals if r["source"]["system"] != "supplementalops.incident_intake"]
    rows, clock = collect(tmp_path, originals)
    permission = permission_checks(History(rows, as_of=clock))["selected_attempts"][0]
    assert permission["status"] == "RECORDED_ACCESS_EVALUATION_TIME_UNAVAILABLE"
    assert "independent_local_decision" not in permission


def test_actual_cached_document_is_ignored_and_missing_trace_does_not_stop_other_tasks(tmp_path):
    originals = original_history()
    originals = [r for r in originals if r["source"]["record"] != "FIX"]
    rows, clock = collect(tmp_path, originals)
    modified = copy.deepcopy(rows)
    for r in modified:
        r["document"] = {"fake_latest_complete": True}
    results = examine(modified, as_of=clock, scratch_root=tmp_path / "unused")
    assert len(results) == 38
    sec3 = task(results, "SEC-003", "CHECK-SOC2:CC7.1")["result"]["examined_attributes"][
        "accepted_pure_selected_inventory_scan_baseline_reperformance"
    ]
    assert sec3["status"] == "SELECTED_TRACE_UNPERFORMED"
    assert not sec3["actual_execution_performed"]
    assert (
        task(results, "CFG-002", "IMPLEMENTATION")["result"]["examined_attributes"][
            "exact_native_embedded_drift"
        ][0]["equal_embedded_configuration"]
        is False
    )


def test_native_transfer_path_traces_indirect_recipient_and_endpoint_mismatch(tmp_path):
    digest = "a" * 64
    rows = []

    def add(role, record, day, d, links=None):
        r = native(
            "sec001transfer",
            role,
            record,
            f"2027-05-{day:02}T09:00:00Z",
            {"payload_sha256": digest, **d},
            fields={
                "actor_id": "OPERATOR" if role == "transfer_operations" else "AUTHORITY",
                "record_links": {k: reference(v["source"]) for k, v in (links or {}).items()},
            },
        )
        rows.append(r)
        return r

    purpose = add("transfer_authority", "PURPOSE", 1, {"purpose": "SYNTHETIC_TEST_ONLY"})
    recipient = add(
        "transfer_authority",
        "RECIPIENT",
        2,
        {"recipient_id": "RIGHT", "approved_fixture_endpoint": "synthetic:approved"},
    )
    channel = add("security_path", "CHANNEL", 3, {"channel_fixture": "SYNTHETIC_TLS"})
    endpoint = add("security_path", "ENDPOINT", 4, {"endpoint_fixture": "synthetic:wrong"})
    request = add(
        "transfer_operations",
        "REQUEST",
        5,
        {"self_approval_allowed": False},
        {"PURPOSE": purpose, "RECIPIENT": recipient, "CHANNEL": channel, "ENDPOINT": endpoint},
    )
    add(
        "transfer_operations",
        "OBSERVATION",
        6,
        {"recipient_fixture": "WRONG"},
        {"REQUEST": request, "ENDPOINT": endpoint},
    )
    actual, clock = collect(tmp_path, rows)
    result = task(
        examine(actual, as_of=clock, scratch_root=tmp_path / "unused"),
        "SEC-001",
        "CHECK-SOC2:CC6.7",
    )["result"]["examined_attributes"]["purpose_recipient_channel_endpoint_and_receipt_trace"]
    operation = result["selected_operations"][1]
    assert set(operation["declared_path_status"].values()) == {"EXACT_AVAILABLE_ORIGINAL"}
    assert operation["declared_payload_digests_agree"]
    assert operation["recorded_endpoint_matches_recipient_authorization"] is False
    assert operation["observed_recipient_matches_authority"] is False
    assert not operation["real_network_transfer_reperformed"] and len(result["exceptions"]) == 2


def test_symbolic_network_and_inert_digest_checks_do_not_execute_company_code(tmp_path):
    sentinel = tmp_path / "company-script-executed"
    rule = native(
        "sec005",
        "local_boundary_definition",
        "RULE",
        "2027-09-01T09:00:00Z",
        {
            "intended_permitted_interface_ids": ["APPROVED"],
            "staged_rule_permitted_interface_ids": ["APPROVED", "UNAUTHORIZED"],
        },
    )
    decision = native(
        "sec005",
        "local_boundary_decision",
        "PROBE",
        "2027-09-02T09:00:00Z",
        {
            "requested_interface_id": "UNAUTHORIZED",
            "decision": "ALLOW",
            "stored_sql": "DROP TABLE workpapers",
            "company_script": f"open({str(sentinel)!r}, 'w').write('bad')",
        },
        fields={"source_previous": reference(rule["source"])},
    )
    executable = native(
        "sec005",
        "local_endpoint_decision",
        "EXECUTABLE",
        "2027-09-02T09:00:00Z",
        {"fixture_sha256": "a" * 64, "approved_fixture_sha256": "b" * 64, "decision": "ALLOW"},
    )
    rows, clock = collect(tmp_path, [rule, decision, executable])
    results = examine(rows, as_of=clock, scratch_root=tmp_path / "unused")
    result = task(results, "SEC-005", "CHECK-SOC2:CC6.6")["result"]["examined_attributes"][
        "approved_intended_vs_staged_interface_attempts"
    ]
    assert result["symbolic_interface_attempts"][0]["rule_drift"]
    assert result["symbolic_interface_attempts"][0]["intended_permitted"] is False
    assert result["symbolic_interface_attempts"][0]["staged_permitted"] is True
    assert result["inert_digest_decisions"][0]["declared_fixture_digest_equals_approved"] is False
    assert not sentinel.exists() and len(result["exceptions"]) == 2


def test_restricted_pointer_never_rebases_to_available_desired_original(tmp_path):
    desired = native(
        "configuration-history",
        "configuration_desired",
        "DESIRED",
        "2027-02-01T09:00:00Z",
        {"configuration": {"attempts": 2, "timeout_ms": 10, "max_total_ms": 20}},
    )
    ref = {**reference(desired["source"]), "status": "RESTRICTED_CROSS_BRANCH_DEPENDENCY"}
    drift = native(
        "configuration-history",
        "configuration_drift",
        "DRIFT",
        "2027-02-03T09:00:00Z",
        {},
        fields={"source_records": {"configuration_desired": ref}},
    )
    actual, clock = collect(tmp_path, [desired, drift])
    history = History(actual, as_of=clock)
    assert history.joins[0]["status"] == "RESTRICTED_REFERENCE_NOT_REBASED"
    assert history.joins[0]["target"] is None
    result = task(
        examine(actual, as_of=clock, scratch_root=tmp_path / "unused"),
        "SEC-001",
        "CHECK-SOC2:CC6.7",
    )
    assert result["observations"][0]["status"] == "SUPPORT_UNAVAILABLE"
    assert not result["result"]["required_task_attribute_population_available"]
    assert not result["result"]["selected_native_population_before_selection"]
    assert result["result"]["acquisition_context_witnesses"]


def test_native_census_bool_cannot_substitute_for_integer_count(tmp_path):
    original = native(
        "sec003vuln",
        "vulnerability_inventory",
        "CENSUS",
        "2027-10-01T09:00:00Z",
        {"observed_asset_ids": ["EDGE"], "observed_count": True},
        fields={"operation_basis": "LOCAL_POLICY_AND_DATA_MODEL_ONLY"},
    )
    actual, clock = collect(tmp_path, [original])
    with pytest.raises(ProcedureError, match="Strict native vulnerability census/count"):
        examine(actual, as_of=clock, scratch_root=tmp_path / "unused")


@pytest.mark.parametrize("received_at", [None, "2028-01-01T09:00:00Z"])
def test_null_or_future_recorded_ingestion_time_never_receives_lag_credit(tmp_path, received_at):
    event = {"sequence": 1, "source_event_at": "2027-09-01T09:00:00Z"}
    originals = [
        native(
            "logging-history",
            "publisher_events",
            "EVENT",
            "2027-09-01T09:00:00Z",
            {},
            fields={"event": event, "local_source_id": "LOCAL"},
        ),
        native(
            "logging-history",
            "ingestion_journal",
            "INGEST",
            "2027-09-02T09:00:00Z",
            {},
            fields={
                "event": event,
                "local_source_id": "LOCAL",
                "received_at": received_at,
                "ingestion_lag_seconds": 86400,
            },
        ),
        native(
            "logging-history",
            "publisher_checkpoints",
            "CUT",
            "2027-09-03T09:00:00Z",
            {},
            fields={"local_source_id": "LOCAL", "sequences": [1]},
        ),
    ]
    actual, clock = collect(tmp_path, originals)
    result = logging(History(actual, as_of=clock))
    observed = result["checkpoint_populations_before_selection"][0]["lag_observations"][0]
    assert not observed["observed_interval_chronology_supported"]
    assert observed["calculated_ingestion_lag_seconds"] is None
    assert observed["claim_agrees"] is None and result["exceptions"]


def test_expired_privilege_service_resource_and_temporary_peer_checks_are_independent(tmp_path):
    policy = native(
        "supplementalops",
        "identity_permission",
        "POLICY",
        "2027-09-01T09:00:00Z",
        {
            "model_policy": {
                "issuer": "LOCAL",
                "audience": "BOUNDARY",
                "principals": {
                    "HUMAN": {
                        "kind": "HUMAN",
                        "resources": ["SECRET"],
                        "operations": ["read"],
                        "privilege_eligible": True,
                    },
                    "SERVICE": {
                        "kind": "SERVICE",
                        "resources": ["RECOVERY"],
                        "operations": ["restore"],
                        "privilege_eligible": False,
                    },
                },
                "privilege_approvals": {
                    "APPROVAL": {
                        "principal": "HUMAN",
                        "resource": "SECRET",
                        "operation": "read",
                        "approved_by": "APPROVER",
                        "challenged_by": "CHALLENGER",
                        "valid_from": "2027-09-01T09:00:00Z",
                        "valid_until": "2027-09-03T09:00:00Z",
                    }
                },
                "temporary_restrictions": {
                    "HUMAN": {
                        "valid_from": "2027-09-01T09:00:00Z",
                        "valid_until": "2027-09-10T09:00:00Z",
                        "permitted_peer_initiators": ["CHALLENGER"],
                    }
                },
            }
        },
    )
    originals = [policy]
    for name, day, principal, operation, resource, privileged, initiator in [
        ("EXPIRED-PRIVILEGE", 4, "HUMAN", "read", "SECRET", True, "CHALLENGER"),
        ("SERVICE-WRONG-RESOURCE", 4, "SERVICE", "read", "SECRET", False, "CHALLENGER"),
        ("SELF-INITIATED", 2, "HUMAN", "read", "SECRET", True, "HUMAN"),
        ("VALID-PEER", 2, "HUMAN", "read", "SECRET", True, "CHALLENGER"),
    ]:
        originals.append(
            native(
                "supplementalops",
                "access_operation",
                name,
                f"2027-09-{day:02}T10:00:00Z",
                {
                    "evaluated_at": f"2027-09-{day:02}T09:30:00Z",
                    "decision": "ALLOW",
                    "request": {
                        "issuer": "LOCAL",
                        "audience": "BOUNDARY",
                        "principal": principal,
                        "operation": operation,
                        "resource": resource,
                        "mfa": True,
                        "privileged": privileged,
                        "approval": "APPROVAL",
                        "initiated_by": initiator,
                        "expires_at": "2027-09-06T09:00:00Z",
                    },
                    "native_dependencies": [reference(policy["source"])],
                },
            )
        )
    actual, clock = collect(tmp_path, originals)
    result = permission_checks(History(actual, as_of=clock))
    attempts = result["selected_attempts"]
    assert [r["independent_local_decision"] for r in attempts] == ["DENY", "DENY", "DENY", "ALLOW"]
    assert attempts[0]["boundary_checks"]["privileged_approval"] is False
    assert attempts[1]["boundary_checks"]["resource_permission"] is False
    assert attempts[2]["boundary_checks"]["temporary_peer_initiation"] is False
    assert len(result["exceptions"]) == 3 and not attempts[-1]["actual_identity_provider_login"]


def test_future_inventory_and_assignment_cannot_repair_earlier_discovery_or_movement(tmp_path):
    originals = [
        native(
            "configuration-history",
            "configuration_inventory",
            "NEW-TARGET",
            "2027-09-05T09:00:00Z",
            {"asset_id": "NEW"},
        ),
        native(
            "sec001component",
            "component_inventory",
            "DISCOVERED",
            "2027-09-01T09:00:00Z",
            {"component_ids": ["NEW"]},
            fields={"exercise_id": "NEUTRAL-SELECTED"},
        ),
        native(
            "supplementalops",
            "workstation_inventory",
            "ASSIGNMENT",
            "2027-09-05T09:00:00Z",
            {"resources": [{"asset_id": "NEW"}]},
        ),
        native(
            "supplementalops", "media_movement", "MOVE", "2027-09-02T09:00:00Z", {"assets": ["NEW"]}
        ),
    ]
    actual, clock = collect(tmp_path, originals)
    history = History(actual, as_of=clock)
    assert configuration(history)["independent_selected_discoveries"][0][
        "outside_configuration_inventory"
    ] == ["NEW"]
    moved = integrity_movement(history)["movement_and_reuse_versions"][0]
    assert moved["unjoined_assignment_assets"] == ["NEW"]
    assert not moved["effective_assignment_originals"]
