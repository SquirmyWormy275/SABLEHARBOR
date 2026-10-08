"""Fresh tiny SQLite/Store transitions and explicitly synthetic Root Source gates."""

import copy
import importlib.util
import unittest
from pathlib import Path

from enterprise.audit_suite.managed_history_integrity import (
    CURRENT_VALIDATION_FIELDS,
    ManagedHistoryRuntime,
    validate_runtime_source_upgrade,
    write_new,
)
from enterprise.audit_suite.serialized_json import canonical_projection
from enterprise.audit_suite.store import DomainError, digest

spec = importlib.util.spec_from_file_location(
    "neutral_portable_runtime_cohort", Path(__file__).with_name("test_managed_history_integrity.py")
)
cohort = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cohort)


class _RealFixture(unittest.TestCase):
    # Reuse the existing repository's genuine tiny Store/codec fixture only.
    # No inherited regression tests are silently rerun by this focused module.
    seed_count = 1
    seed_body_bytes = 32
    setUp = cohort.RuntimeTests.setUp
    tearDown = cohort.RuntimeTests.tearDown
    command = cohort.RuntimeTests.command
    append = cohort.RuntimeTests.append
    reopen = cohort.RuntimeTests.reopen


class ProjectionTests(_RealFixture):
    seed_body_bytes = 131072

    def test_full_and_validation_entries_have_same_event_metadata_and_projection(self):
        with self.runtime.locked(), self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            full = self.runtime._read_current_entry(db, 1)
            projected = self.runtime._read_current_entry(db, 1, validation_only=True)
        self.assertEqual(
            {k: full[k] for k in full if k != "state"},
            {k: projected[k] for k in projected if k != "state"},
        )
        self.assertEqual(
            projected["state"], {k: full["state"][k] for k in CURRENT_VALIDATION_FIELDS}
        )
        self.assertNotIn("neutral_padding", projected["state"])
        self.assertEqual(
            self.runtime.selected(self.operator["id"], self.eid)["latest"]["state"], full["state"]
        )

    def test_validation_has_no_partial_public_selected_entries(self):
        value = self.runtime.validate_current(self.operator["id"], self.eid)
        self.assertEqual(value["selected"], {})
        self.assertEqual(value["selected_integrity_reference"], {})
        self.assertEqual(set(value["latest"]["state"]), set(CURRENT_VALIDATION_FIELDS))
        self.assertIn(
            "neutral_padding",
            self.runtime.selected(self.operator["id"], self.eid)["latest"]["state"],
        )

    def test_projection_validates_ignored_malformed_bytes(self):
        for raw in ('{"id":"x","ignored":[}', '{"id":"x","ignored":"\\uD800"}'):
            with self.subTest(raw=raw), self.assertRaises((ValueError, UnicodeError)):
                canonical_projection(raw, CURRENT_VALIDATION_FIELDS)

    def test_validation_refuses_fresh_primary_raw_tamper(self):
        with self.runtime.locked(), self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            raw = db.execute("SELECT state FROM engagements").fetchone()[0]
            db.execute("UPDATE engagements SET state=?", (" " + raw,))
            try:
                with self.assertRaises(DomainError):
                    self.runtime._read_current_entry(db, 1, validation_only=True)
            finally:
                db.rollback()

    def test_validation_refuses_foreign_actor_and_still_checks_company(self):
        with self.assertRaises(DomainError):
            self.runtime.validate_current("USER-FOREIGN", self.eid)
        self.world.refuse = True
        with self.assertRaises(DomainError):
            self.runtime.validate_current(self.operator["id"], self.eid)

    def test_validation_cannot_select_historical_revision(self):
        self.append()
        with self.runtime.locked(), self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            with self.assertRaises(DomainError):
                self.runtime._read_entry(db, 1, validation_only=True)
        self.assertIn(
            "neutral_padding",
            self.runtime.selected(self.operator["id"], self.eid, revisions=[1])["selected"][1][
                "state"
            ],
        )

    def test_refresh_uses_validation_path_but_full_selected_is_unchanged(self):
        self.room.sealed = True
        cohort.RetainedWorkroom._refresh_integrity(self.room, self.operator["id"])
        self.assertEqual(
            self.runtime.selected(self.operator["id"], self.eid)["latest"]["state"][
                "neutral_padding"
            ],
            "x" * self.seed_body_bytes,
        )


class SourceUpgradeTests(_RealFixture):
    def setUp(self):
        super().setUp()
        self.old_map = {
            "neutral_only": "c" * 64,
            "managed_history_integrity.py": "a" * 64,
            "persistent_company_service.py": "d" * 64,
            "retained_explanation_service.py": "e" * 64,
        }
        self.base = self.base | {"source_map_sha256": digest(self.old_map)}
        base_pin = write_new(self.root, "NEUTRAL_BASE_WITH_SOURCE_MAP.json", self.base)
        self.choice = self.choice | {"base": base_pin}
        self.old_config = {
            "schema": "SYNTHETIC_NEUTRAL_ONLY",
            "code_pins": self.old_map,
            "history_integrity": copy.deepcopy(self.choice),
            "authority_head": {"neutral": "old"},
            "session_revocations": {},
            "workroom_binding": {"path": "NEUTRAL_ONLY", "sha256": "b" * 64},
        }
        self.room.config = copy.deepcopy(self.old_config)
        self.runtime = ManagedHistoryRuntime(self.room, self.choice)
        self.runtime.bootstrap()
        self.historical = write_new(self.root, "NEUTRAL_HISTORICAL_CONFIG.json", self.old_config)
        self.current_map = self.old_map | {
            "managed_history_integrity.py": "f" * 64,
            "persistent_company_service.py": "9" * 64,
        }
        self.review = write_new(
            self.root,
            "NEUTRAL_ROOT_SOURCE_REVIEW.json",
            {
                "schema": "SH_ROOT_MANAGED_VALIDATION_PROJECTION_SOURCE_REVIEW_V1",
                "runtime_source_upgrade_sources_accepted": True,
                "current_code_pins": self.current_map,
            },
        )
        self.adopted = write_new(
            self.root,
            "NEUTRAL_ROOT_ADOPTION.json",
            {
                "schema": "SH_ROOT_ACTUAL_MANAGED_VALIDATION_PROJECTION_ADOPTION_V1",
                "actual_runtime_source_upgrade_adopted": True,
                "current_code_pins": self.current_map,
                "selected_source_review": self.review,
            },
        )
        self.admission = {
            "schema": "SH_ROOT_ACTUAL_MANAGED_HISTORY_RUNTIME_SOURCE_UPGRADE_ADMISSION_V1",
            "base": self.choice["base"],
            "historical_retained_configuration": self.historical,
            "current_code_pins": self.current_map,
            "changed_code_pin_names": [
                "managed_history_integrity.py",
                "persistent_company_service.py",
            ],
            "Root_source_review": self.review,
            "Root_actual_adoption": self.adopted,
            "actual_runtime_source_upgrade_accepted": True,
            "base_and_checkpoints_rewritten": False,
            "new_semantic_replay_claimed": False,
        }
        self.upgrade_pin = write_new(
            self.root, "NEUTRAL_RUNTIME_SOURCE_UPGRADE.json", self.admission
        )
        self.upgraded_choice = self.choice | {"runtime_source_admission": self.upgrade_pin}
        self.current_config = self.old_config | {
            "code_pins": self.current_map,
            "history_integrity": self.upgraded_choice,
            "authority_head": {"neutral": "new"},
            "session_revocations": {"neutral": 1},
        }

    def apply_upgrade(self):
        self.room.config = self.current_config
        self.choice = self.upgraded_choice
        self.runtime = ManagedHistoryRuntime(self.room, self.choice)
        self.runtime.bootstrap()

    def reject(self, admission=None, config=None):
        pin = write_new(
            self.root,
            "NEUTRAL_BAD_" + str(len(list(self.root.iterdir()))) + ".json",
            self.admission if admission is None else admission,
        )
        with self.assertRaises(DomainError):
            validate_runtime_source_upgrade(
                pin,
                base_pin=self.choice["base"],
                base=self.base,
                config=self.current_config if config is None else config,
            )

    def test_real_signed_checkpoint_and_base_references_preserved_across_upgrade_and_reopen(self):
        self.append()
        old_base = Path(self.choice["base"]["path"]).read_bytes()
        old_ledger = {
            p.name: p.read_bytes() for p in Path(self.choice["ledger_directory"]).iterdir()
        }
        refs = {r: self.runtime.catalogue.reference(r) for r in (1, 2)}
        self.apply_upgrade()
        self.reopen()
        self.assertEqual({r: self.runtime.catalogue.reference(r) for r in (1, 2)}, refs)
        self.assertEqual(Path(self.choice["base"]["path"]).read_bytes(), old_base)
        self.assertEqual(
            {p.name: p.read_bytes() for p in Path(self.choice["ledger_directory"]).iterdir()},
            old_ledger,
        )
        self.assertEqual(
            self.runtime.selected(self.operator["id"], self.eid)["latest"]["revision"], 2
        )

    def test_default_without_admission_still_refuses_new_map(self):
        self.room.config = self.current_config
        with self.assertRaises(DomainError):
            ManagedHistoryRuntime(self.room, self.choice)

    def test_false_acceptance_or_rewritten_base_or_new_replay_refuses(self):
        for field, value in (
            ("actual_runtime_source_upgrade_accepted", False),
            ("base_and_checkpoints_rewritten", True),
            ("new_semantic_replay_claimed", True),
        ):
            with self.subTest(field=field):
                self.reject(self.admission | {field: value})

    def test_foreign_base_and_wrong_old_map_refuse(self):
        self.reject(self.admission | {"base": self.choice["base"] | {"sha256": "0" * 64}})
        wrong = write_new(
            self.root,
            "NEUTRAL_FOREIGN_HISTORICAL_MAP.json",
            self.old_config | {"code_pins": self.current_map},
        )
        self.reject(self.admission | {"historical_retained_configuration": wrong})

    def test_unlisted_filename_or_changed_shared_pin_refuses(self):
        self.reject(self.admission | {"changed_code_pin_names": []})
        current = self.current_config | {"code_pins": self.current_map | {"neutral_only": "0" * 64}}
        self.reject(
            self.admission
            | {
                "current_code_pins": current["code_pins"],
                "changed_code_pin_names": ["managed_history_integrity.py", "neutral_only"],
            },
            current,
        )

    def test_changed_binding_or_source_configuration_refuses(self):
        self.reject(
            config=self.current_config
            | {"workroom_binding": {"path": "FOREIGN", "sha256": "b" * 64}}
        )

    def test_wrong_current_map_or_adoption_refuses(self):
        self.reject(self.admission | {"current_code_pins": self.old_map})
        false = write_new(
            self.root, "NEUTRAL_FALSE_ADOPTION.json", {"schema": "SOURCE_ONLY_NO_ADOPTION"}
        )
        self.reject(self.admission | {"Root_actual_adoption": false})

    def test_fresh_admission_bytes_tamper_refuses_normal_get(self):
        self.apply_upgrade()
        Path(self.upgrade_pin["path"]).write_text("{}\n")
        with self.assertRaises(DomainError):
            self.store.get(self.operator["id"], self.eid)


if __name__ == "__main__":
    unittest.main()
