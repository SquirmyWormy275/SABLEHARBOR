"""Read-only PBC source-request triage for the 121 unsupported V3 clauses/side."""

from __future__ import annotations

import hashlib
import json
import stat
from collections import Counter, defaultdict
from pathlib import Path

from . import documentary_283_route_reconciliation_v3 as reviewed_routes

SCHEMA = "SH_UNSUPPORTED_121_PAIRED_SOURCE_REQUEST_PLAN_V1"
LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V3_2026-09-29.json"
REVIEW = (
    "enterprise/generated/audit-suite/documentary-283-route-reconciliation-v3-2026-09-29/"
    "independent-review-v1/REVIEW.json"
)
DESIGN = "enterprise/ccf/assurance/design_data/control_procedures.json"
COMPLETION = "enterprise/ccf/assurance/completion_data/control_procedures.json"
APPOINTMENTS = (
    "docs/internal/development/audit-suite/ORGANIZATION_APPOINTMENT_PROPOSALS_2026-09-13.json"
)
PINS = {
    LEDGER: "f7549eca0957a92d442cfabb385ae9eed4509fada804a3dfea5d371cfbbf4d33",
    REVIEW: "b671d3547670b5de9c7f714d51e44b6d2e65b02502dac752464b9f36d7ca1603",
    DESIGN: "258f5c868e16f3dc197594857dc86a4f2b3ef11e3e5a36dd0a80a9fc6d40c679",
    COMPLETION: "cb5d2729e555156b3fc9845031c00c445b5d37f7bc4c0536f275ceebecabf1f6",
    APPOINTMENTS: "53681cf60e85d130d04ef79ed437e70da9b3211896e2098f049bc9ff26f54681",
}

# These are proposed routing contacts from an unaccepted organization proposal,
# not authority to decide the matter or attest that an event did not occur.
CONTACTS = {
    "SH-ASS-001": "AS-P005",
    "SH-ASS-002": "AS-P005",
    "SH-ASS-003": "AS-P009",
    "SH-ASS-004": "AS-P009",
    "SH-BCM-004": "AS-P008",
    "SH-DAT-002": "AS-P014",
    "SH-DAT-003": "AS-P014",
    "SH-ENG-005": "AS-P007",
    "SH-ERM-002": "AS-P005",
    "SH-ETH-001": "AS-P006",
    "SH-ETH-003": "AS-P006",
    "SH-ETH-004": "AS-P005",
    "SH-GOV-001": "AS-P004",
    "SH-GOV-003": "AS-P004",
    "SH-GOV-004": "AS-P004",
    "SH-IAM-005": "AS-P008",
    "SH-LEG-001": "AS-P003",
    "SH-POL-001": "AS-P005",
    "SH-POL-002": "AS-P005",
    "SH-POL-004": "AS-P005",
    "SH-PRD-002": "AS-P003",
    "SH-PRD-003": "AS-P003",
    "SH-PRD-004": "AS-P003",
    "SH-REC-002": "AS-P014",
    "SH-REC-004": "AS-P014",
    "SH-SEC-001": "AS-P008",
    "SH-SEC-003": "AS-P008",
    "SH-SEC-005": "AS-P008",
}

# Request actual originals if they exist. Each design system name remains a
# locator suggestion, never evidence that the system is deployed.
REQUESTS = {
    "SH-ASS-001": (
        "Locate selected-period owner certifications, critical-duty competence/backup "
        "checks, recurring-failure actions and second-line challenges."
    ),
    "SH-ASS-002": (
        "Locate dated second-line plan, technical and nontechnical evaluation "
        "results, change-triggered refresh and escalation."
    ),
    "SH-ASS-003": (
        "Locate approved independent engagement mandate, evaluator conflict check, "
        "performed evaluation, supervisory review and direct escalation."
    ),
    "SH-ASS-004": (
        "Locate independently selected incident/change/vendor populations, source "
        "reconciliations, samples, workpapers and description-assertion comparisons; "
        "the audit workspace alone is not company operation."
    ),
    "SH-BCM-004": (
        "Locate an authorized ePHI emergency-mode exercise, operator permissions, "
        "preserved access decisions and recovery replay; first establish "
        "legal/data-owner authority."
    ),
    "SH-DAT-002": (
        "Locate actual role/purpose/record-set decisions and scoped processing cases, "
        "customer instructions, authorizations, disclosures, rights work and "
        "underlying agreement/recipient records."
    ),
    "SH-DAT-003": (
        "Locate approved retention/hold schedule and original retired-media custody, "
        "sanitization method, verification and release authority."
    ),
    "SH-ENG-005": (
        "Locate selected normal and emergency deployed-change populations with "
        "requirements, security tests, independent approvals, deployment checks and "
        "rollback records."
    ),
    "SH-ERM-002": (
        "Locate approved measurable risk appetite, service commitments, tolerances, "
        "thresholds and dated escalation decisions."
    ),
    "SH-ETH-001": (
        "Locate selected substantiated cases, reasoned sanctions, follow-up and "
        "responsibility-related performance review, or a supported no-case population "
        "decision."
    ),
    "SH-ETH-003": (
        "Locate restricted case population, regulator correspondence if triggered, "
        "investigation disposition, sanctions and anti-retaliation follow-up, or "
        "supported no-event decisions."
    ),
    "SH-ETH-004": (
        "Locate actual override/dishonest-reporting fraud scenarios, "
        "mitigation/review and qualified conflict disposition; the one synthetic "
        "affiliation indicator is insufficient."
    ),
    "SH-GOV-001": (
        "Locate current charter/composition and dated governing minutes challenging a "
        "selected control failure, with conflicts and decision authority."
    ),
    "SH-GOV-003": (
        "Locate reserved matters, effective delegation, actual "
        "security-official/hybrid-entity decisions if legally required, and "
        "cross-site escalation to oversight."
    ),
    "SH-GOV-004": (
        "Locate current director conflict declarations, independence/eligibility "
        "assessments, recusals and minutes challenging a control failure."
    ),
    "SH-IAM-005": (
        "Locate deployed human and service trust-boundary permissions, protected "
        "credentials, privileged path and authorized ePHI emergency exercise; local "
        "inert-object trace is insufficient."
    ),
    "SH-LEG-001": (
        "Locate provision-level current authority and qualified "
        "entity/function/applicability decisions; separately enumerate any "
        "regulator/enforcement/proceeding matters and originals or support a no-event "
        "review."
    ),
    "SH-POL-001": (
        "Locate effective policy versions, approval/distribution and "
        "supersession/retention execution, delegated HIPAA/privacy steps and any "
        "external notice/receipt."
    ),
    "SH-POL-002": (
        "Locate accepted policy/control authority, security-official appointment if "
        "required, cross-site delegation and risk-to-control conflict resolution."
    ),
    "SH-POL-004": (
        "Locate one effective policy-to-procedure trigger, responsible person, dated "
        "execution, exception and correction."
    ),
    "SH-PRD-002": (
        "Locate actual approved customer commitments, recipient/contact population, "
        "issued responsibility information, external concern receipt and response."
    ),
    "SH-PRD-003": (
        "Locate actual customer-impacting change, contractual notice decision, "
        "complete recipients, issued notices, delivery/receipt and response."
    ),
    "SH-PRD-004": (
        "Locate actual support/concern population, external receipt/response, "
        "escalation, validated correction and original omission history."
    ),
    "SH-REC-002": (
        "Locate independent activity/extraction denominator and any actual regulator "
        "demand, preserved source access, response authority and production, or "
        "supported no-demand decision."
    ),
    "SH-REC-004": (
        "Locate physical movement/retired-media population, holds, pre-movement copy, "
        "custody, provider handoff, sanitization verification and release."
    ),
    "SH-SEC-001": (
        "Locate deployed two-site architecture, addressable decisions, "
        "trust/transfer/physical/environmental tests, supplier components and owner "
        "review against the exact selected population."
    ),
    "SH-SEC-003": (
        "Locate full asset/scan/baseline populations and one detected drift/new "
        "vulnerability through triage, correction and retest."
    ),
    "SH-SEC-005": (
        "Locate actual ingress/egress, remote administration, endpoint "
        "installation/update and detection populations; test denied paths/executables "
        "and exceptions."
    ),
}

LEGAL_DECISION_CONTROLS = {"SH-BCM-004", "SH-DAT-002", "SH-DAT-003", "SH-REC-004"}
LEGAL_DECISION_TASK_IDS = {
    "TASK-SH-ETH-003-corporate-ACTION-H-REGULATOR",
    "TASK-SH-GOV-003-corporate-ACTION-H-SECURITY-OFFICIAL",
    "TASK-SH-GOV-003-corporate-CHECK-HIPAA:164.105",
    "TASK-SH-POL-001-corporate-ACTION-H-RETENTION",
    "TASK-SH-POL-001-corporate-ACTION-S-COMMUNICATION",
    "TASK-SH-POL-001-corporate-CHECK-HIPAA:164.530",
    "TASK-SH-POL-002-corporate-ACTION-H-SECURITY-OFFICIAL",
    "TASK-SH-SEC-001-corporate-ACTION-H-ADDRESSABLE",
    "TASK-SH-REC-002-corporate-ACTION-H-REGULATOR",
}
QUALIFIED_OWNER_DECISION_CONTROLS = {
    "SH-ASS-003",
    "SH-ASS-004",
    "SH-ENG-005",
    "SH-ERM-002",
    "SH-ETH-004",
    "SH-GOV-001",
    "SH-GOV-004",
    "SH-IAM-005",
    "SH-PRD-003",
    "SH-PRD-002",
    "SH-PRD-004",
    "SH-SEC-001",
    "SH-POL-001",
    "SH-POL-002",
}
QUALIFIED_OWNER_TASK_IDS = {
    "TASK-SH-ETH-001-corporate-ACTION-H-SANCTIONS",
    "TASK-SH-ETH-003-corporate-ACTION-H-SANCTIONS",
    "TASK-SH-GOV-003-corporate-CHECK-SOC2:CC1.3",
}
EXTERNAL_TASK_IDS = {
    "TASK-SH-DAT-002-corporate-ACTION-H-RIGHTS-ASSISTANCE",
    "TASK-SH-DAT-002-corporate-CHECK-HIPAA:164.506",
    "TASK-SH-DAT-002-corporate-CHECK-HIPAA:164.510",
    "TASK-SH-DAT-002-corporate-CHECK-HIPAA:164.512",
    "TASK-SH-DAT-002-corporate-CHECK-HIPAA:164.522",
    "TASK-SH-ETH-003-corporate-ACTION-H-REGULATOR",
    "TASK-SH-POL-001-corporate-ACTION-S-COMMUNICATION",
    "TASK-SH-PRD-002-corporate-ACTION-S-COMMUNICATION",
    "TASK-SH-PRD-003-corporate-ACTION-S-COMMUNICATION",
    "TASK-SH-PRD-004-corporate-ACTION-S-COMMUNICATION",
    "TASK-SH-REC-002-corporate-ACTION-H-REGULATOR",
    "TASK-SH-SEC-001-corporate-CHECK-SOC2:CC6.4",
    "TASK-SH-SEC-001-corporate-CHECK-SOC2:CC6.7",
}
CONDITIONAL_EXTERNAL_TASK_IDS = {
    "TASK-SH-DAT-003-corporate-CHECK-SOC2:CC6.5",
    "TASK-SH-REC-004-corporate-ACTION-H-PHYSICAL-MOVEMENT",
    "TASK-SH-REC-004-corporate-CHECK-SOC2:CC6.5",
}
NONOCCURRENCE_CANDIDATE_TASK_IDS = {
    "TASK-SH-ETH-001-corporate-ACTION-H-SANCTIONS",
    "TASK-SH-ETH-003-corporate-ACTION-H-REGULATOR",
    "TASK-SH-ETH-003-corporate-ACTION-H-SANCTIONS",
    "TASK-SH-PRD-004-corporate-ACTION-S-COMMUNICATION",
    "TASK-SH-REC-002-corporate-ACTION-H-REGULATOR",
    "TASK-SH-REC-004-corporate-ACTION-H-PHYSICAL-MOVEMENT",
    "TASK-SH-REC-004-corporate-CHECK-SOC2:CC6.5",
}
LEGAL_CONTEXT_TASK_IDS = {
    "TASK-SH-LEG-001-corporate-CHECK-HIPAA:160.300",
    "TASK-SH-LEG-001-corporate-CHECK-HIPAA:160.302",
    "TASK-SH-LEG-001-corporate-CHECK-HIPAA:160.400",
    "TASK-SH-LEG-001-corporate-CHECK-HIPAA:160.500",
}
LEGAL_EXTERNAL_IF_RELIED_ON_TASK_IDS = {
    "TASK-SH-LEG-001-corporate-CHECK-HIPAA:160.204",
}
LIMITS = [
    "Request plan only: no company source, external message, legal opinion, "
    "task command or audit collection was created.",
    "The 2027 fictional source roster is not an actual 2027 operating year as of 2026-09-29.",
    "Proposed systems and named contacts are locator leads, not deployed "
    "systems or accepted decision authority.",
    "Nonoccurrence is never inferred from an empty fictional fixture; it "
    "requires a bounded population, attributable owner statement and "
    "independent challenge.",
    "Every unsupported task remains NOT_STARTED/NOT_RUN with no N/A or audit credit.",
]


class SourceRequestError(ValueError):
    """A reviewed clause, source route or no-credit boundary changed."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pinned(path: Path, expected: str, private: bool = False) -> object:
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise SourceRequestError("Pinned input alias forbidden")
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise SourceRequestError("Pinned input must be an ordinary single-link file")
    if private and stat.S_IMODE(before.st_mode) != 0o600:
        raise SourceRequestError("Private input mode differs")
    raw = path.read_bytes()
    after = path.stat()

    def identity(info) -> tuple[int, int, int, int, int]:
        return (
            info.st_dev,
            info.st_ino,
            info.st_size,
            info.st_mtime_ns,
            stat.S_IMODE(info.st_mode),
        )

    if (
        hashlib.sha256(raw).hexdigest() != expected
        or identity(before) != identity(after)
        or _sha(path) != expected
    ):
        raise SourceRequestError(f"Pinned input differs: {path}")
    return json.loads(raw)


def _is_legal_matter(row: dict) -> bool:
    return (
        row["control_id"] == "SH-LEG-001"
        and row["task_id"] not in LEGAL_CONTEXT_TASK_IDS
        and row["source_limit"].startswith("Triggered regulator/enforcement/proceeding facts")
    )


def _group(row: dict) -> str:
    if row["control_id"] != "SH-LEG-001":
        return row["control_id"]
    if row["task_id"] in LEGAL_CONTEXT_TASK_IDS:
        return "SH-LEG-001/CONTEXT"
    return "SH-LEG-001/MATTER" if _is_legal_matter(row) else "SH-LEG-001/PROVISION"


def _request_text(row: dict) -> str:
    if row["control_id"] != "SH-LEG-001":
        return REQUESTS[row["control_id"]]
    if row["task_id"] in LEGAL_CONTEXT_TASK_IDS:
        return (
            "Locate qualified source-status classification for enforcement and "
            "proceeding provisions, including the reserved entry. Retain the "
            "case playbook as conditional; do not invent a matter or recurring "
            "technical duty."
        )
    if _is_legal_matter(row):
        return (
            "Locate the selected-period counsel-controlled regulator/enforcement/"
            "proceeding population and original notices, demands, orders, deadlines, "
            "responses and dispositions if triggered. Otherwise request an "
            "owner-supported and independently challenged no-matter determination."
        )
    return (
        "Locate current provision-level primary authority, effective/legal-status "
        "overlay, entity/function facts and qualified counsel applicability decisions; "
        "do not substitute the historical XML or synthetic contract calendar."
    )


def _lanes(row: dict) -> tuple[list[str], bool]:
    task_id, cid = row["task_id"], row["control_id"]
    if cid == "SH-LEG-001":
        if _is_legal_matter(row):
            return [
                "EXTERNAL_AUTHORITY_RESPONSE_IF_TRIGGERED",
                "QUALIFIED_LEGAL_APPLICABILITY_DECISION",
                "SUPPORTED_NONOCCURRENCE_REVIEW_IF_NO_CASE",
            ], True
        lanes = ["QUALIFIED_LEGAL_APPLICABILITY_DECISION"]
        if task_id in LEGAL_EXTERNAL_IF_RELIED_ON_TASK_IDS:
            lanes.append("EXTERNAL_AUTHORITY_RESPONSE_IF_RELIED_ON")
        return lanes, False
    lanes = ["MISSING_COMPANY_OPERATION"]
    if cid in LEGAL_DECISION_CONTROLS or task_id in LEGAL_DECISION_TASK_IDS:
        lanes.append("QUALIFIED_LEGAL_APPLICABILITY_DECISION")
    elif cid in QUALIFIED_OWNER_DECISION_CONTROLS or task_id in QUALIFIED_OWNER_TASK_IDS:
        lanes.append("QUALIFIED_OWNER_AUTHORITY_DECISION")
    if task_id in EXTERNAL_TASK_IDS:
        lanes.append("EXTERNAL_COUNTERPARTY_RESPONSE")
    if task_id in CONDITIONAL_EXTERNAL_TASK_IDS:
        lanes.append("EXTERNAL_COUNTERPARTY_RESPONSE_IF_OUTSOURCED")
    nonoccurrence = task_id in NONOCCURRENCE_CANDIDATE_TASK_IDS
    if nonoccurrence:
        lanes.append("SUPPORTED_NONOCCURRENCE_REVIEW_IF_NO_EVENT")
    return lanes, nonoccurrence


def build(repository: Path, private_repository: Path) -> dict:
    """Join reviewed exact clauses to source-request queues without audit writes."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    values = {
        rel: _pinned((private if rel == REVIEW else repository) / rel, digest, rel == REVIEW)
        for rel, digest in PINS.items()
    }
    ledger, review = values[LEDGER], values[REVIEW]
    if (
        review.get("verdict") != "PASS_READ_ONLY_PARTIAL_ROUTE_RECONCILIATION"
        or review.get("tracked_sha256", {}).get("ledger_json") != PINS[LEDGER]
        or ledger.get("audit_task_credit") is not False
        or ledger.get("active_pair_mutated") is not False
    ):
        raise SourceRequestError("V3 independent review/ledger authority differs")
    if reviewed_routes.build(repository, private) != ledger:
        raise SourceRequestError("V3 source-route ledger does not reproduce")
    appointments = values[APPOINTMENTS]
    if appointments.get("repository_acceptance_status") != "PROPOSED_NOT_ACCEPTED_CANON":
        raise SourceRequestError("Proposed contact authority changed")
    people = {person["person_id"]: person for person in appointments["people"]}
    controls = {
        row["control_id"]: (source, row)
        for source in (DESIGN, COMPLETION)
        for row in values[source]
    }
    unsupported = [
        row for row in ledger["rows"] if row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
    ]
    if (
        len(unsupported) != 242
        or Counter(row["side"] for row in unsupported) != {"A": 121, "B": 121}
        or {row["control_id"] for row in unsupported} != set(CONTACTS)
        or set(CONTACTS) != set(REQUESTS)
        or any(cid not in controls for cid in CONTACTS)
        or any(person_id not in people for person_id in CONTACTS.values())
    ):
        raise SourceRequestError("Exact 121/side source-request population differs")
    task_ids = {row["task_id"] for row in unsupported}
    if (
        not (
            EXTERNAL_TASK_IDS
            | CONDITIONAL_EXTERNAL_TASK_IDS
            | NONOCCURRENCE_CANDIDATE_TASK_IDS
            | LEGAL_DECISION_TASK_IDS
            | QUALIFIED_OWNER_TASK_IDS
            | LEGAL_CONTEXT_TASK_IDS
            | LEGAL_EXTERNAL_IF_RELIED_ON_TASK_IDS
        )
        <= task_ids
    ):
        raise SourceRequestError("Declared route-specific gate escaped unsupported population")
    rows = []
    groups = defaultdict(list)
    owner_sources = defaultdict(list)
    for source_row in unsupported:
        row = dict(source_row)
        cid, side = row["control_id"], row["side"]
        group = _group(row)
        source_file, procedure = controls[cid]
        contact = people[CONTACTS[cid]]
        lanes, possible_nonoccurrence = _lanes(row)
        request = {
            "side": side,
            "family": row["family"],
            "control_id": cid,
            "task_id": row["task_id"],
            "procedure_type": row["procedure_type"],
            "authored_test_clause": row["authored_test_clause"],
            "screen_row_sha256": row["screen_row_sha256"],
            "requirement_ids": row["requirement_ids"],
            "remaining_test_gate": row["remaining_test_gate"],
            "v3_source_limit": row["source_limit"],
            "v3_candidate_native_leads": row["candidate_or_design_source_ids"],
            "v3_targeted_source_ids": row["targeted_integrated_source_ids"],
            "request_group_id": group,
            "proposed_system_of_record": procedure["proposed_system_of_record"],
            "system_status": "DESIGN_LOCATOR_ONLY_NOT_VERIFIED_DEPLOYED",
            "system_design_source": source_file,
            "candidate_contact_person_id": contact["person_id"],
            "candidate_contact_title": contact["title"],
            "contact_status": "PROPOSED_NOT_ACCEPTED_DECISION_AUTHORITY",
            "requested_originals_or_decision": _request_text(row),
            "source_request_lanes": lanes,
            "external_request_status": (
                "NOT_SENT_NOT_RECEIVED"
                if any(lane.startswith("EXTERNAL_") for lane in lanes)
                else "NO_EXTERNAL_REQUEST_DEFINED"
            ),
            "qualified_decision_status": (
                "NOT_PROVIDED"
                if any(lane.startswith("QUALIFIED_") for lane in lanes)
                else "NO_QUALIFIED_DECISION_REQUEST_DEFINED"
            ),
            "accepted_nonoccurrence_candidate": possible_nonoccurrence,
            "accepted_nonoccurrence_status": (
                "NOT_ESTABLISHED" if possible_nonoccurrence else "NO_NONOCCURRENCE_PATH_DEFINED"
            ),
            "pbc_request_status": "DRAFT_NOT_SENT",
            "current_task_status": "NOT_STARTED",
            "current_task_conclusion": "NOT_RUN",
            "actual_operation_eligibility_as_of_packet": False,
            "task_credit": False,
        }
        if (
            row["authored_test_clause"] is None
            or row["current_status"] != "NOT_STARTED"
            or row["current_conclusion"] != "NOT_RUN"
            or row["audit_task_credit"] is not False
        ):
            raise SourceRequestError("Unsupported authored task/no-credit boundary differs")
        rows.append(request)
        groups[group].append(request)
        owner_sources[(contact["person_id"], procedure["proposed_system_of_record"])].append(
            request
        )
    leg = [row for row in rows if row["control_id"] == "SH-LEG-001" and row["side"] == "A"]
    if Counter(row["request_group_id"] for row in leg) != {
        "SH-LEG-001/MATTER": 46,
        "SH-LEG-001/CONTEXT": 4,
        "SH-LEG-001/PROVISION": 16,
    }:
        raise SourceRequestError("Legal status/triggered-matter split differs")
    group_rows = [
        {
            "request_group_id": group,
            "control_id": selected[0]["control_id"],
            "candidate_contact_person_id": selected[0]["candidate_contact_person_id"],
            "proposed_system_of_record": selected[0]["proposed_system_of_record"],
            "requested_originals_or_decision": selected[0]["requested_originals_or_decision"],
            "task_ids_per_side": {
                side: sorted(row["task_id"] for row in selected if row["side"] == side)
                for side in "AB"
            },
            "routes_per_side": len([row for row in selected if row["side"] == "A"]),
            "request_status": "DRAFT_NOT_SENT",
            "task_credit": False,
        }
        for group, selected in sorted(groups.items())
    ]
    owner_queues = [
        {
            "candidate_contact_person_id": owner,
            "proposed_system_of_record": system,
            "task_ids_per_side": {
                side: sorted(row["task_id"] for row in selected if row["side"] == side)
                for side in "AB"
            },
            "request_group_ids": sorted({row["request_group_id"] for row in selected}),
        }
        for (owner, system), selected in sorted(owner_sources.items())
    ]
    counts = {
        side: {
            "unsupported_exact_clauses": 121,
            "controls": 28,
            "request_groups": len(group_rows),
            "lane_mentions": dict(
                sorted(
                    Counter(
                        lane
                        for row in rows
                        if row["side"] == side
                        for lane in row["source_request_lanes"]
                    ).items()
                )
            ),
            "accepted_nonoccurrence_candidates": sum(
                row["accepted_nonoccurrence_candidate"] for row in rows if row["side"] == side
            ),
            "accepted_nonoccurrence_determinations": 0,
            "by_family": dict(
                sorted(Counter(row["family"] for row in rows if row["side"] == side).items())
            ),
        }
        for side in "AB"
    }
    if counts["A"] != counts["B"] or len(group_rows) != 30:
        raise SourceRequestError("Paired source-request groups diverged")
    return {
        "schema": SCHEMA,
        "as_of": "2026-09-29",
        "source_pins": PINS,
        "counts": counts,
        "rows": sorted(rows, key=lambda row: (row["side"], row["control_id"], row["task_id"])),
        "request_groups": group_rows,
        "candidate_owner_source_queues": owner_queues,
        "nonoccurrence_acceptance_protocol": [
            "Define the selected-period event population and independent search "
            "locations before claiming zero events.",
            "Retain dated source extracts, availability clocks and an attributable "
            "authorized owner statement.",
            "Have an independent qualified reviewer challenge completeness, routing "
            "and known exceptions.",
            "Until accepted, retain NOT_ESTABLISHED, NOT_STARTED/NOT_RUN and no "
            "task credit; do not convert to N/A.",
        ],
        "limits": LIMITS,
        "external_messages_sent": 0,
        "fresh_pair_created": False,
        "audit_task_credit": False,
        "active_pair_mutated": False,
    }


def markdown(result: dict) -> str:
    """Summarize request queues while the JSON preserves each exact clause."""
    count = result["counts"]["A"]
    lines = [
        "# Unsupported exact clauses: PBC/source-request plan",
        "",
        "This is a read-only request plan over the independently reviewed "
        "21-source V3 route ledger. It lists all 121 unsupported authored clauses "
        "on each audit side, grouped by proposed source locator and candidate "
        "contact. The [paired JSON](UNSUPPORTED_121_PBC_PLAN_2026-09-29.json) "
        "preserves each exact task ID, clause, source limit, request lane and "
        "no-credit state. No request was sent.",
        "",
        "The design procedure's system name is a locator suggestion, not a "
        "verified deployed company system. Named contacts come from an unaccepted "
        "organization proposal and are not automatically authorized decision "
        "makers. Future fictional 2027 events are not actual operation as of "
        "2026-09-29.",
        "",
        "| Per-side denominator | Count |",
        "| --- | ---: |",
        f"| Unsupported exact clauses | {count['unsupported_exact_clauses']} |",
        f"| Affected controls | {count['controls']} |",
        f"| Request groups | {count['request_groups']} |",
        "| Possible no-event reviews, none accepted | "
        f"{count['accepted_nonoccurrence_candidates']} |",
        "",
        "Request lanes overlap because a clause can need both company originals "
        "and a qualified decision, or an outside response if a matter was "
        "triggered. Counts below are lane mentions, not satisfied tasks:",
        "",
        "| Request lane | Clauses per side |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {lane} | {value} |" for lane, value in count["lane_mentions"].items())
    lines += [
        "",
        "The legal-obligation control accounts for 66 per side: 16 provision/"
        "status decisions, four source-context clauses, and 46 actual-matter "
        "clauses. The latter need a complete, counsel-controlled matter "
        "population. If no "
        "qualifying matter exists, an attributable owner statement and independent "
        "challenge are still pending; an empty simulated fixture is not accepted "
        "nonoccurrence or N/A.",
        "",
        "| Candidate contact | Proposed source locator | Clauses per side | Request groups |",
        "| --- | --- | ---: | --- |",
    ]
    for queue in result["candidate_owner_source_queues"]:
        lines.append(
            f"| {queue['candidate_contact_person_id']} | {queue['proposed_system_of_record']} | "
            f"{len(queue['task_ids_per_side']['A'])} | "
            f"{', '.join(queue['request_group_ids'])} |"
        )
    lines += [
        "",
        "External responses remain `NOT_SENT_NOT_RECEIVED`. Qualified legal, "
        "Board, data-owner, security and independent assurance decisions remain "
        "unprovided. Original 2027 company activity, accepted no-event decisions, "
        "complete populations and ordinary audit procedures must be established "
        "separately. All 242 paired task rows remain `NOT_STARTED`/`NOT_RUN` with "
        "no N/A or audit credit; the active pair, Key, Atlas and workpapers were "
        "not changed.",
        "",
    ]
    return "\n".join(lines)
