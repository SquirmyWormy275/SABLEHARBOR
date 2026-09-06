"""Release boundary, exact decimal transport and deterministic container tests."""

import copy
import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from industrial.planning import package


def entry(path, available="2026-09-06"):
    return {
        "path": path,
        "kind": "FINANCIAL_DATA",
        "scope": "PLANNING",
        "available_at": available,
        "effective_at": available,
        "temporal_mode": "MODEL_WITH_FORECASTS",
        "fact_state": "PROVISIONAL_PLANNING_MODEL",
        "record_origin": "PUBLIC_SYNTHETIC_MODEL",
        "availability_basis": "Explicit synthetic fixture",
    }


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old = entry("industrial/generated/finance/old.csv", "2026-09-05")
        self.new = entry("industrial/generated/planning/forecast/monthly_statements.csv")
        self.write_csv(
            self.old["path"], ["year", "period_role"], [["2025", "SYNTHETIC_CALIBRATION"]]
        )
        self.fields = ["scenario", "year", "month", "period_role", "account", "amount_usd", "note"]
        self.rows = [
            ["base", "2027", "1", "CONDITIONAL_FORECAST", "00017", "9007199254740993.0001", ""],
            ["downside", "2028", "2", "CONDITIONAL_FORECAST", "00100", "-0.0000", "=SUM(A1:A9)"],
            ["expansion", "2031", "12", "CONDITIONAL_FORECAST", "00200", "0.0001", "first\nsecond"],
        ]
        self.write_csv(self.new["path"], self.fields, self.rows)
        self.catalog = {
            "version": package.VERSION,
            "cutoff": package.CUTOFF,
            "artifacts": [self.old, self.new],
        }
        preservation = self.root / "industrial/planning/source/preservation.json"
        preservation.parent.mkdir(parents=True)
        preservation.write_text(
            json.dumps(
                {
                    "artifacts": [
                        {
                            "path": self.old["path"],
                            "sha256": package.legacy.digest(self.root / self.old["path"]),
                        }
                    ]
                }
            )
        )
        old_catalog = self.root / "industrial/source/participant_catalog.json"
        old_catalog.parent.mkdir(parents=True)
        old_catalog.write_text(json.dumps({"artifacts": [self.old]}))

    def write_csv(self, name, fields, rows):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(fields)
            writer.writerows(rows)

    def test_allowlist_omits_unreviewed_files_and_preserves_old_metadata(self):
        (self.root / "private.db").write_bytes(b"excluded raw database")
        entries = package.reviewed_entries(self.catalog, self.root)
        self.assertEqual(len(entries), 2)
        changed = copy.deepcopy(self.catalog)
        changed["artifacts"][0]["effective_at"] = "2026-09-06"
        with self.assertRaisesRegex(ValueError, "v1 bytes or metadata"):
            package.reviewed_entries(changed, self.root)
        changed["artifacts"] = changed["artifacts"][1:]
        with self.assertRaisesRegex(ValueError, "omitted accepted v1"):
            package.reviewed_entries(changed, self.root)

    def test_paths_reject_traversal_aliases_and_reserved_outputs(self):
        for name in [
            "../outside.csv",
            "/outside.csv",
            "industrial//bad.csv",
            "README.md",
            ".hidden/anything.csv",
            "industrial/evaluator_key.csv",
        ]:
            with self.subTest(name=name):
                changed = copy.deepcopy(self.catalog)
                changed["artifacts"].append(entry(name))
                with self.assertRaises(ValueError):
                    package.reviewed_entries(changed, self.root)
        changed = copy.deepcopy(self.catalog)
        changed["artifacts"].append(changed["artifacts"][-1])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            package.reviewed_entries(changed, self.root)

    def test_raw_database_and_symlink_are_rejected_even_if_allowlisted(self):
        raw = self.root / "unreviewed.sqlite3"
        raw.write_bytes(b"not a participant database")
        changed = copy.deepcopy(self.catalog)
        changed["artifacts"].append(entry(raw.name))
        with self.assertRaisesRegex(ValueError, "Raw database"):
            package.reviewed_entries(changed, self.root)
        linked = self.root / "linked.csv"
        linked.symlink_to(self.root / self.new["path"])
        changed["artifacts"][-1] = entry(linked.name)
        with self.assertRaisesRegex(ValueError, "Linked participant"):
            package.reviewed_entries(changed, self.root)

    def test_temporal_gate_rejects_nested_completed_future_and_backdating(self):
        rows = copy.deepcopy(self.rows)
        rows[0][-1] = json.dumps({"event_date": "2029-01-01", "status": "COMPLETED"})
        self.write_csv(self.new["path"], self.fields, rows)
        with self.assertRaisesRegex(ValueError, "future completed"):
            package.reviewed_entries(self.catalog, self.root)
        self.write_csv(self.new["path"], self.fields, self.rows)
        changed = copy.deepcopy(self.catalog)
        changed["artifacts"][1]["available_at"] = "2026-09-05"
        with self.assertRaisesRegex(ValueError, "backdated"):
            package.reviewed_entries(changed, self.root)
        rows[0][-1] = json.dumps({"available_at": "2026-09-07", "period_role": "FORECAST"})
        self.write_csv(self.new["path"], self.fields, rows)
        with self.assertRaisesRegex(ValueError, "unavailable"):
            package.reviewed_entries(self.catalog, self.root)

    def test_sqlite_retains_every_decimal_identifier_and_empty_string(self):
        result = package.tabular_database(self.root, [self.new])
        name = result["tables"][0]["table"]
        with sqlite3.connect(self.root / result["path"]) as database:
            actual = database.execute(f'SELECT * FROM "{name}" ORDER BY rowid').fetchall()
            self.assertEqual([list(row) for row in actual], self.rows)
            self.assertTrue(
                all(r[2] == "TEXT" for r in database.execute(f'PRAGMA table_info("{name}")'))
            )
            lineage = database.execute(
                "SELECT source_sha256, row_count FROM artifact_lineage"
            ).fetchone()
            self.assertEqual(lineage, (package.legacy.digest(self.root / self.new["path"]), "3"))
        first_hash = package.legacy.digest(self.root / result["path"])
        package.tabular_database(self.root, [self.new])
        self.assertEqual(first_hash, package.legacy.digest(self.root / result["path"]))

    def test_malformed_or_duplicate_csv_cannot_be_silently_coerced(self):
        for fields, rows in [
            (["amount_usd", "amount_usd"], [["1", "2"]]),
            (["amount_usd"], [["1", "unexpected"]]),
        ]:
            self.write_csv(self.new["path"], fields, rows)
            with self.assertRaises(ValueError):
                package.tabular_database(self.root, [self.new])

    def test_workbook_is_exact_literal_text_and_rebuilds_identically(self):
        result = package.workbook(self.root, [self.new])
        first = (self.root / result["path"]).read_bytes()
        self.assertTrue(result["all_evidence_cells_exact_text"])
        self.assertTrue(result["ooxml_readback_verified"])
        self.assertEqual(result["tables"][0]["rows"], 3)
        package.workbook(self.root, [self.new])
        self.assertEqual(first, (self.root / result["path"]).read_bytes())

    def test_zip_population_hashes_checksums_and_repeat_are_verified(self):
        stage = self.root / "stage"
        stage.mkdir()
        (stage / "data.csv").write_bytes(b"amount_usd\n0.0001\n")
        (stage / "CHECKSUMS.sha256").write_text(
            f"{package.legacy.digest(stage / 'data.csv')}  data.csv\n"
        )
        one, two = self.root / "one.zip", self.root / "two.zip"
        package.legacy.write_zip(stage, one)
        package.legacy.write_zip(stage, two)
        self.assertEqual(one.read_bytes(), two.read_bytes())
        package.validate_archive(one, stage)
        (stage / "data.csv").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            package.validate_archive(one, stage)

    def test_stale_acceptance_cannot_be_rebound_by_packaging(self):
        with patch.object(package.subprocess, "check_output", side_effect=["abc123\n", ""]):
            with patch.object(package.integrity, "preservation", return_value=199):
                with patch.object(
                    package.integrity,
                    "verify_acceptance_binding",
                    side_effect=ValueError("Acceptance is stale"),
                ):
                    with self.assertRaisesRegex(ValueError, "Acceptance is stale"):
                        package.build()

    def test_dirty_tree_requires_explicit_development_mode_before_any_build(self):
        with patch.object(
            package.subprocess, "check_output", side_effect=["abc123\n", " M source.py\n"]
        ):
            with patch.object(package.integrity, "preservation") as preserve:
                with self.assertRaisesRegex(ValueError, "clean source commit"):
                    package.build()
                preserve.assert_not_called()


if __name__ == "__main__":
    unittest.main()
