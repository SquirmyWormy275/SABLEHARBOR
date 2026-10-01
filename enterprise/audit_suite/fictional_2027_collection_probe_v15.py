"""Disposable source-to-collector probe for the reviewed partial V15 portfolio.

Only ordinary-byte copies receive grants and collection journals. This is a
diagnostic of source access, not an audit engagement or an evidence population.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
from pathlib import Path

from . import fictional_2027_collection_probe_v14 as prior_probe
from . import fictional_2027_source_portfolio_v11 as v11_portfolio
from . import fictional_2027_source_portfolio_v12 as v12_portfolio
from . import fictional_2027_source_portfolio_v13 as v13_portfolio
from . import fictional_2027_source_portfolio_v14 as v14_portfolio
from . import fictional_2027_source_portfolio_v15 as v15_portfolio
from .company_federation import FederatedCompanyStore
from .company_store import CompanyStore, CompanyStoreError
from .documentary_283_route_reconciliation_v6 import _p1_inventory
from .fictional_2027_candidate_registry import CandidateRegistryError, _json, _private, _sha
from .fictional_2027_candidate_registry_v15 import candidate_profiles, verify_candidate
from .fictional_2027_collection_probe import _ordinary_copy

SCHEMA = "SH_FICTIONAL_2027_DISPOSABLE_COLLECTION_PROBE_V15"
PRINCIPAL = "F27-PROBE-V15-READER"
ENGAGEMENT = "F27-DISPOSABLE-PROBE-V15"
AS_OF = "2027-12-31T23:59:59+00:00"
REVIEWED_PACKAGE = "enterprise/generated/audit-suite/company-source-portfolio-v15-2026-09-30"
REVIEW_SHA256 = "2f2c76af486fb452858ca35b629e6852c3d963b85fe93c6ef76374ccbd2af972"
PORTFOLIO_REPORT_SHA256 = "9147a65b2f16f4244adbd368811e65171a819b8986ba8df5bd66846ee2090459"
CANDIDATE_REPORT_SHA256 = "9f11bb33cef6b6d1d8f5a5e869bddcb42e7196882e4a25b587e506edb45c5054"
CANDIDATE_A_SHA256 = "fd6ed9cb57809628305ed9d8cbd4445e01ae8920092b88f63f7a7c6e58325fb6"
CANDIDATE_B_SHA256 = "994969e98bea3b0fd78d618e89f848308ba573f6768d1ed9cb4d2c7251042e50"
ISOLATED_REVIEW_SHA256 = "9c8b5faa5c6e0938ff86ace7ff1640f3f6c6882d17f790d35e8866d869aff4eb"
REVIEWED_V14_COLLECTOR = "enterprise/generated/audit-suite/company-collection-probe-v14-2026-09-30"
V14_COLLECTOR_REVIEW_SHA256 = "78b25b6848b30890f7431ff1fbed2db719e5742306745e4d153675aeefe1de11"
V14_COLLECTOR_A_SHA256 = "74a6c92a15d4c7c9ad66e20e9eea16041a3106f3362838a572813b301575c43c"
V14_COLLECTOR_B_SHA256 = "a91a998c903742441d0fb3271cbd0ac9da86afd8f27a769af88ac286fa1690c5"
V14_COLLECTOR_REPORT_SHA256 = "70a178b0ac2a3c699864872520cb394667e1fa0b0009d25e131362280802e5e5"
P1_FREEZE = {
    "file_count": 538,
    "inventory_sha256": "f266ef682b502b3b093170f8a7b64fcf5cbab722d5c8ddf6715a63c0e535360f",
}
REC_BASELINE = {"grants": 12, "collections": 22, "access_events": 25}
ZERO_BASELINE = {"grants": 0, "collections": 0, "access_events": 0}
IDENTITY = (
    "company",
    "branch",
    "system",
    "record",
    "version",
    "sha256",
    "event_at",
    "available_at",
    "imported_at",
)


def _source_id(pin: dict) -> str:
    key = pin["source"]
    ledger = pin.get("ledger")
    if key == "rec003" and ledger in ("A", "B"):
        return "scenario-rec003-dq"
    if ledger not in (None, "native", "human", "service"):
        raise CandidateRegistryError("Unknown scenario source ledger")
    return (
        "scenario-"
        + key.replace("_", "-")
        + ("-" + ledger if ledger in ("human", "service") else "")
    )


def _no_sidecars(path: Path) -> None:
    if any(
        Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CandidateRegistryError("Company source has SQLite sidecar")


def _native(path: Path, component: dict) -> tuple[dict, str]:
    """Select one exact, frozen native version and hash the full business rows."""
    before = _private(path)
    _no_sidecars(path)
    with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CandidateRegistryError("Source integrity failed")
        systems = db.execute(
            "SELECT company,branch,system,owner FROM systems ORDER BY company,branch,system"
        ).fetchall()
        versions = db.execute(
            "SELECT company,branch,system,record,version,event_at,available_at,"
            "imported_at,origin,provenance,content,sha256,command_id,input_digest "
            "FROM versions ORDER BY company,branch,system,record,version"
        ).fetchall()
    _no_sidecars(path)
    if _private(path) != before or not versions:
        raise CandidateRegistryError("Frozen native source changed or is empty")
    business = {
        "systems": systems,
        "versions": [
            [*row[:10], hashlib.sha256(row[10]).hexdigest(), *row[11:]] for row in versions
        ],
    }
    digest = hashlib.sha256(
        json.dumps(business, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    selected = next(
        (
            row
            for row in versions
            if row[0] == component["company"]
            and row[1] == component["branch"]
            and row[2] in component["systems"]
            and (
                component["namespace"] != "F27ETH001CONDUCT"
                or (row[2], row[3], row[4]) == ("conduct_reconciliation", "FINAL", 1)
            )
            and (
                component["namespace"] != "F27SEC001TRANSFER"
                or (row[2], row[3], row[4]) == ("exception_register", "FINAL", 1)
            )
            and (
                component["namespace"] != "F27SEC001COMPONENT"
                or (row[2], row[3], row[4]) == ("exception_register", "FINAL", 1)
            )
            and (
                component["namespace"] != "F27POL004PROCEDURE"
                or (row[2], row[3], row[4]) == ("result_register", "FINAL", 1)
            )
            and (
                component["namespace"] != "F27EMERGENCYREPLAY"
                or (row[2], row[3], row[4])
                == (
                    ("exception_register", "EXCEPTION-STATUS", 1)
                    if row[1] == "EMERGENCY-REPLAY-MESSY"
                    else ("replay_review", "REVIEW", 1)
                )
            )
        ),
        None,
    )
    if selected is None or hashlib.sha256(selected[10]).hexdigest() != selected[11]:
        raise CandidateRegistryError("Selected native version missing or damaged")
    ref = dict(zip(IDENTITY, (*selected[:5], selected[11], *selected[5:8]), strict=True))
    if ref["available_at"] > AS_OF:
        raise CandidateRegistryError("Selected source is future to probe clock")
    return ref, digest


def _addressable_pending(path: Path, ref: dict) -> dict:
    """Prove the selected source is a pending case, never an environment decision."""
    if (ref["system"], ref["record"], ref["version"]) != (
        "addressable_candidate",
        "SPEC-01",
        1,
    ):
        raise CandidateRegistryError("Expected exact pending addressable native case")
    with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        row = db.execute(
            "SELECT content,sha256 FROM versions WHERE company=? AND branch=? "
            "AND system=? AND record=? AND version=?",
            (ref["company"], ref["branch"], ref["system"], ref["record"], ref["version"]),
        ).fetchone()
    if row is None or hashlib.sha256(row[0]).hexdigest() != row[1] or row[1] != ref["sha256"]:
        raise CandidateRegistryError("Pending addressable native content differs")
    body = json.loads(row[0])
    if (
        body.get("docket_state") != "PENDING_ENVIRONMENT_AND_QUALIFIED_LEGAL_REVIEW"
        or body.get("entity_role_and_hipaa_applicability") != "UNDETERMINED"
        or body.get("generic_waiver_effect") != "NONE"
        or body.get("source_disposition") != "ENVIRONMENTAL_DECISION_REQUIRED"
        or body.get("related_generic_exception_control_id") != "SH-POL-003"
        or body.get("source_locator") != "164.308(a)(3)(ii)(A)"
        or any(
            body.get(key) is not None
            for key in (
                "actual_ephi_systems",
                "actual_service_environment",
                "reasonableness_analysis",
                "equivalent_alternative_analysis",
                "implemented_safeguard_evidence",
                "approver_id",
                "approval_at",
            )
        )
    ):
        raise CandidateRegistryError("Addressable case asserted an unreviewed decision")
    return {
        "source_locator": body["source_locator"],
        "docket_state": body["docket_state"],
        "actual_hipaa_applicability": "UNDETERMINED",
        "environmental_decision": False,
        "implemented_safeguard": False,
    }


def _eth001_final(path: Path, ref: dict) -> dict:
    """Select only the fictional final reconciliation, retaining the open Messy history."""
    if (ref["system"], ref["record"], ref["version"]) != (
        "conduct_reconciliation",
        "FINAL",
        1,
    ) or ref["branch"] not in v11_portfolio.ETH_BRANCHES:
        raise CandidateRegistryError("Expected exact ETH001 final native version")
    with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        row = db.execute(
            "SELECT content,sha256 FROM versions WHERE company=? AND branch=? "
            "AND system=? AND record=? AND version=?",
            (ref["company"], ref["branch"], ref["system"], ref["record"], ref["version"]),
        ).fetchone()
    if row is None or hashlib.sha256(row[0]).hexdigest() != row[1] or row[1] != ref["sha256"]:
        raise CandidateRegistryError("ETH001 final native content differs")
    body = json.loads(row[0])
    messy = ref["branch"] == "ETH001-MESSY"
    if (
        body.get("control_id") != "SH-ETH-001"
        or body.get("qualification") != "FUTURE_FICTIONAL_SELECTED_CONDUCT_EXERCISE_ONLY"
        or body.get("canon_reconciliation")
        != "2026_ENTERPRISE_CODE_FUTURE_OPEN;_2027_LOCAL_APPROVAL_FICTIONAL_ONLY"
        or body.get("scenario") != ("MESSY" if messy else "CLEAN")
        or body.get("final_state")
        != (
            "SELECTED_COMPLETE_WITH_LATE_ACK_AND_OPEN_EXCEPTION"
            if messy
            else "SELECTED_TWO_ON_TIME_NO_LOCAL_EXCEPTION"
        )
        or body.get("selected_acknowledgment_count") != 2
        or body.get("selected_late_count") != int(messy)
        or body.get("open_exception_ids") != (["LOCAL-ETH001-FALSE-CLEAN-EXC-001"] if messy else [])
        or body.get("historical_false_clean_erased") is not False
        or body.get("real_enterprise_code_approved") is not False
        or body.get("workforce_population_complete") is not False
        or body.get("actual_employee_action_or_signature") is not False
        or body.get("substantiated_case_evidence_present") is not False
        or body.get("sanctions_or_performance_review_conclusion") is not False
        or body.get("audit_task_credit") is not False
        or body.get("fictional_approval_original", {}).get("record") != "FICTIONAL-LOCAL-APPROVAL"
        or body.get("fictional_approval_original", {}).get("branch") != ref["branch"]
        or len(body.get("selected_acknowledgment_originals", [])) != 2
    ):
        raise CandidateRegistryError("ETH001 final asserted unreviewed operation or closure")
    return {
        "final_state": body["final_state"],
        "selected_acknowledgment_count": 2,
        "selected_late_count": int(messy),
        "open_exception_ids": body["open_exception_ids"],
        "fictional_local_approval_only": True,
        "real_enterprise_code_approved": False,
        "workforce_population_complete": False,
        "actual_employee_action_or_signature": False,
        "sanctions_or_performance_review_conclusion": False,
        "audit_task_credit": False,
    }


def _sec001_final(path: Path, ref: dict) -> dict:
    """Check the selected synthetic transfer closeout without crediting CC6.7."""
    if (ref["system"], ref["record"], ref["version"]) != (
        "exception_register",
        "FINAL",
        1,
    ) or ref["branch"] not in v12_portfolio.SEC_BRANCHES:
        raise CandidateRegistryError("Expected exact SEC001 final native version")
    with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        row = db.execute(
            "SELECT content,sha256 FROM versions WHERE company=? AND branch=? "
            "AND system=? AND record=? AND version=?",
            (ref["company"], ref["branch"], ref["system"], ref["record"], ref["version"]),
        ).fetchone()
    if row is None or hashlib.sha256(row[0]).hexdigest() != row[1] or row[1] != ref["sha256"]:
        raise CandidateRegistryError("SEC001 final native content differs")
    body = json.loads(row[0])
    detail = body.get("detail", {})
    messy = ref["branch"] == "SEC001-XFER-MESSY"
    exception = "SIM-SEC001-FALSE-CLOSE-EXC-001"
    if (
        body.get("control_id") != "SH-SEC-001"
        or body.get("selected_task_id") != "TASK-SH-SEC-001-corporate-CHECK-SOC2:CC6.7"
        or body.get("scenario") != ("MESSY" if messy else "CLEAN")
        or body.get("record_id") != "FINAL"
        or body.get("qualification") != "AUTHORED_FUTURE_SELECTED_EXERCISE_NOT_REAL_OPERATION"
        or body.get("actor_authority") != "CANON_LISTED_FICTIONAL_APPOINTMENT_PENDING_ACCEPTANCE"
        or body.get("source_complete") is not False
        or body.get("audit_task_credit") is not False
        or detail.get("scope") != "ONE_SELECTED_FUTURE_FICTIONAL_SYNTHETIC_NON_PHI_TRANSFER"
        or detail.get("real_network_bytes") != 0
        or detail.get("actual_customer_or_phi_data") is not False
        or detail.get("deployed_channel_or_endpoint") is not False
        or detail.get("approved_enterprise_transfer_standard") is not False
        or detail.get("selected_fixture_reconciled") is not True
        or detail.get("exception_open") is not messy
        or detail.get("open_exception_ids") != ([exception] if messy else [])
        or detail.get("authored_clause_satisfied") is not False
        or ("CORRECTION" in body.get("record_links", {})) is not messy
    ):
        raise CandidateRegistryError("SEC001 final asserted unreviewed transfer or closure")
    return {
        "selected_fixture_reconciled": True,
        "open_exception_ids": detail["open_exception_ids"],
        "actual_network_transfer": False,
        "actual_customer_or_phi_data": False,
        "deployed_channel_or_endpoint": False,
        "approved_enterprise_transfer_standard": False,
        "authored_clause_satisfied": False,
        "audit_task_credit": False,
    }


def _sec001_component_final(path: Path, ref: dict) -> dict:
    """Qualify the selected CC5.2 reconciliation without closing its route."""
    if (ref["system"], ref["record"], ref["version"]) != (
        "exception_register",
        "FINAL",
        1,
    ) or ref["branch"] not in v13_portfolio.COMPONENT_BRANCHES:
        raise CandidateRegistryError("Expected exact CC5.2 component final native version")
    with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        row = db.execute(
            "SELECT content,sha256 FROM versions WHERE company=? AND branch=? "
            "AND system=? AND record=? AND version=?",
            (ref["company"], ref["branch"], ref["system"], ref["record"], ref["version"]),
        ).fetchone()
    if row is None or hashlib.sha256(row[0]).hexdigest() != row[1] or row[1] != ref["sha256"]:
        raise CandidateRegistryError("CC5.2 component final native content differs")
    body = json.loads(row[0])
    detail = body.get("detail", {})
    messy = ref["branch"] == "SEC001-COMPONENT-MESSY"
    exception = "SIM-SEC001-COMPONENT-FALSE-CLOSE-EXC-001"
    expected_link = "FALSE-CLOSE-CORRECTION" if messy else "REVIEW"
    if (
        body.get("control_id") != "SH-SEC-001"
        or body.get("selected_task_id") != "TASK-SH-SEC-001-corporate-CHECK-SOC2:CC5.2"
        or body.get("scenario") != ("MESSY" if messy else "CLEAN")
        or body.get("record_id") != "FINAL"
        or body.get("qualification") != "AUTHORED_FUTURE_SELECTED_EXERCISE_NOT_REAL_OPERATION"
        or body.get("actor_authority") != "CANON_LISTED_FICTIONAL_APPOINTMENT_PENDING_ACCEPTANCE"
        or body.get("source_complete") is not False
        or body.get("audit_task_credit") is not False
        or detail.get("scope") != "TWO_SELECTED_FUTURE_FICTIONAL_NON_DEPLOYED_COMPONENT_FIXTURES"
        or detail.get("selected_fixture_reconciled") is not True
        or detail.get("exception_open") is not messy
        or detail.get("open_exception_ids") != ([exception] if messy else [])
        or detail.get("outsourced_candidate_blocked") is not True
        or any(
            detail.get(key) is not False
            for key in (
                "actual_deployed_component",
                "actual_supplier_selected_or_contracted",
                "full_technology_population",
                "authored_clause_satisfied",
            )
        )
        or body.get("previous_original") != body.get("record_links", {}).get(expected_link)
        or ("USE-BLOCK" in body.get("record_links", {})) is not messy
    ):
        raise CandidateRegistryError(
            "CC5.2 component final asserted unreviewed closure or deployment"
        )
    return {
        "selected_fixture_reconciled": True,
        "open_exception_ids": detail["open_exception_ids"],
        "outsourced_candidate_blocked": True,
        "actual_deployed_component": False,
        "actual_supplier_selected_or_contracted": False,
        "full_technology_population": False,
        "authored_clause_satisfied": False,
        "audit_task_credit": False,
    }


def _pol004_final(path: Path, ref: dict) -> dict:
    """Keep one pending fictional trial and its adverse history visible."""
    if (ref["system"], ref["record"], ref["version"]) != ("result_register", "FINAL", 1) or ref[
        "branch"
    ] not in v14_portfolio.PROCEDURE_BRANCHES:
        raise CandidateRegistryError("Expected exact POL004 final native version")
    with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        row = db.execute(
            "SELECT content,sha256 FROM versions WHERE company=? AND branch=? "
            "AND system=? AND record=? AND version=?",
            (ref["company"], ref["branch"], ref["system"], ref["record"], ref["version"]),
        ).fetchone()
    if row is None or hashlib.sha256(row[0]).hexdigest() != row[1] or row[1] != ref["sha256"]:
        raise CandidateRegistryError("POL004 final native content differs")
    body = json.loads(row[0])
    detail = body.get("detail", {})
    messy = ref["branch"] == "POL004-PROCEDURE-MESSY"
    if (
        body.get("schema") != v14_portfolio.procedure.SCHEMA
        or body.get("control_id") != "SH-POL-004"
        or body.get("selected_task_id") != v14_portfolio.procedure.TASK
        or body.get("record_id") != "FINAL"
        or body.get("scenario") != ("MESSY" if messy else "CLEAN")
        or body.get("actor_id") != "AS-P005"
        or body.get("actor_authority") != "CANON_LISTED_FICTIONAL_APPOINTMENT_PENDING_ACCEPTANCE"
        or body.get("source_complete") is not False
        or body.get("audit_task_credit") is not False
        or detail.get("selected_local_trial_only") is not True
        or detail.get("enterprise_policy_status_2026") != "OPEN"
        or detail.get("document_standard_status") != "APPROVED_DESIGN_STANDARD_ONLY"
        or detail.get("procedure_approval") != "PENDING_AUTHORIZED_DECISION"
        or detail.get("effective_enterprise_procedure") is not False
        or detail.get("actual_operation") is not False
        or detail.get("authored_clause_satisfied") is not False
        or detail.get("exception_open") is not messy
        or detail.get("selected_result")
        != (
            "CORRECTED_FALSE_CLOSE_HISTORICAL_GAP_OPEN"
            if messy
            else "NO_SELECTED_VARIATION_PENDING_PROCEDURE_APPROVAL"
        )
        or (body.get("prior_false_close") is not None) is not messy
        or (body.get("prior_correction") is not None) is not messy
        or ("EXPIRY-ESCALATE" in body.get("source_originals", {})) is not messy
        or ("LATE-RECONCILE" in body.get("source_originals", {})) is not messy
    ):
        raise CandidateRegistryError("POL004 final asserted unreviewed closure or authority")
    return {
        "selected_result": detail["selected_result"],
        "enterprise_policy_status_2026": "OPEN",
        "procedure_approval": "PENDING_AUTHORIZED_DECISION",
        "messy_exception_open": messy,
        "prior_false_close_retained": messy,
        "prior_correction_retained": messy,
        "actual_operation": False,
        "authored_clause_satisfied": False,
        "audit_task_credit": False,
    }


def _emergency_final(path: Path, ref: dict) -> dict:
    """Bound one selected marker and retain the Messy open-gate disposition."""
    messy = ref["branch"] == "EMERGENCY-REPLAY-MESSY"
    expected = (
        ("exception_register", "EXCEPTION-STATUS", 1) if messy else ("replay_review", "REVIEW", 1)
    )
    if (
        ref["branch"] not in v15_portfolio.REPLAY_BRANCHES
        or (ref["system"], ref["record"], ref["version"]) != expected
    ):
        raise CandidateRegistryError("Expected exact emergency replay terminal native version")
    with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        row = db.execute(
            "SELECT content,sha256 FROM versions WHERE company=? AND branch=? "
            "AND system=? AND record=? AND version=?",
            (ref["company"], ref["branch"], ref["system"], ref["record"], ref["version"]),
        ).fetchone()
    if row is None or hashlib.sha256(row[0]).hexdigest() != row[1] or row[1] != ref["sha256"]:
        raise CandidateRegistryError("Emergency replay terminal native content differs")
    body = json.loads(row[0])
    open_gates = {
        "bcm_capacity_bia": "OPEN",
        "iam_coverage": "OPEN",
        "phi_ba_flowdown": "OPEN",
        "sec005_telemetry": "OPEN",
    }
    if (
        body.get("schema") != v15_portfolio.replay.SCHEMA + "_NATIVE_EVENT"
        or body.get("branch") != ref["branch"]
        or body.get("actor_id") != "AS-P005"
        or body.get("truth_class") != "TRAINING_SCENARIO_ONLY"
        or body.get("service_id") != "SIM-RESTRICTED-HOSTING-01"
        or body.get("site") != "BOISE"
        or body.get("marker_id") != "SIM-EPHI-RECOVERY-MARKER-01"
        or body.get("marker_sha256")
        != "fb5a872ccff0e97081593ba6338b2bbb40556168999a253dc9d0df402638870a"
        or body.get("selected_population_count") != 1
        or body.get("actual_phi_processing") is not False
        or body.get("outbound_bytes") != 0
        or body.get("outbound_packets") != 0
        or body.get("observed_checkpoint_sha256") is not None
        or body.get("action")
        != ("RETAIN_HISTORICAL_GAP_AND_UPSTREAM_HOLDS" if messy else "REVIEW_SELECTED_LOCAL_RESULT")
        or body.get("decision") != ("OPEN" if messy else "LOCAL_TRACE_ONLY")
        or body.get("upstream_exception_status") != (open_gates if messy else {})
        or body.get("previous_native_content", {}).get("record") != ("REVIEW" if messy else "RECON")
    ):
        raise CandidateRegistryError("Emergency replay asserted closure or operation")
    return {
        "selected_terminal": ref["record"],
        "selected_population_count": 1,
        "payload_free": True,
        "actual_phi_processing": False,
        "deployed_recovery_proven": False,
        "messy_local_exception_open": messy,
        "messy_upstream_gates_open": messy,
        "audit_task_credit": False,
    }


def _component_rows(profile: dict) -> list[tuple[str, dict, dict]]:
    """Preserve 36 V14 scenario components, then add emergency replay."""
    pins = profile["source_pins"]
    components = profile["manifest"]["components"]
    names = [_source_id(pin) for pin in pins]
    if len(pins) != 37 or len(set(names)) != 37 or len(components) != 50:
        raise CandidateRegistryError("Expected exact 37 scenario components")
    if {name for name in components if name.startswith("scenario-")} != set(names):
        raise CandidateRegistryError("Scenario source component roster differs")
    name = "scenario-emergencyreplay"
    if names[-1] != name or names.count(name) != 1:
        raise CandidateRegistryError("One emergency replay source required per profile")
    old = prior_probe._component_rows(
        {
            "source_pins": pins[:-1],
            "manifest": {
                "components": {key: value for key, value in components.items() if key != name}
            },
        }
    )
    pin = pins[-1]
    component = components[name]
    if (
        pin.get("source_review_sha256") != v15_portfolio.REPLAY_REVIEW_SHA
        or pin.get("database_sha256") != v15_portfolio.REPLAY_DB_SHA
        or pin.get("receipt_sha256") != v15_portfolio.REPLAY_RECEIPT_SHA
        or pin.get("manifest_sha256") != v15_portfolio.REPLAY_MANIFEST_SHA
        or pin.get("physical_branch") not in v15_portfolio.REPLAY_BRANCHES
        or pin.get("system_count") != v15_portfolio.REPLAY_SYSTEMS
        or pin.get("inherited_audit_journals") != ZERO_BASELINE
        or component.get("company") != "SABLE-HARBOR-REFERENCE"
        or component.get("branch") != pin["physical_branch"]
        or component.get("namespace") != "F27EMERGENCYREPLAY"
        or component.get("systems")
        != [
            "exception_register",
            "replay_authority",
            "replay_decision",
            "replay_plan",
            "replay_reconciliation",
            "replay_request",
            "replay_result",
            "replay_review",
            "replay_scope",
        ]
    ):
        raise CandidateRegistryError("Reviewed emergency replay source route differs")
    return [*old, (name, pin, component)]


def _no_shared_extents(path: Path) -> None:
    result = subprocess.run(
        ["filefrag", "-v", str(path)], capture_output=True, text=True, check=True
    )
    if not any(marker in result.stdout for marker in ("extent found", "extents found")) or any(
        line.lstrip()[:1].isdigit() and "shared" in line for line in result.stdout.splitlines()
    ):
        raise CandidateRegistryError("Disposable copy has shared or uninspectable extents")


def _journal_rows(path: Path) -> dict[str, list[tuple]]:
    _no_sidecars(path)
    with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CandidateRegistryError("Disposable journal database integrity differs")
        rows = {
            "grants": db.execute(
                "SELECT * FROM grants ORDER BY principal,engagement,company,branch,system"
            ).fetchall(),
            "collections": db.execute("SELECT * FROM collections ORDER BY command_id").fetchall(),
            "access_events": db.execute("SELECT * FROM access_events ORDER BY id").fetchall(),
        }
    _no_sidecars(path)
    return rows


def _journal_baseline(path: Path, source_id: str) -> tuple[dict, dict, str]:
    rows = _journal_rows(path)
    counts = {name: len(value) for name, value in rows.items()}
    expected = REC_BASELINE if source_id == "scenario-rec003-dq" else ZERO_BASELINE
    if counts != expected:
        raise CandidateRegistryError("Reviewed inherited journal baseline differs")
    if any(
        row[0] == PRINCIPAL and row[1] == ENGAGEMENT
        for row in rows["grants"] + rows["access_events"]
    ):
        raise CandidateRegistryError("Probe principal already present in historical access")
    if any(
        (receipt := json.loads(row[2])).get("principal_id") == PRINCIPAL
        and receipt.get("engagement_id") == ENGAGEMENT
        for row in rows["collections"]
    ):
        raise CandidateRegistryError("Probe principal already present in historical collection")
    digest = hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return rows, counts, digest


def _journal(path: Path, ref: dict, baseline: dict[str, list[tuple]]) -> dict:
    rows = _journal_rows(path)
    historical = {
        "grants": [r for r in rows["grants"] if (r[0], r[1]) != (PRINCIPAL, ENGAGEMENT)],
        "access_events": [
            r for r in rows["access_events"] if (r[1], r[2]) != (PRINCIPAL, ENGAGEMENT)
        ],
        "collections": [
            r
            for r in rows["collections"]
            if ((v := json.loads(r[2])).get("principal_id"), v.get("engagement_id"))
            != (PRINCIPAL, ENGAGEMENT)
        ],
    }
    if historical != baseline:
        raise CandidateRegistryError("Inherited historical journals changed in disposable copy")
    counts = {name: len(value) for name, value in rows.items()}
    if counts != {name: len(value) + 1 for name, value in baseline.items()}:
        raise CandidateRegistryError("Disposable access journal delta differs")
    grants = [r for r in rows["grants"] if (r[0], r[1]) == (PRINCIPAL, ENGAGEMENT)]
    events = [r for r in rows["access_events"] if (r[1], r[2]) == (PRINCIPAL, ENGAGEMENT)]
    receipts = [
        json.loads(r[2])
        for r in rows["collections"]
        if ((v := json.loads(r[2])).get("principal_id"), v.get("engagement_id"))
        == (PRINCIPAL, ENGAGEMENT)
    ]
    expected = (PRINCIPAL, ENGAGEMENT, ref["company"], ref["branch"], ref["system"], 1)
    if (
        grants != [expected]
        or len(events) != 1
        or events[0][1:7] != expected
        or len(receipts) != 1
        or any(receipts[0]["source"][key] != ref[key] for key in IDENTITY)
    ):
        raise CandidateRegistryError("Disposable journal lacks exact scoped collection")
    return {
        "inherited_counts": {name: len(value) for name, value in baseline.items()},
        "post_counts": counts,
        "new_scoped_receipt_sha256": hashlib.sha256(
            json.dumps(receipts[0], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    path.chmod(0o600)


def _reviewed_v15(repository: Path, private_repository: Path) -> None:
    """Require the independently reviewed main-local V15 portfolio/candidate bytes."""
    base = private_repository / REVIEWED_PACKAGE
    review_path = base / "independent-review-main-v1/REVIEW.json"
    portfolio_path = base / "main-report-v1/REPORT.json"
    candidate_root = base / "main-candidate-v1"
    candidate_path = candidate_root / "REPORT.json"
    candidate_a = candidate_root / "A.json"
    candidate_b = candidate_root / "B.json"
    if (
        _private(review_path)[-1] != REVIEW_SHA256
        or _private(portfolio_path)[-1] != PORTFOLIO_REPORT_SHA256
        or _private(candidate_path)[-1] != CANDIDATE_REPORT_SHA256
        or _private(candidate_a)[-1] != CANDIDATE_A_SHA256
        or _private(candidate_b)[-1] != CANDIDATE_B_SHA256
    ):
        raise CandidateRegistryError("Independently reviewed V15 package hash differs")
    review = _json(review_path)
    if (
        review.get("verdict") != "PASS_MAIN_PARTIAL_CANDIDATE_NO_AUDIT_CREDIT"
        or review.get("output_sha256")
        != {
            "main-report-v1/REPORT.json": PORTFOLIO_REPORT_SHA256,
            "main-candidate-v1/A.json": CANDIDATE_A_SHA256,
            "main-candidate-v1/B.json": CANDIDATE_B_SHA256,
            "main-candidate-v1/REPORT.json": CANDIDATE_REPORT_SHA256,
        }
        or review.get("isolated_review_sha256") != ISOLATED_REVIEW_SHA256
        or review.get("integrated_commit") != "26e463e7"
        or review.get("source_complete") is not False
        or review.get("fresh_audit_pair_created") is not False
        or review.get("audit_task_credit") is not False
    ):
        raise CandidateRegistryError("Independently reviewed V15 verdict differs")
    verify_candidate(candidate_root, repository, private_repository)


def _reviewed_v14_collector(repository: Path, private_repository: Path) -> dict:
    """Pin and reverify the whole previously reviewed disposable collector run."""
    base = private_repository / REVIEWED_V14_COLLECTOR
    review_path = base / "independent-review-main-v1/REVIEW.json"
    run_root = base / "main-run-v1"
    paths = {
        "review": review_path,
        "A.json": run_root / "A.json",
        "B.json": run_root / "B.json",
        "REPORT.json": run_root / "REPORT.json",
    }
    expected = {
        "review": V14_COLLECTOR_REVIEW_SHA256,
        "A.json": V14_COLLECTOR_A_SHA256,
        "B.json": V14_COLLECTOR_B_SHA256,
        "REPORT.json": V14_COLLECTOR_REPORT_SHA256,
    }
    before = {name: _private(path) for name, path in paths.items()}
    if any(before[name][-1] != digest for name, digest in expected.items()):
        raise CandidateRegistryError("Independently reviewed V14 collector byte pin differs")
    review = _json(review_path)
    if (
        review.get("verdict") != "PASS_MAIN_DISPOSABLE_BOUNDARY_NO_AUDIT_CREDIT"
        or review.get("output_sha256")
        != {name: expected[name] for name in ("A.json", "B.json", "REPORT.json")}
        or review.get("p1_freeze") != P1_FREEZE
        or review.get("integrated_commit") != "b20ddfdd"
        or review.get("isolated_review_sha256")
        != "0782b1cf31998ec235a0964adee436f7f26a8fbc918275f700413ca55d58f34d"
        or review.get("source_complete") is not False
        or review.get("fresh_audit_pair_created") is not False
        or review.get("audit_task_credit") is not False
    ):
        raise CandidateRegistryError("Independently reviewed V14 collector verdict differs")
    report = prior_probe.verify(run_root, repository, private_repository)
    if report != _json(paths["REPORT.json"]) or any(
        _private(path) != before[name] for name, path in paths.items()
    ):
        raise CandidateRegistryError("Reviewed V14 collector changed during verification")
    return report


def _semantic_prefix_keys() -> tuple[str, ...]:
    """Fields independent of disposable path, journal write time and copy bytes."""
    return (
        "source_store_id",
        "alias",
        "source_database_sha256",
        "native_business_sha256",
        "native_identity",
        "pregrant_invisible_and_read_denied",
        "scoped_grant_and_discovery_verified",
        "original_read_sha256_verified",
        "retained_collection_verified",
        "inherited_journal_counts",
        "inherited_journal_sha256",
        "addressable_pending_case",
        "eth001_selected_case",
        "sec001_selected_case",
        "cc52_selected_case",
        "pol004_selected_case",
    )


def run(repository: Path, private_repository: Path, destination: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise CandidateRegistryError("Fresh disposable V15 probe destination required")
    _private(destination.parent, directory=True)
    freeze = _p1_inventory(private_repository)
    if freeze != P1_FREEZE:
        raise CandidateRegistryError("Frozen active P1 inventory differs")
    _reviewed_v15(repository, private_repository)
    previous_collector = _reviewed_v14_collector(repository, private_repository)
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    if (
        diagnostic["source_count"],
        diagnostic["native_versions"],
        diagnostic["source_complete"],
    ) != (36, 819, False) or diagnostic["sources"][:35] != previous_collector["reviewed_sources"]:
        raise CandidateRegistryError(
            "Reviewed V15 source qualification or V14 collector prefix differs"
        )
    destination.mkdir(mode=0o700)
    originals: dict[Path, tuple] = {}
    sides = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        profile = profiles[side]
        manifest = json.loads(json.dumps(profile["manifest"]))
        side_root = destination / side
        side_root.mkdir(mode=0o700)
        frozen = []
        for source_id, component in profile["manifest"]["components"].items():
            if source_id.startswith("scenario-"):
                continue
            origin = Path(component["root"]) / "company.sqlite3"
            before = _private(origin)
            _no_sidecars(origin)
            originals[origin] = before
            target = side_root / source_id / "company.sqlite3"
            _ordinary_copy(origin, target)
            _no_shared_extents(target)
            manifest["components"][source_id]["root"] = str(target.parent)
            frozen.append((source_id, origin, target, before[-1]))
        if len(frozen) != 13:
            raise CandidateRegistryError("Frozen 13-component baseline differs")
        selected = []
        for source_id, pin, component in _component_rows(profile):
            origin = Path(component["root"]) / "company.sqlite3"
            original = _private(origin)
            if original[-1] != pin["database_sha256"]:
                raise CandidateRegistryError("Pinned original database hash differs")
            _no_sidecars(origin)
            originals[origin] = original
            ref, business = _native(origin, component)
            pending = (
                _addressable_pending(origin, ref)
                if source_id == "scenario-addressabledocket"
                else None
            )
            eth001 = _eth001_final(origin, ref) if source_id == "scenario-eth001conduct" else None
            sec001 = _sec001_final(origin, ref) if source_id == "scenario-sec001transfer" else None
            cc52 = (
                _sec001_component_final(origin, ref)
                if source_id == "scenario-sec001component"
                else None
            )
            pol004 = _pol004_final(origin, ref) if source_id == "scenario-pol004procedure" else None
            emergency = (
                _emergency_final(origin, ref) if source_id == "scenario-emergencyreplay" else None
            )
            baseline, baseline_counts, baseline_digest = _journal_baseline(origin, source_id)
            if source_id == "scenario-rec003-dq":
                if (
                    pin.get("root_locator") != "snapshot://" + side
                    or pin.get("inherited_audit_journals") != REC_BASELINE
                ):
                    raise CandidateRegistryError("REC003 portable route/journal pin differs")
            elif pin.get("inherited_audit_journals", ZERO_BASELINE) != ZERO_BASELINE:
                raise CandidateRegistryError("Unexpected inherited access in V15 source pin")
            if (ref["company"], ref["branch"]) != (pin["physical_company"], pin["physical_branch"]):
                raise CandidateRegistryError("Selected original physical route differs")
            target = side_root / source_id / "company.sqlite3"
            _ordinary_copy(origin, target)
            _no_shared_extents(target)
            if _journal_rows(target) != baseline:
                raise CandidateRegistryError("Disposable copy changed inherited journals")
            manifest["components"][source_id]["root"] = str(target.parent)
            selected.append(
                (
                    source_id,
                    target,
                    component,
                    ref,
                    business,
                    original[-1],
                    baseline,
                    baseline_counts,
                    baseline_digest,
                    pending,
                    eth001,
                    sec001,
                    cc52,
                    pol004,
                    emergency,
                )
            )
        registry_path = destination / f"{side}.json"
        _write_json(registry_path, manifest)
        federated = FederatedCompanyStore(registry_path, profile["profile_id"])
        rows = []
        for (
            source_id,
            target,
            component,
            ref,
            business,
            original_sha,
            baseline,
            baseline_counts,
            baseline_digest,
            pending,
            eth001,
            sec001,
            cc52,
            pol004,
            emergency,
        ) in selected:
            alias = component["namespace"] + ":" + ref["system"]
            before = federated.list_systems(
                PRINCIPAL, ENGAGEMENT, "SABLEHARBOR", profile["profile_id"]
            )
            if alias in {row["system"] for row in before["systems"]}:
                raise CandidateRegistryError("Source visible before scoped grant")
            try:
                federated.read_version(
                    PRINCIPAL,
                    ENGAGEMENT,
                    "SABLEHARBOR",
                    profile["profile_id"],
                    alias,
                    ref["record"],
                    version=ref["version"],
                    as_of=AS_OF,
                )
            except CompanyStoreError:
                pass
            else:
                raise CandidateRegistryError("Original read succeeded before grant")
            CompanyStore(target.parent).grant(
                PRINCIPAL, ENGAGEMENT, ref["company"], ref["branch"], ref["system"]
            )
            discovered = federated.list_systems(
                PRINCIPAL, ENGAGEMENT, "SABLEHARBOR", profile["profile_id"]
            )
            if alias not in {row["system"] for row in discovered["systems"]}:
                raise CandidateRegistryError("Granted source system undiscoverable")
            records = federated.list_records(
                PRINCIPAL,
                ENGAGEMENT,
                "SABLEHARBOR",
                profile["profile_id"],
                alias,
                as_of=ref["available_at"],
            )
            if not any(
                all(row[key] == ref[key] for key in ("record", "version", "sha256"))
                for row in records["records"]
            ):
                raise CandidateRegistryError("Exact native record undiscoverable")
            read = federated.read_version(
                PRINCIPAL,
                ENGAGEMENT,
                "SABLEHARBOR",
                profile["profile_id"],
                alias,
                ref["record"],
                version=ref["version"],
                as_of=AS_OF,
            )
            if (
                read["source_store_id"] != source_id
                or hashlib.sha256(read["content"]).hexdigest() != ref["sha256"]
                or any(read[key] != ref[key] for key in IDENTITY)
            ):
                raise CandidateRegistryError("Federated original read differs")
            collection = federated.collect(
                PRINCIPAL,
                ENGAGEMENT,
                "SABLEHARBOR",
                profile["profile_id"],
                alias,
                ref["record"],
                version=ref["version"],
                as_of=AS_OF,
                command_id=f"PROBE-V15-{side}-{source_id.upper()}",
            )
            if any(collection["source"][key] != ref[key] for key in IDENTITY):
                raise CandidateRegistryError("Retained collection differs from native source")
            journal = _journal(target, ref, baseline)
            if _native(target, component)[1] != business:
                raise CandidateRegistryError("Disposable native business rows changed")
            result_row = {
                "source_store_id": source_id,
                "alias": alias,
                "source_database_sha256": original_sha,
                "disposable_database_sha256": _sha(target),
                "native_business_sha256": business,
                "native_identity": ref,
                "pregrant_invisible_and_read_denied": True,
                "scoped_grant_and_discovery_verified": True,
                "original_read_sha256_verified": True,
                "retained_collection_verified": True,
                "inherited_journal_counts": baseline_counts,
                "inherited_journal_sha256": baseline_digest,
                "disposable_journal_delta": journal,
            }
            if pending is not None:
                result_row["addressable_pending_case"] = pending
            if eth001 is not None:
                result_row["eth001_selected_case"] = eth001
            if sec001 is not None:
                result_row["sec001_selected_case"] = sec001
            if cc52 is not None:
                result_row["cc52_selected_case"] = cc52
            if pol004 is not None:
                result_row["pol004_selected_case"] = pol004
            if emergency is not None:
                result_row["emergency_selected_case"] = emergency
            rows.append(result_row)
        frozen_rows = []
        for source_id, origin, target, before_sha in frozen:
            if _sha(origin) != before_sha or _sha(target) != before_sha:
                raise CandidateRegistryError("Frozen component changed during disposable probe")
            frozen_rows.append(
                {
                    "source_store_id": source_id,
                    "original_database_sha256": before_sha,
                    "disposable_database_sha256": before_sha,
                    "no_grant_or_collection_added": True,
                }
            )
        old_rows = previous_collector["sides"][side]["collections"]
        prefix_keys = _semantic_prefix_keys()
        if (
            len(rows) != 37
            or len(old_rows) != 36
            or any(
                any(new.get(key) != old.get(key) for key in prefix_keys)
                for new, old in zip(rows[:36], old_rows, strict=True)
            )
            or frozen_rows != previous_collector["sides"][side]["frozen_copies"]
        ):
            raise CandidateRegistryError("Exact reviewed V14 collector semantic prefix differs")
        sides[side] = {
            "scenario": scenario,
            "profile_id": profile["profile_id"],
            "registry_sha256": _sha(registry_path),
            "source_component_count": len(rows),
            "frozen_component_count": len(frozen_rows),
            "frozen_copies": frozen_rows,
            "collections": rows,
        }
    if any(_private(path) != state for path, state in originals.items()):
        raise CandidateRegistryError("Reviewed original source changed during probe")
    later, _ = candidate_profiles(repository, private_repository)
    if later["sources"] != diagnostic["sources"]:
        raise CandidateRegistryError("Reviewed portfolio changed during probe")
    _reviewed_v15(repository, private_repository)
    if _p1_inventory(private_repository) != freeze:
        raise CandidateRegistryError("Active P1 inventory changed during disposable probe")
    report = {
        "schema": SCHEMA,
        "status": "PASS_DISPOSABLE_SOURCE_TO_COLLECTOR_BOUNDARY_ONLY",
        "probe_module_sha256": _sha(Path(__file__)),
        "reviewed_portfolio_verifier_sha256": diagnostic["verifier_module_sha256"],
        "reviewed_v15_review_sha256": REVIEW_SHA256,
        "reviewed_v15_portfolio_report_sha256": PORTFOLIO_REPORT_SHA256,
        "reviewed_v15_candidate_report_sha256": CANDIDATE_REPORT_SHA256,
        "reviewed_v14_collector_review_sha256": V14_COLLECTOR_REVIEW_SHA256,
        "reviewed_v14_collector_report_sha256": V14_COLLECTOR_REPORT_SHA256,
        "reviewed_sources": diagnostic["sources"],
        "reviewed_source_count": 36,
        "reviewed_native_version_count": 819,
        "scenario_source_component_count_per_side": 37,
        "frozen_baseline_component_count_per_side": 13,
        "disposable_component_count_per_side": 50,
        "disposable_copy_count": 100,
        "disposable_collection_count": 74,
        "p1_freeze": freeze,
        "sides": sides,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "original_company_sources_unchanged": True,
        "limits": [
            "Grants and collection journals exist only in disposable ordinary-byte copies.",
            "Frozen 13-component baseline routes also use isolated ordinary-byte copies.",
            "REC003 journals (12/22/25) are historical; only one new scoped delta counts.",
            "SEC003 Messy false clean and open historical exception remain in the selected source.",
            "Physical-site Messy false closure, unescorted entry and open exception remain.",
            "LEG001 real legal applicability is undetermined and Messy histories remain open.",
            "Sixty-six authored LEG001 routes per side remain unsupported.",
            "Addressable SPEC-01 is a pending source-locator case per side, not an "
            "actual ePHI environment or safeguard decision.",
            "Messy blanket-waiver history and the SH-POL-003 gap remain OPEN.",
            "ETH001 FINAL is a selected fictional conduct reconciliation per side: "
            "the 2026 enterprise code remains OPEN, and Messy false-clean/late history "
            "and its exception remain visible.",
            "No actual employee attestation, workforce census, sanctions or performance-"
            "review conclusion follows from ETH001.",
            "SEC001 FINAL is one selected synthetic non-PHI transfer reconciliation per "
            "side; the Messy wrong-endpoint block and corrected false close retain an "
            "open historical exception.",
            "No real transmission, customer or PHI payload, deployed endpoint, approved "
            "transfer standard or authored CC6.7 satisfaction follows from SEC001.",
            "CC5.2 FINAL is one selected fictional non-deployed component reconciliation "
            "per side; the outsourced candidate is unnamed and remains blocked.",
            "Messy CC5.2 omitted-component and corrected false close retain an OPEN "
            "historical exception; no full technology population, approved architecture, "
            "deployed component or authored clause satisfaction follows.",
            "POL004 FINAL is one selected fictional two-endpoint procedure trial per side; "
            "the 2026 enterprise policy stays OPEN and procedure approval pending.",
            "Messy POL004 corrected false close, missed interval and expired exception "
            "remain visible; CC5.3 is unsupported and unrun.",
            "Emergency replay selects one payload-free local marker per side, not actual "
            "ePHI processing, deployed recovery or a period population.",
            "Messy emergency fast-path denial, stale result, local exception and upstream "
            "BA/BCM/IAM/SEC005 holds remain visible and open.",
            "One exact native version per component is selected, not a period population.",
            "No PBC, audit engagement, workpaper, task, grade or Key changed.",
            "The partial 36-cohort portfolio does not resolve all discovery routes.",
        ],
    }
    _write_json(destination / "REPORT.json", report)
    return report


def verify(destination: Path, repository: Path, private_repository: Path) -> dict:
    """Read-only verification of sealed probe, clones, journals and source pins."""
    root = Path(destination).absolute()
    _private(root, directory=True)
    if {path.name for path in root.iterdir()} != {"A", "B", "A.json", "B.json", "REPORT.json"}:
        raise CandidateRegistryError("Exact V15 disposable probe layout required")
    for name in ("A.json", "B.json", "REPORT.json"):
        _private(root / name)
    report = _json(root / "REPORT.json")
    freeze = _p1_inventory(private_repository)
    if freeze != P1_FREEZE:
        raise CandidateRegistryError("Frozen active P1 inventory differs")
    _reviewed_v15(repository, private_repository)
    previous_collector = _reviewed_v14_collector(repository, private_repository)
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    if (
        report.get("schema") != SCHEMA
        or report.get("status") != "PASS_DISPOSABLE_SOURCE_TO_COLLECTOR_BOUNDARY_ONLY"
        or report.get("probe_module_sha256") != _sha(Path(__file__))
        or report.get("reviewed_sources") != diagnostic["sources"]
        or diagnostic["sources"][:35] != previous_collector["reviewed_sources"]
        or report.get("reviewed_portfolio_verifier_sha256") != diagnostic["verifier_module_sha256"]
        or report.get("reviewed_v15_review_sha256") != REVIEW_SHA256
        or report.get("reviewed_v15_portfolio_report_sha256") != PORTFOLIO_REPORT_SHA256
        or report.get("reviewed_v15_candidate_report_sha256") != CANDIDATE_REPORT_SHA256
        or report.get("reviewed_v14_collector_review_sha256") != V14_COLLECTOR_REVIEW_SHA256
        or report.get("reviewed_v14_collector_report_sha256") != V14_COLLECTOR_REPORT_SHA256
        or report.get("reviewed_source_count") != 36
        or report.get("reviewed_native_version_count") != 819
        or report.get("scenario_source_component_count_per_side") != 37
        or report.get("frozen_baseline_component_count_per_side") != 13
        or report.get("disposable_component_count_per_side") != 50
        or report.get("disposable_copy_count") != 100
        or report.get("disposable_collection_count") != 74
        or report.get("p1_freeze") != freeze
        or report.get("source_complete") is not False
        or report.get("fresh_audit_pair_created") is not False
        or report.get("audit_task_credit") is not False
        or report.get("original_company_sources_unchanged") is not True
    ):
        raise CandidateRegistryError("V15 probe report qualification differs")
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        profile = profiles[side]
        side_root = root / side
        _private(side_root, directory=True)
        selected = _component_rows(profile)
        if {p.name for p in side_root.iterdir()} != set(profile["manifest"]["components"]):
            raise CandidateRegistryError("Disposable source roster differs")
        manifest = _json(root / f"{side}.json")
        expected_manifest = json.loads(json.dumps(profile["manifest"]))
        frozen_rows = report["sides"][side]["frozen_copies"]
        frozen_components = [
            (name, component)
            for name, component in profile["manifest"]["components"].items()
            if not name.startswith("scenario-")
        ]
        if len(frozen_rows) != 13 or report["sides"][side]["frozen_component_count"] != 13:
            raise CandidateRegistryError("Frozen disposable roster count differs")
        for row, (source_id, component) in zip(frozen_rows, frozen_components, strict=True):
            copy_dir = side_root / source_id
            _private(copy_dir, directory=True)
            if {p.name for p in copy_dir.iterdir()} != {"company.sqlite3"}:
                raise CandidateRegistryError("Frozen disposable directory differs")
            origin = Path(component["root"]) / "company.sqlite3"
            copy = copy_dir / "company.sqlite3"
            original = _private(origin)
            cloned = _private(copy)
            if (
                original[-1] != cloned[-1]
                or row["source_store_id"] != source_id
                or row["original_database_sha256"] != original[-1]
                or row["disposable_database_sha256"] != cloned[-1]
                or row["no_grant_or_collection_added"] is not True
                or original[:2] == cloned[:2]
            ):
                raise CandidateRegistryError("Frozen original or ordinary-byte copy differs")
            _no_shared_extents(copy)
            expected_manifest["components"][source_id]["root"] = str(copy_dir)
        rows = report["sides"][side]["collections"]
        if len(rows) != 37 or report["sides"][side]["scenario"] != scenario:
            raise CandidateRegistryError("Disposable collection count differs")
        for row, (source_id, pin, component) in zip(rows, selected, strict=True):
            copy_dir = side_root / source_id
            _private(copy_dir, directory=True)
            if {p.name for p in copy_dir.iterdir()} != {"company.sqlite3"}:
                raise CandidateRegistryError("Disposable source has unexpected files")
            copy = copy_dir / "company.sqlite3"
            origin = Path(component["root"]) / "company.sqlite3"
            if (
                _private(origin)[-1] != pin["database_sha256"]
                or _sha(copy) != row["disposable_database_sha256"]
            ):
                raise CandidateRegistryError("Original or copied database hash differs")
            if (origin.stat().st_dev, origin.stat().st_ino) == (
                copy.stat().st_dev,
                copy.stat().st_ino,
            ):
                raise CandidateRegistryError("Original and copy share inode")
            _no_shared_extents(copy)
            original_ref, business = _native(origin, component)
            copy_ref, copied_business = _native(copy, component)
            if (
                original_ref != copy_ref
                or business != copied_business
                or business != row["native_business_sha256"]
            ):
                raise CandidateRegistryError("Original and collected business rows differ")
            if (
                row["source_store_id"] != source_id
                or row["source_database_sha256"] != pin["database_sha256"]
                or row["native_identity"] != original_ref
                or row["alias"] != component["namespace"] + ":" + original_ref["system"]
            ):
                raise CandidateRegistryError("Disposable original route differs")
            if source_id == "scenario-addressabledocket":
                if row.get("addressable_pending_case") != _addressable_pending(
                    origin, original_ref
                ):
                    raise CandidateRegistryError("Pending addressable selected case differs")
            elif "addressable_pending_case" in row:
                raise CandidateRegistryError("Non-addressable route has pending-case claim")
            if source_id == "scenario-eth001conduct":
                if row.get("eth001_selected_case") != _eth001_final(origin, original_ref):
                    raise CandidateRegistryError("ETH001 selected final case differs")
            elif "eth001_selected_case" in row:
                raise CandidateRegistryError("Non-ETH001 route has conduct-case claim")
            if source_id == "scenario-sec001transfer":
                if row.get("sec001_selected_case") != _sec001_final(origin, original_ref):
                    raise CandidateRegistryError("SEC001 selected final case differs")
            elif "sec001_selected_case" in row:
                raise CandidateRegistryError("Non-SEC001 route has transfer-case claim")
            if source_id == "scenario-sec001component":
                if row.get("cc52_selected_case") != _sec001_component_final(origin, original_ref):
                    raise CandidateRegistryError("CC5.2 selected final case differs")
            elif "cc52_selected_case" in row:
                raise CandidateRegistryError("Non-CC5.2 route has component-case claim")
            if source_id == "scenario-pol004procedure":
                if row.get("pol004_selected_case") != _pol004_final(origin, original_ref):
                    raise CandidateRegistryError("POL004 selected final case differs")
            elif "pol004_selected_case" in row:
                raise CandidateRegistryError("Non-POL004 route has procedure-case claim")
            if source_id == "scenario-emergencyreplay":
                if row.get("emergency_selected_case") != _emergency_final(origin, original_ref):
                    raise CandidateRegistryError("Emergency selected terminal case differs")
            elif "emergency_selected_case" in row:
                raise CandidateRegistryError("Non-emergency route has replay-case claim")
            baseline, baseline_counts, baseline_digest = _journal_baseline(origin, source_id)
            if (
                any(
                    row[key] is not True
                    for key in (
                        "pregrant_invisible_and_read_denied",
                        "scoped_grant_and_discovery_verified",
                        "original_read_sha256_verified",
                        "retained_collection_verified",
                    )
                )
                or row["inherited_journal_counts"] != baseline_counts
                or row["inherited_journal_sha256"] != baseline_digest
                or _journal(copy, original_ref, baseline) != row["disposable_journal_delta"]
            ):
                raise CandidateRegistryError("Disposable collection proof differs")
            expected_manifest["components"][source_id]["root"] = str(copy_dir)
        if (
            manifest != expected_manifest
            or _sha(root / f"{side}.json") != report["sides"][side]["registry_sha256"]
        ):
            raise CandidateRegistryError("Disposable routing manifest differs")
        FederatedCompanyStore(root / f"{side}.json", profile["profile_id"])
        old_rows = previous_collector["sides"][side]["collections"]
        prefix_keys = _semantic_prefix_keys()
        if (
            report["sides"][side]["frozen_copies"]
            != previous_collector["sides"][side]["frozen_copies"]
            or len(old_rows) != 36
            or any(
                any(new.get(key) != old.get(key) for key in prefix_keys)
                for new, old in zip(rows[:36], old_rows, strict=True)
            )
        ):
            raise CandidateRegistryError("Exact reviewed V14 collector semantic prefix differs")
    _reviewed_v15(repository, private_repository)
    if _p1_inventory(private_repository) != freeze:
        raise CandidateRegistryError("Active P1 inventory changed during verification")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "verify"))
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "run":
        result = run(args.repository, args.private_repository, args.destination)
    else:
        result = verify(args.destination, args.repository, args.private_repository)
    print(
        json.dumps({key: value for key, value in result.items() if key != "sides"}, sort_keys=True)
    )


if __name__ == "__main__":
    main()
