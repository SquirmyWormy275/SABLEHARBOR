"""Sixty-two governance/risk/policy examinations of ordinary retained originals.

No company database, stored query, Key, cached method result or outside standard
is read by this pure callback. Governance decisions are source records rather
than qualified approval, and local trials remain local with their actual dates.
"""

from __future__ import annotations

import calendar
import hashlib
import json
import math
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path

from .company_store import _time
from .fresh_sec003_procedure import CLOCK_ID, NATIVE_ID, require

BUSINESS_ID = tuple(k for k in CLOCK_ID if k != "imported_at")
FAMILIES = {
    "govapp",
    "govoversight",
    "risk-history",
    "baseline-risk",
    "policy",
    "pol004procedure",
    "addressabledocket",
    "eth003",
    "eth004",
    "supplementalops",
    "bcm",
    "phi_ba",
    "legprovision",
    "legint",
    "legaloriginals",
    "transition",
    "incident-history",
    "prdconcern",
    "controlled_record",
    "privacyops",
    "processing",
}
PLAN_SHA = "9583a9dcd37e51242f4b597d8ffae72abfdf87790543201e0f88bfa751555519"


def _key(source):
    return tuple(source[k] for k in NATIVE_ID)


def _references(value, path="$"):
    if isinstance(value, dict):
        if set(NATIVE_ID) <= value.keys():
            yield path, value
        else:
            for key, child in value.items():
                yield from _references(child, path + "." + key)
    elif isinstance(value, list):
        for number, child in enumerate(value):
            yield from _references(child, f"{path}[{number}]")


class History:
    def __init__(self, records, as_of):
        self.as_of = _time(as_of)
        self.rows, self.index = [], {}
        for record in records:
            source, receipt, raw = record["source"], record["receipt"], record["retained_bytes"]
            require(set(CLOCK_ID) <= source.keys(), "Full native source clocks required")
            require(
                type(source["version"]) is int and source["version"] > 0,
                "Strict native version required",
            )
            require(
                all(isinstance(source[k], str) and source[k] for k in NATIVE_ID[:-1]),
                "Explicit native identity required",
            )
            require(isinstance(raw, bytes), "Actual retained bytes required")
            require(
                hashlib.sha256(raw).hexdigest() == source["sha256"] == record["artifact_sha256"],
                "Actual retained hash differs",
            )
            require(
                type(receipt.get("content_bytes")) is int and receipt["content_bytes"] == len(raw),
                "Actual receipt byte count differs",
            )
            require(
                type(receipt["source"]["version"]) is int
                and all(receipt["source"].get(k) == source[k] for k in CLOCK_ID),
                "Exact receipt source required",
            )
            require(
                all(
                    isinstance(receipt.get(k), str) and receipt[k]
                    for k in ["engagement_id", "principal_id", "command_id"]
                ),
                "Actual collection identities required",
            )
            require(
                _time(source["event_at"])
                <= _time(source["available_at"])
                <= _time(receipt["simulated_as_of"])
                <= self.as_of,
                "Native occurrence/publication/collection chronology differs",
            )
            require(
                _time(source["imported_at"])
                <= _time(receipt["collected_at"])
                <= _time(datetime.now(UTC).isoformat()),
                "Real import and collection chronology differs",
            )
            family, role = record["logical_family"], record["logical_system"]
            require(
                family in FAMILIES and source["system"] == family + "." + role,
                "Exact declared native governance/context role required",
            )
            require(
                record["content_type"] in {"application/json", "text/plain"},
                "Typed retained original required",
            )
            body = (
                json.loads(raw)
                if record["content_type"] == "application/json"
                else raw.decode("utf-8")
            )
            require(
                isinstance(body, (dict, str)),
                "Structured or explicit unparsed business original required",
            )
            if isinstance(body, dict):
                for identity_field in ("company", "branch"):
                    require(
                        identity_field not in body
                        or body[identity_field] == source[identity_field],
                        "Original body company/branch differs from native custody",
                    )
                require(
                    "version" not in body or type(body["version"]) is int,
                    "Strict original body version required",
                )
                for clock in ["event_at", "available_at"]:
                    require(
                        clock not in body or _time(body[clock]) == _time(source[clock]),
                        "Body clock differs from custody",
                    )
                for name in [
                    "finding_closed",
                    "actual_credentials_verified",
                    "reviewer_prepared_tests",
                    "preparer_operating_control_ownership",
                    "reviewer_operating_control_ownership",
                ]:
                    require(
                        name not in body or type(body[name]) is bool,
                        "Strict company decision Boolean required",
                    )
            require(_key(source) not in self.index, "Distinct collected native versions required")
            row = {**record, "document": body}
            self.rows.append(row)
            self.index[_key(source)] = row
        require(self.rows, "Actual collected originals required")
        require(
            len({r["artifact_id"] for r in self.rows}) == len(self.rows),
            "Distinct actual artifact identities required",
        )
        require(
            len({(r["receipt"]["engagement_id"], r["receipt"]["principal_id"]) for r in self.rows})
            == 1,
            "One actual collecting engagement/principal required",
        )
        require(
            len({(r["source"]["company"], r["source"]["branch"]) for r in self.rows}) == 1,
            "One collected branch required",
        )

    def selected(self, systems):
        return [
            r
            for r in self.rows
            if r["source"]["system"] in systems and isinstance(r["document"], dict)
        ]

    def resolve(self, origin, ref, roles=None):
        if str(ref.get("status", "")).startswith("RESTRICTED"):
            return None, "RESTRICTED_REFERENCE_NOT_REBASED"
        require(
            set(BUSINESS_ID) <= ref.keys() and type(ref["version"]) is int and ref["version"] > 0,
            "Strict exact native pointer required",
        )
        if any(ref[k] != origin["source"][k] for k in ["company", "branch"]):
            return None, "OUTSIDE_COLLECTED_BRANCH_AUTHORITY"
        target = self.index.get(_key(ref))
        if target is None:
            return None, "ORIGINAL_NOT_COLLECTED"
        require(
            all(
                ref[k] == target["source"][k]
                for k in (CLOCK_ID if "imported_at" in ref else BUSINESS_ID)
            ),
            "Exact target hash/clocks differ",
        )
        if roles is not None and target["source"]["system"] not in roles:
            return None, "ACTUAL_NATIVE_ROLE_DIFFERS"
        if _time(target["source"]["available_at"]) > _time(origin["source"]["event_at"]):
            return None, "SOURCE_UNAVAILABLE_AT_COMPANY_EVENT"
        if not _action_supported(origin) or not _action_supported(target):
            return None, "RECORDED_ACTION_UNAVAILABLE_AT_NATIVE_EVENT"
        return target, "EXACT_AVAILABLE_ORIGINAL"


def _observation(label, facts, rows, *, status="OBSERVED", locator="$"):
    rows = list({r["artifact_id"]: r for r in rows}.values())
    return {
        "id": label,
        "facts": facts,
        "status": status,
        "evidence": [
            {"artifact_id": r["artifact_id"], "sha256": r["artifact_sha256"], "locator": locator}
            for r in rows
        ],
    }


def _partition_citations(observations):
    """Preserve every original while honoring the writer's twenty-citation cap."""
    result = []
    for observation in observations:
        evidence = observation["evidence"]
        if len(evidence) <= 20:
            result.append(observation)
            continue
        chunks = [evidence[start : start + 20] for start in range(0, len(evidence), 20)]
        for number, chunk in enumerate(chunks, 1):
            result.append(
                {
                    **observation,
                    "id": observation["id"] + "-citations-" + str(number),
                    "evidence": chunk,
                    "facts": {
                        "aggregate_facts": observation["facts"],
                        "citation_partition": number,
                        "citation_partitions": len(chunks),
                        "all_citation_part_ids": [
                            observation["id"] + "-citations-" + str(i)
                            for i in range(1, len(chunks) + 1)
                        ],
                        "aggregate_requires_all_citation_partitions": True,
                    },
                }
            )
    return result


def task_plan():
    raw = Path(__file__).with_name("governance_collected_task_plan_v1.json").read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PLAN_SHA, "Exact authored B07 plan required")
    plan = json.loads(raw)
    require(plan["task_count"] == len(plan["tasks"]) == 62, "Exact sixty-two B07 tasks required")
    return plan["tasks"]


def contracts():
    return {
        t["task_id"]: {
            "performed": "Reperform selected retained-original attributes for "
            + t["task_id"]
            + ": "
            + t["authored_instruction"],
            "unperformed": t["task_kind_rule"] + " Entire enterprise/year populations, "
            "actual appointment/standards/applicability/design decisions and independent "
            "operating sufficiency remain unestablished; exact missing facets are listed.",
            "allowed_dispositions": [
                {"status": "IN_PROGRESS", "conclusion": c} for c in ("LIMITATION", "FAIL")
            ],
        }
        for t in task_plan()
    }


ROLES = {
    "SH-GOV-001": {
        "govapp.board_decision",
        "govapp.board_member_action",
        "govoversight.charter_register",
        "govoversight.committee_note",
        "govoversight.audit_committee_packet",
        "govoversight.action_register",
    },
    "SH-GOV-003": {
        "govapp.ceo_delegation",
        "govapp.ceo_disposition",
        "govapp.control_mapping",
        "supplementalops.local_authority",
    },
    "SH-GOV-004": {
        "govoversight.committee_roster",
        "govoversight.conflict_questionnaire",
        "govoversight.eligibility_review",
        "govoversight.committee_note",
    },
    "SH-ERM-001": {
        "risk-history.risk_input_ledger",
        "risk-history.risk_assessments",
        "risk-history.risk_import_configuration",
        "risk-history.risk_reconciliation",
        "risk-history.risk_reviews",
        "baseline-risk.risk_assessments",
    },
    "SH-ERM-002": {"govapp.appetite_motion", "govapp.measure_challenge", "govapp.board_decision"},
    "SH-ERM-003": {
        "govapp.waiver_request",
        "govapp.ceo_disposition",
        "govapp.selected_application",
        "govapp.security_challenge",
        "govapp.appetite_motion",
        "govapp.board_decision",
        "risk-history.risk_followup",
    },
    "SH-ERM-004": {
        "risk-history.risk_input_ledger",
        "risk-history.risk_followup",
        "supplementalops.risk_decision",
        "supplementalops.procedure_operation",
        "supplementalops.communication_directory",
        "supplementalops.policy_document",
        "supplementalops.communication_event",
    },
    "SH-POL-001": {
        "policy.policy_baseline",
        "policy.policy_revision",
        "policy.revision_review",
        "policy.distribution_plan",
        "policy.local_delivery",
        "policy.distribution_reconcile",
        "supplementalops.policy_document",
        "supplementalops.communication_event",
        "supplementalops.communication_directory",
        "supplementalops.privacy_responsibility",
        "supplementalops.retention_register",
    },
    "SH-POL-002": {"govapp.control_mapping", "govapp.ceo_delegation"},
    "SH-POL-003": {
        "addressabledocket.addressable_candidate",
        "addressabledocket.docket_event",
        "supplementalops.risk_decision",
        "supplementalops.security_configuration",
    },
    "SH-POL-004": {
        "pol004procedure.procedure_candidate",
        "pol004procedure.approval_gate",
        "pol004procedure.due_trigger",
        "pol004procedure.execution_trace",
        "pol004procedure.challenge",
        "pol004procedure.result_register",
        "supplementalops.procedure_document",
        "supplementalops.procedure_calendar",
        "supplementalops.procedure_operation",
    },
    "SH-ETH-003": {
        "eth003.report_intake",
        "eth003.separate_triage",
        "eth003.protective_handling",
        "eth003.case_state",
        "supplementalops.workforce_case",
        "supplementalops.responsibility_feedback",
        "legint.legal_response_exercise",
        "legint.regulatory_response_playbook",
        "legint.legal_matter_classification",
        "legaloriginals.legal_inbound_message",
        "legaloriginals.legal_inbound_attachment",
    },
    "SH-ETH-004": {"eth004.conflict_intake", "eth004.conflict_gate", "eth004.risk_review"},
}


def _current(history, roles):
    selected = {}
    for row in history.selected(roles):
        key = _key(row["source"])[:-1]
        if key not in selected or row["source"]["version"] > selected[key]["source"]["version"]:
            selected[key] = row
    return list(selected.values())


def _digest_target(history, origin, digest, roles):
    if not isinstance(digest, str) or len(digest) != 64:
        return None, "TYPED_DECLARED_DIGEST_ABSENT"
    targets = [r for r in history.selected(roles) if r["source"]["sha256"] == digest]
    if len(targets) != 1:
        return None, "EXACT_TYPED_ORIGINAL_NOT_COLLECTED_OR_AMBIGUOUS"
    row = targets[0]
    if _time(row["source"]["available_at"]) > _time(origin["source"]["event_at"]):
        return None, "ORIGINAL_UNAVAILABLE_AT_RECORDED_DECISION"
    if not _action_supported(origin) or not _action_supported(row):
        return None, "RECORDED_ACTION_UNAVAILABLE_AT_NATIVE_EVENT"
    return row, "EXACT_TYPED_CAUSALLY_AVAILABLE_ORIGINAL"


def _obs(label, facts, rows, *, status="OBSERVED", locator="$"):
    digest = hashlib.sha256(label.encode()).hexdigest()[:20]
    return _observation("gov-" + digest, facts, rows, status=status, locator=locator)


def _links(history, row):
    facts, originals = [], [row]
    for path, ref in _references(row["document"]):
        target, status = history.resolve(row, ref)
        facts.append({"locator": path, "status": status, "source": ref})
        if target:
            originals.append(target)
    return facts, originals


def _risk(history):
    observations = []
    for row in history.selected(
        {"risk-history.risk_assessments", "baseline-risk.risk_assessments"}
    ):
        body = row["document"]
        links, originals = _links(history, row)
        risks = body.get("risks", [])
        require(isinstance(risks, list), "Typed risk scenario vector required")
        _ids([risk["id"] for risk in risks])
        computed = []
        for risk in risks:
            require(
                type(risk.get("inherent_local_score")) is int
                and type(risk.get("projected_residual_local_score")) is int,
                "Strict recorded risk scores required",
            )
            values = {
                k: risk.get(k)
                for k in ["likelihood", "impact", "projected_likelihood", "projected_impact"]
            }
            require(
                all(type(v) is int and 1 <= v <= 5 for v in values.values()),
                "Strict ordinal risk factors required",
            )
            inherent = values["likelihood"] * values["impact"]
            projected = values["projected_likelihood"] * values["projected_impact"]
            computed.append(
                {
                    "scenario": risk.get("id"),
                    "input_id": risk.get("input_id"),
                    "recomputed_inherent_local_score": inherent,
                    "recorded_inherent_local_score": risk.get("inherent_local_score"),
                    "recomputed_projected_local_score": projected,
                    "recorded_projected_local_score": risk.get("projected_residual_local_score"),
                    "score_matches": inherent == risk.get("inherent_local_score")
                    and projected == risk.get("projected_residual_local_score"),
                    "assumption_basis": risk.get("assumption_rationale"),
                    "accountable_owner": risk.get("management_owner_id"),
                    "treatment": risk.get("treatment_proposal"),
                    "treatment_status": risk.get("treatment_status"),
                    "risk_acceptance": risk.get("risk_acceptance"),
                    "projected_score_is_achieved_residual_risk": False,
                }
            )
        observations.append(
            _obs(
                str(_key(row["source"])) + "risk",
                {
                    "native_scenarios": computed,
                    "source_links": links,
                    "period_start": body.get("period_start"),
                    "period_end_exclusive": body.get("period_end_exclusive"),
                    "actual_selected_scenario_count": len(risks),
                    "recorded_coverage": body.get("coverage"),
                    "quarterly_corporate_risk_universe_established": False,
                    "outage_hypothesis_is_observed_supplier_outage": False,
                },
                originals,
                status="SUPPORT_UNAVAILABLE"
                if not _action_supported(row)
                else "EXCEPTION_RECORDED"
                if any(not r["score_matches"] for r in computed)
                else "OBSERVED",
                locator="$.risks",
            )
        )
    for row in history.selected(
        {"risk-history.risk_reconciliation", "baseline-risk.risk_reconciliation"}
    ):
        body = row["document"]
        declared, included = body.get("declared_input_ids", []), body.get("imported_input_ids", [])
        require(
            isinstance(declared, list) and isinstance(included, list),
            "Typed risk input census required",
        )
        declared_ids, included_ids = _ids(declared), _ids(included)
        missing, extra = sorted(declared_ids - included_ids), sorted(included_ids - declared_ids)
        observations.append(
            _obs(
                str(_key(row["source"])) + "risk-inputs",
                {
                    "declared_selected_inputs": declared,
                    "imported_selected_inputs": included,
                    "recomputed_missing_inputs": missing,
                    "recomputed_unexpected_inputs": extra,
                    "reported_missing_inputs": body.get("missing_declared_input_ids"),
                    "reported_unexpected_inputs": body.get("unexpected_input_ids"),
                    "whole_enterprise_population_is_established": False,
                },
                [row],
                status="EXCEPTION_RECORDED" if missing or extra else "OBSERVED",
            )
        )
    return observations


def _governing_decisions(history):
    observations = []
    for row in history.selected({"govapp.board_decision"}):
        body = row["document"]
        for field in ("support_count", "dissent_count"):
            require(
                type(body.get(field)) is int and body[field] >= 0,
                "Strict recorded board vote count required",
            )
        motion, status = _digest_target(
            history, row, body.get("accepted_motion_sha256"), {"govapp.appetite_motion"}
        )
        actions, absent = [], []
        for action in body.get("member_actions", []):
            target, reason = _digest_target(
                history, row, action.get("action_sha256"), {"govapp.board_member_action"}
            )
            if (
                target
                and target["document"].get("motion_sha256") == body.get("accepted_motion_sha256")
                and target["document"].get("actor_id") == action.get("director_id")
                and target["document"].get("vote") == action.get("vote")
                and isinstance(action.get("event_at"), str)
                and _time(action["event_at"]) == _time(target["source"]["event_at"])
            ):
                actions.append(target)
            else:
                absent.append({"member": action.get("director_id"), "reason": reason})
        members = [r["document"].get("actor_id") for r in actions]
        originals = {_key(r["source"]): r for r in actions}
        by_member = {}
        for action in originals.values():
            by_member.setdefault(action["document"].get("actor_id"), []).append(action)
        ambiguous = [
            {
                "member": member,
                "actual_originals": [r["source"] for r in rows],
                "reason": "MULTIPLE_DISTINCT_MEMBER_ACTIONS_NO_SELECTED_VOTE",
            }
            for member, rows in by_member.items()
            if len(rows) != 1
        ]
        counted = [rows[0] for rows in by_member.values() if len(rows) == 1]
        votes = Counter(r["document"].get("vote") for r in counted)
        duplicate_originals = len(actions) - len(originals)
        observed = {
            "motion_link": status,
            "distinct_actual_member_actions": len(set(members)),
            "duplicate_member_actions": len(members) - len(set(members)),
            "duplicate_original_references": duplicate_originals,
            "ambiguous_individual_member_actions": ambiguous,
            "counted_individual_member_originals": [r["source"] for r in counted],
            "recomputed_votes": dict(votes),
            "recorded_support_count": body.get("support_count"),
            "recorded_dissent_count": body.get("dissent_count"),
            "missing_member_originals": absent,
            "effective_at": body.get("effective_at"),
            "expires_at": body.get("expires_at"),
            "legal_quorum_or_entire_period_oversight_established": False,
            "fictional_source_vote_is_real_member_signature": False,
        }
        mismatch = votes.get("SUPPORT", 0) != body.get("support_count") or votes.get(
            "DISSENT", 0
        ) != body.get("dissent_count")
        observed["recorded_vote_counts_match_collected_individual_actions"] = (
            not mismatch and not ambiguous
        )
        observations.append(
            _obs(
                str(_key(row["source"])) + "votes",
                observed,
                [row, *actions, *([motion] if motion else [])],
                status="EXCEPTION_RECORDED"
                if mismatch or duplicate_originals or ambiguous
                else "SUPPORT_UNAVAILABLE"
                if motion is None or absent or not actions
                else "OBSERVED",
            )
        )
    return observations


def _authority(history):
    observations = []
    for row in history.selected(
        {
            "govapp.ceo_delegation",
            "govapp.control_mapping",
            "govapp.ceo_disposition",
            "govapp.waiver_request",
        }
    ):
        body = row["document"]
        board, status = _digest_target(
            history,
            row,
            body.get("board_decision_sha256", body.get("source_decision_sha256")),
            {"govapp.board_decision"},
        )
        effective = False
        if board:
            decision = board["document"]
            effective = bool(
                decision.get("effective_at")
                and decision.get("expires_at")
                and _time(decision["effective_at"])
                <= _time(row["source"]["event_at"])
                <= _time(decision["expires_at"])
            )
        assignments = body.get("accountable_roles", {})
        require(isinstance(assignments, dict), "Typed control accountability assignments required")
        technical = assignments.get("technical_owner", body.get("technology_owner_person_id"))
        challenger = assignments.get("security_challenge", body.get("security_challenge_person_id"))
        conflict = (
            technical == challenger
            if isinstance(technical, str)
            and technical
            and isinstance(challenger, str)
            and challenger
            else None
        )
        observations.append(
            _obs(
                str(_key(row["source"])) + "authority",
                {
                    "native_role": row["source"]["system"],
                    "exact_board_link": status,
                    "board_window_effective_at_this_native_event": effective,
                    "recorded_assignment_or_disposition": {
                        k: v
                        for k, v in body.items()
                        if k
                        in {
                            "actor_id",
                            "scope",
                            "accountable_roles",
                            "risk_monitor_person_id",
                            "security_challenge_person_id",
                            "technical_configuration_authority",
                            "waiver_of_board_envelope",
                            "security_official_designation",
                            "decision",
                            "status",
                        }
                    },
                    "named_technical_owner": technical,
                    "named_security_challenger": challenger,
                    "same_named_technical_executor_and_security_challenger": conflict,
                    "compensating_measure_operating_effectiveness_established": False,
                    "title_or_coordination_establishes_reserved_authority": False,
                },
                [row, *([board] if board else [])],
                status="EXCEPTION_RECORDED"
                if conflict is True
                else "OBSERVED"
                if effective
                else "SUPPORT_UNAVAILABLE",
            )
        )
    return observations


def _appetite(history):
    observations = []
    for row in history.selected({"govapp.appetite_motion"}):
        body = row["document"]
        thresholds = {
            k: body.get(k)
            for k in [
                "internal_marker_rpo_minutes_max",
                "internal_marker_rto_minutes_max",
                "unreviewed_boise_key_gate_bypass_tolerance",
            ]
        }
        numeric = all(
            type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in thresholds.values()
        )
        observations.append(
            _obs(
                str(_key(row["source"])) + "appetite",
                {
                    "recorded_measurable_selected_limits": thresholds,
                    "numeric_limits_present": numeric,
                    "recorded_scope": body.get("scope", body.get("selected_service")),
                    "customer_service_commitment": body.get("customer_service_commitment"),
                    "recorded_status": body.get("status"),
                    "threshold_breach_route": body.get("threshold_breach_route"),
                    "material_challenge_route": body.get("material_challenge_route"),
                    "selected_marker_limits_establish_customer_or_whole_service_objectives": False,
                },
                [row],
                status="OBSERVED" if numeric else "SUPPORT_UNAVAILABLE",
            )
        )
    return observations + _governing_decisions(history)


def _policy_distribution(history):
    observations = []
    for plan in history.selected({"policy.distribution_plan"}):
        body = plan["document"]
        endpoints = body.get("recipient_endpoints", [])
        require(
            isinstance(endpoints, list) and len(endpoints) == len(set(endpoints)),
            "Distinct typed policy endpoints required",
        )
        due = _time(body["due_at"])
        deliveries, facts = [], []
        for endpoint in endpoints:
            candidates = [
                r
                for r in history.selected({"policy.local_delivery"})
                if r["document"].get("endpoint") == endpoint
                and r["document"].get("approved_document_sha256")
                == body.get("approved_document_sha256")
            ]
            valid = []
            for row in candidates:
                delivery = row["document"]
                ref = delivery.get("plan_ref")
                target, link = (
                    history.resolve(row, ref, {"policy.distribution_plan"})
                    if isinstance(ref, dict)
                    else (None, "PLAN_REF_ABSENT")
                )
                exact = target is plan and delivery.get("copy_sha256") == delivery.get(
                    "source_sha256"
                ) == body.get("approved_document_sha256")
                if exact:
                    valid.append(row)
                deliveries.append(row)
                facts.append(
                    {
                        "endpoint": endpoint,
                        "source": row["source"],
                        "exact_plan_link": link,
                        "reported_byte_hashes_match_selected_plan": exact,
                        "on_time_by_native_event": exact
                        and _time(row["source"]["event_at"]) <= due,
                        "on_time_by_native_publication": exact
                        and _time(row["source"]["available_at"]) <= due,
                    }
                )
            if not valid:
                facts.append({"endpoint": endpoint, "no_exact_collected_delivery": True})
        on_time = {
            f["endpoint"]
            for f in facts
            if f.get("on_time_by_native_event") and f.get("on_time_by_native_publication")
        }
        missing = sorted(set(endpoints) - on_time)
        observations.append(
            _obs(
                str(_key(plan["source"])) + "distribution",
                {
                    "selected_endpoint_denominator": endpoints,
                    "recomputed_missing_at_due": missing,
                    "actual_delivery_attributes": facts,
                    "human_acknowledgment_or_full_workforce_delivery_established": False,
                    "approved_baseline_is_approval_of_candidate_revision": False,
                },
                [plan, *deliveries],
                status="EXCEPTION_RECORDED" if missing else "OBSERVED",
            )
        )
    return observations


def _ids(values):
    require(
        isinstance(values, list)
        and all(isinstance(v, str) and v for v in values)
        and len(set(values)) == len(values),
        "Distinct typed governance identifier vector required",
    )
    return set(values)


def _action_supported(row):
    body = row["document"]
    if not isinstance(body, dict):
        return False
    times = [
        body[k] for k in ("recorded_at", "received_at", "approved_at", "executed_at") if k in body
    ]
    approval = body.get("approval")
    if isinstance(approval, dict) and "at" in approval:
        times.append(approval["at"])
    return all(isinstance(t, str) and _time(t) <= _time(row["source"]["event_at"]) for t in times)


def _dependencies(history, origin, roles):
    facts, targets = [], []
    for path, ref in _references(origin["document"]):
        if ref.get("system") not in roles:
            continue
        target, status = history.resolve(origin, ref, roles)
        facts.append({"path": path, "reference": ref, "status": status})
        if target is not None:
            targets.append(target)
    return facts, list({_key(r["source"]): r for r in targets}.values())


def _closest(history, origin, roles):
    seen, level = {_key(origin["source"])}, [origin]
    while level:
        following, found = [], {}
        for row in level:
            for _, ref in _references(row["document"]):
                target, status = history.resolve(row, ref)
                if target is None or status != "EXACT_AVAILABLE_ORIGINAL":
                    continue
                identity = _key(target["source"])
                if identity in seen:
                    continue
                seen.add(identity)
                if target["source"]["system"] in roles:
                    found[identity] = target
                else:
                    following.append(target)
        if found:
            return list(found.values())
        level = following
    return []


def _scalar_original(history, origin, locator, roles, *, output_identity=False):
    if not isinstance(locator, str):
        return None, "EXPLICIT_SCALAR_LOCATOR_ABSENT"
    parts = locator.split("/")
    if len(parts) != 3 or not parts[2].isascii() or not parts[2].isdigit() or int(parts[2]) < 1:
        return None, "UNTYPED_SCALAR_LOCATOR_NO_ALIAS"
    systems = {"supplementalops." + parts[0]} & roles
    targets = [
        r
        for r in history.selected(systems)
        if r["source"]["record"] == parts[1] and r["source"]["version"] == int(parts[2])
    ]
    if len(targets) != 1:
        return None, "EXACT_SCALAR_ORIGINAL_MISSING_OR_AMBIGUOUS"
    if output_identity and _key(targets[0]["source"]) == _key(origin["source"]):
        return targets[0], "EXACT_CURRENT_OUTPUT_IDENTITY_NOT_PRIOR_INPUT"
    if _time(targets[0]["source"]["available_at"]) > _time(origin["source"]["event_at"]):
        return None, "ORIGINAL_UNAVAILABLE_AT_COMPANY_EVENT"
    if not _action_supported(origin) or not _action_supported(targets[0]):
        return None, "RECORDED_ACTION_UNAVAILABLE_AT_NATIVE_EVENT"
    return targets[0], "EXACT_SCALAR_VERSION_WITNESS_NOT_NATIVE_POINTER"


def _procedure_due(history):
    observations = []
    operations = history.selected({"supplementalops.procedure_operation"})
    for calendar_row in history.selected({"supplementalops.procedure_calendar"}):
        body = calendar_row["document"]
        due_entries = body.get("scheduled")
        if not isinstance(due_entries, list):
            observations.append(
                _obs(
                    str(_key(calendar_row["source"])) + "calendar-missing",
                    {
                        "declared_scheduled_vector_unavailable": True,
                        "absence_is_not_zero_due_reviews": True,
                    },
                    [calendar_row],
                    status="SUPPORT_UNAVAILABLE",
                )
            )
            continue
        due_times = [d.get("due_at") for d in due_entries]
        require(
            all(
                isinstance(d, dict)
                and isinstance(d.get("trigger_at"), str)
                and isinstance(d.get("due_at"), str)
                for d in due_entries
            )
            and len(set(due_times)) == len(due_times),
            "Distinct typed calendar due vector required",
        )
        for due in due_entries:
            if _time(due["due_at"]) > history.as_of:
                continue
            causal_calendar = _time(calendar_row["source"]["available_at"]) <= _time(
                due["trigger_at"]
            )
            candidates, originals = [], [calendar_row]
            for row in operations:
                if row["document"].get("due_at") != due["due_at"]:
                    continue
                links, targets = _dependencies(history, row, {"supplementalops.procedure_calendar"})
                exact = len(targets) == 1 and _key(targets[0]["source"]) == _key(
                    calendar_row["source"]
                )
                event = _time(row["source"]["event_at"])
                ontime = (
                    causal_calendar
                    and exact
                    and _action_supported(row)
                    and (
                        _time(due["trigger_at"]) <= event <= _time(due["due_at"])
                        and _time(row["source"]["available_at"]) <= _time(due["due_at"])
                    )
                )
                candidates.append(
                    {
                        "original": row["source"],
                        "exact_calendar_links": links,
                        "exact_calendar_and_due_match": exact,
                        "within_declared_trigger_due_window": ontime,
                        "recorded_factual_result": row["document"].get("factual_result"),
                    }
                )
                originals.extend([row, *targets])
            missing = not any(c["within_declared_trigger_due_window"] for c in candidates)
            observations.append(
                _obs(
                    str(_key(calendar_row["source"])) + due["due_at"],
                    {
                        "declared_due_occurrence": due,
                        "calendar_available_at_trigger": causal_calendar,
                        "actual_selected_operation_versions": candidates,
                        "missing_or_late_at_due": missing,
                        "operations_need_exact_calendar_and_due_not_invented_trigger_id": True,
                        "later_success_cures_prior_missed_interval": False,
                        "native_not_scheduled_interval": body.get("not_scheduled_interval"),
                    },
                    originals,
                    status="EXCEPTION_RECORDED" if missing else "OBSERVED",
                )
            )
    # Earlier unapproved candidate runs remain visible, separate from approved calendar.
    for row in history.selected(
        {"pol004procedure.execution_trace", "pol004procedure.result_register"}
    ):
        links, originals = _links(history, row)
        body = row["document"]
        observations.append(
            _obs(
                str(_key(row["source"])) + "candidate-execution",
                {
                    "recorded_result": body.get("result", body.get("status")),
                    "candidate_approval_and_execution_links": links,
                    "candidate_run_is_corporate_executable_procedure": False,
                },
                originals,
                status="SUPPORT_UNAVAILABLE" if not _action_supported(row) else "OBSERVED",
            )
        )
    return observations


def _calendar_date(value):
    # Retention source fields explicitly contain ISO calendar dates, not native
    # occurrence timestamps. Keep their units separate from strict source clocks.
    require(isinstance(value, str), "Explicit retention calendar date required")
    return (
        date.fromisoformat(value)
        if len(value) == 10
        else datetime.fromisoformat(_time(value)).date()
    )


def _add_years(value, years):
    stamp = _calendar_date(value)
    year = stamp.year + years
    return stamp.replace(
        year=year, day=min(stamp.day, calendar.monthrange(year, stamp.month)[1])
    ).isoformat()


def _retention(history):
    observations = []
    roles = {
        "supplementalops.policy_document",
        "supplementalops.procedure_document",
        "supplementalops.risk_decision",
        "supplementalops.communication_event",
        "supplementalops.incident_intake",
        "supplementalops.facility_maintenance",
    }
    for row in history.selected({"supplementalops.retention_register"}):
        body = row["document"]
        links, originals = _links(history, row)
        _, native_targets = _dependencies(history, row, roles)
        retrieved, dates = [], []
        locators = body.get("retrievable_original_refs", [])
        _ids(locators)
        extra = body.get("superseded_original_retrieval", {})
        if isinstance(extra, dict) and isinstance(extra.get("exact_original_ref"), str):
            locators = list(dict.fromkeys([*locators, extra["exact_original_ref"]]))
        for locator in locators:
            target, status = _scalar_original(history, row, locator, roles)
            exact_native = target is not None and any(
                _key(t["source"]) == _key(target["source"]) for t in native_targets
            )
            retrieved.append(
                {
                    "locator": locator,
                    "scalar_status": status,
                    "exact_original_collected_unchanged": target is not None,
                    "same_original_explicit_native_dependency": exact_native,
                    "original": target["source"] if target else None,
                }
            )
            if target:
                originals.append(target)
        entries = body.get("required_records", [])
        require(
            isinstance(entries, list) and all(isinstance(i, dict) for i in entries),
            "Typed retention required-record vector required",
        )
        _ids([i["id"] for i in entries])
        for item in entries:
            for flag in ("current_effective", "hold", "actual_deletion"):
                require(
                    flag not in item or type(item[flag]) is bool,
                    "Strict retention Boolean required",
                )
            created, ended = item.get("created_date"), item.get("last_in_effect_date")
            supported = isinstance(created, str) and _calendar_date(created) <= _calendar_date(
                row["source"]["event_at"]
            )
            if ended is not None:
                supported = (
                    supported
                    and isinstance(ended, str)
                    and _calendar_date(ended) <= _calendar_date(row["source"]["event_at"])
                )
            floor = (
                _add_years(
                    max(_calendar_date(created), _calendar_date(ended)).isoformat()
                    if ended
                    else created,
                    6,
                )
                if supported
                else None
            )
            current_hold = item.get("current_effective") is True and ended is None
            requested = item.get("requested_date")
            expected_deny = (
                current_hold
                or item.get("hold") is True
                or (
                    floor is not None
                    and isinstance(requested, str)
                    and _calendar_date(requested) <= _calendar_date(floor)
                )
            )
            known = (
                supported
                and type(item.get("current_effective")) is bool
                and type(item.get("hold")) is bool
            )
            expected = (
                "DENY" if expected_deny else "RELEASE_ELIGIBLE_AFTER_FLOOR" if known else None
            )
            matches = item.get("decision") == "DENY" if expected_deny else None
            dates.append(
                {
                    "id": item["id"],
                    "class": item.get("class"),
                    "created_date": created,
                    "last_in_effect_date": ended,
                    "recomputed_six_calendar_year_later_of_floor": floor,
                    "reported_floor_matches": _calendar_date(item["minimum_retain_through"])
                    == _calendar_date(floor)
                    if floor and isinstance(item.get("minimum_retain_through"), str)
                    else None,
                    "current_effective_without_end_held": current_hold,
                    "existing_hold_preserved": item.get("hold"),
                    "requested_date": requested,
                    "computed_local_disposition": expected,
                    "reported_disposition": item.get("decision"),
                    "reported_denial_matches": matches,
                    "actual_deletion": item.get("actual_deletion"),
                    "future_requested_disposition_is_local_training_trial_not_future_action": True,
                }
            )
        discrepancy = any(
            d["reported_floor_matches"] is False
            or d["reported_denial_matches"] is False
            or d["actual_deletion"] is True
            and d["computed_local_disposition"] == "DENY"
            for d in dates
        )
        missing = any(not r["same_original_explicit_native_dependency"] for r in retrieved)
        observations.append(
            _obs(
                str(_key(row["source"])) + "retention",
                {
                    "actual_retention_classes": body.get("classes"),
                    "exact_retrieval_population": retrieved,
                    "recomputed_required_record_dates": dates,
                    "actual_causal_source_links": links,
                    "claimed_superseded_retrieval": extra,
                    "prior_held_records_not_released": body.get("earlier_held_records"),
                    "medical_record_or_customer_retention_authority_accepted": False,
                    "actual_disposition_operation_executed_by_method": False,
                },
                originals,
                status="EXCEPTION_RECORDED"
                if discrepancy
                else "SUPPORT_UNAVAILABLE"
                if missing or not (dates or retrieved)
                else "OBSERVED",
            )
        )
    return observations


def _addressable(history):
    candidates = _current(history, {"addressabledocket.addressable_candidate"})
    observations = []
    specs = [r["document"].get("source_locator") for r in candidates]
    typed = all(isinstance(s, str) and s for s in specs)
    distinct = typed and len(specs) == len(set(specs))
    decisions = history.selected({"supplementalops.risk_decision"})
    configurations = history.selected({"supplementalops.security_configuration"})
    observations.append(
        _obs(
            "addressable-selected-census",
            {
                "distinct_candidate_original_count": len(candidates),
                "declared_specification_vector": specs,
                "all22_distinct_specification_candidates_present": len(candidates) == 22
                and distinct,
                "count_alone_establishes_environmental_decision_or_applicability": False,
            },
            candidates or history.rows[:1],
            status="OBSERVED" if len(candidates) == 22 and distinct else "SUPPORT_UNAVAILABLE",
        )
    )
    for candidate in candidates:
        spec = candidate["document"].get("source_locator")
        chosen = [
            r
            for r in decisions
            if isinstance(spec, str)
            and r["document"].get("specification") == spec
            and _time(candidate["source"]["available_at"]) <= _time(r["source"]["event_at"])
        ]
        for decision in chosen or [None]:
            assessment = decision["document"].get("assessment", {}) if decision else {}
            required = (
                "size_complexity_capability",
                "infrastructure",
                "cost",
                "probability_and_criticality",
            )
            missing = [
                k
                for k in required
                if not isinstance(assessment, dict)
                or not isinstance(assessment.get(k), str)
                or not assessment[k].strip()
            ]
            disposition = decision["document"].get("decision") if decision else None
            if disposition in {"ALTERNATIVE", "DO_NOT_IMPLEMENT", "EQUIVALENT_ALTERNATIVE"} and (
                not decision["document"].get("equivalent_alternative")
                or not decision["document"].get("reasoned_treatment")
            ):
                missing.append("reasoned_equivalent_alternative")
            candidate_links, explicit_candidates = (
                _dependencies(history, decision, {"addressabledocket.addressable_candidate"})
                if decision
                else ([], [])
            )
            exact_candidate = any(
                _key(r["source"]) == _key(candidate["source"]) for r in explicit_candidates
            )
            implemented = []
            originals = [candidate, *([decision] if decision else [])]
            for cfg in configurations:
                if cfg["document"].get("specification") != spec:
                    continue
                links, targets = _dependencies(history, cfg, {"supplementalops.risk_decision"})
                loc_target, loc_status = _scalar_original(
                    history,
                    cfg,
                    cfg["document"].get("implementation_decision_original"),
                    {"supplementalops.risk_decision"},
                )
                if (
                    decision is not None
                    and loc_target is not None
                    and (
                        _key(loc_target["source"]) != _key(decision["source"])
                        and not any(_key(t["source"]) == _key(decision["source"]) for t in targets)
                    )
                ):
                    # This exact retained output belongs to another dated decision;
                    # preserve it in that decision's separate history examination.
                    continue
                exact = (
                    decision is not None
                    and len(targets) == 1
                    and _key(targets[0]["source"]) == _key(decision["source"])
                )
                exact = (
                    exact
                    and loc_target is not None
                    and _key(loc_target["source"]) == _key(decision["source"])
                )
                planned, planned_status = _scalar_original(
                    history,
                    cfg,
                    decision["document"].get("planned_configuration_record") if decision else None,
                    {"supplementalops.security_configuration"},
                    output_identity=True,
                )
                planned_exact = planned is not None and _key(planned["source"]) == _key(
                    cfg["source"]
                )
                implemented.append(
                    {
                        "configuration_original": cfg["source"],
                        "decision_links": links,
                        "explicit_decision_scalar_status": loc_status,
                        "exact_typed_prior_decision": exact,
                        "planned_setting_scalar_status": planned_status,
                        "exact_planned_setting": planned_exact,
                        "observed_local_values": cfg["document"].get("observed_values"),
                        "actually_deployed_or_independently_effective_safeguard": False,
                    }
                )
                originals.append(cfg)
            observations.append(
                _obs(
                    str(_key(candidate["source"]))
                    + str(_key(decision["source"]) if decision else None)
                    + "addressable-chain",
                    {
                        "specification": spec,
                        "candidate_original": candidate["source"],
                        "candidate_pending_history": candidate["document"].get("docket_state"),
                        "scalar_specification_correlated_decision_original": decision["source"]
                        if decision
                        else None,
                        "candidate_native_pointer_links": candidate_links,
                        "exact_candidate_native_pointer_present": exact_candidate,
                        "scalar_specification_match_is_native_pointer": False,
                        "selected_environmental_assessment": assessment,
                        "missing_reasoning_fields": missing,
                        "recorded_disposition": disposition,
                        "selected_configuration_chain": implemented,
                        "legal_equivalence_or_actual_hipaa_environment_accepted": False,
                    },
                    originals,
                    status="EXCEPTION_RECORDED"
                    if decision
                    and (
                        missing
                        or any(
                            not c["exact_typed_prior_decision"] or not c["exact_planned_setting"]
                            for c in implemented
                        )
                    )
                    else "SUPPORT_UNAVAILABLE"
                    if not decision or not exact_candidate or not implemented
                    else "OBSERVED",
                )
            )
    for row in decisions:
        if row["document"].get("request") and not row["document"].get("specification"):
            observations.append(
                _obs(
                    str(_key(row["source"])) + "generic-waiver",
                    {
                        "generic_request": row["document"].get("request"),
                        "recorded_disposition": row["document"].get("disposition"),
                        "blank_request_basis": not row["document"].get("request_basis"),
                        "generic_waiver_substitutes_for_environmental_assessment": False,
                    },
                    [row],
                    status="EXCEPTION_RECORDED",
                )
            )
    return observations


def _conflicts(history):
    observations = []
    for row in history.selected({"govoversight.eligibility_review", "govoversight.committee_note"}):
        body, detail = row["document"], row["document"].get("detail", {})
        require(isinstance(detail, dict), "Typed governing review detail required")
        subject = detail.get("subject_recused_from_own_review")
        contacts = detail.get("review_contacts")
        independent = (
            subject not in _ids(contacts)
            if isinstance(subject, str) and contacts is not None
            else None
        )
        questionnaire = _closest(history, row, {"govoversight.conflict_questionnaire"})
        # The actual legacy oversight chain has a scalar predecessor witness;
        # retain its missing full-version authority separately rather than guessing.
        previous = body.get("previous_native_content", {})
        witness, witness_status = _digest_target(
            history,
            row,
            previous.get("sha256"),
            {"govoversight.conflict_questionnaire", "govoversight.audit_committee_packet"},
        )
        if witness is not None and witness["source"]["record"] != previous.get("record"):
            witness, witness_status = None, "DECLARED_PREDECESSOR_RECORD_DIFFERS"
        case_match = (
            all(q["document"].get("case_id") == body.get("case_id") for q in questionnaire)
            if questionnaire
            else None
        )
        for flag in ("questionnaire_returned", "collective_resolution"):
            require(
                flag not in detail or type(detail[flag]) is bool,
                "Strict conflict review Boolean required",
            )
        exception = (
            independent is False
            or case_match is False
            or detail.get("questionnaire_returned") is False
        )
        observations.append(
            _obs(
                str(_key(row["source"])) + "recusal",
                {
                    "subject_recused_from_own_review": subject,
                    "named_review_contacts": contacts,
                    "subject_excluded_from_named_review": independent,
                    "exact_questionnaire_ancestor_originals": [q["source"] for q in questionnaire],
                    "same_exact_review_case": case_match,
                    "scalar_predecessor_status": witness_status,
                    "scalar_predecessor_original": witness["source"] if witness else None,
                    "self_attestation_establishes_independent_conflict_clearance": False,
                    "adopted_minutes": body.get("adopted_minutes"),
                    "actual_question_or_challenge": detail.get("question"),
                    "collective_resolution_recorded": body.get("collective_resolution_recorded"),
                    "whole_governing_membership_and_legal_quorum_established": False,
                },
                [row, *questionnaire, *([witness] if witness else [])],
                status="EXCEPTION_RECORDED"
                if exception
                else "SUPPORT_UNAVAILABLE"
                if independent is None or not questionnaire
                else "OBSERVED",
            )
        )
    return observations


def _threshold_routes(history):
    observations = []
    for row in history.selected(
        {"govapp.waiver_request", "govapp.security_challenge", "govapp.ceo_disposition"}
    ):
        body = row["document"]
        board, bstatus = _digest_target(
            history, row, body.get("board_decision_sha256"), {"govapp.board_decision"}
        )
        motion, mstatus = (
            _digest_target(
                history,
                board,
                board["document"].get("accepted_motion_sha256"),
                {"govapp.appetite_motion"},
            )
            if board
            else (None, "BOARD_ABSENT")
        )
        waiver, wstatus = (
            _digest_target(
                history, row, body.get("waiver_request_sha256"), {"govapp.waiver_request"}
            )
            if row["source"]["system"] != "govapp.waiver_request"
            else (row, "OWN_ORIGINAL")
        )
        limits = motion["document"] if motion else {}
        values = waiver["document"] if waiver else {}
        tests = []
        for claim, limit in (
            ("claimed_selected_retest_restore_minutes", "internal_marker_rto_minutes_max"),
            ("claimed_selected_retest_replay_gap_minutes", "internal_marker_rpo_minutes_max"),
        ):
            value, maximum = values.get(claim), limits.get(limit)
            numeric = (
                type(value) in (int, float)
                and type(maximum) in (int, float)
                and value >= 0
                and maximum >= 0
            )
            tests.append(
                {
                    "attribute": claim,
                    "recorded_value": value,
                    "recorded_limit": maximum,
                    "exceeds_local_envelope": value > maximum if numeric else None,
                }
            )
        gate = values.get("actual_key_bypass_open")
        require(gate is None or type(gate) is bool, "Strict bypass Boolean required")
        tolerance = limits.get("unreviewed_boise_key_gate_bypass_tolerance")
        bypass_breach = (
            gate and tolerance == 0 if type(gate) is bool and type(tolerance) is int else None
        )
        window = bool(
            board
            and isinstance(board["document"].get("effective_at"), str)
            and isinstance(board["document"].get("expires_at"), str)
            and _time(board["document"]["effective_at"])
            <= _time(row["source"]["event_at"])
            <= _time(board["document"]["expires_at"])
        )
        challenge, cstatus = _digest_target(
            history, row, body.get("security_challenge_sha256"), {"govapp.security_challenge"}
        )
        challenge_same = (
            challenge is not None
            and waiver is not None
            and challenge["document"].get("waiver_request_sha256") == waiver["source"]["sha256"]
        )
        hours = (
            (
                datetime.fromisoformat(_time(row["source"]["event_at"]))
                - datetime.fromisoformat(_time(waiver["source"]["event_at"]))
            ).total_seconds()
            / 3600
            if waiver
            else None
        )
        observations.append(
            _obs(
                str(_key(row["source"])) + "reserved-risk-route",
                {
                    "board_original_status": bstatus,
                    "motion_original_status": mstatus,
                    "waiver_original_status": wstatus,
                    "measured_local_numeric_claims": tests,
                    "unreviewed_key_bypass_exceeds_zero_tolerance": bypass_breach,
                    "numeric_retest_closes_independent_key_bypass_or_capacity_issue": False,
                    "board_envelope_effective_for_occurrence": window,
                    "recorded_reserved_authority_route": board["document"].get(
                        "reserved_boundary_route"
                    )
                    if board
                    else None,
                    "recorded_disposition": body.get("status"),
                    "recorded_risk_acceptance": body.get("risk_acceptance"),
                    "recorded_issue_closed": body.get("issue_closed"),
                    "security_challenge_original_status": cstatus,
                    "challenge_bound_same_exact_request": challenge_same,
                    "elapsed_hours_from_selected_request": hours,
                    "explicit_local_48_hour_route_met": hours <= 48
                    if hours is not None and hours >= 0
                    else None,
                    "requested_body": body.get("requested_body"),
                    "committee_ack_is_reserved_risk_acceptance": False,
                    "actual_accepted_residual_risk_or_collective_disposition": False,
                },
                [row, *[r for r in (board, motion, waiver, challenge) if r is not None]],
                status="EXCEPTION_RECORDED"
                if bypass_breach
                or any(t["exceeds_local_envelope"] is True for t in tests)
                or hours is not None
                and hours > 48
                else "SUPPORT_UNAVAILABLE"
                if not window or not waiver
                else "OBSERVED",
            )
        )
    return observations


def _material_changes(history):
    observations = []
    changes = history.selected(
        {"supplementalops.policy_document", "supplementalops.communication_directory"}
    )
    for row in changes:
        if row["source"]["version"] <= 1:
            continue
        prior = history.index.get((*_key(row["source"])[:-1], row["source"]["version"] - 1))
        keys = {
            "required_internal_recipients",
            "external_concern_address",
            "template_address",
            "policy_text",
            "responsibility_owner",
        }
        changed = sorted(
            k
            for k in keys
            if prior is not None and row["document"].get(k) != prior["document"].get(k)
        )
        followups = []
        for follow in history.selected(
            {
                "risk-history.risk_followup",
                "supplementalops.risk_decision",
                "supplementalops.procedure_operation",
            }
        ):
            links, targets = _dependencies(history, follow, {row["source"]["system"]})
            if not any(_key(t["source"]) == _key(row["source"]) for t in targets):
                continue
            due = row["document"].get("risk_review_due_at")
            elapsed = (
                datetime.fromisoformat(_time(follow["source"]["event_at"]))
                - datetime.fromisoformat(_time(row["source"]["event_at"]))
            ).total_seconds() / 3600
            followups.append(
                {
                    "original": follow["source"],
                    "exact_change_links": links,
                    "hours_after_change": elapsed,
                    "explicit_due_at": due,
                    "within_explicit_review_due": _time(follow["source"]["available_at"])
                    <= _time(due)
                    if isinstance(due, str)
                    else None,
                    "recorded_assessment_or_no_change_reason": follow["document"].get(
                        "assessment",
                        follow["document"].get("reason", follow["document"].get("factual_result")),
                    ),
                }
            )
        observations.append(
            _obs(
                str(_key(row["source"])) + "material-change",
                {
                    "exact_previous_version_collected": prior is not None,
                    "changed_selected_fields": changed,
                    "exact_causally_linked_followups": followups,
                    "new_version_alone_establishes_timely_risk_reassessment": False,
                    "supplier_service_change_universe_established": False,
                },
                [
                    row,
                    *([prior] if prior else []),
                    *[history.index[_key(f["original"])] for f in followups],
                ],
                status="EXCEPTION_RECORDED"
                if any(f["within_explicit_review_due"] is False for f in followups)
                else "SUPPORT_UNAVAILABLE"
                if not followups or not prior
                else "OBSERVED",
            )
        )
    return observations


def _communications(history):
    observations = []
    for row in history.selected({"supplementalops.communication_event"}):
        body = row["document"]
        links, directories = _dependencies(
            history, row, {"supplementalops.communication_directory"}
        )
        directory = directories[0] if len(directories) == 1 else None
        # Reject explicit stale directory versions at the action time.
        effective = [
            d
            for d in history.selected({"supplementalops.communication_directory"})
            if directory is not None
            and _key(d["source"])[:-1] == _key(directory["source"])[:-1]
            and _time(d["source"]["available_at"]) <= _time(row["source"]["event_at"])
        ]
        latest = max(effective, key=lambda d: d["source"]["version"]) if effective else None
        current = (
            directory is not None
            and latest is not None
            and _key(latest["source"]) == _key(directory["source"])
        )
        expected = (
            _ids(directory["document"].get("required_internal_recipients", []))
            if directory
            else None
        )
        declared = _ids(body["required_recipients"]) if "required_recipients" in body else None
        receipts = body.get("delivery_receipts", [])
        require(
            isinstance(receipts, list) and all(isinstance(r, dict) for r in receipts),
            "Typed delivery receipts required",
        )
        delivered, receipt_attributes = set(), []
        for receipt in receipts:
            recipient, received = receipt.get("recipient"), receipt.get("received_at")
            require(isinstance(recipient, str) and recipient, "Typed delivery recipient required")
            for flag in ("document_sha_bound",):
                require(
                    flag not in receipt or type(receipt[flag]) is bool,
                    "Strict delivery Boolean required",
                )
            bound = receipt.get("document_sha_bound")
            timely = isinstance(received, str) and _time(received) <= _time(
                row["source"]["event_at"]
            )
            timely = timely and (
                not isinstance(body.get("due_at"), str) or _time(received) <= _time(body["due_at"])
            )
            supported = bound is True and timely
            if supported:
                delivered.add(recipient)
            receipt_attributes.append(
                {
                    "recipient": recipient,
                    "reported_received_at": received,
                    "reported_document_sha_bound": bound,
                    "document_binding_attribute_present": "document_sha_bound" in receipt,
                    "document_binding_status": "REPORTED_BOUND"
                    if bound is True
                    else "REPORTED_UNBOUND"
                    if bound is False
                    else "DOCUMENT_BINDING_NOT_REPORTED",
                    "reported_receipt_time_within_source_event_and_any_declared_due": timely,
                    "counts_as_source_bounded_received": supported,
                }
            )
        missing = sorted(expected - delivered) if expected is not None else None
        omitted = (
            sorted(expected - declared) if expected is not None and declared is not None else None
        )
        contact = (
            directory["document"].get(
                "external_concern_address",
                directory["document"].get("channels", {}).get("external_concerns"),
            )
            if directory
            else None
        )
        template = body.get("external_template_contact")
        contact_match = (
            template == contact if isinstance(template, str) and isinstance(contact, str) else None
        )
        observations.append(
            _obs(
                str(_key(row["source"])) + "communication",
                {
                    "directory_links": links,
                    "directory_original_effective_at_event": current,
                    "independent_directory_recipients": sorted(expected)
                    if expected is not None
                    else None,
                    "declared_recipients": sorted(declared) if declared is not None else None,
                    "declared_required_audience_omissions": omitted,
                    "source_bounded_received_recipients": sorted(delivered),
                    "actual_receipt_documentary_attributes": receipt_attributes,
                    "method_verified_delivery_or_bound_document_bytes": False,
                    "missing_actual_receipts": missing,
                    "source_directory_contact": contact,
                    "reported_template_contact": template,
                    "template_contact_matches_effective_directory": contact_match,
                    "recorded_customer_concern_or_response": body.get(
                        "customer_concern", body.get("response")
                    ),
                    "customer_receipt_and_real_noninvalid_contact_verified": False,
                    "delegated_vs_customer_privacy_authority_not_inferred": True,
                },
                [row, *directories, *([latest] if latest else [])],
                status="EXCEPTION_RECORDED"
                if missing or omitted or contact_match is False
                else "SUPPORT_UNAVAILABLE"
                if expected is None or not current
                else "OBSERVED",
            )
        )
    return observations


def _ethics(history):
    observations = []
    for row in history.selected(
        {
            "eth003.report_intake",
            "eth003.separate_triage",
            "eth003.protective_handling",
            "eth003.case_state",
        }
    ):
        body = row["document"]
        prior = _closest(
            history,
            row,
            {"eth003.report_intake", "eth003.separate_triage", "eth003.protective_handling"},
        )
        distinct = (
            body.get("actor") != prior[0]["document"].get("actor")
            if len(prior) == 1 and body.get("actor") and prior[0]["document"].get("actor")
            else None
        )
        same_case = (
            all(p["document"].get("case_id") == body.get("case_id") for p in prior)
            if prior
            else None
        )
        for flag in (
            "case_existence_sent_to_implicated_line",
            "actual_retaliation",
            "investigation_complete",
            "sanction_or_performance_decision",
            "substantiated_case",
        ):
            require(
                flag not in body or type(body[flag]) is bool,
                "Strict ethics decision Boolean required",
            )
        observations.append(
            _obs(
                str(_key(row["source"])) + "protected-intake",
                {
                    "exact_prior_case_originals": [p["source"] for p in prior],
                    "same_exact_case": same_case,
                    "distinct_recorded_triage_actor": distinct,
                    "case_existence_sent_to_implicated_line": body.get(
                        "case_existence_sent_to_implicated_line"
                    ),
                    "restricted_access_requested": body.get("restricted_access_requested"),
                    "recorded_route": body.get("current_route", body.get("recipient")),
                    "investigation_complete": body.get("investigation_complete"),
                    "committee_disposition": body.get("committee_disposition"),
                    "actual_retaliation_or_real_person_protection_proven": False,
                    "marker_is_entire_hotline_denominator": False,
                },
                [row, *prior],
                status="EXCEPTION_RECORDED"
                if body.get("case_existence_sent_to_implicated_line") is True or same_case is False
                else "SUPPORT_UNAVAILABLE"
                if not prior
                else "OBSERVED",
            )
        )
    for row in history.selected(
        {"supplementalops.workforce_case", "supplementalops.responsibility_feedback"}
    ):
        body = row["document"]
        links, originals = _links(history, row)
        facts = _closest(history, row, {"supplementalops.workforce_case"})
        for flag in ("action_applied", "reporter_adverse_action", "coaching_completed"):
            require(
                flag not in body or type(body[flag]) is bool,
                "Strict workforce action Boolean required",
            )
        target = body.get("decision_target")
        late = _time(row["source"]["event_at"]) > _time(target) if isinstance(target, str) else None
        reporter_proposal = "proposed_action" in body
        substantiated = len(facts) == 1 and bool(facts[0]["document"].get("substantiated_facts"))
        considerations = body.get("considerations", {})
        missing = [
            k
            for k in ("intent", "impact", "proportionality", "protected_reporting")
            if "sanction" in body
            and (not isinstance(considerations, dict) or not considerations.get(k))
        ]
        observations.append(
            _obs(
                str(_key(row["source"])) + "sanction-followup",
                {
                    "exact_causal_case_links": links,
                    "exact_substantiated_facts_original": facts[0]["source"]
                    if substantiated
                    else None,
                    "recorded_sanction": body.get("sanction"),
                    "reasoned_considerations_missing": missing,
                    "recorded_subject": body.get("subject", body.get("participant")),
                    "reporter_adverse_action_proposal_preserved": reporter_proposal,
                    "proposal_applied": body.get("action_applied"),
                    "recorded_disposition": body.get("decision"),
                    "recorded_enforcement_witness": body.get("enforcement_record"),
                    "decision_late_against_original_target": late,
                    "responsibility_performance_discussion": body.get("discussion"),
                    "reward_and_pressure_review": body.get("reward_and_pressure_review"),
                    "reported_followup": body.get("protected_reporter_followup"),
                    "actual_lawful_sanction_or_protected_disclosure_determination": False,
                    "completed_action_is_effectiveness_closure": False,
                },
                originals,
                status="EXCEPTION_RECORDED"
                if late
                or missing
                or body.get("reporter_adverse_action") is True
                or reporter_proposal
                and body.get("action_applied") is True
                else "SUPPORT_UNAVAILABLE"
                if "sanction" in body and not substantiated
                else "OBSERVED",
            )
        )
    return observations


def _fraud(history):
    observations = []
    for row in history.selected(
        {"eth004.conflict_intake", "eth004.conflict_gate", "eth004.risk_review"}
    ):
        body = row["document"]
        prior = _closest(
            history, row, {"eth004.conflict_intake", "eth004.conflict_gate", "eth004.risk_review"}
        )
        same = (
            all(
                p["document"].get("opportunity_id") == body.get("opportunity_id")
                and p["document"].get("indicator_id") == body.get("indicator_id")
                for p in prior
            )
            if prior
            else None
        )
        for flag in (
            "indicator_included",
            "opportunity_held",
            "draft_recommendation_active",
            "award_or_payment",
            "substantiated_fraud",
        ):
            require(
                flag not in body or type(body[flag]) is bool, "Strict fraud gate Boolean required"
            )
        themes = body.get("risk_themes", [])
        _ids(themes)
        missing = sorted({"RELATED_PARTY", "CONTROL_OVERRIDE", "DISHONEST_REPORTING"} - set(themes))
        unsafe = body.get("indicator_included") is False or body.get("award_or_payment") is True
        unsafe = unsafe or (row["source"]["system"] == "eth004.risk_review" and bool(missing))
        unsafe = (
            unsafe
            or body.get("draft_recommendation_active") is True
            and body.get("opportunity_held") is not True
        )
        observations.append(
            _obs(
                str(_key(row["source"])) + "fraud-gate",
                {
                    "exact_prior_indicator_chain": [p["source"] for p in prior],
                    "same_indicator_and_opportunity": same,
                    "declared_non_intrusion_risk_themes": themes,
                    "missing_override_reporting_related_party_themes": missing,
                    "recorded_indicator_included": body.get("indicator_included"),
                    "recorded_hold": body.get("opportunity_held"),
                    "recorded_recommendation_active": body.get("draft_recommendation_active"),
                    "recorded_award_or_payment": body.get("award_or_payment"),
                    "qualified_legal_or_independent_disposition": body.get(
                        "qualified_legal_or_independent_disposition"
                    ),
                    "actual_affiliation_fraud_or_corporate_award_proven": False,
                },
                [row, *prior],
                status="EXCEPTION_RECORDED"
                if unsafe or same is False
                else "SUPPORT_UNAVAILABLE"
                if not prior
                else "OBSERVED",
            )
        )
    return observations


def _regulator(history):
    observations = []
    for row in history.selected(
        {
            "legint.legal_response_exercise",
            "legint.regulatory_response_playbook",
            "legint.legal_matter_classification",
        }
    ):
        body = row["document"]
        links, originals = _links(history, row)
        inputs = _closest(
            history,
            row,
            {"legaloriginals.legal_inbound_message", "legaloriginals.legal_inbound_attachment"},
        )
        classification = body.get("classification")
        official = body.get("official_regulator_notice")
        require(
            official is None or type(official) is bool, "Strict regulator-notice Boolean required"
        )
        observations.append(
            _obs(
                str(_key(row["source"])) + "regulator-route",
                {
                    "actual_native_causal_links": links,
                    "exact_inbound_originals": [r["source"] for r in inputs],
                    "recorded_classification": classification,
                    "recorded_official_regulator_notice": official,
                    "contract_question_is_official_agency_notice": False,
                    "available_company_copy_ids": body.get("available_company_copy_ids"),
                    "urgent_access_path_recorded": body.get("urgent_access_path_exercised"),
                    "recorded_playbook_steps": body.get("procedure"),
                    "provider_unavailability_and_preservation_fields": {
                        k: body[k]
                        for k in (
                            "provider_records_accessible",
                            "provider_requests",
                            "preservation_receipts",
                            "authority_ref",
                        )
                        if k in body
                    },
                    "actual_lawful_regulator_authority_or_real_access_exercised": False,
                    "ordinary_customer_disclosure_rule_is_regulator_access_bar": False,
                    "actual_trigger_population_and_applicable_legal_process_unperformed": True,
                },
                [*originals, *inputs],
                status="SUPPORT_UNAVAILABLE",
            )
        )
    return observations


def _record_facets(history, selected, names, label):
    observations = []
    for row in selected:
        body = row["document"]
        links, originals = _links(history, row)
        present = {k: body[k] for k in names if k in body}
        observations.append(
            _obs(
                str(_key(row["source"])) + label,
                {
                    "native_role": row["source"]["system"],
                    "actual_retained_fields": present,
                    "fields_absent_from_this_original": [k for k in names if k not in body],
                    "exact_causal_source_links": links,
                    "company_claim_or_proposed_role_is_qualified_control_acceptance": False,
                },
                originals,
                status="OBSERVED" if present and _action_supported(row) else "SUPPORT_UNAVAILABLE",
            )
        )
    return observations


CLAUSE_FIELDS = {
    "CHECK-SOC2:CC1.2": [
        "detail",
        "member_capacity",
        "vote",
        "actor_id",
        "adopted_minutes",
        "collective_resolution_recorded",
        "independent_assurance_completed",
        "complete_oversight_population",
    ],
    "ACTION-H-SECURITY-OFFICIAL": [
        "security_official_designation",
        "actual_security_official_designation",
        "appointment_ref",
        "official_person_id",
        "technical_configuration_authority",
    ],
    "CHECK-HIPAA:164.105": [
        "actual_hipaa_applicability",
        "entity_role",
        "covered_components",
        "separation_safeguards",
        "designation_ref",
    ],
    "CHECK-SOC2:CC1.3": [
        "scope",
        "accountable_roles",
        "security_challenge_person_id",
        "technical_configuration_authority",
        "waiver_of_board_envelope",
        "detail",
    ],
    "CHECK-SOC2:CC3.2": [
        "risks",
        "assumed_risk_scenarios",
        "inputs",
        "method_basis",
        "risk_acceptance",
        "treatment_status",
    ],
    "CHECK-SOC2:CC3.1": [
        "internal_marker_rpo_minutes_max",
        "internal_marker_rto_minutes_max",
        "customer_service_commitment",
        "threshold_breach_route",
        "status",
    ],
    "CHECK-SOC2:CC3.3": [
        "risk_themes",
        "decision",
        "indicator_included",
        "opportunity_held",
        "draft_recommendation_active",
        "qualified_legal_or_independent_disposition",
        "substantiated_fraud",
    ],
    "CHECK-SOC2:CC3.4": [
        "assessment",
        "native_dependencies",
        "treatment_proposal",
        "reason",
        "change_basis",
        "factual_result",
    ],
    "CHECK-SOC2:CC5.1": [
        "accountable_roles",
        "control_ids",
        "rationale",
        "technical_configuration_authority",
        "preventive_steps",
        "detective_steps",
        "compensating_measures",
    ],
    "CHECK-SOC2:CC9.1": [
        "residual_status",
        "risk_acceptance",
        "treatment_proposal",
        "source_refs",
        "measured_selected_marker_restore_minutes",
        "status",
    ],
    "CHECK-SOC2:CC5.3": [
        "detail",
        "trigger",
        "inputs",
        "frequency_and_trigger",
        "responsible_person_id",
        "due_at",
        "factual_result",
        "exception_handling",
    ],
    "ACTION-H-REGULATOR": [
        "regulator_request_or_response",
        "actual_person_protection_or_legal_opinion",
        "restricted_access_requested",
        "current_route",
        "authority_ref",
        "preservation_receipt",
    ],
    "ACTION-H-SANCTIONS": [
        "substantiated_case",
        "sanction_or_performance_decision",
        "actual_retaliation",
        "investigation_complete",
        "committee_disposition",
        "considerations",
        "protected_reporting",
        "discussion",
        "followup_owner",
    ],
    "ACTION-S-COMMUNICATION": [
        "audience",
        "receipt_at",
        "recipient_endpoints",
        "endpoint",
        "customer_decision",
        "contact_review",
        "required_recipients",
        "received_by",
    ],
    "CHECK-HIPAA:164.304": [
        "incident_attempts_included",
        "usability_verified",
        "customer_privacy_rights",
        "security_access",
        "policy_text",
    ],
    "CHECK-HIPAA:164.530": [
        "classes",
        "approval",
        "customer_retained_notice_authority",
        "customer_decision",
        "considerations",
        "policy_text",
    ],
}


PRIMARY_FIELDS = {
    "SH-ERM-001": (
        "assumption_basis",
        "recomputed_inherent_local_score",
        "recomputed_missing_inputs",
    ),
    "SH-ERM-002": (
        "recorded_measurable_selected_limits",
        "recorded_vote_counts_match_collected_individual_actions",
        "effective_at",
    ),
    "SH-ERM-003": (
        "recorded_reserved_authority_route",
        "measured_local_numeric_claims",
        "unreviewed_key_bypass_exceeds_zero_tolerance",
    ),
    "SH-ERM-004": (
        "changed_selected_fields",
        "exact_causally_linked_followups",
        "supplier_service_change_universe_established",
    ),
    "SH-GOV-001": ("motion_link", "recomputed_votes", "missing_member_originals"),
    "SH-GOV-003": (
        "exact_board_link",
        "recorded_assignment_or_disposition",
        "board_window_effective_at_this_native_event",
    ),
    "SH-GOV-004": (
        "named_review_contacts",
        "subject_excluded_from_named_review",
        "same_exact_review_case",
    ),
    "SH-POL-001": (
        "independent_directory_recipients",
        "reported_byte_hashes_match_selected_plan",
        "missing_actual_receipts",
    ),
    "SH-POL-002": (
        "recorded_assignment_or_disposition",
        "exact_board_link",
        "board_window_effective_at_this_native_event",
    ),
    "SH-POL-003": (
        "selected_environmental_assessment",
        "selected_configuration_chain",
        "candidate_pending_history",
    ),
    "SH-POL-004": (
        "declared_due_occurrence",
        "actual_selected_operation_versions",
        "missing_or_late_at_due",
    ),
    "SH-ETH-003": (
        "recorded_route",
        "exact_substantiated_facts_original",
        "decision_late_against_original_target",
    ),
    "SH-ETH-004": (
        "declared_non_intrusion_risk_themes",
        "same_indicator_and_opportunity",
        "recorded_hold",
    ),
}


def _task_focus(control, kind, clause, observations):
    fields = PRIMARY_FIELDS[control]
    field = {
        "ACTION-H-RETENTION": "recomputed_required_record_dates",
        "ACTION-H-ADDRESSABLE": "selected_configuration_chain",
        "ACTION-H-REGULATOR": "exact_inbound_originals",
        "ACTION-H-SANCTIONS": "reasoned_considerations_missing",
        "ACTION-H-SECURITY-OFFICIAL": "recorded_assignment_or_disposition",
        "ACTION-S-COMMUNICATION": "missing_actual_receipts",
        "CHECK-HIPAA:164.530": "recomputed_required_record_dates",
        "CHECK-SOC2:CC5.1": "same_named_technical_executor_and_security_challenger",
        "CHECK-SOC2:CC5.3": "declared_due_occurrence",
        "CHECK-SOC2:CC3.3": "declared_non_intrusion_risk_themes",
        "CHECK-SOC2:CC3.4": "exact_causally_linked_followups",
    }.get(clause, fields[{"TOD": 0, "IMPLEMENTATION": 1, "TOE": 2}.get(kind, 1)])

    # Find nested independently derived attributes without recopying unexamined bodies.
    def values(value, path="$"):
        if isinstance(value, dict):
            if field in value:
                yield {"locator": path + "." + field, "value": value[field]}
            for key, child in value.items():
                yield from values(child, path + "." + key)
        elif isinstance(value, list):
            for i, child in enumerate(value):
                yield from values(child, f"{path}[{i}]")

    return {
        "control_id": control,
        "task_kind": kind,
        "exact_clause": clause,
        "primary_attribute": field,
        "bounded_derived_attribute_items": [
            {"observation_id": o["id"], "observation_status": o["status"], "attributes": found}
            for o in observations
            if (found := list(values(o["facts"])))
        ],
        "exact_additional_attribute_scope": CLAUSE_FIELDS.get(clause, []),
        "clauses_complete_or_professional_pass": False,
    }


def examine(records, *, as_of, scratch_root=None):
    del scratch_root
    history = History(records, as_of)
    terms, output = contracts(), []
    for task in task_plan():
        control, kind = task["control_id"], task["kind"]
        selected = history.selected(ROLES[control])
        fallback = history.rows[:1]
        observations = []
        if control == "SH-ERM-001":
            observations.extend(_risk(history))
        elif control == "SH-ERM-002":
            observations.extend(_appetite(history))
        elif control in {"SH-GOV-003", "SH-POL-002"}:
            observations.extend(_authority(history))
        elif control == "SH-ERM-003":
            observations.extend(_authority(history))
            observations.extend(_threshold_routes(history))
        elif control == "SH-ERM-004":
            observations.extend(_material_changes(history))
        elif control == "SH-GOV-004":
            observations.extend(_conflicts(history))
        elif control == "SH-ETH-003":
            observations.extend(_ethics(history))
        elif control == "SH-ETH-004":
            observations.extend(_fraud(history))
        elif control == "SH-GOV-001":
            observations.extend(_governing_decisions(history))
        elif control == "SH-POL-001":
            observations.extend(_policy_distribution(history))
            observations.extend(_communications(history))
        elif control == "SH-POL-003":
            observations.extend(_addressable(history))
        elif control == "SH-POL-004":
            observations.extend(_procedure_due(history))
        base_fields = {
            "TOD": [
                "scope",
                "criteria",
                "frequency_and_trigger",
                "approval",
                "effective_at",
                "expires_at",
                "detail",
                "source_implementation_class",
            ],
            "IMPLEMENTATION": [
                "actor_id",
                "action",
                "recorded_at",
                "event_at",
                "native_dependencies",
                "previous_source",
                "source_refs",
                "detail",
            ],
            "TOE": [
                "due_at",
                "effective_at",
                "period_start",
                "period_end_exclusive",
                "status",
                "missing_at_due",
                "detail",
                "case_status",
                "investigation_complete",
            ],
        }
        clause = task["task_id"].split("-corporate-", 1)[1]
        names = base_fields.get(kind, CLAUSE_FIELDS.get(clause, []))
        observations.extend(_record_facets(history, selected, names, kind + ":" + clause))
        for row in selected:
            if not _action_supported(row):
                observations.append(
                    _obs(
                        str(_key(row["source"])) + "recorded-action-clock",
                        {
                            "actual_native_occurrence": row["source"]["event_at"],
                            "recorded_action_chronology_supported": False,
                            "future_or_null_recorded_action_is_dated_performance": False,
                        },
                        [row],
                        status="SUPPORT_UNAVAILABLE",
                    )
                )
        if clause == "ACTION-H-REGULATOR":
            observations.extend(_regulator(history))
        if clause in {"ACTION-H-RETENTION", "CHECK-HIPAA:164.530"}:
            observations.extend(_retention(history))
        if clause in {"CHECK-SOC2:CC5.3", "CHECK-SOC2:CC3.4"} and control != "SH-POL-004":
            observations.extend(_procedure_due(history))
        if not selected:
            observations.append(
                _obs(
                    control + ":absent:" + clause,
                    {
                        "authored_instruction": task["authored_instruction"],
                        "required_native_roles_not_collected": sorted(ROLES[control]),
                        "cited_original_is_context_only_not_substantive_support": True,
                    },
                    fallback,
                    status="SUPPORT_UNAVAILABLE",
                )
            )
        observations.append(
            _obs(
                control + ":period:" + clause,
                {
                    "task_kind": kind,
                    "authored_instruction": task["authored_instruction"],
                    "actual_selected_original_versions": len(selected),
                    "actual_selected_distinct_native_records": len(
                        {_key(r["source"])[:-1] for r in selected}
                    ),
                    "selected_native_role_counts": dict(
                        Counter(r["source"]["system"] for r in selected)
                    ),
                    "qualified_clause_or_entire_year_effectiveness_asserted": False,
                    "remaining_unperformed": [
                        "Clause-specific missing source/authority/operating attributes above",
                        task["required_checks"],
                        "Enterprise population, accepted authority and independent sufficient "
                        "operating tests remain unestablished",
                    ],
                },
                selected or fallback,
                status="SUPPORT_UNAVAILABLE",
            )
        )
        observations = _partition_citations(observations)
        ids = list(dict.fromkeys(e["artifact_id"] for o in observations for e in o["evidence"]))
        output.append(
            {
                "task_id": task["task_id"],
                "artifact_ids": ids,
                "observations": observations,
                "performed": terms[task["task_id"]]["performed"],
                "unperformed": terms[task["task_id"]]["unperformed"],
                "result": {
                    "authored_instruction": task["authored_instruction"],
                    "task_specific_primary_attributes": _task_focus(
                        control, kind, clause, observations
                    ),
                    "actual_observation_count": len(observations),
                    "actual_exception_count": sum(
                        o["status"] == "EXCEPTION_RECORDED" for o in observations
                    ),
                    "professional_or_enterprise_acceptance_asserted": False,
                },
                "disposition": {
                    "status": "IN_PROGRESS",
                    "conclusion": "FAIL"
                    if any(o["status"] == "EXCEPTION_RECORDED" for o in observations)
                    else "LIMITATION",
                    "rationale": "Exact selected retained-original facets examined; explicit "
                    "source/authority/cadence/applicability and operating sufficiency "
                    "limits remain.",
                },
            }
        )
    return output
