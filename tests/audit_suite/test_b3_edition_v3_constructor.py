"""One explicit source-edition lifetime to retained V3 seam; two own native originals."""

import json
import os
import sys
from pathlib import Path

from enterprise.audit_suite.company_source_lifetime import initialize_edition_lifetime
from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.explanation_binding import bind_snapshot
from enterprise.audit_suite.instructor_reference_crosswalk import build_reference_crosswalk
from enterprise.audit_suite.persistent_company_journey import native_rows, write
from enterprise.audit_suite.persistent_company_service import (
    BINDING_SCHEMA,
    RetainedWorkroom,
    configuration,
)
from enterprise.audit_suite.retained_explanation_service import (
    create_explained_app,
    reference_configuration,
)
from enterprise.audit_suite.source_library_audit import EMPTY_WORKROOM, file_sha
from enterprise.ccf.registry import compile_registry, digest
from tests.audit_suite.test_b3_v3_reference_index_composition import _events, _private_archive
from tests.audit_suite.test_native_edition_retained_setup import (
    BRANCH,
    COMPANY,
    accepted_for,
    runtime_review,
)
from tests.audit_suite.test_persistent_company_service import command, login

pytest_plugins = ["tests.audit_suite.test_native_edition_retained_setup"]
REPO = Path(__file__).resolve().parents[2]


def test_explicit_published_edition_lifetime_reaches_same_room_v3(published, tmp_path, monkeypatch):
    tmp_path.chmod(0o700)
    accepted = accepted_for(published["edition"])
    source_before = file_sha(accepted.database)
    runtime, runtime_pin = runtime_review(accepted, tmp_path / "OWN-EDITION-RUNTIME.json")
    world = initialize_edition_lifetime(
        accepted,
        tmp_path / "lifetime",
        operator_id="OWN-V3-EDITION-OPERATOR",
        runtime_review=runtime,
        runtime_review_sha256=runtime_pin,
        engineering_only=True,
    )
    initial_native = native_rows(world.database)
    assert initial_native == published["native"]
    instructions = {
        "native_digest": digest(compile_registry(REPO)),
        "selections": {"baseline": {"controls": [], "actions": [], "dependency_gates": []}},
        "engineering_fixture_not_actual_program_acceptance": True,
    }
    instructions["digest"] = digest(instructions)
    pack = tmp_path / "OWN-EDITION-PACK.json"
    write(pack, instructions)
    engine = Engine(tmp_path / "audit", repository=REPO, program_pack=pack)
    engine.company_store = world.store
    people = {
        role: engine.store.provision("Owned edition " + role, [permission])
        for role, permission in (
            ("operator", "instructor"),
            ("auditor", "learner"),
            ("reviewer", "reviewer"),
        )
    }
    ids = {key: value["id"] for key, value in people.items()}
    initial = engine.create(
        ids["operator"],
        {
            "command_id": "OWN-EDITION-V3-BIRTH",
            "title": "Owned published-edition V3 seam",
            "discipline": "IT",
            "mode": "CLEAN",
            "configuration": {"selections": []},
            "scope": {
                "programs": ["SOC2", "HIPAA"],
                "report_type": "Type 2",
                "period_start": "2027-01-01",
                "period_end": "2027-12-31",
                "fieldwork_start": "2028-01-16",
                "timezone": "UTC",
                "boundaries": ["corporate"],
                "control_ids": ["SH-SEC-003"],
            },
        },
    )
    eid = initial["id"]
    engine.store.grant(eid, ids["auditor"], "learn")
    engine.store.grant(eid, ids["reviewer"], "review")
    engine.company_bindings[eid] = {"company": COMPANY, "branch": BRANCH}
    command(engine, ids["operator"], eid, "company.activate", {})
    command(engine, ids["auditor"], eid, "kickoff.start", {})
    system = "operations.account_review"
    world.store.grant(ids["auditor"], eid, COMPANY, BRANCH, system)
    requested = command(
        engine,
        ids["auditor"],
        eid,
        "pbc.create",
        {
            "title": "Existing edition source",
            "purpose": "Owned V3 source seam",
            "control_id": "SH-SEC-003",
            "person_id": "AS-P007",
            "boundary_id": "corporate",
        },
    )
    request = requested["requests"][-1]["id"]
    command(engine, ids["auditor"], eid, "pbc.issue", {"request_id": request})
    command(
        engine,
        ids["auditor"],
        eid,
        "company.collect",
        {
            "system_id": system,
            "record_id": "REVIEW-ONE",
            "version": 1,
            "request_id": request,
        },
    )
    state = engine.store.get(ids["auditor"], eid)
    source = state["artifacts"][0]["source"]["receipt"]["source"]
    world.store.grant(world.operator.principal, eid, COMPANY, BRANCH, system)
    snapshot = tmp_path / "snapshot"
    binding_receipt = bind_snapshot(
        engine,
        instructor_id=ids["operator"],
        audited_actor_id=ids["auditor"],
        engagement_id=eid,
        source_operator_id=world.operator.principal,
        source_as_of=state["simulated_at"],
        source_refs=[
            {
                "id": "OWN-NATIVE",
                **{
                    key: source[key]
                    for key in ("company", "branch", "system", "record", "version", "sha256")
                },
            }
        ],
        authored={
            "issues": [
                {
                    "id": "OWN-EDITION-CARD",
                    "control_ids": ["SH-SEC-003"],
                    "source_ids": ["OWN-NATIVE"],
                    "claim": "Owned byte-bound edition source",
                    "uncertainty": "No professional or whole-period acceptance",
                }
            ],
            "expectations": [],
            "uncertainty": ["Engineering only"],
            "source_pins": {},
        },
        output=snapshot,
    )
    bindings = tmp_path / "OWN-BINDINGS.json"
    write(
        bindings,
        {eid: {"path": str(snapshot), "manifest_sha256": binding_receipt["manifest_sha256"]}},
    )
    binding = tmp_path / "OWN-RETAINED-BINDING.json"
    write(
        binding,
        {
            "schema": BINDING_SCHEMA,
            "company_root": str(world.root),
            "company_initialization_sha256": file_sha(world.root / "INITIALIZATION.json"),
            "accepted_baseline_pins": world.pins,
            "audit_root": str(engine.store.root),
            "engagement_id": eid,
            "company": COMPANY,
            "branch": BRANCH,
            "identities": ids,
            "company_operator_id": world.operator.principal,
            "program_pack": {"path": str(pack), "sha256": file_sha(pack)},
            "task_count": len(initial["tasks"]),
            "mode": initial["mode"],
            "initial_simulated_at": initial["simulated_at"],
            "scope": initial["scope"],
            "zero_workroom_counts": {key: len(initial[key]) for key in EMPTY_WORKROOM},
        },
    )
    retained_config = tmp_path / "OWN-RETAINED-CONFIG.json"
    write(retained_config, configuration(world, binding, file_sha(binding), repository=REPO))
    selection = _private_archive(tmp_path / "owned-reference", monkeypatch)
    pin = build_reference_crosswalk(
        selection,
        json.loads((snapshot / "snapshot.json").read_bytes()),
        tmp_path / "OWN-CROSSWALK.json",
        engineering_neutral_only=True,
    )
    config = tmp_path / "OWN-EDITION-V3.json"
    write(
        config,
        reference_configuration(
            retained_config,
            file_sha(retained_config),
            bindings,
            file_sha(bindings),
            repository=REPO,
            instructor_writeback=True,
            background_jobs=False,
            reference_archive=selection,
            reference_crosswalk=pin,
        ),
    )
    retained = RetainedWorkroom(
        retained_config, file_sha(retained_config), private_root=engine.store.root, repository=REPO
    )
    retained.refresh_integrity(ids["operator"])
    before_events = _events(retained.engine.store, eid)
    before_company = file_sha(world.database)
    app = create_explained_app(
        engine.store.root,
        config,
        file_sha(config),
        repository=REPO,
        retained_workroom=retained,
        allowed_hosts=["testserver"],
    )
    teacher, _ = login(app, {"people": people}, "operator")
    learner, _ = login(app, {"people": people}, "auditor")
    url = "/api/engagements/" + eid
    response = teacher.get(url + "/instructor-binding")
    assert response.status_code == 200, response.text
    assert (
        response.json()["reference_crosswalk"]["rows"][0]["relations"][0]["status"]
        == "SHARED_CONTROL_ONLY"
    )
    assert teacher.get(url + "/instructor-key/MM-13.03.V01/original").status_code == 200
    assert learner.get(url + "/instructor-key").status_code == 403
    assert app.state.engine is retained.engine
    assert native_rows(world.database) == initial_native
    assert file_sha(world.database) == before_company
    assert file_sha(accepted.database) == source_before
    assert _events(app.state.engine.store, eid) == before_events
    assert app.state.engine.store.get(ids["auditor"], eid) == state
    loaded = {}
    for name, module in sorted(sys.modules.items()):
        path = getattr(module, "__file__", None)
        if path and (
            Path(path).is_relative_to(REPO) or name.startswith(("cryptography", "_cffi_backend"))
        ):
            path = Path(path).absolute()
            assert Path(module.__spec__.origin).absolute() == path
            loaded[name] = {
                "path": str(path),
                "sha256": file_sha(path),
                "spec_origin": module.__spec__.origin,
            }
    write(
        Path(os.environ.get("B3_V3_OWN_OUTPUT", str(tmp_path))) / "OWN_EDITION_V3_RESULT.json",
        {
            "schema": "SH_OWN_EXPLICIT_SOURCE_EDITION_V3_CONSTRUCTOR_SEAM_V1",
            "status": "PASS_EXPLICIT_NATIVE_EDITION_LIFETIME_RETAINED_V3",
            "task_count": len(initial["tasks"]),
            "native_versions": 2,
            "ordinary_collection_count": 1,
            "source_edition_branch_exercised": True,
            "source_setup_sha256": file_sha(
                REPO / "enterprise/audit_suite/company_source_lifetime.py"
            ),
            "source_manifest_format": json.loads(accepted.manifest.read_bytes())["format"],
            "source_schema_admission": json.loads(accepted.review.read_bytes())[
                "source_schema_admission"
            ],
            "same_room_reused": True,
            "loaded_file_modules": loaded,
            "native14_and_public_events_unchanged": True,
            "published_library_unchanged": True,
            "actual_inputs_used": False,
            "professional_acceptance": "NOT_ASSERTED",
        },
    )
