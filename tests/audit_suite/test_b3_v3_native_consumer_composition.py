"""One tiny native list-reader/documentary WP and same-room V3 composition."""

import json
import os
import sys
from pathlib import Path

import pytest

from enterprise.audit_suite import source_native_operating_methods as native
from enterprise.audit_suite.company_source_edition import publish_edition
from enterprise.audit_suite.company_source_lifetime import initialize_edition_lifetime
from enterprise.audit_suite.company_store import CompanyStore, _time
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
from enterprise.audit_suite.source_continuity_methods import examine as continuity
from enterprise.audit_suite.source_governance_methods import examine as governance
from enterprise.audit_suite.source_library_audit import EMPTY_WORKROOM, AcceptedLibrary, file_sha
from enterprise.audit_suite.source_workforce_methods import inspections as workforce
from enterprise.audit_suite.store import DomainError
from enterprise.ccf.registry import compile_registry, digest
from tests.audit_suite.test_b3_v3_reference_index_composition import _events, _private_archive
from tests.audit_suite.test_native_edition_retained_setup import (
    review_for,
    runtime_review,
)
from tests.audit_suite.test_persistent_company_service import command, login

COMPANY, BRANCH = "NEUTRAL-NATIVE-V3-COMPOSITION", "ALPHA"
REPO = Path(__file__).resolve().parents[2]


def test_genuine_native_list_qualified_workpaper_and_same_room_v3(tmp_path, monkeypatch):
    assert sys.version_info >= (3, 11)
    tmp_path.chmod(0o700)
    root = tmp_path / "independent-source-before-audit"
    root.mkdir(mode=0o700)
    original = CompanyStore(root)
    at = _time("2027-01-01T00:00:00Z")
    item = {
        "id": "DECLARED-POLICY",
        "system_id": "OWN-POLICY-NATIVE",
        "kind": "POLICY",
        "operating_from": at,
        "operating_to_exclusive": _time("2028-01-01T00:00:00Z"),
        "commissioning_ref": None,
    }
    calendar = {
        "declared_at": at,
        "period_start": at,
        "period_end_exclusive": _time("2027-01-02T00:00:00Z"),
        "cadence_days": 1,
        "due_offset_days": 1,
        "items": [item],
        "exclusions": [],
    }

    def append(system, record, body, mime="application/json"):
        original.register_system(COMPANY, BRANCH, system, "OWN-SOURCE-OWNER")
        return original.append_version(
            COMPANY,
            BRANCH,
            system,
            record,
            expected_version=0,
            command_id="OWN-SOURCE-" + system + "-" + record,
            event_at=at,
            available_at=at,
            content=body if type(body) is bytes else native.encoded(body),
            provenance={
                "source_reference": "OWN independent native source before audit",
                "name": record + (".bin" if mime == "application/octet-stream" else ".json"),
                "content_type": mime,
            },
        )

    inventory = append(
        "business_inventory",
        "OWN-BUSINESS",
        {"systems": [{"system": item["system_id"]}], "operating_depth_calendar": calendar},
    )
    definition = {
        "schema": "SH_COMPANY_NATIVE_OPERATING_DEPTH_DECLARATION_V1",
        "runtime_id": "OWN-CALENDAR",
        "company": COMPANY,
        "branch": BRANCH,
        "recorded_at": at,
        "inventory_scope": "EXPLICIT_COMPANY_BUSINESS_INVENTORY_NOT_SELECTED_AUDIT_ARTIFACTS",
        **calendar,
        "business_inventory_ref": {k: inventory[k] for k in native.PIN},
        "retained_period_refs": [],
        "local_basis": "OWN tiny fixture; no activity assertion",
    }
    append("operating_depth_definition", "OWN-CALENDAR", definition)
    append(
        "source_dataset",
        "OWN-OPAQUE",
        b"OWN bounded opaque bytes\x00\xff",
        "application/octet-stream",
    )
    original_pin, original_native = file_sha(original.path), native_rows(original.path)
    edition = tmp_path / "published-native"
    publish_edition(
        [
            {
                "id": "OWN-native-before-audit",
                "database": {"path": str(original.path), "sha256": original_pin},
                "systems": 3,
                "versions": 3,
            }
        ],
        edition,
    )
    review = review_for(edition)
    review["native_versions"] = 3
    review["qualified_OWN_source_contract_only_not_actual_admission"] = True
    review_path = tmp_path / "OWN-SOURCE-REVIEW.json"
    write(review_path, review)
    accepted = AcceptedLibrary(
        edition / "company/company.sqlite3",
        file_sha(edition / "company/company.sqlite3"),
        edition / "MANIFEST.json",
        file_sha(edition / "MANIFEST.json"),
        review_path,
        file_sha(review_path),
        3,
    )
    source_before = file_sha(accepted.database)
    runtime, runtime_pin = runtime_review(accepted, tmp_path / "OWN-EDITION-RUNTIME.json")
    world = initialize_edition_lifetime(
        accepted,
        tmp_path / "lifetime",
        operator_id="OWN-V3-EDITION-OPERATOR",
        runtime_review=runtime,
        runtime_review_sha256=runtime_pin,
        engineering_only=False,
    )
    initial_native = native_rows(world.database)
    assert initial_native == original_native and len(initial_native) == 3
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
                "fieldwork_start": "2028-01-18",
                "timezone": "UTC",
                "boundaries": ["corporate"],
                "control_ids": ["SH-POL-001"],
            },
        },
    )
    eid = initial["id"]
    engine.store.grant(eid, ids["auditor"], "learn")
    engine.store.grant(eid, ids["reviewer"], "review")
    engine.company_bindings[eid] = {"company": COMPANY, "branch": BRANCH}
    command(engine, ids["operator"], eid, "company.activate", {})
    command(engine, ids["auditor"], eid, "kickoff.start", {})
    systems = ("business_inventory", "operating_depth_definition", "source_dataset")
    for system in systems:
        world.store.grant(ids["auditor"], eid, COMPANY, BRANCH, system)
    requested = command(
        engine,
        ids["auditor"],
        eid,
        "pbc.create",
        {
            "title": "Existing edition source",
            "purpose": "Owned V3 source seam",
            "control_id": "SH-POL-001",
            "person_id": "AS-P007",
            "boundary_id": "corporate",
        },
    )
    request = requested["requests"][-1]["id"]
    command(engine, ids["auditor"], eid, "pbc.issue", {"request_id": request})
    for system, record in [
        ("business_inventory", "OWN-BUSINESS"),
        ("operating_depth_definition", "OWN-CALENDAR"),
        ("source_dataset", "OWN-OPAQUE"),
    ]:
        command(
            engine,
            ids["auditor"],
            eid,
            "company.collect",
            {"system_id": system, "record_id": record, "version": 1, "request_id": request},
        )
    before = engine.store.get(ids["auditor"], eid)
    rows = native.retained_inputs(
        engine, ids["auditor"], eid, [a["id"] for a in before["artifacts"]]
    )
    assert type(rows) is list and len(rows) == 3
    opaque = next(a for a in before["artifacts"] if a["name"].endswith(".bin"))
    assert opaque["status"] == "QUARANTINED"
    assert opaque["quarantine_reason"] == native.UNSUPPORTED_INTAKE
    observations = native.examine(rows, as_of=before["simulated_at"])
    assert observations and observations[0]["status"] == "SUPPORT_UNAVAILABLE"
    assert not observations[0]["facts"]["complete_native_operation_inventory_established"]
    results = {
        "workforce": workforce(rows, as_of=before["simulated_at"]),
        "governance": governance(rows, as_of=before["simulated_at"]),
        "continuity": continuity(rows, as_of=before["simulated_at"], scratch_root=tmp_path),
    }
    assert {k: len(v) for k, v in results.items()} == {
        "workforce": 52,
        "governance": 62,
        "continuity": 20,
    }
    assert engine.store.get(ids["auditor"], eid) == before
    task = next(t for t in before["tasks"] if t["kind"] == "TOE")
    inspected = next(r for r in results["governance"] if r["task_id"] == task["id"])
    assert inspected["result"]["native_operating_attributes"]
    assert inspected["disposition"]["conclusion"] == "LIMITATION"
    text = {
        "observations": inspected["observations"],
        "performed": inspected["performed"],
        "unperformed": inspected["unperformed"],
        "professional_acceptance": "NOT_ASSERTED",
        "opaque_bytes_scope": "HELD_BYTES_SHA_ONLY_NO_RESTORE_OR_INGESTION_ACCEPTANCE",
        "raw_original_custody": [
            {
                "artifact_id": r["artifact_id"],
                "native": r["source"],
                "artifact_intake": r["artifact_intake"],
            }
            for r in rows
        ],
        "population_sample_retest_or_full_clause_credit": False,
    }
    documented = command(
        engine,
        ids["auditor"],
        eid,
        "workpaper.add",
        {
            "title": "Qualified native period and raw custody",
            "control_id": task["control_id"],
            "task_ids": [task["id"]],
            "text": json.dumps(text, sort_keys=True),
            "objective": inspected["performed"],
            "procedures": inspected["performed"] + inspected["unperformed"],
            "evidence_ids": [r["artifact_id"] for r in rows],
            "conclusion": "LIMITATION",
        },
    )
    state = command(
        engine,
        ids["auditor"],
        eid,
        "task.update",
        {
            "task_id": task["id"],
            "status": "IN_PROGRESS",
            "conclusion": "LIMITATION",
            "rationale": (
                "Exact selected calendar; no collected due followthrough, "
                "no population/sample/retest credit"
            ),
        },
    )
    state = engine.store.get(ids["auditor"], eid)
    assert (
        len(state["workpapers"]) == 1
        and not state["populations"]
        and not state["sample_executions"]
    )
    assert documented["workpapers"][0]["versions"][0]["evidence_ids"] == [
        r["artifact_id"] for r in rows
    ]
    with pytest.raises(DomainError, match="Quarantined content"):
        command(engine, ids["auditor"], eid, "population.import", {"artifact_id": opaque["id"]})
    assert engine.store.get(ids["auditor"], eid) == state
    source = next(
        r["source"] for r in rows if r["source"]["system"] == "operating_depth_definition"
    )
    world.store.grant(world.operator.principal, eid, COMPANY, BRANCH, source["system"])
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
                    "control_ids": ["SH-POL-001"],
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
    assert response.json()["reference_crosswalk"]["rows"]
    assert teacher.get(url + "/instructor-key/MM-13.03.V01/original").status_code == 200
    assert learner.get(url + "/instructor-key").status_code == 403
    assert app.state.engine is retained.engine
    assert native_rows(world.database) == initial_native
    assert file_sha(world.database) == before_company
    assert file_sha(accepted.database) == source_before
    assert file_sha(original.path) == original_pin and native_rows(original.path) == original_native
    assert state["artifacts"] == before["artifacts"]
    assert _events(app.state.engine.store, eid) == before_events
    assert app.state.engine.store.get(ids["auditor"], eid) == state
    loaded, namespaces = {}, {}
    for name, module in sorted(sys.modules.items()):
        path = getattr(module, "__file__", None)
        if (
            not path
            and name.startswith(("enterprise", "tools", "src", "tests"))
            and hasattr(module, "__path__")
        ):
            locations = list(module.__path__)
            spec_locations = list(module.__spec__.submodule_search_locations)
            assert locations == spec_locations
            namespaces[name] = {"path": locations, "spec_search_locations": spec_locations}
            assert all(Path(location).resolve().is_relative_to(REPO) for location in locations)
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
        Path(os.environ.get("B3_V3_OWN_OUTPUT", str(tmp_path)))
        / "OWN_NATIVE_V3_COMPOSITION_RESULT.json",
        {
            "schema": "SH_OWN_NATIVE_LIST_DOCUMENTARY_WORKPAPER_V3_COMPOSITION_V1",
            "status": "PASS_EXPLICIT_NATIVE_EDITION_LIFETIME_RETAINED_V3",
            "task_count": len(initial["tasks"]),
            "native_versions": 3,
            "ordinary_collection_count": 3,
            "pure_callback_counts": {k: len(v) for k, v in results.items()},
            "qualified_workpapers": 1,
            "opaque_QUARANTINED_unchanged": True,
            "population_refusal_preserved": True,
            "sample_executions": 0,
            "world_initialization_engineering_only": False,
            "explicit_OWN_reviews_no_actual_admission": True,
            "task_disposition": {
                k: next(t for t in state["tasks"] if t["id"] == task["id"])[k]
                for k in ("id", "status", "conclusion")
            },
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
            "observed_namespaces": namespaces,
            "intake": [
                {
                    k: a[k]
                    for k in (
                        "id",
                        "name",
                        "mime",
                        "status",
                        "quarantine_reason",
                        "sha256",
                        "bytes",
                    )
                }
                for a in state["artifacts"]
            ],
            "public_checks": {"instructor_binding": response.status_code, "learner_key": 403},
            "source_original": {"path": str(original.path), "sha256": original_pin},
            "published_source": {"path": str(accepted.database), "sha256": source_before},
            "workpaper_text_digest": digest(text),
            "native14_and_public_events_unchanged": True,
            "published_library_unchanged": True,
            "actual_inputs_used": False,
            "professional_acceptance": "NOT_ASSERTED",
        },
    )
