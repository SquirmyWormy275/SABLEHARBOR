"""Exercise source population boundaries and the full transaction trace."""

import importlib.util
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "walkthroughs", ROOT / "tools/legal_gaps/walkthroughs.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture(scope="module")
def derived():
    return module.derive()


def test_native_journals_and_statement_chain(derived):
    tables, _ = derived
    assert len(tables["aru_2026_journal"]) == 1926
    assert len(tables["aru_acquisition_opening_trial_balance"]) == 16
    assert all(Decimal(r["difference_usd"]) == 0 for r in tables["checks"])


def test_release_boundaries_and_exact_accepted_invoice(derived):
    tables, provenance = derived
    assert provenance["no_new_postings"]
    assert all(
        r["scenario"] == "base" and r["year"] == "2027" and r["unit"] == "foundry-field"
        for r in tables["ff_journal"]
    )
    assert len(tables["ff_packet_journal"]) == 12
    assert len(tables["ff_statements"]) == 12
    assert len(tables["ff_contract_trace"]) < len(tables["ff_journal"])


def test_requests_do_not_claim_execution(derived):
    rows = derived[0]["evidence_requests"]
    assert len({r["id"] for r in rows}) == 6
    assert all(r["blocked_conclusion"].startswith("Cannot") for r in rows)
    assert all((ROOT / r["source_path"]).is_file() for r in rows)


def test_regeneration_is_deterministic(tmp_path):
    module.build(tmp_path / "a")
    module.build(tmp_path / "b")
    for p in (tmp_path / "a").rglob("*"):
        if p.is_file():
            assert p.read_bytes() == (tmp_path / "b" / p.relative_to(tmp_path / "a")).read_bytes()


def test_changed_source_is_rejected(monkeypatch):
    original = module.csvread

    def changed(path):
        rows = original(path)
        if str(path).endswith("close/source/monthly_statements.csv"):
            rows[0]["revenue_usd"] = str(Decimal(rows[0]["revenue_usd"]) + 1)
        return rows

    monkeypatch.setattr(module, "csvread", changed)
    with pytest.raises(ValueError):
        module.derive()


def test_missing_statement_account_is_rejected(monkeypatch):
    original = module.csvread

    def changed(path):
        rows = original(path)
        if path.name == "financial_statements.csv":
            return [
                r
                for r in rows
                if not (
                    r["entity"] == "ARU_GROUP" and r["year"] == "2026" and r["line_id"] == "1000"
                )
            ]
        return rows

    monkeypatch.setattr(module, "csvread", changed)
    with pytest.raises(ValueError, match="coverage differs"):
        module.derive()
