import copy
import json
import unittest

from .rail_reporting import SOURCE, validate


class RailReportingTest(unittest.TestCase):
    def test_complete_case_population(self):
        result = validate(json.loads(SOURCE.read_text()))
        self.assertEqual(result["cases"], 14)
        self.assertEqual(result["incident_form_records"], 11)
        self.assertEqual(result["states"]["MODELED_SUBMITTED_LATE"], 1)

    def test_claims_groups_dates_and_population(self):
        source = json.loads(SOURCE.read_text())
        for mutate in [
            lambda d: d["cases"].pop(),
            lambda d: d["cases"].append(copy.deepcopy(d["cases"][0])),
            lambda d: d["cases"][0].update(repair_cost_usd="18000"),
            lambda d: d["cases"][7].update(crossing=False),
            lambda d: d["cases"][8].update(reportable_injury=False),
            lambda d: d["cases"][5].update(filing_state="MODELED_SUBMITTED"),
            lambda d: d["cases"][0].update(acknowledgement_state="REAL_FRA_ACCEPTED"),
            lambda d: d.update(available_on="2014-02-12"),
        ]:
            data = copy.deepcopy(source)
            mutate(data)
            with self.assertRaises(ValueError):
                validate(data)
