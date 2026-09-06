from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

import build_red_wash_package as builder  # noqa: E402
import red_wash_projection_contract as projections  # noqa: E402
import validate_red_wash_record as validator  # noqa: E402
from red_wash_contract import (  # noqa: E402
    DATABASE_FILENAME,
    DATASETS,
    DIST,
    DIST_ALLOWED,
    GENERATED,
    GENERATED_ALLOWED,
    MANIFEST_FILENAME,
    SOURCE,
    SOURCE_FILENAMES,
    VISUAL_HASHES,
)

from sable_harbor.exports.safety import scan_generated_artifacts  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_payload_digest(payload: dict[str, str]) -> str:
    encoded = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def package_digests() -> dict[str, str]:
    paths = [entry for entry in GENERATED.iterdir() if entry.is_file()]
    paths.extend(entry for entry in DIST.iterdir() if entry.is_file())
    return {str(path.relative_to(REPOSITORY_ROOT)): digest(path) for path in sorted(paths)}


def rows(filename: str) -> list[dict[str, str]]:
    with (GENERATED / filename).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


class RedWashRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        builder.build()

    def test_core_identity_and_controlled_math(self) -> None:
        core = json.loads((SOURCE / "core_operating_data.json").read_text(encoding="utf-8"))
        self.assertEqual(core["record_id"], "SH-PS-RW-TOR-001")
        self.assertEqual(core["classification"], "PUBLIC_SYNTHETIC_DIEGETIC")
        self.assertNotIn("actual_through", core)
        self.assertEqual(core["synthetic_calibration_through"], "2026-08-31")
        self.assertEqual(core["mine_2026"]["ore_tons"], 175_000)
        self.assertEqual(core["mine_2026"]["contained_u3o8_lb"], 595_000)
        self.assertEqual(core["mine_2026"]["produced_u3o8_lb"], 547_400)
        self.assertEqual(core["mine_2026"]["sold_u3o8_lb"], 500_000)
        self.assertEqual(core["mine_2026"]["ending_finished_inventory_lb"], 172_400)
        self.assertEqual(core["finance_2026"]["revenue_usd"], 36_475_000)
        self.assertEqual(core["workforce_2026"]["total_fte"], 140)
        self.assertEqual(core["workforce_2026"]["pale_sun_business_layer"], 12)
        self.assertEqual(core["workforce_2026"]["red_wash_site"], 128)
        self.assertEqual(core["closure"]["opening_aro_usd"], 16_000_000)
        self.assertEqual(core["closure"]["current_cost_usd"], 25_000_000)

    def test_generated_database_passes_public_safety_scan(self) -> None:
        self.assertEqual(scan_generated_artifacts(DIST / DATABASE_FILENAME), [])

    def test_physical_and_resource_equations_are_driver_derived(self) -> None:
        core = json.loads((SOURCE / "core_operating_data.json").read_text(encoding="utf-8"))
        resource = core["resource_basis"]
        mine = core["mine_2026"]

        resource_contained = (
            Decimal(resource["indicated_tons"])
            * Decimal(2000)
            * Decimal(str(resource["grade_u3o8_pct"]))
            / Decimal(100)
        )
        resource_recoverable = (
            resource_contained * Decimal(str(resource["modeled_recovery_pct"])) / Decimal(100)
        )
        mine_contained = (
            Decimal(mine["ore_tons"])
            * Decimal(2000)
            * Decimal(str(mine["head_grade_u3o8_pct"]))
            / Decimal(100)
        )
        mine_produced = mine_contained * Decimal(str(mine["recovery_pct"])) / Decimal(100)
        self.assertEqual(resource_contained, resource["contained_lb"])
        self.assertEqual(resource_recoverable, resource["recoverable_lb"])
        self.assertEqual(mine_contained, mine["contained_u3o8_lb"])
        self.assertEqual(mine_produced, mine["produced_u3o8_lb"])
        self.assertEqual(
            mine["opening_finished_inventory_lb"] + mine["produced_u3o8_lb"] - mine["sold_u3o8_lb"],
            mine["ending_finished_inventory_lb"],
        )

        production = rows("monthly_production_2026.csv")
        inventory = rows("inventory_rollforward_2026.csv")
        for index, (production_row, inventory_row) in enumerate(
            zip(production, inventory, strict=True)
        ):
            calculated_contained = (
                Decimal(production_row["ore_tons"])
                * Decimal(2000)
                * Decimal(production_row["head_grade_u3o8_pct"])
                / Decimal(100)
            )
            calculated_produced = (
                Decimal(production_row["contained_u3o8_lb"])
                * Decimal(production_row["recovery_pct"])
                / Decimal(100)
            )
            self.assertLessEqual(
                abs(calculated_contained - Decimal(production_row["contained_u3o8_lb"])),
                Decimal("0.25"),
            )
            self.assertLessEqual(
                abs(calculated_produced - Decimal(production_row["u3o8_produced_lb"])),
                Decimal("0.001"),
            )
            self.assertEqual(
                Decimal(production_row["u3o8_sold_lb"])
                * Decimal(production_row["modeled_realized_price_usd_lb"]),
                Decimal(production_row["revenue_usd"]),
            )
            self.assertEqual(
                Decimal(inventory_row["opening_finished_u3o8_lb"])
                + Decimal(inventory_row["production_u3o8_lb"])
                - Decimal(inventory_row["sales_u3o8_lb"]),
                Decimal(inventory_row["ending_finished_u3o8_lb"]),
            )
            if index:
                self.assertEqual(
                    inventory_row["opening_finished_u3o8_lb"],
                    inventory[index - 1]["ending_finished_u3o8_lb"],
                )

    def test_dd_and_a_is_derived_from_disclosed_asset_and_depletion_drivers(self) -> None:
        core = json.loads((SOURCE / "core_operating_data.json").read_text(encoding="utf-8"))
        finance = core["finance_2026"]
        model = core["dd_and_a_model_2026"]
        self.assertNotIn("dd_and_a_incurred_usd", finance)
        self.assertEqual(model["method"], "COMPOSITE_UNITS_OF_PRODUCTION")
        self.assertEqual(model["fact_state"], "MODEL_PROPOSED")
        self.assertEqual(model["epistemic_state"], "SUPPORTED_ESTIMATE")
        basis = Decimal(core["transaction"]["operating_assets_usd"]) + Decimal(
            core["transaction"]["capitalized_rehabilitation_usd"]
        )
        production_factor = Decimal(core["mine_2026"]["produced_u3o8_lb"]) / Decimal(
            core["resource_basis"]["recoverable_lb"]
        )
        self.assertEqual(basis, 50_000_000)
        self.assertEqual(production_factor, Decimal("0.07"))
        self.assertEqual(builder.derive_dd_and_a_usd(core), 3_500_000)
        statement = {
            (row["statement"], row["line"]): Decimal(row["amount_usd"])
            for row in rows("financial_statements_2026.csv")
        }
        self.assertEqual(statement[("Inventory Cost Bridge", "2026 DD&A incurred")], 3_500_000)

    def test_source_backed_provenance_preserves_mixed_evidence_states(self) -> None:
        ownership = {row["owner_display_name"]: row for row in rows("ownership_history.csv")}
        northstar = ownership["Northstar Resources"]
        self.assertEqual(northstar["owner_display_name_state"], "PROVISIONAL")
        self.assertEqual(northstar["owner_legal_name"], "")
        self.assertEqual(northstar["owner_legal_name_state"], "OPEN")
        self.assertEqual(northstar["fact_state"], "PROVISIONAL_CANON")
        current = next(row for row in ownership.values() if row["end_date"] == "")
        self.assertEqual(current["owner_display_name"], "Sable Harbor")
        self.assertEqual(current["owner_display_name_state"], "LOCKED")
        self.assertEqual(current["owner_legal_name_state"], "OPEN")

        resources = rows("resource_basis.csv")
        self.assertTrue(all(row["epistemic_state"] == "SUPPORTED_ESTIMATE" for row in resources))
        quality = rows("quality_of_earnings.csv")
        self.assertTrue(
            all(
                row["fact_state"] == "SCENARIO_INPUT"
                for row in quality
                if row["line_role"] != "RESULT"
            )
        )
        result = next(row for row in quality if row["line_role"] == "RESULT")
        self.assertEqual((result["fact_state"], result["epistemic_state"]), ("DERIVED", "DERIVED"))

    def test_exact_file_and_schema_contract(self) -> None:
        self.assertEqual({entry.name for entry in SOURCE.iterdir()}, SOURCE_FILENAMES)
        self.assertEqual({entry.name for entry in GENERATED.iterdir()}, GENERATED_ALLOWED)
        self.assertEqual({entry.name for entry in DIST.iterdir()}, DIST_ALLOWED)
        for spec in DATASETS:
            with (GENERATED / spec.filename).open(newline="", encoding="utf-8") as stream:
                reader = csv.DictReader(stream)
                self.assertEqual(tuple(reader.fieldnames or ()), spec.fieldnames)
                self.assertGreater(len(list(reader)), 0)

    def test_generated_package_passes_independent_validator(self) -> None:
        result = validator.validate()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["failures"], [])
        self.assertGreater(result["checks_passed"], 100)

    def test_generation_manifest_has_constitutional_lineage_and_hashes(self) -> None:
        core = json.loads((SOURCE / "core_operating_data.json").read_text(encoding="utf-8"))
        manifest = json.loads((DIST / MANIFEST_FILENAME).read_text(encoding="utf-8"))
        required = {
            "scenario_id",
            "scenario_version",
            "generator_version",
            "input_version",
            "seed",
            "effective_period",
            "source_snapshot_ids",
            "built_at",
            "output_hashes",
        }
        self.assertTrue(required.issubset(manifest))
        self.assertEqual(manifest["scenario_id"], "red-wash-2025-2026")
        self.assertEqual(manifest["scenario_version"], core["version"])
        self.assertEqual(manifest["generator_version"], builder.GENERATOR_VERSION)
        self.assertEqual(manifest["input_version"], "red-wash-public-source/1.0.0")
        self.assertEqual(manifest["seed"], 20250718)
        self.assertEqual(
            manifest["effective_period"],
            {
                "from": "2024-08-19",
                "through": "2026-12-31",
                "synthetic_calibration_through": "2026-08-31",
            },
        )
        self.assertEqual(manifest["built_at"], "2026-09-05T00:00:00Z")
        self.assertRegex(manifest["built_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(
            manifest["built_at_semantics"],
            "DETERMINISTIC_CANON_PREPARED_DATE_AT_00_00_00Z_NOT_WALL_CLOCK",
        )

        snapshot_paths = {row["path"] for row in manifest["source_snapshot_ids"]}
        self.assertEqual(
            snapshot_paths,
            {
                *(f"red_wash/source/{name}" for name in SOURCE_FILENAMES),
                *VISUAL_HASHES,
                "assets/brand/red_wash_visual_manifest.json",
            },
        )
        self.assertTrue(
            all(
                row["repository"] == "SquirmyWormy275/SABLEHARBOR"
                and row["revision"].startswith("sha256:")
                and len(row["revision"]) == 71
                for row in manifest["source_snapshot_ids"]
            )
        )
        expected_output_hashes = {
            f"red_wash/generated/{spec.filename}": digest(GENERATED / spec.filename)
            for spec in DATASETS
        }
        expected_output_hashes[f"red_wash/dist/{DATABASE_FILENAME}"] = digest(
            DIST / DATABASE_FILENAME
        )
        self.assertEqual(manifest["output_hashes"], expected_output_hashes)
        self.assertEqual(manifest["output_hash_scope"], "ALL_NON_SELF_GENERATED_OUTPUTS")

    def test_vdr_hashes_bind_canonical_payload_not_identity_alone(self) -> None:
        fields = ("vdr_id", "category", "document", "effective_date", "review_status")
        records = rows("virtual_data_room_index.csv")
        for row in records:
            payload = {field: row[field] for field in fields}
            self.assertEqual(row["document_sha256"], canonical_payload_digest(payload))
            self.assertNotEqual(
                row["document_sha256"], hashlib.sha256(row["vdr_id"].encode()).hexdigest()
            )
        changed = {field: records[0][field] for field in fields}
        original_hash = canonical_payload_digest(changed)
        changed["document"] += " amended"
        self.assertNotEqual(original_hash, canonical_payload_digest(changed))

    def test_drill_coordinates_have_explicit_coherent_crs(self) -> None:
        collars = rows("drill_collars.csv")
        self.assertTrue(
            all(
                row["coordinate_crs"] == "NAD83 / UTM zone 13N"
                and row["epsg_code"] == "26913"
                and row["utm_zone"] == "13N"
                and row["horizontal_datum"] == "NAD83"
                and Decimal("339560") <= Decimal(row["easting_m"]) <= Decimal("343760")
                and Decimal("4684780") <= Decimal(row["northing_m"]) <= Decimal("4687780")
                for row in collars
            )
        )

    def test_deterministic_rebuild_is_byte_identical(self) -> None:
        before = package_digests()
        builder.build()
        after_first = package_digests()
        builder.build()
        after_second = package_digests()
        self.assertEqual(before, after_first)
        self.assertEqual(after_first, after_second)

    def test_compatibility_entry_point_delegates_without_drift(self) -> None:
        before = package_digests()
        completed = subprocess.run(
            [sys.executable, str(TOOLS / "generate_red_wash_corpus.py")],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(json.loads(completed.stdout)["status"], "PASS")
        self.assertEqual(before, package_digests())

    def test_unexpected_generated_file_is_refused(self) -> None:
        unexpected = GENERATED / "not_allowlisted.txt"
        unexpected.write_text("must be rejected\n", encoding="utf-8")
        try:
            completed = subprocess.run(
                [sys.executable, str(TOOLS / "build_red_wash_package.py")],
                cwd=REPOSITORY_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("unexpected file(s) in owned output", completed.stderr)
        finally:
            unexpected.unlink(missing_ok=True)
            builder.build()

    def test_stale_expected_output_is_refused(self) -> None:
        target = GENERATED / "ownership_history.csv"
        original = target.read_text(encoding="utf-8")
        target.write_text(
            original.replace("exploration and land assembly", "stale record"), encoding="utf-8"
        )
        try:
            completed = subprocess.run(
                [sys.executable, str(TOOLS / "validate_red_wash_record.py")],
                cwd=REPOSITORY_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("FAIL", completed.stdout)
            self.assertIn("manifest generated contract agrees", completed.stdout)
        finally:
            builder.build()

    def test_unexpected_source_file_is_refused_without_touching_real_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            copy = Path(temporary) / "source"
            shutil.copytree(SOURCE, copy)
            (copy / "stale.csv").write_text("stale\n", encoding="utf-8")
            with mock.patch.object(builder, "SOURCE", copy):
                with self.assertRaisesRegex(ValueError, "source filename allowlist mismatch"):
                    builder.load_inputs()

    def test_owned_output_root_symlink_is_refused_before_cleanup(self) -> None:
        with (
            tempfile.TemporaryDirectory() as target,
            tempfile.TemporaryDirectory(dir=ROOT) as holder,
        ):
            output_link = Path(holder) / "output-link"
            output_link.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "output root must not be a symlink"):
                builder.prepare_owned_directory(
                    output_link, ".test-owned", frozenset({".test-owned"})
                )

    def test_owned_output_marker_symlink_is_refused_before_cleanup(self) -> None:
        with (
            tempfile.TemporaryDirectory() as target,
            tempfile.TemporaryDirectory(dir=ROOT) as output,
        ):
            marker = ".test-owned"
            marker_link = Path(output) / marker
            marker_link.symlink_to(Path(target) / "external-marker")
            with self.assertRaisesRegex(ValueError, "output marker must not be a symlink"):
                builder.prepare_owned_directory(Path(output), marker, frozenset({marker}))

    def test_allowlisted_output_member_symlink_is_refused_before_cleanup(self) -> None:
        with (
            tempfile.TemporaryDirectory() as target,
            tempfile.TemporaryDirectory(dir=ROOT) as output,
        ):
            marker = ".test-owned"
            member = "controlled.csv"
            (Path(output) / marker).write_text("owned\n", encoding="utf-8")
            (Path(output) / member).symlink_to(Path(target) / "external.csv")
            with self.assertRaisesRegex(ValueError, "unexpected symlink in owned output"):
                builder.prepare_owned_directory(Path(output), marker, frozenset({marker, member}))

    def test_owned_output_root_must_resolve_beneath_red_wash(self) -> None:
        with tempfile.TemporaryDirectory() as outside:
            candidate = Path(outside) / "generated"
            with self.assertRaisesRegex(ValueError, "must resolve beneath"):
                builder.prepare_owned_directory(
                    candidate, ".test-owned", frozenset({".test-owned"})
                )
            self.assertFalse(candidate.exists())

    def test_sqlite_is_typed_constrained_and_foreign_keyed(self) -> None:
        database = DIST / DATABASE_FILENAME
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        connection.execute("PRAGMA foreign_keys = ON")
        self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        self.assertTrue({spec.table for spec in DATASETS}.issubset(table_names))
        production_types = {
            row[1]: row[2]
            for row in connection.execute("PRAGMA table_info(monthly_production_2026)")
        }
        self.assertEqual(production_types["ore_tons"], "INTEGER")
        self.assertEqual(production_types["head_grade_u3o8_pct"], "REAL")
        foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(inventory_rollforward_2026)"
        ).fetchall()
        self.assertEqual(len(foreign_keys), 1)
        self.assertEqual(foreign_keys[0][2], "monthly_production_2026")
        connection.close()

        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "package.sqlite3"
            shutil.copy2(database, copied)
            writable = sqlite3.connect(copied)
            writable.execute("PRAGMA foreign_keys = ON")
            with self.assertRaises(sqlite3.IntegrityError):
                writable.execute(
                    """INSERT INTO downhole_surveys VALUES
                       ('MISSING-HOLE',0,0,-90,'gyro',
                        'PUBLIC_SYNTHETIC_DIEGETIC','SYNTHETIC_INSTANCE','SCENARIO',
                        'SH-PS-RW-TOR-001')"""
                )
            writable.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                writable.execute(
                    """INSERT INTO employee_census_2026 VALUES
                       ('BAD-STATE','Red Wash','Test','Test','Red Wash','TEST',
                        'AUTHOR_PRIVATE','SYNTHETIC_INSTANCE','SCENARIO',
                        'SH-PS-RW-TOR-001')"""
                )
            writable.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                writable.execute(
                    """INSERT INTO monthly_production_2026 VALUES
                       ('2099-01-01','MANAGEMENT_FORECAST','not-an-integer',0.17,92,
                        1,1,1,1,1,'PUBLIC_SYNTHETIC_DIEGETIC',
                        'SYNTHETIC_INSTANCE','SCENARIO','SH-PS-RW-TOR-001')"""
                )
            writable.close()

    def test_weighted_average_inventory_and_financial_reconciliation(self) -> None:
        statement = {
            (row["statement"], row["line"]): Decimal(row["amount_usd"])
            for row in rows("financial_statements_2026.csv")
        }
        self.assertEqual(
            statement[("Inventory Cost Bridge", "Cash cost available for sale")]
            + statement[("Inventory Cost Bridge", "Cash cost released to sales")],
            statement[("Inventory Cost Bridge", "Ending finished inventory cash cost")],
        )
        self.assertEqual(
            statement[("Inventory Cost Bridge", "DD&A available for sale")]
            + statement[("Inventory Cost Bridge", "DD&A released to sales")],
            statement[("Inventory Cost Bridge", "Ending finished inventory DD&A")],
        )
        self.assertEqual(statement[("Income Statement", "Net income")], 902_095)
        self.assertEqual(statement[("Cash Flow", "Operating cash flow")], 1_522_479)
        self.assertEqual(statement[("Cash Flow", "Free cash flow")], -7_477_521)

    def test_limited_aru_bst_bridge_boundaries(self) -> None:
        bridge = json.loads((SOURCE / "aru_bst_bridge.json").read_text(encoding="utf-8"))
        self.assertEqual(bridge["source_commit_state"], "REQUIRES_EXACT_RELEASE_MANIFEST_BINDING")
        boundaries = bridge["boundaries"]
        self.assertFalse(boundaries["pre_existing_relationship"])
        self.assertEqual(boundaries["red_wash_2025_carrier"], "qualified external carriers")
        self.assertEqual(boundaries["annual_2025_revenue_impact_usd"], 0)
        self.assertEqual(boundaries["preliminary_interface_envelope_usd"], 15_000_000)
        self.assertFalse(boundaries["interface_envelope_booked"])
        self.assertFalse(boundaries["direct_uranium_custody_authorized"])
        self.assertFalse(boundaries["full_aru_case_authorized"])
        self.assertEqual(len(bridge["open_aru_fields"]), 32)

        rail = rows("rail_access_candidates.csv")
        self.assertEqual(len(rail), 1)
        self.assertEqual(rail[0]["direct_mine_connection"], "0")
        self.assertEqual(rail[0]["suitable_transload"], "0")
        self.assertEqual(rail[0]["uranium_capability"], "0")
        capex = rows("aru_red_wash_preliminary_capex.csv")
        quantified = [row for row in capex if row["amount_usd"]]
        self.assertEqual(len(quantified), 1)
        self.assertEqual(Decimal(quantified[0]["amount_usd"]), 15_000_000)
        self.assertTrue(
            all(row["amount_state"] == "OPEN" for row in capex if not row["amount_usd"])
        )
        custody = rows("custody_authority_matrix.csv")
        self.assertTrue(
            any(
                row["activity"] == "Physical custody and transport"
                and row["aru_bst_authority"] == "none"
                and row["status"] == "OPEN"
                for row in custody
            )
        )

    def test_public_structured_and_canon_projections_agree_with_source(self) -> None:
        core = json.loads((SOURCE / "core_operating_data.json").read_text(encoding="utf-8"))
        bridge = json.loads((SOURCE / "aru_bst_bridge.json").read_text(encoding="utf-8"))
        transaction_projection = json.loads(
            projections.TRANSACTION_PROJECTION_PATH.read_text(encoding="utf-8")
        )
        bridge_projection = json.loads(
            projections.BRIDGE_PROJECTION_PATH.read_text(encoding="utf-8")
        )
        self.assertEqual(
            transaction_projection["workforce_2026"],
            {
                "fact_state": "SCENARIO_INPUT",
                "pale_sun_red_wash_total": 140,
                "red_wash_site": 128,
                "pale_sun_business_layer": 12,
            },
        )
        self.assertNotIn("enterprise_total", transaction_projection["workforce_2026"])
        checks = projections.projection_checks(
            core,
            bridge,
            transaction_projection,
            bridge_projection,
            projections.TRANSACTION_CANON_PATH.read_text(encoding="utf-8"),
            projections.DECISION_ADDENDUM_PATH.read_text(encoding="utf-8"),
        )
        self.assertGreaterEqual(len(checks), 25)
        self.assertEqual([label for condition, label in checks if not condition], [])

    def test_projection_contract_rejects_structured_open_field_or_decision_drift(self) -> None:
        core = json.loads((SOURCE / "core_operating_data.json").read_text(encoding="utf-8"))
        bridge = json.loads((SOURCE / "aru_bst_bridge.json").read_text(encoding="utf-8"))
        transaction_projection = json.loads(
            projections.TRANSACTION_PROJECTION_PATH.read_text(encoding="utf-8")
        )
        bridge_projection = json.loads(
            projections.BRIDGE_PROJECTION_PATH.read_text(encoding="utf-8")
        )
        bridge_projection["open_aru_fields"] = bridge_projection["open_aru_fields"][:-1]
        bridge_projection["projection_contract"]["decision_ids"][-1] = "ARU-025"
        failures = [
            label
            for condition, label in projections.projection_checks(
                core,
                bridge,
                transaction_projection,
                bridge_projection,
                projections.TRANSACTION_CANON_PATH.read_text(encoding="utf-8"),
                projections.DECISION_ADDENDUM_PATH.read_text(encoding="utf-8"),
            )
            if not condition
        ]
        self.assertIn(
            "structured bridge preserves the exact ordered set of 32 OPEN ARU fields",
            failures,
        )
        self.assertIn(
            "structured bridge binds exact addendum decisions RW-017 through RW-025",
            failures,
        )

    def test_projection_contract_rejects_canon_numeric_drift(self) -> None:
        core = json.loads((SOURCE / "core_operating_data.json").read_text(encoding="utf-8"))
        bridge = json.loads((SOURCE / "aru_bst_bridge.json").read_text(encoding="utf-8"))
        transaction_projection = json.loads(
            projections.TRANSACTION_PROJECTION_PATH.read_text(encoding="utf-8")
        )
        bridge_projection = json.loads(
            projections.BRIDGE_PROJECTION_PATH.read_text(encoding="utf-8")
        )
        canon = projections.TRANSACTION_CANON_PATH.read_text(encoding="utf-8").replace(
            "| Modeled revenue | $36.475M | DERIVED |",
            "| Modeled revenue | $35.000M | DERIVED |",
        )
        failures = [
            label
            for condition, label in projections.projection_checks(
                core,
                bridge,
                transaction_projection,
                bridge_projection,
                canon,
                projections.DECISION_ADDENDUM_PATH.read_text(encoding="utf-8"),
            )
            if not condition
        ]
        self.assertIn(
            "Red Wash canon tables contain one exact projection of each selected case value",
            failures,
        )

    def test_no_deprecated_actual_label_in_generated_records(self) -> None:
        for spec in DATASETS:
            for row in rows(spec.filename):
                self.assertNotIn("ACTUAL", {value.strip().upper() for value in row.values()})

    def test_exact_owner_approved_visual_hashes(self) -> None:
        manifest = json.loads((DIST / MANIFEST_FILENAME).read_text(encoding="utf-8"))
        recorded = {row["path"]: row["sha256"] for row in manifest["visual_assets"]}
        self.assertEqual(recorded, VISUAL_HASHES)
        for relative, expected in VISUAL_HASHES.items():
            self.assertEqual(digest(REPOSITORY_ROOT / relative), expected)


if __name__ == "__main__":
    unittest.main()
