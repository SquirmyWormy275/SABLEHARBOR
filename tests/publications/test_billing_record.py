"""Reject material corruption of the adopted invoice and its source reconciliation."""

import copy
import json
import unittest

from tools.documents import billing_record as billing


class BillingRecordTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((billing.HERE / "record.json").read_text())
        self.source = json.loads(billing.SOURCE.read_text())
        self.proposal = json.loads(billing.PROPOSAL.read_text())

    def result(self):
        return billing.reconcile(self.record, self.source, self.proposal)

    def test_principal_claim_and_tax_are_distinct(self):
        result = self.result()
        self.assertEqual(billing.D(result["surviving_writtenoff_claim_usd"]), 971500)
        self.assertEqual(billing.D(result["legacy_journal_debits_usd"]), 3813500)
        self.assertEqual(billing.D(result["initial_tax_payable_usd"]), 152250)
        self.assertEqual(billing.D(result["legacy_ending_customer_ar_usd"]), 0)

    def test_recovery_cannot_be_counted_twice_even_if_snapshots_match(self):
        self.source["rows"]["invoices"][0]["collected_usd"] = "783000.0000"
        self.proposal["preserved_source_values"]["invoice"] = copy.deepcopy(
            self.source["rows"]["invoices"][0]
        )
        with self.assertRaisesRegex(ValueError, "Recovery"):
            self.result()

    def test_balanced_but_reversed_tax_entry_is_rejected(self):
        for row in self.record["supplemental_journal"]:
            row["debit_usd"], row["credit_usd"] = row["credit_usd"], row["debit_usd"]
        with self.assertRaisesRegex(ValueError, "misclassified"):
            self.result()

    def test_tax_inclusive_divisor_is_rejected(self):
        self.record["tax"]["taxable_gross_receipts_usd"] = "1600000.00"
        with self.assertRaisesRegex(ValueError, "Tax basis"):
            self.result()

    def test_source_journal_imbalance_is_rejected(self):
        self.source["rows"]["journal"][0]["debit_usd"] = "1739999.00"
        with self.assertRaisesRegex(ValueError, "journal imbalance"):
            self.result()

    def test_unknown_customer_or_omitted_decision_is_rejected(self):
        self.record["invoice"]["customer_id"] = "ANOTHER-CUSTOMER"
        with self.assertRaisesRegex(ValueError, "Cross-customer"):
            self.result()
        self.setUp()
        self.record["fields"].pop()
        with self.assertRaisesRegex(ValueError, "Missing"):
            self.result()

    def test_future_cannot_be_promoted_to_actual(self):
        self.record["fact_state"] = "ACTUAL"
        with self.assertRaisesRegex(ValueError, "Future"):
            self.result()

    def test_generated_artifacts_and_protected_inputs(self):
        billing.validate()


if __name__ == "__main__":
    unittest.main()
