import copy
import json
import sqlite3
import tempfile
from pathlib import Path
import unittest
from enterprise.runtime import model, planning, temporal, database


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.data = model.load()
        self.a = self.data["capital"]["implementation_assumptions"]

    def test_every_source_object_field_is_required(self):
        def objects(value, path=()):
            if isinstance(value, dict):
                yield path, value
                for k, v in value.items():
                    yield from objects(v, path + (k,))
            elif isinstance(value, list):
                for k, v in enumerate(value):
                    yield from objects(v, path + (k,))

        # Explicit saved schema, not whatever columns an exporter happens to emit.
        from jsonschema import Draft202012Validator

        validator = Draft202012Validator(
            json.loads(
                (model.ROOT / "enterprise/runtime/source_schema.json").read_text()
            )
        )
        validator.validate(self.data)
        for path, record in objects(self.data):
            for field in record:
                changed = copy.deepcopy(self.data)
                target = changed
                for key in path:
                    target = target[key]
                del target[field]
                with self.subTest(path=path, field=field):
                    self.assertFalse(validator.is_valid(changed))

    def test_rack_placement_conserves_bom_and_enforces_limits(self):
        result = planning.capacity(self.a, 2027, "base")
        self.assertGreaterEqual(result["racks"], result["gpu_systems"])
        items = [i for r in result["rack_placements"] for i in r["equipment"]]
        self.assertEqual(len({i["id"] for i in items}), len(items))
        self.assertEqual(sum(i["u"] for i in items), result["rack_u"])
        self.assertAlmostEqual(sum(i["peak_kw"] for i in items), result["peak_kw"])
        for rack in result["rack_placements"]:
            self.assertLessEqual(rack["peak_kw"], self.a["hardware"]["rack_max_kw"])
            self.assertLessEqual(rack["u"], self.a["hardware"]["rack_usable_u"])
            self.assertLessEqual(
                rack["weight_kg"], self.a["hardware"]["rack_max_weight_kg"]
            )
        self.a["hardware"]["rack_max_kw"] = 7
        with self.assertRaises(ValueError):
            planning.capacity(self.a, 2027, "base")

    def test_retention_and_context_are_causal(self):
        before = planning.capacity(self.a, 2027, "base")
        self.a["drivers"]["retention_years"] *= 2
        self.assertGreater(
            planning.capacity(self.a, 2027, "base")["storage_shelves"],
            before["storage_shelves"],
        )
        self.a["drivers"]["context_tokens"] *= 100
        self.assertGreater(
            planning.capacity(self.a, 2027, "base")["gpu_systems"],
            before["gpu_systems"],
        )

    def test_recovery_insufficiency_cannot_claim_acceptance(self):
        size = planning.capacity(self.a, 2027, "base", True)
        bad = planning.recovery_gate(size, 10, False, False, True)
        self.assertEqual(bad["design_gate"], "FAIL")
        self.assertEqual(bad["operating_recovery"], "NOT_ASSERTED")
        good = planning.recovery_gate(size, 25, True, True)
        self.assertEqual(good["design_gate"], "PASS")
        self.assertEqual(good["operating_recovery"], "NOT_ASSERTED")

    def test_shell_commissioning_operation_are_distinct(self):
        events = temporal.baseline_events(self.data)
        self.assertEqual(
            temporal.construction(events, "2026-09-03", "2026-09-11")["stage"],
            "NOT_ACQUIRED",
        )
        self.assertEqual(
            temporal.construction(events, "2026-09-04", "2026-09-11")["stage"],
            "LAND_ACQUIRED",
        )
        self.assertEqual(
            temporal.construction(events, "2026-09-11", "2026-09-04")["stage"],
            "NOT_ACQUIRED",
        )
        self.assertEqual(
            temporal.construction(events, "2036-12-31", "2036-12-31")["stage"],
            "PRECONSTRUCTION",
        )
        for seq, stage in enumerate(temporal.STAGES[2:], 3):
            event = dict(
                events[-1],
                id=f"TEST-{seq}",
                sequence=seq,
                stage=stage,
                effective_on=f"2028-0{seq}-01",
                recorded_on=f"2028-0{seq}-02",
                commissioned_kw=250 if seq >= 7 else 0,
            )
            events.append(event)
            result = temporal.construction(
                events, event["effective_on"], event["recorded_on"]
            )
            self.assertEqual(result["shell_complete"], seq >= 5)
            self.assertEqual(result["operating"], seq == 8)
            if stage == "SHELL_COMPLETE":
                self.assertEqual(result["commissioned_kw"], 0)
        events[-1]["origin"] = "FORECAST_NOT_EVIDENCE"
        with self.assertRaises(ValueError):
            temporal.construction(events, "2036-01-01", "2036-01-01")

    def test_revocation_is_enforced_in_live_disclosure(self):
        from enterprise.runtime.security import revoke_graph, authorize

        resource = {
            "payload": "secret",
            "tenant": "A",
            "purposes": ["work"],
            "classification": "OPEN",
            "rights": "INTERNAL_REUSE",
        }
        principal = {"id": "user", "tenant": "A", "purpose": "work"}
        self.assertEqual(authorize(resource, principal, "read", "2026-09-11"), "ALLOW")
        revoke_graph({"r": resource}, "r", held=True)
        self.assertIn("payload", resource)
        self.assertEqual(authorize(resource, principal, "read", "2026-09-11"), "DENY")

    def test_explicit_database_scope_and_source_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime.sqlite3"
            result = model.export(self.data)
            database.build(path, result)
            with sqlite3.connect(path) as db:
                self.assertEqual(
                    db.execute("select source_sha256 from source_identity").fetchone()[
                        0
                    ],
                    result["source_sha256"],
                )
                self.assertEqual(
                    {r[1] for r in db.execute("pragma table_info(runtime_site)")},
                    {
                        "id",
                        "entity_id",
                        "facility_id",
                        "geospatial_site_id",
                        "provider_id",
                        "status",
                        "operating",
                    },
                )
                self.assertEqual(db.execute("pragma foreign_key_check").fetchall(), [])
            with self.assertRaises(ValueError):
                database.build(path, result)
