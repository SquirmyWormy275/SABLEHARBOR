"""Verify every current industrial source, extracted table and acquisition identity."""

import csv
import hashlib
import json
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def validate(folder=HERE):
    bridge = json.loads((folder / "CURRENT_SOURCE_BRIDGE.json").read_text())
    for relative, digest in bridge["source_hashes"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest, relative
    target = folder / Path(bridge["database"]["path"]).name
    assert hashlib.sha256(target.read_bytes()).hexdigest() == bridge["database"]["sha256"], target
    db = sqlite3.connect(target)
    db.row_factory = sqlite3.Row
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok", target
    assert {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")} == {
        r["table"] for r in bridge["files"]
    }, "Current bridge table population differs"
    for entry in bridge["files"]:
        p = folder / Path(entry["path"]).name
        assert hashlib.sha256(p.read_bytes()).hexdigest() == entry["sha256"], p
        rows = list(csv.DictReader(p.open()))
        assert len(rows) == entry["rows"], p
        assert [dict(r) for r in db.execute('SELECT * FROM "' + entry["table"] + '"')] == rows, p
    db.close()
    ppa = bridge["ppa"]
    assert ppa["close_sources_before_fees_usd"] == ppa["close_uses_before_fees_usd"], "Sources/uses"
    assert (
        ppa["stock_consideration_usd"] - ppa["identifiable_net_assets_before_refinancing_usd"]
        == ppa["goodwill_usd"]
    ), "Book goodwill"
    assert (
        ppa["tax_allocation"]["modeled_agub_usd"]
        - sum(ppa["tax_allocation"]["other_tax_asset_bases_usd"].values())
        == ppa["tax_goodwill_basis_usd"]
    ), "Tax goodwill"
    print("PASS current transaction source hashes, complete CSV/SQLite mirror and PPA identities")


if __name__ == "__main__":
    validate()
