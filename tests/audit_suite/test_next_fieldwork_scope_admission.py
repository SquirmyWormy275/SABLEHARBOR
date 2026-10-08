"""No-world checks of exact pair-review and retained binding scope admission."""

import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from enterprise.audit_suite import full_scope_company_pair as subject
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.source_library_audit import BusinessRoute, file_sha


def test_default_and_explicit_fieldwork_scope_review_and_bound_state(tmp_path):
    # These are owned metadata, not a company/world, birth or actual Root grant.
    tmp_path.chmod(0o700)
    routes = {
        mode: [BusinessRoute("OWN", branch, "own.metadata", "own", "metadata")]
        for mode, branch in (("CLEAN", "A"), ("MESSY", "B"))
    }
    pins = {"owned_metadata_only": True}
    path = tmp_path / "OWN_PAIR_REVIEW.json"

    def review(scope):
        value = {
            "schema": subject.PAIR_SCHEMA,
            "verdict": subject.PAIR_VERDICT,
            "source_execution_authorized": True,
            "engineering_only_shape_not_actual_authority": True,
            "orchestration_module_sha256": file_sha(Path(subject.__file__)),
            "dependency_module_sha256": subject.dependencies(),
            "accepted_baseline_pins": pins,
            "program_pack_sha256": subject.PROGRAM_SHA,
            "route_vector": subject.route_vector(routes),
            "scope": scope,
        }
        path.write_text(json.dumps(value))
        path.chmod(0o600)
        return subject.PinnedReview(path, file_sha(path))

    legacy = subject.FullScopePair()
    assert legacy.expected_scope == subject.SCOPE
    subject.require_pair_gate(review(subject.SCOPE), pins, routes)
    selected = subject.FullScopePair(expected_fieldwork_start="2028-01-18")
    assert selected.expected_scope == {**subject.SCOPE, "fieldwork_start": "2028-01-18"}
    owned_review = review(selected.expected_scope)
    subject.require_pair_gate(owned_review, pins, routes, expected_scope=selected.expected_scope)
    with pytest.raises(ProcedureError):
        subject.require_pair_gate(owned_review, pins, routes)
    with pytest.raises(ProcedureError):
        subject.require_pair_gate(
            review(subject.SCOPE), pins, routes, expected_scope=selected.expected_scope
        )
    changed = {**selected.expected_scope, "period_end": "2028-01-17"}
    with pytest.raises(ProcedureError):
        subject.require_pair_gate(review(changed), pins, routes, expected_scope=changed)
    owned_review = review(selected.expected_scope)
    original_sha = owned_review.sha256
    path.write_text(path.read_text() + " ")
    with pytest.raises(ProcedureError):
        subject.require_pair_gate(
            subject.PinnedReview(path, original_sha),
            pins,
            routes,
            expected_scope=selected.expected_scope,
        )
    for bad in (True, "20280118", "2028-02-30", "2026-12-31", "2040-01-18"):
        with pytest.raises(ProcedureError):
            subject.FullScopePair(expected_fieldwork_start=bad)

    def bound_room(pair):
        gate = review(pair.expected_scope)
        pair.check = lambda: subject.require_pair_gate(
            gate, pins, routes, expected_scope=pair.expected_scope
        )
        store = object()
        pair.world = SimpleNamespace(store=store)
        scope = {
            **pair.expected_scope,
            "programs": sorted(pair.expected_scope["programs"]),
            "temporal_basis": "PERIOD",
            "control_ids": [],
            "organization_revision": "OWN",
            "program_versions": {},
            "professional_acceptance": "NOT_ASSERTED",
        }
        initial = pair.expected_scope["fieldwork_start"] + "T09:00:00Z"
        state = {
            "scope": scope,
            "mode": "CLEAN",
            "simulated_at": initial,
            "tasks": [{} for _ in range(409)],
        }
        binding = {
            "company": "OWN",
            "branch": "A",
            "scope": deepcopy(scope),
            "initial_simulated_at": initial,
            "audit_root": str(tmp_path / "absent-audit"),
        }
        engine = SimpleNamespace(
            company_store=store, company_bindings={"OWN-ENG": {"company": "OWN", "branch": "A"}}
        )
        session = SimpleNamespace(
            engine=engine,
            engagement="OWN-ENG",
            identities={"operator": "OWN-OP", "auditor": "OWN-AU", "reviewer": "OWN-RV"},
            _context=lambda *_: (state, {}),
        )
        return subject.BoundWorkroom(pair, "CLEAN", session, binding), state

    room, state = bound_room(selected)
    assert room.state() is state
    room.binding["scope"]["fieldwork_start"] = "2027-12-31"
    with pytest.raises(ProcedureError):
        room.state()
    room.binding["scope"] = deepcopy(state["scope"])
    state["scope"]["period_end"] = "2028-01-17"
    room.binding["scope"] = deepcopy(state["scope"])
    with pytest.raises(ProcedureError):
        room.state()
    state["scope"]["period_end"] = subject.SCOPE["period_end"]
    room.binding["scope"] = deepcopy(state["scope"])
    room.binding["initial_simulated_at"] = "2028-01-17T09:00:00Z"
    with pytest.raises(ProcedureError):
        room.state()
    room.binding["initial_simulated_at"] = "2028-01-18T09:00:00Z"
    state["simulated_at"] = "2028-01-18T08:59:59Z"
    with pytest.raises(ProcedureError):
        room.state()
    old_room, old_state = bound_room(legacy)
    assert old_room.state() is old_state
    assert subject.SCOPE["fieldwork_start"] == "2027-12-31"
