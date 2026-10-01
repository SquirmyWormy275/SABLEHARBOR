"""Reconcile company assurance history from ordinary retained originals.

Company workpapers and attestations are examined as business records. They never
supply the auditor's verdict. This module does not read company databases, execute
stored queries, create evidence, update tasks or consult an instructor Key.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime

from .company_store import _time
from .fresh_sec003_procedure import CLOCK_ID, NATIVE_ID, require

BUSINESS_ID = tuple(k for k in CLOCK_ID if k != "imported_at")
FAMILIES = {"ass001002", "assurance", "assuranceops", "bcm", "transition"}


def custody(row):
    return {k: row["source"][k] for k in CLOCK_ID}


def _key(source):
    return tuple(source[k] for k in NATIVE_ID)


def _references(value, path="$"):
    """Keep every declared full native pointer and its original business location."""
    if isinstance(value, dict):
        if set(NATIVE_ID) <= value.keys():
            yield path, value
        else:
            for name, child in value.items():
                yield from _references(child, path + "." + name)
    elif isinstance(value, list):
        for number, child in enumerate(value):
            yield from _references(child, f"{path}[{number}]")


class CollectedHistory:
    """Typed, exact receipts and causal pointers within one collected branch."""

    def __init__(self, records, as_of):
        cutoff = _time(as_of)
        self.rows, self.index, self.joins = [], {}, []
        for record in records:
            source = record["source"]
            require(set(CLOCK_ID) <= source.keys(), "Exact collected source clocks required")
            require(
                type(source["version"]) is int and source["version"] > 0,
                "Strict positive collected version required",
            )
            require(
                all(isinstance(source[k], str) and source[k] for k in NATIVE_ID[:-1]),
                "Native company, branch, system and record required",
            )
            require(
                _time(source["event_at"]) <= _time(source["available_at"]) <= cutoff
                and _time(source["imported_at"]) <= _time(datetime.now(UTC).isoformat()),
                "Collected source chronology differs from examination boundary",
            )
            receipt = record["receipt"]
            require(
                all(receipt["source"].get(k) == source[k] for k in CLOCK_ID)
                and type(receipt["source"].get("version")) is int,
                "Ordinary collection receipt differs from native custody",
            )
            raw = record["retained_bytes"]
            require(isinstance(raw, bytes), "Actual retained bytes required")
            require(
                hashlib.sha256(raw).hexdigest() == source["sha256"] == record["artifact_sha256"],
                "Retained assurance artifact hash differs",
            )
            require(record["content_type"] == "application/json", "Typed business JSON required")
            document = json.loads(raw)
            require(isinstance(document, dict), "Structured business document required")
            family, role = record["logical_family"], record["logical_system"]
            require(
                family in FAMILIES and source["system"] == family + "." + role,
                "Business role differs from actual native system",
            )
            for clock in ("event_at", "available_at"):
                require(
                    clock not in document or document[clock] == source[clock],
                    "Document clock differs from native custody",
                )
            if family == "assurance" and "finding_closed" in document:
                require(type(document["finding_closed"]) is bool, "Typed finding closure required")
            key = _key(source)
            require(key not in self.index, "Duplicate collected native version")
            row = {**record, "document": document}
            self.rows.append(row)
            self.index[key] = row
        require(self.rows, "Collected company assurance history required")
        require(
            len({(r["source"]["company"], r["source"]["branch"]) for r in self.rows}) == 1,
            "One actually collected company branch required",
        )
        for row in self.rows:
            for path, ref in _references(row["document"]):
                target, status = self.resolve(row, ref)
                self.joins.append(
                    {
                        "from": custody(row),
                        "path": path,
                        "declared_reference": ref,
                        "status": status,
                        "to": custody(target) if target else None,
                    }
                )

    def selected(self, family, role):
        return [
            r for r in self.rows if r["logical_family"] == family and r["logical_system"] == role
        ]

    def resolve(self, origin, ref, *, role=None):
        require(
            isinstance(ref, dict)
            and set(BUSINESS_ID) <= ref.keys()
            and type(ref["version"]) is int
            and ref["version"] > 0,
            "Exact positive-version business reference required",
        )
        source = origin["source"]
        if (ref["company"], ref["branch"]) != (source["company"], source["branch"]):
            return None, "OUTSIDE_COLLECTED_BRANCH_AUTHORITY"
        target = self.index.get(_key(ref))
        if target is None:
            return None, "ORIGINAL_NOT_COLLECTED"
        fields = CLOCK_ID if "imported_at" in ref else BUSINESS_ID
        require(
            all(ref[k] == target["source"][k] for k in fields),
            "Collected business reference hash or clocks differ",
        )
        if role is not None and target["source"]["system"] not in role:
            return None, "ACTUAL_NATIVE_ROLE_DIFFERS"
        if _time(target["source"]["available_at"]) > _time(source["event_at"]):
            return None, "SOURCE_UNAVAILABLE_AT_COMPANY_EVENT"
        return target, "EXACT_AVAILABLE_ORIGINAL"

    def targets(self, row, field, *, role=None):
        values = row["document"].get(field, [])
        require(isinstance(values, list), "Business reference vector required")
        targets, limitations = [], []
        for ref in values:
            target, status = self.resolve(row, ref, role=role)
            if target:
                targets.append(target)
            else:
                limitations.append({"reference": ref, "status": status})
        return targets, limitations


def _check(attribute, evidence, *, exceptions=(), unperformed=()):
    return {
        "attribute": attribute,
        "performance": "PERFORMED" if evidence else "UNPERFORMED",
        "evidence": evidence,
        "exceptions": list(exceptions),
        "unperformed": list(unperformed),
    }


def _prior_issues(history, at, records=None):
    latest = {}
    for row in history.rows:
        if row["logical_family"] != "assurance" or (
            records is not None and row["source"]["record"] not in records
        ):
            continue
        if _time(row["source"]["available_at"]) > _time(at):
            continue
        if row["logical_system"] == "issue_finding":
            require(
                type(row["document"].get("finding_closed")) is bool,
                "Typed finding closure required",
            )
            latest.setdefault(row["source"]["record"], []).append(row)
    return [
        max(rows, key=lambda r: (_time(r["source"]["available_at"]), r["source"]["version"]))
        for rows in latest.values()
    ]


def _owner_assessments(history):
    evidence, errors, missing = [], [], []
    for owner in history.selected("ass001002", "owner_self_assessment"):
        body = owner["document"]
        scopes = [
            r
            for r in history.selected("ass001002", "monitoring_scope")
            if all(
                r["document"].get(k) == body.get(k) and body.get(k) is not None
                for k in ("quarter", "selected_control", "selected_service")
            )
            and _time(r["source"]["available_at"]) <= _time(owner["source"]["event_at"])
        ]
        if len(scopes) != 1:
            missing.append({"owner": custody(owner), "reason": "UNIQUE_PRIOR_SCOPE_NOT_COLLECTED"})
            continue
        original, limits = history.targets(scopes[0], "upstream_refs")
        missing.extend(limits)
        issue_ids = {r["source"]["record"] for r in original if r["logical_family"] == "assurance"}
        issues = _prior_issues(history, owner["source"]["event_at"], issue_ids)
        observed_ids = {r["source"]["record"] for r in issues}
        for screened in original:
            if (
                screened["source"]["system"] == "assurance.issue_screening"
                and screened["document"].get("status") == "SELECTED_DEFECT_REQUIRES_FINDING"
                and screened["source"]["record"] not in observed_ids
            ):
                missing.append(
                    {
                        "owner": custody(owner),
                        "screening": custody(screened),
                        "reason": "SCREENED_DEFECT_FINDING_HISTORY_NOT_COLLECTED",
                    }
                )
        open_issues = [r for r in issues if r["document"]["finding_closed"] is False]
        statement = body.get("statement")
        no_issue_claim = statement in {
            "SELECTED_RETEST_PASSED_NO_OPEN_ISSUE_REPORTED",
            "SELECTED_EXERCISE_REVIEWED_NO_SELECTED_DEFECT",
        }
        if statement is None:
            missing.append({"owner": custody(owner), "reason": "MANAGEMENT_STATEMENT_ABSENT"})
        if no_issue_claim and open_issues:
            errors.append(
                {
                    "owner": custody(owner),
                    "reason": "MANAGEMENT_NO_ISSUE_CLAIM_CONTRADICTED",
                    "issues": [custody(r) for r in open_issues],
                }
            )
        evidence.append(
            {
                "owner": custody(owner),
                "scope": custody(scopes[0]),
                "recorded_statement": statement,
                "actual_prior_open_findings": [custody(r) for r in open_issues],
                "classification": "MANAGEMENT_SELF_ASSESSMENT",
            }
        )
    return _check(
        "OWNER_CERTIFICATION_VERSUS_PRIOR_SELECTED_ISSUE_HISTORY",
        evidence,
        exceptions=errors,
        unperformed=[
            *missing,
            "Quarterly full-period owner execution counts, competence, backups and accountability "
            "response require additional originals; no company-wide certification inferred.",
        ],
    )


def _second_line(history):
    evidence, errors, missing = [], [], []
    for row in history.selected("ass001002", "second_line_observation"):
        body, joined = row["document"], {}
        for name, role in (
            ("technical_input", {"bcm.exercise_result"}),
            ("nontechnical_input", {"assurance.issue_finding", "assurance.issue_screening"}),
        ):
            if name not in body:
                missing.append({"observation": custody(row), "reason": name + "_ABSENT"})
                continue
            target, status = history.resolve(row, body[name], role=role)
            if target:
                joined[name] = target
            else:
                missing.append({"observation": custody(row), "reason": status, "field": name})
        owners = [
            r
            for r in history.selected("ass001002", "owner_self_assessment")
            if r["source"]["sha256"] == body.get("owner_submission_sha256")
            and _time(r["source"]["available_at"]) <= _time(row["source"]["event_at"])
        ]
        if len(owners) != 1:
            missing.append(
                {
                    "observation": custody(row),
                    "reason": "EXACT_PRIOR_OWNER_SUBMISSION_NOT_COLLECTED",
                }
            )
        screeners = [
            r
            for r in history.selected("assurance", "issue_screening")
            if r["document"].get("issue_manager_person_id") == body.get("actor_person_id")
            and _time(r["source"]["available_at"]) <= _time(row["source"]["event_at"])
        ]
        if screeners:
            errors.append(
                {
                    "observation": custody(row),
                    "reason": "EVALUATOR_PREVIOUSLY_SCREENED_ISSUE",
                    "prior_work": [custody(r) for r in screeners],
                }
            )
        evidence.append(
            {
                "observation": custody(row),
                "underlying_originals": {k: custody(v) for k, v in joined.items()},
                "owner_submission": custody(owners[0]) if len(owners) == 1 else None,
                "recorded_effectiveness_conclusion": body.get("evaluated_effectiveness"),
                "independence_verified": False,
            }
        )
    return _check(
        "SECOND_LINE_UNDERLYING_TECHNICAL_AND_NONTECHNICAL_ORIGINALS",
        evidence,
        exceptions=errors,
        unperformed=[
            *missing,
            "Risk-based enterprise/site selection, actual configuration effectiveness and "
            "qualified "
            "evaluator competence are not established by a monitoring note.",
        ],
    )


def _programme(history):
    evidence, errors, missing = [], [], []
    programmes = history.selected("assuranceops", "assurance_programme")
    for planned in programmes:
        body = planned["document"]
        if body.get("status") != "SCHEDULED":
            continue
        completed = [
            r
            for r in programmes
            if r["source"]["record"] == planned["source"]["record"]
            and r["document"].get("status") == "COMPLETED_SCOPED_INTERNAL_EVALUATION"
            and r["source"]["version"] > planned["source"]["version"]
        ]
        require(len(completed) <= 1, "Ambiguous selected workstream completion")
        done = completed[0] if completed else None
        reviews, limits = (
            history.targets(done, "dependencies", role={"assuranceops.assurance_review"})
            if done
            else ([], [])
        )
        missing.extend(limits)
        if done and not reviews:
            missing.append(
                {"completion": custody(done), "reason": "EXACT_QUALITY_REVIEW_NOT_COLLECTED"}
            )
        if done and _time(done["source"]["event_at"]) < _time(planned["source"]["available_at"]):
            errors.append({"plan": custody(planned), "reason": "COMPLETION_PRECEDES_PLAN"})
        if (
            done
            and body.get("due_at")
            and _time(done["source"]["event_at"]) > _time(body["due_at"])
        ):
            errors.append({"plan": custody(planned), "reason": "COMPLETION_AFTER_DUE_DATE"})
        if not done:
            missing.append(
                {
                    "plan": custody(planned),
                    "reason": "COMPLETION_OR_AUTHORIZED_DEFERRAL_NOT_COLLECTED",
                }
            )
        for review in reviews:
            rb = review["document"]
            if not isinstance(rb.get("reviewer_id"), str) or not isinstance(
                rb.get("preparer_id"), str
            ):
                missing.append({"review": custody(review), "reason": "REVIEW_IDENTITIES_ABSENT"})
            elif rb["reviewer_id"] == rb["preparer_id"]:
                errors.append({"review": custody(review), "reason": "SELF_REVIEW"})
        evidence.append(
            {
                "plan": custody(planned),
                "completion": custody(done) if done else None,
                "prior_exact_quality_reviews": [custody(r) for r in reviews],
            }
        )
    for close in history.selected("assuranceops", "assurance_period_reconciliation"):
        body = close["document"]
        ids = body.get("workstream_record_ids")
        require(
            isinstance(ids, list)
            and all(isinstance(x, str) for x in ids)
            and len(set(ids)) == len(ids),
            "Distinct declared workstream roster required",
        )
        prior = [
            r
            for r in programmes
            if r["source"]["record"] in ids
            and _time(r["source"]["available_at"]) <= _time(close["source"]["event_at"])
        ]
        observed = {
            "planned_workstreams": len(
                {r["source"]["record"] for r in prior if r["document"].get("status") == "SCHEDULED"}
            ),
            "completed_workstreams": len(
                {
                    r["source"]["record"]
                    for r in prior
                    if r["document"].get("status") == "COMPLETED_SCOPED_INTERNAL_EVALUATION"
                }
            ),
        }
        for name, count in observed.items():
            if type(body.get(name)) is not int or body[name] != count:
                errors.append(
                    {
                        "close": custody(close),
                        "reason": "RECORDED_COUNT_DIFFERS",
                        "field": name,
                        "recomputed": count,
                        "recorded": body.get(name),
                    }
                )
        if body.get("period", {}).get("end") and _time(close["source"]["event_at"]) < _time(
            body["period"]["end"]
        ):
            missing.append(
                {"close": custody(close), "reason": "RECONCILIATION_PRECEDES_DECLARED_PERIOD_END"}
            )
        evidence.append(
            {
                "close": custody(close),
                "recomputed_selected_roster": observed,
                "observed_originals": [custody(r) for r in prior],
            }
        )
    return _check(
        "DATED_EVALUATION_SCHEDULE_COMPLETION_AND_SELECTED_ROSTER",
        evidence,
        exceptions=errors,
        unperformed=[
            *missing,
            "Annual programme approval, live access, operating-role independence, reviewer "
            "credentials, direct committee delivery and independent closure tests require "
            "separate originals.",
        ],
    )


def _population(history):
    evidence, errors, missing = [], [], []
    family_names = {
        "bcm": "BCM",
        "assurance": "ISSUE",
        "ass001002": "MONITOR",
        "transition": "TRANSITION",
    }
    for row in history.selected("assuranceops", "assurance_population"):
        body = row["document"]
        events, event_limits = history.targets(row, "source_period_event_refs")
        antecedents, antecedent_limits = history.targets(row, "antecedent_context_refs")
        missing.extend(event_limits + antecedent_limits)
        period = body.get("period", {})
        require(
            set(("start", "end")) <= period.keys()
            and _time(period["start"]) <= _time(period["end"]),
            "Explicit selected population period required",
        )
        for target in events:
            if (
                not _time(period["start"])
                <= _time(target["source"]["event_at"])
                <= _time(period["end"])
            ):
                errors.append(
                    {
                        "population": custody(row),
                        "reason": "PERIOD_EVENT_OUTSIDE_PERIOD",
                        "target": custody(target),
                    }
                )
        for target in antecedents:
            if _time(target["source"]["event_at"]) >= _time(period["start"]):
                errors.append(
                    {
                        "population": custody(row),
                        "reason": "ANTECEDENT_IS_PERIOD_EVENT",
                        "target": custody(target),
                    }
                )
        ids = [_key(r["source"]) for r in events + antecedents]
        if len(set(ids)) != len(ids):
            errors.append(
                {
                    "population": custody(row),
                    "reason": "DUPLICATE_OR_OVERLAPPING_DECLARED_POPULATION",
                }
            )
        counts = Counter(
            family_names.get(r["logical_family"], r["logical_family"])
            for r in {_key(t["source"]): t for t in events + antecedents}.values()
        )
        reported = body.get("source_version_counts", {})
        require(isinstance(reported, dict), "Typed population count map required")
        for family, count in reported.items():
            if type(count) is not int or count < 0 or count != counts[family]:
                errors.append(
                    {
                        "population": custody(row),
                        "reason": "DECLARED_COHORT_COUNT_DIFFERS_OR_ORIGINAL_MISSING",
                        "family": family,
                        "recorded": count,
                        "collected": counts[family],
                    }
                )
        if not isinstance(body.get("source_queries"), dict) or not body["source_queries"]:
            missing.append({"population": custody(row), "reason": "SOURCE_QUERY_DEFINITION_ABSENT"})
        if body.get("collection_as_of") and _time(body["collection_as_of"]) < _time(period["end"]):
            missing.append(
                {
                    "population": custody(row),
                    "reason": "FROZEN_QUERY_DOES_NOT_COVER_REMAINING_PERIOD",
                }
            )
        selections = {}
        for field, role in (
            ("selected_technical_versions", {"bcm.exercise_result"}),
            (
                "selected_nontechnical_versions",
                {"ass001002.owner_self_assessment", "ass001002.second_line_observation"},
            ),
        ):
            targets, limitations = history.targets(row, field, role=role)
            selections[field] = [custody(t) for t in targets]
            missing.extend(limitations)
            for target in targets:
                if _key(target["source"]) not in set(ids):
                    errors.append(
                        {
                            "population": custody(row),
                            "reason": "SELECTION_OUTSIDE_DECLARED_COLLECTED_POPULATION",
                            "target": custody(target),
                        }
                    )
        evidence.append(
            {
                "population": custody(row),
                "recomputed_collected_cohort_counts": dict(counts),
                "selections": selections,
                "stored_query_executed": False,
            }
        )
    for wp in history.selected("assuranceops", "assurance_workpaper"):
        dependencies, limits = history.targets(wp, "dependencies")
        missing.extend(limits)
        populations = [
            r for r in dependencies if r["source"]["system"] == "assuranceops.assurance_population"
        ]
        originals, limits = history.targets(wp, "upstream_originals")
        missing.extend(limits)
        reviews = []
        for review in history.selected("assuranceops", "assurance_review"):
            targets, _ = history.targets(
                review,
                "dependencies",
                role={"assuranceops.assurance_workpaper", "assuranceops.assurance_independence"},
            )
            if any(_key(t["source"]) == _key(wp["source"]) for t in targets):
                reviews.append(review)
        evidence.append(
            {
                "company_workpaper": custody(wp),
                "prior_population": [custody(r) for r in populations],
                "underlying_originals": [custody(r) for r in originals],
                "reviews_of_exact_version": [custody(r) for r in reviews],
                "company_workpaper_is_auditor_reperformance": False,
            }
        )
        if not populations or not reviews:
            missing.append(
                {
                    "company_workpaper": custody(wp),
                    "reason": "EXACT_PRIOR_POPULATION_OR_VERSION_REVIEW_NOT_COLLECTED",
                }
            )
    return _check(
        "SOURCE_POPULATION_PERIOD_SELECTION_AND_EXACT_WORKPAPER_REVIEW",
        evidence,
        exceptions=errors,
        unperformed=[
            *missing,
            "Company workpaper conclusions, query-text existence and selected counts do not "
            "execute "
            "the auditor's technical/nontechnical attribute tests or establish an enterprise "
            "denominator.",
        ],
    )


def _issues(history):
    evidence, errors, missing = [], [], []
    for finding in history.selected("assurance", "issue_finding"):
        key, body = finding["source"]["record"], finding["document"]
        for field in (
            "severity",
            "severity_basis",
            "technical_action_owner_person_id",
            "plan_response_due_at",
            "closure_criteria",
        ):
            if not isinstance(body.get(field), str) or not body[field]:
                missing.append(
                    {"finding": custody(finding), "reason": "FINDING_FIELD_ABSENT", "field": field}
                )
        history_rows = sorted(
            [
                r
                for r in history.rows
                if r["logical_family"] == "assurance" and r["source"]["record"] == key
            ],
            key=lambda r: (_time(r["source"]["event_at"]), r["source"]["version"]),
        )
        for row in history_rows:
            b = row["document"]
            prior_digest = b.get("prior_issue_event_sha256")
            if prior_digest:
                prior = [
                    r
                    for r in history_rows
                    if r["source"]["sha256"] == prior_digest
                    and _time(r["source"]["available_at"]) <= _time(row["source"]["event_at"])
                ]
                if len(prior) != 1:
                    missing.append(
                        {"event": custody(row), "reason": "EXACT_PRIOR_ISSUE_EVENT_NOT_COLLECTED"}
                    )
            if b.get("finding_closed") is True:
                missing.append(
                    {
                        "event": custody(row),
                        "reason": "INDEPENDENT_RETEST_AND_CLOSURE_APPROVAL_ORIGINALS_REQUIRED",
                    }
                )
            if row["logical_system"] == "overdue_escalation" and b.get("plan_response_due_at"):
                if _time(row["source"]["event_at"]) <= _time(b["plan_response_due_at"]):
                    errors.append(
                        {"event": custody(row), "reason": "OVERDUE_ESCALATION_PRECEDES_DUE_DATE"}
                    )
                if b.get("governance_delivery_status") != "ACKNOWLEDGED":
                    missing.append(
                        {
                            "event": custody(row),
                            "reason": "GOVERNANCE_ROUTING_IS_NOT_DELIVERY_OR_DECISION",
                        }
                    )
        evidence.append(
            {
                "finding": custody(finding),
                "retained_history": [custody(r) for r in history_rows],
                "notification_originals": [
                    custody(r) for r in history_rows if r["logical_system"] == "owner_notification"
                ],
                "remediation_request_originals": [
                    custody(r) for r in history_rows if r["logical_system"] == "remediation_request"
                ],
                "actual_open_finding": body.get("finding_closed") is False,
                "technical_correction_is_closure": False,
            }
        )
    return _check(
        "SEVERITY_OWNER_DUE_NOTIFICATION_REMEDIATION_AND_HISTORICAL_ISSUE_CHAIN",
        evidence,
        exceptions=errors,
        unperformed=[
            *missing,
            "Approved corrective plan, independently executed retest, durable prevention, "
            "authorized risk acceptance and governance decision require their own dated originals; "
            "later technical correction never erases the finding.",
        ],
    )


def examine(records, *, as_of):
    """Five distinct selected assurance examinations; no automatic task credit."""
    history = CollectedHistory(records, as_of)
    return {
        "schema": "SH_COLLECTED_ASSURANCE_EXAMINATION_V1",
        "as_of": _time(as_of),
        "checks": {
            "SH-ASS-001": _owner_assessments(history),
            "SH-ASS-002": _second_line(history),
            "SH-ASS-003": _programme(history),
            "SH-ASS-004": _population(history),
            "SH-ASS-005": _issues(history),
        },
        "native_reference_joins": history.joins,
        "collected_original_count": len(history.rows),
        "enterprise_population_established": False,
        "professional_assurance_concluded": False,
        "company_workpapers_are_auditor_results": False,
        "full_period_toe_completed": False,
        "task_credit": False,
    }
