"""Examine source dependencies from ordinary collected company originals.

This is a pure content method behind a separately reviewed Engine-bound
collector. Company decisions remain attributed business evidence, never the
auditor's or owner's acceptance. No database, stored query, Key, previous audit
result or external source is opened here.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime

from .company_store import _time
from .fresh_sec003_procedure import CLOCK_ID, NATIVE_ID, require

TASKS = ("TASK-GATE-QUALIFIED-REVIEW", "TASK-GATE-SERVICE-FACTS")
FAMILIES = {
    "transition",
    "phi_ba",
    "person-access-history",
    "govapp",
    "legprovision",
    "assuranceops",
}
BUSINESS_ID = tuple(k for k in CLOCK_ID if k != "imported_at")
CONTRACTS = {
    TASKS[0]: {
        "performed": "Inspect collected source edition/status, declared conditions and historical "
        "exceptions, scoped applicability and attributed company review decisions; reconcile "
        "exact available native dependencies and preserve selected review boundaries.",
        "unperformed": "Qualified source interpretation and independent design sufficiency "
        "acceptance for this entire engagement; primary text/status recheck for the fictional "
        "2027 period; actual professional credentials and external opinion authority.",
        "allowed_dispositions": [{"status": "IN_PROGRESS", "conclusion": "LIMITATION"}],
    },
    TASKS[1]: {
        "performed": "Reconcile collected declared entity, service/site boundary, synthetic data "
        "flows, agreements, local system/population scope, attributed execution owners and "
        "dated operating history; keep original reference facts and separate service contexts.",
        "unperformed": "Service-owner acceptance of the complete engagement facts; enterprise "
        "population and full-year continuity beyond collected declared histories; real site "
        "deployment, actual PHI processing, real contracts and real legal applicability.",
        "allowed_dispositions": [{"status": "IN_PROGRESS", "conclusion": "LIMITATION"}],
    },
}


def _pointer(row):
    return {k: row["source"][k] for k in CLOCK_ID}


def _native_key(source):
    return tuple(source[k] for k in NATIVE_ID)


def _references(value, path="$"):
    if isinstance(value, dict):
        if set(NATIVE_ID) <= value.keys():
            yield path, value
        else:
            for name, item in value.items():
                yield from _references(item, path + "." + name)
    elif isinstance(value, list):
        for number, item in enumerate(value):
            yield from _references(item, f"{path}[{number}]")


class ScopeHistory:
    def __init__(self, records, as_of):
        require(isinstance(records, list) and records, "Actual collected scope originals required")
        self.rows, self.index, self.joins = [], {}, []
        cutoff, now = _time(as_of), _time(datetime.now(UTC).isoformat())
        for record in records:
            source, receipt, raw = record["source"], record["receipt"], record["retained_bytes"]
            require(
                set(CLOCK_ID) <= source.keys()
                and type(source["version"]) is int
                and source["version"] > 0
                and all(isinstance(source[k], str) and source[k] for k in NATIVE_ID[:-1]),
                "Strict complete collected native identity required",
            )
            require(
                isinstance(raw, bytes)
                and type(receipt.get("content_bytes")) is int
                and receipt["content_bytes"] == len(raw)
                and type(receipt["source"].get("version")) is int
                and all(receipt["source"].get(k) == source[k] for k in CLOCK_ID)
                and all(
                    isinstance(receipt.get(k), str) and receipt[k]
                    for k in ("engagement_id", "principal_id", "command_id")
                )
                and isinstance(record["artifact_id"], str)
                and record["artifact_id"],
                "Actual ordinary receipt, bytes and collecting identity required",
            )
            require(
                hashlib.sha256(raw).hexdigest() == source["sha256"] == record["artifact_sha256"]
                and _time(source["available_at"]) <= _time(receipt["simulated_as_of"]) <= cutoff
                and (
                    source["event_at"] is None
                    or _time(source["event_at"]) <= _time(source["available_at"])
                )
                and _time(source["imported_at"]) <= _time(receipt["collected_at"]) <= now,
                "Collected scope custody hash or clocks differ",
            )
            family, role = record["logical_family"], record["logical_system"]
            require(
                family in FAMILIES and source["system"] == family + "." + role,
                "Actual native scope role differs from route",
            )
            require(
                record["content_type"] in {"application/json", "text/plain"},
                "Declared scope content type required",
            )
            body = json.loads(raw) if record["content_type"] == "application/json" else None
            require(
                body is None or isinstance(body, dict), "Typed scope business document required"
            )
            if body is not None:
                for clock in ("event_at", "available_at"):
                    require(
                        clock not in body or body[clock] == source[clock],
                        "Document scope clocks differ",
                    )
                for flag in (
                    "fixture_contains_real_phi",
                    "real_world_operation",
                    "actual_real_world_phi_processing",
                    "real_signature_or_agreement",
                    "real_world_legal_approval",
                    "real_external_signature",
                    "2027_legal_text_verified",
                    "exception_open",
                    "included_in_service_boundary",
                    "contract_executed_in_simulation",
                    "fictional_in_universe_contract_executed",
                    "fictional_in_universe_operating_release",
                    "actual_credentials_verified",
                    "professional_external_opinion_authority",
                    "independent_from_preparation_and_operation",
                    "source_complete",
                    "complete_soc2_description_or_external_opinion",
                    "entire_service_or_period_assessed",
                    "forecast_positions_are_operating_workers",
                    "employment_appointments_made",
                ):
                    require(
                        flag not in body or type(body[flag]) is bool,
                        "Strict scope Boolean required",
                    )
                if "payload_bytes" in body:
                    require(
                        type(body["payload_bytes"]) is int and body["payload_bytes"] >= 0,
                        "Strict declared payload byte count required",
                    )
            key = _native_key(source)
            require(key not in self.index, "Duplicate scope native version")
            row = {**record, "document": body}
            self.rows.append(row)
            self.index[key] = row
        require(
            len({(r["source"]["company"], r["source"]["branch"]) for r in self.rows}) == 1
            and len(
                {(r["receipt"]["engagement_id"], r["receipt"]["principal_id"]) for r in self.rows}
            )
            == 1
            and len({r["artifact_id"] for r in self.rows}) == len(self.rows),
            "One actually collected branch/engagement/principal and distinct artifacts required",
        )
        for row in self.rows:
            for path, ref in _references(row["document"]):
                require(
                    set(BUSINESS_ID) <= ref.keys()
                    and type(ref["version"]) is int
                    and ref["version"] > 0,
                    "Exact strict-version business reference required",
                )
                target = self.index.get(_native_key(ref))
                if (ref["company"], ref["branch"]) != (
                    row["source"]["company"],
                    row["source"]["branch"],
                ):
                    status = "OUTSIDE_COLLECTED_BRANCH_AUTHORITY"
                elif target is None:
                    status = "ORIGINAL_NOT_COLLECTED"
                else:
                    fields = CLOCK_ID if "imported_at" in ref else BUSINESS_ID
                    require(
                        all(ref[k] == target["source"][k] for k in fields),
                        "Collected scope reference hash or clocks differ",
                    )
                    status = (
                        "EXACT_AVAILABLE_ORIGINAL"
                        if row["source"]["event_at"] is not None
                        and _time(target["source"]["available_at"])
                        <= _time(row["source"]["event_at"])
                        else "SOURCE_UNAVAILABLE_AT_COMPANY_EVENT"
                    )
                self.joins.append(
                    {"from": _pointer(row), "path": path, "reference": ref, "status": status}
                )

    def selected(self, *systems):
        return [
            r for r in self.rows if r["source"]["system"] in systems and r["document"] is not None
        ]


def _observation(name, row, facts, *, status="OBSERVED", locator="$"):
    if not facts:
        facts = {
            "boundary": "Expected fact fields are absent from this retained typed original",
            "native_system": row["source"]["system"],
        }
        status = "SUPPORT_UNAVAILABLE"
    return {
        "id": name + "-" + row["artifact_id"],
        "facts": facts,
        "status": status,
        "evidence": [
            {
                "artifact_id": row["artifact_id"],
                "sha256": row["artifact_sha256"],
                "locator": locator,
            }
        ],
    }


def _fields(row, names):
    body = row["document"]
    return {name: body[name] for name in names if name in body}


def _service_facts(history):
    out = []
    for row in history.selected("phi_ba.operation_scope"):
        out.append(
            _observation(
                "entity-and-separate-flow-scope",
                row,
                _fields(
                    row,
                    (
                        "fictional_contracting_entity_id",
                        "sim_service_id",
                        "sim_customer_id",
                        "sim_subcontractor_id",
                        "data_class",
                        "declared_responsibilities",
                        "site_provider_ba_status",
                        "actual_sable_harbor_ba_status",
                        "transition_release_refs",
                        "fixture_contains_real_phi",
                        "actual_legal_applicability",
                    ),
                ),
            )
        )
    for row in history.selected("transition.site_release", "transition.provider_contract"):
        out.append(
            _observation(
                "dated-site-or-contract",
                row,
                _fields(
                    row,
                    (
                        "site",
                        "status",
                        "fictional_in_universe_operating_release",
                        "fictional_in_universe_contract_executed",
                        "fictional_executed_terms",
                        "data_class",
                        "business_associate_role",
                        "customer_duties_status",
                        "signatory_authority_status",
                        "actor_authority_limit",
                        "real_external_signature",
                    ),
                ),
            )
        )
    for row in history.selected(
        "phi_ba.flow_register", "phi_ba.contract_register", "phi_ba.legal_decision"
    ):
        body = row["document"]
        out.append(
            _observation(
                "synthetic-flow-contract-or-role-history",
                row,
                _fields(
                    row,
                    (
                        "action",
                        "before",
                        "after",
                        "sim_service_id",
                        "site_route",
                        "payload_bytes",
                        "fixture_contains_real_phi",
                        "flow_gate_disposition",
                        "simulated_copy_reached_support",
                        "destination_ack",
                        "contract_id",
                        "contract_party_ids",
                        "contract_executed_in_simulation",
                        "simulated_contract_effective_at",
                        "legal_role_decision",
                        "actual_legal_applicability",
                        "actor_id",
                        "actor_authority",
                        "exception_id",
                        "exception_open",
                    ),
                ),
                status="EXCEPTION_RECORDED" if body.get("exception_open") is True else "OBSERVED",
            )
        )
    for row in history.selected("person-access-history.account_system_inventory"):
        systems = row["document"].get("systems")
        require(
            isinstance(systems, list)
            and all(
                isinstance(s, dict) and isinstance(s.get("system"), str) and s["system"]
                for s in systems
            ),
            "Declared local system inventory required",
        )
        require(
            len({s["system"] for s in systems}) == len(systems),
            "Unique declared local systems required",
        )
        out.append(
            _observation(
                "declared-local-system-population",
                row,
                {
                    "recomputed_declared_system_count": len(systems),
                    **_fields(row, ("systems", "other_estate_inventory", "authority", "catalogue")),
                },
            )
        )
    for row in history.selected(
        "person-access-history.company_authority",
        "person-access-history.service_delegation",
        "person-access-history.contractor_relationship",
    ):
        out.append(
            _observation(
                "dated-attributed-operating-authority",
                row,
                _fields(
                    row,
                    (
                        "issued_by",
                        "management_acceptance",
                        "scope",
                        "effective_from",
                        "effective_to",
                        "operating_access_ready_from",
                        "closing_authority_until",
                        "delegations",
                        "reserved_authority",
                        "employment_appointments_made",
                        "forecast_positions_are_operating_workers",
                        "actor_id",
                        "capacity",
                        "appointment_is_employment",
                        "office_status",
                        "service_effective_from",
                        "service_effective_to",
                        "sponsor",
                        "accepted_terms",
                    ),
                ),
            )
        )
    affiliations = history.selected("person-access-history.affiliation_register")
    if affiliations:
        # Count declared records by actual native record identity. Person/display
        # IDs alone can be reused by proposed contacts and are never a join key.
        latest = {}
        for row in sorted(
            affiliations, key=lambda r: (_time(r["source"]["available_at"]), r["source"]["version"])
        ):
            body = row["document"]
            require(
                type(body.get("included_in_service_boundary")) is bool
                and isinstance(body.get("relationship_kind"), str),
                "Typed affiliation boundary and relationship required",
            )
            latest[row["source"]["record"]] = row
            out.append(
                _observation(
                    "dated-affiliation-boundary",
                    row,
                    _fields(
                        row,
                        (
                            "person_id",
                            "name",
                            "relationship_kind",
                            "employer_legal_entity",
                            "source_status",
                            "source_titles",
                            "included_in_service_boundary",
                            "inclusion_or_exclusion_reason",
                            "service_effective_from",
                            "service_effective_to",
                            "employment_start",
                            "employment_start_basis",
                            "joining_records",
                        ),
                    ),
                    status=(
                        "EXCEPTION_RECORDED"
                        if body["included_in_service_boundary"]
                        and body["relationship_kind"] == "PROPOSED_CONTACT"
                        else "OBSERVED"
                    ),
                )
            )
        out.append(
            _observation(
                "collected-affiliation-denominator",
                affiliations[-1],
                {
                    "distinct_native_affiliation_records": len(latest),
                    "latest_declared_relationship_counts": dict(
                        Counter(r["document"]["relationship_kind"] for r in latest.values())
                    ),
                    "latest_declared_included_records": sum(
                        r["document"]["included_in_service_boundary"] for r in latest.values()
                    ),
                    "employee_account_census_or_enterprise_completeness": "NOT_INFERRED",
                },
            )
        )
    for row in history.selected("assuranceops.assurance_scope"):
        out.append(
            _observation(
                "separate-selected-assurance-boundary",
                row,
                _fields(
                    row,
                    (
                        "boundary_id",
                        "service_id",
                        "scope_services",
                        "scope_sites",
                        "period",
                        "excluded",
                        "exclusion_reason",
                        "scope_decision_owner",
                    ),
                ),
            )
        )
    return out


def _qualified_dependencies(history):
    out = []
    for row in history.selected(
        "legprovision.provision_locator",
        "legprovision.obligation_snapshot",
        "legprovision.overlay_reconciliation",
    ):
        body, detail = row["document"], row["document"].get("detail", {})
        require(isinstance(detail, dict), "Structured legal reference scope required")
        out.append(
            _observation(
                "edition-status-and-applicability",
                row,
                {
                    **_fields(
                        row,
                        (
                            "2027_legal_text_verified",
                            "counsel_person_id",
                            "actual_phi",
                            "real_hipaa_applicability",
                            "source_complete",
                        ),
                    ),
                    "declared_reference": {
                        k: detail[k]
                        for k in (
                            "provision",
                            "locator_status",
                            "qualified_review_status",
                            "required_qualified_review_inputs",
                            "applicability_status",
                            "counsel_authority",
                            "publication_status_hold",
                            "source_research_accessed",
                            "predecessor_legal_reference_checked_as_of",
                            "open_historical_exception_ids",
                            "nonoccurrence_status",
                            "performance_fact_status",
                            "contract_term_status",
                            "selected_term_count",
                            "chain",
                        )
                        if k in detail
                    },
                },
                status="SUPPORT_UNAVAILABLE"
                if body.get("2027_legal_text_verified") is not True
                else "OBSERVED",
            )
        )
    for row in history.selected(
        "assuranceops.assurance_independence",
        "assuranceops.assurance_review",
        "govapp.selected_application",
        "govapp.control_mapping",
    ):
        body = row["document"]
        preparer = body.get("preparer_id")
        reviewers = {key: body.get(key) for key in ("reviewer_id", "quality_reviewer_id")}
        require(
            all(
                value is None or isinstance(value, str) and value
                for value in [preparer, *reviewers.values()]
            ),
            "Typed attributed preparer and reviewer identities required",
        )
        self_review = {
            key: preparer is not None and preparer == value for key, value in reviewers.items()
        }
        out.append(
            _observation(
                "attributed-selected-company-review",
                row,
                {
                    **_fields(
                        row,
                        (
                            "actor_person_id",
                            "preparer_id",
                            "reviewer_id",
                            "quality_reviewer_id",
                            "scope_decision_owner",
                            "competence_basis",
                            "actual_credentials_verified",
                            "professional_external_opinion_authority",
                            "reviewer_identity_type",
                            "independent_from_preparation_and_operation",
                            "review_disposition",
                            "description_version",
                            "period",
                            "service_id",
                            "boundary_id",
                            "entire_service_or_period_assessed",
                            "complete_soc2_description_or_external_opinion",
                            "status",
                            "selected_control",
                            "source_refs",
                        ),
                    ),
                    "actual_preparer_equals_each_reviewer": self_review,
                    "qualified_acceptance_for_this_audit": "NOT_INFERRED_FROM_COMPANY_REVIEW",
                },
                status="EXCEPTION_RECORDED" if any(self_review.values()) else "OBSERVED",
            )
        )
    for row in history.rows:
        body = row["document"]
        if body and body.get("exception_open") is True:
            out.append(
                _observation(
                    "original-open-exception-history",
                    row,
                    _fields(
                        row,
                        (
                            "exception_id",
                            "exception_open",
                            "detected_at",
                            "cure_status",
                            "before",
                            "after",
                            "action",
                        ),
                    ),
                    status="EXCEPTION_RECORDED",
                )
            )
    return out


def examine(records, *, as_of, scratch_root=None):
    """Two distinct bounded inspections; qualified/owner dependency stays open."""
    del scratch_root
    history = ScopeHistory(records, as_of)
    results = []
    required = {
        TASKS[0]: {
            "source-edition-status": ("legprovision.provision_locator",),
            "conditions-and-exceptions": ("legprovision.obligation_snapshot",),
            "scoped-applicability": ("phi_ba.legal_decision", "legprovision.provision_locator"),
            "attributed-design-review": (
                "assuranceops.assurance_review",
                "assuranceops.assurance_independence",
            ),
        },
        TASKS[1]: {
            "entity-and-service": ("phi_ba.operation_scope",),
            "site-boundary": ("transition.site_release", "assuranceops.assurance_scope"),
            "data-flow": ("phi_ba.flow_register",),
            "agreements": ("phi_ba.contract_register", "transition.provider_contract"),
            "system-and-person-populations": (
                "person-access-history.account_system_inventory",
                "person-access-history.affiliation_register",
            ),
            "execution-owners": ("person-access-history.company_authority",),
        },
    }
    for task, observations in zip(
        TASKS, (_qualified_dependencies(history), _service_facts(history)), strict=True
    ):
        for attribute, systems in required[task].items():
            absent = [system for system in systems if not history.selected(system)]
            if absent:
                observations.append(
                    _observation(
                        "uncollected-" + attribute,
                        history.rows[0],
                        {
                            "attribute": attribute,
                            "typed_native_roles_absent_from_retained_inputs": absent,
                            "company_nonoccurrence_or_inapplicability": "NOT_INFERRED",
                        },
                        status="SUPPORT_UNAVAILABLE",
                    )
                )
        if task == TASKS[1]:
            dated = [r for r in history.rows if r["source"]["event_at"] is not None]
            observations.append(
                _observation(
                    "collected-operating-period-bounds",
                    history.rows[0],
                    {
                        "earliest_retained_event": min(
                            (r["source"]["event_at"] for r in dated), key=_time, default=None
                        ),
                        "latest_retained_event": max(
                            (r["source"]["event_at"] for r in dated), key=_time, default=None
                        ),
                        "latest_retained_publication": max(
                            (r["source"]["available_at"] for r in history.rows), key=_time
                        ),
                        "declared_company_assurance_periods": [
                            _fields(r, ("period", "service_id", "boundary_id"))
                            for r in history.selected("assuranceops.assurance_scope")
                        ],
                        "continuous_full_year_operation": (
                            "NOT_ESTABLISHED_BY_RETAINED_EVENT_BOUNDS"
                        ),
                    },
                    locator="ordinary_receipt.source.event_at/available_at",
                )
            )
        if not observations:
            observations = [
                _observation(
                    "required-typed-source-not-collected",
                    history.rows[0],
                    {
                        "task_id": task,
                        "boundary": (
                            "Required typed source roles are absent from these collected originals"
                        ),
                    },
                    status="SUPPORT_UNAVAILABLE",
                )
            ]
        for row in history.rows:
            unresolved = [
                j
                for j in history.joins
                if j["from"] == _pointer(row) and j["status"] != "EXACT_AVAILABLE_ORIGINAL"
            ]
            if unresolved:
                observations.append(
                    _observation(
                        "declared-dependency-limit",
                        row,
                        {"unresolved_exact_native_dependencies": unresolved},
                        status="SUPPORT_UNAVAILABLE",
                    )
                )
            if row["document"] is None:
                observations.append(
                    _observation(
                        "unparsed-original-limit",
                        row,
                        {
                            "content_type": row["content_type"],
                            "boundary": (
                                "Retained original cited without inventing a parsed decision"
                            ),
                        },
                        status="SUPPORT_UNAVAILABLE",
                    )
                )
        evidence = sorted({e["artifact_id"] for o in observations for e in o["evidence"]})
        results.append(
            {
                "task_id": task,
                "artifact_ids": evidence,
                "observations": observations,
                "performed": CONTRACTS[task]["performed"],
                "unperformed": CONTRACTS[task]["unperformed"],
                "result": {
                    "examination_as_of": as_of,
                    "observations": len(observations),
                    "observed_exception_records": sum(
                        o["status"] == "EXCEPTION_RECORDED" for o in observations
                    ),
                    "support_unavailable_records": sum(
                        o["status"] == "SUPPORT_UNAVAILABLE" for o in observations
                    ),
                    "native_dependency_reconciliation": history.joins,
                    "actual_professional_or_owner_acceptance": "NOT_ASSERTED",
                    "company_decisions_are_attributed_business_evidence": True,
                    "full_enterprise_or_annual_assurance": False,
                },
                "disposition": {
                    "status": "IN_PROGRESS",
                    "conclusion": "LIMITATION",
                    "rationale": CONTRACTS[task]["unperformed"],
                },
            }
        )
    return results
