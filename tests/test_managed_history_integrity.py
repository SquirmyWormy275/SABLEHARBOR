"""Real selected Store/codec/SQL/Ed25519 transitions, neutral fixtures only.

The tiny Root/proof envelopes are SYNTHETIC NEUTRAL TEST INPUTS, not operational
replay or Root acceptance. Fresh Company source calls use a counted empty
neutral World; exact production custody/birth/current functions are retained.
"""

import contextlib
import hashlib
import json
import sqlite3
import tempfile
import threading
import types
import unittest
from contextlib import contextmanager
from pathlib import Path

from enterprise.audit_suite.history_integrity_reference import validate_reference
from enterprise.audit_suite.managed_history_integrity import (
    BASE_SCHEMA,
    ManagedHistoryRuntime,
    audit_frame_inventory,
    file_pin,
    frame_vector,
    node_inventory,
    write_new,
)
from enterprise.audit_suite.persistent_company_service import RetainedWorkroom
from enterprise.audit_suite.sealed_history_store import SealedHistoryStore, prepare_tail
from enterprise.audit_suite.source_library_audit import EMPTY_WORKROOM
from enterprise.audit_suite.store import DomainError, Store, canonical, digest, identifier


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


adapter = types.SimpleNamespace(
    Store=Store, SealedHistoryStore=SealedHistoryStore, prepare_tail=prepare_tail, file_sha=file_sha
)


class NeutralWorld:
    def __init__(self, root):
        self.root = root
        self.database = root / "company-neutral.sqlite3"
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            db.execute("CREATE TABLE collections(command_id TEXT,receipt TEXT)")
            db.commit()
        self.database.chmod(0o600)
        self.initialization = {"initialized_at": "2026-01-01T00:00:00+00:00"}
        self.operator = types.SimpleNamespace(principal=identifier("USER"))
        self.calls = 0
        self.mutex = threading.RLock()
        self.refuse = False
        self.native = {}

    @contextlib.contextmanager
    def locked(self):
        with self.mutex:
            yield

    def verify(self, _return_native_rows=False):
        self.calls += 1
        if self.refuse:
            raise DomainError("NEUTRAL changed Company source/clock boundary")
        return ({}, self.native) if _return_native_rows else {}


class RuntimeTests(unittest.TestCase):
    seed_count = 1
    seed_body_bytes = 32

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="neutral-real-history-")
        self.root = Path(self.tmp.name)
        self.root.chmod(0o700)
        self.original = adapter.Store(self.root / "original")
        (self.original.root / "artifacts").mkdir(mode=0o700)
        self.operator = self.original.provision("FICTIONAL operator", ["instructor"])
        self.learner = self.original.provision("FICTIONAL learner", ["learner"])
        self.reviewer = self.original.provision("FICTIONAL reviewer", ["reviewer"])
        self.selected = {"company": "COMPANY-NEUTRAL", "branch": "BRANCH-NEUTRAL"}
        state = {
            "engineering_neutral_only": True,
            "mode": "CLEAN",
            "phase": "READY",
            "tasks": [{"id": "TASK-NEUTRAL", "status": "NOT_STARTED", "conclusion": "NOT_RUN"}],
            **{name: [] for name in EMPTY_WORKROOM},
            "scope": {"soc2_categories": ["Security"]},
            "simulated_at": "2027-12-31T09:00:00+00:00",
            "company_source_binding": self.selected,
            "evidence_acquisition": "COMPANY_SOURCE_COLLECTION",
        }
        self.state = self.original.create(self.operator["id"], state, "neutral-birth")
        self.eid = self.state["id"]
        self.original.grant(self.eid, self.learner["id"], "learn")
        self.original.grant(self.eid, self.reviewer["id"], "review")
        self.prefix_sha = adapter.file_sha(self.original.db_path)
        choice = adapter.prepare_tail(
            self.original, self.operator["id"], self.eid, self.root / "tail", state_codec=True
        )
        self.store = adapter.SealedHistoryStore(
            self.original.root, choice["path"], choice["sha256"]
        )
        # One genuine tiny pre-certificate event makes the base graph nonempty.
        for index in range(self.seed_count):
            self.store.command(
                self.operator["id"],
                self.eid,
                self.command("neutral-seed-" + str(index), index),
                lambda state, command, actor, index=index: (
                    state
                    | {
                        "note": "FICTIONAL seed " + str(index),
                        "neutral_padding": "x" * self.seed_body_bytes,
                    }
                ),
                permissions={"instruct"},
            )
        self.world = NeutralWorld(self.root)
        self.room = types.SimpleNamespace(
            root=self.original.root,
            sealed_store=self.store,
            engagement=self.eid,
            selected=self.selected,
            _integrity_lock=threading.RLock(),
            world=self.world,
            binding={
                "mode": "CLEAN",
                "scope": state["scope"],
                "initial_simulated_at": state["simulated_at"],
                "identities": {
                    "operator": self.operator["id"],
                    "auditor": self.learner["id"],
                    "reviewer": self.reviewer["id"],
                },
                "task_count": 1,
                "zero_workroom_counts": {name: 0 for name in EMPTY_WORKROOM},
            },
            binding_sha256="b" * 64,
            config={"code_pins": {"neutral_only": "c" * 64}},
            check_pins=lambda: None,
        )
        for name in ("_verify_memberships", "_verify_integrity_descriptors", "verify_artifacts"):
            setattr(self.room, name, types.MethodType(getattr(RetainedWorkroom, name), self.room))
        lock = self.root / "room.lock"
        lock.write_bytes(b"")
        lock.chmod(0o600)
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = audit_frame_inventory(self.store, db)
            nodes = node_inventory(db)
            entries = [
                {
                    key: row[key]
                    for key in (
                        "actor",
                        "recorded_at",
                        "previous_hash",
                        "command_id",
                        "hash",
                        "revision",
                    )
                }
                | {"state": json.loads(row["state"]), "command": json.loads(row["command"])}
                for row in db.execute("SELECT * FROM events ORDER BY revision")
            ]
        self.actual_base_history_sha = digest(entries)
        final = rows[-1]
        # This is a fixture digest, explicitly not a real global replay claim.
        replay = {
            "schema": "SH_INDEPENDENT_CORRECTED_NATIVE_PAIRED_FIELDWORK_REPLAY_V1",
            "modes": {
                "CLEAN": {
                    "engagement_id": self.eid,
                    "final_revision": self.seed_count,
                    "last_event_sha256": final["event_sha256"],
                    "final_state_sha256": final["state_sha256"],
                    "history_sha256": self.actual_base_history_sha,
                }
            },
        }
        self.replay_pin = write_new(self.root, "NEUTRAL_REPLAY.json", replay)
        images = {"prefix": file_pin(self.store.prefix_path), "tail": file_pin(self.store.db_path)}
        acceptance = {
            "schema": "SH_ROOT_ACTUAL_CORRECTED_NATIVE_FULL_REPLAY_ACCEPTANCE_V1",
            "actual_9e_complete_replay_and_genuine_wait0_accepted": True,
            "actual_independent_fieldwork_replay_accepted": True,
            "actual_proof": self.replay_pin,
            "fresh_refs": [
                {
                    "path": value["path"],
                    "sha256": value["sha256"],
                    "bytes": value["bytes"],
                    "metadata9": list(value["metadata"].values()),
                }
                for value in images.values()
            ],
        }
        accepted = write_new(self.root, "NEUTRAL_ACCEPTANCE.json", acceptance)
        self.base = {
            "schema": BASE_SCHEMA,
            "engagement_id": self.eid,
            "mode": "CLEAN",
            "base_revision": self.seed_count,
            "accepted_replay": self.replay_pin,
            "Root_replay_acceptance": accepted,
            "images": images,
            "image_provenance": {"kind": "EXACT_ACCEPTED_REPLAY_IMAGES", "admission": None},
            "frames": rows,
            "frame_vector_sha256": frame_vector(rows),
            "custody": {"files": {}, "custody": {}},
            "known_prefix_sha256": {str(self.seed_count): self.actual_base_history_sha},
            "born_binding_sha256": self.room.binding_sha256,
            "source_map_sha256": digest(self.room.config["code_pins"]),
            "metadata_inventory_is_not_a_new_full_replay": True,
            "node_inventory": nodes,
        }
        pin = write_new(self.root, "NEUTRAL_BASE.json", self.base)
        ledger = self.store.manifest_path.parent / "MANAGED_HISTORY_INTEGRITY"
        ledger.mkdir(mode=0o700)
        self.choice = {"base": pin, "ledger_directory": str(ledger)}
        self.runtime = ManagedHistoryRuntime(self.room, self.choice)
        self.runtime.bootstrap()

    def tearDown(self):
        self.tmp.cleanup()

    def command(self, identifier="neutral-append", expected=1):
        return {
            "command_id": identifier,
            "expected_revision": expected,
            "kind": "neutral.note",
            "payload": {"text": "FICTIONAL current note"},
        }

    def append(self, command=None, reducer=None, actor=None):
        return self.store.command(
            actor or self.operator["id"],
            self.eid,
            command or self.command(),
            reducer or (lambda state, command, actor: state | {"note": command["payload"]["text"]}),
            permissions={"instruct"},
        )

    def reopen(self):
        self.store = adapter.SealedHistoryStore(
            self.original.root,
            self.store.manifest_path,
            self.store.manifest_sha256,
            authority_head=self.store.authority_head,
            session_revocations=dict(self.store.session_authority.known_revocations),
        )
        self.room.sealed_store = self.store
        self.runtime = ManagedHistoryRuntime(self.room, self.choice)
        self.runtime.bootstrap()

    def test_real_append_signed_checkpoint_and_reopen(self):
        self.assertEqual(self.append()["revision"], 2)
        reference = self.runtime.catalogue.reference(2)
        self.assertEqual(reference["kind"], "MANAGED_STORE_CHECKPOINT")
        self.reopen()
        self.assertEqual(self.runtime.catalogue.reference(2), reference)
        self.assertEqual(self.store.get(self.learner["id"], self.eid)["revision"], 2)
        self.assertEqual(adapter.file_sha(self.original.db_path), self.prefix_sha)

    def test_selected_v2_omits_unknown_legacy_array_digest(self):
        self.append()
        result = self.runtime.selected(self.operator["id"], self.eid, revisions=[1, 2])
        self.assertEqual(result["prefix_sha256"], {1: self.actual_base_history_sha})
        self.assertNotIn("history_sha256", result)
        validate_reference(
            result["selected_integrity_reference"][2],
            engagement=self.eid,
            revision=2,
            state_sha256=digest(result["selected"][2]["state"]),
            event_sha256=result["selected"][2]["hash"],
        )

    def test_duplicate_real_command_does_not_issue(self):
        first = self.append()
        sequence = self.runtime.catalogue.sequence
        self.assertEqual(self.append(), first)
        self.assertEqual(self.runtime.catalogue.sequence, sequence)

    def test_real_rollback_creates_no_checkpoint(self):
        def fail(*args):
            raise KeyboardInterrupt("NEUTRAL before commit")

        with self.assertRaises(KeyboardInterrupt):
            self.append(reducer=fail)
        self.assertEqual(self.runtime.catalogue.sequence, 0)
        self.assertFalse(
            (Path(self.choice["ledger_directory"]) / "UNCERTIFIED_MUTATION.json").exists()
        )

    def test_real_revision_conflict_has_no_checkpoint(self):
        with self.assertRaises(DomainError):
            self.append(self.command("stale", 0))
        self.assertEqual(self.runtime.catalogue.sequence, 0)

    def test_real_post_commit_signature_failure_preserves_mutation(self):
        def fail(fields):
            raise RuntimeError("NEUTRAL after actual commit")

        self.store.authority.sign_history_checkpoint = fail
        with self.assertRaises(RuntimeError):
            self.append()
        marker = Path(self.choice["ledger_directory"]) / "UNCERTIFIED_MUTATION.json"
        self.assertTrue(marker.exists())
        self.assertTrue(json.loads(marker.read_text())["genuine_Store_return_before_failure"])
        with contextlib.closing(sqlite3.connect(self.store.db_path)) as db:
            self.assertEqual(db.execute("SELECT revision FROM engagements").fetchone()[0], 2)
        with self.assertRaises(DomainError):
            self.store.get(self.operator["id"], self.eid)
        with self.assertRaises(DomainError):
            self.reopen()

    def test_committed_then_exception_before_return_is_not_rollback(self):
        real = self.store._managed_history_integrity

        def operation():
            self.store._managed_history_integrity = None
            try:
                self.append()
            finally:
                self.store._managed_history_integrity = real
            raise RuntimeError("NEUTRAL committed before return")

        with self.assertRaises(RuntimeError):
            real.mutate(operation, kind="AUDIT_APPEND", command=self.command())
        marker = json.loads(
            (Path(self.choice["ledger_directory"]) / "UNCERTIFIED_MUTATION.json").read_text()
        )
        self.assertFalse(marker["genuine_Store_return_before_failure"])
        self.assertTrue(marker["actual_image_changed_or_closure_unknown"])

    def test_existing_checkpoint_tamper_refused(self):
        self.append()
        path = Path(self.choice["ledger_directory"]) / "CHECKPOINT-00000001.json"
        path.write_bytes(path.read_bytes().replace(b"AUDIT_APPEND", b"WRONG_APPEND"))
        with self.assertRaises(DomainError):
            self.runtime.selected(self.operator["id"], self.eid, revisions=[2])
        with self.assertRaises(DomainError):
            self.reopen()

    def test_unsigned_unknown_ledger_file_refused(self):
        write_new(self.choice["ledger_directory"], "FORGED.json", {"not_a_checkpoint": True})
        with self.assertRaises(DomainError):
            self.runtime.selected(self.operator["id"], self.eid)

    def test_base_bytes_tamper_refused(self):
        path = Path(self.choice["base"]["path"])
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaises(DomainError):
            self.runtime.selected(self.operator["id"], self.eid)
        with self.assertRaises(DomainError):
            self.store.get(self.operator["id"], self.eid)
        with self.assertRaises(DomainError):
            self.runtime.validate_reference(self.runtime.catalogue.reference(1))

    def test_current_state_image_tamper_refused_before_get(self):
        with contextlib.closing(sqlite3.connect(self.store.db_path)) as db, db:
            db.execute("UPDATE engagements SET state=?", (canonical({"forged": True}),))
        with self.assertRaises(DomainError):
            self.store.get(self.operator["id"], self.eid)

    def test_actual_login_logout_zero_audit_frames_and_reopen(self):
        count = len(self.runtime.catalogue.frames)
        login = self.store.login(self.operator["credential"])
        self.store.logout(login["token"])
        self.assertEqual(len(self.runtime.catalogue.frames), count)
        self.assertEqual(self.runtime.catalogue.sequence, 2)
        self.reopen()
        self.assertEqual(self.runtime.catalogue.sequence, 2)

    def test_company_fresh_closure_not_cached(self):
        start = self.world.calls
        self.runtime.selected(self.operator["id"], self.eid)
        self.runtime.selected(self.operator["id"], self.eid)
        self.assertGreaterEqual(self.world.calls - start, 4)
        self.world.refuse = True
        with self.assertRaises(DomainError):
            self.runtime.selected(self.operator["id"], self.eid)

    def test_foreign_scope_reducer_never_certified(self):
        with self.assertRaises(DomainError):
            self.append(reducer=lambda state, command, actor: state | {"scope": {"foreign": True}})
        self.assertTrue(
            (Path(self.choice["ledger_directory"]) / "UNCERTIFIED_MUTATION.json").exists()
        )

    def test_explicit_full_stays_exact_after_two_invocations(self):
        self.append()
        first = self.runtime.full_public_history(self.operator["id"], [1, 2])
        self.assertEqual(first["prefix_sha256"][1], self.actual_base_history_sha)
        self.assertIn("history_sha256", first)
        second = self.store._typed_composed_reader(self.operator["id"], [2])
        self.assertEqual(second["history_sha256"], first["history_sha256"])
        self.assertFalse(self.runtime.force_full)
        self.assertEqual(self.runtime.catalogue.known_prefixes["2"], first["prefix_sha256"][2])

    def test_preexisting_sidecar_refused(self):
        path = Path(str(self.store.db_path) + "-wal")
        path.write_bytes(b"unsettled")
        path.chmod(0o600)
        with self.assertRaises((DomainError, sqlite3.DatabaseError)):
            self.store.get(self.operator["id"], self.eid)

    def test_wrong_selected_checkpoint_refused(self):
        self.append()
        reference = self.runtime.catalogue.reference(2)
        with self.assertRaises(DomainError):
            self.runtime.validate_reference(reference | {"checkpoint_sha256": "0" * 64})

    def test_no_parsed_state_or_source_body_retained_on_runtime(self):
        self.append()
        result = self.runtime.selected(self.operator["id"], self.eid, revisions=[2])
        self.assertIn("note", result["selected"][2]["state"])
        retained = canonical(
            {"frames": self.runtime.catalogue.frames, "custody": self.runtime.catalogue.custody}
        )
        self.assertNotIn("FICTIONAL current note", retained)
        self.assertNotIn("payload", retained)

    def test_final_full_callback_survives_reset_interruption(self):
        self.append()
        local = self.runtime._writer_local

        class FailReset:
            armed = True

            def __getattr__(self, name):
                return getattr(local, name)

            def __setattr__(self, name, value):
                if name == "full_token" and value is None and self.armed:
                    object.__setattr__(self, "armed", False)
                    raise KeyboardInterrupt("NEUTRAL before full flag reset")
                setattr(local, name, value)

        self.runtime._writer_local = FailReset()
        with self.assertRaises(KeyboardInterrupt):
            self.runtime.full_public_history(self.operator["id"], [2])
        self.assertFalse(self.runtime.force_full)
        result = self.store._typed_composed_reader(self.operator["id"], [2])
        self.assertIn("history_sha256", result)
        self.assertIn(2, result["prefix_sha256"])

    def test_artifact_census_whole_filename_byte_mismatch_refused(self):
        from enterprise.audit_suite.managed_history_integrity import artifact_namespace_inventory

        raw = b"FICTIONAL source, not a product answer"
        value = hashlib.sha256(raw).hexdigest()
        path = self.original.root / "artifacts" / value
        path.write_bytes(raw)
        path.chmod(0o600)
        observed = artifact_namespace_inventory(self.original.root)
        self.assertEqual(observed[str(path)]["bytes"], len(raw))
        path.write_bytes(b"changed")
        with self.assertRaises(DomainError):
            artifact_namespace_inventory(self.original.root)

    def test_root_census_default_disabled_and_actual_neutral_inventory(self):
        from enterprise.audit_suite.managed_history_integrity import collect_root_history_metadata

        del self.store._managed_history_integrity
        fd = __import__("os").open(self.root / "room.lock", __import__("os").O_RDWR)
        try:
            with self.assertRaises(DomainError):
                collect_root_history_metadata(self.room, held_writer_fd=fd)
            result = collect_root_history_metadata(
                self.room, held_writer_fd=fd, root_authorized=True
            )
            self.assertFalse(result["new_full_semantic_replay_claimed"])
            self.assertFalse(result["certificate_issued"])
            self.assertEqual(result["frame_vector_sha256"], self.base["frame_vector_sha256"])
        finally:
            __import__("os").close(fd)

    def historical_receipt(self):
        from enterprise.audit_suite.company_store import CompanyStore

        raw = b"FICTIONAL historical original absent from current artifacts"
        value = hashlib.sha256(raw).hexdigest()
        path = self.original.root / "artifacts" / value
        path.write_bytes(raw)
        path.chmod(0o600)
        row = {
            "company": self.selected["company"],
            "branch": self.selected["branch"],
            "system": "NEUTRAL-S",
            "record": "NEUTRAL-R",
            "version": 1,
            "event_at": "2027-12-30T00:00:00+00:00",
            "available_at": "2027-12-30T00:00:00+00:00",
            "imported_at": "2026-01-02T00:00:00+00:00",
            "origin": "NEUTRAL",
            "provenance": canonical({"neutral": True}),
            "sha256": value,
        }
        key = tuple(row[name] for name in ("company", "branch", "system", "record", "version"))
        self.world.native[key] = row
        receipt = {
            "source": CompanyStore._metadata(row),
            "principal_id": self.learner["id"],
            "engagement_id": self.eid,
            "collected_at": "2026-01-03T00:00:00+00:00",
            "simulated_as_of": self.state["simulated_at"],
            "command_id": "NEUTRAL-HISTORICAL",
            "content_bytes": len(raw),
        }
        with contextlib.closing(sqlite3.connect(self.world.database)) as db, db:
            db.execute(
                "INSERT INTO collections VALUES (?,?)", (receipt["command_id"], canonical(receipt))
            )
        return path, key

    def census(self):
        from enterprise.audit_suite.managed_history_integrity import collect_root_history_metadata

        del self.store._managed_history_integrity
        fd = __import__("os").open(self.root / "room.lock", __import__("os").O_RDWR)
        try:
            return collect_root_history_metadata(self.room, held_writer_fd=fd, root_authorized=True)
        finally:
            __import__("os").close(fd)

    def test_census_retains_historical_receipt_absent_current_artifacts(self):
        path, key = self.historical_receipt()
        result = self.census()
        self.assertEqual(result["selected_historical_auditor_receipts"], 1)
        self.assertIn(str(path), result["custody"]["files"])
        self.assertIn("NEUTRAL-HISTORICAL", result["custody"]["custody"])
        self.assertNotIn("FICTIONAL historical original", canonical(result))

    def test_census_missing_historical_original_refuses(self):
        path, key = self.historical_receipt()
        path.unlink()
        with self.assertRaises(DomainError):
            self.census()

    def test_census_changed_native_metadata_refuses(self):
        path, key = self.historical_receipt()
        self.world.native[key]["origin"] = "FOREIGN"
        with self.assertRaises(DomainError):
            self.census()

    def test_census_unknown_filename_refuses(self):
        path = self.original.root / "artifacts" / "UNDECLARED"
        path.write_bytes(b"neutral")
        path.chmod(0o600)
        with self.assertRaises(DomainError):
            self.census()

    def live_reuse_context(self):
        from enterprise.audit_suite.persistent_company_journey import PersistentCompany
        from enterprise.audit_suite.persistent_company_service import RetainedEngine

        # Exact live class identities, real Store/runtime/image closures; only
        # normal Company/config boundaries are explicitly neutral test doubles.
        room = RetainedWorkroom.__new__(RetainedWorkroom)
        room.__dict__.update(vars(self.room))
        world = PersistentCompany.__new__(PersistentCompany)
        world.__dict__.update(vars(self.world))
        world.store = object()
        world.locked = types.MethodType(NeutralWorld.locked, world)
        world.verify = types.MethodType(NeutralWorld.verify, world)
        room.world = world
        room.repository = self.root
        room.sealed = True
        binding_pin = write_new(self.root, "NEUTRAL_REUSE_BINDING.json", room.binding)
        room.binding_path = Path(binding_pin["path"])
        room.binding_sha256 = binding_pin["sha256"]
        room.config = {
            "code_pins": room.config["code_pins"],
            "workroom_binding": binding_pin,
            "history_integrity": self.choice,
        }
        configuration = write_new(self.root, "NEUTRAL_REUSE_CONFIG.json", room.config)
        room.path = Path(configuration["path"])
        room.expected_sha256 = configuration["sha256"]
        engine = RetainedEngine.__new__(RetainedEngine)
        engine.store = self.store
        engine.repository = self.root
        engine.company_store = world.store
        engine.company_bindings = {self.eid: self.selected}
        room.engine = engine
        room.refresh_integrity = types.MethodType(
            lambda instance, actor: self.runtime.selected(actor, self.eid), room
        )
        # Actual original close_protected_read/integrity_stamp methods retain
        # journal-bound publication, with neutral Source refresh as above.
        room._refresh_integrity = room.refresh_integrity
        self.runtime.room = room
        self.room = room
        self.runtime.complete_startup()
        return room, configuration

    def test_completed_managed_reuse_without_fake_legacy_memos(self):
        from enterprise.audit_suite.retained_explanation_service import _reuse_retained_workroom

        room, configuration = self.live_reuse_context()
        self.assertIsNone(self.store._prefix_integrity)
        self.assertFalse(hasattr(room, "_prefix_custody"))
        self.assertFalse(hasattr(room, "_tail_integrity"))
        actual = _reuse_retained_workroom(
            configuration["path"],
            configuration["sha256"],
            private_root=room.root,
            repository=room.repository,
            retained_workroom=room,
        )
        self.assertIs(actual, room)
        self.assertIsNone(self.store._prefix_integrity)
        self.assertFalse(hasattr(room, "_prefix_custody"))
        self.assertFalse(hasattr(room, "_tail_integrity"))

    def test_unselected_reuse_still_refuses_missing_legacy_memos(self):
        from enterprise.audit_suite.retained_explanation_service import _reuse_retained_workroom

        room, configuration = self.live_reuse_context()
        del self.store._managed_history_integrity
        with self.assertRaises((DomainError, ValueError)):
            _reuse_retained_workroom(
                configuration["path"],
                configuration["sha256"],
                private_root=room.root,
                repository=room.repository,
                retained_workroom=room,
            )

    def test_incomplete_managed_reuse_refused(self):
        from enterprise.audit_suite.retained_explanation_service import _reuse_retained_workroom

        room, configuration = self.live_reuse_context()
        self.runtime._startup_completed = False
        with self.assertRaises((DomainError, ValueError)):
            _reuse_retained_workroom(
                configuration["path"],
                configuration["sha256"],
                private_root=room.root,
                repository=room.repository,
                retained_workroom=room,
            )


class OneShotTLS:
    def __init__(self, phase):
        self.depth = 0
        self.phase = phase
        self.issuer_token = None
        self.armed = True

    def __setattr__(self, name, value):
        if name == "issuer_token" and getattr(self, "armed", False):
            if self.phase == "entry" and type(value) is dict:
                object.__setattr__(self, name, value)
                object.__setattr__(self, "armed", False)
                raise KeyboardInterrupt("NEUTRAL after actual lease publication")
            if self.phase == "close" and value is None and getattr(self, name, None) is not None:
                object.__setattr__(self, "armed", False)
                raise KeyboardInterrupt("NEUTRAL before lease reset")
        if (
            name == "current_context"
            and self.phase == "outer_close"
            and value is None
            and getattr(self, "armed", False)
        ):
            object.__setattr__(self, "armed", False)
            raise KeyboardInterrupt("NEUTRAL outer context teardown")
        object.__setattr__(self, name, value)


def runtime(phase):
    value = ManagedHistoryRuntime.__new__(ManagedHistoryRuntime)
    value._writer_local = OneShotTLS(phase)
    value.room = types.SimpleNamespace(
        _integrity_lock=threading.RLock(),
        binding={"identities": {"operator": "NEUTRAL"}},
        engagement="NEUTRAL-E",
    )

    @contextmanager
    def lock():
        yield

    value._outer_writer_lock = lock
    value.selected = lambda *args, **kwargs: None
    value.validate_current = lambda *args, **kwargs: {
        "latest": {"state": {"simulated_at": "2027-01-01T00:00:00Z"}}
    }
    value._images = lambda: {"neutral": "UNCHANGED"}
    return value


class CancellationTests(unittest.TestCase):
    def test_entry_publication_does_not_leave_bypass(self):
        value = runtime("entry")
        with self.assertRaises(KeyboardInterrupt):
            value.mutate(lambda: "duplicate", kind="AUDIT_APPEND")
        self.assertFalse(value._issuing)
        with value.locked():
            self.assertFalse(value._issuing)

    def test_cleanup_does_not_leave_same_thread_bypass(self):
        value = runtime("close")
        with self.assertRaises(KeyboardInterrupt):
            value.mutate(lambda: "duplicate", kind="AUDIT_APPEND")
        self.assertFalse(value._issuing)
        with value.locked():
            self.assertFalse(value._issuing)

    def test_nested_cleanup_while_outer_lock_held(self):
        value = runtime("close")
        with value.locked():
            with self.assertRaises(KeyboardInterrupt):
                value.mutate(lambda: "duplicate", kind="AUDIT_APPEND")
            self.assertFalse(value._issuing)
            with value.locked():
                self.assertFalse(value._issuing)

    def test_external_rlock_held_does_not_resurrect_closed_lease(self):
        value = runtime("close")
        with value.room._integrity_lock:
            with self.assertRaises(KeyboardInterrupt):
                value.mutate(lambda: "duplicate", kind="AUDIT_APPEND")
            self.assertFalse(value._issuing)
            with value.locked():
                self.assertFalse(value._issuing)

    def test_outer_teardown_interruption_leaves_closed_generator(self):
        value = runtime("outer_close")
        with self.assertRaises(KeyboardInterrupt):
            with value.locked():
                value._issuing = True
        self.assertFalse(value._issuing)
        with value.locked():
            self.assertFalse(value._issuing)

    def test_unprotected_flag_publication_refused(self):
        value = runtime("none")
        with self.assertRaises(ValueError):
            value._issuing = True

    def test_nested_live_invocation_only(self):
        value = runtime("none")
        with value.locked():
            value._issuing = True
            with value.locked():
                self.assertTrue(value._issuing)
        self.assertFalse(value._issuing)

    def test_full_flag_closes_with_actual_invocation(self):
        value = runtime("none")
        with value.locked():
            value.force_full = True
        self.assertFalse(value.force_full)


class SuccessorCensusGuards(unittest.TestCase):
    def test_baseline_and_extra_guards_both_run_at_both_boundaries(self):
        module = types.SimpleNamespace(RuntimeTests=RuntimeTests)
        value = module.RuntimeTests(
            "test_root_census_default_disabled_and_actual_neutral_inventory"
        )
        value.setUp()
        try:
            events = []
            value.room.check_pins = lambda: events.append("baseline")
            value.room.check_history_metadata_sources = lambda: events.append("extra")
            value.census()
            self.assertEqual(events, ["baseline", "extra", "baseline", "extra"])
        finally:
            value.tearDown()

    def refusal(self, boundary):
        module = types.SimpleNamespace(RuntimeTests=RuntimeTests)
        value = module.RuntimeTests(
            "test_root_census_default_disabled_and_actual_neutral_inventory"
        )
        value.setUp()
        try:
            calls, extra = [], []

            def baseline():
                calls.append("baseline")
                if len(calls) == boundary:
                    raise DomainError("NEUTRAL actual baseline changed")

            value.room.check_pins = baseline
            value.room.check_history_metadata_sources = lambda: extra.append("extra")
            with self.assertRaises(DomainError):
                value.census()
            self.assertEqual(len(calls), boundary)
            self.assertEqual(len(extra), boundary - 1)
        finally:
            value.tearDown()

    def test_baseline_refusal_at_entry(self):
        self.refusal(1)

    def test_baseline_refusal_at_closing(self):
        self.refusal(2)


if __name__ == "__main__":
    unittest.main()
