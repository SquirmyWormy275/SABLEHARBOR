"""Release boundary tests; these deliberately exercise rejected inputs."""

import importlib.util
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools/build_package.py"
SPEC = importlib.util.spec_from_file_location("industrial_package", TOOL)
package = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package)


def entry(**changes):
    return {
        "path": "industrial/model.csv",
        "available_at": "2026-09-05",
        "effective_at": "2026-09-05",
        "availability_basis": "Selected dated synthetic company model",
        "fact_state": "SYNTHETIC_INSTANCE",
        "temporal_mode": "MODEL_WITH_FORECASTS",
        **changes,
    }


class PublicationBoundaryTests(unittest.TestCase):
    def test_nested_future_events_and_missing_period_role_do_not_bypass_cutoff(self):
        rejected = [
            {"available_at": "2026-12-01"},
            {"date": "2026-12-01", "status": "COMPLETE_SYNTHETIC"},
            {"year": "2026", "month": "12", "status": "ACTUAL"},
            {"month": "2026-12", "period_role": "SYNTHETIC_CALIBRATION"},
            {"effective_period_end": "2026-09-30", "period_role": "SYNTHETIC_CALIBRATION"},
        ]
        for row in rejected:
            with self.subTest(row=row), self.assertRaises(ValueError):
                package.validate_temporal_tree(
                    {"features": [{"properties": row}]}, "nested.geojson"
                )
        package.validate_temporal_tree(
            {
                "received": "2026-11-01T00:30:00-06:00",
                "record_origin": "SYNTHETIC_SERVICE_SIMULATION",
            },
            "calendar.json",
        )
        package.validate_temporal_tree(
            {"event_date": "2027-01-07", "state": "CONTRACTUAL_FUTURE_OBLIGATION"},
            "chronology.json",
        )
        self.assertFalse(package.eligible(entry(available_at="2026-09")))

    def test_unknown_availability_fails_closed(self):
        for value in (None, "", "2026-09-05T10:00:00"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                package.eligible(entry(available_at=value))

    def test_exact_day_boundary_and_known_commitment(self):
        self.assertTrue(package.eligible(entry()))
        self.assertFalse(package.eligible(entry(available_at="2026-09-06")))
        self.assertFalse(
            package.eligible(entry(effective_at="2027-01-07", temporal_mode="HISTORICAL_RECORD"))
        )
        self.assertTrue(
            package.eligible(entry(effective_at="2027-01-07", temporal_mode="COMMITMENT"))
        )
        self.assertFalse(
            package.eligible(
                entry(
                    effective_at="2027-01-07", available_at="2026-09-06", temporal_mode="COMMITMENT"
                )
            )
        )

    def test_september_full_month_is_forecast_at_september_fifth(self):
        package.validate_row_time(
            {"year": "2026", "through_month": "8", "period_role": "SYNTHETIC_CALIBRATION"},
            "statement.csv",
        )
        for row in (
            {"year": "2026", "through_month": "9", "period_role": "SYNTHETIC_CALIBRATION"},
            {"month": "2026-09-01", "period_role": "SYNTHETIC_CALIBRATION"},
            {"year": "2026", "month": "1", "period_role": "ACTUAL"},
        ):
            with self.subTest(row=row), self.assertRaises(ValueError):
                package.validate_row_time(row, "statement.csv")
        package.validate_row_time(
            {"year": "2026", "through_month": "9", "period_role": "FORECAST"}, "statement.csv"
        )

    def test_unsafe_and_nonparticipant_paths_rejected(self):
        for path in (
            "../secret",
            "/etc/passwd",
            "industrial/../../private",
            "industrial\\escape",
            "docs/handoffs/source.md",
            "industrial/history/old.md",
            "private/evaluator.json",
            "answers/hidden_truth.json",
        ):
            with self.subTest(path=path), self.assertRaises(ValueError):
                package.member_path(path)
        self.assertEqual(
            str(package.member_path("industrial/CASE_GUIDE.md")), "industrial/CASE_GUIDE.md"
        )

    def test_symlink_and_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "model.csv").write_text("id,value\n1,42\n")
            (root / "alias.csv").symlink_to(root / "model.csv")
            catalog = {
                "cutoff": package.CUTOFF,
                "version": package.VERSION,
                "artifacts": [entry(path="alias.csv")],
            }
            with self.assertRaisesRegex(ValueError, "linked"):
                package.reviewed_entries(catalog, root)
            catalog["artifacts"] = [entry(path="model.csv"), entry(path="model.csv")]
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                package.reviewed_entries(catalog, root)

    def test_independent_database_and_archive_builds_match(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outputs = []
            for index in range(2):
                stage = root / str(index)
                (stage / "industrial/finance").mkdir(parents=True)
                path = "industrial/finance/model.csv"
                (stage / path).write_text("id,amount,rate\n1,42,1\n2,-42,1.5\n")
                database = package.tabular_database(stage, [entry(path=path)])
                with sqlite3.connect(stage / database["path"]) as db:
                    self.assertEqual(
                        db.execute("SELECT SUM(amount) FROM finance__model").fetchone()[0], 0
                    )
                    self.assertEqual(
                        db.execute("SELECT SUM(rate) FROM finance__model").fetchone()[0], 2.5
                    )
                    self.assertEqual(
                        db.execute("SELECT source_path FROM artifact_lineage").fetchone()[0], path
                    )
                output = root / f"{index}.zip"
                package.write_zip(stage, output)
                with zipfile.ZipFile(output) as archive:
                    self.assertIsNone(archive.testzip())
                    self.assertTrue(
                        all(
                            info.date_time == (2026, 9, 5, 23, 59, 58)
                            for info in archive.infolist()
                        )
                    )
                outputs.append(output.read_bytes())
            self.assertEqual(*outputs)

    def test_database_rejects_injection_column(self):
        with tempfile.TemporaryDirectory() as temp:
            stage = Path(temp)
            (stage / "bad.csv").write_text('"x); DROP TABLE artifact_lineage;--"\n42\n')
            with self.assertRaisesRegex(ValueError, "Unsafe SQL"):
                package.tabular_database(stage, [entry(path="bad.csv")])


if __name__ == "__main__":
    unittest.main()
