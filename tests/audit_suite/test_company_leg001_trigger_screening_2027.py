"""Screening declarations cannot manufacture nonoccurrence or cure prior reviews."""

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_leg001_trigger_screening_2027 as source
from enterprise.audit_suite.company_store import CompanyStoreError

REPO = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


@pytest.fixture(scope="module")
def context():
    return source._context(REPO, PRIVATE)


@pytest.fixture(scope="module")
def native(tmp_path_factory):
    parent = tmp_path_factory.mktemp("legal-intake")
    parent.chmod(0o700)
    run = parent / "source"
    receipt = source.create(run, repository=REPO, private_repository=PRIVATE)
    return run, receipt


def _copy(native, tmp_path):
    dst = tmp_path / "copy"
    dst.mkdir(mode=0o700)
    for p in native[0].iterdir():
        shutil.copyfile(p, dst / p.name)
        (dst / p.name).chmod(0o600)
    return dst


def _reseal(run):
    manifest = json.loads((run / "MANIFEST.json").read_text())
    for filename, field in (
        ("company.sqlite3", "company_db_sha256"),
        ("RECEIPT.json", "receipt_sha256"),
    ):
        manifest[field] = hashlib.sha256((run / filename).read_bytes()).hexdigest()
    (run / "MANIFEST.json").write_text(json.dumps(manifest))


def test_scope_counts_and_operational_separation(native):
    run, receipt = native
    assert len(receipt["target_task_ids_per_side"]) == 48
    assert receipt["nonoccurrence_acceptance"] is receipt["audit_task_credit"] is False
    assert receipt["source_complete"] is False
    assert receipt["actual_phi"] is receipt["outside_message_sent"] is False
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in run.iterdir())
    for scenario, refs in receipt["records"].items():
        assert len([r for r in refs if r["system"] == "intake_channel_ledger"]) == 48
        assert len([r for r in refs if r["system"] == "monthly_intake_screening"]) == (
            12 if scenario == "CLEAN" else 13
        )
        assert all(r["origin"] == "AUTHORED_TRAINING_SOURCE" for r in refs)
    with sqlite3.connect(f"file:{run / 'company.sqlite3'}?mode=ro", uri=True) as db:
        contents = [json.loads(r[0]) for r in db.execute("SELECT content FROM versions")]
        assert all("audit_task_credit" not in body for body in contents)
        assert all("TASK-SH-" not in json.dumps(body) for body in contents)
        assert all("false_clean" not in json.dumps(body) for body in contents)


def test_historical_gap_is_retained_and_not_a_regulatory_case(context):
    rows = source._steps("MESSY", context["refs"]["MESSY"])
    screen = [
        (at, body)
        for sys, rec, at, body in rows
        if sys == "monthly_intake_screening" and rec == "SCREEN-09"
    ]
    assert len(screen) == 2
    assert screen[0][0] < screen[1][0]
    assert screen[0][1]["reviewed_channel_ids"] == list(source.CHANNELS[:-1])
    assert screen[1][1]["reviewed_channel_ids"] == list(source.CHANNELS)
    original = [
        body
        for sys, rec, _, body in rows
        if sys == "intake_channel_ledger" and rec == "LEDGER-09-PROVIDER-LEGAL"
    ][0]
    assert original["intake_items"][0]["item_id"] == "INQ-PROVIDER-0907"
    disposition = [body for sys, _, _, body in rows if sys == "period_legal_disposition"][0]
    assert disposition["official_notice_ids"] == disposition["hearing_case_ids"] == []
    assert disposition["open_exception_ids"] == ["EXC-INTAKE-2027"]
    assert disposition["later_period_tail"] == "NOT_REVIEWED"
    assert disposition["unregistered_channels"] == "NOT_ESTABLISHED"


def test_exercise_is_explicit_and_remediation_keeps_original(context):
    for scenario in source.BRANCHES:
        exercise = [
            body
            for sys, _, _, body in source._steps(scenario, context["refs"][scenario])
            if sys == "legal_response_exercise"
        ]
        assert all(body["exercise_only"] is True for body in exercise)
        assert exercise[0]["real_notice_received"] is False
        assert exercise[3]["customer_disclosure_rule_is_authority_basis"] is False
    messy = [
        body
        for sys, _, _, body in source._steps("MESSY", context["refs"]["MESSY"])
        if sys == "legal_response_exercise"
    ]
    assert messy[3]["decision"] == "WAIT_FOR_PROVIDER_COPY"
    assert messy[-1]["urgent_access_path_exercised"] is True
    assert messy[-1]["prior_report_id"] == "EXERCISE-REPORT"


def test_resealed_missing_channel_still_rejected(native, tmp_path):
    run = _copy(native, tmp_path)
    with sqlite3.connect(run / "company.sqlite3") as db:
        db.execute("DROP TRIGGER no_version_delete")
        db.execute("DELETE FROM versions WHERE record='LEDGER-09-PROVIDER-LEGAL'")
    _reseal(run)
    with pytest.raises(CompanyStoreError, match="native legal-intake record"):
        source.verify(run, repository=REPO, private_repository=PRIVATE)


def test_resealed_false_nonoccurrence_claim_rejected(native, tmp_path):
    run = _copy(native, tmp_path)
    receipt = json.loads((run / "RECEIPT.json").read_text())
    receipt["nonoccurrence_acceptance"] = True
    (run / "RECEIPT.json").write_text(json.dumps(receipt))
    _reseal(run)
    with pytest.raises(CompanyStoreError, match="receipt boundary"):
        source.verify(run, repository=REPO, private_repository=PRIVATE)


def test_read_only_verification_and_native_immutability(native):
    run = native[0]
    before = {p.name: p.read_bytes() for p in run.iterdir()}
    source.verify(run, repository=REPO, private_repository=PRIVATE)
    assert before == {p.name: p.read_bytes() for p in run.iterdir()}
    with sqlite3.connect(run / "company.sqlite3") as db:
        with pytest.raises(sqlite3.IntegrityError, match="Immutable source"):
            db.execute("DELETE FROM versions")
