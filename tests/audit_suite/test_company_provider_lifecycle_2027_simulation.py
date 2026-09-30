"""Provider lifecycle depends on reviewed native roles, not a vendor-list shortcut."""

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_provider_lifecycle_2027_simulation as simulation
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded

REPOSITORY = Path(__file__).resolve().parents[2]
OWNER_DECISION = (
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md"
)
TERM_IDS = (
    "permitted_uses_and_disclosures",
    "safeguards_and_security",
    "incident_and_breach_reporting",
    "subcontractor_flowdown",
    "rights_request_support",
    "regulator_records_access",
    "return_or_destruction_and_continuing_protection",
    "material_breach_cure_and_termination",
)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    path.chmod(0o600)


def _fixture_pair(tmp_path, monkeypatch, *, site_real_operation=False):
    transition = tmp_path / "transition"
    transition.mkdir(mode=0o700)
    phi = tmp_path / "phi"
    phi.mkdir(mode=0o700)
    trans_branches = {"CLEAN": "TRANS-CLEAN", "MESSY": "TRANS-MESSY"}
    phi_branches = {"CLEAN": "PHI-CLEAN", "MESSY": "PHI-MESSY"}
    trans_store = CompanyStore(transition)
    trans_records = {}
    for scenario, branch in trans_branches.items():
        for system in ("provider_contract", "site_release"):
            trans_store.register_system(simulation.COMPANY, branch, system, "AS-P013")
        trans_records[scenario] = []
        for site, provider, contract_at, release_at in (
            ("RENO", "CP-SWITCH", "2027-02-15T10:00:00+00:00", "2027-05-20T14:00:00+00:00"),
            (
                "BOISE",
                "CP-IDACORE",
                "2027-03-05T10:00:00+00:00",
                "2027-07-28T14:00:00+00:00" if scenario == "CLEAN" else "2027-08-10T14:00:00+00:00",
            ),
        ):
            for system, record, event, body in (
                (
                    "provider_contract",
                    f"C-{site}",
                    contract_at,
                    {
                        "status": "EXECUTED_SIMULATED",
                        "site": {"provider_id": provider},
                        "fictional_executed_terms": {
                            "master_terms": {
                                "ephi_processing": "NOT_AUTHORIZED_BY_THIS_CONTRACT",
                                "service": "Fictional facility only",
                                "provider_incident_notice_hours": 24,
                                "provider_security_report_frequency": "ANNUAL",
                                "exit_notice_days": 90,
                            }
                        },
                        "real_external_signature": False,
                        "real_world_provider_operation": site_real_operation,
                    },
                ),
                (
                    "site_release",
                    f"RL-{site}",
                    release_at,
                    {
                        "site": {"provider_id": provider},
                        "fictional_in_universe_operating_release": True,
                        "real_world_provider_operation": site_real_operation,
                        "actual_real_world_phi_processing": False,
                    },
                ),
            ):
                trans_records[scenario].append(
                    trans_store.append_version(
                        simulation.COMPANY,
                        branch,
                        system,
                        record,
                        expected_version=0,
                        command_id=f"T-{branch}-{record}",
                        event_at=event,
                        available_at=event,
                        content=encoded(body),
                        provenance={"source_reference": "fixture-transition"},
                    )
                )
    trans_receipt = {
        "schema": simulation.UPSTREAM["TRANSITION_V3"]["schema"],
        "company": simulation.COMPANY,
        "branches": trans_branches,
        "records": trans_records,
        "source_pins": {OWNER_DECISION: simulation.SOURCE_PINS[OWNER_DECISION]},
    }
    _write(transition / "RECEIPT.json", trans_receipt)
    _write(
        transition / "MANIFEST.json",
        {
            "schema": trans_receipt["schema"] + "_MANIFEST",
            "receipt_sha256": _sha(transition / "RECEIPT.json"),
            "company_db_sha256": _sha(transition / "company.sqlite3"),
            "audit_task_credit": False,
        },
    )
    transition_pins = {
        name: _sha(transition / filename)
        for name, filename in (
            ("receipt", "RECEIPT.json"),
            ("manifest", "MANIFEST.json"),
            ("database", "company.sqlite3"),
        )
    }
    phi_store = CompanyStore(phi)
    phi_records = {}
    for scenario, branch in phi_branches.items():
        for system in (
            "scenario_scope",
            "legal_decision",
            "contract_register",
            "flow_register",
            "exception_register",
        ):
            phi_store.register_system(simulation.COMPANY, branch, system, "AS-P003")
        phi_records[scenario] = []
        day = "2027-07-28" if scenario == "CLEAN" else "2027-08-10"
        items = [
            (
                "scenario_scope",
                "SCOPE-01",
                f"{day}T15:00:00+00:00",
                {
                    "sim_subcontractor_id": "SIM-RECOVERY-SUPPORT-01",
                    "actual_legal_applicability": "UNDETERMINED",
                    "fixture_contains_real_phi": False,
                },
            ),
            (
                "legal_decision",
                "ROLE-01",
                f"{day}T16:00:00+00:00",
                {
                    "legal_role_decision": "BA_AND_SUBCONTRACTOR_FOR_TRAINING_ONLY",
                    "real_world_legal_approval": False,
                },
            ),
            (
                "contract_register",
                "BAA-CUST-01",
                f"{day}T17:00:00+00:00",
                {
                    "contract_id": "SIM-BAA-CUST-01",
                    "real_signature_or_agreement": False,
                    "contract_executed_in_simulation": True,
                    "synthetic_terms": [
                        {
                            "clause_candidate_id": key,
                            "scenario_obligation": "Synthetic customer term",
                        }
                        for key in TERM_IDS
                    ],
                },
            ),
            (
                "contract_register",
                "BAA-SUB-01",
                f"{day}T18:00:00+00:00",
                {
                    "contract_id": "SIM-BAA-SUB-01",
                    "real_signature_or_agreement": False,
                    "contract_executed_in_simulation": True,
                    "synthetic_terms": [
                        {
                            "clause_candidate_id": key,
                            "scenario_obligation": "Synthetic support term",
                        }
                        for key in TERM_IDS
                    ],
                },
            ),
            (
                "flow_register",
                "FLOW-BOISE-01",
                f"{day}T19:00:00+00:00",
                {
                    "sim_subcontractor_id": "SIM-RECOVERY-SUPPORT-01",
                    "payload_bytes": 0,
                    "fixture_contains_real_phi": False,
                    "simulated_copy_reached_support": "SIMULATED_ACK_ONLY"
                    if scenario == "CLEAN"
                    else "UNDETERMINED",
                },
            ),
        ]
        if scenario == "MESSY":
            items.append(
                (
                    "exception_register",
                    "EXC-01",
                    f"{day}T20:00:00+00:00",
                    {
                        "exception_id": simulation.BA_EXCEPTION_ID,
                        "exception_open": True,
                    },
                )
            )
        for system, record, event, body in items:
            phi_records[scenario].append(
                phi_store.append_version(
                    simulation.COMPANY,
                    branch,
                    system,
                    record,
                    expected_version=0,
                    command_id=f"P-{branch}-{record}",
                    event_at=event,
                    available_at=event,
                    content=encoded(body),
                    provenance={"source_reference": "fixture-phi"},
                )
            )
    phi_receipt = {
        "schema": simulation.UPSTREAM["PHI_BA_V1"]["schema"],
        "company": simulation.COMPANY,
        "branches": phi_branches,
        "records": phi_records,
        "source_pins": {OWNER_DECISION: simulation.SOURCE_PINS[OWNER_DECISION]},
        "transition_pins": transition_pins,
        "transition_releases": {
            scenario: {
                site: next(x for x in trans_records[scenario] if x["record"] == f"RL-{site}")
                for site in ("RENO", "BOISE")
            }
            for scenario in ("CLEAN", "MESSY")
        },
        "open_exception_ids": {
            "CLEAN": [],
            "MESSY": [simulation.BA_EXCEPTION_ID],
        },
    }
    _write(phi / "RECEIPT.json", phi_receipt)
    _write(
        phi / "MANIFEST.json",
        {
            "schema": phi_receipt["schema"] + "_MANIFEST",
            "receipt_sha256": _sha(phi / "RECEIPT.json"),
            "company_db_sha256": _sha(phi / "company.sqlite3"),
            "audit_task_credit": False,
        },
    )
    pins = {key: dict(value) for key, value in simulation.UPSTREAM.items()}
    pins["TRANSITION_V3"].update(transition_pins)
    pins["PHI_BA_V1"].update(
        {
            name: _sha(phi / filename)
            for name, filename in (
                ("receipt", "RECEIPT.json"),
                ("manifest", "MANIFEST.json"),
                ("database", "company.sqlite3"),
            )
        }
    )
    monkeypatch.setattr(simulation, "UPSTREAM", pins)
    return transition, phi


def _create(tmp_path, transition, phi):
    dest = tmp_path / "lifecycle"
    manifest = simulation.create(
        dest,
        repository=REPOSITORY,
        transition_root=transition,
        phi_root=phi,
        clean_branch="LIFE-CLEAN",
        messy_branch="LIFE-MESSY",
    )
    return dest, manifest


def test_three_relationships_q4_checks_and_distinct_historical_exception(tmp_path, monkeypatch):
    transition, phi = _fixture_pair(tmp_path, monkeypatch)
    dest, manifest = _create(tmp_path, transition, phi)
    assert manifest["native_version_count"] == 24
    assert (
        simulation.verify(dest, repository=REPOSITORY, transition_root=transition, phi_root=phi)
        == manifest
    )
    receipt = json.loads((dest / "RECEIPT.json").read_text())
    assert receipt["initial_relationship_counts"] == {"CLEAN": 3, "MESSY": 2}
    assert receipt["final_relationship_counts"] == {"CLEAN": 3, "MESSY": 3}
    assert receipt["q4_internal_review_counts"] == {"CLEAN": 3, "MESSY": 3}
    assert receipt["open_exception_counts"] == {"CLEAN": 0, "MESSY": 1}
    assert receipt["exception_event_row_counts"] == {"CLEAN": 0, "MESSY": 2}
    with sqlite3.connect(dest / "company.sqlite3") as db:
        db.row_factory = sqlite3.Row
        bodies = [json.loads(x[0]) for x in db.execute("SELECT content FROM versions")]
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0
    clean_pop = next(
        x for x in bodies if x["scenario"] == "CLEAN" and x["system"] == "population_reconcile"
    )
    messy_pop = next(
        x for x in bodies if x["scenario"] == "MESSY" and x["system"] == "population_reconcile"
    )
    assert clean_pop["missing_provider_ids"] == []
    assert messy_pop["missing_provider_ids"] == ["SIM-RECOVERY-SUPPORT-01"]
    assert (
        messy_pop["independent_expected_source_refs"]["SUPPORT_FLOW"]["record"] == "FLOW-BOISE-01"
    )
    backfill = next(x for x in bodies if x["scenario"] == "MESSY" and x["record"] == "REL-SUPPORT")
    assert backfill["event_at"] < backfill["available_at"]
    exceptions = [
        x for x in bodies if x["scenario"] == "MESSY" and x["system"] == "exception_register"
    ]
    assert [x["version"] for x in exceptions] == [1, 2]
    assert all(
        x["exception_id"] == simulation.EXCEPTION_ID and x["status"] == "OPEN" for x in exceptions
    )
    assert all(x["ba_late_flowdown_exception_id"] == simulation.BA_EXCEPTION_ID for x in exceptions)
    assert simulation.EXCEPTION_ID != simulation.BA_EXCEPTION_ID
    reviews = [x for x in bodies if x["system"] == "review_register"]
    assert len(reviews) == 6
    assert all(x["external_assurance_request_status"] == "NOT_SENT_NOT_RECEIVED" for x in reviews)
    assert all(x["vendor_report_or_representation"] == "NONE" for x in reviews)
    assert sorted(len(x["obligation_checks"]) for x in reviews) == [5, 5, 5, 5, 8, 8]
    assert all(
        check["internal_result"] == "SOURCE_TERM_INDEXED_ONLY"
        and check["external_performance_state"] == "NOT_VERIFIED"
        for review in reviews
        for check in review["obligation_checks"]
    )
    assert all(
        x["offboarding_readiness"] == "TERMS_INDEXED_ONLY_NO_ACTUAL_OFFBOARDING" for x in reviews
    )
    assert all(
        x["real_world_provider_operation"] is False
        and x["actual_real_world_phi_processing"] is False
        and x["audit_task_credit"] is False
        for x in bodies
    )


def test_missing_independent_support_flow_blocks_even_when_repinning(tmp_path, monkeypatch):
    transition, phi = _fixture_pair(tmp_path, monkeypatch)
    receipt_path, manifest_path = phi / "RECEIPT.json", phi / "MANIFEST.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["records"]["MESSY"] = [
        x for x in receipt["records"]["MESSY"] if x["record"] != "FLOW-BOISE-01"
    ]
    _write(receipt_path, receipt)
    manifest = json.loads(manifest_path.read_text())
    manifest["receipt_sha256"] = _sha(receipt_path)
    _write(manifest_path, manifest)
    simulation.UPSTREAM["PHI_BA_V1"].update(
        {"receipt": _sha(receipt_path), "manifest": _sha(manifest_path)}
    )
    with pytest.raises(CompanyStoreError, match="Required upstream native source tuple"):
        _create(tmp_path, transition, phi)
    assert not (tmp_path / "lifecycle").exists()


def test_dangling_upstream_sidecar_blocks_source(tmp_path, monkeypatch):
    transition, phi = _fixture_pair(tmp_path, monkeypatch)
    (transition / "company.sqlite3-shm").symlink_to(transition / "missing-shm")
    with pytest.raises(CompanyStoreError, match="no sidecars"):
        _create(tmp_path, transition, phi)


def test_real_provider_operation_claim_blocks_source(tmp_path, monkeypatch):
    transition, phi = _fixture_pair(tmp_path, monkeypatch, site_real_operation=True)
    with pytest.raises(CompanyStoreError, match="Site contract/release boundary"):
        _create(tmp_path, transition, phi)


def test_source_mode_change_during_immutable_read_blocks_source(tmp_path, monkeypatch):
    transition, phi = _fixture_pair(tmp_path, monkeypatch)
    original = simulation._frozen
    first = True

    def flip(paths):
        nonlocal first
        snapshot = original(paths)
        if first:
            first = False
            paths["database"].chmod(0o644)
        return snapshot

    monkeypatch.setattr(simulation, "_frozen", flip)
    with pytest.raises(CompanyStoreError, match="Private regular source file"):
        _create(tmp_path, transition, phi)


def test_lifecycle_receipt_tamper_rejected_after_manifest_repin(tmp_path, monkeypatch):
    transition, phi = _fixture_pair(tmp_path, monkeypatch)
    dest, _manifest = _create(tmp_path, transition, phi)
    receipt_path, manifest_path = dest / "RECEIPT.json", dest / "MANIFEST.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["open_exception_counts"]["MESSY"] = 0
    _write(receipt_path, receipt)
    manifest = json.loads(manifest_path.read_text())
    manifest["receipt_sha256"] = _sha(receipt_path)
    _write(manifest_path, manifest)
    with pytest.raises(CompanyStoreError, match="Lifecycle receipt/manifest scope"):
        simulation.verify(dest, repository=REPOSITORY, transition_root=transition, phi_root=phi)


def test_lifecycle_limit_upgrade_rejected_after_manifest_repin(tmp_path, monkeypatch):
    transition, phi = _fixture_pair(tmp_path, monkeypatch)
    dest, _manifest = _create(tmp_path, transition, phi)
    receipt_path, manifest_path = dest / "RECEIPT.json", dest / "MANIFEST.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["limits"][1] = "Real vendor operation and response confirmed"
    _write(receipt_path, receipt)
    manifest = json.loads(manifest_path.read_text())
    manifest["receipt_sha256"] = _sha(receipt_path)
    _write(manifest_path, manifest)
    with pytest.raises(CompanyStoreError, match="Lifecycle receipt/manifest scope"):
        simulation.verify(dest, repository=REPOSITORY, transition_root=transition, phi_root=phi)
