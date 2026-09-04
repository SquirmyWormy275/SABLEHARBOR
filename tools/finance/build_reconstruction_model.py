#!/usr/bin/env python3
"""Build Sable Harbor's non-canon diagnostic financial reconstruction.

All inputs are explicit below. Outputs are decision-support artifacts, never canon.
The model intentionally refuses to present unknown acquisition terms or reserves as facts.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "finance" / "model_outputs"


WORKFORCE = {
    "minimum_survival": {
        "foundry_field": 5800, "willow": 500, "atlas_meridian": 1200,
        "pale_sun_red_wash": 6500, "project_cradle": 800, "aru_bst": 25000,
        "advisory": 4000, "corporate_ess_ex_j2": 2963, "j2": 237,
    },
    "healthy": {
        "foundry_field": 5800, "willow": 500, "atlas_meridian": 1200,
        "pale_sun_red_wash": 6500, "project_cradle": 800, "aru_bst": 25000,
        "advisory": 4000, "corporate_ess_ex_j2": 2963, "j2": 237,
    },
    "high_performance": {
        "foundry_field": 5800, "willow": 500, "atlas_meridian": 1200,
        "pale_sun_red_wash": 6500, "project_cradle": 800, "aru_bst": 25000,
        "advisory": 4000, "corporate_ess_ex_j2": 2963, "j2": 237,
    },
    "canon_congruent_reference": {
        "foundry_field": 1350, "willow": 75, "atlas_meridian": 225,
        "pale_sun_red_wash": 550, "project_cradle": 75, "aru_bst": 1750,
        "advisory": 375, "corporate_ess_ex_j2": 363, "j2": 237,
    },
}

LABOR = {
    # cash pay, benefit/statutory load, work enablement; USD per employee
    "foundry_field": (150000, 45000, 32000),
    "willow": (170000, 51000, 70000),
    "atlas_meridian": (165000, 50000, 40000),
    "pale_sun_red_wash": (85000, 38000, 30000),
    "project_cradle": (125000, 45000, 45000),
    "aru_bst": (78000, 36000, 27000),
    "advisory": (140000, 42000, 35000),
    "corporate_ess_ex_j2": (145000, 44000, 35000),
    "j2": (155000, 47000, 70000),
}

SEGMENT_REVENUE = {
    "minimum_survival": {
        "foundry_field": 3800, "willow": 0, "atlas_meridian": 500,
        "pale_sun_red_wash": 2400, "project_cradle": 500,
        "aru_bst": 7100, "advisory": 1200,
    },
    "healthy": {
        "foundry_field": 6000, "willow": 0, "atlas_meridian": 1200,
        "pale_sun_red_wash": 3500, "project_cradle": 800,
        "aru_bst": 8500, "advisory": 2000,
    },
    "high_performance": {
        "foundry_field": 9000, "willow": 0, "atlas_meridian": 2000,
        "pale_sun_red_wash": 4500, "project_cradle": 1200,
        "aru_bst": 10300, "advisory": 3000,
    },
    "canon_congruent_reference": {
        "foundry_field": 1050, "willow": 0, "atlas_meridian": 120,
        "pale_sun_red_wash": 310, "project_cradle": 45,
        "aru_bst": 640, "advisory": 135,
    },
}

GROSS_MARGIN = {
    "minimum_survival": {"foundry_field": .60, "willow": 0, "atlas_meridian": .35, "pale_sun_red_wash": .22, "project_cradle": .30, "aru_bst": .24, "advisory": .36},
    "healthy": {"foundry_field": .70, "willow": 0, "atlas_meridian": .55, "pale_sun_red_wash": .32, "project_cradle": .40, "aru_bst": .30, "advisory": .43},
    "high_performance": {"foundry_field": .77, "willow": 0, "atlas_meridian": .68, "pale_sun_red_wash": .42, "project_cradle": .50, "aru_bst": .35, "advisory": .48},
    "canon_congruent_reference": {"foundry_field": .68, "willow": 0, "atlas_meridian": .42, "pale_sun_red_wash": .28, "project_cradle": .35, "aru_bst": .27, "advisory": .40},
}

# Consolidated statement controls in USD millions. They are reverse-solved scenarios.
STATEMENTS = {
    "minimum_survival": {"gross_profit": 5269, "ebitda": 450, "da": 700, "interest": 280, "tax": -180, "net_income": -350, "ocf": 750, "capex": 1200, "cash": 900, "debt": 5200, "assets": 17800, "liabilities": 9800, "equity": 8000, "nwc": 1050},
    "healthy": {"gross_profit": 9710, "ebitda": 2200, "da": 950, "interest": 420, "tax": 150, "net_income": 680, "ocf": 2000, "capex": 1550, "cash": 1600, "debt": 6000, "assets": 22800, "liabilities": 12000, "equity": 10800, "nwc": 1760},
    "high_performance": {"gross_profit": 15825, "ebitda": 4800, "da": 1150, "interest": 520, "tax": 780, "net_income": 2350, "ocf": 4400, "capex": 2050, "cash": 3100, "debt": 6200, "assets": 28500, "liabilities": 13900, "equity": 14600, "nwc": 2400},
    "canon_congruent_reference": {"gross_profit": 1093.75, "ebitda": 250, "da": 135, "interest": 48, "tax": 17, "net_income": 50, "ocf": 225, "capex": 190, "cash": 260, "debt": 650, "assets": 2800, "liabilities": 1550, "equity": 1250, "nwc": 175},
}

CORPORATE_COSTS = {
    "minimum_survival": {"executive_board_communications": 55, "finance_treasury_accounting_tax": 105, "legal_compliance_risk": 85, "internal_audit": 20, "people_culture": 110, "technology_total": 950, "procurement_safety_quality": 60, "facilities_hq": 110, "j2": 95, "insurance_professional_other": 160},
    "healthy": {"executive_board_communications": 65, "finance_treasury_accounting_tax": 125, "legal_compliance_risk": 100, "internal_audit": 25, "people_culture": 130, "technology_total": 1200, "procurement_safety_quality": 75, "facilities_hq": 155, "j2": 110, "insurance_professional_other": 190},
    "high_performance": {"executive_board_communications": 80, "finance_treasury_accounting_tax": 150, "legal_compliance_risk": 125, "internal_audit": 32, "people_culture": 160, "technology_total": 1550, "procurement_safety_quality": 95, "facilities_hq": 200, "j2": 130, "insurance_professional_other": 230},
    "canon_congruent_reference": {"executive_board_communications": 22, "finance_treasury_accounting_tax": 38, "legal_compliance_risk": 31, "internal_audit": 9, "people_culture": 32, "technology_total": 115, "procurement_safety_quality": 19, "facilities_hq": 42, "j2": 82, "insurance_professional_other": 55},
}

TECHNOLOGY = {
    "minimum_survival": {"labor": 230, "endpoints": 80, "enterprise_saas": 120, "cloud_network_observability": 180, "security_identity": 80, "developer_tooling": 45, "data_ai": 120, "backup_support_other": 95},
    "healthy": {"labor": 300, "endpoints": 105, "enterprise_saas": 165, "cloud_network_observability": 260, "security_identity": 110, "developer_tooling": 65, "data_ai": 220, "backup_support_other": 75},
    "high_performance": {"labor": 370, "endpoints": 135, "enterprise_saas": 210, "cloud_network_observability": 340, "security_identity": 155, "developer_tooling": 90, "data_ai": 175, "backup_support_other": 75},
    "canon_congruent_reference": {"labor": 45, "endpoints": 10, "enterprise_saas": 15, "cloud_network_observability": 15, "security_identity": 10, "developer_tooling": 5, "data_ai": 10, "backup_support_other": 5},
}


def write_csv(name: str, fieldnames: list[str], rows: list[dict]) -> None:
    with (OUT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    workforce_rows, labor_rows, segment_rows, corp_rows, tech_rows = [], [], [], [], []
    statement_rows, reality_rows = [], []
    summary = {"model_status": "NOT_CANON", "cases": {}}

    for case, allocation in WORKFORCE.items():
        headcount = sum(allocation.values())
        revenue = sum(SEGMENT_REVENUE[case].values())
        people_enabled = 0.0
        cash_benefits = 0.0
        for population, employees in allocation.items():
            cash, benefits, enablement = LABOR[population]
            all_in = cash + benefits + enablement
            cash_benefits += employees * (cash + benefits) / 1_000_000
            people_enabled += employees * all_in / 1_000_000
            workforce_rows.append({"case": case, "population": population, "employees": employees, "evidence_class": "LOCKED" if population == "j2" else "SCENARIO"})
            labor_rows.append({"case": case, "population": population, "employees": employees, "cash_pay_per_employee": cash, "benefits_per_employee": benefits, "enablement_per_employee": enablement, "all_in_per_employee": all_in, "total_all_in_usd_m": round(employees * all_in / 1_000_000, 3), "evidence_class": "SUPPORTED ESTIMATE"})

        segment_gp = 0.0
        for segment, seg_revenue in SEGMENT_REVENUE[case].items():
            margin = GROSS_MARGIN[case][segment]
            segment_gp += seg_revenue * margin
            segment_rows.append({"case": case, "segment": segment, "revenue_usd_m": seg_revenue, "gross_margin_pct": round(margin * 100, 1), "gross_profit_usd_m": round(seg_revenue * margin, 1), "employees": allocation[segment], "revenue_per_employee_usd": round(seg_revenue * 1_000_000 / allocation[segment]) if allocation[segment] else 0, "evidence_class": "SCENARIO"})

        for item, amount in CORPORATE_COSTS[case].items():
            corp_rows.append({"case": case, "cost_family": item, "annual_cost_usd_m": amount, "evidence_class": "SUPPORTED ESTIMATE"})
        for item, amount in TECHNOLOGY[case].items():
            tech_rows.append({"case": case, "cost_family": item, "annual_cost_usd_m": amount, "evidence_class": "SUPPORTED ESTIMATE"})

        s = STATEMENTS[case]
        assert abs(segment_gp - s["gross_profit"]) <= 3.0, (case, segment_gp, s["gross_profit"])
        ebit = s["ebitda"] - s["da"]
        fcf = s["ocf"] - s["capex"]
        balance_check = s["assets"] - s["liabilities"] - s["equity"]
        assert balance_check == 0, (case, balance_check)
        assert round(s["ebitda"] - s["da"] - s["interest"] - s["tax"], 6) == s["net_income"], case
        for line, amount in [
            ("revenue", revenue), ("gross_profit", s["gross_profit"]), ("ebitda", s["ebitda"]),
            ("depreciation_amortization", -s["da"]), ("ebit", ebit), ("interest_expense", -s["interest"]),
            ("income_tax", -s["tax"]), ("net_income", s["net_income"]), ("operating_cash_flow", s["ocf"]),
            ("capital_expenditure", -s["capex"]), ("free_cash_flow", fcf), ("cash", s["cash"]),
            ("debt", s["debt"]), ("total_assets", s["assets"]), ("total_liabilities", s["liabilities"]),
            ("total_equity", s["equity"]), ("net_working_capital", s["nwc"]),
        ]:
            statement_rows.append({"case": case, "statement_line": line, "amount_usd_m": round(amount, 3), "evidence_class": "SCENARIO"})

        metrics = {
            "headcount": headcount,
            "revenue_per_employee_usd": revenue * 1_000_000 / headcount,
            "gross_profit_per_employee_usd": s["gross_profit"] * 1_000_000 / headcount,
            "ebitda_per_employee_usd": s["ebitda"] * 1_000_000 / headcount,
            "corporate_employees_pct": (allocation["corporate_ess_ex_j2"] + allocation["j2"]) / headcount * 100,
            "technology_cost_pct_revenue": CORPORATE_COSTS[case]["technology_total"] / revenue * 100,
            "j2_cost_pct_revenue": CORPORATE_COSTS[case]["j2"] / revenue * 100,
            "people_enabled_cost_pct_revenue": people_enabled / revenue * 100,
            "cash_comp_benefits_pct_revenue": cash_benefits / revenue * 100,
            "capex_pct_revenue": s["capex"] / revenue * 100,
            "fcf_conversion_pct": fcf / s["ebitda"] * 100,
            "working_capital_intensity_pct": s["nwc"] / revenue * 100,
            "debt_to_ebitda": s["debt"] / s["ebitda"],
            "interest_coverage": ebit / s["interest"],
            "balance_sheet_check_usd_m": balance_check,
        }
        for metric, value in metrics.items():
            reality_rows.append({"case": case, "metric": metric, "value": round(value, 4), "evidence_class": "DERIVED"})
        summary["cases"][case] = {"headcount": headcount, "revenue_usd_m": revenue, "people_enabled_cost_usd_m": round(people_enabled, 3), "cash_comp_benefits_usd_m": round(cash_benefits, 3), "free_cash_flow_usd_m": fcf, "balance_sheet_check_usd_m": balance_check}

    write_csv("workforce_census.csv", ["case", "population", "employees", "evidence_class"], workforce_rows)
    write_csv("loaded_labor.csv", ["case", "population", "employees", "cash_pay_per_employee", "benefits_per_employee", "enablement_per_employee", "all_in_per_employee", "total_all_in_usd_m", "evidence_class"], labor_rows)
    write_csv("segment_economics.csv", ["case", "segment", "revenue_usd_m", "gross_margin_pct", "gross_profit_usd_m", "employees", "revenue_per_employee_usd", "evidence_class"], segment_rows)
    write_csv("corporate_costs.csv", ["case", "cost_family", "annual_cost_usd_m", "evidence_class"], corp_rows)
    write_csv("technology_costs.csv", ["case", "cost_family", "annual_cost_usd_m", "evidence_class"], tech_rows)
    write_csv("financial_statements.csv", ["case", "statement_line", "amount_usd_m", "evidence_class"], statement_rows)
    write_csv("reality_tests.csv", ["case", "metric", "value", "evidence_class"], reality_rows)
    (OUT / "model_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
