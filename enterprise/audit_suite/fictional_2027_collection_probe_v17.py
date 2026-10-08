"""Disposable source-to-collector probe for the reviewed partial V17 portfolio.

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

from . import fictional_2027_candidate_registry_v17 as v17_candidates
from . import fictional_2027_collection_probe_v16 as prior_probe
from . import fictional_2027_source_portfolio_v11 as v11_portfolio
from . import fictional_2027_source_portfolio_v12 as v12_portfolio
from . import fictional_2027_source_portfolio_v13 as v13_portfolio
from . import fictional_2027_source_portfolio_v14 as v14_portfolio
from . import fictional_2027_source_portfolio_v15 as v15_portfolio
from . import fictional_2027_source_portfolio_v16 as v16_portfolio
from . import fictional_2027_source_portfolio_v17 as v17_portfolio
from .company_federation import FederatedCompanyStore
from .company_store import CompanyStore, CompanyStoreError
from .documentary_283_route_reconciliation_v6 import _p1_inventory
from .fictional_2027_candidate_registry import CandidateRegistryError, _json, _private, _sha
from .fictional_2027_candidate_registry_v17 import candidate_profiles
from .fictional_2027_collection_probe import _ordinary_copy

SCHEMA = "SH_FICTIONAL_2027_DISPOSABLE_COLLECTION_PROBE_V17"
PRINCIPAL = "F27-PROBE-V17-READER"
ENGAGEMENT = "F27-DISPOSABLE-PROBE-V17"
AS_OF = "2027-12-31T23:59:59+00:00"
REVIEWED_PACKAGE = "enterprise/generated/audit-suite/company-source-portfolio-v17-2026-10-01"
REVIEW_SHA256 = "c006878e9ece6251fbfb52333322ad33e3fd7cdaad9a9394649e4865c019f967"
PORTFOLIO_REPORT_SHA256 = "82f8edc2f1f71d27420a073ff39bf7b6661cca1d2926f1d81be780ce068c15b9"
CANDIDATE_REPORT_SHA256 = "c5cbccbbbd8cec184927432836f0568dc76c38c09ad1023f7125f0f6e55bb80f"
CANDIDATE_A_SHA256 = "4e4345719f8b9e1b0fa1123d478c289b9651343b88fc83f0c3f395a6f231bc46"
CANDIDATE_B_SHA256 = "99ec160cce55def5fe981d8175bee6d636e9c0c2e068400e906c9cf5f28579e8"
ISOLATED_REVIEW_SHA256 = "dbb5d06a593de6ef5509e17f23839a98d89477e895a25271cf0e5f65eac46876"
V17_INTEGRATED_COMMIT = "041fe52b"
REVIEWED_V16_COLLECTOR = "enterprise/generated/audit-suite/company-collection-probe-v16-2026-10-01"
V16_COLLECTOR_REVIEW_SHA256 = "f072d518cbbaf9e29272bf246b0a54de0a8afaca52acf0113a1794a38a083fd0"
V16_COLLECTOR_A_SHA256 = "eead875afddb251e1496b71770d4996762217a498ba3ca65494f52691b478752"
V16_COLLECTOR_B_SHA256 = "864bcb1cb417a6d4a87a203b1af6f1c3a65b0b7b5e058b3edea358489a4e634a"
V16_COLLECTOR_REPORT_SHA256 = "8a0721593da055c4ef084c560fcbd4e31132064e45c01957efeade35e91c24e4"
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
            and (
                component["namespace"] != "F27PRDCONCERN"
                or (row[2], row[3], row[4])
                == (
                    ("exception_register", "EXCEPTION-OPEN", 1)
                    if row[1] == "PRD-CONCERN-MESSY"
                    else ("reconciliation", "RECON-01", 1)
                )
            )
            and (
                component["namespace"] != "F27ENG005OPERATING"
                or (row[2], row[3], row[4])
                == (
                    ("exception_register", "EXC-ENG005-EMG-01", 1)
                    if row[1] == "ENG005-OPERATED-MESSY"
                    else ("change_review", "EMG-BLOCKED-REVIEW", 1)
                )
            )
            and (
                component["namespace"] != "F27GOVOVERSIGHT"
                or (row[2], row[3], row[4]) == ("secretariat_reconciliation", "RECON-01", 1)
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


def _prd_concern_final(path: Path, ref: dict) -> dict:
    """Keep the held Clean reconciliation and Messy OPEN historical exception."""
    messy = ref["branch"] == "PRD-CONCERN-MESSY"
    expected = (
        ("exception_register", "EXCEPTION-OPEN", 1) if messy else ("reconciliation", "RECON-01", 1)
    )
    if (
        ref["branch"] not in v16_portfolio.CONCERN_BRANCHES
        or (ref["system"], ref["record"], ref["version"]) != expected
    ):
        raise CandidateRegistryError("Expected exact PRD concern selected native version")
    with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        row = db.execute(
            "SELECT content,sha256 FROM versions WHERE company=? AND branch=? "
            "AND system=? AND record=? AND version=?",
            (ref["company"], ref["branch"], ref["system"], ref["record"], ref["version"]),
        ).fetchone()
    if row is None or hashlib.sha256(row[0]).hexdigest() != row[1] or row[1] != ref["sha256"]:
        raise CandidateRegistryError("PRD concern selected native content differs")
    body = json.loads(row[0])
    if (
        body.get("schema") != v16_portfolio.concern.SCHEMA + "_NATIVE_EVENT"
        or body.get("branch") != ref["branch"]
        or body.get("company") != ref["company"]
        or body.get("truth_class") != "TRAINING_SCENARIO_ONLY"
        or body.get("concern_id") != "SIM-CUSTOMER-CONCERN-01"
        or body.get("claimant_id") != "SIM-UNVERIFIED-CLIENT-OPS-01"
        or body.get("claimant_customer_identity_verified") is not False
        or body.get("service_id") != "SIM-RESTRICTED-HOSTING-01"
        or body.get("change_id") != "SIM-PRD-SUPPORT-ROUTE-CHANGE-01"
        or body.get("actor_id") != "P004"
        or body.get("actor_authority") != "SCENARIO_CONTACT_ONLY_NO_ACCEPTED_EXTERNAL_SIGNATORY"
        or body.get("external_notice_duty") != "UNDETERMINED_PENDING_CUSTOMER_TERMS"
        or body.get("company_outbound_delivery_accepted") is not False
        or body.get("separate_customer_acknowledgment_exists") is not False
        or body.get("fictional_accepted_deliveries") != 0
        or body.get("real_external_messages_sent") != 0
        or body.get("regulated_payload_bytes") != 0
        or body.get("actual_phi_processing") is not False
        or body.get("authored_communication_clause_satisfied") is not False
        or body.get("historical_exception_open") is not messy
        or body.get("action")
        != ("OPEN_HISTORICAL_RECIPIENT_EXCEPTION" if messy else "RECONCILE_SELECTED_CASE")
        or body.get("status") != ("OPEN" if messy else "OPEN_NO_DELIVERY_OR_ACK")
        or body.get("previous_native_content", {}).get("record")
        != ("DISCOVERY-01" if messy else "GATE-01")
        or body.get("selected_internal_recipient_roles")
        != (
            ["CUSTOMER_DELIVERY", "LEGAL", "PRODUCT"]
            if messy
            else ["CUSTOMER_DELIVERY", "LEGAL", "PRODUCT", "SUPPORT_RECOVERY"]
        )
    ):
        raise CandidateRegistryError("PRD concern selected version asserted delivery or closure")
    return {
        "selected_terminal": ref["record"],
        "claimant_customer_identity_verified": False,
        "company_outbound_delivery_accepted": False,
        "separate_customer_acknowledgment_exists": False,
        "external_notice_duty": "UNDETERMINED_PENDING_CUSTOMER_TERMS",
        "historical_exception_open": messy,
        "actual_phi_processing": False,
        "authored_communication_clause_satisfied": False,
        "audit_task_credit": False,
    }


def _selected_body(path: Path, ref: dict) -> dict:
    """Read exact pinned native content from either original or disposable copy."""
    with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        row = db.execute(
            "SELECT content,sha256 FROM versions WHERE company=? AND branch=? "
            "AND system=? AND record=? AND version=?",
            (ref["company"], ref["branch"], ref["system"], ref["record"], ref["version"]),
        ).fetchone()
    if row is None or hashlib.sha256(row[0]).hexdigest() != row[1] or row[1] != ref["sha256"]:
        raise CandidateRegistryError("Selected native original content differs")
    return json.loads(row[0])


def _linked_sha(path: Path, branch: str, system: str, record: str, version: int) -> str:
    with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        row = db.execute(
            "SELECT content,sha256 FROM versions WHERE branch=? AND system=? "
            "AND record=? AND version=?",
            (branch, system, record, version),
        ).fetchone()
    if row is None or hashlib.sha256(row[0]).hexdigest() != row[1]:
        raise CandidateRegistryError("Selected predecessor native original differs")
    return row[1]


def _eng005_operating_final(path: Path, ref: dict) -> dict:
    messy = ref["branch"] == "ENG005-OPERATED-MESSY"
    expected = (
        ("exception_register", "EXC-ENG005-EMG-01", 1)
        if messy
        else ("change_review", "EMG-BLOCKED-REVIEW", 1)
    )
    if (
        ref["branch"] not in v17_portfolio.eng.BRANCHES.values()
        or (ref["system"], ref["record"], ref["version"]) != expected
    ):
        raise CandidateRegistryError("Expected exact ENG005 selected native version")
    body = _selected_body(path, ref)
    prior = body.get("source_previous", {})
    if (
        prior.get("record") != ("EMG-RETROSPECTIVE" if messy else "EMG-AUTHORITY-GATE")
        or prior.get("system") != ("change_review" if messy else "change_approval")
        or prior.get("version") != 1
        or prior.get("sha256")
        != _linked_sha(path, ref["branch"], prior["system"], prior["record"], 1)
        or body.get("company") != ref["company"]
        or body.get("scenario") != ("MESSY" if messy else "CLEAN")
        or body.get("record") != ref["record"]
        or body.get("service_id") != "SVC-compute"
        or body.get("site") != "RUNTIME-BOISE-DR"
        or body.get("change_id") != "CHG-BOI-GATE-2027-02"
        or body.get("qualification")
        != "FICTIONAL_2027_COMPANY_SELECTED_CHANGE_OPERATION_NO_REAL_DEPLOYMENT"
        or body.get("enterprise_policy_approved") is not False
        or body.get("real_deployment") is not False
        or body.get("actual_phi") is not False
        or body.get("external_packets_or_writes") != 0
        or body.get("audit_task_credit") is not False
        or body.get("historical_exercise_is_operating_source") is not False
        or body.get("action")
        != ("OPEN_HISTORICAL_EMERGENCY_BYPASS" if messy else "UNEXECUTED_EMERGENCY_REQUEST_REVIEW")
        or (body.get("status") == "OPEN") is not messy
        or (body.get("closure_authority_evidenced") is False) is not messy
        or (body.get("emergency_authority_established") is False) is messy
    ):
        raise CandidateRegistryError("ENG005 selected version asserted authority or deployment")
    return {
        "selected_terminal": ref["record"],
        "corporate_emergency_authority_status": "NOT_EVIDENCED_OPEN",
        "messy_emergency_exception_open": messy,
        "messy_ordinary_exception_open": messy,
        "real_deployment": False,
        "actual_phi": False,
        "audit_task_credit": False,
    }


def _gov_oversight_final(path: Path, ref: dict) -> dict:
    messy = ref["branch"] == "GOV-OVERSIGHT-MESSY"
    if ref["branch"] not in v17_portfolio.gov.BRANCHES.values() or (
        ref["system"],
        ref["record"],
        ref["version"],
    ) != ("secretariat_reconciliation", "RECON-01", 1):
        raise CandidateRegistryError("Expected exact GOV selected native version")
    body = _selected_body(path, ref)
    prior = body.get("previous_native_content", {})
    if (
        prior.get("record") != ("ACTION-REOPEN" if messy else "ACTION-01")
        or prior.get("sha256")
        != _linked_sha(path, ref["branch"], "action_register", prior["record"], 1)
        or body.get("schema") != v17_portfolio.gov.SCHEMA + "_NATIVE_EVENT"
        or body.get("truth_class") != "TRAINING_SCENARIO_ONLY"
        or body.get("company") != ref["company"]
        or body.get("branch") != ref["branch"]
        or body.get("scenario") != ("MESSY" if messy else "CLEAN")
        or body.get("actor_id") != "AS-P004"
        or body.get("case_id") != "SIM-GOV-SEC003-Q4-01"
        or body.get("fictional_committee_cycle") is not True
        or body.get("locked_charter_reference_only") is not True
        or any(
            body.get(key) is not False
            for key in (
                "actual_board_meeting",
                "adopted_minutes",
                "legal_quorum_established",
                "collective_resolution_recorded",
                "independent_assurance_completed",
                "complete_oversight_population",
                "actual_phi_processing",
                "authored_cc12_clause_satisfied",
                "fresh_audit_pair_created",
                "source_complete",
                "audit_task_credit",
            )
        )
        or body.get("real_external_messages_sent") != 0
        or body.get("status")
        != (
            "HISTORICAL_GOV_EXCEPTION_OPEN"
            if messy
            else "SELECTED_CYCLE_OPEN_NO_COLLECTIVE_APPROVAL"
        )
        or body.get("action")
        != (
            "RECONCILE_CORRECTION_AND_HISTORICAL_EXCEPTION"
            if messy
            else "RECONCILE_SELECTED_DRAFT_AND_OPEN_QUESTION"
        )
        or len(body.get("upstream_original_refs", [])) != (3 if messy else 2)
        or (body.get("detail", {}).get("questionnaire_still_missing") is True) is not messy
    ):
        raise CandidateRegistryError("GOV selected version asserted Board closure or assurance")
    return {
        "selected_terminal": "RECON-01",
        "selected_cycle_open": True,
        "messy_historical_governance_exception_open": messy,
        "messy_historical_sec003_exception_open": messy,
        "actual_board_meeting": False,
        "adopted_minutes": False,
        "legal_quorum_established": False,
        "independent_assurance_completed": False,
        "audit_task_credit": False,
    }


def _component_rows(profile: dict) -> list[tuple[str, dict, dict]]:
    """Preserve 38 reviewed V16 components, then add ENG005 and GOV."""
    pins = profile["source_pins"]
    components = profile["manifest"]["components"]
    names = [_source_id(pin) for pin in pins]
    if len(pins) != 40 or len(set(names)) != 40 or len(components) != 53:
        raise CandidateRegistryError("Expected exact 40 scenario components")
    if {name for name in components if name.startswith("scenario-")} != set(names):
        raise CandidateRegistryError("Scenario source component roster differs")
    added = ["scenario-eng005operating", "scenario-govoversight"]
    if names[-2:] != added or any(names.count(name) != 1 for name in added):
        raise CandidateRegistryError("Exact ENG005/GOV source pair required per profile")
    old = prior_probe._component_rows(
        {
            "source_pins": pins[:-2],
            "manifest": {
                "components": {key: value for key, value in components.items() if key not in added}
            },
        }
    )
    rows = list(old)
    for name, pin, selected in zip(added, pins[-2:], v17_portfolio.SOURCES, strict=True):
        component = components[name]
        module = selected["module"]
        if (
            pin.get("source") != selected["source"]
            or pin.get("ledger") != "native"
            or pin.get("source_review_sha256") != selected["review_sha"]
            or pin.get("database_sha256") != selected["db_sha"]
            or pin.get("receipt_sha256") != selected["receipt_sha"]
            or pin.get("manifest_sha256") != selected["manifest_sha"]
            or pin.get("physical_company") != module.COMPANY
            or pin.get("physical_branch") not in module.BRANCHES.values()
            or pin.get("system_count") != selected["systems"]
            or pin.get("inherited_audit_journals") != ZERO_BASELINE
            or component.get("company") != module.COMPANY
            or component.get("branch") != pin["physical_branch"]
            or component.get("namespace") != v17_candidates.NAMESPACES[selected["source"]]
            or component.get("systems") != v17_candidates.ALIASES[selected["source"]]
        ):
            raise CandidateRegistryError("Reviewed ENG005/GOV selected source route differs")
        rows.append((name, pin, component))
    return rows


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


def _reviewed_v17(repository: Path, private_repository: Path) -> None:
    """Require independently reviewed main-local V17 portfolio/candidate bytes."""
    if (
        any(
            not isinstance(digest, str) or len(digest) != 64
            for digest in (
                REVIEW_SHA256,
                PORTFOLIO_REPORT_SHA256,
                CANDIDATE_REPORT_SHA256,
                CANDIDATE_A_SHA256,
                CANDIDATE_B_SHA256,
                ISOLATED_REVIEW_SHA256,
            )
        )
        or not V17_INTEGRATED_COMMIT
    ):
        raise CandidateRegistryError("V17 main independent review pins are pending")
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
        raise CandidateRegistryError("Independently reviewed V17 package hash differs")
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
        or review.get("integrated_commit") != V17_INTEGRATED_COMMIT
        or review.get("source_complete") is not False
        or review.get("fresh_audit_pair_created") is not False
        or review.get("audit_task_credit") is not False
    ):
        raise CandidateRegistryError("Independently reviewed V17 verdict differs")
    portfolio_report = _json(portfolio_path)
    candidate_report = _json(candidate_path)
    if (
        (portfolio_report.get("source_count"), portfolio_report.get("native_versions")) != (39, 897)
        or portfolio_report.get("source_component_count") != 40
        or portfolio_report.get("source_complete") is not False
        or candidate_report.get("reviewed_native_versions") != 897
        or candidate_report.get("source_complete") is not False
        or candidate_report.get("audit_task_credit") is not False
        or any(
            (
                candidate_report.get("sides", {}).get(side, {}).get("component_count"),
                candidate_report.get("sides", {})
                .get(side, {})
                .get("scenario_source_component_count"),
                candidate_report.get("sides", {}).get(side, {}).get("system_alias_count"),
            )
            != (53, 40, 345)
            for side in "AB"
        )
    ):
        raise CandidateRegistryError("Reviewed V17 portfolio/candidate shape differs")


def _match_reviewed_v17_candidates(profiles: dict, private_repository: Path) -> None:
    """Tie recomputed source routes to the exact reviewed main A/B manifests."""
    root = private_repository / REVIEWED_PACKAGE / "main-candidate-v1"
    reviewed = _json(root / "REPORT.json")
    for side, expected_sha in (("A", CANDIDATE_A_SHA256), ("B", CANDIDATE_B_SHA256)):
        path = root / f"{side}.json"
        selected = reviewed["sides"][side]
        profile = profiles[side]
        if (
            _private(path)[-1] != expected_sha
            or profile["manifest"] != _json(path)
            or profile["source_pins"] != selected["source_pins"]
            or profile["profile_id"] != selected["profile_id"]
            or profile["base_registry_sha256"] != selected["base_registry_sha256"]
            or selected["registry_sha256"] != expected_sha
            or selected["source_complete"] is not False
        ):
            raise CandidateRegistryError("Recomputed V17 candidate differs from reviewed main")


def _reviewed_v16_collector(repository: Path, private_repository: Path) -> dict:
    """Pin and reverify the whole previously reviewed disposable collector run."""
    base = private_repository / REVIEWED_V16_COLLECTOR
    review_path = base / "independent-review-main-v1/REVIEW.json"
    run_root = base / "main-run-v1"
    paths = {
        "review": review_path,
        "A.json": run_root / "A.json",
        "B.json": run_root / "B.json",
        "REPORT.json": run_root / "REPORT.json",
    }
    expected = {
        "review": V16_COLLECTOR_REVIEW_SHA256,
        "A.json": V16_COLLECTOR_A_SHA256,
        "B.json": V16_COLLECTOR_B_SHA256,
        "REPORT.json": V16_COLLECTOR_REPORT_SHA256,
    }
    before = {name: _private(path) for name, path in paths.items()}
    if any(before[name][-1] != digest for name, digest in expected.items()):
        raise CandidateRegistryError("Independently reviewed V16 collector byte pin differs")
    review = _json(review_path)
    if (
        review.get("verdict") != "PASS_MAIN_DISPOSABLE_COLLECTION_NO_AUDIT_CREDIT"
        or review.get("main_output_sha256")
        != {name: expected[name] for name in ("A.json", "B.json", "REPORT.json")}
        or review.get("p1_freeze") != P1_FREEZE
        or review.get("integrated_commit") != "45ededc1"
        or review.get("isolated_review_sha256")
        != "6a19299529d62f4c08cc533303356bc2b4178eee063a43a7bdf84077139f04a0"
        or review.get("source_complete") is not False
        or review.get("fresh_audit_pair_created") is not False
        or review.get("audit_task_credit") is not False
    ):
        raise CandidateRegistryError("Independently reviewed V16 collector verdict differs")
    report = _json(paths["REPORT.json"])
    if (
        report.get("schema") != prior_probe.SCHEMA
        or report.get("status") != "PASS_DISPOSABLE_SOURCE_TO_COLLECTOR_BOUNDARY_ONLY"
        or report.get("p1_freeze") != P1_FREEZE
        or (
            report.get("reviewed_source_count"),
            report.get("reviewed_native_version_count"),
            report.get("scenario_source_component_count_per_side"),
            report.get("frozen_baseline_component_count_per_side"),
            report.get("disposable_component_count_per_side"),
            report.get("disposable_copy_count"),
            report.get("disposable_collection_count"),
        )
        != (37, 840, 38, 13, 51, 102, 76)
        or len(report.get("reviewed_sources", [])) != 37
        or any(
            len(report.get("sides", {}).get(side, {}).get("collections", [])) != 38
            or len(report.get("sides", {}).get(side, {}).get("frozen_copies", [])) != 13
            for side in "AB"
        )
        or any(
            report.get(key) is not False
            for key in ("source_complete", "fresh_audit_pair_created", "audit_task_credit")
        )
        or report.get("original_company_sources_unchanged") is not True
        or any(_private(path) != before[name] for name, path in paths.items())
    ):
        raise CandidateRegistryError("Reviewed V16 collector changed during verification")
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
        "emergency_selected_case",
        "prd_concern_selected_case",
    )


def run(repository: Path, private_repository: Path, destination: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise CandidateRegistryError("Fresh disposable V17 probe destination required")
    _private(destination.parent, directory=True)
    freeze = _p1_inventory(private_repository)
    if freeze != P1_FREEZE:
        raise CandidateRegistryError("Frozen active P1 inventory differs")
    _reviewed_v17(repository, private_repository)
    previous_collector = _reviewed_v16_collector(repository, private_repository)
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    _match_reviewed_v17_candidates(profiles, private_repository)
    if (
        diagnostic["source_count"],
        diagnostic["native_versions"],
        diagnostic["source_complete"],
    ) != (39, 897, False) or diagnostic["sources"][:37] != previous_collector["reviewed_sources"]:
        raise CandidateRegistryError(
            "Reviewed V17 source qualification or V16 collector prefix differs"
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
            prd_concern = (
                _prd_concern_final(origin, ref) if source_id == "scenario-prdconcern" else None
            )
            eng005 = (
                _eng005_operating_final(origin, ref)
                if source_id == "scenario-eng005operating"
                else None
            )
            gov_oversight = (
                _gov_oversight_final(origin, ref) if source_id == "scenario-govoversight" else None
            )
            baseline, baseline_counts, baseline_digest = _journal_baseline(origin, source_id)
            if source_id == "scenario-rec003-dq":
                if (
                    pin.get("root_locator") != "snapshot://" + side
                    or pin.get("inherited_audit_journals") != REC_BASELINE
                ):
                    raise CandidateRegistryError("REC003 portable route/journal pin differs")
            elif pin.get("inherited_audit_journals", ZERO_BASELINE) != ZERO_BASELINE:
                raise CandidateRegistryError("Unexpected inherited access in V17 source pin")
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
                    prd_concern,
                    eng005,
                    gov_oversight,
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
            prd_concern,
            eng005,
            gov_oversight,
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
                command_id=f"PROBE-V17-{side}-{source_id.upper()}",
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
            if prd_concern is not None:
                result_row["prd_concern_selected_case"] = prd_concern
            if eng005 is not None:
                result_row["eng005_operating_selected_case"] = eng005
            if gov_oversight is not None:
                result_row["gov_oversight_selected_case"] = gov_oversight
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
            len(rows) != 40
            or len(old_rows) != 38
            or any(
                any(new.get(key) != old.get(key) for key in prefix_keys)
                for new, old in zip(rows[:38], old_rows, strict=True)
            )
            or frozen_rows != previous_collector["sides"][side]["frozen_copies"]
        ):
            raise CandidateRegistryError("Exact reviewed V16 collector semantic prefix differs")
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
    _reviewed_v17(repository, private_repository)
    if _p1_inventory(private_repository) != freeze:
        raise CandidateRegistryError("Active P1 inventory changed during disposable probe")
    report = {
        "schema": SCHEMA,
        "status": "PASS_DISPOSABLE_SOURCE_TO_COLLECTOR_BOUNDARY_ONLY",
        "probe_module_sha256": _sha(Path(__file__)),
        "reviewed_portfolio_verifier_sha256": diagnostic["verifier_module_sha256"],
        "reviewed_v17_review_sha256": REVIEW_SHA256,
        "reviewed_v17_portfolio_report_sha256": PORTFOLIO_REPORT_SHA256,
        "reviewed_v17_candidate_report_sha256": CANDIDATE_REPORT_SHA256,
        "reviewed_v16_collector_review_sha256": V16_COLLECTOR_REVIEW_SHA256,
        "reviewed_v16_collector_report_sha256": V16_COLLECTOR_REPORT_SHA256,
        "reviewed_sources": diagnostic["sources"],
        "reviewed_source_count": 39,
        "reviewed_native_version_count": 897,
        "scenario_source_component_count_per_side": 40,
        "frozen_baseline_component_count_per_side": 13,
        "disposable_component_count_per_side": 53,
        "disposable_copy_count": 106,
        "disposable_collection_count": 80,
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
            "PRD concern Clean selects held reconciliation; Messy selects the OPEN "
            "historical recipient exception, followed by a corrected matrix without closure.",
            "The claimant remains unverified, legal notice duty and signatory authority "
            "unresolved, and no accepted delivery or customer acknowledgment occurred.",
            "No actual PHI, authored communication-clause satisfaction or complete "
            "customer/channel population follows from PRD concern.",
            "ENG005 Clean selects a blocked Boise emergency authority review; Messy "
            "selects an OPEN bypass exception after rollback. Ordinary and emergency "
            "Messy historical exceptions remain open.",
            "ENG005 has no corporate emergency delegation, deployed device change, "
            "network writes, PHI or full change population.",
            "GOV selects secretary reconciliation of one committee draft cycle; "
            "Messy governance and SEC003 historical exceptions remain OPEN.",
            "No actual Board meeting, adopted minutes, legal quorum, independent "
            "assurance or authored CC1.2 satisfaction follows from GOV.",
            "One exact native version per component is selected, not a period population.",
            "No PBC, audit engagement, workpaper, task, grade or Key changed.",
            "The partial 39-cohort portfolio does not resolve all discovery routes.",
        ],
    }
    _write_json(destination / "REPORT.json", report)
    return report


def verify(destination: Path, repository: Path, private_repository: Path) -> dict:
    """Read-only verification of sealed probe, clones, journals and source pins."""
    root = Path(destination).absolute()
    _private(root, directory=True)
    if {path.name for path in root.iterdir()} != {"A", "B", "A.json", "B.json", "REPORT.json"}:
        raise CandidateRegistryError("Exact V17 disposable probe layout required")
    for name in ("A.json", "B.json", "REPORT.json"):
        _private(root / name)
    report = _json(root / "REPORT.json")
    freeze = _p1_inventory(private_repository)
    if freeze != P1_FREEZE:
        raise CandidateRegistryError("Frozen active P1 inventory differs")
    _reviewed_v17(repository, private_repository)
    previous_collector = _reviewed_v16_collector(repository, private_repository)
    diagnostic, profiles = candidate_profiles(repository, private_repository)
    _match_reviewed_v17_candidates(profiles, private_repository)
    if (
        report.get("schema") != SCHEMA
        or report.get("status") != "PASS_DISPOSABLE_SOURCE_TO_COLLECTOR_BOUNDARY_ONLY"
        or report.get("probe_module_sha256") != _sha(Path(__file__))
        or report.get("reviewed_sources") != diagnostic["sources"]
        or diagnostic["sources"][:37] != previous_collector["reviewed_sources"]
        or report.get("reviewed_portfolio_verifier_sha256") != diagnostic["verifier_module_sha256"]
        or report.get("reviewed_v17_review_sha256") != REVIEW_SHA256
        or report.get("reviewed_v17_portfolio_report_sha256") != PORTFOLIO_REPORT_SHA256
        or report.get("reviewed_v17_candidate_report_sha256") != CANDIDATE_REPORT_SHA256
        or report.get("reviewed_v16_collector_review_sha256") != V16_COLLECTOR_REVIEW_SHA256
        or report.get("reviewed_v16_collector_report_sha256") != V16_COLLECTOR_REPORT_SHA256
        or report.get("reviewed_source_count") != 39
        or report.get("reviewed_native_version_count") != 897
        or report.get("scenario_source_component_count_per_side") != 40
        or report.get("frozen_baseline_component_count_per_side") != 13
        or report.get("disposable_component_count_per_side") != 53
        or report.get("disposable_copy_count") != 106
        or report.get("disposable_collection_count") != 80
        or report.get("p1_freeze") != freeze
        or report.get("source_complete") is not False
        or report.get("fresh_audit_pair_created") is not False
        or report.get("audit_task_credit") is not False
        or report.get("original_company_sources_unchanged") is not True
    ):
        raise CandidateRegistryError("V17 probe report qualification differs")
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
        if len(rows) != 40 or report["sides"][side]["scenario"] != scenario:
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
            if source_id == "scenario-prdconcern":
                if row.get("prd_concern_selected_case") != _prd_concern_final(origin, original_ref):
                    raise CandidateRegistryError("PRD concern selected terminal case differs")
            elif "prd_concern_selected_case" in row:
                raise CandidateRegistryError("Non-concern route has PRD concern claim")
            if source_id == "scenario-eng005operating":
                if row.get("eng005_operating_selected_case") != _eng005_operating_final(
                    origin, original_ref
                ):
                    raise CandidateRegistryError("ENG005 selected terminal case differs")
            elif "eng005_operating_selected_case" in row:
                raise CandidateRegistryError("Non-ENG005 route has operating-change claim")
            if source_id == "scenario-govoversight":
                if row.get("gov_oversight_selected_case") != _gov_oversight_final(
                    origin, original_ref
                ):
                    raise CandidateRegistryError("GOV selected terminal case differs")
            elif "gov_oversight_selected_case" in row:
                raise CandidateRegistryError("Non-GOV route has oversight claim")
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
            or len(old_rows) != 38
            or any(
                any(new.get(key) != old.get(key) for key in prefix_keys)
                for new, old in zip(rows[:38], old_rows, strict=True)
            )
        ):
            raise CandidateRegistryError("Exact reviewed V16 collector semantic prefix differs")
    _reviewed_v17(repository, private_repository)
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
