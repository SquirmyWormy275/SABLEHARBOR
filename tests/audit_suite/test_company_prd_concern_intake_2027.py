"""Selected customer concern is native, held, and historically honest."""

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_prd_concern_intake_2027 as source
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE_REPOSITORY = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


@pytest.fixture
def run(tmp_path: Path) -> Path:
    tmp_path.chmod(0o700)
    destination = tmp_path / "source"
    source.create(destination, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)
    return destination


def test_selected_concern_preserves_held_response_and_open_messy_history(run: Path) -> None:
    assert source.verify(run, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)[
        "native_version_counts"
    ] == {"CLEAN": 8, "MESSY": 13}
    receipt = json.loads((run / "RECEIPT.json").read_text())
    assert receipt["native_version_counts"] == {"CLEAN": 8, "MESSY": 13}
    assert receipt["local_open_exception_counts"] == {"CLEAN": 0, "MESSY": 1}
    assert receipt["real_external_messages_sent"] == 0
    assert receipt["fictional_accepted_deliveries"] == 0
    assert receipt["customer_acknowledgments"] == 0
    assert all(
        receipt[key] is False
        for key in (
            "selected_claimant_verified",
            "actual_phi_processing",
            "source_complete",
            "fresh_audit_pair_created",
            "audit_task_credit",
        )
    )
    assert {k: len(v) for k, v in receipt["upstream_original_refs"].items()} == {
        "CLEAN": 5,
        "MESSY": 7,
    }
    assert all(
        set(ref) == set(source.ORIGINAL_FIELDS)
        for refs in receipt["upstream_original_refs"].values()
        for ref in refs.values()
    )
    context = source._context(REPOSITORY, PRIVATE_REPOSITORY)
    for side in source.BRANCHES:
        rows = [json.loads(item["content"]) for item in source._rows(context, side)]
        assert all(row["real_external_messages_sent"] == 0 for row in rows)
        assert all(row["company_outbound_delivery_accepted"] is False for row in rows)
        assert all(row["separate_customer_acknowledgment_exists"] is False for row in rows)
        assert all(row["authored_communication_clause_satisfied"] is False for row in rows)
        assert all(row["claimant_customer_identity_verified"] is False for row in rows)
        assert rows[0]["upstream_original_refs"] == context["refs"][side]
        for earlier, later in zip(rows, rows[1:], strict=False):
            assert earlier["event_at"] < later["event_at"]
            assert (
                later["previous_native_content"]["sha256"]
                == hashlib.sha256(
                    json.dumps(earlier, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()
            )
    by_record = {
        item["record"]: json.loads(item["content"]) for item in source._rows(context, "MESSY")
    }
    assert (
        "SUPPORT_RECOVERY" not in by_record["MATRIX-INITIAL"]["selected_internal_recipient_roles"]
    )
    assert by_record["FALSE-CLOSE"]["claimed_selected_routing_complete"] is True
    assert by_record["FALSE-CLOSE"]["status"] == "FALSE_CLEAN"
    assert by_record["DENY-01"]["status"] == "DENIED_NO_SEND"
    assert by_record["RECON-01"]["historical_exception_open"] is True
    assert "SUPPORT_RECOVERY" in by_record["MATRIX-CORRECTED"]["selected_internal_recipient_roles"]
    with sqlite3.connect(
        (run / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        assert [
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "collections", "access_events")
        ] == [0, 0, 0]


def test_disposable_native_byte_tamper_fails(run: Path) -> None:
    database = run / "company.sqlite3"
    with database.open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(CompanyStoreError, match="manifest differs"):
        source.verify(run, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)


def test_unreviewed_attachment_fails_closed(run: Path) -> None:
    attachment = run / "unreviewed.txt"
    attachment.write_text("extra")
    attachment.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="Exact three-file"):
        source.verify(run, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)


def test_unpinned_spec_fails_before_source_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tmp_path.chmod(0o700)
    monkeypatch.setattr(source, "SPEC_SHA256", "0" * 64)
    with pytest.raises(CompanyStoreError, match="specification differs"):
        source.create(
            tmp_path / "source", repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY
        )
    assert not (tmp_path / "source").exists()
