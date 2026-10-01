"""Adversarial source changes must invalidate scoped zero-tax classifications."""

import copy
import json
import unittest

from .industrial_tax import ROOT, SOURCE, validate


class IndustrialTaxTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(SOURCE.read_text())
        self.tables = {"current_contracts": [], "current_invoices": []}
        for r in self.data["rows"]:
            self.tables["current_contracts"].append(
                {
                    **{
                        k: r[k]
                        for k in ["contract_id", "customer_id", "legal_entity", "unit", "kind"]
                    },
                    "monthly_fee_usd": r["principal_usd"],
                }
            )
            self.tables["current_invoices"].append(
                {k: r[k] for k in ["contract_id", "invoice_id", "principal_usd"]}
            )
        # Unit tests exercise factual logic; fresh source-byte binding and genuine
        # current generator populations are reperformed by the CLI integration check.

    def test_bound_population(self):
        self.assertEqual(
            validate(self.data, self.tables, ROOT, verify_source_bytes=False)["contracts"], 34
        )

    def test_no_automatic_exemption_after_facts_change(self):
        cases = [
            ("WY_FREIGHT", "passenger_transport", True),
            ("WY_FREIGHT", "well_site_production_service", True),
            ("WY_HANDLING", "cargo_repair_or_alteration", True),
            ("WY_CUSTODY_STORAGE", "equipment_possession_transferred_to_customer", True),
            ("WV_REFINER_INPUT_RESALE", "refiner_resells_recovered_material", False),
            ("IL_YELLOWCAKE_RESALE", "onward_title_transfer_before_consumption", False),
            ("IL_YELLOWCAKE_RESALE", "buyer_consumes_this_intermediate_without_resale", True),
        ]
        for classification, field, value in cases:
            with self.subTest(classification=classification, field=field):
                d = copy.deepcopy(self.data)
                next(r for r in d["rows"] if r["classification"] == classification)["facts"][
                    field
                ] = value
                with self.assertRaises(ValueError):
                    validate(d, self.tables, ROOT, verify_source_bytes=False)

    def test_certificate_scope_and_chronology(self):
        for key, value in [
            ("received_on", "2026-09-30"),
            ("canceled", True),
            ("seller_legal_entity", "ARU"),
            ("purchaser_id", "WRONG"),
            ("signer_id", ""),
            ("available_at", "2026-08-20T00:00:00Z"),
        ]:
            with self.subTest(key=key):
                d = copy.deepcopy(self.data)
                d["certificates"][0][key] = value
                with self.assertRaises(ValueError):
                    validate(d, self.tables, ROOT, verify_source_bytes=False)

    def test_missing_duplicate_and_wrong_invoice(self):
        for mutate in [
            lambda d: d["rows"].pop(),
            lambda d: d["rows"].__setitem__(1, copy.deepcopy(d["rows"][2])),
            lambda d: d["rows"][0].update(principal_usd="1"),
            lambda d: d["rows"][0].update(invoice_id="WRONG"),
            lambda d: d["rows"][0].update(event_period="2027-01"),
        ]:
            d = copy.deepcopy(self.data)
            mutate(d)
            with self.assertRaises(ValueError):
                validate(d, self.tables, ROOT, verify_source_bytes=False)

    def test_utility_tax_cannot_be_zeroed_or_treated_as_resale(self):
        for field, value in [
            ("sales_tax_usd", "0"),
            ("tax_rate", ".0625"),
            ("tax_payable_usd", "0"),
            ("customer_tax_billed_usd", "55281.24"),
        ]:
            d = copy.deepcopy(self.data)
            row = next(r for r in d["rows"] if r["classification"] == "IL_UTILITY_OWN_USE")
            row[field] = value
            with self.assertRaises(ValueError):
                validate(d, self.tables, ROOT, verify_source_bytes=False)
        for field in ["inside_special_business_district", "onward_resale_supported"]:
            d = copy.deepcopy(self.data)
            row = next(r for r in d["rows"] if r["classification"] == "IL_UTILITY_OWN_USE")
            row["facts"][field] = True
            with self.assertRaises(ValueError):
                validate(d, self.tables, ROOT, verify_source_bytes=False)
