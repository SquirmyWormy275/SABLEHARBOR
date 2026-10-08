"""Exact candidate function slices and neutral private metadata fixtures.

No product Store/Company constructors, data files, credentials or requests.
The separate runtime integration tests exercise actual transactional storage.
"""

import ast
import copy
import json
import re
import types
import unittest
from datetime import UTC, datetime
from pathlib import Path

from enterprise.audit_suite import history_integrity_reference as ref
from enterprise.audit_suite import instructor_key_views as key_source
from enterprise.audit_suite import store

ROOT = Path(ref.__file__).resolve().parent

NATIVE = Path(key_source.__file__).resolve().parent
BASE_REFERENCE = {
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
    "accepted_base_sha256": "1" * 64,
    "checkpoint_sha256": "1" * 64,
}
fixture = types.SimpleNamespace(BASE=BASE_REFERENCE)


def extracted(path, *, functions=(), classes=(), assignments=True, injected=None):
    tree = ast.parse(path.read_text())
    nodes = [
        node
        for node in tree.body
        if (
            isinstance(node, ast.FunctionDef)
            and node.name in functions
            or isinstance(node, ast.ClassDef)
            and node.name in classes
            or assignments
            and isinstance(node, ast.Assign)
        )
    ]
    namespace = {
        "__name__": "neutral_private_dispatch",
        "__package__": "enterprise.audit_suite",
        "DomainError": store.DomainError,
        "canonical": store.canonical,
        "digest": store.digest,
        "json": json,
        "re": re,
        "datetime": datetime,
        "UTC": UTC,
        "validate_reference": ref.validate_reference,
        "validate_store_reference": ref.validate_store_reference,
    } | (injected or {})
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return types.SimpleNamespace(**namespace)


key_helpers = extracted(
    NATIVE / "instructor_key_views.py", functions=("fields", "integer", "pin", "require", "text")
)
assessment = extracted(
    ROOT / "instructor_assessments.py",
    functions=(
        "history_pin_fields",
        "ids",
        "authored",
        "references",
        "validate_document",
        "validate_archive",
    ),
    classes=("InstructorAssessments",),
    injected={k: getattr(key_helpers, k) for k in ("fields", "integer", "pin", "require", "text")}
    | {"contextmanager": __import__("contextlib").contextmanager},
)
debrief = extracted(
    ROOT / "instructor_debrief.py",
    functions=("require", "fields", "text", "ids", "pin", "annotation", "validate_document"),
)
SHA = "1" * 64
REFERENCE = fixture.BASE | {"selected_state_sha256": "5" * 64, "selected_event_sha256": "2" * 64}
USER = {
    "title": "Neutral authored statement",
    "issue_ids": ["I"],
    "expectation_ids": ["X"],
    "dimensions": [
        {
            "dimension": name,
            "assessment": "Neutral assessment",
            "rationale": "Neutral rationale",
            "reference_ids": [],
        }
        for name in assessment.DIMENSIONS
    ],
    "alternatives": [],
    "overrides": [],
    "defects": [],
}
ISSUE = {"id": "I", "control_ids": ["C"], "claim": "Neutral claim", "uncertainty": "Unvalidated"}
EXPECTATION = {
    "id": "X",
    "issue_ids": ["I"],
    "procedure": "Neutral procedure",
    "acceptable_alternatives": [],
}


def assessment_doc(version=2):
    pins = {
        "key_pin": SHA,
        "rubric_sha256": SHA,
        "inventory_sha256": SHA,
        "audited_actor_id": "A",
        "learner_revision": 0,
        "selected_state_sha256": "5" * 64,
        "selected_history_tip_sha256": "2" * 64,
        "bound_revision": 0,
    }
    pins.update(
        {"selected_history_integrity_reference": copy.deepcopy(REFERENCE)}
        if version == 2
        else {"selected_history_sha256": "a" * 64}
    )
    return {
        "schema": "INSTRUCTOR_AUTHORED_ASSESSMENT_V" + str(version),
        "id": "ASSESSMENT-N",
        "version": 1,
        "actor_id": "INSTRUCTOR",
        "engagement_id": "NEUTRAL-E",
        "recorded_at": "2026-10-07T00:00:00+00:00",
        "predecessor": None,
        "pins": pins,
        "authored": copy.deepcopy(USER),
        "selected_issues": [copy.deepcopy(ISSUE)],
        "selected_expectations": [copy.deepcopy(EXPECTATION)],
        "references": [],
        "qualification": assessment.QUALIFICATION,
    }


def debrief_doc(version=2):
    learner = {
        "actor_id": "A",
        "revision": 0,
        "state_sha256": "5" * 64,
        "event_sha256": "2" * 64,
        "simulated_at": "2028-01-18T09:00:00+00:00",
        "qualification": "SHARED_STATE_NOT_SUBMISSION_KEY_SUPPORT_MAY_POSTDATE_LEARNER_REVISION",
    }
    learner.update(
        {"history_integrity_reference": copy.deepcopy(REFERENCE)}
        if version == 2
        else {"history_sha256": "a" * 64}
    )
    return {
        "schema": "SELECTED_INSTRUCTOR_DEBRIEF_V" + str(version),
        "title": "Neutral debrief",
        "version": 1,
        "predecessor": None,
        "key_manifest_sha256": SHA,
        "learner": learner,
        "source_references": [],
        "sections": [
            {
                "issues": [copy.deepcopy(ISSUE)],
                "expectations": [copy.deepcopy(EXPECTATION)],
                "explanation": "Neutral explanation",
                "limitations": "Unvalidated",
                "prompts": ["Consider this"],
                "annotations": [],
            }
        ],
        "qualification": "INSTRUCTOR_AUTHORED_UNVALIDATED_LOCATORS_NOT_VERIFIED_NO_GRADING",
    }


class PrivateDocumentTests(unittest.TestCase):
    def test_assessment_v1_preserved(self):
        assessment.validate_document(assessment_doc(1))

    def test_assessment_v2_exact(self):
        assessment.validate_document(assessment_doc(2))

    def test_debrief_v1_preserved(self):
        debrief.validate_document(debrief_doc(1))

    def test_debrief_v2_exact(self):
        debrief.validate_document(debrief_doc(2))

    def test_assessment_pin_shape_v1(self):
        self.assertEqual(
            assessment.history_pin_fields(assessment_doc(1)["pins"]), assessment.PIN_FIELDS
        )

    def test_assessment_pin_shape_v2(self):
        self.assertEqual(
            assessment.history_pin_fields(assessment_doc(2)["pins"]), assessment.PIN_FIELDS_V2
        )

    def test_assessment_v2_root_rule(self):
        value = assessment_doc()
        value["pins"]["selected_history_integrity_reference"]["checkpoint_sha256"] = "8" * 64
        with self.assertRaises(store.DomainError):
            assessment.validate_document(value)

    def test_debrief_v2_root_rule(self):
        value = debrief_doc()
        value["learner"]["history_integrity_reference"]["checkpoint_sha256"] = "8" * 64
        with self.assertRaises(store.DomainError):
            debrief.validate_document(value)

    def test_catalogue_binds_whole_reference(self):
        data = {
            "engagement_id": "NEUTRAL-E",
            "current_engagement_revision": 0,
            "rubric_sha256": SHA,
            "references": [],
            **assessment_doc()["pins"],
        }
        left = assessment.InstructorAssessments._catalogue(
            "INSTRUCTOR", data, {"basis": SHA, "state": {"id": "NEUTRAL-E"}}
        )
        value = copy.deepcopy(data)
        value["selected_history_integrity_reference"]["selected_request_sha256"] = "9" * 64
        right = assessment.InstructorAssessments._catalogue(
            "INSTRUCTOR", value, {"basis": SHA, "state": {"id": "NEUTRAL-E"}}
        )
        self.assertNotEqual(left["context_sha256"], right["context_sha256"])

    def test_dto_authenticates_v2_checkpoint(self):
        class Runtime:
            def validate_reference(self, value):
                raise store.DomainError("foreign checkpoint")

        obj = object.__new__(assessment.InstructorAssessments)
        obj.engine = types.SimpleNamespace(
            store=types.SimpleNamespace(_managed_history_integrity=Runtime())
        )
        with self.assertRaises(store.DomainError):
            obj._dto({"document": assessment_doc()}, {})


def document_refusal(name, family, update):
    def case(self):
        value = assessment_doc() if family == "assessment" else debrief_doc()
        update(value)
        with self.assertRaises(store.DomainError):
            (assessment if family == "assessment" else debrief).validate_document(value)

    setattr(PrivateDocumentTests, "test_" + family + "_refuses_" + name, case)


for field, wrong in {
    "engagement_id": "FOREIGN",
    "revision": 1,
    "selected_state_sha256": "8" * 64,
    "selected_event_sha256": "8" * 64,
}.items():
    document_refusal(
        field,
        "assessment",
        lambda value, field=field, wrong=wrong: value["pins"][
            "selected_history_integrity_reference"
        ].__setitem__(field, wrong),
    )
for field, wrong in {
    "revision": 1,
    "selected_state_sha256": "8" * 64,
    "selected_event_sha256": "8" * 64,
}.items():
    document_refusal(
        field,
        "debrief",
        lambda value, field=field, wrong=wrong: value["learner"][
            "history_integrity_reference"
        ].__setitem__(field, wrong),
    )
for family, holder, reference_name, legacy_name in (
    ("assessment", "pins", "selected_history_integrity_reference", "selected_history_sha256"),
    ("debrief", "learner", "history_integrity_reference", "history_sha256"),
):
    document_refusal(
        "missing_v2",
        family,
        lambda value, holder=holder, reference_name=reference_name: value[holder].pop(
            reference_name
        ),
    )
    document_refusal(
        "extra_legacy_sha",
        family,
        lambda value, holder=holder, legacy_name=legacy_name: value[holder].__setitem__(
            legacy_name, SHA
        ),
    )
    document_refusal(
        "v1_discriminator_v2_pins",
        family,
        lambda value: value.__setitem__("schema", value["schema"].replace("_V2", "_V1")),
    )


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.current = {
            "id": "NEUTRAL-E",
            "revision": 0,
            "scope": {"neutral": True},
            "controls": [],
            "company_source_binding": {"company": "NEUTRAL-C", "branch": "NEUTRAL-B"},
        }
        self.entry = {"state": self.current, "revision": 0, "hash": "2" * 64}
        self.reference = REFERENCE | {"selected_state_sha256": store.digest(self.current)}
        self.history = {
            "count": 1,
            "latest": self.entry,
            "selected": {0: self.entry},
            "prefix_sha256": {0: "a" * 64},
            "selected_integrity_reference": {0: self.reference},
            "activity": [],
        }

        class Runtime:
            def selected(inner, actor, engagement, revisions=()):
                return copy.deepcopy(self.history)

            def validate_reference(inner, value):
                ref.validate_reference(value, engagement="NEUTRAL-E")
                if value != self.reference:
                    raise store.DomainError("NEUTRAL foreign checkpoint")

            def legacy_prefix_sha256(inner, actor, engagement, revision):
                return "a" * 64

        self.runtime = Runtime()
        self.engine = types.SimpleNamespace(
            store=types.SimpleNamespace(
                membership=lambda *args: "instruct",
                get=lambda *args: self.current,
                _managed_history_integrity=self.runtime,
                root=Path("/neutral"),
            ),
            company_bindings={"NEUTRAL-E": self.current["company_source_binding"]},
        )
        snapshot = {
            "engagement": {
                "revision": 0,
                "state_sha256": store.digest(self.current),
                "history_sha256": "a" * 64,
                "scope": self.current["scope"],
            },
            "company_binding": self.current["company_source_binding"],
            "audited_actor_id": "A",
            "authored": {"issues": [ISSUE], "expectations": [EXPECTATION]},
        }
        self.bound = {"snapshot": snapshot, "binding": {"manifest_sha256": SHA}}

        class Log:
            def __init__(inner, *args):
                pass

            def append(inner, **kwargs):
                pass

        self.comparison = extracted(
            ROOT / "instructor_comparison.py",
            functions=("_compare", "compare"),
            injected={
                "read_binding": lambda *args: self.bound,
                "validate_routes": lambda *args: None,
                "InstructorAccessLog": Log,
                "_inventory": lambda *args: {
                    "sources": [],
                    "expectations": [],
                    "inspection": {"status": "NO_INSPECTION"},
                    "audited_actor_activity": [],
                },
            },
        )
        # The exact assessment methods use the exact comparison dispatch above.
        namespace = assessment.InstructorAssessments._options.__globals__
        namespace["read_binding"] = lambda *args: self.bound
        namespace["compare"] = self.comparison.compare
        namespace["_basis"] = extracted(
            NATIVE / "workspace_context.py", functions=("_basis",), assignments=False
        )._basis
        self.obj = object.__new__(assessment.InstructorAssessments)
        self.obj.engine = self.engine
        self.obj.bindings = {}
        self.obj._state = lambda *args: self.current
        self.obj._finish = lambda *args: None

    def test_comparison_v2_has_reference_without_legacy_sha(self):
        value = self.comparison.compare(
            self.engine, {"id": "INSTRUCTOR"}, "NEUTRAL-E", {}, revision=0
        )
        self.assertEqual(value["schema_version"], "2.0")
        self.assertEqual(value["selected_history_integrity_reference"], self.reference)
        self.assertNotIn("selected_history_sha256", value)

    def test_comparison_v1_unselected_keeps_exact_old_sha(self):
        del self.engine.store._managed_history_integrity
        import sys

        legacy = types.ModuleType("enterprise.audit_suite.history_inspection")
        legacy.inspect_history = lambda *args, **kwargs: {
            k: v
            for k, v in copy.deepcopy(self.history).items()
            if k != "selected_integrity_reference"
        }
        previous = sys.modules.get(legacy.__name__)
        try:
            sys.modules[legacy.__name__] = legacy
            value = self.comparison.compare(
                self.engine, {"id": "INSTRUCTOR"}, "NEUTRAL-E", {}, revision=0
            )
        finally:
            if previous is None:
                sys.modules.pop(legacy.__name__, None)
            else:
                sys.modules[legacy.__name__] = previous
        self.assertEqual(value["schema_version"], "1.0")
        self.assertEqual(value["selected_history_sha256"], "a" * 64)
        self.assertNotIn("selected_history_integrity_reference", value)

    def test_options_v2_joins_complete_reference(self):
        value = self.obj.options("INSTRUCTOR", "NEUTRAL-E", 0)
        self.assertEqual(
            value["history_integrity_format"], "SELECTED_HISTORY_INTEGRITY_REFERENCE_V2"
        )
        self.assertEqual(value["selected_history_integrity_reference"], self.reference)
        self.assertNotIn("selected_history_sha256", value)

    def test_stored_v1_compatibility_uses_actual_legacy_shape(self):
        value, context = self.obj._options("INSTRUCTOR", "NEUTRAL-E", 0, legacy_record=True)
        self.assertEqual(value["selected_history_sha256"], "a" * 64)
        self.assertNotIn("selected_history_integrity_reference", value)
        self.assertNotIn("history_integrity_format", value)

    def test_comparison_changed_state_join_refused(self):
        self.history["selected_integrity_reference"][0] = self.reference | {
            "selected_state_sha256": "8" * 64
        }
        with self.assertRaises(store.DomainError):
            self.obj.options("INSTRUCTOR", "NEUTRAL-E", 0)

    def test_comparison_changed_event_join_refused(self):
        self.history["selected_integrity_reference"][0] = self.reference | {
            "selected_event_sha256": "8" * 64
        }
        with self.assertRaises(store.DomainError):
            self.obj.options("INSTRUCTOR", "NEUTRAL-E", 0)

    def test_comparison_wrong_engagement_refused(self):
        self.history["selected_integrity_reference"][0] = self.reference | {
            "engagement_id": "FOREIGN"
        }
        with self.assertRaises(store.DomainError):
            self.obj.options("INSTRUCTOR", "NEUTRAL-E", 0)

    def test_comparison_requires_real_instructor_membership(self):
        self.engine.store.membership = lambda *args: "learn"
        with self.assertRaises(store.DomainError):
            self.obj.options("INSTRUCTOR", "NEUTRAL-E", 0)

    def test_comparison_bound_legacy_digest_still_exact(self):
        self.history["prefix_sha256"][0] = "9" * 64
        with self.assertRaises(store.DomainError):
            self.obj.options("INSTRUCTOR", "NEUTRAL-E", 0)


if __name__ == "__main__":
    unittest.main()
