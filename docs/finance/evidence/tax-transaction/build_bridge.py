"""Reproduce accepted industrial transaction/tax schedules without altering its source."""

import hashlib
import importlib.util
import json
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
spec = importlib.util.spec_from_file_location(
    "industrial_financials", ROOT / "industrial/tools/build_financials.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def build():
    source, operations, _ = m.read_sources()
    _, _, monthly = m.customer_schedules(source)
    _, payroll = m.payroll_schedules(source)
    history, _ = m.build_2025(source, monthly, payroll)
    _, invoices = m.interface_schedules(operations)
    ppa = m.acquisition(source, history)
    aru, opening, stub, monthly2026, funding, assets, debt, tax = m.build_2026(
        source, operations, history, monthly, payroll, invoices, ppa
    )
    fields = {k: v for k, v in ppa.items() if isinstance(v, int)}
    datasets = {
        "aru_2026_tax_rollforward": tax,
        "aru_acquisition_opening_trial_balance": opening,
        "aru_2026_debt": debt,
        "aru_2026_assets": assets,
        "acquisition_ppa": [{"measure": k, "amount_usd": v} for k, v in fields.items()],
    }
    dbpath = HERE / "transaction-support.sqlite3"
    if dbpath.exists():
        dbpath.unlink()
    db = sqlite3.connect(dbpath)
    files = []
    for name, rs in datasets.items():
        path = HERE / (name + ".csv")
        m.write_csv(path, rs)
        columns = list(rs[0])
        db.execute(
            'CREATE TABLE "' + name + '" (' + ",".join('"' + c + '" TEXT' for c in columns) + ")"
        )
        db.executemany(
            'INSERT INTO "' + name + '" VALUES (' + ",".join("?" for c in columns) + ")",
            [[str(r.get(c, "")) for c in columns] for r in rs],
        )
        files.append(
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "rows": len(rs),
                "table": name,
            }
        )
    db.commit()
    db.execute("VACUUM")
    db.close()
    assert ppa["close_sources_before_fees_usd"] == ppa["close_uses_before_fees_usd"]
    assert (
        ppa["stock_consideration_usd"] - ppa["identifiable_net_assets_before_refinancing_usd"]
        == ppa["goodwill_usd"]
    )
    assert (
        ppa["tax_allocation"]["modeled_agub_usd"]
        - sum(ppa["tax_allocation"]["other_tax_asset_bases_usd"].values())
        == ppa["tax_goodwill_basis_usd"]
    )
    refs = [
        "industrial/source/finance.json",
        "industrial/source/operations.json",
        "red_wash/source/core_operating_data.json",
        "industrial/tools/build_financials.py",
        "industrial/transaction/04_ARU_APPROVAL_AND_PURCHASE_AGREEMENT.md",
        "industrial/transaction/05_ARU_CLOSING_AND_TAX_DELIVERY.md",
        "industrial/transaction/07_ARU_TAX_STRUCTURE_MEMORANDUM.md",
        "industrial/finance/TRANSACTION_ACCOUNTING.md",
    ]
    record = {
        "status": "REPRODUCED_CURRENT_SYNTHETIC_MODEL_NOT_FILED_TAX",
        "base_revision": "8898d2d0310a60bdf0e4753036790c6eda1388cd",
        "source_hashes": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in refs},
        "database": {
            "path": str(dbpath.relative_to(ROOT)),
            "sha256": hashlib.sha256(dbpath.read_bytes()).hexdigest(),
        },
        "files": files,
        "reconciliation": "Sources equal uses; consideration less fair net assets equals book goodwill; modeled AGUB less other tax bases equals tax goodwill.",
        "ppa": ppa,
        "boundaries": [
            "Current 2026 industrial reconstruction, separate from immutable operations release; never additive.",
            "ARU-CL-07 filing-ready 2026-03-02 is not IRS filing/acceptance.",
            "Red Wash pre-close day dates conflict across summaries/instruments; July 18 2025 close and $28M price agree; no date reconciliation inferred.",
            "Northern Nevada $3M land acquisition is later runtime canon, not part of this scoped release/tax bridge; settlement remains unresolved.",
        ],
    }
    (HERE / "CURRENT_SOURCE_BRIDGE.json").write_text(json.dumps(record, indent=2) + "\n")
    (HERE / "TRANSACTION_SUPPORT.md").write_text("""# Current industrial transaction and tax support

These files reproduce the accepted industrial financial generator at base `8898d2d0310a60bdf0e4753036790c6eda1388cd`; they are separate from the immutable operations release and must not be added as new transactions. [Source hashes and full PPA](CURRENT_SOURCE_BRIDGE.json) identify every input and generated schedule. [Native mirror](transaction-support.sqlite3) contains the same CSV populations.

| Schedule | Scope |
|---|---|
| [PPA](acquisition_ppa.csv) | Stock price, book/tax goodwill, net assets, cash and funding bridge |
| [Opening trial balance](aru_acquisition_opening_trial_balance.csv) | Complete acquisition opening accounts |
| [Tax rollforward](aru_2026_tax_rollforward.csv) | All twelve modeled months; tax basis, expense and cash stay distinct |
| [Debt](aru_2026_debt.csv) | Complete 2026 term/revolver/lease schedule |
| [Assets](aru_2026_assets.csv) | Complete 2026 owned/leased depreciation schedule |

The generator asserts sources equal uses, stock consideration less identifiable net assets equals book goodwill, and modeled AGUB less other tax bases equals tax goodwill. No balancing plugs are added. Book goodwill is $14,762,500; separately computed tax goodwill is $13,000,000. The $587,500 reserve DTA and initial $1,762,500 book/tax goodwill component retain the source's conditional accounting treatment.

ARU-CL-07 is filing-ready as of March 2 2026, not evidence of IRS filing/acceptance. The joint election remains a documentary condition. The modeled tax rate, basis and deductions are scenario assumptions, not a tax opinion. ARU's $3M escrow is included in $48M stock consideration. Red Wash's $3M escrow and $0.5M holdback are included in its separate $28M price.

The legal lane identified inconsistent Red Wash pre-close day dates across summaries and instruments; accepted close date and price agree. This schedule preserves that discrepancy without choosing a date. The later accepted Northern Nevada $3M land purchase belongs to separate runtime canon; its unresolved settlement is not imported as an assumed cash payment or vendor liability.
""")
    print("PASS current-source acquisition/tax bridge", [(k, len(v)) for k, v in datasets.items()])


if __name__ == "__main__":
    build()
