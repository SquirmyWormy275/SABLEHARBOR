"""Twenty-six B09 tasks examined from ordinary collected native company bytes.

The current Engine caller separately enforces membership/source/runtime pins.
No source database, stored program, old audit result or instructor Key is read.
Local exercise response, simulated BA duties, professional legal decisions and
actual recipient delivery remain separate. No legal applicability is inferred.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

from .collected_incident_history import History, custody, detail, key
from .company_store import _json, _time
from .fresh_sec003_procedure import require

PLAN_SHA = "4c80ca60dfd3130d377d9f6898d80167c991f77d986f157c72375ceda040c1f9"
BROAD = (
    "Full enterprise/period incident, dismissed-event and complaint populations; "
    "live containment/eradication/recovery; causal root cause, accepted severity, "
    "qualified second-line/closure authority and representative retests; real PHI, "
    "legal breach/reportability/delegation, actual notices and independent receipt "
    "remain unperformed. Company assertions never issue professional assurance."
)
# These are examination attributes named by the locked rehearsal task, not a
# finding of legal applicability or an accepted company risk-assessment policy.
RISK_FACTORS = (
    "nature_and_extent",
    "unauthorized_person",
    "actual_acquisition_or_viewing",
    "mitigation",
)


def task_plan():
    raw = Path(__file__).with_name("incident_complaints_collected_task_plan_v1.json").read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PLAN_SHA, "Exact26 B09 instruction pack required")
    plan = json.loads(raw)
    require(plan["task_count"] == len(plan["tasks"]) == 26, "Exact26 B09 task census required")
    return plan["tasks"]


def contracts():
    return {
        t["task_id"]: {
            "performed": "Examine actual retained "
            + t["control_id"]
            + " "
            + t["clause_group"]
            + " originals: "
            + t["authored_instruction"]
            + (
                " Record bounded executed attributes, discrepancies and unavailable "
                "support separately."
            ),
            "unperformed": t["task_kind_rule"] + " " + BROAD,
            "allowed_dispositions": [
                {"status": "IN_PROGRESS", "conclusion": c} for c in ("LIMITATION", "FAIL")
            ],
        }
        for t in task_plan()
    }


def _ids(value):
    require(
        isinstance(value, list)
        and all(isinstance(v, str) and v for v in value)
        and len(set(value)) == len(value),
        "Distinct typed B09 occurrence identifiers required",
    )
    return set(value)


def _number(value):
    return type(value) in {int, float} and value >= 0


def _effective(rows, at):
    found = {}
    for row in rows:
        if _time(row["source"]["available_at"]) > _time(at):
            continue
        ident = key(row["source"])[:-1]
        if ident not in found or row["source"]["version"] > found[ident]["source"]["version"]:
            found[ident] = row
    return list(found.values())


def _stamp(row, value):
    if not isinstance(value, str) or not value:
        return None
    try:
        stamp = _time(value)
    except ValueError:
        return None
    return stamp if stamp <= _time(row["source"]["event_at"]) else None


def _interval(row, start, finish):
    a, b = _stamp(row, start), _stamp(row, finish)
    supported = a is not None and b is not None and a <= b
    return {
        "start": start,
        "finish": finish,
        "native_occurrence_chronology_supported": supported,
        "calculated_minutes": (
            datetime.fromisoformat(b) - datetime.fromisoformat(a)
        ).total_seconds()
        / 60
        if supported
        else None,
    }


def _attributes(rows, names):
    return [
        {"source": custody(r), "attributes": {k: detail(r)[k] for k in names if k in detail(r)}}
        for r in rows
    ]


def _ancestors(history, row, family, roles):
    return [
        r
        for r in history.ancestors(row)
        if r["logical_family"] == family and r["logical_system"] in roles
    ]


def _one_ancestor(history, row, family, roles):
    # Follow the closest exact full-native chain, never a latest-name lookup.
    # Direct named target wins over earlier versions further back in history;
    # same-level ambiguity remains unavailable.
    pending, visited = [row], {key(row["source"])}
    incident = detail(row).get("incident_id")
    while pending:
        targets = {}
        for current in pending:
            for join in history.joins:
                if key(join["origin"]) == key(current["source"]) and join["target"] is not None:
                    identity = key(join["target"])
                    if identity not in visited:
                        targets[identity] = history.index[identity]
        selected = [
            r
            for r in targets.values()
            if r["logical_family"] == family
            and r["logical_system"] in roles
            and (
                not isinstance(incident, str)
                or not incident
                or detail(r).get("incident_id") == incident
            )
        ]
        if selected:
            return selected[0] if len(selected) == 1 else None
        visited.update(targets)
        pending = list(targets.values())
    return None


def _rules(history, row):
    incident = detail(row).get("incident_id")
    candidates = [
        r
        for r in _effective(
            history.select("incident-history", {"inventory"}), row["source"]["event_at"]
        )
        if isinstance(incident, str) and incident and detail(r).get("incident_id") == incident
    ]
    rules = [detail(r).get("local_rules") for r in candidates]
    accepted = rules[0] if len(rules) == 1 and isinstance(rules[0], dict) else {}
    return candidates, accepted


def response_history(history):
    probes, tickets, escalations, recoveries, reviews, exceptions = [], [], [], [], [], []
    for row in history.select("incident-history", {"monitoring"}):
        d = detail(row)
        rules, local = _rules(history, row)
        requests = d.get("requests", [])
        require(
            isinstance(requests, list) and all(isinstance(v, dict) for v in requests),
            "Typed native probe vector required",
        )
        ids = _ids([v.get("request_id") for v in requests])
        require(
            all(
                type(v.get("http_status")) is int and 100 <= v["http_status"] <= 599
                for v in requests
            ),
            "Strict typed HTTP observation status required",
        )
        errors = sum(v["http_status"] >= 500 for v in requests)
        total = len(ids)
        require(
            all(
                k not in d or type(d[k]) is int and d[k] >= 0
                for k in ("total_requests", "error_requests")
            ),
            "Strict reported probe counts required",
        )
        window = _stamp(row, d.get("window_ends_at", d.get("recorded_at")))
        chronology = window is not None and all(
            _stamp(row, v.get("observed_at")) is not None and _time(v["observed_at"]) <= window
            for v in requests
        )
        percent = 100 * errors / total if total and chronology else None
        threshold = local.get("error_threshold_percent")
        require(threshold is None or _number(threshold), "Typed local severity threshold required")
        fact = {
            "source": custody(row),
            "local_rule_originals": [custody(r) for r in rules],
            "recomputed_total_requests": total,
            "recomputed_error_requests": errors,
            "reported_total_agrees": total == d.get("total_requests")
            if "total_requests" in d
            else None,
            "reported_error_agrees": errors == d.get("error_requests")
            if "error_requests" in d
            else None,
            "request_window_chronology_supported": chronology,
            "window_basis": "DECLARED_WINDOW_END"
            if "window_ends_at" in d
            else "NATIVE_RECORDED_OBSERVATION_CUTOFF",
            "calculated_error_percent": percent,
            "local_exercise_threshold_percent": threshold,
            "meets_local_incident_threshold": percent >= threshold
            if percent is not None and threshold is not None
            else None,
            "accepted_enterprise_severity_or_real_availability_conclusion": False,
        }
        if (
            fact["reported_total_agrees"] is False
            or fact["reported_error_agrees"] is False
            or not chronology
        ):
            exceptions.append({"facet": "PROBE_POPULATION", **fact})
        probes.append(fact)
    for row in history.select("incident-history", {"incident_ticket"}):
        d = detail(row)
        rules, local = _rules(history, row)
        observed = _one_ancestor(history, row, "incident-history", {"monitoring"})
        probe = next(
            (p for p in probes if observed and key(p["source"]) == key(observed["source"])), None
        )
        discovered = _stamp(row, d.get("discovered_at"))
        limit = local.get("escalation_due_minutes")
        require(limit is None or _number(limit), "Typed local escalation period required")
        due = (
            (datetime.fromisoformat(discovered) + timedelta(minutes=limit)).isoformat(
                timespec="microseconds"
            )
            if discovered and limit is not None
            else None
        )
        fact = {
            "source": custody(row),
            "local_rule_originals": [custody(r) for r in rules],
            "monitoring_original": custody(observed) if observed else None,
            "independent_monitoring_threshold_result": probe["meets_local_incident_threshold"]
            if probe
            else None,
            "recorded_local_severity": d.get("local_severity"),
            "recorded_classification": d.get("decision"),
            "discovery_timestamp_supported": discovered is not None,
            "original_discovered_at": d.get("discovered_at"),
            "calculated_local_escalation_due_at": due,
            "reported_escalation_due_at": d.get("escalation_due_at"),
            "reported_due_agrees": due == _time(d["escalation_due_at"])
            if due and isinstance(d.get("escalation_due_at"), str)
            else None,
            "real_security_incident_or_breach_classification_accepted": False,
        }
        if fact["reported_due_agrees"] is False or not fact["discovery_timestamp_supported"]:
            exceptions.append({"facet": "DISCOVERY_OR_ESCALATION_DUE", **fact})
        tickets.append(fact)
    for row in history.select("incident-history", {"escalation"}):
        d = detail(row)
        ticket = _one_ancestor(history, row, "incident-history", {"incident_ticket"})
        ticket_fact = next(
            (t for t in tickets if ticket and key(t["source"]) == key(ticket["source"])), None
        )
        interval = _interval(row, d.get("queued_at"), d.get("delivered_at"))
        due = ticket_fact["calculated_local_escalation_due_at"] if ticket_fact else None
        delivered = _stamp(row, d.get("delivered_at"))
        rules, _ = _rules(history, row)
        commander = detail(rules[0]).get("commander") if len(rules) == 1 else None
        fact = {
            "source": custody(row),
            "ticket_original": custody(ticket) if ticket else None,
            "delivery_interval": interval,
            "original_discovery_not_restarted": detail(ticket).get("discovered_at")
            if ticket
            else None,
            "local_due_at": due,
            "delivered_by_local_due": delivered <= due if delivered and due else None,
            "recipient_matches_declared_commander": d.get("recipient") == commander
            if commander
            else None,
            "recorded_delivery_state": d.get("delivery_state"),
            "real_oncall_or_external_receipt_verified": False,
        }
        if (
            fact["delivered_by_local_due"] is False
            or fact["recipient_matches_declared_commander"] is False
            or (
                d.get("delivery_state") == "DELIVERED"
                and not interval["native_occurrence_chronology_supported"]
            )
        ):
            exceptions.append({"facet": "ESCALATION_DELIVERY", **fact})
        escalations.append(fact)
    for row in history.select("incident-history", {"recovery"}):
        d = detail(row)
        ticket = _one_ancestor(history, row, "incident-history", {"incident_ticket"})
        rules, local = _rules(history, row)
        candidate_observation = _one_ancestor(history, row, "incident-history", {"monitoring"})
        candidate_detail = detail(candidate_observation) if candidate_observation else {}
        recovery_result_at = _stamp(row, d.get("restored_at"))
        observation = (
            candidate_observation
            if recovery_result_at is not None
            and "checkpoint_captured_at" in candidate_detail
            and "checkpoint_observed_at" in candidate_detail
            else None
        )
        observed = detail(observation) if observation else {}
        requests = observed.get("requests", [])
        require(
            isinstance(requests, list) and all(isinstance(v, dict) for v in requests),
            "Typed recovery probe vector required",
        )
        ids = _ids([v.get("request_id") for v in requests])
        require(
            all(
                type(v.get("http_status")) is int and 100 <= v["http_status"] <= 599
                for v in requests
            ),
            "Strict recovery status required",
        )
        supported = bool(requests) and all(
            _stamp(observation, v.get("observed_at")) is not None for v in requests
        )
        successes = sum(200 <= v["http_status"] < 300 for v in requests) if supported else None
        require(
            "successful_probes" not in d
            or type(d["successful_probes"]) is int
            and d["successful_probes"] >= 0,
            "Strict reported successful probe census required",
        )
        require(
            "checkpoint_age_minutes" not in d or _number(d["checkpoint_age_minutes"]),
            "Typed reported checkpoint age required",
        )
        required = local.get("recovery_probe_required_successes")
        require(
            required is None or type(required) is int and required > 0,
            "Strict required recovery-success census required",
        )
        checkpoint = observed.get("checkpoint_captured_at")
        activated = observed.get("checkpoint_observed_at")
        age = (
            _interval(observation, checkpoint, activated)
            if observation
            else _interval(row, None, None)
        )
        age_limit = local.get("recovery_checkpoint_age_limit_minutes")
        require(
            age_limit is None or _number(age_limit), "Typed local checkpoint age limit required"
        )
        authorization = d.get("authorization")
        fact = {
            "source": custody(row),
            "local_rule_originals": [custody(r) for r in rules],
            "ticket_original": custody(ticket) if ticket else None,
            "recorded_recovery_state": d.get("state"),
            "recovery_monitoring_original": custody(observation) if observation else None,
            "prior_diagnostic_not_relabelled_as_recovery_validation": custody(candidate_observation)
            if candidate_observation and observation is None
            else None,
            "restored_result_timestamp_supported": recovery_result_at is not None,
            "reported_success_count": d.get("successful_probes"),
            "reported_success_count_agrees": d.get("successful_probes") == successes
            if successes is not None and "successful_probes" in d
            else None,
            "reported_checkpoint_age_minutes": d.get("checkpoint_age_minutes"),
            "reported_checkpoint_age_agrees": d.get("checkpoint_age_minutes")
            == age["calculated_minutes"]
            if age["calculated_minutes"] is not None and "checkpoint_age_minutes" in d
            else None,
            "declared_probe_count": len(ids),
            "supported_successful_probe_count": successes,
            "required_local_success_count": required,
            "local_probe_success_requirement_met": successes >= required
            if successes is not None and required is not None
            else None,
            "checkpoint_age": age,
            "local_checkpoint_age_limit_minutes": age_limit,
            "checkpoint_within_local_limit": age["calculated_minutes"] <= age_limit
            if age["calculated_minutes"] is not None and age_limit is not None
            else None,
            "recorded_authorization": authorization,
            "recovery_credential_record_only": d.get("recovery_credential_ref"),
            "real_recovery_credentials_or_deployment_or_erasure_executed": False,
        }
        if (
            fact["local_probe_success_requirement_met"] is False
            or fact["checkpoint_within_local_limit"] is False
            or fact["reported_success_count_agrees"] is False
            or fact["reported_checkpoint_age_agrees"] is False
        ):
            exceptions.append({"facet": "RECOVERY_VALIDATION", **fact})
        recoveries.append(fact)
    for row in history.select("incident-history", {"postincident_review"}):
        d = detail(row)
        replay = _one_ancestor(history, row, "incident-history", {"recovery"})
        ticket = _one_ancestor(history, row, "incident-history", {"incident_ticket"})
        interval = _interval(
            row,
            _stamp(ticket, detail(ticket).get("discovered_at")) if ticket else None,
            _stamp(replay, detail(replay).get("restored_at")) if replay else None,
        )
        performer = (
            detail(replay).get("performed_by", detail(replay).get("verified_by"))
            if replay
            else None
        )
        reviewer = d.get("reviewed_by")
        fact = {
            "source": custody(row),
            "recovery_original": custody(replay) if replay else None,
            "ticket_original": custody(ticket) if ticket else None,
            "reported_outage_cause": d.get("outage_cause"),
            "causal_assessment_status": d.get("causal_assessment_status"),
            "remaining_investigation": d.get("remaining_investigation"),
            "source_restoration_interval": interval,
            "reported_restoration_minutes": d.get("observed_service_restoration_minutes"),
            "restoration_claim_agrees": interval["calculated_minutes"]
            == d.get("observed_service_restoration_minutes")
            if interval["calculated_minutes"] is not None
            else None,
            "distinct_named_response_performer_and_reviewer": performer != reviewer
            if performer and reviewer
            else None,
            "notification_applicability_company_claim": d.get("notification_applicability"),
            "risk_update_company_statement": d.get("risk_update"),
            "independent_cause_or_qualified_second_line_accepted": False,
        }
        if (
            fact["restoration_claim_agrees"] is False
            or fact["distinct_named_response_performer_and_reviewer"] is False
        ):
            exceptions.append({"facet": "POSTINCIDENT_REVIEW", **fact})
        reviews.append(fact)
    return {
        "monitoring_populations": probes,
        "ticket_occurrences": tickets,
        "escalation_occurrences": escalations,
        "recovery_occurrences": recoveries,
        "postincident_reviews": reviews,
        "response_status_communications": _attributes(
            history.select("incident-history", {"status_updates"}),
            ["audience", "sent_by", "service_state", "recovery_state"],
        ),
        "local_design_originals": _attributes(
            history.select("incident-history", {"inventory"}),
            [
                "local_rules",
                "commander",
                "responder",
                "outside_response_reviewer",
                "service_definition_state",
            ],
        ),
        "exceptions": exceptions,
        "containment_eradication_or_enterprise_complete_population_performed": False,
    }


def corrective_history(history):
    validations, exceptions = [], []
    for row in history.select("incident-history", {"action_validation"}):
        d = detail(row)
        replay = _one_ancestor(history, row, "incident-history", {"dispatch_replay"})
        action = _one_ancestor(history, row, "incident-history", {"corrective_action"})
        observed = detail(replay) if replay else {}
        interval = (
            _interval(replay, observed.get("queued_at"), observed.get("fallback_delivered_at"))
            if replay
            else _interval(row, None, None)
        )
        reported = _interval(row, d.get("queued_at"), d.get("fallback_delivered_at"))
        timeout = observed.get("timeout_minutes")
        require(timeout is None or _number(timeout), "Typed local fallback timeout required")
        require(
            "elapsed_minutes" not in d or _number(d["elapsed_minutes"]),
            "Typed reported validation duration required",
        )
        expected = d.get("expected_timeout_minutes")
        require(expected is None or _number(expected), "Typed recorded expected timeout required")
        validator, owner = d.get("validated_by"), detail(action).get("owner") if action else None
        actor = observed.get("actor")
        valid = interval["calculated_minutes"] is not None
        fact = {
            "source": custody(row),
            "replay_original": custody(replay) if replay else None,
            "action_original": custody(action) if action else None,
            "independent_replay_interval": interval,
            "validation_record_interval": reported,
            "reported_elapsed_agrees": d.get("elapsed_minutes") == interval["calculated_minutes"]
            if valid
            else None,
            "validation_timestamps_match_exact_replay": _json(
                [d.get("queued_at"), d.get("fallback_delivered_at")]
            )
            == _json([observed.get("queued_at"), observed.get("fallback_delivered_at")])
            if replay
            else None,
            "timeout_matches_exact_replay": expected == timeout
            if replay and expected is not None and timeout is not None
            else None,
            "fallback_within_declared_timeout": interval["calculated_minutes"] <= timeout
            if valid and timeout is not None
            else None,
            "distinct_named_action_owner_replayer_and_validator": validator not in {owner, actor}
            if validator and owner and actor
            else None,
            "recorded_action_state": detail(action).get("state") if action else None,
            "real_preventive_change_recurrence_retest_or_qualified_closure": False,
        }
        if (replay is not None and not valid) or any(
            fact[k] is False
            for k in (
                "reported_elapsed_agrees",
                "validation_timestamps_match_exact_replay",
                "timeout_matches_exact_replay",
                "fallback_within_declared_timeout",
                "distinct_named_action_owner_replayer_and_validator",
            )
        ):
            exceptions.append(fact)
        validations.append(fact)
    closure_discrepancies = []
    for row in history.select(
        "assurance",
        {
            "issue_screening",
            "issue_finding",
            "owner_notification",
            "remediation_request",
            "overdue_escalation",
        },
    ):
        d = detail(row)
        require(
            all(
                name not in d or type(d[name]) is bool
                for name in (
                    "finding_closed",
                    "validation_performed",
                    "durable_bypass_prevention_implemented",
                )
            ),
            "Strict assurance closure/validation flags required",
        )
        if d.get("finding_closed") is True and (
            d.get("validation_performed") is False
            or d.get("durable_bypass_prevention_implemented") is False
        ):
            closure_discrepancies.append(
                {
                    "source": custody(row),
                    "recorded_finding_closed": True,
                    "recorded_validation_performed": d.get("validation_performed"),
                    "recorded_durable_prevention_implemented": d.get(
                        "durable_bypass_prevention_implemented"
                    ),
                    "company_closure_claim_supported": False,
                    "professional_closure_accepted": False,
                }
            )
    exceptions.extend(closure_discrepancies)
    return {
        "company_closure_discrepancies": closure_discrepancies,
        "declared_actions_before_selection": _attributes(
            history.select("incident-history", {"corrective_action"}),
            ["owner", "due_at", "change", "state", "completion_condition"],
        ),
        "original_dispatch_replays": _attributes(
            history.select("incident-history", {"dispatch_replay"}),
            [
                "queued_at",
                "fallback_delivered_at",
                "delivery_state",
                "timeout_minutes",
                "actor",
                "production_dispatch",
            ],
        ),
        "independent_selected_action_validations": validations,
        "separate_assurance_closure_statements": _attributes(
            history.select(
                "assurance",
                {
                    "issue_screening",
                    "issue_finding",
                    "owner_notification",
                    "remediation_request",
                    "overdue_escalation",
                },
            ),
            [
                "severity",
                "severity_factors",
                "plan_response_due_at",
                "plan_approval",
                "validation_performed",
                "finding_closed",
                "governance_delivery_status",
                "risk_acceptance",
            ],
        ),
        "exceptions": exceptions,
        "technical_retry_or_closed_ticket_does_not_close_enterprise_finding": True,
    }


def attempted_intake(history):
    facts, exceptions = [], []
    operations = history.select("supplementalops", {"access_operation"})
    for row in history.select("supplementalops", {"incident_intake"}):
        d = detail(row)
        ids = _ids(d.get("source_operation_ids", []))
        selected = [
            r
            for r in _effective(operations, row["source"]["event_at"])
            if r["source"]["record"] in ids or detail(r).get("request", {}).get("request_id") in ids
        ]
        missing = sorted(
            ids
            - {r["source"]["record"] for r in selected}
            - {detail(r).get("request", {}).get("request_id") for r in selected}
        )
        denied = bool(selected) and all(detail(r).get("decision") == "DENY" for r in selected)
        included = d.get("security_incident_definition_includes_attempts")
        require(
            included is None or type(included) is bool,
            "Strict attempted-incident definition flag required",
        )
        fact = {
            "source": custody(row),
            "source_operation_originals": [custody(r) for r in selected],
            "missing_operation_originals": missing,
            "all_selected_original_decisions_deny": denied,
            "source_definition_includes_attempts": included,
            "local_attempt_intake_supported": included is True
            and denied
            and not missing
            and _stamp(row, d.get("received_at")) is not None,
            "company_reported_succeeded": d.get("succeeded"),
            "company_intake_type": d.get("intake_type"),
            "actual_severity_interference_or_full_dismissal_population_accepted": False,
            "security_event_without_actual_phi_not_assumed_hipaa_breach": True,
        }
        if d.get("succeeded") is True and denied:
            exceptions.append(fact)
        facts.append(fact)
    return {
        "selected_attempt_intake_occurrences": facts,
        "separate_concern_channel_history": _attributes(
            history.select(
                "prdconcern",
                {"simulated_inbox", "case_intake", "concern_assessment", "exception_register"},
            ),
            [
                "customer_id",
                "service_id",
                "claimant_customer_identity_verified",
                "status",
                "external_notice_duty",
                "real_external_messages_sent",
            ],
        ),
        "original_logging_alerts": _attributes(
            [
                r
                for f in ("baseline-logging", "logging-history")
                for r in history.select(
                    f, {"detection_alerts", "detection_review", "publisher_events"}
                )
            ],
            ["rule_id", "severity", "owner_id", "event", "status"],
        ),
        "exceptions": exceptions,
        "complete_incident_and_dismissed_case_census_established": False,
    }


def breach_and_notice(history):
    decisions, clocks, deliveries, exceptions = [], [], [], []
    # A role decision/contract/marker flow is not itself a breach case. Optional
    # explicit case attributes must be present in an actual collected legal record.
    for row in history.select("phi_ba", {"legal_decision"}):
        d = detail(row)
        case = d.get("breach_case")
        if case is None:
            continue
        require(
            isinstance(case, dict) and isinstance(case.get("case_id"), str) and case["case_id"],
            "Explicit typed fictional breach case required",
        )
        for flag in (
            "phi_involved",
            "impermissible_use_or_disclosure",
            "encryption_protection_claimed",
            "no_notice_claimed",
        ):
            require(
                flag not in case or type(case[flag]) is bool,
                "Strict fictional breach decision flag required",
            )
        factors = case.get("risk_factors", {})
        require(isinstance(factors, dict), "Typed breach factor attributes required")
        missing = [
            name
            for name in RISK_FACTORS
            if name not in factors or factors[name] in (None, "", {}, [])
        ]
        encryption = case.get("encryption_original_refs", [])
        require(isinstance(encryption, list), "Typed encryption support pointer vector required")
        supports = [
            history.resolve(
                row,
                ref,
                expected={"supplementalops.key_custody", "supplementalops.integrity_operation"},
            )
            for ref in encryption
        ]
        protected_supported = bool(supports) and all(
            status == "EXACT_AVAILABLE_ORIGINAL" for _, status in supports
        )
        fact = {
            "source": custody(row),
            "case_id": case["case_id"],
            "phi_involved_recorded": case.get("phi_involved"),
            "impermissible_use_or_disclosure_recorded": case.get("impermissible_use_or_disclosure"),
            "examined_recorded_risk_factors": factors,
            "omitted_examined_risk_factors": missing,
            "encryption_claim_support_originals": [custody(r) for r, _ in supports if r],
            "encryption_support_statuses": [status for _, status in supports],
            "encryption_claim_has_exact_support_witnesses": protected_supported,
            "recorded_no_notice": case.get("no_notice_claimed"),
            "source_case_occurrence_at": case.get("occurred_at"),
            "case_occurrence_chronology_supported": _stamp(row, case.get("occurred_at"))
            is not None,
            "security_without_phi_distinguished": case.get("phi_involved") is False,
            "actual_crypto_or_legal_breach_determination_accepted": False,
        }
        if (
            case.get("no_notice_claimed") is True
            and case.get("phi_involved") is True
            and (
                missing
                or case.get("encryption_protection_claimed") is True
                and not protected_supported
            )
        ):
            exceptions.append({"facet": "UNSUBSTANTIATED_NO_NOTICE", **fact})
        decisions.append(fact)
        awareness = case.get("awareness_events", [])
        require(
            isinstance(awareness, list) and all(isinstance(v, dict) for v in awareness),
            "Typed original agent awareness history required",
        )
        available = [(_stamp(row, v.get("known_at")), v) for v in awareness]
        supported, awareness_support = [], []
        for stamp, event in available:
            ref = event.get("original_ref")
            original, status = (
                history.resolve(
                    row,
                    ref,
                    expected={
                        "incident-history.incident_ticket",
                        "supplementalops.incident_intake",
                        "prdconcern.simulated_inbox",
                        "phi_ba.exception_register",
                    },
                )
                if isinstance(ref, dict)
                else (None, "EXACT_AGENT_AWARENESS_ORIGINAL_ABSENT")
            )
            field = event.get("timestamp_field")
            body = detail(original) if original else {}
            actors = {
                body.get(k)
                for k in ("actor", "actor_id", "reported_by", "receiver", "assigned_responder")
                if isinstance(body.get(k), str)
            }
            case_occurred = _stamp(row, case.get("occurred_at"))
            causal_awareness = (
                case_occurred is not None and stamp is not None and case_occurred <= stamp
            )
            exact = (
                original is not None
                and field in {"discovered_at", "received_at", "detected_at"}
                and _stamp(original, body.get(field)) == stamp
                and stamp is not None
                and event.get("actor_id") in actors
            )
            awareness_support.append(
                {
                    "declared_event": event,
                    "original_status": status,
                    "original": custody(original) if original else None,
                    "exact_original_awareness_field_and_actor_match": exact,
                    "awareness_not_before_supported_case_occurrence": causal_awareness,
                }
            )
            if exact and causal_awareness:
                supported.append((stamp, event))
        discovery = min(stamp for stamp, _ in supported) if supported else None
        maximum = case.get("declared_training_max_notice_days")
        contract_hours = case.get("declared_contract_notice_hours")
        require(
            maximum is None or type(maximum) is int and maximum > 0,
            "Strict declared training notice ceiling required",
        )
        require(
            contract_hours is None or _number(contract_hours),
            "Typed declared contract notice period required",
        )
        # Explicit original policy/contract pointers are required before arithmetic
        # is treated as supported; no natural-language/legal-rule inference.
        policy_ref, contract_ref = case.get("notice_policy_original"), case.get("contract_original")
        policy, ps = (
            history.resolve(
                row, policy_ref, expected={"supplementalops.policy_document"}, at=discovery
            )
            if isinstance(policy_ref, dict)
            else (None, "EXACT_NOTICE_POLICY_ABSENT")
        )
        contract, cs = (
            history.resolve(row, contract_ref, expected={"phi_ba.contract_register"}, at=discovery)
            if isinstance(contract_ref, dict)
            else (None, "EXACT_CONTRACT_ABSENT")
        )
        if discovery is None:
            policy, ps = None, "ORIGINAL_DISCOVERY_UNAVAILABLE_FOR_EFFECTIVE_POLICY"
            contract, cs = None, "ORIGINAL_DISCOVERY_UNAVAILABLE_FOR_EFFECTIVE_CONTRACT"
        maximum_supported = (
            policy is not None
            and type(detail(policy).get("training_max_notice_days")) is int
            and detail(policy).get("training_max_notice_days") == maximum
            and maximum is not None
        )
        contract_supported = (
            contract is not None
            and _number(detail(contract).get("training_notice_hours"))
            and detail(contract).get("training_notice_hours") == contract_hours
            and contract_hours is not None
        )
        candidates = []
        if discovery and maximum_supported:
            candidates.append(
                (datetime.fromisoformat(discovery) + timedelta(days=maximum)).isoformat(
                    timespec="microseconds"
                )
            )
        if discovery and contract_supported:
            candidates.append(
                (datetime.fromisoformat(discovery) + timedelta(hours=contract_hours)).isoformat(
                    timespec="microseconds"
                )
            )
        due = min(candidates) if candidates else None
        claimed_start = case.get("clock_started_at")
        delivered = _stamp(row, case.get("upstream_notice_delivered_at"))
        delays = case.get("law_enforcement_delay_records", [])
        require(
            isinstance(delays, list) and all(isinstance(v, dict) for v in delays),
            "Typed claimed law-enforcement delay vector required",
        )
        delay_attributes = []
        oral_ceiling = detail(policy).get("training_oral_delay_ceiling_days") if policy else None
        require(
            oral_ceiling is None or type(oral_ceiling) is int and oral_ceiling > 0,
            "Strict declared oral-delay ceiling required",
        )
        for delayed in delays:
            days = delayed.get("specified_days")
            require(
                days is None or type(days) is int and days > 0,
                "Strict claimed delay duration required",
            )
            delay_ref = delayed.get("original_ref")
            original, status = (
                history.resolve(row, delay_ref, expected={"phi_ba.legal_decision"})
                if isinstance(delay_ref, dict)
                else (None, "EXACT_DELAY_REQUEST_ORIGINAL_ABSENT")
            )
            source_delay = detail(original).get("law_enforcement_delay") if original else None
            source_matches = (
                (
                    isinstance(source_delay, dict)
                    and all(
                        _json(delayed.get(name)) == _json(source_delay.get(name))
                        for name in ("kind", "identity", "specified_days")
                    )
                )
                if original
                else None
            )
            excessive = (
                days > oral_ceiling
                if delayed.get("kind") == "ORAL" and days is not None and oral_ceiling is not None
                else None
            )
            delay_attributes.append(
                {
                    "claimed_delay": delayed,
                    "delay_original_status": status,
                    "delay_original": custody(original) if original else None,
                    "claimed_kind_identity_duration_match_exact_original": source_matches,
                    "declared_oral_policy_ceiling_days": oral_ceiling,
                    "oral_duration_exceeds_declared_policy_ceiling": excessive,
                    "claimed_delay_not_added_to_notice_due_without_accepted_authority": True,
                }
            )
        clock = {
            "source": custody(row),
            "case_id": case["case_id"],
            "supported_original_agent_awareness": [
                {"known_at": stamp, **event} for stamp, event in supported
            ],
            "native_agent_awareness_examinations": awareness_support,
            "unsupported_awareness_events": [event for stamp, event in available if stamp is None],
            "earliest_supported_discovery_at": discovery,
            "claimed_clock_started_at": claimed_start,
            "clock_restarted_after_original_discovery": _time(claimed_start) > discovery
            if isinstance(claimed_start, str) and discovery
            else None,
            "policy_original_status": ps,
            "contract_original_status": cs,
            "policy_original": custody(policy) if policy else None,
            "contract_original": custody(contract) if contract else None,
            "declared_training_ceiling_supported": maximum_supported,
            "declared_contract_period_supported": contract_supported,
            "earliest_declared_due_at": due,
            "recorded_upstream_delivered_at": case.get("upstream_notice_delivered_at"),
            "upstream_delivery_within_declared_limit": delivered <= due
            if delivered and due
            else None,
            "management_confirmation_does_not_restart_discovery": True,
            "ceiling_is_not_routine_target_or_without_unreasonable_delay_conclusion": True,
            "claimed_law_enforcement_delays": delays,
            "original_oral_written_delay_attribute_examinations": delay_attributes,
            "law_enforcement_authority_and_valid_oral_written_delay_accepted": False,
            "incomplete_initial_information_recorded": case.get("initial_information_incomplete"),
            "statutory_law_period_applicability_and_real_delivery_verified": False,
        }
        if (
            clock["clock_restarted_after_original_discovery"] is True
            or clock["upstream_delivery_within_declared_limit"] is False
            or any(
                v["oral_duration_exceeds_declared_policy_ceiling"] is True
                or v["claimed_kind_identity_duration_match_exact_original"] is False
                for v in delay_attributes
            )
        ):
            exceptions.append({"facet": "NOTICE_CLOCK", **clock})
        clocks.append(clock)
        affected = case.get("affected_individual_ids", [])
        total = len(_ids(affected)) if "affected_individual_ids" in case else None
        jurisdictions = case.get("resident_ids_by_jurisdiction", {})
        require(isinstance(jurisdictions, dict), "Typed resident jurisdiction census required")
        resident_ids = {name: _ids(values) for name, values in jurisdictions.items()}
        population_bound = (
            set().union(*resident_ids.values()) <= set(affected)
            if "affected_individual_ids" in case and "resident_ids_by_jurisdiction" in case
            else None
        )
        notice_content = case.get("individual_notice_content")
        content_fields = (
            detail(policy).get("training_required_notice_content_fields") if policy else None
        )
        content_required = _ids(content_fields) if content_fields is not None else None
        posting = _interval(
            row, case.get("substitute_posting_start_at"), case.get("substitute_posting_finish_at")
        )
        missing_content = (
            sorted(content_required - set(notice_content))
            if content_required is not None and isinstance(notice_content, dict)
            else None
        )
        delivery = {
            "source": custody(row),
            "case_id": case["case_id"],
            "recomputed_total_individuals": total,
            "affected_individual_census_available": "affected_individual_ids" in case,
            "resident_jurisdiction_census_available": "resident_ids_by_jurisdiction" in case,
            "jurisdiction_resident_counts": {name: len(v) for name, v in resident_ids.items()},
            "residents_all_in_total_individual_census": population_bound,
            "authored_more_than_500_media_training_threshold": {
                name: len(v) > 500 for name, v in resident_ids.items()
            },
            "authored_500_or_more_total_training_threshold": total >= 500
            if total is not None
            else None,
            "individual_delegated_notice_content": notice_content,
            "missing_declared_notice_content_fields": missing_content,
            "contact_quality_record": case.get("contact_quality_record"),
            "substitute_posting_start_at": case.get("substitute_posting_start_at"),
            "substitute_posting_finish_at": case.get("substitute_posting_finish_at"),
            "substitute_posting_interval": posting,
            "meets_authored_90_day_posting_attribute": posting["calculated_minutes"] >= 90 * 1440
            if posting["calculated_minutes"] is not None
            else None,
            "substitute_phone_record": case.get("substitute_phone_record"),
            "covered_entity_reporting_and_limited_delegation_record": case.get(
                "reporting_delegation"
            ),
            "upstream_associate_notice_separate_from_delegated_individual_media_reporting": True,
            ("actual_delegation_authority_contact_delivery_posting_phone_or_reporting_verified"): (
                False
            ),
        }
        if (
            population_bound is False
            or missing_content
            or delivery["meets_authored_90_day_posting_attribute"] is False
        ):
            exceptions.append({"facet": "AFFECTED_POPULATION_OR_NOTICE_ATTRIBUTES", **delivery})
        deliveries.append(delivery)
    return {
        "explicit_breach_case_examinations": decisions,
        "separate_discovery_and_notice_clocks": clocks,
        "separate_individual_jurisdiction_and_total_population_examinations": deliveries,
        "case_attributes_available": bool(decisions),
        "clause_attribute_availability": {
            "ACTION-H-BREACH-DECISION": bool(decisions),
            "CHECK-HIPAA:164.400": any(
                d["case_occurrence_chronology_supported"] for d in decisions
            ),
            "ACTION-H-NOTICE-CLOCK": any(
                c["earliest_supported_discovery_at"] is not None
                and c["earliest_declared_due_at"] is not None
                for c in clocks
            ),
            "CHECK-HIPAA:164.404": any(
                d["individual_delegated_notice_content"] is not None for d in deliveries
            ),
            "CHECK-HIPAA:164.406": any(
                d["resident_jurisdiction_census_available"] for d in deliveries
            ),
            "CHECK-HIPAA:164.408": any(
                d["affected_individual_census_available"] for d in deliveries
            ),
        },
        "contract_and_role_witnesses_not_breach_cases": _attributes(
            history.select(
                "phi_ba",
                {
                    "operation_scope",
                    "legal_decision",
                    "contract_register",
                    "contract_approval",
                    "exception_register",
                },
            ),
            [
                "legal_role_decision",
                "synthetic_terms",
                "actual_legal_applicability",
                "actual_sable_harbor_ba_status",
                "detected_at",
                "exception_open",
                "limited_delegation_scope",
            ],
        ),
        "exceptions": exceptions,
        "actual_breach_or_notice_legal_applicability_accepted": False,
    }


def description_population(history):
    inputs = _attributes(
        history.select("incident-history", {"incident_ticket", "corrective_action"}),
        ["incident_id", "state", "decision", "change"],
    )
    assertions = []
    for row in history.select("assurance", {"issue_screening", "issue_finding"}):
        d = detail(row)
        declared = d.get("disclosed_incident_ids")
        if declared is None:
            continue
        named = _ids(declared)
        incidents = {
            detail(r)["incident_id"]
            for r in _effective(
                history.select("incident-history", {"incident_ticket"}), row["source"]["event_at"]
            )
            if isinstance(detail(r).get("incident_id"), str)
        }
        assertions.append(
            {
                "source": custody(row),
                "independent_incident_ids": sorted(incidents),
                "declared_disclosure_incident_ids": sorted(named),
                "omitted_independent_incident_ids": sorted(incidents - named),
                "professional_description_assertion_or_relevance_acceptance": False,
            }
        )
    return {
        "independent_incident_change_inputs": inputs,
        "explicit_description_assertion_comparisons": assertions,
        "change_vendor_disclosure_complete_denominator_established": False,
        "exceptions": [a for a in assertions if a["omitted_independent_incident_ids"]],
    }


def _task_facts(task, analyses):
    response, corrective, intake, notice, description = analyses
    control, kind = task["control_id"], task["kind"]
    clause = task["task_id"].split("-corporate-", 1)[1]
    families = {"incident-history", "supplementalops", "baseline-logging", "logging-history"}
    if control == "SH-INC-001":
        facets = {
            "design_local_scope_roles_and_thresholds": response["local_design_originals"],
            "independent_probe_and_ticket_classification": [
                response["monitoring_populations"],
                response["ticket_occurrences"],
            ],
            "actual_original_escalation_and_communication_trace": [
                response["escalation_occurrences"],
                response["response_status_communications"],
            ],
            "attempted_access_and_unverified_concern_intake": intake,
            "live_command_containment_eradication_recovery_authority": "UNPERFORMED",
        }
        exceptions = response["exceptions"] + intake["exceptions"]
    elif control == "SH-INC-002":
        facets = {
            "exact_incident_recovery_and_separate_notice_analysis": response,
            "explicit_breach_risk_factors_and_upstream_clock": notice,
            "independent_disclosure_population_comparison": description,
        }
        families |= {"phi_ba", "assurance", "prdconcern"}
        exceptions = response["exceptions"] + notice["exceptions"] + description["exceptions"]
    elif control == "SH-INC-003":
        facets = {
            "source_cause_and_remaining_investigation_not_independent_cause": response[
                "postincident_reviews"
            ],
            "declared_corrective_action_and_risk_update": corrective[
                "declared_actions_before_selection"
            ],
            "earlier_recovery_failures_and_later_originals": response["recovery_occurrences"],
            "stakeholder_communication_scope": response["response_status_communications"],
        }
        exceptions = [
            e
            for e in response["exceptions"]
            if e["facet"] in {"POSTINCIDENT_REVIEW", "RECOVERY_VALIDATION"}
        ]
    else:
        facets = {
            "dated_action_owner_due_and_execution_state": corrective[
                "declared_actions_before_selection"
            ],
            "actual_original_replay_before_validation": corrective["original_dispatch_replays"],
            "independently_reperformed_timing_and_named_validator": corrective[
                "independent_selected_action_validations"
            ],
            "separate_assurance_plan_governance_and_closure_statements": corrective[
                "separate_assurance_closure_statements"
            ],
        }
        families.add("assurance")
        exceptions = corrective["exceptions"]
    needs_breach_case = clause.startswith("CHECK-HIPAA:") or clause in {
        "ACTION-H-BREACH-DECISION",
        "ACTION-H-NOTICE-CLOCK",
    }
    if needs_breach_case:
        field = (
            "explicit_breach_case_examinations"
            if clause in {"ACTION-H-BREACH-DECISION", "CHECK-HIPAA:164.400"}
            else "separate_discovery_and_notice_clocks"
            if clause == "ACTION-H-NOTICE-CLOCK"
            else "separate_individual_jurisdiction_and_total_population_examinations"
        )
        facets = {
            "exact_additional_clause": clause,
            "clause_specific_original_case_attributes": notice[field],
            "case_attributes_available": notice["case_attributes_available"],
            "exact_clause_attributes_available": notice["clause_attribute_availability"][clause],
            "company_role_and_contract_witnesses_are_not_cases": notice[
                "contract_and_role_witnesses_not_breach_cases"
            ],
            "local_incident_vs_regulated_notice_duty_separated": True,
            "qualified_legal_applicability_or_complete_clause_conditions": "UNPERFORMED",
        }
        families = {"phi_ba", "supplementalops"}
        exceptions = notice["exceptions"]
    elif clause == "ACTION-S-DESCRIPTION":
        facets = description
        families = {"assurance", "incident-history"}
        exceptions = description["exceptions"]
    elif clause == "CHECK-SOC2:CC7.3":
        facets = {
            "local_threshold_reperformance": response["monitoring_populations"],
            "dated_ticket_and_attempt_intake": [response["ticket_occurrences"], intake],
            "dismissed_event_rationale_and_accepted_criteria_denominator": "UNPERFORMED",
        }
    elif clause == "CHECK-SOC2:CC7.4":
        facets = {
            "original_command_escalation_and_recovery_witnesses": response,
            "separate_regulated_notice_clock": notice["separate_discovery_and_notice_clocks"],
            "real_containment_eradication_and_qualified_recovery_authorization": "UNPERFORMED",
        }
        families.add("phi_ba")
    elif clause == "CHECK-SOC2:CC7.5":
        facets = {
            "restored_service_original_validation_and_communications": [
                response["recovery_occurrences"],
                response["response_status_communications"],
            ],
            "reported_cause_vs_unfinished_investigation": response["postincident_reviews"],
            "action_execution_replay_validation_and_separate_closure": corrective,
            "accepted_prevent_recurrence_representative_change_retest": "UNPERFORMED",
        }
        families.add("assurance")
        exceptions += corrective["exceptions"]
    keys = list(facets)
    if kind == "TOD":
        primary = {k: facets[k] for k in keys[:1]}
    elif kind == "IMPLEMENTATION":
        primary = {k: facets[k] for k in keys[1:3] or keys}
    elif kind == "TOE":
        primary = {k: facets[k] for k in keys[2:] or keys}
    else:
        primary = facets
    return (
        {
            "control_id": control,
            "exact_clause": clause,
            "task_kind": kind,
            "task_kind_primary_attributes": primary,
            "control_specific_facets": facets,
            "all_authored_steps_or_full_clause_performed": False,
        },
        exceptions,
        families,
        needs_breach_case and not notice["clause_attribute_availability"][clause],
    )


def _aggregate(label, facts, rows, status):
    chunks = [rows[n : n + 20] for n in range(0, len(rows), 20)]
    ids = [label] + [f"{label}-CITE-{n + 1:04d}" for n in range(1, len(chunks))]
    result = []
    for n, chunk in enumerate(chunks):
        group = {
            "aggregate_observation_id": label,
            "citation_part_index": n + 1,
            "citation_part_count": len(chunks),
            "all_citation_part_ids": ids,
            "this_part_extends_aggregate_direct_citations": True,
        }
        body = (
            {**facts, "citation_group": group}
            if n == 0
            else {
                "citation_group": group,
                "source_custody_subset": [custody(r) for r in chunk],
                "aggregate_facts_held_in_observation": label,
            }
        )
        require(len(ids[n]) <= 128, "Bounded exact B09 observation ID required")
        result.append(
            {
                "id": ids[n],
                "facts": body,
                "status": status,
                "evidence": [
                    {
                        "artifact_id": r["artifact_id"],
                        "sha256": r["artifact_sha256"],
                        "locator": "$",
                    }
                    for r in chunk
                ],
            }
        )
    return result


def examine(records, *, as_of, scratch_root):
    """Pure actual-retained-byte examination; scratch_root is never opened."""
    history = History(records, as_of=as_of)
    analyses = (
        response_history(history),
        corrective_history(history),
        attempted_intake(history),
        breach_and_notice(history),
        description_population(history),
    )
    task_contracts, output = contracts(), []
    for task in task_plan():
        facts, exceptions, families, exact_scope_missing = _task_facts(task, analyses)
        rows = history.supported_rows(facts)
        missing = not rows or exact_scope_missing
        if missing:
            rows = [r for r in history.rows if r["logical_family"] in families] or history.rows[:1]
        while True:
            included = {key(r["source"]) for r in rows}
            joins = [j for j in history.joins if key(j["origin"]) in included]
            targets = {key(j["target"]) for j in joins if j["target"] is not None}
            linked = [r for r in history.rows if key(r["source"]) in targets - included]
            if not linked:
                break
            rows.extend(linked)
        status = (
            "EXCEPTION_RECORDED" if exceptions else "SUPPORT_UNAVAILABLE" if missing else "OBSERVED"
        )
        observations = _aggregate(
            "EXACT-TASK-ATTRIBUTES",
            {
                "authored_instruction": task["authored_instruction"],
                "task_kind_rule": task["task_kind_rule"],
                "examined_attributes": facts,
                "bounded_exceptions": exceptions,
                "full_clause_performed": False,
            },
            rows,
            status,
        )
        for n, r in enumerate(rows):
            observations.append(
                {
                    "id": (
                        f"ACQUISITION-CONTEXT-{n + 1:04d}"
                        if missing
                        else f"NATIVE-OCCURRENCE-{n + 1:04d}"
                    ),
                    "facts": {
                        "source": custody(r),
                        "actual_retained_bytes_reparsed": True,
                        "task_specific_attributes_supported": not missing,
                        "full_period_completeness_not_asserted": True,
                    },
                    "status": "SUPPORT_UNAVAILABLE" if missing else "OBSERVED",
                    "evidence": [
                        {
                            "artifact_id": r["artifact_id"],
                            "sha256": r["artifact_sha256"],
                            "locator": "$",
                        }
                    ],
                }
            )
        if joins:
            observations.extend(
                _aggregate(
                    "EXACT-NATIVE-SUPPORT",
                    {"joins": joins, "recorded_action_chronology": history.action_chronology},
                    rows,
                    "SUPPORT_UNAVAILABLE"
                    if any(j["status"] != "EXACT_AVAILABLE_ORIGINAL" for j in joins)
                    else "OBSERVED",
                )
            )
        contract = task_contracts[task["task_id"]]
        output.append(
            {
                "task_id": task["task_id"],
                "artifact_ids": [r["artifact_id"] for r in rows],
                "observations": observations,
                "performed": contract["performed"],
                "unperformed": contract["unperformed"],
                "result": {
                    "schema": "SH_COLLECTED_INCIDENT_COMPLAINTS_TASK_EXAMINATION_V1",
                    "task_id": task["task_id"],
                    "authored_procedure": task["authored_procedure"],
                    "examined_attributes": facts,
                    "exceptions": exceptions,
                    "native_support": joins,
                    "selected_native_population_before_selection": [custody(r) for r in rows]
                    if not missing
                    else [],
                    "acquisition_context_witnesses": [custody(r) for r in rows] if missing else [],
                    "required_task_attribute_population_available": not missing,
                    "professional_or_actual_source_applicability_accepted": False,
                    "prior_audit_or_Key_outcomes_used": False,
                    "broader_unperformed": BROAD,
                },
                "disposition": {
                    "status": "IN_PROGRESS",
                    "conclusion": "FAIL" if exceptions else "LIMITATION",
                    "rationale": (
                        "Exact bounded discrepancies and missing broader support "
                        "retained separately."
                    )
                    if exceptions
                    else (
                        "Selected original-source attributes examined; broad and unavailable "
                        "criteria remain unperformed."
                    ),
                },
            }
        )
    return output
