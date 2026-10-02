"""Selected B06 legal and provider documentary examinations.

Actual ordinary collected bytes/receipts/current clock only. Recorded fictional
legal judgments, contract terms and response exercises remain separate from
qualified source interpretation, live enforcement and professional assurance.
No company database, recipe, source path or cached audit outcome is read.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from . import source_legal_intake_methods as intake
from .company_store import _time
from .fresh_sec003_procedure import CLOCK_ID, NATIVE_ID, require
from .inference import _json

CONTRACT_PATH = Path(__file__).with_name("source_legal_provider_method_contracts_v1.json")
CONTRACT_SHA256 = "28f75fc34b3feb34785c1c5fdc2e35e8731fd58844eb300a0c887402fae560ff"
INTAKE_SHA256 = "2d9c7cd9c42646fcbd32b0fd012b095fa5c7cda79f694034b314ec8d0cfcb281"
FAMILIES = set(
    (
        "leg001docket legprovision legint legaloriginals addressabledocket"
        " contract phi_ba provider provider-history transition "
        "supplementalops dat002rights privacyops processing assuranceops"
    ).split()
)
ARRAY_ROLES = set()
SHA = re.compile(r"[0-9a-f]{64}\Z")
BOOLEAN_FIELDS = set(
    (
        "actual_phi outside_message_sent real_contract_executed "
        "real_hipaa_applicability real_world_operation "
        "real_world_legal_approval real_signature_or_agreement "
        "fixture_contains_real_phi real_external_signature "
        "actual_real_world_phi_processing real_world_provider_operation "
        "external_request_sent external_response_received "
        "real_external_representation new_contract_executed "
        "owner_attests_selected_source_enumeration "
        "owner_attests_preliminary_service_mapping "
        "statutory_applicability_decided actual_cure_completed "
        "actual_owner_approval actual_legal_approval actual_risk_waiver "
        "source_complete late_backfill contract_executed_in_simulation "
        "exception_open fictional_in_universe_contract_executed "
        "fictional_in_universe_operating_release real_signed_instrument "
        "current_effective hold actual_deletion accepted_amendment "
        "accounting_complete complete_record_population "
        "record_copy_prepared premature_no_record_mark copy_sent "
        "actual_external_message official_regulator_notice exercise_only "
        "available actual_operation actual_trigger "
        "qualified_review_verified full_company_population closed "
        "waiver_granted notice_sent authority_verified actual_phi_payload "
        "real_phi_payload real_world_processing_or_transfer "
        "real_world_personal_data real_world_processing_or_transfer "
        "actual_ephi_process"
    ).split()
)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def integer(value, label, *, positive=False):
    require(type(value) is int and value >= int(positive), "Strict integer " + label + " required")
    return value


def tokens(value, label):
    require(
        isinstance(value, list)
        and all(isinstance(v, str) and v for v in value)
        and len(set(value)) == len(value),
        "Distinct explicit " + label + " required",
    )
    return set(value)


def strict_fields(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in BOOLEAN_FIELDS and child is not None:
                # Native legal overlays explicitly preserve undetermined real
                # HIPAA applicability. This exact declaration is not Boolean
                # support, a fictional applicability decision, or legal credit.
                if key == "real_hipaa_applicability" and child == "UNDETERMINED":
                    continue
                # usable_JSON is also an actual parsed document in recovery records.
                if key != "usable_JSON" or not isinstance(child, dict):
                    require(type(child) is bool, "Strict Boolean field " + key + " required")
            strict_fields(child)
    elif isinstance(value, list):
        for child in value:
            strict_fields(child)


def identity(source):
    return tuple(source[k] for k in NATIVE_ID)


def refs(value, path="$"):
    if isinstance(value, dict):
        if set(NATIVE_ID) <= value.keys():
            yield path, value
        else:
            for name, child in value.items():
                yield from refs(child, path + "." + name)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from refs(child, f"{path}[{index}]")


class History:
    """Typed native custody and date-effective joins, never a source fetcher."""

    def __init__(self, records, as_of):
        self.as_of, self.rows, self.index, self.links = _time(as_of), [], {}, []
        now = _time(datetime.now(UTC).isoformat())
        for record in records:
            source, receipt = record["source"], record["receipt"]
            require(set(CLOCK_ID) <= source.keys(), "Exact native clocks required")
            require(
                type(source["version"]) is int
                and source["version"] > 0
                and all(isinstance(source[k], str) and source[k] for k in NATIVE_ID[:-1])
                and isinstance(source["sha256"], str)
                and SHA.fullmatch(source["sha256"]),
                "Strict native identity/version/hash required",
            )
            require(
                source["event_at"] is not None
                and _time(source["event_at"]) <= _time(source["available_at"]) <= self.as_of
                and _time(source["imported_at"]) <= now,
                "Selected source chronology exceeds examination clock",
            )
            raw = record.get("retained_bytes", record.get("content"))
            require(isinstance(raw, bytes), "Actual retained bytes required")
            require(
                type(receipt["source"].get("version")) is int
                and all(receipt["source"].get(k) == source[k] for k in CLOCK_ID)
                and type(receipt.get("content_bytes")) is int
                and receipt["content_bytes"] == len(raw)
                and all(
                    isinstance(receipt.get(k), str) and receipt[k]
                    for k in ("engagement_id", "principal_id", "command_id")
                )
                and _time(source["available_at"]) <= _time(receipt["simulated_as_of"]) <= self.as_of
                and _time(source["imported_at"]) <= _time(receipt["collected_at"]) <= now,
                "Ordinary receipt identity/count/clocks differ",
            )
            require(
                sha(raw) == source["sha256"] == record["artifact_sha256"],
                "Retained artifact hash differs",
            )
            require(
                isinstance(record.get("artifact_id"), str) and record["artifact_id"],
                "Actual artifact identity required",
            )
            family, role = source["system"].split(".", 1)
            require(
                family in FAMILIES
                and record.get("logical_family") == family
                and record.get("logical_system") == role,
                "Native business routing differs",
            )
            media = record.get("content_type", source.get("provenance", {}).get("content_type"))
            require(media == "application/json", "Typed B06 JSON original required")
            document = _json(raw)
            require(
                isinstance(document, list if (family, role) in ARRAY_ROLES else dict),
                "Business document type differs from native role",
            )
            strict_fields(document)
            if isinstance(document, dict):
                for field in (
                    "real_phi_payload",
                    "real_world_processing_or_transfer",
                    "real_world_operation",
                    "real_world_personal_data",
                    "fixture_contains_real_phi",
                ):
                    if field in document:
                        require(
                            document[field] is False,
                            "Fictional nonpersonal source boundary differs",
                        )
                for field in ("event_at", "available_at"):
                    if field in document:
                        require(
                            _time(document[field]) == _time(source[field]),
                            "Business publication clock differs from native source",
                        )
            if isinstance(document, dict) and ("record" in document or "record_id" in document):
                require(
                    document.get("record", document.get("record_id")) == source["record"],
                    "Business record identity differs from native custody",
                )
            key = identity(source)
            require(key not in self.index, "Duplicate collected native version")
            row = {
                **{k: v for k, v in record.items() if k != "document"},
                "retained_bytes": raw,
                "content_type": media,
                "document": document,
                "family": family,
                "role": role,
            }
            self.rows.append(row)
            self.index[key] = row
        require(self.rows, "Collected B06 originals required")
        require(
            len({(r["source"]["company"], r["source"]["branch"]) for r in self.rows}) == 1
            and len(
                {(r["receipt"]["engagement_id"], r["receipt"]["principal_id"]) for r in self.rows}
            )
            == 1,
            "One company/branch/engagement/performer required",
        )
        for row in self.rows:
            for path, ref in refs(row["document"]):
                target, status = self.resolve(ref, at=row["source"]["event_at"])
                self.links.append(
                    {
                        "from_artifact_id": row["artifact_id"],
                        "locator": path,
                        "reference": ref,
                        "status": status,
                        "target_artifact_id": target["artifact_id"] if target else None,
                    }
                )

    def select(self, family, roles=None):
        return sorted(
            (
                r
                for r in self.rows
                if r["family"] == family and (roles is None or r["role"] in roles)
            ),
            key=lambda r: (r["source"]["event_at"], r["source"]["record"], r["source"]["version"]),
        )

    def resolve(self, ref, *, at=None):
        require(
            isinstance(ref, dict)
            and set(NATIVE_ID) <= ref.keys()
            and type(ref["version"]) is int
            and ref["version"] > 0,
            "Strict native dependency required",
        )
        if ref.get("status") == "RESTRICTED_UNREGISTERED_DEPENDENCY":
            require(
                ref.get("event_at") is None
                and "sha256" not in ref
                and isinstance(ref.get("custody_id"), str)
                and ref["custody_id"],
                "Restricted witness cannot impersonate native custody",
            )
            return None, "RESTRICTED_ORIGINAL_NOT_COLLECTED"
        if (ref["company"], ref["branch"]) != (
            self.rows[0]["source"]["company"],
            self.rows[0]["source"]["branch"],
        ):
            return None, "OUTSIDE_COLLECTED_BRANCH_AUTHORITY"
        require(
            set(CLOCK_ID) - {"imported_at"} <= ref.keys(), "Exact dependency hash/clocks required"
        )
        target = self.index.get(identity(ref))
        if target is None:
            return None, "ORIGINAL_NOT_COLLECTED"
        fields = set(CLOCK_ID) if "imported_at" in ref else set(CLOCK_ID) - {"imported_at"}
        require(all(ref[k] == target["source"][k] for k in fields), "Dependency hash/clocks differ")
        if at is not None and _time(target["source"]["available_at"]) > _time(at):
            return target, "UNAVAILABLE_AT_OPERATION"
        return target, "EXACT_COLLECTED_ORIGINAL"

    def shorthand(self, token, *, at=None):
        require(
            isinstance(token, str) and len(token.split("/")) == 3,
            "Explicit source shorthand required",
        )
        role, record, version = token.split("/")
        require(version.isdecimal() and int(version) > 0, "Positive shorthand version required")
        candidates = [
            r
            for r in self.select("supplementalops", {role})
            if r["source"]["record"] == record and r["source"]["version"] == int(version)
        ]
        if not candidates:
            return None, "ORIGINAL_NOT_COLLECTED"
        row = candidates[0]
        if at is not None and _time(row["source"]["available_at"]) > _time(at):
            return row, "UNAVAILABLE_AT_OPERATION"
        return row, "EXACT_COLLECTED_ORIGINAL"


def evidence(row, locator="$"):
    return {"artifact_id": row["artifact_id"], "sha256": row["artifact_sha256"], "locator": locator}


def observation(name, facts, rows=(), *, failure=False, limited=False, locator="$"):
    return {
        "id": name,
        "facts": facts,
        "status": "EXCEPTION"
        if failure
        else "LIMITATION"
        if limited
        else "CORROBORATED_SELECTED_ATTRIBUTE",
        "evidence": [evidence(r, locator) for r in rows],
    }


def selected_fields(rows, fields):
    return [
        {
            "artifact_id": r["artifact_id"],
            "native": {k: r["source"][k] for k in CLOCK_ID},
            "attributes": {k: r["document"][k] for k in fields if k in r["document"]},
        }
        for r in rows
        if isinstance(r["document"], dict)
    ]


def bounded_observations(observations):
    """Preserve complete calculations/custody within the reviewed 20-citation limit."""
    out = []
    for original in observations:
        evidence = original["evidence"]
        if len(evidence) <= 20:
            out.append(original)
            continue
        parts = [evidence[start : start + 20] for start in range(0, len(evidence), 20)]
        continuation_ids = [
            "CUSTODY-" + sha(original["id"].encode()) + f"-{number}"
            for number in range(2, len(parts) + 1)
        ]
        out.append(
            {
                **original,
                "evidence": parts[0],
                "facts": {
                    **(
                        original["facts"]
                        if isinstance(original["facts"], dict)
                        else {"selected_record_facts": original["facts"]}
                    ),
                    "continued_evidence_observation_ids": continuation_ids,
                    "complete_citation_count": len(evidence),
                    "custody_part": 1,
                    "custody_part_count": len(parts),
                },
            }
        )
        for number, part in enumerate(parts[1:], 2):
            out.append(
                {
                    "id": "CUSTODY-" + sha(original["id"].encode()) + f"-{number}",
                    "status": original["status"],
                    "evidence": part,
                    "facts": {
                        "supports_complete_calculation_observation_id": original["id"],
                        "custody_part": number,
                        "custody_part_count": len(parts),
                        "complete_citation_count": len(evidence),
                    },
                }
            )
    return out


def authored_contracts():
    raw = CONTRACT_PATH.read_bytes()
    require(sha(raw) == CONTRACT_SHA256, "Exact B06 authored contract pin differs")
    value = _json(raw)
    require(
        value["task_count"] == 99 and len(value["tasks"]) == 99, "Full exact B06 vector required"
    )
    require(
        value["selected_task_ids"] == sorted(t["task_id"] for t in value["tasks"]),
        "B06 vector differs",
    )
    return value


def detail(row):
    return row["document"].get("detail", row["document"])


def native(row):
    return {k: row["source"][k] for k in CLOCK_ID}


def retained(rows):
    return [
        {"artifact_id": r["artifact_id"], "native": native(r), "recorded": r["document"]}
        for r in rows
    ]


def active(rows, at):
    """One date-effective published version per exact physical native object."""
    at, found = _time(at), {}
    for row in rows:
        if _time(row["source"]["available_at"]) > at:
            continue
        key = identity(row["source"])[:-1]
        previous = found.get(key)
        if previous is None or row["source"]["version"] > previous["source"]["version"]:
            found[key] = row
    return sorted(found.values(), key=lambda r: identity(r["source"]))


def own_links(history, rows):
    chosen = {r["artifact_id"] for r in rows}
    return [link for link in history.links if link["from_artifact_id"] in chosen]


def used_rows(history, rows):
    selected = {r["artifact_id"]: r for r in rows}
    for link in own_links(history, rows):
        target = link["target_artifact_id"]
        if target:
            selected[target] = next(r for r in history.rows if r["artifact_id"] == target)
    return list(selected.values())


def documentary(history, name, rows, *, fields=None, failure=False):
    links = own_links(history, rows)
    facts = retained(rows) if fields is None else selected_fields(rows, fields)
    return observation(
        name,
        {
            "selected_originals": facts,
            "exact_native_dependency_tests": links,
            "source_scope": "SELECTED_COLLECTED_ORIGINALS_ONLY",
            "qualified_decision_or_operating_performance_not_inferred": True,
        },
        used_rows(history, rows),
        failure=failure,
        limited=not rows or any(link["status"] != "EXACT_COLLECTED_ORIGINAL" for link in links),
    )


def context_rows(history):
    return history.select(
        "leg001docket", {"scope_decision", "reconciliation", "change_watch", "matter_watch"}
    ) + history.select("legprovision", {"overlay_reconciliation", "obligation_snapshot"})


# These are explicit documentary examination attributes of the authored tests,
# not an implementation of law. No penalty amounts, statutory deadlines,
# legal category, authority or rights are supplied by this table.
CLAUSE_FIELDS = {
    "160.101": ("authority_citation", "source_edition", "category"),
    "160.102": ("entity_id", "function", "role_decision", "direct_provisions"),
    "160.103": (
        "contracting_chain",
        "on_behalf_of_flow",
        "workforce_status",
        "definition_exceptions",
    ),
    "160.104": ("final_rule", "effective_date", "compliance_date", "date_exceptions"),
    "160.105": ("modified_rule", "override_provision", "compliance_date", "date_exceptions"),
    "160.201": ("authority_citation", "preemption_analysis", "context_classification"),
    "160.202": ("state_provision", "federal_provision", "comparison_test", "comparison_facts"),
    "160.203": ("conflicting_law", "actual_exception", "supporting_law", "displacement_decision"),
    "160.204": ("written_request", "determination", "request_status", "compliance_stopped"),
    "160.205": (
        "relied_on_exception",
        "legal_factual_change",
        "revocation_monitoring",
        "reassessment",
    ),
    "160.300": ("trigger_classification", "response_playbook_ref", "case_id"),
    "160.302": ("reserved", "source_edition", "inventory_entry"),
    "160.304": ("correspondence_ref", "sender_authority", "assistance_status", "approval_status"),
    "160.306": (
        "complaint_received_at",
        "complaint_records",
        "reporter_protection",
        "regulator_correspondence",
    ),
    "160.308": (
        "notice_received_at",
        "preservation",
        "response_authority",
        "review_scope",
        "response_order",
    ),
    "160.312": (
        "notice_received_at",
        "response_at",
        "service_proof",
        "corrective_plan",
        "written_disposition",
    ),
    "160.314": (
        "subpoena_scope",
        "designated_witnesses",
        "service_proof",
        "transcript_corrections",
        "counsel_objections",
    ),
    "160.400": ("enforcement_classification", "source_edition", "trigger"),
    "160.401": ("knowledge_facts", "diligence_facts", "correction_facts", "counsel_standard"),
    "160.402": ("agency_relationship", "conduct", "contract_scope", "counsel_exposure_analysis"),
    "160.404": (
        "applicable_date",
        "tier",
        "primary_adjustment",
        "amount_authority",
        "exposure_amount",
    ),
    "160.406": (
        "failure_start",
        "failure_end",
        "affected_occurrences",
        "continuous_failure_analysis",
    ),
    "160.408": ("supporting_facts", "provenance", "privilege_handling", "mitigation_analysis"),
    "160.410": ("discovery_at", "correction_at", "secretary_extension", "defense_analysis"),
    "160.412": ("eligibility_analysis", "waiver_request", "actual_disposition", "waiver_granted"),
    "160.414": (
        "occurrence_at",
        "commencement_at",
        "applicable_authority",
        "counsel_limitations_analysis",
    ),
    "160.416": (
        "proposed_terms",
        "counsel_authority",
        "management_authority",
        "executed_settlement",
        "settlement_duties",
    ),
    "160.418": ("payment", "separate_exposure_analysis", "proceeding_dispositions"),
    "160.420": ("notice_received_at", "notice_completeness", "hearing_path", "statistical_study"),
    "160.422": (
        "hearing_deadline",
        "hearing_requested_at",
        "final_notice",
        "appeal_availability_analysis",
    ),
    "160.424": (
        "final_determination",
        "payment_offset",
        "available_remedies",
        "finance_authorization",
    ),
    "160.426": (
        "finality",
        "authorized_communication",
        "publication_authority",
        "communication_audience",
    ),
    "160.500": ("proceeding_id", "case_playbook_ref", "trigger", "context_classification"),
    "160.502": ("appellate_body", "addressee", "filing_destination"),
    "160.504": (
        "actual_receipt_at",
        "presumed_receipt_at",
        "admitted_denied_facts",
        "defense_grounds",
        "mailing_proof",
        "hearing_request_deadline",
    ),
    "160.506": ("representative_authority", "ethical_conduct", "exercised_rights", "waived_rights"),
    "160.508": ("orders", "assigned_actions", "directions_requests_split", "contested_authority"),
    "160.510": ("case_communications", "ex_parte_screen", "scheduling_status_basis"),
    "160.512": (
        "conference_at",
        "representative_authority",
        "resulting_order",
        "action_owners",
        "deadlines",
    ),
    "160.514": (
        "settlement_counterparty_authority",
        "executed_settlement",
        "alj_signature_requirement_basis",
    ),
    "160.516": (
        "discovery_request",
        "scoped_objections",
        "production",
        "protective_motion",
        "compel_motion",
        "motion_window",
    ),
    "160.518": (
        "exchange_deadline",
        "delivered_at",
        "objections",
        "extraordinary_circumstance_ruling",
    ),
    "160.520": (
        "motion",
        "opposition",
        "service_proof",
        "quash",
        "named_witnesses",
        "necessary_evidence",
        "allowed_exceptions",
    ),
    "160.522": ("subpoenaing_party", "service_package", "fee_payment", "payment_authority"),
    "160.524": (
        "actual_order",
        "filing_form",
        "mailing_at",
        "opposing_counsel_service",
        "service_proof",
    ),
    "160.526": (
        "docket",
        "federal_holidays",
        "service_method",
        "hearing_request_exception",
        "qualified_calendar",
    ),
    "160.528": ("motion", "service_at", "alj_response_deadline", "oral_motion_exception"),
    "160.530": ("missed_order", "actual_sanction", "sanction_authority", "missed_history_retained"),
    "160.532": ("prior_final_determination", "participation_record", "issue_preclusion_analysis"),
    "160.534": (
        "issue_burdens",
        "breach_notification_support",
        "no_breach_support",
        "counsel_burden_analysis",
    ),
    "160.536": ("study", "study_population", "study_methods", "qualified_rebuttal"),
    "160.538": ("witness_statements", "witness_availability", "disclosures", "actual_alj_order"),
    "160.540": (
        "evidence_provenance",
        "counsel_privilege_assessment",
        "counsel_admissibility_assessment",
    ),
    "160.542": (
        "official_record",
        "protection_request",
        "counsel_authority",
        "actual_protection_order",
    ),
    "160.544": ("actual_order", "received_at", "brief_deadline", "filed_at", "allowed_reply"),
    "160.546": ("service_at", "finality_at", "appeal_path", "appeal_deadline"),
    "160.548": (
        "appeal",
        "opposition",
        "reconsideration",
        "service_events",
        "finality_at",
        "court_stamped_petition_service",
    ),
    "160.550": ("stay_request", "appeal_copy", "interim_status", "security", "actual_ruling"),
    "160.552": ("alleged_error", "prejudice_evidence", "counsel_harmless_error_analysis"),
    "164.102": ("authority_citation", "source_edition", "category"),
    "164.103": ("ownership_control", "covered_functions", "legal_demands", "hybrid_designation"),
    "164.104": (
        "actual_functions",
        "direct_provisions",
        "scenario_hypothesis",
        "qualified_applicability",
    ),
    "164.106": ("transaction_functions", "part162_dependency", "dependency_review"),
    "164.318": ("initial_compliance_dates", "later_service_dates", "no_new_service_grace_period"),
    "164.532": (
        "pretransition_evidence",
        "exact_exception",
        "agreement_dates",
        "reliance_decision",
    ),
    "164.534": ("initial_compliance_dates", "later_changes", "period_context"),
    "164.535": ("actual_judgment", "status_analysis", "affected_text", "enforceability_decision"),
}


def section(value):
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"(?:HIPAA:|45-CFR-)?(\d+\.\d+)(?:\([a-z0-9]+\))*", value)
    return match.group(1) if match else None


def provision_rows(history, code):
    candidates = history.select("legprovision", {"provision_locator"}) + history.select(
        "leg001docket", {"provision_status"}
    )
    return [r for r in candidates if section(detail(r).get("provision", {}).get("id")) == code]


def case_rows(history, code):
    roles = {"legal_matter_classification", "legal_response_exercise"}
    candidates = history.select("legint", roles) + history.select(
        "leg001docket", {"matter_watch", "change_watch"}
    )
    selected = []
    for row in candidates:
        doc = detail(row)
        codes = doc.get("requirement_ids", doc.get("provision_ids", []))
        if doc.get("requirement_id"):
            codes = [*codes, doc["requirement_id"]]
        if code in {section(c) for c in codes}:
            selected.append(row)
    return selected


def clause_observations(history, code, authored):
    locators, cases = provision_rows(history, code), case_rows(history, code)
    context = context_rows(history)
    selected, field_tests, exceptions = [*locators, *cases], [], []
    fields = CLAUSE_FIELDS[code]
    for row in cases:
        doc = detail(row)
        values = {field: doc[field] for field in fields if field in doc}
        tests = {
            "artifact_id": row["artifact_id"],
            "native": native(row),
            "recorded": values,
            "missing_authored_attributes": [field for field in fields if field not in doc],
            "exercise_only": doc.get("exercise_only"),
            "actual_trigger": doc.get("actual_trigger"),
        }
        if (
            code == "160.204"
            and doc.get("request_status") == "PENDING"
            and doc.get("compliance_stopped") is True
        ):
            exceptions.append(
                {
                    "artifact_id": row["artifact_id"],
                    "reason": "PENDING_REQUEST_USED_AS_STOP_AUTHORITY",
                }
            )
        if (
            code == "160.412"
            and doc.get("waiver_granted") is True
            and not doc.get("actual_disposition")
        ):
            exceptions.append(
                {
                    "artifact_id": row["artifact_id"],
                    "reason": "REQUEST_OR_ELIGIBILITY_IS_NOT_GRANTED_DISPOSITION",
                }
            )
        if (
            code == "160.404"
            and doc.get("exposure_amount") is not None
            and not (doc.get("amount_authority") and doc.get("primary_adjustment"))
        ):
            exceptions.append(
                {
                    "artifact_id": row["artifact_id"],
                    "reason": "AMOUNT_WITHOUT_VERIFIED_PRIMARY_ADJUSTMENT",
                }
            )
        if (
            code == "160.530"
            and doc.get("missed_order")
            and doc.get("missed_history_retained") is False
        ):
            exceptions.append(
                {"artifact_id": row["artifact_id"], "reason": "MISSED_ORDER_HISTORY_DISCARDED"}
            )
        clock_pairs = [
            ("notice_received_at", "response_at"),
            ("service_at", "filed_at"),
            ("received_at", "filed_at"),
            ("failure_start", "failure_end"),
            ("discovery_at", "correction_at"),
        ]
        tests["recorded_clock_arithmetic"] = [
            {
                "start_field": start,
                "end_field": end,
                "elapsed_seconds": (
                    datetime.fromisoformat(_time(doc[end]))
                    - datetime.fromisoformat(_time(doc[start]))
                ).total_seconds(),
                "statutory_deadline_compliance_inferred": False,
            }
            for start, end in clock_pairs
            if doc.get(start) and doc.get(end)
        ]
        for deadline, performed in [
            ("exchange_deadline", "delivered_at"),
            ("brief_deadline", "filed_at"),
            ("hearing_deadline", "hearing_requested_at"),
        ]:
            if doc.get(deadline) and doc.get(performed):
                late = _time(doc[performed]) > _time(doc[deadline])
                tests.setdefault("company_recorded_deadline_comparisons", []).append(
                    {
                        "deadline": deadline,
                        "performed": performed,
                        "late": late,
                        "statutory_calendar_acceptance": False,
                    }
                )
                if late:
                    exceptions.append(
                        {
                            "artifact_id": row["artifact_id"],
                            "reason": "ACTUAL_AFTER_RECORDED_DEADLINE",
                            "deadline_field": deadline,
                        }
                    )
        field_tests.append(tests)
    locator_details = [
        {"artifact_id": r["artifact_id"], "native": native(r), **detail(r)} for r in locators
    ]
    used = selected or context
    return [
        observation(
            "legal-clause-" + code,
            {
                "authored_instruction": authored,
                "exact_section": code,
                "expected_documentary_attributes": list(fields),
                "exact_section_locator_versions": locator_details,
                "exact_section_case_attribute_tests": field_tests,
                "exceptions": exceptions,
                "selected_section_locator_missing": not locators,
                "selected_clause_case_originals_not_collected": not cases,
                "missing_selected_case_does_not_establish_enterprise_nonoccurrence": True,
                "source_edition_and_judicial_applicability_accepted": False,
                "live_enforcement_or_regulator_rights_exercised": False,
                "exact_native_dependencies": own_links(history, selected),
            },
            used_rows(history, used),
            failure=bool(exceptions),
            limited=True,
        )
    ]


def term_map(row):
    doc = row["document"]
    if (row["family"], row["role"]) == ("phi_ba", "contract_register"):
        items = doc.get("synthetic_terms", [])
        require(isinstance(items, list), "Synthetic term list required")
        keys = [t["clause_candidate_id"] for t in items]
        require(len(keys) == len(set(keys)), "Duplicate synthetic term ID")
        return {t["clause_candidate_id"]: t["declared_obligation"] for t in items}
    if (row["family"], row["role"]) == ("transition", "provider_contract"):
        terms = doc.get("fictional_executed_terms", {})
        return {"master_terms:" + k: v for k, v in terms.get("master_terms", {}).items()} | {
            "site_order:" + k: v for k, v in terms.get("site_order", {}).items()
        }
    if (row["family"], row["role"]) == ("provider", "obligation_calendar"):
        return {t["id"]: t["source_obligation"] for t in doc.get("obligations", [])}
    return {}


def term_inventory(history):
    rows = history.select("contract", {"selected_term_inventory", "owner_candidate_triage"})
    out = []
    for row in rows:
        doc, used, tests = row["document"], [row], []
        occurrences = doc.get("term_occurrences", [])
        ids = [t["occurrence_id"] for t in occurrences]
        require(len(ids) == len(set(ids)), "Duplicate selected contract occurrence")
        for entry in occurrences:
            target, status = history.resolve(entry["source_ref"], at=row["source"]["event_at"])
            if target:
                used.append(target)
            allowed_role = target is not None and (target["family"], target["role"]) in {
                ("phi_ba", "contract_register"),
                ("transition", "provider_contract"),
                ("provider", "obligation_calendar"),
            }
            actual = term_map(target).get(entry["term_id"]) if allowed_role else None
            tests.append(
                {
                    "occurrence_id": entry["occurrence_id"],
                    "term_id": entry["term_id"],
                    "reference_status": status,
                    "actual_role_supported": allowed_role,
                    "actual_value": actual,
                    "recorded_value": entry.get("term_value"),
                    "actual_value_matches": allowed_role
                    and actual is not None
                    and actual == entry.get("term_value"),
                    "typed_value_sha256_matches": actual is not None
                    and sha(encoded(actual)) == entry.get("term_sha256"),
                    "preliminary_service_mapping": entry.get("preliminary_service_mapping"),
                }
            )
        reported = (
            integer(doc["term_occurrence_count"], "term occurrence count")
            if "term_occurrence_count" in doc
            else None
        )
        bad = any(
            t["reference_status"] != "EXACT_COLLECTED_ORIGINAL"
            or not t["actual_value_matches"]
            or not t["typed_value_sha256_matches"]
            for t in tests
        )
        out.append(
            observation(
                "selected-contract-inventory-" + row["artifact_id"],
                {
                    "term_occurrence_tests": tests,
                    "observed_occurrences": len(tests),
                    "reported_occurrences": reported,
                    "count_matches": reported == len(tests) if reported is not None else None,
                    "recorded_owner_attestation_scope": doc.get("actor_attestation_scope"),
                    "qualified_counsel_provision_review": doc.get(
                        "qualified_counsel_provision_review"
                    ),
                    "actual_hipaa_applicability": doc.get("actual_hipaa_applicability"),
                    "terms_do_not_establish_performance_or_contract_completeness": True,
                },
                list({r["artifact_id"]: r for r in used}.values()),
                failure=bad or (reported is not None and reported != len(tests)),
                limited=True,
            )
        )
    return out or [
        documentary(history, "selected-contract-inventory-unavailable", context_rows(history))
    ]


def calendar_contract_terms(history):
    observations = []
    mapping = {
        "facility_service": "service",
        "site_incident_notice_hours": "provider_incident_notice_hours",
        "security_report_frequency": "provider_security_report_frequency",
        "exit_notice_days": "exit_notice_days",
        "ephi_processing": "ephi_processing",
    }
    for row in history.select("provider", {"obligation_calendar"}):
        doc = row["document"]
        reference = doc.get("source_contract_ref")
        target, status = (
            history.resolve(reference, at=row["source"]["event_at"])
            if reference
            else (None, "ORIGINAL_REFERENCE_NOT_RECORDED")
        )
        allowed = target is not None and (target["family"], target["role"]) in {
            ("transition", "provider_contract"),
            ("phi_ba", "contract_register"),
        }
        actual = (
            target["document"].get("fictional_executed_terms", {}).get("master_terms", {})
            if allowed and target["family"] == "transition"
            else term_map(target)
            if allowed
            else {}
        )
        tests = []
        for obligation in doc.get("obligations", []):
            key = (
                mapping.get(obligation["id"], obligation["id"])
                if target and target["family"] == "transition"
                else obligation["id"]
            )
            value = actual.get(key)
            tests.append(
                {
                    "obligation_id": obligation["id"],
                    "actual_upstream_field": key,
                    "actual_upstream_value": value,
                    "calendar_value": obligation.get("source_obligation"),
                    "actual_value_matches": allowed
                    and value is not None
                    and value == obligation.get("source_obligation"),
                    "source_hash_matches": bool(target)
                    and obligation.get("source_contract_sha256") == target["artifact_sha256"],
                }
            )
        observations.append(
            observation(
                "provider-calendar-upstream-terms-" + row["artifact_id"],
                {
                    "provider_id": doc.get("provider_id"),
                    "source_reference_status": status,
                    "actual_upstream_role_supported": allowed,
                    "upstream_contract_native": native(target) if target else None,
                    "obligation_tests": tests,
                    "calendar_index_not_external_provider_performance": True,
                },
                [row, *([target] if target else [])],
                failure=bool(target)
                and (
                    not allowed
                    or any(
                        not t["actual_value_matches"] or not t["source_hash_matches"] for t in tests
                    )
                ),
                limited=status != "EXACT_COLLECTED_ORIGINAL",
            )
        )
    return observations


def ba_chain(history):
    contracts = history.select("phi_ba", {"contract_register"})
    authorities = history.select("phi_ba", {"contract_authority"})
    flows = history.select("phi_ba", {"flow_register"})
    out = [
        documentary(
            history,
            "fictional-ba-legal-role-authority-and-contracts",
            history.select(
                "phi_ba",
                {
                    "legal_decision",
                    "contract_authority",
                    "contract_approval",
                    "counterparty_acceptance",
                    "contract_register",
                },
            ),
        )
    ]
    for row in flows:
        doc, at = row["document"], row["source"]["event_at"]
        support = doc.get("sim_subcontractor_id")
        terms = [
            r
            for r in contracts
            if support and support in r["document"].get("contract_party_ids", [])
        ]
        prior = active(terms, at)
        prior_executed = [
            r
            for r in prior
            if r["document"].get("contract_executed_in_simulation") is True
            and r["document"].get("simulated_contract_effective_at")
            and _time(r["document"]["simulated_contract_effective_at"]) <= _time(at)
        ]
        routed = (
            doc.get("site_route")
            and "BOISE" in doc["site_route"]
            or doc.get("downstream_flow") is True
        )
        failed = bool(routed) and not prior_executed
        out.append(
            observation(
                "downstream-flow-signed-scope-" + row["artifact_id"],
                {
                    "flow_native": native(row),
                    "actual_event_at": at,
                    "actual_support_party": support,
                    "actual_marker_id": doc.get("flow_marker_id"),
                    "actual_site_route": doc.get("site_route"),
                    "contract_versions_available_and_effective_at_flow": [
                        native(r) for r in prior_executed
                    ],
                    "later_contract_versions": [
                        native(r) for r in terms if _time(r["source"]["available_at"]) > _time(at)
                    ],
                    "downstream_route_before_effective_flowdown": failed,
                    "recorded_flow_disposition": doc.get("flow_gate_disposition"),
                    "actual_copy_or_destination_acknowledgement": doc.get("destination_ack"),
                    "support_copy_status": doc.get("simulated_copy_reached_support"),
                    "acknowledgement_status": doc.get(
                        "simulated_support_copy_acknowledgement_status"
                    ),
                    "recorded_cure_status": doc.get("cure_status"),
                    "exception_open": doc.get("exception_open"),
                    "later_terms_or_quarantine_do_not_erase_prior_route": True,
                    "real_phi_ba_or_party_status_established": False,
                },
                [row, *terms],
                failure=failed,
                limited=True,
            )
        )
    # Delegation is scoped to actual contract identifiers; title or role alone gives no authority.
    for row in contracts:
        doc, at = row["document"], row["source"]["event_at"]
        prior = active(authorities, at)
        named = [
            r for r in prior if r["source"]["record"] == doc.get("limited_delegation_record_id")
        ]
        scopes = [r["document"].get("limited_delegation_scope", []) for r in named]
        scope_matches = any(doc.get("contract_id") in values for values in scopes)
        signers = doc.get("simulated_signer_ids", [])
        tokens(signers, "simulated signer identities")
        delegatees = {r["document"].get("delegatee_id") for r in named}
        signer_matches = (
            all(person in delegatees for person in signers) if signers and named else None
        )
        effective = doc.get("simulated_contract_effective_at")
        out.append(
            observation(
                "contract-scope-and-signing-" + row["artifact_id"],
                {
                    "contract_id": doc.get("contract_id"),
                    "parties": doc.get("contract_party_ids"),
                    "simulated_terms": term_map(row),
                    "simulated_contract_effective_at": effective,
                    "effective_not_after_publication": bool(effective)
                    and _time(effective) <= _time(row["source"]["available_at"]),
                    "recorded_executed_in_simulation": doc.get("contract_executed_in_simulation"),
                    "exact_named_delegation_versions": [native(r) for r in named],
                    "named_scope_includes_contract": scope_matches,
                    "actual_named_signers_match_published_delegatee": signer_matches,
                    "signer_ids": doc.get("simulated_signer_ids"),
                    "recorded_signer_authority": doc.get("simulated_signer_authority"),
                    "real_signature_and_qualified_legal_authority_accepted": False,
                },
                [row, *named],
                failure=(bool(named) and not scope_matches) or signer_matches is False,
                limited=True,
            )
        )
    return out


def provider_register_id(row):
    """Read only the native vendor-register's explicit flat or nested declaration."""
    require(
        row["family"] == "provider-history" and row["role"] == "vendor_register",
        "Exact native planned vendor-register role required",
    )
    document = row["document"]
    values = []
    if "provider_id" in document:
        values.append(document["provider_id"])
    provider = document.get("provider")
    if isinstance(provider, dict) and "provider_id" in provider:
        values.append(provider["provider_id"])
    require(
        values
        and all(isinstance(value, str) and value.strip() for value in values)
        and len(set(values)) == 1,
        "Exact unambiguous declared planned provider ID required",
    )
    return values[0]


def provider_population(history):
    transitions = history.select("transition", {"provider_contract"})
    flows = history.select("phi_ba", {"flow_register"})
    reconciles = history.select("provider", {"population_reconcile"})
    relationships = history.select("provider", {"relationship_register"})
    out = []
    for row in reconciles:
        doc, at = row["document"], row["source"]["event_at"]
        sources = [*active(transitions, at), *active(flows, at)]
        expected = set()
        for source in sources:
            body = source["document"]
            pid = (
                body.get("site", {}).get("provider_id")
                if source["family"] == "transition"
                else body.get("sim_subcontractor_id")
            )
            if pid:
                expected.add(pid)
        current = active(relationships, at)
        observed = {r["document"]["provider_id"] for r in current}
        missing = sorted(expected - observed)
        declared = set(tokens(doc.get("expected_provider_ids", []), "expected provider IDs"))
        reported = set(tokens(doc.get("missing_provider_ids", []), "missing provider IDs"))
        out.append(
            observation(
                "provider-independent-population-" + row["artifact_id"],
                {
                    "recalculated_source_contract_and_flow_provider_ids": sorted(expected),
                    "available_register_provider_ids": sorted(observed),
                    "actual_missing_provider_ids": missing,
                    "declared_expected_provider_ids": sorted(declared),
                    "declared_missing_provider_ids": sorted(reported),
                    "declared_expected_matches_actual_selected_sources": declared == expected,
                    "declared_missing_matches_date_effective_register": reported == set(missing),
                    "recorded_discovery_method": doc.get("discovery_method"),
                    "recorded_ba_and_population_exception_separate": doc.get(
                        "ba_exception_is_distinct"
                    ),
                    "enterprise_or_uncollected_provider_denominator_established": False,
                    "later_register_backfill_does_not_cure_earlier_omission": True,
                },
                [row, *sources, *current],
                failure=bool(missing) or declared != expected or reported != set(missing),
                limited=True,
            )
        )
    if not out:
        out.append(
            documentary(
                history,
                "provider-population-selected-context-only",
                history.select("provider", {"operation_scope", "relationship_register"})
                + transitions
                + flows,
            )
        )
    for row in history.select("provider-history", {"coverage_reconciliation"}):
        doc, at = row["document"], row["source"]["event_at"]
        plans = active(history.select("provider-history", {"planned_dependency_inventory"}), at)
        expected = {d["provider_id"] for r in plans for d in r["document"].get("dependencies", [])}
        actual = active(history.select("provider-history", {"vendor_register"}), at)
        observed = {provider_register_id(r) for r in actual}
        missing = sorted(expected - observed)
        out.append(
            observation(
                "planned-provider-historical-coverage-" + row["artifact_id"],
                {
                    "planned_dependency_ids": sorted(expected),
                    "registered_ids_at_occurrence": sorted(observed),
                    "missing_ids": missing,
                    "declared_missing_ids": doc.get("missing_provider_ids"),
                    "reported_support_obtained": doc.get("diligence_support_obtained"),
                    "outstanding_support_items": doc.get("outstanding_diligence_support_items"),
                    "local_planned_intake_does_not_establish_operating_supplier_monitoring": True,
                },
                [row, *plans, *actual],
                failure=bool(missing),
                limited=True,
            )
        )
    return out


def provider_due(history):
    out = []
    schedules = history.select("provider-history", {"review_schedule"})
    monitoring = history.select("provider-history", {"monitoring_reviews"})
    calendars = history.select("provider", {"obligation_calendar"})
    reviews = history.select("provider", {"review_register"})
    for schedule in [*schedules, *calendars]:
        doc = schedule["document"]
        due = doc.get("due_at", doc.get("internal_review_due_at"))
        if not due or _time(due) > history.as_of:
            continue
        family = schedule["family"]
        candidates = monitoring if family == "provider-history" else reviews
        found = [
            r
            for r in candidates
            if r["document"].get("provider_id") == doc.get("provider_id")
            and _time(r["document"].get("original_due_at", r["document"].get("review_due_at", due)))
            == _time(due)
        ]
        tests = []
        for review in found:
            body = review["document"]
            late = (
                datetime.fromisoformat(_time(review["source"]["event_at"]))
                - datetime.fromisoformat(_time(due))
            ).total_seconds()
            tests.append(
                {
                    "native": native(review),
                    "actual_late_seconds": max(0, late),
                    "reported_late_seconds": body.get("late_seconds"),
                    "reported_lateness_matches": integer(
                        body["late_seconds"], "review late seconds"
                    )
                    == max(0, late)
                    if "late_seconds" in body
                    else None,
                    "native_original_available_by_due": _time(review["source"]["available_at"])
                    <= _time(due),
                    "support_status": body.get("support_status"),
                    "actual_obligation_checks": body.get("obligation_checks"),
                    "assurance_request_status": body.get("external_assurance_request_status"),
                    "performance_data": body.get("performance_data"),
                    "financial_health": body.get("financial_health"),
                    "review_disposition": body.get("review_disposition", body.get("review_result")),
                }
            )
        out.append(
            observation(
                "provider-due-review-" + schedule["artifact_id"],
                {
                    "provider_id": doc.get("provider_id"),
                    "actual_due_at": due,
                    "scheduled_source_native": native(schedule),
                    "review_tests": tests,
                    "due_occurrence_missing": not found,
                    "operating_or_planned_intake_basis": family,
                    "source_term_index_or_internal_review_not_supplier_performance_assurance": True,
                },
                [schedule, *found],
                failure=not found
                or all(not t["native_original_available_by_due"] for t in tests)
                or any(t["reported_lateness_matches"] is False for t in tests),
                limited=True,
            )
        )
    return out or [
        documentary(
            history,
            "provider-review-calendar-missing",
            history.select("provider", {"operation_scope", "relationship_register"}),
        )
    ]


def diligence(history):
    rows = history.select(
        "provider-history", {"diligence_work_items", "tier_assessments", "internal_actions"}
    ) + history.select("provider", {"relationship_register", "review_register"})
    observations = []
    for row in rows:
        observations.append(
            documentary(
                history,
                "provider-risk-support-" + row["artifact_id"],
                [row],
                fields={
                    "provider_id",
                    "requirement_id",
                    "assessment",
                    "tier",
                    "tier_rationale",
                    "data_access_boundary",
                    "support_status",
                    "external_request_status",
                    "received_document_sha256",
                    "report_scope",
                    "report_period",
                    "exceptions",
                    "customer_controls",
                    "financial_condition",
                    "performance_data",
                    "incident_history",
                    "financial_health",
                    "planned_recovery_independence",
                    "review_result",
                    "review_disposition",
                    "supplier_decisions",
                    "policy_status",
                    "monitoring_basis",
                    "contract_execution",
                    "actual_provider_assurance_received",
                    "internal_checks",
                    "obligation_checks",
                    "status",
                },
            )
        )
    return observations or [
        documentary(
            history,
            "provider-risk-support-unavailable",
            history.select("provider", {"operation_scope"}),
        )
    ]


def service_description(history):
    rows = (
        history.select("assuranceops")
        + history.select(
            "provider", {"relationship_register", "review_register", "exception_register"}
        )
        + history.select("transition", {"site_release", "site_commissioning", "recovery_exercise"})
    )
    return [
        documentary(history, "provider-service-description-assertions-and-source-boundary", rows)
    ]


def purpose(history):
    rows = history.select("processing") + history.select(
        "supplementalops", {"privacy_responsibility"}
    )
    terms = history.select("phi_ba", {"contract_register"})
    out = []
    for row in rows:
        doc = row["document"]
        out.append(
            observation(
                "contract-purpose-and-reuse-" + row["artifact_id"],
                {
                    "actual_requested_or_delegated_scope": doc,
                    "available_customer_terms": [
                        {
                            "native": native(r),
                            "permitted_use": term_map(r).get("permitted_uses_and_disclosures"),
                        }
                        for r in active(terms, row["source"]["event_at"])
                    ],
                    "possession_or_baa_does_not_grant_new_ai_training_use": True,
                    "executable_scope_or_qualified_purpose_acceptance_established": False,
                    "native_dependencies": own_links(history, [row]),
                },
                used_rows(history, [row, *active(terms, row["source"]["event_at"])]),
                limited=True,
            )
        )
    return out or [documentary(history, "purpose-source-selected-terms-only", terms)]


def rights(history):
    rows = history.select("dat002rights") + history.select(
        "privacyops",
        {"privacy_customer_instruction", "privacy_dataset_inventory", "privacy_disclosure"},
    )
    authority = history.select("supplementalops", {"privacy_responsibility"})
    out = []
    for row in rows:
        doc = row["document"]
        out.append(
            observation(
                "contract-rights-request-support-" + row["artifact_id"],
                {
                    "actual_native_role": row["role"],
                    "actual_request_records": doc,
                    "direct_vs_customer_retained_authority": retained(
                        active(authority, row["source"]["event_at"])
                    ),
                    "exact_native_reference_tests": own_links(history, [row]),
                    "copy_amendment_accounting_exercise_complete": False,
                    "complete_designated_record_set_and_actual_recipient_established": False,
                },
                used_rows(history, [row, *active(authority, row["source"]["event_at"])]),
                failure=doc.get("premature_no_record_mark") is True,
                limited=True,
            )
        )
    return out or [
        documentary(
            history,
            "contract-rights-exercise-not-collected",
            history.select("phi_ba", {"contract_register"}) + authority,
        )
    ]


def notice_clock(history):
    rows = [
        r
        for r in history.select(
            "supplementalops", {"communication_event", "privacy_responsibility"}
        )
        if any(
            k in r["document"]
            for k in (
                "discovery_at",
                "agent_discovery_at",
                "notice_at",
                "notice_sent_at",
                "law_enforcement_delay",
                "customer_retained_notice_authority",
            )
        )
    ]
    rows += [
        r
        for r in history.select("legint", {"legal_response_exercise"})
        if r["document"].get("notice_clock_exercise") is True
    ]
    terms = history.select("phi_ba", {"contract_register"})
    out = []
    for row in rows:
        doc = row["document"]
        starts = [_time(doc[k]) for k in ("agent_discovery_at", "discovery_at") if doc.get(k)]
        start = min(starts) if starts else None
        notice = doc.get("notice_sent_at", doc.get("notice_at"))
        require(
            all(at <= _time(row["source"]["event_at"]) for at in starts),
            "Recorded discovery exceeds source event",
        )
        if notice:
            require(
                _time(notice) <= _time(row["source"]["event_at"]),
                "Recorded notice exceeds source event",
            )
            require(start is None or start <= _time(notice), "Recorded notice precedes discovery")
        hours = (
            (
                datetime.fromisoformat(_time(notice)) - datetime.fromisoformat(_time(start))
            ).total_seconds()
            / 3600
            if start and notice
            else None
        )
        sla = doc.get("contractual_notice_hours")
        if sla is not None:
            integer(sla, "fictional contractual notice hours", positive=True)
        delayed = hours is not None and sla is not None and hours > sla
        reset = bool(
            start and doc.get("clock_started_at") and _time(doc["clock_started_at"]) > _time(start)
        )
        out.append(
            observation(
                "contract-notice-clock-" + row["artifact_id"],
                {
                    "recorded_event": doc,
                    "source_contract_terms": [
                        {
                            "native": native(r),
                            "notice_term": term_map(r).get("incident_and_breach_reporting"),
                        }
                        for r in active(terms, row["source"]["event_at"])
                    ],
                    "actual_elapsed_hours_from_earliest_recorded_discovery": hours,
                    "actual_contractual_sla_exceeded": delayed,
                    "recorded_clock_reset_after_discovery": reset,
                    "statutory_trigger_clock_or_law_enforcement_delay_accepted": False,
                    "actual_notice_recipient_and_received_delivery_established": False,
                    "day60_routine_target_or_management_confirmation_reset_not_accepted": True,
                    "exact_native_dependencies": own_links(history, [row]),
                },
                used_rows(history, [row, *active(terms, row["source"]["event_at"])]),
                failure=delayed or reset,
                limited=True,
            )
        )
    return out or [
        documentary(
            history,
            "notice-clock-exercise-unavailable",
            history.select("phi_ba", {"contract_register", "exception_register"}),
        )
    ]


def provider_exit(history):
    rows = history.select(
        "provider", {"obligation_calendar", "exception_register"}
    ) + history.select("provider-history", {"internal_actions"})
    events = [
        r
        for r in history.select("provider")
        if r["role"] in {"exit_event", "offboarding_event", "termination_event"}
    ]
    tests = []
    for row in events:
        doc = row["document"]
        fields = (
            "transition_ref",
            "identity_revocation_ref",
            "connection_revocation_ref",
            "data_disposition_ref",
            "residual_backups",
            "open_financial_obligations",
        )
        tests.append(
            {
                "native": native(row),
                "actual_exit": doc,
                "missing_exit_attributes": [f for f in fields if f not in doc],
                "native_reference_tests": own_links(history, [row]),
                "actual_sanitization_or_counsel_feasibility_reperformed": False,
            }
        )
    return [
        observation(
            "provider-exit-and-continuing-protection",
            {
                "recorded_selected_exit_context": retained(rows),
                "actual_collected_exit_event_tests": tests,
                "empty_collected_exit_vector_does_not_establish_no_exits": not events,
                "all_access_connections_backup_copies_and_financial_obligations_reconciled": False,
            },
            used_rows(history, [*rows, *events]),
            limited=True,
        )
    ]


def regulator_response(history):
    originals = history.select(
        "legaloriginals", {"legal_inbound_message", "legal_inbound_attachment"}
    )
    playbooks = history.select("legint", {"regulatory_response_playbook"})
    all_exercises = history.select("legint", {"legal_response_exercise"})
    exercises = [
        r
        for r in all_exercises
        if any(
            k in r["document"]
            for k in (
                "urgent_access",
                "urgent_access_path_exercised",
                "provider_copy_state",
                "available_company_copy_ids",
                "customer_disclosure_rule_is_authority_basis",
                "preserved_record_sets",
            )
        )
    ]
    observations = []
    for row in exercises:
        doc = row["document"]
        at = row["source"]["event_at"]
        prior_id = doc.get("prior_report_id")
        prior = (
            [r for r in active(all_exercises, at) if r["source"]["record"] == prior_id]
            if prior_id
            else []
        )
        observations.append(
            observation(
                "regulator-provider-urgent-exercise-" + row["artifact_id"],
                {
                    "actual_exercise_record": doc,
                    "date_effective_playbook_originals": retained(active(playbooks, at)),
                    "exact_prior_report_originals": retained(prior),
                    "prior_report_unavailable": bool(prior_id) and not prior,
                    "actual_received_original_communications": [
                        native(r) for r in active(originals, at)
                    ],
                    "provider_copy_state": doc.get("provider_copy_state"),
                    "company_copy_ids": doc.get("available_company_copy_ids"),
                    "urgent_path_exercised": doc.get("urgent_access_path_exercised"),
                    "customer_disclosure_rule_is_authority_basis": doc.get(
                        "customer_disclosure_rule_is_authority_basis"
                    ),
                    "earlier_followup_or_access_failure_remains_separate_after_retest": True,
                    "actual_regulator_order_rights_and_response_executed": False,
                },
                [row, *active(playbooks, at), *prior, *active(originals, at)],
                failure=doc.get("urgent_access_path_exercised") is False
                or doc.get("customer_disclosure_rule_is_authority_basis") is True,
                limited=True,
            )
        )
    return observations or [
        documentary(
            history,
            "regulator-provider-urgent-exercise-unavailable",
            playbooks + originals + context_rows(history),
        )
    ]


BASE_FACETS = {
    "SH-LEG-001": ("legal_context", "terms", "intake"),
    "SH-LEG-002": ("purpose", "terms", "ba"),
    "SH-TPR-001": ("population", "diligence"),
    "SH-TPR-002": ("diligence", "description", "population"),
    "SH-TPR-003": ("terms", "ba", "notice", "rights"),
    "SH-TPR-004": ("due", "population", "diligence", "ba"),
    "SH-TPR-005": ("exit",),
}
FACET_SCOPE = {
    "legal_context": (
        "exact dated fictional source/role/status/edition overlays, "
        "judicial-publication hold and matter/change watch native joins"
    ),
    "terms": (
        "each exact native selected term occurrence, typed value hash, "
        "actual contract edition and date-effective source availability"
    ),
    "intake": (
        "once-rederived registered monthly channels, original "
        "communication and attachment custody, ledger/screen/tail/quarter "
        "histories and retained exceptions"
    ),
    "purpose": (
        "actual collected proposed reuse/delegated purpose scope and "
        "contemporaneous fictional permitted-use terms"
    ),
    "ba": (
        "fictional customer/BA/subcontractor legal-role and contract "
        "authority records, scoped delegation and downstream flow before "
        "effective terms"
    ),
    "population": (
        "provider identities independently derived from site "
        "contracts/flows and planned dependencies, contemporaneous "
        "register and historical omissions"
    ),
    "diligence": (
        "selected risk dimensions, actual diligence work items/report "
        "support gaps, recorded source term and review restrictions"
    ),
    "description": (
        "actual collected service-description/source assertions, "
        "commissioned/recovery records, provider exception and review "
        "histories"
    ),
    "notice": (
        "actual available fictional notice terms and retained event "
        "clocks; local elapsed time, recorded contract SLA and improper "
        "reset when actual facts exist"
    ),
    "rights": (
        "selected synthetic rights/DRS/customer authority records, native "
        "supporting-original joins and premature no-record histories"
    ),
    "due": (
        "actual provider/calendar review deadlines, all collected matching"
        " occurrences and native event/publication lateness without "
        "converting planned intake to operating monitoring"
    ),
    "exit": (
        "selected exit/return/destruction/continuing-protection terms and "
        "every actual collected exit event/native revocation/disposition "
        "dependency"
    ),
    "regulator": (
        "actual received original communications, date-effective response playbooks "
        "and each provider-copy/urgent-access exercise with explicit prior-report "
        "custody and retained earlier failure"
    ),
}
BASE_LIMITS = {
    "SH-LEG-001": (
        "Qualified period-specific primary text/amendment/judicial-status,"
        " direct/delegated/entity/function applicability and full-company "
        "matter completeness; four registered channels and source locators"
        " do not establish enterprise nonoccurrence."
    ),
    "SH-LEG-002": (
        "Qualified exact workflow/purpose/minimum-necessary authority, "
        "real PHI or BA status and executable disclosure/new-use "
        "enforcement across a complete population."
    ),
    "SH-TPR-001": (
        "Accepted enterprise tier/risk method and complete "
        "supplier/data-flow census; supplier-sourced diligence, current "
        "scope/exception/customer-control evidence and qualified "
        "onboarding acceptance."
    ),
    "SH-TPR-002": (
        "Independent received supplier reports and report "
        "period/scope/exception/customer-control review, actual services "
        "and full incident/change populations; a queued request or "
        "internal description is not assurance support."
    ),
    "SH-TPR-003": (
        "Qualified signed-party/counsel acceptance of exact contractual "
        "responsibilities, direct/delegated legal duties and actual "
        "upstream completion/notice/rights performance."
    ),
    "SH-TPR-004": (
        "Complete due/triggered supplier operating review population, "
        "received "
        "performance/incident/financial/concentration/subcontractor "
        "support and qualified failed-cure/termination decisions."
    ),
    "SH-TPR-005": (
        "Complete actual exit occurrence population, operating supplier "
        "identity/connection revocation, all active/backup/provider-copy "
        "return/destruction, termination feasibility and financial "
        "closure."
    ),
}


def selection(task):
    suffix = task["task_id"].split("-corporate-", 1)[1]
    control = task["control_id"]
    if control == "SH-LEG-001" and suffix.startswith("CHECK-HIPAA:"):
        return (
            ("clause",),
            (
                "Actual case-specific authority, each required documentary "
                "attribute and qualified source/context interpretation for "
            )
            + suffix[12:]
            + "; no reserved/authority text becomes a recurring technical duty.",
        )
    if suffix == "ACTION-H-LEGAL-STATUS":
        return (
            ("legal_context",),
            (
                "Actual current affected-text/judgment/status review for "
                "164.502/164.509/164.520; historical XML/printed locator cannot "
                "establish enforceability or applicability."
            ),
        )
    if suffix == "ACTION-H-REGULATOR":
        return (
            ("regulator", "legal_context"),
            (
                "An exercised regulator demand involving inaccessible provider "
                "records and urgent access with actual received original, "
                "authority/preservation and outcome; ordinary disclosure "
                "restrictions do not establish regulator rights."
            ),
        )
    if suffix == "ACTION-H-PRIVACY-PURPOSE":
        return ("purpose", "terms"), BASE_LIMITS[control]
    if suffix == "ACTION-S-DESCRIPTION":
        return (
            ("description", "population", "diligence"),
            (
                "Every description assertion independently traced to authoritative"
                " original; complete incident/change/vendor populations and actual"
                " omissions need separate source support."
            ),
        )
    if suffix == "ACTION-H-NOTICE-CLOCK":
        return (
            ("notice", "terms"),
            (
                "Delayed escalation/agent discovery, shorter contractual limit, "
                "incomplete initial facts and oral/written law-enforcement-delay "
                "scenarios with actual delivery; qualified trigger/calendar and "
                "statutory legal decisions remain unperformed."
            ),
        )
    if suffix == "ACTION-H-RIGHTS-ASSISTANCE":
        return (
            ("rights", "terms"),
            (
                "Exercised electronic copy, accepted amendment and accounting on "
                "complete synthetic records, actual correct recipient and "
                "independently verified upstream completion; holds are not "
                "completed rights exercises."
            ),
        )
    if suffix == "ACTION-H-SUBCONTRACT":
        return (
            ("ba", "population", "due", "terms"),
            (
                "Independent complete downstream-flow census, equivalent signed "
                "scope/reporting paths and an actual unsuccessful cure with "
                "qualified termination-feasibility assessment."
            ),
        )
    if suffix == "CHECK-SOC2:CC9.2":
        return (
            ("population", "diligence", "due", "exit", "terms"),
            (
                "Accepted supplier selection/responsibility/monitoring/exit "
                "sufficiency, complete actual populations and unresolved "
                "received-report exceptions; possession of a report never closes "
                "its exceptions."
            ),
        )
    return BASE_FACETS[control], BASE_LIMITS[control]


def task_contracts():
    result = {}
    for task in authored_contracts()["tasks"]:
        facets, limits = selection(task)
        descriptions = "; ".join(
            FACET_SCOPE.get(
                f,
                "exact "
                + task["task_id"].split("-corporate-", 1)[1]
                + " source locator/case-specific documentary attributes and native clocks",
            )
            for f in facets
        )
        result[task["task_id"]] = {
            "performed": task["task_id"]
            + ": Reparse ordinarily collected originals and examine "
            + descriptions
            + (
                ". Bound all actual citation custody and source-specific "
                "discrepancies; documentary facts only."
            ),
            "unperformed": task["task_id"]
            + ": "
            + limits
            + " Exact remaining authored acceptance: "
            + task["authored_instruction"]
            + " Required final procedure: "
            + task["authored_procedure"]
            + " Kind boundary: "
            + task["task_kind_rule"],
            "allowed_dispositions": [
                {"status": "IN_PROGRESS", "conclusion": "LIMITATION"},
                {"status": "IN_PROGRESS", "conclusion": "FAIL"},
            ],
        }
    return result


def inspections(rows, *, as_of, scratch_root):
    del scratch_root
    require(
        sha(Path(intake.__file__).read_bytes()) == INTAKE_SHA256,
        "Accepted pure intake method pin differs",
    )
    history = History(rows, as_of)
    authored = authored_contracts()
    contracts = task_contracts()
    intake_rows = [
        r
        for r in history.rows
        if r["family"] in intake.SYSTEMS and r["role"] in intake.SYSTEMS[r["family"]]
    ]
    calculation = (
        intake.examine(intake_rows, as_of=as_of)
        if any(r["role"] == "intake_channel_register" for r in intake_rows)
        else None
    )
    intake_observations = [
        observation(
            "registered-company-legal-intake-calculation",
            calculation
            if calculation
            else {
                "selected_original_intake_calculation_unavailable": True,
                "enterprise_nonoccurrence_established": False,
            },
            intake_rows or context_rows(history),
            failure=bool(
                calculation
                and (
                    calculation["documentary_discrepancies"]
                    or calculation["missing_monthly_exports"]
                )
            ),
            limited=True,
        )
    ]
    facets = {
        "legal_context": [
            documentary(
                history,
                "legal-source-entity-role-and-period-context",
                context_rows(history)
                + history.select("legprovision", {"provision_locator"})
                + history.select("addressabledocket"),
            )
        ],
        "intake": intake_observations,
        "terms": [*term_inventory(history), *calendar_contract_terms(history)],
        "ba": ba_chain(history),
        "population": provider_population(history),
        "due": provider_due(history),
        "diligence": diligence(history),
        "description": service_description(history),
        "purpose": purpose(history),
        "rights": rights(history),
        "notice": notice_clock(history),
        "exit": provider_exit(history),
        "regulator": regulator_response(history),
    }
    output = []
    for task in authored["tasks"]:
        names, limits = selection(task)
        suffix = task["task_id"].split("-corporate-", 1)[1]
        chosen = (
            clause_observations(
                history, suffix.removeprefix("CHECK-HIPAA:"), task["authored_instruction"]
            )
            if names == ("clause",)
            else [o for name in names for o in facets[name]]
        )
        # Reused selected legal methods remain actual original calculations,
        # including context/communications for 160.300/160.304 exactly once.
        if task["control_id"] == "SH-LEG-001" and suffix in {
            "TOE",
            "CHECK-HIPAA:160.300",
            "CHECK-HIPAA:160.304",
        }:
            chosen = [*chosen, *intake_observations] if names == ("clause",) else chosen
        bounded = bounded_observations([dict(o) for o in chosen])
        id_map = {
            o["id"]: "B06-" + sha((task["task_id"] + ":" + o["id"]).encode()) for o in bounded
        }
        for original in bounded:
            old_id = original["id"]
            original["id"] = id_map[old_id]
            if isinstance(original["facts"], dict):
                original["facts"] = {
                    **original["facts"],
                    "calculation_local_observation_id": old_id,
                }
                if "continued_evidence_observation_ids" in original["facts"]:
                    original["facts"]["continued_evidence_observation_ids"] = [
                        id_map[value]
                        for value in original["facts"]["continued_evidence_observation_ids"]
                    ]
                if "supports_complete_calculation_observation_id" in original["facts"]:
                    original["facts"]["supports_complete_calculation_observation_id"] = id_map[
                        original["facts"]["supports_complete_calculation_observation_id"]
                    ]
            original["status"] = {
                "EXCEPTION": "EXCEPTION_RECORDED",
                "LIMITATION": "SUPPORT_UNAVAILABLE",
                "CORROBORATED_SELECTED_ATTRIBUTE": "OBSERVED",
            }[original["status"]]
        artifacts = sorted({e["artifact_id"] for o in bounded for e in o["evidence"]})
        selected = [r for r in history.rows if r["artifact_id"] in artifacts]
        failed = any(o["status"] == "EXCEPTION_RECORDED" for o in bounded)
        conclusion = "FAIL" if failed and task["kind"] != "TOD" else "LIMITATION"
        contract = contracts[task["task_id"]]
        output.append(
            {
                "task_id": task["task_id"],
                "artifact_ids": artifacts,
                "observations": bounded,
                "performed": contract["performed"],
                "unperformed": contract["unperformed"],
                "result": {
                    "schema": "SH_COLLECTED_B06_TASK_EXAMINATION_V1",
                    "task_id": task["task_id"],
                    "authored_instruction": task["authored_instruction"],
                    "authored_procedure": task["authored_procedure"],
                    "task_kind": task["kind"],
                    "facets": list(names),
                    "as_of": history.as_of,
                    "population": {
                        "scope": "ACTUAL_SELECTED_COLLECTED_NATIVE_ORIGINALS",
                        "source_version_count": len(selected),
                        "native_originals": [native(r) for r in selected],
                        "full_period_enterprise_denominator_established": False,
                    },
                    "sample": {
                        "selection": (
                            "ALL_ACTUAL_COLLECTED_VERSIONS_REFERENCED_BY_THIS_DISTINCT_CLAUSE_EXAMINATION"
                        ),
                        "artifact_ids": artifacts,
                    },
                    "explicit_exception_observation_ids": [
                        o["id"] for o in bounded if o["status"] == "EXCEPTION_RECORDED"
                    ],
                    "professional_pass_or_full_authored_task_completion_asserted": False,
                },
                "disposition": {
                    "status": "IN_PROGRESS",
                    "conclusion": conclusion,
                    "rationale": "Actual selected documentary exceptions retained."
                    if conclusion == "FAIL"
                    else (
                        "Selected documentary attributes examined; exact remaining "
                        "acceptance and source-specific limits retained."
                    ),
                },
            }
        )
    require(
        [t["task_id"] for t in output] == authored["selected_task_ids"],
        "Exact full99 inspection vector differs",
    )
    return output
