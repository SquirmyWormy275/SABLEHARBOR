import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from industrial.planning.integrity import (
    acceptance_binding,
    bank_reconciliations,
    journals,
    producer_pins,
    temporal,
    verify_acceptance_binding,
)


class ExportIntegrityTests(unittest.TestCase):
    def test_in_memory_policy_override_cannot_be_rebound_as_default_release(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            patch("industrial.planning.integrity.subprocess.check_output", return_value="a" * 40),
        ):
            root = Path(temp)
            source = root / "industrial/planning/source"
            source.mkdir(parents=True)
            for key in ("operating_plan", "capital_options", "forecast"):
                (source / f"{key}.json").write_text("{}")
            digest = hashlib.sha256(b"{}").hexdigest()
            output = root / "industrial/generated/planning"
            for scope in ("operations", "capital", "forecast", "enterprise"):
                (output / scope).mkdir(parents=True)
                if scope == "enterprise":
                    (output / scope / "summary.json").write_text(
                        json.dumps(
                            {
                                "source_revision": "a" * 40,
                                "identity": {
                                    "source_inputs": {},
                                    "legacy_metadata": {"source_revision": "a" * 40},
                                },
                            }
                        )
                    )
                    continue
                (output / scope / "manifest.json").write_text(
                    json.dumps(
                        {
                            "artifacts": {},
                            "source_sha256": digest,
                            "effective_input_sha256": {
                                "operating_plan": digest,
                                "capital_options": digest,
                            },
                        }
                    )
                )
            producer_pins(output, root)
            path = output / "operations/manifest.json"
            manifest = json.loads(path.read_text())
            manifest["effective_input_sha256"]["operating_plan"] = hashlib.sha256(
                b'{"growth":99}'
            ).hexdigest()
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "noncanonical effective"):
                producer_pins(output, root)
            manifest["effective_input_sha256"]["operating_plan"] = digest
            path.write_text(json.dumps(manifest))
            enterprise = output / "enterprise/summary.json"
            value = json.loads(enterprise.read_text())
            value["identity"]["legacy_metadata"]["source_revision"] = "b" * 40
            enterprise.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "same source revision"):
                producer_pins(output, root)

    def test_stale_source_or_altered_export_cannot_reuse_acceptance(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            patch("industrial.planning.integrity.subprocess.check_output", return_value="a" * 40),
        ):
            root = Path(temp)
            source = root / "industrial/planning/source"
            source.mkdir(parents=True)
            (root / "industrial/planning/browser_template.html").write_text("<html>Case</html>")
            (root / "uv.lock").write_text("locked")
            (source / "participant_catalog.json").write_text(
                json.dumps({"artifacts": [{"path": "industrial/generated/planning/example.csv"}]})
            )
            output = root / "industrial/generated/planning"
            output.mkdir(parents=True)
            data = output / "example.csv"
            data.write_text("amount_usd\n0.0001\n")
            (output / "acceptance.json").write_text(
                json.dumps({"status": "PASS", "binding": acceptance_binding(output, root)})
            )
            verify_acceptance_binding(output, root)
            data.write_text("amount_usd\n0.0002\n")
            with self.assertRaisesRegex(ValueError, "stale or altered"):
                verify_acceptance_binding(output, root)
            data.write_text("amount_usd\n0.0001\n")
            (source / "assumptions.json").write_text('{"new_assumption": true}')
            with self.assertRaisesRegex(ValueError, "stale or altered"):
                verify_acceptance_binding(output, root)

    def test_future_completed_descendant_cannot_inherit_forecast_permission(self):
        record = {
            "fact_state": "FORECAST",
            "events": [{"year": 2029, "month": 2, "status": "COMPLETED"}],
        }
        with self.assertRaisesRegex(ValueError, "future completed"):
            temporal(record)
        record["events"][0]["status"] = "CONDITIONAL_FORECAST"
        temporal(record)

    def test_unknown_or_late_availability_fails(self):
        with self.assertRaisesRegex(ValueError, "unavailable"):
            temporal({"available_at": "2026-09-07", "fact_state": "FORECAST"})
        with self.assertRaises(ValueError):
            temporal({"available_at": "unknown"})

    def test_opening_balance_uses_january_not_december(self):
        temporal({"year": 2026, "month": 0, "period_role": "SYNTHETIC_CALIBRATION"})
        with self.assertRaises(ValueError):
            temporal({"year": 2027, "month": 0, "period_role": "SYNTHETIC_CALIBRATION"})

    def test_four_decimal_ledger_precision_preserved(self):
        rows = [
            {
                "scenario": "base",
                "entity": "SHI",
                "year": "2027",
                "month": "1",
                "journal_id": "A",
                "account": "1000",
                "debit_usd": "0.0001",
                "credit_usd": "0",
                "signed_usd": "0.0001",
            },
            {
                "scenario": "base",
                "entity": "SHI",
                "year": "2027",
                "month": "1",
                "journal_id": "A",
                "account": "4000",
                "debit_usd": "0",
                "credit_usd": "0.0001",
                "signed_usd": "-0.0001",
            },
        ]
        self.assertEqual(journals(rows)["journal_count"], 1)
        rows[1]["signed_usd"] = "0"
        with self.assertRaisesRegex(ValueError, "sign"):
            journals(rows)

    def test_bank_difference_column_is_not_trusted(self):
        row = {
            "opening_bank_cash_usd": "100",
            "cleared_receipts_usd": "10",
            "cleared_payments_usd": "5",
            "closing_bank_cash_usd": "105",
            "deposits_in_transit_usd": "3",
            "outstanding_payments_usd": "2",
            "ledger_cash_usd": "106",
            "difference_usd": "0",
        }
        self.assertEqual(bank_reconciliations([row]), 1)
        row["closing_bank_cash_usd"] = "104"
        with self.assertRaisesRegex(ValueError, "bank"):
            bank_reconciliations([row])
