"""Thirty-seven bounded B04 examinations of ordinary retained company bytes.

The reviewed caller proves actual Engine membership, clock and source gates.
No company database, stored query, original script or prior audit outcome is read.
Local data arithmetic, simulated operating statements and actual deployment are
separate attributes; these methods cannot issue professional assurance.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .collected_engineering_history import History, custody, detail, key
from .company_store import _json, _time
from .fresh_sec003_procedure import require

PLAN_SHA = "d7870db9704448a3ccb3aa6556d4376d57b55d356f1ecf9841e2e5c3c3b508a7"
BROAD = (
    "Full enterprise/year code, infrastructure, data-change and emergency populations; "
    "live protected branches, pipeline/device execution, deployment and representative "
    "rollback; qualified approval authority, accepted customer/AI commitments, legal "
    "notice duties, all support channels and actual external receipt remain unperformed."
)


def task_plan():
    raw = Path(__file__).with_name("engineering_product_collected_task_plan_v1.json").read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PLAN_SHA, "Exact 37-task B04 plan required")
    plan = json.loads(raw)
    require(plan["task_count"] == len(plan["tasks"]) == 37, "Exact B04 task census required")
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
                " Record executed bounded attributes, discrepancies and unavailable "
                "support separately."
            ),
            "unperformed": t["task_kind_rule"] + " " + BROAD,
            "allowed_dispositions": [
                {"status": "IN_PROGRESS", "conclusion": c} for c in ("LIMITATION", "FAIL")
            ],
        }
        for t in task_plan()
    }


def _ids(values):
    require(
        isinstance(values, list)
        and all(isinstance(v, str) and v for v in values)
        and len(set(values)) == len(values),
        "Distinct typed engineering identifier vector required",
    )
    return set(values)


def _retry(value):
    typed = isinstance(value, dict) and all(
        type(value.get(k)) is int and value[k] > 0
        for k in ("attempts", "timeout_ms", "max_total_ms")
    )
    return {
        "strict_positive_integer_configuration": typed,
        "calculated_total_timeout_ms": value["attempts"] * value["timeout_ms"] if typed else None,
        "within_local_limit": value["attempts"] * value["timeout_ms"] <= value["max_total_ms"]
        if typed
        else None,
        "actual_target_or_original_test_script_executed": False,
    }


def _effective(rows, at):
    chosen = {}
    for row in rows:
        if _time(row["source"]["available_at"]) > _time(at):
            continue
        identity = key(row["source"])[:-1]
        if (
            identity not in chosen
            or row["source"]["version"] > chosen[identity]["source"]["version"]
        ):
            chosen[identity] = row
    return list(chosen.values())


def _attributes(rows, fields):
    return [
        {"source": custody(r), "attributes": {k: detail(r)[k] for k in fields if k in detail(r)}}
        for r in rows
    ]


def _binding(history, origin, field, family, roles):
    d = detail(origin)
    ref = d.get(field)
    if isinstance(ref, dict):
        return history.resolve(origin, ref, expected={family + "." + role for role in roles})
    if isinstance(ref, str) and ref:
        full = d.get("source_refs", {}).get(ref)
        if isinstance(full, dict):
            return history.resolve(origin, full, expected={family + "." + role for role in roles})
        # The exact record is a documentary witness only; no version/digest
        # authority can be synthesized when its full source_refs entry is absent.
        return history.scalar(origin, record=ref, family=family, roles=roles)
    return None, "REQUIRED_EXACT_ORIGINAL_REFERENCE_ABSENT"


def _ancestors(history, origin, family, roles):
    return [
        r
        for r in history.ancestors(origin)
        if r["logical_family"] == family and r["logical_system"] in roles
    ]


def local_packages(history):
    packages, tests, peers, gates, releases, recovery, exceptions = [], [], [], [], [], [], []
    builds = history.select("change-history", {"builds"})
    for build in builds:
        d = detail(build)
        original, status = _binding(history, build, "source", "change-history", {"configurations"})
        package = d.get("package")
        calculation = _retry(package.get("configuration") if isinstance(package, dict) else None)
        fact = {
            "source": custody(build),
            "configuration_original_status": status,
            "configuration_original": custody(original) if original else None,
            "local_budget_reperformance": calculation,
            "canonical_embedded_package_sha256": hashlib.sha256(_json(package).encode()).hexdigest()
            if isinstance(package, dict)
            else None,
            "company_package_sha256": d.get("package_sha256"),
            "digest_basis": "RECONSTRUCTED_CANONICAL_JSON_NOT_COMPILATION_OR_ORIGINAL_BINARY",
            "package_configuration_equals_exact_original": _json(package.get("configuration"))
            == _json(detail(original).get("configuration"))
            if original and isinstance(package, dict)
            else None,
            "actual_binary_build_or_deployment_performed": False,
        }
        if (
            calculation["within_local_limit"] is False
            or fact["package_configuration_equals_exact_original"] is False
        ):
            exceptions.append({"facet": "PACKAGE", **fact})
        packages.append(fact)
    for row in history.select("change-history", {"tests"}):
        d = detail(row)
        build, status = _binding(history, row, "artifact", "change-history", {"builds"})
        calculation = _retry(
            detail(build).get("package", {}).get("configuration") if build else None
        )
        reported = d.get("tests", [])
        require(
            isinstance(reported, list) and all(isinstance(t, dict) for t in reported),
            "Typed reported local test vector required",
        )
        for test in reported:
            require(
                "passed" not in test or type(test["passed"]) is bool,
                "Strict local test result flag required",
            )
        fact = {
            "source": custody(row),
            "build_original_status": status,
            "build_original": custody(build) if build else None,
            "company_test_scope": d.get("test_scope"),
            "company_test_names": [t.get("name") for t in reported],
            "independently_reperformed_retry_budget": calculation,
            "company_reported_passed": d.get("passed"),
            "schema_pass_does_not_test_combined_budget": True,
            "original_source_tests_or_ci_jobs_executed": False,
        }
        if calculation["within_local_limit"] is False and d.get("passed") is True:
            exceptions.append({"facet": "TEST_SCOPE", **fact})
        tests.append(fact)
    for row in history.select("change-history", {"peer_reviews"}):
        d = detail(row)
        build, status = _binding(history, row, "artifact", "change-history", {"builds"})
        intents = [
            r
            for r in history.select("change-history", {"change_intents"})
            if isinstance(d.get("cycle_id"), str)
            and d["cycle_id"]
            and detail(r).get("cycle_id") == d["cycle_id"]
            and _time(r["source"]["available_at"]) <= _time(row["source"]["event_at"])
        ]
        author = detail(intents[0]).get("owner_id") if len(intents) == 1 else None
        reviewer = d.get("reviewer_id")
        fact = {
            "source": custody(row),
            "build_original_status": status,
            "build_original": custody(build) if build else None,
            "intent_original": custody(intents[0]) if len(intents) == 1 else None,
            "recorded_author_id": author,
            "recorded_reviewer_id": reviewer,
            "distinct_named_author_and_reviewer": author != reviewer
            if isinstance(author, str) and author and isinstance(reviewer, str) and reviewer
            else None,
            "recorded_decision": d.get("decision"),
            "protected_branch_configuration_collected": False,
            "qualified_reviewer_or_corporate_approval_accepted": False,
        }
        if fact["distinct_named_author_and_reviewer"] is False:
            exceptions.append({"facet": "PEER_INDEPENDENCE", **fact})
        peers.append(fact)
    for row in history.select("change-history", {"release_gate"}):
        d = detail(row)
        review, rstatus = _binding(history, row, "peer_review", "change-history", {"peer_reviews"})
        build, bstatus = _binding(history, row, "artifact", "change-history", {"builds"})
        tested, tstatus = _binding(history, row, "tests", "change-history", {"tests"})
        review_build, _ = (
            _binding(history, review, "artifact", "change-history", {"builds"})
            if review
            else (None, "ABSENT")
        )
        test_build, _ = (
            _binding(history, tested, "artifact", "change-history", {"builds"})
            if tested
            else (None, "ABSENT")
        )
        tested_same = (
            key(test_build["source"]) == key(build["source"]) if test_build and build else None
        )
        test_results = detail(tested).get("tests", []) if tested else []
        documented_test_pass = (
            tested is not None
            and detail(tested).get("passed") is True
            and bool(test_results)
            and all(t.get("passed") is True for t in test_results)
        )
        same = (
            key(review_build["source"]) == key(build["source"]) if review_build and build else None
        )
        calculation = _retry(
            detail(build).get("package", {}).get("configuration") if build else None
        )
        approved = (
            review is not None and detail(review).get("decision") == "APPROVED" and same is True
        )
        independent = (
            next(
                (
                    p["distinct_named_author_and_reviewer"]
                    for p in peers
                    if key(p["source"]) == key(review["source"])
                ),
                None,
            )
            if review
            else None
        )
        package_fact = next(
            (p for p in packages if build and key(p["source"]) == key(build["source"])), None
        )
        exact_package_support = (
            package_fact is not None
            and package_fact["configuration_original_status"] == "EXACT_AVAILABLE_ORIGINAL"
            and package_fact["package_configuration_equals_exact_original"] is True
        )
        could_release = (
            approved
            and exact_package_support
            and independent is True
            and tested_same is True
            and documented_test_pass
            and history.action_supported(row)
            and history.action_supported(review)
            and history.action_supported(tested)
            and calculation["within_local_limit"] is True
        )
        fact = {
            "source": custody(row),
            "review_status": rstatus,
            "build_status": bstatus,
            "test_original_status": tstatus,
            "exact_review_original": custody(review) if review else None,
            "exact_build_original": custody(build) if build else None,
            "exact_test_original": custody(tested) if tested else None,
            "review_covers_exact_selected_build": same,
            "tests_cover_exact_selected_build": tested_same,
            "package_configuration_original_supported": exact_package_support,
            "documented_tests_all_pass": documented_test_pass,
            "named_peer_independence": independent,
            "independent_local_release_prerequisites": could_release,
            "company_gate_decision": d.get("decision"),
            "qualified_corporate_release_authority_accepted": False,
        }
        if d.get("decision") in {"APPROVED", "RELEASE_ALLOWED", "ALLOWED"} and not could_release:
            exceptions.append({"facet": "RELEASE_GATE", **fact})
        gates.append(fact)
    for row in history.select("change-history", {"local_releases"}):
        d = detail(row)
        gate, gstatus = _binding(history, row, "gate", "change-history", {"release_gate"})
        build, bstatus = _binding(history, row, "artifact", "change-history", {"builds"})
        gate_test = next(
            (g for g in gates if gate and key(g["source"]) == key(gate["source"])), None
        )
        gate_build, _ = (
            _binding(history, gate, "artifact", "change-history", {"builds"})
            if gate
            else (None, "ABSENT")
        )
        exact = key(gate_build["source"]) == key(build["source"]) if gate_build and build else None
        fact = {
            "source": custody(row),
            "gate_original_status": gstatus,
            "build_original_status": bstatus,
            "gate_original": custody(gate) if gate else None,
            "build_original": custody(build) if build else None,
            "gate_covers_exact_released_build": exact,
            "gate_recorded_permission": detail(gate).get("decision") if gate else None,
            "gate_recorded_release_allowed": detail(gate).get("decision")
            in {"APPROVED", "RELEASE_ALLOWED", "ALLOWED"}
            if gate
            else None,
            "gate_prerequisites_supported": gate_test["independent_local_release_prerequisites"]
            if gate_test
            else None,
            "reported_active_configuration_sha256": d.get("active_configuration_sha256"),
            "release_identity": d.get("actor_id"),
            "actual_external_deployment": False,
        }
        if gate_test and (
            not fact["gate_prerequisites_supported"]
            or exact is False
            or fact["gate_recorded_release_allowed"] is False
        ):
            exceptions.append({"facet": "RELEASE_AFTER_UNSUPPORTED_GATE", **fact})
        releases.append(fact)
    for row in history.select("change-history", {"recovery"}):
        baseline, status = _binding(
            history, row, "restore_source", "change-history", {"configurations"}
        )
        recovery.append(
            {
                "source": custody(row),
                "restore_original_status": status,
                "restore_original": custody(baseline) if baseline else None,
                "recomputed_baseline_configuration_budget": _retry(
                    detail(baseline).get("configuration") if baseline else None
                ),
                "company_method": detail(row).get("method"),
                "actual_restore_or_representative_rehearsal_performed": False,
            }
        )
    exports = []
    for row in history.select("configuration-runtime-history", {"configuration_export"}):
        md = row["source"]["provenance"].get("operational_metadata", {})
        ref = md.get("source_references", {}).get("release")
        released, status = (
            history.resolve(row, ref, expected={"change-history.local_releases"})
            if isinstance(ref, dict)
            else (None, "EXACT_RELEASE_REFERENCE_ABSENT")
        )
        exports.append(
            {
                "source": custody(row),
                "release_original_status": status,
                "release_original": custody(released) if released else None,
                "export_bytes_equal_released_declared_digest": row["source"]["sha256"]
                == detail(released).get("active_configuration_sha256")
                if released
                else None,
                "raw_export_retry_reperformance": _retry(row["document"]),
                "actual_deployed_target_or_out_of_band_population_covered": False,
            }
        )
    differences = []
    for row in history.select("change-history", {"change_intents"}):
        baseline, bs = _binding(history, row, "baseline", "change-history", {"configurations"})
        candidate, cs = _binding(history, row, "candidate", "change-history", {"configurations"})
        before = detail(baseline).get("configuration") if baseline else None
        after = detail(candidate).get("configuration") if candidate else None
        differences.append(
            {
                "source": custody(row),
                "baseline_original_status": bs,
                "candidate_original_status": cs,
                "baseline_original": custody(baseline) if baseline else None,
                "candidate_original": custody(candidate) if candidate else None,
                "changed_configuration_fields": [
                    {
                        "field": name,
                        "before_present": name in before,
                        "after_present": name in after,
                        "before": before.get(name),
                        "after": after.get(name),
                    }
                    for name in sorted(set(before) | set(after))
                    if (name in before) != (name in after)
                    or _json(before.get(name)) != _json(after.get(name))
                ]
                if isinstance(before, dict) and isinstance(after, dict)
                else None,
                "actual_code_diff_or_protected_branch_execution": False,
            }
        )
    return {
        "configuration_differences": differences,
        "intent_and_requirements": _attributes(
            history.select("change-history", {"change_intents"}),
            [
                "owner_id",
                "requirement",
                "change_type",
                "emergency",
                "local_requirement_basis",
                "cycle_id",
                "period_start",
                "period_end_exclusive",
            ],
        ),
        "packages": packages,
        "tests": tests,
        "peer_reviews": peers,
        "release_gates": gates,
        "local_releases": releases,
        "rollback_sources": recovery,
        "raw_configuration_exports": exports,
        "observed_failure_versions": _attributes(
            history.select("change-history", {"observations"}),
            ["observed_local_calculation", "request"],
        ),
        "exceptions": exceptions,
        "complete_change_population_established": False,
    }


def operating_changes(history):
    requests = history.select("eng005operating", {"change_request"})
    tests, approvals, releases, applications, verifications, recoveries, exceptions = (
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    )
    for row in history.select("eng005operating", {"change_test"}):
        d = detail(row)
        required, passed = _ids(d.get("required_tests", [])), _ids(d.get("passed_tests", []))
        results = d.get("test_results", {})
        require(
            isinstance(results, dict) and all(type(v) is bool for v in results.values()),
            "Strict selected change test results required",
        )
        request = _ancestors(history, row, "eng005operating", {"change_request"})
        candidate = detail(request[0]).get("candidate") if len(request) == 1 else None
        risk_inputs = _ancestors(history, row, "eng005operating", {"change_risk"})
        risk_declared = {v for r in risk_inputs for v in _ids(detail(r).get("test_plan", []))}
        mandatory = required | risk_declared
        fact = {
            "source": custody(row),
            "risk_test_design_originals": [custody(r) for r in risk_inputs],
            "required_tests": sorted(required),
            "independent_risk_required_tests": sorted(risk_declared),
            "mandatory_test_population_declared": bool(mandatory),
            "risk_required_tests_omitted": sorted(risk_declared - required),
            "reported_passed_tests": sorted(passed),
            "missing_mandatory_results": sorted(mandatory - {k for k, v in results.items() if v}),
            "claim_passes_without_result": sorted(passed - {k for k, v in results.items() if v}),
            "exact_request_original": custody(request[0]) if len(request) == 1 else None,
            "tested_value_equals_exact_request": _json(d.get("tested_candidate"))
            == _json(candidate)
            if len(request) == 1
            else None,
            "original_test_or_device_execution": False,
        }
        if (
            fact["missing_mandatory_results"]
            or fact["risk_required_tests_omitted"]
            or fact["claim_passes_without_result"]
            or fact["tested_value_equals_exact_request"] is False
        ):
            exceptions.append({"facet": "MANDATORY_TESTS", **fact})
        tests.append(fact)
    for row in history.select("eng005operating", {"change_approval"}):
        d = detail(row)
        request = _ancestors(history, row, "eng005operating", {"change_request"})
        actor = d.get("actor_id")
        named = detail(request[0]).get("actor_id") if len(request) == 1 else None
        approvals.append(
            {
                "source": custody(row),
                "exact_request_original": custody(request[0]) if len(request) == 1 else None,
                "decision": d.get("decision"),
                "named_approver_id": actor,
                "distinct_from_named_requester": actor != named if actor and named else None,
                "corporate_policy_or_qualified_approval_accepted": False,
            }
        )
    for row in history.select("eng005operating", {"change_release"}):
        approval, status = _binding(
            history, row, "security_decision_ref", "eng005operating", {"change_approval"}
        )
        ancestors = _ancestors(history, row, "eng005operating", {"change_test"})
        test_attrs = [
            t for t in tests if any(key(t["source"]) == key(r["source"]) for r in ancestors)
        ]
        accepted_test = bool(test_attrs) and all(
            t["mandatory_test_population_declared"]
            and not t["risk_required_tests_omitted"]
            and not t["missing_mandatory_results"]
            and not t["claim_passes_without_result"]
            and t["tested_value_equals_exact_request"] is True
            for t in test_attrs
        )
        approval_attr = next(
            (a for a in approvals if approval and key(a["source"]) == key(approval["source"])), None
        )
        request_pointer = approval_attr["exact_request_original"] if approval_attr else None
        same_request = (
            all(
                t["exact_request_original"] is not None
                and key(t["exact_request_original"]) == key(request_pointer)
                for t in test_attrs
            )
            if request_pointer is not None and test_attrs
            else None
        )
        request_original = history.index.get(key(request_pointer)) if request_pointer else None
        explicit_fields = [
            name for name in ("change_id", "configuration_key", "candidate") if name in detail(row)
        ]
        explicit_matches = (
            all(
                name in detail(request_original)
                and _json(detail(row)[name]) == _json(detail(request_original)[name])
                for name in explicit_fields
            )
            if request_original is not None
            else None
        )
        decision = detail(approval).get("decision") if approval else None
        local_approved = decision in {"APPROVE_SELECTED_LOCAL_CHANGE", "APPROVED"}
        fact = {
            "source": custody(row),
            "approval_original_status": status,
            "approval_original": custody(approval) if approval else None,
            "approval_decision": decision,
            "mandatory_test_attributes": test_attrs,
            "mandatory_test_support": accepted_test,
            "approval_request_original": request_pointer,
            "tests_and_approval_bind_exact_same_request": same_request,
            "explicit_release_request_fields_examined": explicit_fields,
            "explicit_release_request_fields_match_approved_request": explicit_matches,
            "distinct_recorded_requester_and_approver": approval_attr[
                "distinct_from_named_requester"
            ]
            if approval_attr
            else None,
            "local_release_supported": status == "EXACT_AVAILABLE_ORIGINAL"
            and local_approved
            and accepted_test
            and same_request is True
            and explicit_matches is True
            and approval_attr is not None
            and approval_attr["distinct_from_named_requester"] is True
            and history.action_supported(row)
            and history.action_supported(approval),
            "company_release_decision": detail(row).get("decision"),
            "actual_live_pipeline_release": False,
        }
        if (
            approval
            and not local_approved
            or test_attrs
            and not accepted_test
            or same_request is False
            or explicit_matches is False
            or approval_attr
            and approval_attr["distinct_from_named_requester"] is False
        ):
            exceptions.append({"facet": "OPERATING_RELEASE_GATE", **fact})
        releases.append(fact)
    for row in history.select("eng005operating", {"change_application"}):
        released, status = _binding(
            history, row, "release_ref", "eng005operating", {"change_release"}
        )
        request = _ancestors(history, row, "eng005operating", {"change_request"})
        expected = detail(request[0]).get("candidate") if len(request) == 1 else None
        fact = {
            "source": custody(row),
            "release_original_status": status,
            "release_original": custody(released) if released else None,
            "request_original": custody(request[0]) if len(request) == 1 else None,
            "recorded_applied_value": detail(row).get("applied_value"),
            "applied_value_equals_exact_requested_candidate": _json(
                detail(row).get("applied_value")
            )
            == _json(expected)
            if len(request) == 1
            else None,
            "actual_device_write_performed": False,
        }
        if fact["applied_value_equals_exact_requested_candidate"] is False:
            exceptions.append({"facet": "APPLIED_VALUE", **fact})
        applications.append(fact)
    for row in history.select("eng005operating", {"change_verification"}):
        d = detail(row)
        released, status = _binding(
            history, row, "approved_release_ref", "eng005operating", {"change_release"}
        )
        request = _ancestors(history, row, "eng005operating", {"change_request"})
        expected = detail(request[0]).get("candidate") if len(request) == 1 else None
        fact = {
            "source": custody(row),
            "approved_release_original_status": status,
            "request_original": custody(request[0]) if len(request) == 1 else None,
            "approved_value_equals_exact_request": (
                _json(d.get("approved_value")) == _json(expected) if len(request) == 1 else None
            ),
            "approved_release_original": custody(released) if released else None,
            "recorded_approved_value": d.get("approved_value"),
            "recorded_observed_value": d.get("observed_value"),
            "independent_recorded_values_match": _json(d["approved_value"])
            == _json(d["observed_value"])
            if "approved_value" in d and "observed_value" in d
            else None,
            "company_match_claim": d.get("local_match"),
            "actual_device_state_observed": False,
        }
        if (
            fact["independent_recorded_values_match"] is False
            or fact["approved_value_equals_exact_request"] is False
        ):
            exceptions.append({"facet": "POST_CHANGE_VERIFICATION", **fact})
        verifications.append(fact)
    for row in history.select("eng005operating", {"change_recovery"}):
        request = _ancestors(history, row, "eng005operating", {"change_request"})
        baseline = detail(request[0]).get("baseline") if len(request) == 1 else None
        recovery_fact = {
            "source": custody(row),
            "request_original": custody(request[0]) if len(request) == 1 else None,
            "rehearsed_value_equals_exact_baseline": _json(detail(row).get("rehearsed_baseline"))
            == _json(baseline)
            if len(request) == 1
            else None,
            "restored_active_value": detail(row).get("restored_active_value"),
            "real_recovery_or_representative_data_effects_executed": False,
        }
        if recovery_fact["rehearsed_value_equals_exact_baseline"] is False:
            exceptions.append({"facet": "RECOVERY_BASELINE", **recovery_fact})
        recoveries.append(recovery_fact)
    return {
        "declared_selected_request_population": _attributes(
            requests,
            [
                "change_id",
                "business_intent",
                "affected_data",
                "baseline",
                "candidate",
                "rollback",
                "service_id",
                "site",
                "selected_period",
                "action",
            ],
        ),
        "risk_and_test_design": _attributes(
            history.select("eng005operating", {"change_risk"}),
            ["test_plan", "rollback_reference", "full_service_population"],
        ),
        "tests": tests,
        "approvals": approvals,
        "releases": releases,
        "applications": applications,
        "verifications": verifications,
        "recoveries": recoveries,
        "review_versions": _attributes(
            history.select("eng005operating", {"change_review", "exception_register"}),
            [
                "actor_id",
                "status",
                "current_selected_value",
                "historical_exception_open",
                "closure_authority_evidenced",
            ],
        ),
        "exceptions": exceptions,
        "full_normal_emergency_change_denominator_established": False,
    }


def emergency(history):
    definitions = history.select("eng005", {"emergency_intake"})
    states, exceptions = [], []
    for row in history.select("eng005", {"local_change_state"}):
        d = detail(row)
        ancestors = history.ancestors(row)
        gates = [r for r in ancestors if r["source"]["system"] == "eng005.emergency_gate"]
        original = [
            r
            for r in definitions
            if isinstance(d.get("exercise_id"), str)
            and d["exercise_id"]
            and detail(r).get("exercise_id") == d["exercise_id"]
            and "baseline" in detail(r)
            and "candidate" in detail(r)
            and _time(r["source"]["available_at"]) <= _time(row["source"]["event_at"])
        ]
        definition = original[0] if len(original) == 1 else None
        applies = d.get("candidate_applied")
        require(
            applies is None or type(applies) is bool, "Strict emergency application flag required"
        )
        authority_unavailable = not gates or all(not detail(g).get("evidence") for g in gates)
        fact = {
            "source": custody(row),
            "definition_original": custody(definition) if definition else None,
            "gate_originals": [custody(g) for g in gates],
            "recorded_candidate_applied": applies,
            "recorded_active_sha256": d.get("active_sha256"),
            "matches_declared_baseline_digest": d.get("active_sha256")
            == detail(definition).get("baseline_sha256")
            if definition
            else None,
            "no_prior_evidenced_authority_original": authority_unavailable,
            "recorded_retrospective_is_qualified_approval": False,
            "actual_emergency_operation_or_company_authority_accepted": False,
        }
        if applies is True and authority_unavailable:
            exceptions.append(fact)
        states.append(fact)
    return {
        "reason_scope_and_local_gate_design": _attributes(
            definitions,
            [
                "subject",
                "local_rule",
                "corporate_emergency_authority",
                "assignment_status",
                "baseline",
                "candidate",
                "test",
            ],
        ),
        "dated_states": states,
        "retrospectives": _attributes(
            history.select("eng005", {"retrospective_observation"}),
            ["actor", "decision", "corporate_retroactive_approval", "finding"],
        ),
        "exceptions": exceptions,
        "source_fixture_not_relabelled_as_later_operating_change": True,
    }


def stage_assessments(history):
    facts = []
    for row in history.select(
        "stagegate",
        {"stage_assessment", "stage_reassessment", "technical_gate", "residual_request"},
    ):
        d = detail(row)
        facts.append(
            {
                "source": custody(row),
                "actor": d.get("actor_person_id"),
                "status": d.get("status"),
                "risk_statement": d.get("risk_statement"),
                "technical_decision_scope": d.get("technical_decision_scope"),
                "residual_risk_request": d.get("residual_risk_request"),
                "company_risk_acceptance": d.get("risk_acceptance"),
                "qualified_risk_acceptance_or_transition_release_accepted": False,
            }
        )
    return {
        "dated_assessment_and_reassessment": facts,
        "original_role_inputs": _attributes(
            history.select("stagegate", {"stage_input"}),
            ["actor_person_id", "risk_statement", "selected_changed_service"],
        ),
    }


def contract_commitments(history):
    populations, exceptions = [], []
    for row in history.select("contract", {"selected_term_inventory"}):
        d = detail(row)
        terms = d.get("term_occurrences", [])
        require(
            isinstance(terms, list) and all(isinstance(t, dict) for t in terms),
            "Typed selected contract term occurrences required",
        )
        require(
            "term_occurrence_count" not in d or type(d["term_occurrence_count"]) is int,
            "Strict selected term count required",
        )
        occurrence_ids = _ids([t["occurrence_id"] for t in terms])
        examined = []
        for term in terms:
            ref = term.get("source_ref")
            original, status = (
                history.resolve(
                    row,
                    ref,
                    expected={"phi_ba.contract_register", "provider.relationship_register"},
                )
                if isinstance(ref, dict)
                else (None, "EXACT_TERM_ORIGINAL_REFERENCE_ABSENT")
            )
            original_terms = detail(original).get("synthetic_terms", {}) if original else {}
            if isinstance(original_terms, dict):
                value = original_terms.get(term.get("term_id"))
            elif isinstance(original_terms, list):
                require(
                    all(isinstance(t, dict) for t in original_terms),
                    "Typed original synthetic contract clause vector required",
                )
                _ids([t.get("clause_candidate_id") for t in original_terms])
                matches = [
                    t for t in original_terms if t["clause_candidate_id"] == term.get("term_id")
                ]
                value = matches[0].get("declared_obligation") if len(matches) == 1 else None
            else:
                value = None
            examined.append(
                {
                    "occurrence_id": term["occurrence_id"],
                    "term_id": term.get("term_id"),
                    "original_status": status,
                    "original": custody(original) if original else None,
                    "term_value_equals_exact_original": _json(term.get("term_value"))
                    == _json(value)
                    if value is not None
                    else None,
                    "professional_provision_or_applicability_review_accepted": False,
                }
            )
        agrees = (
            d.get("term_occurrence_count") == len(occurrence_ids)
            if "term_occurrence_count" in d
            else None
        )
        fact = {
            "source": custody(row),
            "selected_occurrence_ids": sorted(occurrence_ids),
            "recomputed_term_count": len(occurrence_ids),
            "company_count_agrees": agrees,
            "term_original_examinations": examined,
            "qualified_counsel_provision_review_reported": d.get(
                "qualified_counsel_provision_review"
            ),
            "full_customer_terms_denominator_established": False,
        }
        if agrees is False or any(t["term_value_equals_exact_original"] is False for t in examined):
            exceptions.append(fact)
        populations.append(fact)
    return {
        "selected_term_populations_before_selection": populations,
        "commitment_owner_and_limits": _attributes(
            history.select("prd", {"commitment_scope"}),
            [
                "commitment",
                "customer_id",
                "service_id",
                "delivery_contacts",
                "role_title_states",
                "nonstandard_product_promises_approved",
                "actual_customer_or_contract_status",
            ],
        ),
        "provisional_owner_triage": _attributes(
            history.select("contract", {"owner_candidate_triage"}),
            [
                "status",
                "actor_person_id",
                "owner_attests_preliminary_service_mapping",
                "qualified_counsel_provision_review",
            ],
        ),
        "exceptions": exceptions,
        "actual_delivery_capability_or_contract_authority_accepted": False,
    }


def product_impact(history):
    populations, notices, exceptions = [], [], []
    for row in history.select("prd", {"impact_assessment"}):
        d = detail(row)
        scopes = _effective(
            history.select("provider", {"operation_scope"}), row["source"]["event_at"]
        )
        declared = {v for r in scopes for v in _ids(detail(r).get("declared_relationship_ids", []))}
        relationships = _effective(
            history.select("provider", {"relationship_register"}), row["source"]["event_at"]
        )
        registered = {
            detail(r)["provider_id"]
            for r in relationships
            if isinstance(detail(r).get("provider_id"), str)
        }
        included = _ids(d.get("internal_dependency_ids", []))
        fact = {
            "source": custody(row),
            "independent_selected_scope_originals": [custody(r) for r in scopes],
            "independent_relationship_originals": [custody(r) for r in relationships],
            "declared_scope_dependencies": sorted(declared),
            "registered_dependencies": sorted(registered),
            "impact_included_dependencies": sorted(included),
            "scope_dependencies_omitted_from_impact": sorted(declared - included),
            "registered_dependencies_omitted_from_impact": sorted(registered - included),
            "dependency_register_omissions": sorted(declared - registered),
            "recipient_matrix": sorted(_ids(d.get("original_recipient_matrix", []))),
            "company_execution_state": d.get("change_execution_state"),
            "all_customer_AI_purpose_or_actual_release_population_established": False,
        }
        if declared - included or registered - included:
            exceptions.append({"facet": "IMPACT_DEPENDENCIES", **fact})
        populations.append(fact)
    for row in history.select("prd", {"notice_decision"}):
        d = detail(row)
        commitments = _ancestors(history, row, "prd", {"commitment_scope"})
        # A record/digest chain can have intervening stages; no latest contact alias.
        contacts = (
            detail(commitments[0]).get("delivery_contacts", {}) if len(commitments) == 1 else {}
        )
        fact = {
            "source": custody(row),
            "exact_commitment_original": custody(commitments[0]) if len(commitments) == 1 else None,
            "delivery_contact_matches_declared_owner": d.get("customer_delivery_contact_id")
            == contacts.get("customer_delivery")
            if contacts.get("customer_delivery")
            else None,
            "legal_contact_matches_declared_reviewer": d.get("legal_reviewer_id")
            == contacts.get("legal_review")
            if contacts.get("legal_review")
            else None,
            "source_notice_duty": d.get("external_notice_duty"),
            "source_send_gate": d.get("send_gate"),
            "reported_customer_receipt": d.get("customer_receipt_or_acknowledgment"),
            "actual_duty_timing_and_customer_delivery_reperformed": False,
        }
        if (
            fact["delivery_contact_matches_declared_owner"] is False
            or fact["legal_contact_matches_declared_reviewer"] is False
        ):
            exceptions.append({"facet": "NOTICE_CONTACTS", **fact})
        notices.append(fact)
    return {
        "declared_service_change_requests": _attributes(
            history.select("prd", {"change_request"}),
            [
                "change_id",
                "service_id",
                "customer_id",
                "change_execution_state",
                "external_notice_duty",
            ],
        ),
        "impact_populations_before_selection": populations,
        "notice_contact_tests": notices,
        "dependency_discovery_and_escalation_versions": _attributes(
            history.select(
                "prd", {"dependency_discovery", "internal_concern", "internal_escalation"}
            ),
            [
                "omitted_dependency_id",
                "concern_origin",
                "status",
                "escalated_to_contact_ids",
                "remediation_gate",
            ],
        ),
        "company_reconciliation_claims": _attributes(
            history.select("prd", {"reconciliation"}),
            [
                "selected_change_count",
                "selected_customer_count",
                "external_customer_receipts",
                "external_messages_sent",
                "notice_duty_resolved",
                "historical_open_exception_ids",
            ],
        ),
        "exceptions": exceptions,
        "internal_change_is_not_external_customer_communication": True,
    }


def concern_communication(history):
    matrices, cases, exceptions = [], [], []
    for row in history.select(
        "prdconcern", {"recipient_matrix", "response_draft", "dispatch_gate", "reconciliation"}
    ):
        d = detail(row)
        origins = _effective(history.select("prd", {"commitment_scope"}), row["source"]["event_at"])
        origins = [
            r
            for r in origins
            if detail(r).get("customer_id") == d.get("customer_id")
            and detail(r).get("service_id") == d.get("service_id")
            and d.get("customer_id")
            and d.get("service_id")
        ]
        contacts = detail(origins[0]).get("delivery_contacts", {}) if len(origins) == 1 else {}
        expected = {
            role
            for name, role in [
                ("customer_delivery", "CUSTOMER_DELIVERY"),
                ("legal_review", "LEGAL"),
                ("product", "PRODUCT"),
            ]
            if contacts.get(name)
        }
        support = [
            r
            for r in _effective(
                history.select("phi_ba", {"operation_scope"}), row["source"]["event_at"]
            )
            if detail(r).get("sim_service_id") == d.get("service_id")
            and detail(r).get("sim_customer_id") == d.get("customer_id")
            and isinstance(detail(r).get("sim_subcontractor_id"), str)
            and detail(r)["sim_subcontractor_id"]
        ]
        if support:
            expected.add("SUPPORT_RECOVERY")
        actual = _ids(d.get("selected_internal_recipient_roles", []))
        fact = {
            "source": custody(row),
            "contact_commitment_originals": [custody(r) for r in origins],
            "independent_support_scope_originals": [custody(r) for r in support],
            "expected_internal_roles_from_collected_scopes": sorted(expected),
            "recorded_internal_roles": sorted(actual),
            "missing_internal_roles": sorted(expected - actual),
            "extra_unexplained_roles": sorted(actual - expected) if origins else None,
            "contact_accuracy_supported_by_exact_scope": bool(origins),
            "reported_outbound_delivery": d.get("company_outbound_delivery_accepted"),
            "reported_separate_customer_acknowledgment": d.get(
                "separate_customer_acknowledgment_exists"
            ),
            "actual_external_audience_receipt_established": False,
        }
        if expected - actual:
            exceptions.append(fact)
        matrices.append(fact)
    for row in history.select(
        "prdconcern",
        {
            "simulated_inbox",
            "case_intake",
            "concern_assessment",
            "legal_gate",
            "dispatch_attempt",
            "exception_register",
        },
    ):
        d = detail(row)
        prior = d.get("previous_native_content")
        target, status = (
            history.scalar(
                row,
                record=prior.get("record"),
                sha256=prior.get("sha256"),
                family="prdconcern",
                roles={
                    "simulated_inbox",
                    "case_intake",
                    "recipient_matrix",
                    "concern_assessment",
                    "legal_gate",
                    "response_draft",
                    "dispatch_gate",
                    "dispatch_attempt",
                    "reconciliation",
                    "exception_register",
                },
            )
            if isinstance(prior, dict) and prior.get("sha256") is not None
            else (None, "SCALAR_PRIOR_REFERENCE_ABSENT")
        )
        fact = {
            "source": custody(row),
            "prior_original_status": status,
            "prior_original": custody(target) if target else None,
            "claimant_identity_verified_reported": d.get("claimant_customer_identity_verified"),
            "source_status": d.get("status"),
            "source_action": d.get("action"),
            "source_external_notice_duty": d.get("external_notice_duty"),
            "real_external_messages_sent_reported": d.get("real_external_messages_sent"),
            "all_support_channel_case_and_dismissed_report_population_established": False,
            "unverified_simulated_claim_not_relabelled_real_customer_evidence": True,
        }
        cases.append(fact)
    return {
        "dated_recipient_and_delivery_witnesses": matrices,
        "dated_intake_response_failure_and_exception_versions": cases,
        "exceptions": exceptions,
        "qualified_external_signature_delivery_or_validated_closure_accepted": False,
    }


def _task_facts(task, calculations):
    local, operating, urgent, stages, terms, impact, concerns = calculations
    control = task["control_id"]
    kind = task["kind"]
    clause = task["task_id"].split("-corporate-", 1)[1]
    facets, exceptions = {}, []
    families = {"change-history", "eng005operating"}
    if control == "SH-ENG-001":
        facets = {
            "declared_business_intent_and_affected_scope": local["intent_and_requirements"],
            "selected_operating_requests_and_risk_inputs": {
                "requests": operating["declared_selected_request_population"],
                "risk": operating["risk_and_test_design"],
            },
            "dated_stage_inputs_and_reassessment": stages,
            "source_commitment_limits": terms["commitment_owner_and_limits"],
        }
        families |= {"stagegate", "prd", "contract", "phi_ba", "transition"}
    elif control == "SH-ENG-002":
        facets = {
            "exact_package_named_peer_review_attributes": local["peer_reviews"],
            "exact_retained_configuration_diffs": local["configuration_differences"],
            "operating_request_and_approver_separation": operating["approvals"],
            "exact_artifact_release_gate_reperformance": local["release_gates"],
            "actual_branch_protection_and_approval_authority": "UNPERFORMED",
        }
        exceptions = [
            e for e in local["exceptions"] if e["facet"] in {"PEER_INDEPENDENCE", "RELEASE_GATE"}
        ]
        exceptions += [e for e in operating["exceptions"] if e["facet"] == "OPERATING_RELEASE_GATE"]
    elif control == "SH-ENG-003":
        facets = {
            "risk_selected_mandatory_test_design": operating["risk_and_test_design"],
            "local_recorded_tests_vs_independent_package_budget": local["tests"],
            "operating_required_passed_and_actual_result_sets": operating["tests"],
            "native_package_configuration_bindings": local["packages"],
            "actual_security_privacy_data_and_pipeline_test_execution": "UNPERFORMED",
        }
        exceptions = [e for e in local["exceptions"] if e["facet"] in {"PACKAGE", "TEST_SCOPE"}]
        exceptions += [e for e in operating["exceptions"] if e["facet"] == "MANDATORY_TESTS"]
    elif control == "SH-ENG-004":
        facets = {
            "exact_local_gate_and_released_artifact_chain": local["local_releases"],
            "operating_release_approval_test_and_application_chain": {
                "releases": operating["releases"],
                "applications": operating["applications"],
                "verifications": operating["verifications"],
            },
            "actual_collected_local_export_bytes_reconciliation": local[
                "raw_configuration_exports"
            ],
            "release_identity_and_target_scope_not_actual_pipeline_proof": True,
        }
        families.add("configuration-runtime-history")
        exceptions = [
            e for e in local["exceptions"] if e["facet"] == "RELEASE_AFTER_UNSUPPORTED_GATE"
        ]
        exceptions += [
            e
            for e in operating["exceptions"]
            if e["facet"] in {"OPERATING_RELEASE_GATE", "APPLIED_VALUE", "POST_CHANGE_VERIFICATION"}
        ]
        if clause == "CHECK-SOC2:CC6.8":
            facets = {
                "exact_local_release_gate_installation_boundary": local["local_releases"],
                "collected_local_configuration_export_versions": local["raw_configuration_exports"],
                "installation_restriction_and_unapproved_executable_tests": (
                    "UNPERFORMED_WITHOUT_ACTUAL_ENDPOINT_OR_EXECUTABLE_ORIGINALS"
                ),
                "representative_update_and_detection_response_population": "UNPERFORMED",
            }
    elif control == "SH-ENG-005":
        facets = {
            "separate_prospective_emergency_definition_and_gate": urgent[
                "reason_scope_and_local_gate_design"
            ],
            "earlier_gate_bypass_and_later_state_versions": urgent["dated_states"],
            "dated_retrospective_scope_without_retroactive_approval": urgent["retrospectives"],
            "later_operating_change_requests_and_approval_traces": {
                "requests": operating["declared_selected_request_population"],
                "approvals": operating["approvals"],
                "releases": operating["releases"],
                "recoveries": operating["recoveries"],
                "reviews": operating["review_versions"],
            },
            "corporate_emergency_authority_and_recurring_cause_closure": "UNPERFORMED",
        }
        families.add("eng005")
        exceptions = urgent["exceptions"] + [
            e for e in operating["exceptions"] if e["facet"] == "OPERATING_RELEASE_GATE"
        ]
    elif control == "SH-ENG-006":
        facets = {
            "exact_native_rollback_source_budget_reperformance": local["rollback_sources"],
            "selected_request_prerequisites_and_data_effect_scope": operating[
                "risk_and_test_design"
            ],
            "recorded_operating_rehearsal_vs_baseline_and_active_state": operating["recoveries"],
            "local_release_stop_and_failure_paths": local["release_gates"],
            ("actual_representative_restore_irreversible_effects_or_alternative_execution"): (
                "UNPERFORMED"
            ),
        }
        exceptions = [e for e in local["exceptions"] if e["facet"] == "RELEASE_GATE"]
        exceptions += [e for e in operating["exceptions"] if e["facet"] == "RECOVERY_BASELINE"]
    elif control == "SH-PRD-002":
        facets = {
            "exact_selected_term_occurrence_census_and_provision_bytes": terms[
                "selected_term_populations_before_selection"
            ],
            "delivery_contact_owner_and_stated_use_limitations": terms[
                "commitment_owner_and_limits"
            ],
            "provisional_contact_attestation_scope": terms["provisional_owner_triage"],
            "notice_contact_accuracy_against_exact_commitment": impact["notice_contact_tests"],
            "accepted_actual_delivery_capability_and_nonstandard_promise_review": "UNPERFORMED",
        }
        families = {"contract", "phi_ba", "prd", "provider", "legaloriginals"}
        exceptions = terms["exceptions"] + [
            e for e in impact["exceptions"] if e["facet"] == "NOTICE_CONTACTS"
        ]
    elif control == "SH-PRD-003":
        facets = {
            "independent_selected_dependency_vs_change_impact_populations": impact[
                "impact_populations_before_selection"
            ],
            "dated_changed_service_request_and_notice_contact_tests": {
                "requests": impact["declared_service_change_requests"],
                "notices": impact["notice_contact_tests"],
            },
            "later_dependency_discovery_and_escalation_history": impact[
                "dependency_discovery_and_escalation_versions"
            ],
            "actual_customer_AI_purpose_changes_and_notice_delivery_clock": "UNPERFORMED",
        }
        families = {"prd", "provider", "phi_ba", "transition"}
        exceptions = impact["exceptions"]
    else:
        facets = {
            "selected_internal_and_unverified_external_claim_intake_versions": concerns[
                "dated_intake_response_failure_and_exception_versions"
            ],
            "independently_expected_audience_vs_recorded_recipient_versions": concerns[
                "dated_recipient_and_delivery_witnesses"
            ],
            "internal_escalation_risk_and_change_linkage": impact[
                "dependency_discovery_and_escalation_versions"
            ],
            "separate_company_reconciliation_claims": impact["company_reconciliation_claims"],
            "all_channels_timely_repeat_high_impact_cases_and_validated_closure": "UNPERFORMED",
        }
        families = {"prdconcern", "prd", "phi_ba", "provider"}
        exceptions = concerns["exceptions"]
    if clause == "ACTION-S-COMMUNICATION":
        facets = {
            "control_specific_commitment_change_or_concern_context": facets,
            "exact_contact_accuracy_and_notice_duty_witnesses": impact["notice_contact_tests"],
            "source_audience_and_separate_receipt_response_trace": concerns,
            "actual_external_sender_authority_and_complete_receipt_population": "UNPERFORMED",
        }
        exceptions += concerns["exceptions"]
        families |= {"prdconcern", "prd", "phi_ba", "provider"}
    elif clause == "CHECK-SOC2:CC8.1":
        facets = {
            "control_specific_change_attribute": facets,
            "normal_and_emergency_native_chain_context": {
                "intents": local["intent_and_requirements"],
                "requests": operating["declared_selected_request_population"],
                "emergency_reasons_and_scope": urgent["reason_scope_and_local_gate_design"],
            },
            "real_code_infrastructure_data_and_emergency_population_scope": "UNPERFORMED",
        }
        families.add("eng005")
    primary_by_control = {
        "SH-ENG-001": {
            "TOD": ["declared_business_intent_and_affected_scope", "source_commitment_limits"],
            "IMPLEMENTATION": ["selected_operating_requests_and_risk_inputs"],
            "TOE": [
                "dated_stage_inputs_and_reassessment",
                "selected_operating_requests_and_risk_inputs",
            ],
        },
        "SH-ENG-002": {
            "TOD": ["actual_branch_protection_and_approval_authority"],
            "IMPLEMENTATION": [
                "exact_retained_configuration_diffs",
                "exact_package_named_peer_review_attributes",
                "exact_artifact_release_gate_reperformance",
            ],
            "TOE": [
                "operating_request_and_approver_separation",
                "exact_package_named_peer_review_attributes",
            ],
        },
        "SH-ENG-003": {
            "TOD": ["risk_selected_mandatory_test_design"],
            "IMPLEMENTATION": [
                "native_package_configuration_bindings",
                "local_recorded_tests_vs_independent_package_budget",
            ],
            "TOE": [
                "operating_required_passed_and_actual_result_sets",
                "local_recorded_tests_vs_independent_package_budget",
            ],
        },
        "SH-ENG-004": {
            "TOD": ["release_identity_and_target_scope_not_actual_pipeline_proof"],
            "IMPLEMENTATION": [
                "exact_local_gate_and_released_artifact_chain",
                "actual_collected_local_export_bytes_reconciliation",
            ],
            "TOE": [
                "operating_release_approval_test_and_application_chain",
                "actual_collected_local_export_bytes_reconciliation",
            ],
        },
        "SH-ENG-005": {
            "TOD": ["separate_prospective_emergency_definition_and_gate"],
            "IMPLEMENTATION": ["earlier_gate_bypass_and_later_state_versions"],
            "TOE": [
                "dated_retrospective_scope_without_retroactive_approval",
                "later_operating_change_requests_and_approval_traces",
            ],
        },
        "SH-ENG-006": {
            "TOD": ["selected_request_prerequisites_and_data_effect_scope"],
            "IMPLEMENTATION": [
                "exact_native_rollback_source_budget_reperformance",
                "local_release_stop_and_failure_paths",
            ],
            "TOE": ["recorded_operating_rehearsal_vs_baseline_and_active_state"],
        },
        "SH-PRD-002": {
            "TOD": ["delivery_contact_owner_and_stated_use_limitations"],
            "IMPLEMENTATION": ["exact_selected_term_occurrence_census_and_provision_bytes"],
            "TOE": [
                "notice_contact_accuracy_against_exact_commitment",
                "provisional_contact_attestation_scope",
            ],
        },
        "SH-PRD-003": {
            "TOD": ["dated_changed_service_request_and_notice_contact_tests"],
            "IMPLEMENTATION": ["independent_selected_dependency_vs_change_impact_populations"],
            "TOE": [
                "later_dependency_discovery_and_escalation_history",
                "independent_selected_dependency_vs_change_impact_populations",
            ],
        },
        "SH-PRD-004": {
            "TOD": ["selected_internal_and_unverified_external_claim_intake_versions"],
            "IMPLEMENTATION": [
                "independently_expected_audience_vs_recorded_recipient_versions",
                "internal_escalation_risk_and_change_linkage",
            ],
            "TOE": [
                "separate_company_reconciliation_claims",
                "selected_internal_and_unverified_external_claim_intake_versions",
            ],
        },
    }
    # Each base test uses its own design, occurrence or population lens. Reusing a
    # calculation is explicit; it does not satisfy all authored steps or clauses.
    lens = {
        "TOD": "DATED_DESIGN_AUTHORITY_CONDITIONS_AND_FAILURE_SCOPE",
        "IMPLEMENTATION": "EXACT_DATED_ACTION_CHAIN_AND_ATTRIBUTE_REPERFORMANCE",
        "TOE": "ALL_RETAINED_SELECTED_OCCURRENCES_BEFORE_SELECTION_WITH_FAILURE_HISTORY",
        "ADDITIONAL_DUTY": "EXACT_ADDITIONAL_ACCEPTANCE_FACETS_AND_SEPARATE_MISSING_SCOPE",
    }[kind]
    return (
        {
            "task_kind_lens": lens,
            "control_id": control,
            "exact_clause": clause,
            "control_specific_facets": facets,
            "task_kind_primary_attributes": {
                name: facets[name]
                for name in primary_by_control[control].get(kind, list(facets))
                if name in facets
            },
            "all_authored_steps_or_full_clause_performed": False,
        },
        exceptions,
        families,
    )


def _evidence(rows):
    require(0 < len(rows) <= 20, "Complete engineering citation part must fit writer bound")
    return [
        {"artifact_id": r["artifact_id"], "sha256": r["artifact_sha256"], "locator": "$"}
        for r in rows
    ]


def _aggregate(label, facts, rows, status):
    chunks = [rows[n : n + 20] for n in range(0, len(rows), 20)]
    ids = [label] + [f"{label}-CITE-{n + 1:04d}" for n in range(1, len(chunks))]
    observations = []
    for n, chunk in enumerate(chunks):
        group = {
            "aggregate_observation_id": label,
            "citation_part_index": n + 1,
            "citation_part_count": len(chunks),
            "all_citation_part_ids": ids,
            "this_part_extends_aggregate_direct_citations": True,
        }
        part = (
            {**facts, "citation_group": group}
            if n == 0
            else {
                "citation_group": group,
                "source_custody_subset": [custody(r) for r in chunk],
                "aggregate_facts_held_in_observation": label,
            }
        )
        require(len(ids[n]) <= 128, "Bounded engineering observation ID required")
        observations.append(
            {"id": ids[n], "facts": part, "status": status, "evidence": _evidence(chunk)}
        )
    return observations


def examine(records, *, as_of, scratch_root):
    """Pure data callback; scratch_root is not opened and company code is inert."""
    tasks, task_contracts = task_plan(), contracts()
    history = History(records, as_of=as_of)
    calculations = (
        local_packages(history),
        operating_changes(history),
        emergency(history),
        stage_assessments(history),
        contract_commitments(history),
        product_impact(history),
        concern_communication(history),
    )
    output = []
    for task in tasks:
        facts, exceptions, families = _task_facts(task, calculations)
        rows = history.supported_rows(facts)
        missing = not rows
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
        for n, row in enumerate(rows):
            observations.append(
                {
                    "id": f"ACQUISITION-CONTEXT-{n + 1:04d}"
                    if missing
                    else f"NATIVE-OCCURRENCE-{n + 1:04d}",
                    "facts": {
                        "source": custody(row),
                        "actual_retained_bytes_reparsed": True,
                        "task_specific_attributes_supported": not missing,
                        "full_period_completeness_not_asserted": True,
                    },
                    "status": "SUPPORT_UNAVAILABLE" if missing else "OBSERVED",
                    "evidence": _evidence([row]),
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
                    "schema": "SH_COLLECTED_ENGINEERING_PRODUCT_TASK_EXAMINATION_V1",
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
                        "Bounded original-source discrepancies remain with explicit "
                        "unsupported broader scope."
                    )
                    if exceptions
                    else (
                        "Bounded retained-source attributes examined; exact broader conditions "
                        "or missing originals remain unperformed."
                    ),
                },
            }
        )
    return output
