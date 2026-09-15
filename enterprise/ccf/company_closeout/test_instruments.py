import copy
import unittest

from .instruments import read, report, validate_instruments, validate_risks


class InstrumentsTest(unittest.TestCase):
    def test_reperformed_denominators(self):
        value = report()
        self.assertEqual(value["permit_performance"]["occurrences"], 204)
        self.assertEqual(value["permit_performance"]["outcomes"]["FAILED_CORRECTED"], 3)
        self.assertEqual(value["ccf_denominators"]["combined_unmapped"], 0)
        self.assertEqual(value["ccf_denominators"]["forecast_expected_occurrences"], 7560)

    def test_population_and_time_mutations(self):
        source = read("synthetic_permit_instruments_august.json")
        for mutate in [
            lambda d: d["evidence"].pop(),
            lambda d: d["evidence"].append(copy.deepcopy(d["evidence"][0])),
            lambda d: d["evidence"][0].update(available_on="2026-08-31"),
            lambda d: d["conditions"][6]["population_members"].__setitem__(0, "INVENTED-WELL"),
            lambda d: d["evidence"][0].update(reviewer_id="RW-0119"),
        ]:
            d = copy.deepcopy(source)
            mutate(d)
            with self.assertRaises(ValueError):
                validate_instruments(d)

    def test_adverse_outcomes_not_promoted(self):
        source = read("synthetic_permit_instruments_august.json")
        for condition, member in [
            ("RW-AUG-COND-007", "MW-17"),
            ("RW-AUG-COND-011", "C07 selected yellowcake shipment authority gate"),
        ]:
            d = copy.deepcopy(source)
            next(
                r for r in d["evidence"] if r["condition_id"] == condition and r["member"] == member
            )["state"] = "PERFORMED"
            with self.assertRaises(ValueError):
                validate_instruments(d)

    def test_mapping_missing_duplicate_unknown(self):
        source = read("risk_mapping_supplement.json")
        for mutate in [
            lambda d: d["mappings"].pop(),
            lambda d: d["mappings"].__setitem__(0, copy.deepcopy(d["mappings"][1])),
            lambda d: d["mappings"][0].update(risk_id="SH-RISK-INVENTED"),
        ]:
            d = copy.deepcopy(source)
            mutate(d)
            with self.assertRaises(ValueError):
                validate_risks(d)
