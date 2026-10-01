"""Separately identified acquisition-cost basis; original ARU allocation retained."""

import json
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def build():
    source = json.loads(
        (ROOT / "enterprise/ccf/company_closeout/aru_transaction_costs.json").read_text()
    )
    total = sum((D(r["amount_usd"]) for r in source["costs"]), D(0))
    finance = json.loads((ROOT / "industrial/source/finance.json").read_text())
    if total != D(str(finance["transaction"]["transaction_expense"])) or total != D(900000):
        raise ValueError("Acquisition cost components differ from existing transaction expense")
    # Retained tax-filing source allocates all55M non-goodwill FMV against68M
    # original AGUB. No unallocated ClassI–VI fair-value capacity remains.
    return dict(
        source_id=source["record_id"],
        original_agub_usd="68000000",
        unchanged_classes_i_vi_usd="55000000",
        original_tax_goodwill_usd="13000000",
        additional_class_vii_usd=str(total),
        successor_agub_usd=str(D(68000000) + total),
        successor_tax_goodwill_usd=str(D(13000000) + total),
        book_goodwill_usd="14762500",
        additional_book_cash_usd="0",
        annual_additional_amortization_usd=str(total / 180 * 12),
        treatment="CONDITIONAL_338_ELECTED_SOURCE_ARCHITECTURE; ORIGINAL_ALLOCATION_RETAINED_SEPARATELY",
    )
