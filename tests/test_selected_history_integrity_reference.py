"""Neutral exact-schema tests; no product constructor, SQL, secrets or requests."""

import copy
import types
import unittest

from enterprise.audit_suite import history_integrity_reference as ref
from enterprise.audit_suite import store

SHA = "1" * 64
BASE = {
    "schema": ref.REFERENCE_SCHEMA,
    "kind": "ROOT_ACCEPTED_BASE",
    "algorithm": ref.REFERENCE_ALGORITHM,
    "engagement_id": "NEUTRAL-E",
    "revision": 0,
    "selected_event_sha256": "2" * 64,
    "selected_request_sha256": "3" * 64,
    "state_storage": "CANONICAL_CODEC_GRAPH",
    "selected_state_root_sha256": "4" * 64,
    "selected_state_sha256": "5" * 64,
    "selected_state_bytes": 17,
    "accepted_base_sha256": SHA,
    "checkpoint_sha256": SHA,
}


class ReferenceTests(unittest.TestCase):
    def test_exact_base(self):
        self.assertIs(ref.validate_reference(BASE), BASE)

    def test_exact_managed(self):
        value = BASE | {
            "kind": "MANAGED_STORE_CHECKPOINT",
            "revision": 1,
            "checkpoint_sha256": "6" * 64,
        }
        self.assertIs(ref.validate_reference(value), value)

    def test_exact_raw(self):
        value = BASE | {"state_storage": "RAW_CANONICAL_JSON", "selected_state_root_sha256": None}
        self.assertIs(ref.validate_reference(value), value)

    def test_safe_integer_limits(self):
        ref.validate_reference(
            BASE | {"revision": ref.MAX_SAFE_INTEGER, "selected_state_bytes": ref.MAX_SAFE_INTEGER}
        )

    def test_full_reference_equality(self):
        self.assertTrue(ref.same_reference(BASE, copy.deepcopy(BASE)))
        self.assertFalse(ref.same_reference(BASE, BASE | {"selected_request_sha256": "9" * 64}))

    def test_all_expected_joins(self):
        ref.validate_reference(
            BASE,
            engagement="NEUTRAL-E",
            revision=0,
            state_sha256=BASE["selected_state_sha256"],
            event_sha256=BASE["selected_event_sha256"],
            accepted_base_sha256=SHA,
            checkpoint_sha256=SHA,
        )

    def test_unknown_runtime_refused(self):
        with self.assertRaises(store.DomainError):
            ref.validate_store_reference(object(), BASE)

    def test_runtime_refusal_propagates(self):
        class Runtime:
            def validate_reference(self, value):
                raise store.DomainError("foreign checkpoint")

        with self.assertRaises(store.DomainError):
            ref.validate_store_reference(
                types.SimpleNamespace(_managed_history_integrity=Runtime()), BASE
            )

    def test_managed_uses_introducing_checkpoint(self):
        frame = {
            "engagement_id": "NEUTRAL-E",
            "revision": 1,
            "event_sha256": "2" * 64,
            "request_sha256": "3" * 64,
            "state_storage": "CANONICAL_CODEC_GRAPH",
            "state_root_sha256": "4" * 64,
            "state_sha256": "5" * 64,
            "state_bytes": 17,
        }
        value = ref.reference_for_frame(
            frame, accepted_base_sha256=SHA, checkpoint_sha256="6" * 64, base_revision=0
        )
        self.assertEqual(value["checkpoint_sha256"], "6" * 64)
        self.assertEqual(value["kind"], "MANAGED_STORE_CHECKPOINT")


def reject_case(name, changes=None, remove=None, expected=None):
    def case(self):
        value = copy.deepcopy(BASE)
        value.update(changes or {})
        if remove:
            value.pop(remove)
        with self.assertRaises(store.DomainError):
            ref.validate_reference(value, **(expected or {}))

    setattr(ReferenceTests, "test_refuses_" + name, case)


for key in ref.REFERENCE_FIELDS:
    reject_case("missing_" + key, remove=key)
for name, changes in {
    "extra": {"untrusted": True},
    "schema": {"schema": "OTHER"},
    "kind": {"kind": "OTHER"},
    "algorithm": {"algorithm": "SHA256_JSON_ARRAY"},
    "empty_identity": {"engagement_id": ""},
    "foreign_base_checkpoint": {"checkpoint_sha256": "6" * 64},
    "bool_revision": {"revision": True},
    "float_revision": {"revision": 0.0},
    "negative_revision": {"revision": -1},
    "unsafe_revision": {"revision": 2**53},
    "bool_bytes": {"selected_state_bytes": True},
    "zero_bytes": {"selected_state_bytes": 0},
    "unsafe_bytes": {"selected_state_bytes": 2**53},
    "graph_null_root": {"selected_state_root_sha256": None},
    "raw_nonnull_root": {"state_storage": "RAW_CANONICAL_JSON"},
    "unknown_storage": {"state_storage": "OTHER"},
    "uppercase_sha": {"selected_event_sha256": "A" * 64},
    "null_sha": {"selected_state_sha256": None},
}.items():
    reject_case(name, changes)
for key, value in {
    "engagement": "FOREIGN",
    "revision": 1,
    "state_sha256": "8" * 64,
    "event_sha256": "8" * 64,
    "accepted_base_sha256": "8" * 64,
    "checkpoint_sha256": "8" * 64,
}.items():
    reject_case("join_" + key, expected={key: value})


FRAME = {
    "engagement_id": "NEUTRAL-E",
    "revision": 0,
    "command_id": "CMD-0",
    "request_sha256": "3" * 64,
    "event_sha256": "2" * 64,
    "previous_event_sha256": "",
    "actor": "NEUTRAL-A",
    "recorded_at": 1.0,
    "command_kind": "create",
    "state_storage": "CANONICAL_CODEC_GRAPH",
    "state_root_sha256": "4" * 64,
    "state_sha256": "5" * 64,
    "state_bytes": 17,
}


class SuccessorTests(unittest.TestCase):
    def test_real_numeric_frame(self):
        ref.validate_frame(FRAME, engagement="NEUTRAL-E", revision=0, previous_event_sha256="")

    def test_frame_raw(self):
        ref.validate_frame(
            FRAME | {"state_storage": "RAW_CANONICAL_JSON", "state_root_sha256": None},
            engagement="NEUTRAL-E",
            revision=0,
            previous_event_sha256="",
        )


def ref_case(name, field, value):
    def case(self):
        with self.assertRaises(store.DomainError):
            ref.validate_reference(BASE | {field: value})

    setattr(SuccessorTests, "test_container_" + name, case)


for field in ("schema", "kind", "algorithm", "state_storage"):
    for label, value in (("list", []), ("dict", {}), ("null", None), ("bool", True)):
        ref_case(field + "_" + label, field, value)


def frame_case(name, changes=None, omit=None, joins=None):
    def case(self):
        value = FRAME | (changes or {})
        if omit:
            value.pop(omit)
        expected = {"engagement": "NEUTRAL-E", "revision": 0, "previous_event_sha256": ""} | (
            joins or {}
        )
        with self.assertRaises(store.DomainError):
            ref.validate_frame(value, **expected)

    setattr(SuccessorTests, "test_frame_refuses_" + name, case)


for key in ref.FRAME_FIELDS:
    frame_case("missing_" + key, omit=key)
for name, changes in {
    "extra": {"extra": 0},
    "foreign_engagement": {"engagement_id": "FOREIGN"},
    "revision_bool": {"revision": True},
    "revision_float": {"revision": 0.0},
    "revision_negative": {"revision": -1},
    "revision_wrong": {"revision": 1},
    "huge_time": {"recorded_at": 10**1000},
    "nan_time": {"recorded_at": float("nan")},
    "inf_time": {"recorded_at": float("inf")},
    "bool_time": {"recorded_at": True},
    "str_time": {"recorded_at": "1"},
    "negative_time": {"recorded_at": -1},
    "null_root": {"state_root_sha256": None},
    "foreign_chain": {"previous_event_sha256": "7" * 64},
    "bad_request": {"request_sha256": None},
    "bad_state": {"state_sha256": []},
    "bad_kind": {"command_kind": []},
    "bad_actor": {"actor": {}},
    "zero_bytes": {"state_bytes": 0},
}.items():
    frame_case(name, changes)


if __name__ == "__main__":
    unittest.main()
