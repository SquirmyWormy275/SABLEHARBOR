"""Validate finance evidence extracts, population identity and accounting equations."""

import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/finance/evidence"
spec = importlib.util.spec_from_file_location(
    "finance_extract", Path(__file__).with_name("build.py")
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def validate(base=BASE):
    totals = {}
    for family in m.FAMILIES:
        folder = base / family
        reg = json.loads((folder / "evidence-register.json").read_text())
        db = sqlite3.connect(folder / "evidence.sqlite3")
        db.row_factory = sqlite3.Row
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert (
            m.digest((folder / "evidence.sqlite3").read_bytes())
            == reg["extracted_database"]["sha256"]
        )
        data = {}
        for s in reg["sources"]:
            p = folder / "source" / Path(s["path"]).name
            assert m.digest(p.read_bytes()) == s["sha256"]
            rs = m.rows(p.read_bytes())
            assert len(rs) == s["row_count"]
            data[p.stem] = rs
            assert [dict(r) for r in db.execute('SELECT * FROM "' + p.stem + '"')] == rs
            assert all(m.selected(r, int(reg["scope"]["period_start"][:4])) for r in rs)
        db.close()
        actual = m.checks(data, family)
        expected = json.loads((folder / "RECONCILIATION.json").read_text())
        assert actual == expected["checks"]
        assert all(r["status"] == "PASS" for r in actual)
        totals[family] = sum(len(rs) for rs in data.values())
    customer = {p.stem: m.rows(p.read_bytes()) for p in (base / "customer/source").glob("*.csv")}
    journals = m.rows((base / "close/source/journal.csv").read_bytes())
    invoice_ids = {r["invoice_id"] for r in customer["invoices"]}
    event_ids = {r["event_id"] for r in customer["events"]}
    posted = {r["source_id"] for r in journals}
    contract_ids = {r["contract_id"] for r in customer["contracts"]}
    assert all(r["contract_id"] in contract_ids for r in customer["contract_versions"]), (
        "contract_versions.contract_id absent from contracts"
    )
    for table in ("credit_history", "credit_notes", "receivable_aging", "credit_allowance"):
        assert all(r["invoice_id"] in invoice_ids for r in customer[table]), table
    assert all(
        r["source_id"] in event_ids and r["source_id"] in posted for r in customer["credit_history"]
    ), "credit_history.source_id absent from events.event_id or close journal.source_id"
    assert all(r["event_id"] in posted for r in customer["events"] if r.get("invoice_id")), (
        "Invoice events.event_id absent from close journal.source_id"
    )
    bridge = json.loads((base / "tax-transaction/CURRENT_SOURCE_BRIDGE.json").read_text())
    for relative, digest in bridge["source_hashes"].items():
        assert m.digest((ROOT / relative).read_bytes()) == digest, (
            "Current transaction source changed: " + relative
        )
    for entry in bridge["files"]:
        path = base / "tax-transaction" / Path(entry["path"]).name
        assert m.digest(path.read_bytes()) == entry["sha256"], entry["path"]
        assert len(m.rows(path.read_bytes())) == entry["rows"], entry["path"]
    ppa = bridge["ppa"]
    assert ppa["close_sources_before_fees_usd"] == ppa["close_uses_before_fees_usd"], (
        "Acquisition sources/uses mismatch"
    )
    assert (
        ppa["stock_consideration_usd"] - ppa["identifiable_net_assets_before_refinancing_usd"]
        == ppa["goodwill_usd"]
    ), "Book PPA residual mismatch"
    assert (
        ppa["tax_allocation"]["modeled_agub_usd"]
        - sum(ppa["tax_allocation"]["other_tax_asset_bases_usd"].values())
        == ppa["tax_goodwill_basis_usd"]
    ), "Tax goodwill residual mismatch"
    print("PASS exact CSV/database populations, hashes, scope and accounting:", totals)
    return totals


if __name__ == "__main__":
    validate()
