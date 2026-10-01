"""Branch-matched selected committee-cycle originals and no-credit boundaries."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_gov_selected_oversight_2027 as source
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE_REPOSITORY = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


@pytest.fixture
def run(tmp_path: Path) -> Path:
    tmp_path.chmod(0o700)
    destination = tmp_path / "source"
    source.create(destination, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)
    return destination


def test_branch_matched_native_cycle_and_open_limits(run: Path) -> None:
    verified = source.verify(run, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)
    assert verified["native_version_counts"] == {"CLEAN": 9, "MESSY": 14}
    receipt = json.loads((run / "RECEIPT.json").read_text())
    assert receipt["selected_case_count"] == 1
    assert len(receipt["target_task_ids"]) == 8
    assert receipt["messy_historical_sec003_exception_status"] == "OPEN"
    assert receipt["messy_historical_governance_exception_status"] == "OPEN"
    for key in (
        "actual_board_meeting",
        "legal_quorum_established",
        "adopted_minutes",
        "complete_oversight_population",
        "authored_cc12_clause_satisfied",
        "independent_assurance_completed",
        "actual_phi_processing",
        "source_complete",
        "fresh_audit_pair_created",
        "audit_task_credit",
    ):
        assert receipt[key] is False
    assert receipt["real_external_messages_sent"] == 0
    assert {side: len(refs) for side, refs in receipt["upstream_original_refs"].items()} == {
        "CLEAN": 2,
        "MESSY": 3,
    }
    for side in source.BRANCHES:
        upstream = receipt["upstream_original_refs"][side]
        assert {ref["branch"] for ref in upstream} == {source.sec3.BRANCHES[side]}
        assert all(set(ref) == set(source.SOURCE_FIELDS) for ref in upstream)
    with sqlite3.connect(
        (run / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        assert [
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "collections", "access_events")
        ] == [0, 0, 0]
        for side, branch in source.BRANCHES.items():
            rows = db.execute(
                "SELECT * FROM versions WHERE branch=? ORDER BY rowid", (branch,)
            ).fetchall()
            assert len(rows) == (9 if side == "CLEAN" else 14)
            bodies = [json.loads(row["content"]) for row in rows]
            for row, body in zip(rows, bodies, strict=True):
                assert body["upstream_original_refs"] == receipt["upstream_original_refs"][side]
                assert body["scenario"] == side
                assert body["branch"] == branch
                assert body["actual_board_meeting"] is False
                assert body["adopted_minutes"] is False
                assert body["audit_task_credit"] is False
                assert row["sha256"] == hashlib.sha256(row["content"]).hexdigest()
            for earlier, later in zip(bodies, bodies[1:], strict=False):
                assert earlier["event_at"] < later["event_at"]
                assert later["previous_native_content"] == {
                    "record": earlier["record"],
                    "sha256": hashlib.sha256(
                        json.dumps(earlier, sort_keys=True, separators=(",", ":")).encode()
                    ).hexdigest(),
                }
            by_record = {row["record"]: body for row, body in zip(rows, bodies, strict=True)}
            if side == "CLEAN":
                assert by_record["DRAFT-NOTE-01"]["detail"]["no_control_failure_in_clean_source"]
                assert by_record["ACTION-01"]["status"] == "OPEN_REQUEST_FOR_INDEPENDENT_REVIEW"
            else:
                assert by_record["CALDER-Q-PENDING"]["status"] == "QUESTIONNAIRE_NOT_RETURNED"
                assert by_record["PACKET-INITIAL"]["status"] == "ADVERSE_RECORD_OMITTED"
                assert by_record["ACTION-FALSE-CLOSE"]["status"] == "FALSE_CLOSE"
                assert by_record["EXC-OPEN-01"]["status"] == "OPEN"
                assert by_record["DRAFT-NOTE-AMENDMENT"]["detail"]["historical_exception_open"]
                assert by_record["RECON-01"]["status"] == "HISTORICAL_GOV_EXCEPTION_OPEN"


def test_disposable_native_byte_tamper_fails(run: Path) -> None:
    with (run / "company.sqlite3").open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(CompanyStoreError, match="manifest differs"):
        source.verify(run, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)


def test_rehashed_trailing_sqlite_byte_fails(run: Path) -> None:
    database = run / "company.sqlite3"
    with database.open("ab") as handle:
        handle.write(b"tamper")
    manifest_path = run / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["db_sha256"] = hashlib.sha256(database.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    with pytest.raises(CompanyStoreError, match="physical byte extent differs"):
        source.verify(run, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)


@pytest.mark.parametrize("tamper", ["cross_branch", "false_approval"])
def test_cross_branch_ref_and_false_approval_fail_closed(run: Path, tamper: str) -> None:
    receipt_path = run / "RECEIPT.json"
    manifest_path = run / "MANIFEST.json"
    receipt = json.loads(receipt_path.read_text())
    if tamper == "cross_branch":
        receipt["upstream_original_refs"]["CLEAN"][0] = receipt["upstream_original_refs"]["MESSY"][
            0
        ]
    else:
        receipt["adopted_minutes"] = True
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    manifest = json.loads(manifest_path.read_text())
    manifest["receipt_sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    with pytest.raises(CompanyStoreError, match="receipt scope differs"):
        source.verify(run, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)


def test_unreviewed_attachment_fails_closed(run: Path) -> None:
    extra = run / "unreviewed.txt"
    extra.write_text("extra")
    extra.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="Exact three-file"):
        source.verify(run, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)


def test_unpinned_upstream_review_blocks_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tmp_path.chmod(0o700)
    monkeypatch.setitem(source.PRIVATE_PINS, source.SEC3_REVIEW, "0" * 64)
    with pytest.raises(CompanyStoreError, match="Reviewed SEC003 source bytes differ"):
        source.create(
            tmp_path / "source", repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY
        )
    assert not (tmp_path / "source").exists()
