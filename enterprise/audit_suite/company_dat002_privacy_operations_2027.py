"""Company-owned fictional privacy routing history, separate from audit execution.

Only nonpersonal token metadata is stored. Imported times are insertion times;
2027 business clocks are explicitly simulated. Source payloads contain the
operating team's records, never learner answers or audit conclusions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from . import company_dat002_rights_scope_2027 as rights
from . import company_processing_purpose_2027_simulation as purpose
from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_DAT002_PRIVACY_OPERATIONS_V1"
COMPANY = purpose.COMPANY
BRANCHES = {"CLEAN": "PRIVACY-OPS-A", "MESSY": "PRIVACY-OPS-B"}
DATASET = "DS-SIM-PRIVACY-OPERATIONS-01"
SCHEDULE = "SIM-BAA-CUST-01-PRIVACY-SCHEDULE-01"
SOURCE_REFERENCE = "enterprise/audit_suite/company_dat002_privacy_operations_2027.py"
PERIOD = {"start": "2027-09-01T00:00:00+00:00", "end": "2027-09-30T23:59:59+00:00"}
SPEC_REL = "enterprise/audit_suite/dat002_privacy_operations_spec_v1.json"
RIGHTS_REL = "enterprise/generated/audit-suite/company-dat002-rights-scope-2027-2026-10-01"
RIGHTS_PINS = {
    "manifest": "222b21ad5a90e05fb1c690951e7a94537148a682a69a39a661fbc0fd0ff2f91f",
    "receipt": "55502c4210f1855e570352d4972c002ca8726c74db551691e1e89eb4230064ad",
    "database": "07deca8ba563281439167f5b274364942dab9a9fdc96b01209a722d3f13e1a44",
    "review": "7c244ae5938868b1caf97500682a8f4cad1402d59e29a45c08fb8110e388763e",
}
SOURCE_PINS = {
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md": (
        "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496"
    ),
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md": (
        "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751"
    ),
    "enterprise/audit_suite/phi_ba_2027_contract_spec_v1.json": (
        "557cd3ddf09195207de93be2441710f38be9aa8693de729c07d8cf45e45a081f"
    ),
    "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V17_2026-10-01.json": (
        "43b33d7ca19e670eea704193fff947c268c2d1c736f0c8829420a556576e8bcb"
    ),
    SPEC_REL: "52da9a5239b392de7b22620d999c50e48605766e608f3ac544beb5ba0f81fb7d",
}
TASK_SUFFIXES = (
    "CHECK-HIPAA:164.302",
    "CHECK-HIPAA:164.500",
    "CHECK-HIPAA:164.506",
    "CHECK-HIPAA:164.508",
    "CHECK-HIPAA:164.510",
    "CHECK-HIPAA:164.512",
    "CHECK-HIPAA:164.514",
    "CHECK-HIPAA:164.522",
    "CHECK-SOC2:C1.1",
    "CHECK-SOC2:CC6.7",
    "IMPLEMENTATION",
    "TOD",
    "TOE",
)
TARGET_TASKS = tuple(f"TASK-SH-DAT-002-corporate-{suffix}" for suffix in TASK_SUFFIXES)
SYSTEM_OWNERS = {
    "privacy_contract": "AS-P003",
    "privacy_authority": "AS-P003",
    "privacy_customer_instruction": "AS-P014",
    "privacy_legal_review": "AS-P003",
    "privacy_dataset_inventory": "AS-P014",
    "privacy_configuration": "AS-P007",
    "privacy_change_approval": "AS-P008",
    "privacy_request": "AS-P014",
    "privacy_customer_decision": "AS-P014",
    "privacy_gate_decision": "AS-P003",
    "privacy_release": "AS-P007",
    "privacy_receipt": "AS-P014",
    "privacy_lifecycle": "AS-P014",
    "privacy_monitoring": "AS-P008",
    "privacy_exception": "AS-P003",
    "privacy_reconciliation": "AS-P014",
}
LIMITS = [
    "Fictional 2027 customer-directed privacy service; all customer instruments, approvals, "
    "recipient acknowledgments and legal judgments are authored synthetic records, "
    "not actual communications.",
    "The new schedule applies prospectively to a distinct nonpersonal token dataset. It does not "
    "amend original source bytes or close the older marker purpose, label, "
    "BA-flowdown or rights holds.",
    "The selected September service roster is bounded to one synthetic customer, 23 requests and "
    "five storage/processing locations; it is not the enterprise ePHI, "
    "designated-record-set or audit population.",
    "Printed reproductive-health cross-references remain held for qualified "
    "period-specific legal review; "
    "no 2027 change in actual law or live HIPAA applicability is asserted.",
    "No actual PHI, actual BA status, external release, live deployment, audit task credit, "
    "accepted applicability/N/A, fresh engagement, grade, Key or Atlas mutation.",
]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _context(repository: Path, private_repository: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    for relative, expected in SOURCE_PINS.items():
        path = repository / relative
        if path.is_symlink() or not path.is_file() or _digest(path) != expected:
            raise CompanyStoreError("Pinned DAT002 privacy specification/canon differs")
    spec = json.loads((repository / SPEC_REL).read_text())
    if (
        spec.get("schema") != SCHEMA + "_SPEC"
        or spec.get("dataset_id") != DATASET
        or spec.get("period") != PERIOD
        or spec.get("truth_class") != "TRAINING_SCENARIO_ONLY"
        or spec.get("customer_decision_owner") != "SIM-CUST-PRIVACY-OFFICER-01"
        or spec.get("schedule_id") != SCHEDULE
        or spec.get("prospective_only") is not True
        or spec.get("real_world_authority") is not False
    ):
        raise CompanyStoreError("Privacy service authority specification differs")
    ledger = json.loads((repository / list(SOURCE_PINS)[3]).read_text())
    for side in "AB":
        missing = [
            r
            for r in ledger["rows"]
            if r["side"] == side
            and r["control_id"] == "SH-DAT-002"
            and not r["targeted_integrated_source_ids"]
        ]
        if sorted(r["task_id"] for r in missing) != sorted(TARGET_TASKS) or any(
            r["current_status"] != "NOT_STARTED"
            or r["current_conclusion"] != "NOT_RUN"
            or r["audit_task_credit"] is not False
            for r in missing
        ):
            raise CompanyStoreError("Exact 13 unrun DAT002 routes differ")
    root = private / RIGHTS_REL / "main-run-v1"
    paths = {
        "manifest": root / "MANIFEST.json",
        "receipt": root / "RECEIPT.json",
        "database": root / "company.sqlite3",
        "review": private / RIGHTS_REL / "independent-review-main-v1/REVIEW.json",
    }
    before = purpose._frozen(paths)
    if {key: value[-1] for key, value in before.items()} != RIGHTS_PINS:
        raise CompanyStoreError("Reviewed DAT002 rights source pin differs")
    rights.verify(root, repository=repository, private_repository=private)
    review = json.loads(paths["review"].read_text())
    if (
        review.get("verdict") != "PASS_MAIN_SELECTED_SOURCE_NO_AUDIT_CREDIT"
        or review.get("audit_task_credit") is not False
    ):
        raise CompanyStoreError("Prior rights review boundary differs")
    receipt = json.loads(paths["receipt"].read_text())
    originals = {}
    with closing(
        sqlite3.connect(paths["database"].as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        for scenario in BRANCHES:
            originals[scenario] = []
            for ref in receipt["records"][scenario]:
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    tuple(ref[k] for k in ("company", "branch", "system", "record", "version")),
                ).fetchone()
                if row is None or sha(row["content"]) != ref["sha256"]:
                    raise CompanyStoreError("Prior rights native source differs")
                originals[scenario].append(
                    {
                        "ref": {k: ref[k] for k in rights.ORIGINAL_FIELDS},
                        "body": json.loads(row["content"]),
                    }
                )
    phi_context = purpose._input_context(repository, private)
    if purpose._frozen(paths) != before:
        raise CompanyStoreError("Prior rights source changed during read")
    return {"spec": spec, "rights": originals, "phi": phi_context["phi"]}


def _cases() -> list[dict]:
    """Operational request facts. No audit outcome or learner answer is recorded here."""
    cases = []

    def add(case, route, recipient, facts, decision, reason, day):
        cases.append(
            {
                "case_id": case,
                "route": route,
                "recipient_id": recipient,
                "facts": facts,
                "customer_decision": decision,
                "decision_reason": reason,
                "day": day,
            }
        )

    add(
        "OPS-01",
        "164.506(c)(4)",
        "SIM-COVERED-RECIPIENT-01",
        {
            "sender_relationship": True,
            "recipient_relationship": True,
            "information_relates_to_both_relationships": True,
            "operation": "QUALITY_ASSESSMENT",
            "ordinary_consent_present": True,
            "required_authorization": False,
        },
        "PERMIT",
        "QUALIFYING_QUALITY_OPERATIONS",
        2,
    )
    add(
        "OPS-02",
        "164.506(c)(4)",
        "SIM-COVERED-RECIPIENT-02",
        {
            "sender_relationship": True,
            "recipient_relationship": False,
            "information_relates_to_both_relationships": False,
            "operation": "QUALITY_ASSESSMENT",
            "ordinary_consent_present": True,
            "required_authorization": False,
        },
        "HOLD",
        "RECIPIENT_RELATIONSHIP_NOT_ESTABLISHED",
        3,
    )
    for number, state, permit in (
        (1, "CURRENT_COMPLETE", True),
        (2, "EXPIRED", False),
        (3, "REVOKED", False),
        (4, "MISSING_RECIPIENT", False),
    ):
        add(
            f"AUTH-0{number}",
            "164.508",
            "SIM-AUTHORIZED-RECIPIENT-01",
            {
                "authorization_id": f"SIM-AUTH-0{number}",
                "state": state,
                "description": "SELECTED_TOKEN_RECORD",
                "authorized_discloser": "SIM-COVERED-CUSTOMER-01",
                "named_recipient": None if number == 4 else "SIM-AUTHORIZED-RECIPIENT-01",
                "purpose": "INDIVIDUAL_DIRECTED_COPY",
                "expiration_at": "2027-08-31T23:59:59+00:00"
                if number == 2
                else "2027-12-31T23:59:59+00:00",
                "signature_token": "SIM-SIGNATURE-NONPERSONAL-01",
                "signature_date": "2027-08-30",
                "customer_copy_provided": True,
                "authority_verified_by_customer": True,
                "right_to_revoke_statement": True,
                "conditioning_statement": True,
                "redisclosure_statement": True,
                "plain_language": True,
                "revoked_at": "2027-09-05T08:00:00+00:00" if number == 3 else None,
                "previous_reliance_before_revocation": False,
            },
            "PERMIT" if permit else "HOLD",
            state,
            4 + number,
        )
    add(
        "AUTH-PSY",
        "164.508(a)(2)",
        "SIM-AUTHORIZED-RECIPIENT-01",
        {
            "category": "PSYCHOTHERAPY_NOTES",
            "combined_with_general_authorization": True,
            "separate_notes_authorization": False,
            "exception_asserted": None,
        },
        "HOLD",
        "SEPARATE_NOTES_AUTHORIZATION_REQUIRED",
        9,
    )
    add(
        "AUTH-MKT",
        "164.508(a)(3)",
        "SIM-MARKETING-RECIPIENT-01",
        {
            "category": "THIRD_PARTY_REMUNERATED_MARKETING",
            "remuneration": True,
            "remuneration_statement": False,
            "face_to_face_or_nominal_gift": False,
        },
        "HOLD",
        "MARKETING_REMUNERATION_STATEMENT_ABSENT",
        10,
    )
    add(
        "AUTH-SALE",
        "164.508(a)(4)",
        "SIM-SALE-RECIPIENT-01",
        {
            "category": "SALE_OF_LOGICAL_PHI",
            "remuneration": True,
            "remuneration_statement": False,
            "exception_asserted": None,
        },
        "HOLD",
        "SALE_REMUNERATION_STATEMENT_ABSENT",
        11,
    )
    add(
        "FAMILY-01",
        "164.510(b)(2)",
        "SIM-FAMILY-CONTACT-01",
        {
            "relationship_claim": "SIBLING",
            "individual_available": True,
            "known_preference": "OBJECTS",
            "relevant_scope": ["CARE_COORDINATION_TOKEN"],
            "requested_scope": ["ENTIRE_TOKEN_RECORD"],
            "clinical_judgment": None,
        },
        "HOLD",
        "KNOWN_OBJECTION_NO_GENERAL_FAMILY_ACCESS",
        12,
    )
    add(
        "FAMILY-02",
        "164.510(b)(3)",
        "SIM-FAMILY-CONTACT-02",
        {
            "individual_available": False,
            "reason": "SIMULATED_EMERGENCY",
            "known_preference": "LIMIT_TO_CARE_COORDINATION",
            "clinical_judgment": "BEST_INTEREST_DIRECTLY_RELEVANT_SCOPE",
            "customer_clinical_actor": "SIM-CUST-CLINICIAN-01",
            "relevant_scope": ["CARE_COORDINATION_TOKEN"],
            "requested_scope": ["CARE_COORDINATION_TOKEN"],
        },
        "PERMIT",
        "CUSTOMER_CLINICAL_JUDGMENT_AND_LIMITED_SCOPE",
        13,
    )
    add(
        "JUDICIAL-01",
        "164.512(e)(1)(i)",
        "SIM-TRIBUNAL-RECIPIENT-01",
        {
            "process_id": "SIM-ORDER-01",
            "process_kind": "COURT_ORDER",
            "recipient_authority_verified": True,
            "scope_authorized": ["ORDER_TOKEN_01"],
            "scope_requested": ["ORDER_TOKEN_01"],
            "counsel_scope_screen": "MATCH",
            "reproductive_health_content": False,
        },
        "PERMIT",
        "EXPRESS_ORDER_SCOPE_ONLY",
        14,
    )
    add(
        "JUDICIAL-02",
        "164.512(e)(1)(ii)",
        "SIM-LITIGANT-RECIPIENT-01",
        {
            "process_id": "SIM-SUBPOENA-01",
            "process_kind": "SUBPOENA_WITHOUT_ORDER",
            "recipient_authority_verified": True,
            "notice_assurance_documented": False,
            "qualified_protective_order_assurance_documented": False,
            "reproductive_health_content": False,
        },
        "HOLD",
        "SATISFACTORY_ASSURANCES_ABSENT",
        15,
    )
    add(
        "JUDICIAL-03",
        "164.512",
        "SIM-INVESTIGATOR-RECIPIENT-01",
        {
            "process_id": "SIM-LEGAL-INQUIRY-01",
            "process_kind": "INFORMAL_REQUEST",
            "reproductive_health_content": True,
            "enforceable_mandate": False,
            "qualified_period_legal_status": "PENDING",
            "printed_164509_not_automatically_applied": True,
        },
        "HOLD",
        "NO_MANDATE_AND_PERIOD_LEGAL_OVERLAY_PENDING",
        16,
    )
    add(
        "DEID-01",
        "164.514(b)(2)",
        "SIM-ANALYTICS-RECIPIENT-01",
        {
            "method": "SAFE_HARBOR_CANDIDATE",
            "input_field_categories": ["YEAR", "FULL_DATE", "DEVICE_ID"],
            "output_field_categories": ["YEAR", "FULL_DATE", "DEVICE_ID"],
            "residual_identifier_categories": ["FULL_DATE", "DEVICE_ID"],
            "actual_knowledge_of_identifiability": False,
            "expert_determination": None,
        },
        "HOLD",
        "RESIDUAL_IDENTIFIERS",
        17,
    )
    add(
        "DEID-02",
        "164.514(b)(2)",
        "SIM-ANALYTICS-RECIPIENT-01",
        {
            "method": "SAFE_HARBOR_CANDIDATE",
            "input_field_categories": ["YEAR", "RARE_EVENT_CATEGORY"],
            "output_field_categories": ["YEAR", "RARE_EVENT_CATEGORY"],
            "residual_identifier_categories": [],
            "actual_knowledge_of_identifiability": True,
            "knowledge_basis": "RARE_EVENT_LINKABILITY_IN_CUSTOMER_RECIPIENT_CONTEXT",
            "expert_determination": None,
        },
        "HOLD",
        "ACTUAL_KNOWLEDGE_LIMIT",
        18,
    )
    add(
        "DEID-03",
        "164.514(b)(2),(c)",
        "SIM-ANALYTICS-RECIPIENT-01",
        {
            "method": "SAFE_HARBOR_CUSTOMER_DETERMINATION",
            "identifier_category_screen_count": 18,
            "input_field_categories": [
                "NAME",
                "FULL_DATE",
                "RECORD_NUMBER",
                "STATE",
                "AGE_UNDER_90",
            ],
            "output_field_categories": ["YEAR", "STATE", "AGE_UNDER_90", "RANDOM_CODE"],
            "removal_screen": {
                category: "REMOVED_OR_ABSENT"
                for category in (
                    "NAME",
                    "SUBSTATE_GEOGRAPHY",
                    "DATE_EXCEPT_YEAR_OR_AGE_OVER_89",
                    "PHONE",
                    "FAX",
                    "EMAIL",
                    "SSN",
                    "MEDICAL_RECORD_NUMBER",
                    "HEALTH_PLAN_NUMBER",
                    "ACCOUNT_NUMBER",
                    "LICENSE_NUMBER",
                    "VEHICLE_ID",
                    "DEVICE_ID",
                    "URL",
                    "IP",
                    "BIOMETRIC",
                    "FULL_FACE_IMAGE",
                    "OTHER_UNIQUE_ID",
                )
            },
            "residual_identifier_categories": [],
            "actual_knowledge_of_identifiability": False,
            "reidentification_code_derivation": "RANDOM_NONPERSONAL_NOT_DERIVED",
            "reidentification_mechanism_released": False,
            "expert_determination": None,
        },
        "PERMIT",
        "CUSTOMER_REMOVAL_AND_KNOWLEDGE_DETERMINATION",
        19,
    )
    add(
        "LDS-01",
        "164.514(e)",
        "SIM-RESEARCH-RECIPIENT-01",
        {
            "method": "LIMITED_DATA_SET",
            "deidentified_claim": False,
            "excluded_identifier_screen": "COMPLETE_CUSTOMER_METADATA_SCREEN",
            "remaining_categories": ["DATES", "CITY"],
            "purpose": "RESEARCH",
            "dua_id": "SIM-DUA-01",
            "dua_executed_in_simulation": True,
            "no_reidentification_no_contact_terms": True,
            "minimum_necessary_scope": ["STUDY_TOKEN"],
        },
        "PERMIT",
        "LIMITED_DATA_SET_WITH_DISTINCT_DUA",
        20,
    )
    add(
        "MINIMUM-01",
        "164.514(d)",
        "SIM-COVERED-RECIPIENT-01",
        {
            "purpose": "QUALITY_ASSESSMENT",
            "entire_record_requested": True,
            "entire_record_necessity_justified": False,
            "approved_scope": ["QUALITY_TOKEN"],
        },
        "HOLD",
        "OVERBROAD_SCOPE",
        21,
    )
    add(
        "RESTRICT-01",
        "164.522(a)(2)(iii)",
        "SIM-COVERED-RECIPIENT-01",
        {
            "restriction_id": "SIM-RESTRICTION-01",
            "termination_notice_at": "2027-09-20T08:00:00+00:00",
            "token_created_received_at": "2027-09-19T08:00:00+00:00",
            "termination_basis": "CUSTOMER_UNILATERAL_NOTICE",
            "individual_agreed_to_termination": False,
            "paid_in_full_item": False,
        },
        "HOLD",
        "PRE_NOTICE_INFORMATION_REMAINS_RESTRICTED",
        22,
    )
    add(
        "RESTRICT-02",
        "164.522(a)(2)(iii)",
        "SIM-COVERED-RECIPIENT-01",
        {
            "restriction_id": "SIM-RESTRICTION-01",
            "termination_notice_at": "2027-09-20T08:00:00+00:00",
            "token_created_received_at": "2027-09-21T08:00:00+00:00",
            "termination_basis": "CUSTOMER_UNILATERAL_NOTICE",
            "individual_agreed_to_termination": False,
            "paid_in_full_item": False,
        },
        "PERMIT",
        "POST_NOTICE_INFORMATION_PROSPECTIVE_TERMINATION",
        23,
    )
    add(
        "RESTRICT-03",
        "164.522(a)(1)(vi),(a)(2)(iii)",
        "SIM-HEALTH-PLAN-01",
        {
            "restriction_id": "SIM-PAID-IN-FULL-01",
            "health_plan_disclosure": True,
            "purpose": "PAYMENT",
            "otherwise_required_by_law": False,
            "solely_paid_in_full_item": True,
            "paid_by_individual_not_plan": True,
            "termination_basis": "CUSTOMER_UNILATERAL_NOTICE",
            "individual_agreed_to_termination": False,
            "token_created_received_at": "2027-09-23T08:00:00+00:00",
        },
        "HOLD",
        "PAID_IN_FULL_RESTRICTION_NOT_TERMINATED_BY_UNILATERAL_NOTICE",
        24,
    )
    add(
        "CONTACT-01",
        "164.522(b)",
        "SIM-CONFIDENTIAL-CONTACT-01",
        {
            "customer_kind": "COVERED_HEALTH_CARE_PROVIDER",
            "alternative_contact_token": "SIM-ALT-CHANNEL-01",
            "reasonable_request": True,
            "explanation_demanded": False,
            "default_contact_suppressed": True,
        },
        "PERMIT",
        "CUSTOMER_CONFIDENTIAL_CONTACT_INSTRUCTION",
        25,
    )
    return cases


def _expected_rows(context: dict, scenario: str) -> list[dict]:
    if scenario not in BRANCHES:
        raise CompanyStoreError("Unknown privacy branch")
    upstream = context["rights"][scenario]
    if (
        upstream[-1]["body"]["selected_case_status"] != "HELD_OPEN"
        or upstream[-1]["body"]["actual_disclosure_count"] != 0
        or any(r["ref"]["branch"] != rights.BRANCHES[scenario] for r in upstream)
    ):
        raise CompanyStoreError("Prior rights hold or branch identity differs")
    base = datetime.fromisoformat("2027-08-25T08:00:00+00:00")
    if any(datetime.fromisoformat(r["ref"]["available_at"]) >= base for r in upstream):
        raise CompanyStoreError("Prior source unavailable before prospective service")
    rows = []
    by_record = {}

    def add(system, record, at, details, dependencies=(), version=1, actor=None):
        event = _time(at.isoformat())
        available = _time((at + timedelta(minutes=10)).isoformat())
        refs = [by_record[key] for key in dependencies]
        if any(r["available_at"] >= event for r in refs):
            raise CompanyStoreError("Privacy dependency unavailable at business event")
        previous = by_record.get(record) if version > 1 else None
        body = {
            "schema": SCHEMA,
            "truth_class": "FUTURE_TRAINING_SCENARIO_ONLY",
            "control_id": "SH-DAT-002",
            "boundary_id": "corporate",
            "dataset_id": DATASET,
            "service_id": "SIM-PRIVACY-ROUTING-01",
            "contracting_entity_id": "SHI",
            "customer_id": "SIM-COVERED-CUSTOMER-01",
            "payload_bytes": 0,
            "real_phi_payload": False,
            "real_world_processing_or_transfer": False,
            "actual_hipaa_applicability": "UNDETERMINED",
            "actual_ba_or_legal_status": "UNDETERMINED",
            "business_clock": "FICTIONAL_2027",
            "record_id": record,
            "actor_person_id": actor or SYSTEM_OWNERS[system],
            "event_at": event,
            "available_at": available,
            "dependencies": refs,
            "supersedes": previous,
            **details,
        }
        row = {
            "system": system,
            "record": record,
            "version": version,
            "event_at": event,
            "available_at": available,
            "body": body,
            "sha256": sha(encoded(body)),
        }
        rows.append(row)
        by_record[record] = {
            "company": COMPANY,
            "branch": BRANCHES[scenario],
            **{
                k: row[k]
                for k in ("system", "record", "version", "event_at", "available_at", "sha256")
            },
        }

    add(
        "privacy_authority",
        "DELEGATION-01",
        base,
        {
            "action": "LIMITED_FICTIONAL_SERVICE_DELEGATION",
            "schedule_id": SCHEDULE,
            "limited_authority": "PROSPECTIVE_NONPERSONAL_TOKEN_SERVICE_ONLY",
            "reserved_real_world_decisions": [
                "ACTUAL_BA_STATUS",
                "REAL_LEGAL_ADVICE",
                "ACTUAL_CUSTOMER_CONTRACT",
            ],
            "prior_held_case_originals": [r["ref"] for r in upstream],
            "prior_cases_closed_by_this_record": [],
            "real_world_authority": False,
        },
    )
    for index, (role, owner) in enumerate(
        (("LEGAL", "AS-P003"), ("DATA", "AS-P014"), ("TECH", "AS-P007"), ("SEC", "AS-P008")), 1
    ):
        add(
            "privacy_change_approval",
            f"AP-{role}-01",
            base + timedelta(hours=index),
            {
                "action": "SERVICE_SCHEDULE_REVIEW",
                "review_role": role,
                "schedule_id": SCHEDULE,
                "decision": "APPROVE_LIMITED_SIMULATED_SERVICE",
                "scope": DATASET,
                "approval_is_real_signature": False,
            },
            ("DELEGATION-01",),
            actor=owner,
        )
    phi_refs = {
        name: purpose._ref(context["phi"], scenario, "contract_register", name)
        for name in ("BAA-CUST-01", "BAA-SUB-01")
    }
    add(
        "privacy_contract",
        "SCHEDULE-01",
        base + timedelta(hours=5),
        {
            "action": "EXECUTE_PROSPECTIVE_SYNTHETIC_PRIVACY_SCHEDULE",
            "schedule_id": SCHEDULE,
            "parent_contract_originals": phi_refs,
            "effective_at": PERIOD["start"],
            "applies_only_to_dataset": DATASET,
            "prior_marker_remains_outside_schedule": purpose.MARKER,
            "permitted_operations": [
                "CUSTOMER_DIRECTED_MINIMIZED_TOKEN_ROUTING",
                "CUSTOMER_DELEGATED_PRIVACY_GATES",
            ],
            "unapproved_ai_reuse": "PROHIBITED",
            "customer_signer": "SIM-CUST-PRIVACY-OFFICER-01",
            "customer_authority_in_simulation": "OFFICER_AUTHORITY_IN_AUTHORED_CUSTOMER_INSTRUMENT",
            "company_signer": "AS-P003",
            "schedule_executed_in_simulation": True,
            "real_signature_or_agreement": False,
            "not_a_cure_for_prior_flowdown_exception": True,
        },
        ("DELEGATION-01", "AP-LEGAL-01", "AP-DATA-01", "AP-TECH-01", "AP-SEC-01"),
    )
    add(
        "privacy_customer_instruction",
        "INSTRUCTION-01",
        base + timedelta(hours=6),
        {
            "action": "REGISTER_AUTHORED_CUSTOMER_SERVICE_INSTRUCTION",
            "schedule_id": SCHEDULE,
            "instruction_owner": context["spec"]["customer_decision_owner"],
            "instruction_channel": "SIMULATED_CUSTOMER_PORTAL_INSTRUMENT",
            "actual_external_message_received": False,
            "delegation_in_simulation": True,
            "authority_limit": "CUSTOMER_RETAINS_COVERED_ENTITY_AND_CLINICAL_DECISIONS",
            "approved_endpoints": [
                "SIM-RESTRICTED-RENO-PRIVACY-01",
                "SIM-RESTRICTED-BOISE-PRIVACY-01",
            ],
            "notification_route": "SIM-CUST-PRIVACY-OFFICER-01",
        },
        ("SCHEDULE-01",),
    )
    add(
        "privacy_legal_review",
        "APPLICABILITY-01",
        base + timedelta(hours=7),
        {
            "action": "WORKFLOW_SPECIFIC_FICTIONAL_ROLE_REVIEW",
            "legal_reviewer": "AS-P003",
            "direct_ba_duties": [
                "164.302_EPHI_SECURITY",
                "164.502_CONTRACTUAL_USE_LIMITS",
                "164.504_FLOWDOWN",
            ],
            "delegated_customer_duties": [
                "164.506",
                "164.508",
                "164.510",
                "164.512",
                "164.514",
                "164.522",
            ],
            "not_sable_harbor_functions": [
                "CLINICAL_TREATMENT",
                "HEALTH_PLAN",
                "CLEARINGHOUSE",
                "CUSTOMER_FACILITY_DIRECTORY",
            ],
            "reasoning": (
                "SHI hosts and routes the distinct simulated token set as "
                "the customer's BA; customer decisions govern delegated privacy "
                "actions. SHI cannot infer clinical authority or general permission "
                "from a BAA or transport encryption."
            ),
            "scenario_role": "BUSINESS_ASSOCIATE_OF_SIMULATED_CUSTOMER",
            "qualification": "FICTIONAL_COUNSEL_DECISION_NOT_REAL_LEGAL_ADVICE",
            "law_basis_checked_as_of": "2026-10-01",
            "period_specific_2027_law_not_asserted": True,
            "reproductive_health_overlay": "HOLD_FOR_QUALIFIED_PERIOD_REVIEW",
            "hhs_vacatur_notice_considered": True,
        },
        ("SCHEDULE-01", "INSTRUCTION-01"),
    )
    locations = [
        {
            "location_id": "RENO-INGRESS-01",
            "activity": ["RECEIVED", "TRANSMITTED"],
            "custodian": "SHI",
            "site": "RENO",
        },
        {
            "location_id": "RENO-TOKEN-STORE-01",
            "activity": ["CREATED", "MAINTAINED"],
            "custodian": "SHI",
            "site": "RENO",
        },
        {
            "location_id": "RENO-BACKUP-01",
            "activity": ["MAINTAINED"],
            "custodian": "SHI",
            "site": "RENO",
        },
        {
            "location_id": "BOISE-RECOVERY-01",
            "activity": ["MAINTAINED", "TRANSMITTED"],
            "custodian": "SIM-BOISE-SUBCONTRACTOR-01",
            "site": "BOISE",
        },
        {
            "location_id": "CUSTOMER-DECISION-STORE-01",
            "activity": ["CREATED", "MAINTAINED"],
            "custodian": "SIM-COVERED-CUSTOMER-01",
            "site": "CUSTOMER",
        },
    ]
    add(
        "privacy_dataset_inventory",
        "INVENTORY-01",
        base + timedelta(hours=8),
        {
            "action": "ACCEPT_BOUNDED_SERVICE_DATASET",
            "accepted_by": "AS-P014",
            "data_owner_in_simulation": "SIM-CUST-PRIVACY-OFFICER-01",
            "classification": "CONFIDENTIAL_SIMULATED_PHI_METADATA",
            "actual_personal_data": False,
            "locations": locations,
            "service_location_roster_complete": True,
            "enterprise_location_roster_complete": False,
            "retention_term": "TOKEN_RECORDS_UNTIL_2027-10-31_THEN_CUSTOMER_DISPOSITION",
            "privacy_decision_records_retention_until": "2033-09-30T23:59:59+00:00",
            "backup_retention_until": "2027-11-30T23:59:59+00:00",
            "legal_hold_overrides_disposition": True,
            "subcontractor_copy_policy": "SCHEDULED_RESTRICTED_RECOVERY_ONLY_NO_INDEPENDENT_REUSE",
            "classification_acceptance_not_transferred_to_original_dataset": purpose.DATASET,
        },
        ("INSTRUCTION-01", "APPLICABILITY-01"),
    )
    add(
        "privacy_configuration",
        "CONFIG-01",
        base + timedelta(hours=9),
        {
            "action": "DEPLOY_SCOPED_TOKEN_ROUTER",
            "effective_at": PERIOD["start"],
            "configuration_owner": "AS-P007",
            "default_release": "DENY",
            "authorization_source": "CUSTOMER_DECISION_PLUS_COUNSEL_GATE",
            "revocation_lookup": "WORKER_CACHE"
            if scenario == "MESSY"
            else "CURRENT_CUSTOMER_LEDGER",
            "revocation_cache_refreshed_at": "2027-09-04T08:00:00+00:00"
            if scenario == "MESSY"
            else None,
            "restriction_keys": ["ORDINARY_RESTRICTION"]
            if scenario == "MESSY"
            else ["ORDINARY_RESTRICTION", "PAID_IN_FULL_RESTRICTION"],
            "endpoint_allowlist": [
                "SIM-RESTRICTED-RENO-PRIVACY-01",
                "SIM-RESTRICTED-BOISE-PRIVACY-01",
            ],
            "transport_profile": "SIMULATED_MTLS_ENDPOINT_PINNING",
            "encryption_key_id": "SIM-KMS-PRIVACY-01",
            "receipt_required": True,
            "customer_contact_override": "SIM-ALT-CHANNEL-01",
            "configuration_is_real_deployment": False,
        },
        ("AP-TECH-01", "AP-SEC-01", "INVENTORY-01"),
    )
    if scenario == "MESSY":
        add(
            "privacy_configuration",
            "CACHE-MANIFEST-01",
            datetime.fromisoformat("2027-09-04T08:00:00+00:00"),
            {
                "action": "REFRESH_WORKER_RELEASE_MANIFEST",
                "authorization_id": "SIM-AUTH-03",
                "authorization_state_as_of_snapshot": "CURRENT_COMPLETE",
                "snapshot_as_of": "2027-09-04T08:00:00+00:00",
                "worker_recipient_id": "SIM-AUTHORIZED-RECIPIENT-01",
                "scope": ["TOKEN-AUTH-03"],
                "source": "AUTHORED_CUSTOMER_LEDGER_SNAPSHOT",
                "actual_external_message": False,
            },
            ("CONFIG-01",),
        )
    for sequence, case in enumerate(_cases(), 1):
        cid = case["case_id"]
        start = datetime.fromisoformat(f"2027-09-{case['day']:02d}T09:00:00+00:00")
        req = f"REQ-{cid}"
        dec = f"DEC-{cid}"
        gate = f"GATE-{cid}"
        release = f"EXEC-{cid}"
        scopes = case["facts"].get(
            "requested_scope", case["facts"].get("minimum_necessary_scope", [f"TOKEN-{cid}"])
        )
        add(
            "privacy_request",
            req,
            start,
            {
                "action": "REGISTER_CUSTOMER_DIRECTED_TOKEN_REQUEST",
                "case_id": cid,
                "logical_token_id": f"SIM-TOKEN-{cid}",
                "inlet_sequence": sequence,
                "request_source": "AUTHORED_CUSTOMER_PORTAL_HISTORY",
                "actual_external_request": False,
                "route": case["route"],
                "recipient_id": case["recipient_id"],
                "requested_scope": scopes,
                "request_facts": case["facts"],
                "customer_instruction_id": "INSTRUCTION-01",
                "source_location_id": "RENO-TOKEN-STORE-01",
            },
            ("INSTRUCTION-01", "CONFIG-01"),
        )
        add(
            "privacy_customer_decision",
            dec,
            start + timedelta(hours=1),
            {
                "action": "REGISTER_CUSTOMER_PRIVACY_DECISION",
                "case_id": cid,
                "customer_decision_actor": "SIM-CUST-CLINICIAN-01"
                if cid == "FAMILY-02"
                else "SIM-CUST-PRIVACY-OFFICER-01",
                "decision": case["customer_decision"],
                "reason": case["decision_reason"],
                "customer_facts_screened": case["facts"],
                "recipient_id": case["recipient_id"],
                "scope": scopes,
                "decision_authority_in_simulation": True,
                "actual_customer_decision_received": False,
            },
            (req, "APPLICABILITY-01"),
        )
        add(
            "privacy_gate_decision",
            gate,
            start + timedelta(hours=2),
            {
                "action": "COUNSEL_VALIDATE_CUSTOMER_ROUTE",
                "case_id": cid,
                "decision": case["customer_decision"],
                "reason": case["decision_reason"],
                "independent_from_request_and_router_operator": True,
                "route": case["route"],
                "schedule_id": SCHEDULE,
                "recipient_authorized": case["customer_decision"] == "PERMIT",
                "allowed_scope": scopes if case["customer_decision"] == "PERMIT" else [],
                "separate_legal_review_for_special_categories": cid.startswith("AUTH-"),
                "legal_status_overlay": "PENDING_PERIOD_REVIEW"
                if cid == "JUDICIAL-03"
                else "ORDINARY_SELECTED_ROUTE_SCREEN",
            },
            (req, dec, "SCHEDULE-01"),
        )
        delivered = case["customer_decision"] == "PERMIT" or (
            scenario == "MESSY" and cid in {"AUTH-03", "RESTRICT-03"}
        )
        handling = "CONSUMED_AS_ENCRYPTED_TOKEN_ONLY" if delivered else "NO_RECIPIENT_COPY"
        add(
            "privacy_release",
            release,
            start + timedelta(hours=3),
            {
                "action": "TOKEN_ROUTER_EXECUTION",
                "case_id": cid,
                "execution_status": "DELIVERED" if delivered else "WITHHELD",
                "logical_token_id": f"SIM-TOKEN-{cid}",
                "recipient_id": case["recipient_id"],
                "released_scope": scopes if delivered else [],
                "endpoint_id": "SIM-RESTRICTED-RENO-PRIVACY-01",
                "endpoint_identity_screen": "ALLOWLIST_MATCH",
                "transport_profile": "SIMULATED_MTLS_ENDPOINT_PINNING",
                "purpose": case["facts"].get("purpose", case["route"]),
                "gate_record_id": gate,
                "worker_authority_source": "CACHED_RELEASE_MANIFEST"
                if scenario == "MESSY" and cid == "AUTH-03"
                else "ORDINARY_RESTRICTION_FILTER"
                if scenario == "MESSY" and cid == "RESTRICT-03"
                else "CURRENT_COUNSEL_GATE",
                "actual_external_release": False,
                "encrypted_payload_bytes": 0,
                "after_receipt_handling": handling,
            },
            (gate, "CONFIG-01")
            + (("CACHE-MANIFEST-01",) if scenario == "MESSY" and cid == "AUTH-03" else ()),
        )
        add(
            "privacy_receipt",
            f"ACK-{cid}",
            start + timedelta(hours=4),
            {
                "action": "REGISTER_TOKEN_DELIVERY_STATUS",
                "case_id": cid,
                "status": "RECIPIENT_ACKNOWLEDGED" if delivered else "NO_DELIVERY",
                "recipient_id": case["recipient_id"],
                "receipt_token_id": f"SIM-RECEIPT-{cid}" if delivered else None,
                "recipient_use_limit": "CUSTOMER_APPROVED_CASE_SCOPE_ONLY",
                "copy_in_recipient_scope": delivered,
                "retention_or_return_obligation": "CASE_SPECIFIC_CUSTOMER_INSTRUCTION",
                "actual_external_acknowledgment": False,
            },
            (release,),
        )
    add(
        "privacy_lifecycle",
        "LIFECYCLE-01",
        datetime.fromisoformat("2027-09-27T09:00:00+00:00"),
        {
            "action": "RECONCILE_STORAGE_AND_RETENTION",
            "locations": locations,
            "created_token_count": 23,
            "received_request_count": 23,
            "maintained_token_count": 23,
            "location_seen_logical_token_counts": {
                location["location_id"]: 23 for location in locations
            },
            "quantity_basis": "NONPERSONAL_LOGICAL_TOKEN_DESCRIPTORS_NOT_REAL_EPHI",
            "subcontractor_token_copy_count": 23,
            "backup_copy_count": 23,
            "decision_record_count": 46,
            "protection_profile": "RESTRICTED_CASE_SCOPE_ENCRYPTED_TOKEN_STORE",
            "premature_delete_request_id": "SIM-DELETE-EARLY-01",
            "delete_requested_at": "2027-09-26T08:00:00+00:00",
            "delete_decision": "HOLD_BEFORE_RETENTION_EXPIRY",
            "deleted_token_count": 0,
            "unauthorized_retention_candidate": "SIM-RETAIN-AI-01",
            "retention_extension_decision": "REFUSED_OUTSIDE_SCHEDULE",
            "extra_ai_copy_created": False,
            "enterprise_population_complete": False,
        },
        ("INVENTORY-01", "EXEC-CONTACT-01"),
    )
    for index, location in enumerate(locations):
        add(
            "privacy_lifecycle",
            f"LOCATION-{location['location_id']}",
            datetime.fromisoformat("2027-09-27T12:00:00+00:00") + timedelta(hours=index),
            {
                "action": "REGISTER_LOCATION_CUSTODY_RECONCILIATION",
                "location": location,
                "period": PERIOD,
                "seen_logical_token_ids": [f"SIM-TOKEN-{c['case_id']}" for c in _cases()],
                "custody_assertion_source": "AUTHORED_LOCATION_OPERATOR_SNAPSHOT",
                "actual_provider_message_received": False,
                "customer_decision_records": 46 if location["site"] == "CUSTOMER" else 0,
                "logical_token_count": 23,
                "personal_payload_bytes": 0,
                "count_excludes_prior_marker_dataset": True,
                "delete_before_retention_expiry": "REFUSED",
                "independent_analytics_or_ai_reuse": "PROHIBITED",
            },
            ("LIFECYCLE-01",),
        )
    add(
        "privacy_monitoring",
        "MONITOR-01",
        datetime.fromisoformat("2027-09-28T09:00:00+00:00"),
        {
            "action": "RECONCILE_GATE_DECISIONS_AND_DELIVERY_JOURNAL",
            "checked_case_ids": [c["case_id"] for c in _cases()],
            "gate_delivery_mismatch_case_ids": ["AUTH-03", "RESTRICT-03"]
            if scenario == "MESSY"
            else [],
            "monitoring_owner": "AS-P008",
            "scope": "SEPTEMBER_PRIVACY_ROUTER_ONLY",
            "prior_marker_and_rights_scope_unresolved": True,
        },
        tuple(f"ACK-{c['case_id']}" for c in _cases())
        + ("LIFECYCLE-01",)
        + tuple(f"LOCATION-{location['location_id']}" for location in locations),
    )
    if scenario == "MESSY":
        add(
            "privacy_exception",
            "EXCEPTION-01",
            datetime.fromisoformat("2027-09-28T10:00:00+00:00"),
            {
                "action": "OPEN_DELIVERY_AUTHORITY_INCIDENT",
                "exception_id": "SIM-PRIVACY-DELIVERY-01",
                "affected_case_ids": ["AUTH-03", "RESTRICT-03"],
                "status": "OPEN",
                "observed_condition": "DELIVERY_OCCURRED_AFTER_CUSTOMER_AND_COUNSEL_HOLD",
                "technical_observations": [
                    "REVOCATION_CACHE_PREDATES_REVOCATION",
                    "PAID_IN_FULL_KEY_ABSENT_FROM_FILTER",
                ],
                "containment": "FUTURE_ROUTING_PAUSED_CUSTOMER_REVIEW_REQUESTED",
                "recipient_return_attestation": "PENDING",
                "retrospective_correction": "NOT_PERFORMED",
                "real_breach_determination": "NOT_APPLICABLE_TO_NONPERSONAL_FIXTURE",
            },
            ("MONITOR-01",),
        )
        add(
            "privacy_configuration",
            "CONFIG-01",
            datetime.fromisoformat("2027-09-28T11:00:00+00:00"),
            {
                "action": "PAUSE_PRIVACY_ROUTER_PENDING_REPAIR",
                "effective_at": "2027-09-28T11:00:00+00:00",
                "default_release": "DENY",
                "routing_paused": True,
                "repaired_configuration_accepted": False,
                "configuration_is_real_deployment": False,
            },
            ("EXCEPTION-01",),
            version=2,
        )
    add(
        "privacy_reconciliation",
        "PERIOD-01",
        datetime.fromisoformat("2027-09-30T20:00:00+00:00"),
        {
            "action": "CLOSE_BOUNDED_SERVICE_MONTH_ROSTER",
            "period": PERIOD,
            "inlet_sequence_first": 1,
            "inlet_sequence_last": 23,
            "inlet_sequence_gaps": [],
            "case_ids": [c["case_id"] for c in _cases()],
            "customer_decision_count": 23,
            "counsel_gate_count": 23,
            "execution_journal_count": 23,
            "delivery_status_count": 23,
            "delivered_count": 10 if scenario == "MESSY" else 8,
            "withheld_count": 13 if scenario == "MESSY" else 15,
            "delivery_authority_mismatch_count": 2 if scenario == "MESSY" else 0,
            "open_incident_ids": ["SIM-PRIVACY-DELIVERY-01"] if scenario == "MESSY" else [],
            "service_inlet_roster_complete": True,
            "enterprise_period_population_complete": False,
            "old_held_rights_case_status": "HELD_OPEN",
            "prior_scope_exception_closed": False,
            "reproductive_health_legal_overlay_status": "PENDING_QUALIFIED_PERIOD_REVIEW",
        },
        ("MONITOR-01", "LIFECYCLE-01") + (("EXCEPTION-01",) if scenario == "MESSY" else ()),
    )
    _validate_history(rows, scenario)
    return rows


def _validate_history(rows: list[dict], scenario: str) -> None:
    """Check business causality independently of manifest/checksum acceptance."""
    if scenario not in BRANCHES:
        raise CompanyStoreError("Unknown privacy validation branch")
    case_ids = [c["case_id"] for c in _cases()]
    known = {}
    gates = {}
    executions = {}
    inlet_sequences = []
    for row in rows:
        b = row["body"]
        if (
            b.get("dataset_id") != DATASET
            or b.get("payload_bytes") != 0
            or b.get("real_phi_payload") is not False
            or b.get("real_world_processing_or_transfer") is not False
            or b.get("actual_hipaa_applicability") != "UNDETERMINED"
            or any(
                key in b
                for key in ("scenario", "expected_finding", "false_clean", "rubric", "task_credit")
            )
        ):
            raise CompanyStoreError("Privacy fiction or learner-answer boundary differs")
        for dep in b["dependencies"]:
            key = (dep["system"], dep["record"], dep["version"])
            if (
                key not in known
                or dep != known[key]
                or dep["branch"] != BRANCHES[scenario]
                or dep["available_at"] >= row["event_at"]
            ):
                raise CompanyStoreError("Privacy dependency identity/availability differs")
        key = row["system"], row["record"], row["version"]
        if key in known or sha(encoded(b)) != row["sha256"]:
            raise CompanyStoreError("Duplicate or inconsistent privacy source original")
        known[key] = {
            "company": COMPANY,
            "branch": BRANCHES[scenario],
            **{
                k: row[k]
                for k in ("system", "record", "version", "sha256", "event_at", "available_at")
            },
        }
        if row["system"] == "privacy_request":
            inlet_sequences.append(b["inlet_sequence"])
        if row["system"] == "privacy_gate_decision":
            gates[b["case_id"]] = b
        if row["system"] == "privacy_release":
            executions[b["case_id"]] = b
    if (
        set(gates) != set(case_ids)
        or set(executions) != set(case_ids)
        or inlet_sequences != list(range(1, 24))
    ):
        raise CompanyStoreError(
            "Privacy complete selected request/decision/execution roster differs"
        )
    mismatches = sorted(
        cid
        for cid in case_ids
        if executions[cid]["execution_status"] == "DELIVERED" and gates[cid]["decision"] != "PERMIT"
    )
    if mismatches != (["AUTH-03", "RESTRICT-03"] if scenario == "MESSY" else []):
        raise CompanyStoreError("Privacy delivery/authority causal history differs")
    if any(
        executions[cid]["released_scope"] != gates[cid]["allowed_scope"]
        for cid in case_ids
        if gates[cid]["decision"] == "PERMIT"
    ):
        raise CompanyStoreError("Privacy permitted release scope differs")
    period = rows[-1]["body"]
    actual = sum(e["execution_status"] == "DELIVERED" for e in executions.values())
    if (
        period["delivered_count"] != actual
        or period["withheld_count"] != len(case_ids) - actual
        or period["case_ids"] != case_ids
        or period["delivery_authority_mismatch_count"] != len(mismatches)
        or period["enterprise_period_population_complete"] is not False
    ):
        raise CompanyStoreError("Privacy period reconciliation differs")


def _lead_map(rows: list[dict], refs: list[dict]) -> dict:
    selected = {
        "CHECK-HIPAA:164.302": ["APPLICABILITY-01", "INVENTORY-01", "LIFECYCLE-01"]
        + [r["record"] for r in rows if r["record"].startswith("LOCATION-")],
        "CHECK-HIPAA:164.500": ["SCHEDULE-01", "APPLICABILITY-01", "INSTRUCTION-01"],
        "CHECK-HIPAA:164.506": [
            "REQ-OPS-01",
            "DEC-OPS-01",
            "GATE-OPS-01",
            "EXEC-OPS-01",
            "REQ-OPS-02",
            "GATE-OPS-02",
        ],
        "CHECK-HIPAA:164.508": [
            f"{prefix}-{cid}"
            for cid in (
                "AUTH-01",
                "AUTH-02",
                "AUTH-03",
                "AUTH-04",
                "AUTH-PSY",
                "AUTH-MKT",
                "AUTH-SALE",
            )
            for prefix in ("REQ", "DEC", "GATE", "EXEC")
        ],
        "CHECK-HIPAA:164.510": [
            f"{prefix}-{cid}"
            for cid in ("FAMILY-01", "FAMILY-02")
            for prefix in ("REQ", "DEC", "GATE", "EXEC")
        ],
        "CHECK-HIPAA:164.512": ["APPLICABILITY-01"]
        + [
            f"{prefix}-{cid}"
            for cid in ("JUDICIAL-01", "JUDICIAL-02", "JUDICIAL-03")
            for prefix in ("REQ", "DEC", "GATE", "EXEC")
        ],
        "CHECK-HIPAA:164.514": [
            f"{prefix}-{cid}"
            for cid in ("DEID-01", "DEID-02", "DEID-03", "LDS-01", "MINIMUM-01")
            for prefix in ("REQ", "DEC", "GATE", "EXEC")
        ],
        "CHECK-HIPAA:164.522": ["CONFIG-01"]
        + [
            f"{prefix}-{cid}"
            for cid in ("RESTRICT-01", "RESTRICT-02", "RESTRICT-03", "CONTACT-01")
            for prefix in ("REQ", "DEC", "GATE", "EXEC")
        ],
        "CHECK-SOC2:C1.1": ["SCHEDULE-01", "INVENTORY-01", "LIFECYCLE-01"],
        "CHECK-SOC2:CC6.7": [
            "CONFIG-01",
            "GATE-OPS-01",
            "EXEC-OPS-01",
            "ACK-OPS-01",
            "EXEC-AUTH-03",
            "MONITOR-01",
        ],
        "IMPLEMENTATION": ["SCHEDULE-01", "AP-TECH-01", "AP-SEC-01", "CONFIG-01", "EXEC-OPS-01"],
        "TOD": [
            "DELEGATION-01",
            "SCHEDULE-01",
            "INSTRUCTION-01",
            "APPLICABILITY-01",
            "CONFIG-01",
            "MONITOR-01",
        ],
        "TOE": ["INVENTORY-01", "LIFECYCLE-01", "MONITOR-01", "PERIOD-01"],
    }
    by_record = {r["record"]: r for r in refs}
    if "CACHE-MANIFEST-01" in by_record:
        selected["CHECK-HIPAA:164.508"].append("CACHE-MANIFEST-01")
    # Preserve initial configuration as well as any later containment; a successor
    # must not overwrite the configuration used for September releases.
    return {
        f"TASK-SH-DAT-002-corporate-{suffix}": [
            {k: r[k] for k in rights.ORIGINAL_FIELDS} for r in refs if r["record"] in names
        ]
        for suffix, names in selected.items()
        if all(n in by_record for n in names)
    }


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, ensure_ascii=False, indent=2)
        stream.write("\n")
    path.chmod(0o600)


def _provenance(scenario: str) -> dict:
    return {
        "source_reference": SOURCE_REFERENCE,
        "source_pins": SOURCE_PINS,
        "upstream_rights_sha256": RIGHTS_PINS,
        "history_branch": BRANCHES[scenario],
        "qualification": (
            "AUTHORED_FICTIONAL_CUSTOMER_AND_COMPANY_OPERATIONS_NO_REAL_PHI_OR_AUDIT_CREDIT"
        ),
    }


def _receipt(context: dict, records: dict) -> dict:
    return {
        "schema": SCHEMA,
        "company": COMPANY,
        "branches": BRANCHES,
        "records": records,
        "source_pins": SOURCE_PINS,
        "upstream_rights_sha256": RIGHTS_PINS,
        "native_versions_per_branch": {s: len(_expected_rows(context, s)) for s in BRANCHES},
        "selected_service_period": PERIOD,
        "selected_requests_per_branch": 23,
        "source_leads_by_task": {
            s: _lead_map(_expected_rows(context, s), records[s]) for s in BRANCHES
        },
        "prospective_distinct_dataset": DATASET,
        "prior_held_sources_changed": False,
        "enterprise_source_complete": False,
        "independent_scenario_acceptance": "PENDING",
        "actual_phi_or_ba_claim": False,
        "actual_external_communications": 0,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": LIMITS,
    }


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    destination = Path(destination).absolute()
    purpose._private(destination.parent, directory=True)
    if destination.exists() or destination.is_symlink() or destination != destination.resolve():
        raise CompanyStoreError("Fresh private DAT002 privacy destination required")
    context = _context(repository, private_repository)
    with tempfile.TemporaryDirectory(prefix=".dat002-privacy-", dir=destination.parent) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in BRANCHES.items():
            records[scenario] = []
            for system, owner in SYSTEM_OWNERS.items():
                if scenario == "MESSY" or system != "privacy_exception":
                    store.register_system(COMPANY, branch, system, owner)
            for item in _expected_rows(context, scenario):
                ref = store.append_version(
                    COMPANY,
                    branch,
                    item["system"],
                    item["record"],
                    expected_version=item["version"] - 1,
                    command_id=f"PRIVACY-{branch}-{item['record']}-V{item['version']}",
                    event_at=item["event_at"],
                    available_at=item["available_at"],
                    content=encoded(item["body"]),
                    provenance=_provenance(scenario),
                )
                if ref["sha256"] != item["sha256"]:
                    raise CompanyStoreError("Privacy native serialization differs")
                records[scenario].append(ref)
        _write(stage / "RECEIPT.json", _receipt(context, records))
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _digest(stage / "RECEIPT.json"),
            "company_db_sha256": _digest(stage / "company.sqlite3"),
            "module_sha256": _digest(Path(__file__)),
            "native_version_count": sum(len(r) for r in records.values()),
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return manifest


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    root = purpose._private(destination, directory=True)
    paths = {
        "manifest": root / "MANIFEST.json",
        "receipt": root / "RECEIPT.json",
        "database": root / "company.sqlite3",
    }
    if {p.name for p in root.iterdir()} != {"MANIFEST.json", "RECEIPT.json", "company.sqlite3"}:
        raise CompanyStoreError("Exact private three-file privacy source required")
    before = purpose._frozen(paths)
    manifest = json.loads(paths["manifest"].read_text())
    receipt = json.loads(paths["receipt"].read_text())
    context = _context(repository, private_repository)
    expected_rows = {s: _expected_rows(context, s) for s in BRANCHES}
    count = sum(len(rows) for rows in expected_rows.values())
    if (
        manifest
        != {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": before["receipt"][-1],
            "company_db_sha256": before["database"][-1],
            "module_sha256": _digest(Path(__file__)),
            "native_version_count": count,
            "audit_task_credit": False,
        }
        or set(receipt.get("records", {})) != set(BRANCHES)
        or receipt != _receipt(context, receipt["records"])
    ):
        raise CompanyStoreError("Privacy manifest/receipt boundary differs")
    with closing(
        sqlite3.connect(paths["database"].as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        systems = {
            (COMPANY, branch, system, owner)
            for scenario, branch in BRANCHES.items()
            for system, owner in SYSTEM_OWNERS.items()
            if scenario == "MESSY" or system != "privacy_exception"
        }
        if (
            db.execute("PRAGMA quick_check").fetchone()[0] != "ok"
            or db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != count
            or {tuple(r) for r in db.execute("SELECT company,branch,system,owner FROM systems")}
            != systems
            or any(
                db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in ("grants", "collections", "access_events")
            )
        ):
            raise CompanyStoreError(
                "Privacy native integrity/custody/audit-access boundary differs"
            )
        for scenario, branch in BRANCHES.items():
            refs = receipt["records"][scenario]
            if len(refs) != len(expected_rows[scenario]):
                raise CompanyStoreError("Privacy branch source roster incomplete")
            for ref, item in zip(refs, expected_rows[scenario], strict=True):
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    (COMPANY, branch, item["system"], item["record"], item["version"]),
                ).fetchone()
                if (
                    row is None
                    or ref["company"] != COMPANY
                    or ref["branch"] != branch
                    or ref["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or ref["provenance"] != _provenance(scenario)
                    or any(
                        ref[k] != item[k]
                        for k in (
                            "system",
                            "record",
                            "version",
                            "sha256",
                            "event_at",
                            "available_at",
                        )
                    )
                    or row["content"] != encoded(item["body"])
                    or row["sha256"] != item["sha256"]
                    or row["origin"] != ref["origin"]
                    or json.loads(row["provenance"]) != _provenance(scenario)
                    or any(row[k] != ref[k] for k in ("event_at", "available_at", "imported_at"))
                    or row["available_at"] < row["event_at"]
                    or datetime.fromisoformat(row["imported_at"])
                    >= datetime.fromisoformat(row["event_at"])
                ):
                    raise CompanyStoreError("Privacy native original/provenance/clock differs")
    if purpose._frozen(paths) != before:
        raise CompanyStoreError("Privacy source changed during verification")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    args = parser.parse_args()
    result = (create if args.action == "create" else verify)(
        args.destination, repository=args.repository, private_repository=args.private_repository
    )
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
