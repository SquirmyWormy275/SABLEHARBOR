from __future__ import annotations

import csv
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "tools" / "finance" / "build_reconstruction_model.py"
SPEC = importlib.util.spec_from_file_location("reconstruction_model", MODEL_PATH)
assert SPEC and SPEC.loader
MODEL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODEL)


class ReconstructionModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = MODEL.build()
        cls.output = ROOT / "docs" / "finance" / "model_outputs"

    def test_headcount_cases_reconcile(self) -> None:
        self.assertEqual(self.summary["cases"]["healthy"]["headcount"], 47_000)
        self.assertEqual(self.summary["cases"]["canon_congruent_reference"]["headcount"], 5_000)

    def test_balance_sheets_balance(self) -> None:
        for case in self.summary["cases"].values():
            self.assertEqual(case["balance_sheet_check_usd_m"], 0)

    def test_segment_revenue_reconciles_to_statements(self) -> None:
        with (self.output / "segment_economics.csv").open() as handle:
            segment_rows = list(csv.DictReader(handle))
        with (self.output / "financial_statements.csv").open() as handle:
            statement_rows = list(csv.DictReader(handle))
        for case in self.summary["cases"]:
            segment_revenue = sum(float(row["revenue_usd_m"]) for row in segment_rows if row["case"] == case)
            statement_revenue = next(float(row["amount_usd_m"]) for row in statement_rows if row["case"] == case and row["statement_line"] == "revenue")
            self.assertEqual(segment_revenue, statement_revenue)

    def test_segment_gross_profit_reconciles_to_statements(self) -> None:
        with (self.output / "segment_economics.csv").open() as handle:
            segment_rows = list(csv.DictReader(handle))
        with (self.output / "financial_statements.csv").open() as handle:
            statement_rows = list(csv.DictReader(handle))
        for case in self.summary["cases"]:
            segment_gp = sum(float(row["gross_profit_usd_m"]) for row in segment_rows if row["case"] == case)
            statement_gp = next(float(row["amount_usd_m"]) for row in statement_rows if row["case"] == case and row["statement_line"] == "gross_profit")
            self.assertAlmostEqual(segment_gp, statement_gp, delta=0.1)

    def test_income_statement_math(self) -> None:
        with (self.output / "financial_statements.csv").open() as handle:
            rows = list(csv.DictReader(handle))
        for case in self.summary["cases"]:
            values = {row["statement_line"]: float(row["amount_usd_m"]) for row in rows if row["case"] == case}
            self.assertAlmostEqual(values["ebit"], values["ebitda"] + values["depreciation_amortization"])
            self.assertAlmostEqual(values["net_income"], values["ebit"] + values["interest_expense"] + values["income_tax"])

    def test_free_cash_flow_is_operating_cash_less_capex(self) -> None:
        with (self.output / "financial_statements.csv").open() as handle:
            rows = list(csv.DictReader(handle))
        for case in self.summary["cases"]:
            values = {row["statement_line"]: float(row["amount_usd_m"]) for row in rows if row["case"] == case}
            self.assertAlmostEqual(values["free_cash_flow"], values["operating_cash_flow"] + values["capital_expenditure"])

    def test_outputs_are_explicitly_noncanon(self) -> None:
        payload = json.loads((self.output / "model_summary.json").read_text())
        self.assertEqual(payload["model_status"], "NOT_CANON")


if __name__ == "__main__":
    unittest.main()
