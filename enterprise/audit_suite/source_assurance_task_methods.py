"""Twenty-three distinct assurance-task examinations of collected originals.

Management and internal assurance records remain company evidence. This pure
callback neither substitutes their verdicts for audit tests nor reads a Key,
company database, cached examination, external page or executable stored query.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from .company_store import _time
from .fresh_sec003_procedure import CLOCK_ID, NATIVE_ID, require
from .source_assurance_methods import FAMILIES as CORE_FAMILIES
from .source_assurance_methods import examine as examine_core

BUSINESS_ID = tuple(k for k in CLOCK_ID if k != "imported_at")
FAMILIES = CORE_FAMILIES | {
    "critical_role",
    "ppl002",
    "person-access-history",
    "training-history",
    "change-history",
    "incident-history",
    "prdconcern",
}
PLAN_SHA = "1636c84a4b9ed09de74d72f1aec2505e34b5da5d16537fcc02d73a7cbacff4aa"
ROLES = {
    "SH-ASS-001": ("ass001002.monitoring_scope", "ass001002.owner_self_assessment"),
    "SH-ASS-002": ("ass001002.monitoring_scope", "ass001002.second_line_observation"),
    "SH-ASS-003": (
        "assuranceops.assurance_programme",
        "assuranceops.assurance_scope",
        "assuranceops.assurance_independence",
        "assuranceops.assurance_access",
        "assuranceops.assurance_report",
        "assuranceops.assurance_committee_route",
        "assuranceops.assurance_followup",
    ),
    "SH-ASS-004": (
        "assuranceops.assurance_population",
        "assuranceops.assurance_workpaper",
        "assuranceops.assurance_review",
    ),
    "SH-ASS-005": (
        "assurance.issue_finding",
        "assurance.owner_notification",
        "assurance.remediation_request",
        "assurance.overdue_escalation",
        "assurance.remediation_plan",
        "assurance.independent_retest",
        "assurance.closure_approval",
    ),
}
DESIGN_FIELDS = {
    "SH-ASS-001": ("criteria", "quarter", "selected_control", "selected_service"),
    "SH-ASS-002": ("criteria", "trigger", "selected_control", "selected_service"),
    "SH-ASS-003": ("criteria", "scope_services", "scope_sites", "excluded"),
    "SH-ASS-004": ("period", "source_queries", "source_period_event_refs"),
    "SH-ASS-005": (
        "severity_basis",
        "technical_action_owner_person_id",
        "plan_response_due_at",
        "closure_criteria",
    ),
}


def task_plan():
    path = Path(__file__).with_name("assurance_collected_task_plan_v1.json")
    raw = path.read_bytes()
    require(
        hashlib.sha256(raw).hexdigest() == PLAN_SHA, "Exact authored assurance task plan required"
    )
    plan = json.loads(raw)
    require(
        plan["task_count"] == len(plan["tasks"]) == 23, "Exact twenty-three task vector required"
    )
    return plan["tasks"]


def contracts():
    return {
        task["task_id"]: {
            "performed": "Collected-byte examination of "
            + task["task_id"]
            + ": "
            + task["authored_instruction"]
            + " Selected facets and their actual outcomes are recorded separately.",
            "unperformed": task["task_kind_rule"]
            + " Outstanding source-level applicability/design acceptance, "
            "enterprise denominator, independent technical/operating reperformance, "
            "competence, authority, full-period continuity and qualified assurance "
            "remain explicit below; no shared-evidence credit.",
            "allowed_dispositions": [{"status": "IN_PROGRESS", "conclusion": "LIMITATION"}],
        }
        for task in task_plan()
    }


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
                "Exact declared native assurance/context role required",
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


def _cited(history, facts, fallback):
    found = []
    for _, ref in _references(facts):
        row = history.index.get(_key(ref))
        if row and ref.get("sha256") == row["source"]["sha256"]:
            found.append(row)
    return found or fallback


def _design(history, task, selected, fallback):
    required = DESIGN_FIELDS[task["control_id"]]
    observations = []
    for row in selected:
        present = {key: row["document"][key] for key in required if key in row["document"]}
        absent = [
            key for key in required if key not in present or present[key] in (None, "", [], {})
        ]
        observations.append(
            _observation(
                "design-" + hashlib.sha256(str(_key(row["source"])).encode()).hexdigest()[:16],
                {
                    "native_role": row["source"]["system"],
                    "recorded_design_fields": present,
                    "attributes_not_established_by_this_original": absent,
                    "recorded_scope_or_authority_limits": {
                        k: row["document"][k]
                        for k in [
                            "scope_limit",
                            "contact_authority",
                            "status",
                            "excluded",
                            "exclusion_reason",
                            "competence_basis",
                        ]
                        if k in row["document"]
                    },
                    "design_sufficiency_accepted": False,
                },
                [row],
                status="SUPPORT_UNAVAILABLE" if absent else "OBSERVED",
            )
        )
    return observations or [
        _observation(
            "design-originals-absent",
            {
                "required_native_roles": list(ROLES[task["control_id"]]),
                "required_design_fields": list(required),
                "absence_is_not_nonoccurrence": True,
            },
            fallback,
            status="SUPPORT_UNAVAILABLE",
        )
    ]


def _occurrences(history, task, selected, fallback):
    observed = []
    for row in selected:
        joins = []
        cited = [row]
        for path, ref in _references(row["document"]):
            target, status = history.resolve(row, ref)
            if target:
                cited.append(target)
            joins.append({"path": path, "native_reference": ref, "status": status})
        observed.append(
            _observation(
                "occurrence-" + hashlib.sha256(str(_key(row["source"])).encode()).hexdigest()[:16],
                {
                    "source": {k: row["source"][k] for k in CLOCK_ID},
                    "native_role": row["source"]["system"],
                    "prior_original_joins": joins,
                    "recorded_actor": row["document"].get("actor_person_id"),
                    "recorded_action": row["document"].get("action"),
                    "recorded_status": row["document"].get("status"),
                    "company_result_is_auditor_operating_reperformance": False,
                },
                cited,
                status="SUPPORT_UNAVAILABLE"
                if not joins or any(j["status"] != "EXACT_AVAILABLE_ORIGINAL" for j in joins)
                else "OBSERVED",
            )
        )
    return observed or [
        _observation(
            "dated-occurrences-not-collected",
            {
                "required_native_roles": list(ROLES[task["control_id"]]),
                "authored_procedure": task["authored_procedure"],
                "actual_execution_not_inferred": True,
            },
            fallback,
            status="SUPPORT_UNAVAILABLE",
        )
    ]


def _quarter(stamp):
    at = datetime.fromisoformat(_time(stamp))
    return f"{at.year}-Q{(at.month - 1) // 3 + 1}"


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
                        "aggregate_requires_all_citation_partitions": True,
                    },
                }
            )
    return result


def _period(history, task, selected, fallback):
    counts = Counter(r["source"]["system"] for r in selected)
    quarters = sorted({_quarter(r["source"]["event_at"]) for r in selected})
    expected = (
        ["2027-Q1", "2027-Q2", "2027-Q3", "2027-Q4"]
        if task["control_id"] in {"SH-ASS-001", "SH-ASS-002"}
        else []
    )
    return [
        _observation(
            "selected-period-denominator",
            {
                "recomputed_selected_native_versions": len(selected),
                "recomputed_distinct_native_records": len(
                    {tuple(r["source"][k] for k in NATIVE_ID[:-1]) for r in selected}
                ),
                "native_role_counts": dict(counts),
                "actual_source_event_quarters": quarters,
                "quarterly_calendar_due_intervals": expected,
                "calendar_intervals_without_selected_occurrences": sorted(
                    set(expected) - set(quarters)
                ),
                "calendar_absence_proves_operating_failure": False,
                "full_owner_site_or_control_roster_collected": False,
                "full_year_audit_period": ["2027-01-01", "2027-12-31"],
                "full_period_continuity_established": False,
            },
            selected or fallback,
            status="SUPPORT_UNAVAILABLE",
        )
    ]


def _objectivity(history, fallback):
    rows = history.selected(
        {"assuranceops.assurance_independence", "assuranceops.assurance_review"}
    )
    observations = []
    for row in rows:
        body = row["document"]
        preparer, reviewer = (
            body.get("preparer_id"),
            body.get("reviewer_id", body.get("quality_reviewer_id")),
        )
        known = all(isinstance(x, str) and x for x in [preparer, reviewer])
        self_review = known and preparer == reviewer
        ownership = any(
            body.get(k) is True
            for k in [
                "reviewer_prepared_tests",
                "preparer_operating_control_ownership",
                "reviewer_operating_control_ownership",
            ]
        )
        observations.append(
            _observation(
                "objectivity-" + hashlib.sha256(str(_key(row["source"])).encode()).hexdigest()[:16],
                {
                    "preparer": preparer,
                    "reviewer": reviewer,
                    "identities_present": known,
                    "same_preparer_and_reviewer": self_review,
                    "recorded_operating_or_preparation_conflict": ownership,
                    "declared_conflicts": body.get("conflicts_declared"),
                    "excluded_evaluators": body.get("excluded_evaluators"),
                    "actual_credentials_verified_by_auditor": False,
                    "synthetic_token_is_real_credential": False,
                },
                [row],
                status="EXCEPTION_RECORDED"
                if self_review or ownership
                else ("OBSERVED" if known else "SUPPORT_UNAVAILABLE"),
            )
        )
    return observations or [
        _observation(
            "objectivity-originals-absent",
            {"operating_ownership_and_independent_evaluation_not_inferred": True},
            fallback,
            status="SUPPORT_UNAVAILABLE",
        )
    ]


def _accountability(history, fallback):
    observations = []
    for row in history.selected({"ass001002.owner_self_assessment"}):
        body = row["document"]
        facets = {}
        cited = [row]
        for field, roles in {
            "competence_refs": {
                "critical_role.competence_record",
                "ppl002.screening_result",
                "training-history.completion",
            },
            "backup_refs": {"critical_role.backup_assignment"},
            "accountability_refs": {
                "critical_role.accountability_action",
                "assurance.management_response",
            },
        }.items():
            refs = body.get(field, [])
            require(isinstance(refs, list), "Explicit accountability reference vector required")
            facets[field] = []
            for ref in refs:
                target, status = history.resolve(row, ref, roles)
                if target:
                    cited.append(target)
                facets[field].append({"reference": ref, "status": status})
        observations.append(
            _observation(
                "accountability-"
                + hashlib.sha256(str(_key(row["source"])).encode()).hexdigest()[:16],
                {
                    "management_statement": body.get("statement"),
                    "actual_declared_competence_backup_and_action_joins": facets,
                    "fields_with_no_collected_basis": [k for k, v in facets.items() if not v],
                    "local_subject_names_are_authoritative_identity_join": False,
                    "workload_training_response_and_recurring_failures_not_inferred": True,
                },
                cited,
                status="SUPPORT_UNAVAILABLE",
            )
        )
    return observations or [
        _observation(
            "accountability-occurrences-absent",
            {"critical_duties_competence_backups_and_responses_require_originals": True},
            fallback,
            status="SUPPORT_UNAVAILABLE",
        )
    ]


def _description(history, fallback):
    observations = []
    for row in history.selected({"assuranceops.assurance_description"}):
        assertions = row["document"].get("assertions", [])
        require(isinstance(assertions, list), "Description assertion vector required")
        for number, assertion in enumerate(assertions):
            require(
                isinstance(assertion, dict) and isinstance(assertion.get("sources"), list),
                "Description assertion sources required",
            )
            facts, cited = [], [row]
            for ref in assertion["sources"]:
                target, status = history.resolve(row, ref)
                if target:
                    cited.append(target)
                facts.append({"native_reference": ref, "status": status})
            observations.append(
                _observation(
                    "description-"
                    + hashlib.sha256(str(_key(row["source"])).encode()).hexdigest()[:12]
                    + "-"
                    + str(number),
                    {
                        "assertion_id": assertion.get("assertion_id"),
                        "recorded_statement": assertion.get("statement"),
                        "independent_exact_original_joins": facts,
                        "source_citation_establishes_assertion_truth": False,
                        "scope_and_disclosure_semantics_require_separate_acceptance": True,
                    },
                    cited,
                    status="SUPPORT_UNAVAILABLE"
                    if not facts or any(x["status"] != "EXACT_AVAILABLE_ORIGINAL" for x in facts)
                    else "OBSERVED",
                )
            )
        prior = [
            r
            for r in history.selected(
                {
                    "incident-history.incident",
                    "change-history.change",
                    "transition.provider_contract",
                    "assurance.issue_finding",
                }
            )
            if _time(r["source"]["available_at"]) <= _time(row["source"]["event_at"])
        ]
        cited_keys = {_key(ref) for _, ref in _references(assertions)}
        omitted = [r for r in prior if _key(r["source"]) not in cited_keys]
        observations.append(
            _observation(
                "disclosure-population-"
                + hashlib.sha256(str(_key(row["source"])).encode()).hexdigest()[:12],
                {
                    "actual_prior_selected_incident_change_provider_issue_versions": len(prior),
                    "selected_prior_versions_not_cited": [
                        {k: r["source"][k] for k in CLOCK_ID} for r in omitted
                    ],
                    "uncited_means_material_disclosure_omission": False,
                    "materiality_and_description_boundary_not_accepted": True,
                    "declared_customer_release_status": row["document"].get(
                        "customer_release_status"
                    ),
                },
                [row, *prior],
                status="SUPPORT_UNAVAILABLE",
            )
        )
    return observations or [
        _observation(
            "description-originals-absent",
            {"description_assertions_and_comparison_population_not_collected": True},
            fallback,
            status="SUPPORT_UNAVAILABLE",
        )
    ]


def examine(records, *, as_of, scratch_root=None):
    """Emit exact per-task facets for the separately reviewed ordinary writer."""
    del scratch_root
    history = History(records, as_of)
    fallback = history.rows[:1]
    core_rows = [
        r
        for r in history.rows
        if r["logical_family"] in CORE_FAMILIES and isinstance(r["document"], dict)
    ]
    core = examine_core(core_rows, as_of=as_of) if core_rows else {"checks": {}}
    contract = contracts()
    inspections = []
    for task in task_plan():
        selected = history.selected(set(ROLES[task["control_id"]]))
        base = core["checks"].get(
            task["control_id"],
            {
                "evidence": [],
                "exceptions": [],
                "unperformed": ["Required assurance originals absent"],
            },
        )
        observations = []
        for category, status in [
            ("evidence", "OBSERVED"),
            ("exceptions", "EXCEPTION_RECORDED"),
            ("unperformed", "SUPPORT_UNAVAILABLE"),
        ]:
            for number, facts in enumerate(base.get(category, [])):
                observations.append(
                    _observation(
                        "bounded-" + category + "-" + str(number),
                        {
                            "attribute": base.get("attribute"),
                            "actual_source_check": facts,
                            "company_workpaper_is_auditor_test_result": False,
                        },
                        _cited(history, facts, selected or fallback),
                        status=status,
                    )
                )
        if task["kind"] == "TOD":
            observations.extend(_design(history, task, selected, fallback))
        elif task["kind"] == "IMPLEMENTATION":
            observations.extend(_occurrences(history, task, selected, fallback))
        elif task["kind"] == "TOE":
            observations.extend(_period(history, task, selected, fallback))
            observations.extend(_occurrences(history, task, selected, fallback))
        if task["clause_group"] == "ACTION-S-ACCOUNTABILITY":
            observations.extend(_accountability(history, fallback))
        elif task["clause_group"] == "ACTION-S-DESCRIPTION":
            observations.extend(_description(history, fallback))
        elif task["clause_group"] in {"CHECK-SOC2:CC4.1", "ACTION-H-EVALUATION"}:
            observations.extend(_objectivity(history, fallback))
            observations.extend(_period(history, task, selected, fallback))
            observations.append(
                _observation(
                    "evaluation-technical-nontechnical-and-change-boundary",
                    {
                        "authored_additional_instruction": task["authored_instruction"],
                        "actual_selected_technical_originals": len(
                            history.selected({"bcm.exercise_result", "bcm.exercise_review"})
                        ),
                        "actual_selected_nontechnical_originals": len(
                            history.selected(
                                {
                                    "ass001002.owner_self_assessment",
                                    "assurance.issue_finding",
                                    "assurance.issue_screening",
                                }
                            )
                        ),
                        "actual_selected_change_originals": len(
                            history.selected({"change-history.change"})
                        ),
                        "configuration_and_change_effectiveness_proved_by_counts": False,
                    },
                    selected or fallback,
                    status="SUPPORT_UNAVAILABLE",
                )
            )
        elif task["clause_group"] == "CHECK-SOC2:CC4.2":
            observations.extend(_occurrences(history, task, selected, fallback))
            observations.append(
                _observation(
                    "deficiency-closure-not-ticket-closure",
                    {
                        "actual_selected_independent_retest_versions": len(
                            history.selected({"assurance.independent_retest"})
                        ),
                        "actual_selected_closure_authority_versions": len(
                            history.selected({"assurance.closure_approval"})
                        ),
                        "technical_correction_or_closed_flag_is_independent_closure": False,
                    },
                    selected or fallback,
                    status="SUPPORT_UNAVAILABLE",
                )
            )
        observations = _partition_citations(observations)
        ids = list(dict.fromkeys(e["artifact_id"] for o in observations for e in o["evidence"]))
        require(ids and observations, "Actual task-specific originals and observations required")
        inspections.append(
            {
                "task_id": task["task_id"],
                "artifact_ids": ids,
                "observations": observations,
                "performed": contract[task["task_id"]]["performed"],
                "unperformed": contract[task["task_id"]]["unperformed"],
                "result": json.dumps(
                    {
                        "actual_observations": len(observations),
                        "observed_exceptions": sum(
                            o["status"] == "EXCEPTION_RECORDED" for o in observations
                        ),
                        "unsupported_attributes": sum(
                            o["status"] == "SUPPORT_UNAVAILABLE" for o in observations
                        ),
                        "authored_task_instruction": task["authored_instruction"],
                        "automatic_requirement_or_full_period_credit": False,
                    },
                    sort_keys=True,
                ),
                "disposition": {
                    "status": "IN_PROGRESS",
                    "conclusion": "LIMITATION",
                    "rationale": "Selected exact collected-original facets were examined. "
                    "The separately listed missing source, authority, population "
                    "and independent operating tests remain unresolved.",
                },
            }
        )
    return inspections
