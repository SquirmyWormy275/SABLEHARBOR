import copy
import unittest

from enterprise.ccf.company_closeout.admin_completion import (
    read,
    validate_benefits,
    validate_environment,
)


class CompletionTests(unittest.TestCase):
    def test_environment(self):
        self.assertEqual(
            validate_environment(read("august_admin_completion.json"))["daily_workpractice"], 31
        )

    def test_environment_failures(self):
        base = read("august_admin_completion.json")
        for mutate in [
            lambda x: x["radon"]["cells"][0].update(area_acres="41"),
            lambda x: x["radon"]["cells"][0].update(construction_year=1988),
            lambda x: x["radon"]["daily_workpractice"].pop(),
            lambda x: x["radon"]["liner_compatibility"].update(retained_tensile_strength_pct="80"),
            lambda x: x["bond"].update(additional_parent_guarantee=True),
            lambda x: x["bond"]["premium_component"].update(payer="PS"),
            lambda x: x["bond"]["premium_component"].update(selected_month_expense_usd="40000"),
            lambda x: x["bond"]["premium_component"].update(additional_group_cash_usd="10000"),
            lambda x: x["bond"]["premium_component"].update(independent_external_confirmation=True),
            lambda x: x["bond"]["reconciliation"].update(cash_available_from_bond_usd="25000000"),
        ]:
            with self.subTest(mutate=mutate):
                data = copy.deepcopy(base)
                mutate(data)
                with self.assertRaises(ValueError):
                    validate_environment(data)

    def test_benefits(self):
        data = read("benefit_admin_completion.json")
        people = [
            {"person_id": r["person_id"], "legal_employer": r["legal_employer"]}
            for r in data["enrollment"]
        ]
        self.assertEqual(validate_benefits(data, people)["COVERED"], 612)
        for mutate in [
            lambda x: x["enrollment"].pop(),
            lambda x: x["enrollment"].append(x["enrollment"][0]),
            lambda x: x["administrative_review"].update(covered=702),
            lambda x: x["distributions"].pop(),
            lambda x: x["september_exit"].update(election_made=True),
            lambda x: x["september_exit"].update(employer_notice_to_administrator_on="2026-10-15"),
            lambda x: x["hipaa"].update(no_clinical_claims_at_employer=False),
        ]:
            with self.subTest(mutate=mutate):
                bad = copy.deepcopy(data)
                mutate(bad)
                with self.assertRaises(ValueError):
                    validate_benefits(bad, people)
