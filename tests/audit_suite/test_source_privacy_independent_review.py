"""Independent neutral documentary and real retained-byte boundary challenges."""

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from enterprise.audit_suite.artifacts import Artifacts
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.source_privacy_execution import gate, retained, sample_batches
from enterprise.audit_suite.source_privacy_methods import examine

AS_OF = "2028-01-15T09:00:00Z"


def native_record(system, record, hour, details, day="2027-09-21"):
    at = datetime.fromisoformat(f"{day}T{hour:02d}:00:00+00:00")
    body = {
        "payload_bytes": 0,
        "real_phi_payload": False,
        "real_world_processing_or_transfer": False,
        "event_at": at.isoformat(),
        "available_at": (at + timedelta(minutes=10)).isoformat(),
        "service_id": "SERVICE-ONE",
        "dataset_id": "DATASET-ONE",
        "customer_id": "CUSTOMER-ONE",
        "contracting_entity_id": "ENTITY-ONE",
        "dependencies": [],
        **details,
    }
    content = json.dumps(body, sort_keys=True).encode()
    source = {
        "company": "NEUTRAL",
        "branch": "selected",
        "system": f"privacyops.{system}",
        "record": record,
        "version": 1,
        "event_at": body["event_at"],
        "available_at": body["available_at"],
        "imported_at": "2026-10-01T00:00:00Z",
        "sha256": hashlib.sha256(content).hexdigest(),
    }
    return {
        "source": source,
        "receipt": {"source": deepcopy(source)},
        "retained_bytes": content,
        "artifact_sha256": source["sha256"],
        "artifact_id": f"ART-{record}",
        "content_type": "application/json",
        "logical_family": "privacyops",
        "logical_system": system,
    }


def history(delivered=True):
    common = {"case_id": "case-independent", "recipient_id": "RECIPIENT-ONE"}
    decision = "PERMIT" if delivered else "HOLD"
    return [
        native_record(
            "privacy_request",
            "REQ-INDEPENDENT",
            9,
            {**common, "inlet_sequence": 1, "route": "token-route"},
        ),
        native_record(
            "privacy_customer_decision",
            "CUSTOMER-INDEPENDENT",
            10,
            {**common, "decision": decision},
        ),
        native_record(
            "privacy_gate_decision",
            "GATE-INDEPENDENT",
            11,
            {**common, "decision": decision, "allowed_scope": ["token"] if delivered else []},
        ),
        native_record(
            "privacy_release",
            "RELEASE-INDEPENDENT",
            12,
            {
                **common,
                "execution_status": "DELIVERED" if delivered else "WITHHELD",
                "released_scope": ["token"] if delivered else [],
            },
        ),
        native_record(
            "privacy_receipt",
            "RECEIPT-INDEPENDENT",
            13,
            {
                **common,
                "status": "RECIPIENT_ACKNOWLEDGED" if delivered else "NO_DELIVERY",
                "copy_in_recipient_scope": delivered,
            },
        ),
        native_record(
            "privacy_reconciliation",
            "CLOSE-INDEPENDENT",
            8,
            {
                "period": {"start": "2027-09-01T00:00:00Z", "end": "2027-09-30T23:59:59Z"},
                "case_ids": ["case-independent"],
                "inlet_sequence_first": 1,
                "inlet_sequence_last": 1,
                "inlet_sequence_gaps": [],
                "customer_decision_count": 1,
                "counsel_gate_count": 1,
                "execution_journal_count": 1,
                "delivery_status_count": 1,
                "delivered_count": int(delivered),
                "withheld_count": int(not delivered),
                "delivery_authority_mismatch_count": 0,
            },
            day="2027-10-01",
        ),
    ]


def change(row, **fields):
    body = json.loads(row["retained_bytes"])
    body.update(fields)
    raw = json.dumps(body, sort_keys=True).encode()
    row["retained_bytes"] = raw
    row["source"]["sha256"] = hashlib.sha256(raw).hexdigest()
    row["source"]["event_at"] = body["event_at"]
    row["source"]["available_at"] = body["available_at"]
    row["artifact_sha256"] = row["source"]["sha256"]
    row["receipt"]["source"] = deepcopy(row["source"])


def test_permission_published_after_delivery_is_not_current_even_without_pointer():
    rows = history()
    change(rows[2], event_at="2027-09-22T11:00:00+00:00", available_at="2027-09-22T11:10:00+00:00")
    result = examine(rows, as_of=AS_OF)
    assert result["recorded_mismatch_case_ids"] == ["case-independent"]
    assert any(
        v["source_system"] == "privacy_gate_decision" and v["consumer_system"] == "privacy_release"
        for v in result["cases"][0]["causal_availability_violations"]
    )


@pytest.mark.parametrize(
    "field", ["service_id", "dataset_id", "customer_id", "contracting_entity_id"]
)
def test_permission_for_another_business_boundary_is_not_reused(field):
    rows = history()
    change(rows[2], **{field: "OTHER"})
    with pytest.raises(ProcedureError, match="scopes differ"):
        examine(rows, as_of=AS_OF)


def test_native_request_cannot_be_relabelled_as_gate():
    rows = history()
    rows[2]["source"]["system"] = "privacyops.privacy_request"
    rows[2]["receipt"]["source"] = deepcopy(rows[2]["source"])
    with pytest.raises(ProcedureError, match="actual native system"):
        examine(rows, as_of=AS_OF)


def test_unknown_receipt_status_is_not_known_nondelivery():
    rows = history(False)
    change(rows[4], status="EXPORT_STATUS_UNDETERMINED")
    result = examine(rows, as_of=AS_OF)
    assert result["cases"][0]["recipient_status_known"] is False
    assert "RECIPIENT_STATUS_UNDETERMINED" in result["cases"][0]["recorded_mismatches"]


def test_string_scope_is_not_an_authorized_set_of_characters():
    rows = history()
    change(rows[2], allowed_scope="token")
    change(rows[3], released_scope="token")
    with pytest.raises(ProcedureError, match="string-list"):
        examine(rows, as_of=AS_OF)


def test_numeric_copy_flag_is_not_a_genuine_recipient_boolean():
    rows = history()
    change(rows[4], copy_in_recipient_scope=1)
    with pytest.raises(ProcedureError, match="Genuine boolean"):
        examine(rows, as_of=AS_OF)


def test_missing_gate_preserves_unknown_authority():
    rows = [r for r in history() if r["logical_system"] != "privacy_gate_decision"]
    result = examine(rows, as_of=AS_OF)
    assert result["delivery_authority_unknown_case_ids"] == ["case-independent"]
    assert result["recomputed_counts"]["delivery_authority_mismatch_count"] is None
    assert result["selected_population_corroborated"] is False


def test_observed_case_census_is_derived_for_two_arbitrary_cases():
    first, second = history(), history()
    for row in second[:-1]:
        row["source"]["record"] += "-SECOND"
        row["artifact_id"] += "-SECOND"
        change(row, case_id="separate-case")
    change(second[0], inlet_sequence=2)
    change(
        first[-1],
        case_ids=["case-independent", "separate-case"],
        inlet_sequence_last=2,
        customer_decision_count=2,
        counsel_gate_count=2,
        execution_journal_count=2,
        delivery_status_count=2,
        delivered_count=2,
    )
    result = examine(first[:-1] + second[:-1] + [first[-1]], as_of=AS_OF)
    assert result["selected_request_count"] == 2
    assert result["selected_population_corroborated"] is True
    assert result["recorded_mismatch_case_ids"] == []


def retained_engine(tmp_path, raw):
    artifacts = Artifacts(tmp_path)
    artifact = artifacts.retain_company(
        "neutral-engagement",
        "native.json",
        raw,
        source={"kind": "COLLECTED_COMPANY_SOURCE"},
        coverage={},
    )
    engine = SimpleNamespace(
        artifacts=artifacts,
        store=SimpleNamespace(get=lambda actor, engagement: {"artifacts": [artifact]}),
    )
    row = {
        "artifact_id": artifact["id"],
        "artifact_sha256": artifact["sha256"],
        "source": {"sha256": artifact["sha256"]},
        "document": {"cached_answer": "WRONG"},
    }
    return engine, row


def test_runner_reloads_actual_artifact_and_discards_cached_document(tmp_path):
    engine, row = retained_engine(tmp_path, b'{"actual_native_record":true}')
    actual = retained(engine, "auditor", "neutral-engagement", [row])[0]
    assert "document" not in actual
    assert json.loads(actual["retained_bytes"]) == {"actual_native_record": True}


def test_runner_cannot_consume_quarantined_original(tmp_path):
    engine, row = retained_engine(tmp_path, b"not-json")
    with pytest.raises(ProcedureError, match="Quarantined"):
        retained(engine, "auditor", "neutral-engagement", [row])


def test_runner_rejects_independent_review_changes_required(tmp_path):
    path = tmp_path / "REVIEW.json"
    path.write_text(
        json.dumps(
            {
                "schema": "SH_PRIVACY_METHOD_INDEPENDENT_REVIEW_V2",
                "verdict": "CHANGES_REQUIRED",
                "source_execution_authorized": True,
            }
        )
    )
    path.chmod(0o600)
    with pytest.raises(ProcedureError, match="independently reviewed"):
        gate(path, hashlib.sha256(path.read_bytes()).hexdigest(), method=True)


def test_citation_batches_preserve_all_23_performed_items_with_five_originals_each():
    observed = [
        (
            str(i),
            {},
            "OBSERVED",
            [{"artifact_id": f"ART-{i}-{j}", "retained_bytes": b"native"} for j in range(5)],
        )
        for i in range(23)
    ]
    batches = sample_batches(observed)
    assert [len(b) for b in batches] == [20, 3]
    assert [item[0] for b in batches for item in b] == [str(i) for i in range(23)]
    assert all(len({r["artifact_id"] for item in b for r in item[3]}) <= 100 for b in batches)
