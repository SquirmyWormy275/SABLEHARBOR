"""One tiny native publisher/lifetime/normal retained-service seam, OWN only."""

import json
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.company_source_edition import publish_edition
from enterprise.audit_suite.company_source_lifetime import (
    EDITION_ADMISSION_SCHEMA,
    EDITION_FORMAT,
    EDITION_SCHEMA,
    POPULATION_BOUNDARY,
    initialize_edition_lifetime,
)
from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.persistent_company_journey import (
    RUNTIME_SCHEMA,
    RUNTIME_VERDICT,
    PersistentAudit,
    native_rows,
    write,
)
from enterprise.audit_suite.persistent_company_service import (
    BINDING_SCHEMA,
    configuration,
    create_retained_app,
)
from enterprise.audit_suite.source_library_audit import (
    EMPTY_WORKROOM,
    LIBRARY_REVIEW_SCHEMA,
    LIBRARY_REVIEW_VERDICT,
    AcceptedLibrary,
    BusinessRoute,
    file_sha,
)
from enterprise.audit_suite.store import Store, canonical
from enterprise.ccf.registry import compile_registry, digest

REPO = Path(__file__).resolve().parents[2]
COMPANY = "NEUTRAL-NATIVE-EDITION-RETAINED"
BRANCH = "CLEAN"


def review_for(edition):
    manifest = json.loads((edition / "MANIFEST.json").read_bytes())
    receipt = json.loads((edition / "SOURCE_EDITION.json").read_bytes())
    return {
        "schema": LIBRARY_REVIEW_SCHEMA,
        "verdict": LIBRARY_REVIEW_VERDICT,
        "source_quality_accepted_for_final_learner_audit": True,
        "library_pins": {
            "company.sqlite3": file_sha(edition / "company/company.sqlite3"),
            "MANIFEST.json": file_sha(edition / "MANIFEST.json"),
        },
        "native_versions": 2,
        "source_schema_admission": {
            "schema": EDITION_ADMISSION_SCHEMA,
            "manifest_format": EDITION_FORMAT,
            "source_edition_schema": EDITION_SCHEMA,
            "source_edition_sha256": manifest["members"]["SOURCE_EDITION.json"],
            "publisher_code_pins": receipt["code_pins"],
            "quiescent_source_only": True,
            "operating_provenance_reviewed": True,
            "audit_outcome_imports": False,
            "population_boundary": POPULATION_BOUNDARY,
        },
        "OWN_metadata_contract_exercise_only": True,
        "actual_admission": False,
    }


def accepted_for(edition, review=None, name="OWN-REVIEW.json"):
    path = edition / name
    write(path, review_for(edition) if review is None else review)
    return AcceptedLibrary(
        edition / "company/company.sqlite3",
        file_sha(edition / "company/company.sqlite3"),
        edition / "MANIFEST.json",
        file_sha(edition / "MANIFEST.json"),
        path,
        file_sha(path),
        2,
    )


@pytest.fixture(scope="module")
def published(tmp_path_factory):
    root = tmp_path_factory.mktemp("OWN-native-edition-source-first")
    root.chmod(0o700)
    original = root / "original-company"
    original.mkdir(mode=0o700)
    store = CompanyStore(original)
    for system, record in (
        ("operations.account_review", "REVIEW-ONE"),
        ("operations.policy_receipt", "RECEIPT-ONE"),
    ):
        store.register_system(COMPANY, BRANCH, system, "OWN-COMPANY-OWNER")
        store.append_version(
            COMPANY,
            BRANCH,
            system,
            record,
            expected_version=0,
            command_id="OWN-" + record,
            event_at="2027-01-02T00:00:00Z",
            available_at="2027-01-03T00:00:00Z",
            content=canonical(
                {
                    "engineering_neutral_fixture": True,
                    "name": "Unicode café",
                    "record": record,
                    "exact_boolean": False,
                }
            ).encode(),
            origin="AUTHORED_TRAINING_SOURCE",
            provenance={
                "source_reference": "OWN source operation before audit",
                "name": "operation.json",
                "content_type": "application/json",
            },
        )
    # Real operational access exists in the original but must not transfer.
    store.grant(
        "OWN-PREPUBLICATION-READER",
        "OWN-OLD-ENGAGEMENT",
        COMPANY,
        BRANCH,
        "operations.account_review",
    )
    edition = root / "published"
    publish_edition(
        [
            {
                "id": "OWN-original-native",
                "database": {"path": str(store.path), "sha256": file_sha(store.path)},
                "systems": 2,
                "versions": 2,
            }
        ],
        edition,
    )
    return {
        "root": root,
        "original": store.path,
        "original_sha256": file_sha(store.path),
        "native": native_rows(store.path),
        "edition": edition,
    }


def clone(published, tmp_path):
    tmp_path.chmod(0o700)
    target = tmp_path / "published"
    shutil.copytree(published["edition"], target)
    return target


def rewrite(path, body):
    path.write_text(canonical(body) + "\n")
    path.chmod(0o600)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_admission",
        "wrong_population_boundary",
        "wrong_publisher_pin",
        "admission_boolean_int",
    ],
)
def test_new_source_review_is_explicit(published, tmp_path, mutation):
    edition = clone(published, tmp_path)
    review = review_for(edition)
    if mutation == "missing_admission":
        del review["source_schema_admission"]
    elif mutation == "wrong_population_boundary":
        review["source_schema_admission"]["population_boundary"] = "ENTIRE_ENTERPRISE_ACCEPTED"
    elif mutation == "wrong_publisher_pin":
        review["source_schema_admission"]["publisher_code_pins"]["company_source_edition.py"] = (
            "0" * 64
        )
    else:
        review["source_schema_admission"]["quiescent_source_only"] = 1
    with pytest.raises(ValueError, match="external review"):
        accepted_for(edition, review).verify()


@pytest.mark.parametrize(
    "mutation", ["audit_credit", "boolean_native_count", "unknown_schema", "native_fingerprint"]
)
def test_resealed_format_limits_refuse(published, tmp_path, mutation):
    edition = clone(published, tmp_path)
    manifest = json.loads((edition / "MANIFEST.json").read_bytes())
    receipt = json.loads((edition / "SOURCE_EDITION.json").read_bytes())
    if mutation == "audit_credit":
        receipt["assessment_credit"] = True
    elif mutation == "boolean_native_count":
        receipt["native_counts"]["versions"] = True
    elif mutation == "unknown_schema":
        manifest["source_edition_schema"] = "UNSUPPORTED_NATIVE_EDITION"
    else:
        receipt["native_table_sha256"]["versions"] = "0" * 64
    rewrite(edition / "SOURCE_EDITION.json", receipt)
    manifest["members"]["SOURCE_EDITION.json"] = file_sha(edition / "SOURCE_EDITION.json")
    rewrite(edition / "MANIFEST.json", manifest)
    with pytest.raises(ValueError):
        accepted_for(edition).verify()


def test_source_sidecar_refuses_before_setup(published, tmp_path):
    edition = clone(published, tmp_path)
    accepted = accepted_for(edition)
    Path(str(accepted.database) + "-wal").write_bytes(b"OWN nonempty refusal")
    with pytest.raises(ValueError, match="sidecar"):
        accepted.verify()


@pytest.mark.parametrize(
    "mutation",
    [
        "incoming_trigger",
        "extra_index",
        "extra_table",
        "extra_view",
        "altered_trigger",
        "schema_version",
    ],
)
def test_resealed_incoming_schema_refuses(published, tmp_path, mutation):
    edition = clone(published, tmp_path)
    database = edition / "company/company.sqlite3"
    with sqlite3.connect(database) as db:
        if mutation == "incoming_trigger":
            db.execute(
                "CREATE TRIGGER incoming AFTER INSERT ON versions BEGIN DELETE FROM versions; END"
            )
        elif mutation == "extra_index":
            db.execute("CREATE INDEX incoming_index ON versions(record)")
        elif mutation == "extra_table":
            db.execute("CREATE TABLE incoming(extra TEXT)")
        elif mutation == "extra_view":
            db.execute("CREATE VIEW incoming AS SELECT * FROM versions")
        elif mutation == "altered_trigger":
            db.execute("DROP TRIGGER no_version_update")
            db.execute(
                "CREATE TRIGGER no_version_update BEFORE UPDATE ON versions BEGIN SELECT 1; END"
            )
        else:
            db.execute("PRAGMA user_version=1")
    # Exact native rows/fingerprints are still unchanged. Even resealed caller
    # pins cannot admit incoming SQL definitions as application-owned schema.
    assert native_rows(database) == published["native"]
    manifest = json.loads((edition / "MANIFEST.json").read_bytes())
    manifest["members"]["company/company.sqlite3"] = file_sha(database)
    rewrite(edition / "MANIFEST.json", manifest)
    with pytest.raises(ValueError, match="application-owned.*schema"):
        accepted_for(edition).verify()


def test_old_projection_format_remains_supported(published, tmp_path):
    edition = clone(published, tmp_path)
    legacy = {
        "schema": "SH_COMPANY_OPERATIONAL_PROJECTION_V2_1",
        "files": {"company.sqlite3": file_sha(edition / "company/company.sqlite3")},
    }
    rewrite(edition / "MANIFEST.json", legacy)
    review = {
        "schema": LIBRARY_REVIEW_SCHEMA,
        "verdict": LIBRARY_REVIEW_VERDICT,
        "source_quality_accepted_for_final_learner_audit": True,
        "library_pins": {
            "company.sqlite3": file_sha(edition / "company/company.sqlite3"),
            "MANIFEST.json": file_sha(edition / "MANIFEST.json"),
        },
        "native_versions": 2,
        "OWN_metadata_contract_exercise_only": True,
    }
    assert accepted_for(edition, review).verify()["version_count"] == 2


def runtime_review(accepted, target):
    body = {
        "schema": RUNTIME_SCHEMA,
        "verdict": RUNTIME_VERDICT,
        "source_execution_authorized": True,
        "runtime_module_sha256": file_sha(
            REPO / "enterprise/audit_suite/persistent_company_journey.py"
        ),
        "adapter_module_sha256": file_sha(REPO / "enterprise/audit_suite/source_library_audit.py"),
        "source_setup_module_sha256": file_sha(
            REPO / "enterprise/audit_suite/company_source_lifetime.py"
        ),
        "source_edition_sha256": json.loads(accepted.manifest.read_bytes())["members"][
            "SOURCE_EDITION.json"
        ],
        "accepted_baseline_pins": accepted.verify(),
        "OWN_metadata_contract_exercise_only": True,
        "actual_admission": False,
    }
    write(target, body)
    return target, file_sha(target)


def command(engine, actor, eid, kind, payload):
    return engine.command(
        actor,
        eid,
        {
            "command_id": "OWN-" + kind + "-" + str(engine.store.get(actor, eid)["revision"]),
            "expected_revision": engine.store.get(actor, eid)["revision"],
            "kind": kind,
            "payload": payload,
        },
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_setup_module_sha256", "0" * 64),
        ("source_edition_sha256", "0" * 64),
        ("source_execution_authorized", 1),
    ],
)
def test_runtime_admission_refuses_before_lifetime_output(published, tmp_path, field, value):
    edition = clone(published, tmp_path)
    accepted = accepted_for(edition)
    review_path, _ = runtime_review(accepted, tmp_path / "runtime.json")
    review = json.loads(review_path.read_bytes())
    review[field] = value
    rewrite(review_path, review)
    destination = tmp_path / "must-not-exist"
    with pytest.raises(ValueError, match="Runtime review"):
        initialize_edition_lifetime(
            accepted,
            destination,
            operator_id="OWN-SOURCE-OPERATOR",
            runtime_review=review_path,
            runtime_review_sha256=file_sha(review_path),
            engineering_only=True,
        )
    assert not destination.exists()


def test_native_edition_normal_lifetime_audit_retained_service(published, tmp_path, monkeypatch):
    tmp_path.chmod(0o700)
    accepted = accepted_for(published["edition"])
    edition_before = file_sha(accepted.database)
    runtime, runtime_sha = runtime_review(accepted, tmp_path / "OWN-runtime.json")
    world = initialize_edition_lifetime(
        accepted,
        tmp_path / "lifetime",
        operator_id="OWN-SOURCE-OPERATOR",
        runtime_review=runtime,
        runtime_review_sha256=runtime_sha,
        engineering_only=True,
    )
    assert native_rows(world.database) == published["native"]
    with world.store._db() as db:
        assert all(
            db.execute("SELECT COUNT(*) FROM " + t).fetchone()[0] == 0
            for t in ("grants", "collections", "access_events")
        )
    instructions = {
        "native_digest": digest(compile_registry(REPO)),
        "selections": {"baseline": {"controls": [], "actions": [], "dependency_gates": []}},
        "OWN_fixture_program_not_actual_full_pack_acceptance": True,
    }
    instructions["digest"] = digest(instructions)
    pack = tmp_path / "OWN-program.json"
    write(pack, instructions)
    pair = PersistentAudit(
        world,
        [
            BusinessRoute(
                COMPANY, BRANCH, "operations.account_review", "operations", "account_review"
            )
        ],
    )
    # Observe the genuine ordinary provision receipts in memory; no extra actors,
    # credential recovery, auth SQL edits or secrets in exported proofs.
    people = {}
    provision = Store.provision

    def observe_provision(self, name, roles, **options):
        receipt = provision(self, name, roles, **options)
        people[tuple(roles)] = receipt
        return receipt

    monkeypatch.setattr(Store, "provision", observe_provision)
    engine, initial, birth = pair.create(
        repository=REPO,
        audit_root=tmp_path / "audit",
        program_pack=pack,
        payload={
            "command_id": "OWN-native-edition-birth",
            "title": "Native edition normal retained seam",
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
            },
        },
    )
    monkeypatch.setattr(Store, "provision", provision)
    assert not any(birth["zero_workroom_counts"].values())
    assert all(
        t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN" for t in initial["tasks"]
    )
    ids, eid = pair.identities, initial["id"]
    command(engine, ids["operator"], eid, "company.activate", {})
    command(engine, ids["auditor"], eid, "kickoff.start", {})
    # A source route grants only this genuine newly created actor/engagement.
    world.store.grant(ids["auditor"], eid, COMPANY, BRANCH, "operations.account_review")
    binding = tmp_path / "BINDING.json"
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
            "zero_workroom_counts": {k: len(initial[k]) for k in EMPTY_WORKROOM},
        },
    )
    config = tmp_path / "CONFIG.json"
    write(config, configuration(world, binding, file_sha(binding), repository=REPO))
    app = create_retained_app(
        engine.store.root,
        config,
        file_sha(config),
        repository=REPO,
        allowed_hosts=["testserver"],
        secure_cookie=False,
    )
    assert people[("learner",)]["id"] == ids["auditor"] and len(people) == 3
    url = "/api/engagements/" + eid
    with TestClient(app) as client:
        assert client.get("/api/bootstrap").status_code == 401
        response = client.post(
            "/api/session", json={"credential": people[("learner",)]["credential"]}
        )
        assert response.status_code == 200, response.text
        headers = {"X-CSRF-Token": response.json()["csrf_token"]}
        assert client.get("/api/bootstrap").json()["capabilities"]["company_sources"] is True
        state = client.get(url).json()
        assert len(state["tasks"]) == len(initial["tasks"]) and not state["workpapers"]
        records = client.get(url + "/company/systems/operations.account_review/records")
        assert records.status_code == 200, records.text
        assert client.get(url + "/instructor-key").status_code == 403

        def post(kind, payload):
            current = client.get(url).json()
            result = client.post(
                url + "/commands",
                headers=headers,
                json={
                    "command_id": "OWN-HTTP-" + kind,
                    "kind": kind,
                    "payload": payload,
                    "expected_revision": current["revision"],
                },
            )
            assert result.status_code == 200, result.text
            return result.json()

        requested = post(
            "pbc.create",
            {
                "title": "Exact native source original",
                "purpose": "OWN ordinary source seam",
                "control_id": "SH-SEC-003",
                "person_id": "AS-P007",
                "boundary_id": "corporate",
            },
        )
        request = requested["requests"][-1]["id"]
        post("pbc.issue", {"request_id": request})
        collected = post(
            "company.collect",
            {
                "system_id": "operations.account_review",
                "record_id": "REVIEW-ONE",
                "version": 1,
                "request_id": request,
            },
        )
        artifact = collected["artifacts"][-1]
        body = app.state.engine.artifacts.read(artifact)
        assert json.loads(body)["exact_boolean"] is False
        assert client.post("/api/logout", headers=headers).status_code == 200
        assert client.get(url).status_code == 401
    # Cold config is constructed anew; no optional live object reuse supplied.
    cold = create_retained_app(
        engine.store.root,
        config,
        file_sha(config),
        repository=REPO,
        allowed_hosts=["testserver"],
        secure_cookie=False,
    )
    with TestClient(cold) as client:
        assert client.get("/api/bootstrap").status_code == 401
        response = client.post(
            "/api/session", json={"credential": people[("learner",)]["credential"]}
        )
        assert response.status_code == 200, response.text
        retained = client.get(url).json()
        assert retained["artifacts"] == collected["artifacts"] and not retained["workpapers"]
        assert cold.state.engine.artifacts.read(artifact) == body
        assert all(t["conclusion"] == "NOT_RUN" for t in retained["tasks"])
    with pytest.raises(ValueError):
        create_retained_app(engine.store.root, config, "0" * 64, repository=REPO)
    assert native_rows(world.database) == published["native"]
    assert file_sha(accepted.database) == edition_before
    assert file_sha(published["original"]) == published["original_sha256"]
    write(
        tmp_path / "OWN_SEAM.json",
        {
            "schema": "SH_OWN_NATIVE_EDITION_RETAINED_SERVICE_SEAM_V1",
            "normal_birth_task_count": len(initial["tasks"]),
            "normal_birth_control_count": len(initial["controls"]),
            "initial_zero_outcomes": birth["zero_workroom_counts"],
            "initial_simulated_at": initial["simulated_at"],
            "source_versions_before_audit": 2,
            "old_native_headers_and_bytes_unchanged": True,
            "source_operational_authority_not_transferred": True,
            "fresh_retained_app_and_cold_config": True,
            "ordinary_authenticated_HTTP_collection_count": 1,
            "learner_private_Key_refused": True,
            "cold_original_bytes_identical": True,
            "current_revision": retained["revision"],
            "fixture_metadata_only_not_actual_external_acceptance": True,
            "actual_inputs_used": False,
            "retained_config_module_count": len(json.loads(config.read_bytes())["code_pins"]),
            "project_python_origins": {
                name: {
                    "path": str(Path(module.__file__).resolve()),
                    "sha256": file_sha(Path(module.__file__).resolve()),
                }
                for name, module in sorted(sys.modules.items())
                if getattr(module, "__file__", None)
                and Path(module.__file__).resolve().is_relative_to(REPO)
                and Path(module.__file__).suffix == ".py"
            },
        },
    )
