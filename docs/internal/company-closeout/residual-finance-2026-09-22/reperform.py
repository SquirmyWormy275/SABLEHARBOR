"""Source-only arithmetic; no accounting entries, rights or cash authorization."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PATHS = (
    "industrial/source/finance.json",
    "industrial/planning/source/forecast.json",
    "enterprise/closeout/source/capital_register.json",
    "docs/canon/COMPANY_CLOSEOUT_DIRECTIONS_2026-09-15.md",
    "docs/governance/BOARD_AND_CAPITAL_GOVERNANCE_v1.0.1.md",
    "docs/governance/board-records/2021-06-18_harrison-vale-growth-financing-minutes.md",
    "docs/legal/gap-instruments/source/debt-liens.md",
    "docs/legal/gap-instruments/source/financing-documents.md",
)
f = json.loads((ROOT / PATHS[0]).read_text())
p = json.loads((ROOT / PATHS[1]).read_text())["debt"]
t = f["transaction"]
term = f["opening_2025"]["term_debt"] - f["closing_2025_drivers"]["term_principal"]
revolver = f["opening_2025"]["revolver"]
assert term + revolver == t["existing_term_revolver_refinance"]
# Three first-year payments and four each year 2027–2030, before January maturity.
count = 3 + 4 * 4
balloon = t["new_debt"] - count * t["new_debt_quarterly_principal"]
assert p["legacy_term_maturity"] == "2031-01-07"
assert p["legacy_quarterly_principal_usd"] == t["new_debt_quarterly_principal"]
refinancing = []
for scenario, row in p["refinancing"].items():
    draw = min(balloon, row["available_principal_usd"])
    fee = Decimal(draw) * Decimal(str(row["fee_pct"])) / 100
    refinancing.append(
        {
            "scenario": scenario,
            "conditional_capacity_usd": row["available_principal_usd"],
            "conditional_draw_usd": draw,
            "principal_not_covered_by_new_draw_usd": balloon - draw,
            "conditional_fee_usd": str(fee),
            "principal_plus_fee_not_covered_by_draw_usd": str(balloon - draw + fee),
        }
    )
result = {
    "status": "REVIEWABLE_SOURCE_DERIVATION_NOT_ADOPTED_RIGHTS",
    "source_baseline": "812676c2ac739d6fba91f770ee1369eea9f2b46d",
    "source_hashes": {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in PATHS},
    "existing_payoff_components": [
        {
            "authored_administrative_id": "SH-DEBT-ARU-LEGACY-TERM-PAYOFF-20260107",
            "principal_usd": term,
            "derivation": "2025 opening term principal less 2025 source principal payments",
        },
        {
            "authored_administrative_id": "SH-DEBT-ARU-LEGACY-REVOLVER-PAYOFF-20260107",
            "principal_usd": revolver,
            "derivation": "2025 source revolver principal; no principal movement in closing drivers",
        },
    ],
    "existing_total_payoff_usd": term + revolver,
    "retained_lease_usd_excluded": t["retained_leases"],
    "scheduled_2031_maturity": {
        "date": p["legacy_term_maturity"],
        "scheduled_installments_before_maturity": count,
        "principal_usd_if_scheduled_payments_made": balloon,
        "source_status": "ACCEPTED_CONDITIONAL_FORECAST_NOT_EXECUTED_INSTRUMENT",
    },
    "conditional_refinancing": refinancing,
    "cap_threshold_options_not_adopted": {
        "half_original_registered_units": {
            "Harrison Vale Partners": 9250000,
            "Wolf Ridge Holdings": 7500000,
        },
        "ten_percent_current_units_at_100m_total": {
            "Harrison Vale Partners": 10000000,
            "Wolf Ridge Holdings": 10000000,
        },
        "current_units": {"Harrison Vale Partners": 18500000, "Wolf Ridge Holdings": 15000000},
    },
    "posting_count": 0,
    "boundary": "Schedule arithmetic is not actual future cash sufficiency or a commitment. No old security or lien release inferred. Administrative IDs identify existing obligations, not new instruments or lender acceptance.",
}
print(json.dumps(result, indent=2))
