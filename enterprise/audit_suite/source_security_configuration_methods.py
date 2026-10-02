"""Exact 38-task B02 byte examinations; no company scripts or stored SQL run.

Actual Engine collection membership and clock are enforced by the reviewed caller.
Company records remain declarations/observations with their original availability;
policy models, local exports and synthetic probes never assert real deployment.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from .collected_security_history import History, custody, detail, expected_role, key, pointers
from .company_store import _json, _time
from .fresh_sec003_procedure import ProcedureError, require
from .source_library_security_methods import analyze_security_publishers, analyze_vulnerability

PLAN_SHA = "d3634a5dc05d3a88b378eccbfca55ac86ad44ccd493c1389dd7ef83034daa741"
BROAD = (
    "Full enterprise/year inventory and required-event denominator, "
    "real endpoint/network/SaaS enforcement, "
    "production key custody, deployed identity and physical-site "
    "assurance, actual application/ePHI operations, "
    "accepted environmental applicability and qualified assurance remain unperformed."
)
ADDRESSABLE = {
    "164.308(a)(3)(ii)(A)",
    "164.308(a)(3)(ii)(B)",
    "164.308(a)(3)(ii)(C)",
    "164.308(a)(4)(ii)(B)",
    "164.308(a)(4)(ii)(C)",
    "164.308(a)(5)(ii)(A)",
    "164.308(a)(5)(ii)(B)",
    "164.308(a)(5)(ii)(C)",
    "164.308(a)(5)(ii)(D)",
    "164.308(a)(7)(ii)(D)",
    "164.308(a)(7)(ii)(E)",
    "164.310(a)(2)(i)",
    "164.310(a)(2)(ii)",
    "164.310(a)(2)(iii)",
    "164.310(a)(2)(iv)",
    "164.310(d)(2)(iii)",
    "164.310(d)(2)(iv)",
    "164.312(a)(2)(iii)",
    "164.312(a)(2)(iv)",
    "164.312(c)(2)",
    "164.312(e)(2)(i)",
    "164.312(e)(2)(ii)",
}
SEC003_PLAN = {
    "inventory_record": "INVENTORY-SELECTED-01",
    "baseline_record": "BASELINE-01",
    "census_record": "CENSUS-OCT-01",
    "scan_record": "SCAN-OCT-01",
    "scan_baseline_record": "BASELINE-OCT-01",
    "schedule_record": "SCHEDULE-OCT-01",
    "reconciliation_record": "RECON-OCT-01",
    "advisory_record": "ADV-SH-SIM-2027-01",
    "snapshot_cutoff": "2027-10-31T23:59:59Z",
}
SEC005_PLAN = {
    "inventory_record": "INVENTORY-SELECTED-01",
    "baseline_record": "BASELINE-01",
    "application_record": "APPLY-BASELINE-01",
    "initial_approval_records": ["APPROVE-TECH-01", "APPROVE-SEC-01"],
}


def task_plan():
    raw = (
        Path(__file__).with_name("security_configuration_collected_task_plan_v1.json").read_bytes()
    )
    require(hashlib.sha256(raw).hexdigest() == PLAN_SHA, "Exact 38-task B02 plan required")
    plan = json.loads(raw)
    require(plan["task_count"] == len(plan["tasks"]) == 38, "Exact thirty-eight B02 tasks required")
    return plan["tasks"]


def contracts():
    return {
        t["task_id"]: {
            "performed": (
                f"Examine actual retained {t['control_id']} {t['clause_group']} originals: "
            )
            + t["authored_instruction"]
            + " Record examined, contradicted and unsupported source attributes separately.",
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
        and all(isinstance(i, str) and i for i in values)
        and len(set(values)) == len(values),
        "Distinct typed business identifier vector required",
    )
    return set(values)


def _retry(value):
    typed = all(
        type(value.get(k)) is int and value[k] > 0
        for k in ("attempts", "timeout_ms", "max_total_ms")
    )
    return {
        "exact_positive_integer_fields": typed,
        "calculated_total_timeout_ms": value["attempts"] * value["timeout_ms"] if typed else None,
        "within_local_limit": value["attempts"] * value["timeout_ms"] <= value["max_total_ms"]
        if typed
        else None,
        "scope": "LOCAL_DATA_ONLY_RETRY_ARITHMETIC",
    }


def _pick(rows, fields):
    return [
        {"source": custody(r), "attributes": {k: detail(r)[k] for k in fields if k in detail(r)}}
        for r in rows
    ]


def _joined(history, row, field, expected):
    ref = row["document"].get(field)
    return (
        history.resolve(row, ref, expected=expected)
        if isinstance(ref, dict)
        else (None, "ORIGINAL_REFERENCE_ABSENT")
    )


def _observed_at(row, value):
    """A claimed completed action cannot occur after its original native event."""
    if not isinstance(value, str) or not value:
        return False
    try:
        return _time(value) <= _time(row["source"]["event_at"])
    except (ValueError, TypeError):
        return False


def _effective(rows, at, history):
    """Date-effective native versions, while the original history remains retained."""
    identities = {key(r["source"])[:-1] for r in rows}
    rows = [r for r in history.rows if key(r["source"])[:-1] in identities]
    selected = {}
    for r in rows:
        if _time(r["source"]["available_at"]) > _time(at):
            continue
        identity = key(r["source"])[:-1]
        if (
            identity not in selected
            or r["source"]["version"] > selected[identity]["source"]["version"]
        ):
            selected[identity] = r
    # An unavailable structured body on the actual latest version does not
    # authorize falling back to an older configuration, policy or assignment.
    return [r for r in selected.values() if isinstance(r["document"], dict)]


def configuration(history):
    inventories = history.select("configuration-history", {"configuration_inventory"})
    discoveries = []
    for row in history.select("sec005operated", {"security_inventory"}):
        discoveries.append(
            {
                "source": custody(row),
                "kind": "DECLARED_SELECTED_SECURITY_ASSETS",
                "ids": sorted(_ids([a["id"] for a in row["document"].get("assets", [])])),
            }
        )
    for row in history.select("sec001component", {"component_inventory"}):
        discoveries.append(
            {
                "source": custody(row),
                "kind": "SELECTED_FUTURE_COMPONENT_DECLARATION",
                "ids": sorted(_ids(detail(row).get("component_ids", []))),
            }
        )
    for row in history.select("supplementalops", {"workstation_inventory"}):
        discoveries.append(
            {
                "source": custody(row),
                "kind": "INDEPENDENT_LOCAL_ASSIGNMENT_REGISTRY",
                "ids": sorted(_ids([a["asset_id"] for a in detail(row).get("resources", [])])),
            }
        )
    comparisons, exports, exceptions = [], [], []
    for drift in history.select("configuration-history", {"configuration_drift"}):
        refs = drift["document"].get("source_records", {})
        actual, astatus = (
            history.resolve(
                drift,
                refs["configuration_inventory"],
                expected={"configuration-history.configuration_inventory"},
            )
            if "configuration_inventory" in refs
            else (None, "ORIGINAL_REFERENCE_ABSENT")
        )
        desired, dstatus = (
            history.resolve(
                drift,
                refs["configuration_desired"],
                expected={"configuration-history.configuration_desired"},
            )
            if "configuration_desired" in refs
            else (None, "ORIGINAL_REFERENCE_ABSENT")
        )
        fact = {
            "source": custody(drift),
            "actual_original_status": astatus,
            "desired_original_status": dstatus,
            "full_deployed_baseline_tested": False,
        }
        if actual and desired:
            a, d = detail(actual).get("configuration"), detail(desired).get("configuration")
            require(
                isinstance(a, dict) and isinstance(d, dict),
                "Typed exact configuration snapshots required",
            )
            differences = [
                {"field": k, "actual": a.get(k), "desired": d.get(k)}
                for k in sorted(set(a) | set(d))
                if _json(a.get(k)) != _json(d.get(k))
            ]
            fact.update(
                actual=custody(actual),
                desired=custody(desired),
                field_differences=differences,
                actual_retry=_retry(a),
                desired_retry=_retry(d),
                equal_embedded_configuration=_json(a) == _json(d),
                reported_equal=detail(drift).get("matches_approved_desired"),
                independent_bytes_basis="REPARSED_NATIVE_EMBEDDED_CONFIGURATION_NOT_DEPLOYED_TARGET_EXPORT",
            )
            if (
                differences
                or not fact["actual_retry"]["exact_positive_integer_fields"]
                or fact["actual_retry"]["within_local_limit"] is False
            ):
                exceptions.append(fact)
        comparisons.append(fact)
    for row in history.select("configuration-runtime-history", {"configuration_export"}):
        md = row["source"]["provenance"].get("operational_metadata", {})
        runtime = [
            r
            for r in history.select("configuration-runtime-history", {"configuration_runtime"})
            if r["source"]["record"] == md.get("target_id")
            and r["source"]["sha256"] == md.get("runtime_sha256")
        ]
        fact = {
            "source": custody(row),
            "target_id": md.get("target_id"),
            "raw_export_sha256": row["source"]["sha256"],
            "retry_reperformance": _retry(row["document"]),
            "runtime_reference_basis": "DECLARED_RECORD_AND_DIGEST_NO_NATIVE_VERSION_POINTER",
            "source_export_is_release_approval": False,
            "actual_target_opened": False,
            "export_timestamp_supported": _observed_at(row, md.get("exported_at")),
        }
        if len(runtime) == 1 and _time(runtime[0]["source"]["available_at"]) <= _time(
            row["source"]["event_at"]
        ):
            fact.update(
                runtime=custody(runtime[0]),
                equals_locally_declared_approved_digest=row["source"]["sha256"]
                == runtime[0]["document"].get("approved_sha256"),
            )
        else:
            fact["runtime_support"] = "UNIQUE_CONTEMPORANEOUS_NATIVE_RUNTIME_NOT_COLLECTED"
        if (
            not fact["retry_reperformance"]["exact_positive_integer_fields"]
            or fact["retry_reperformance"]["within_local_limit"] is False
        ):
            exceptions.append(fact)
        exports.append(fact)
    return {
        "inventory_versions": _pick(
            inventories,
            [
                "asset_id",
                "asset_kind",
                "owner_id",
                "source_service_reference",
                "policy_status",
                "custody_basis",
            ],
        ),
        "independent_selected_discoveries": [
            {
                **d,
                "outside_configuration_inventory": sorted(
                    set(d["ids"])
                    - {
                        detail(r)["asset_id"]
                        for r in _effective(inventories, d["source"]["event_at"], history)
                        if isinstance(detail(r).get("asset_id"), str)
                    }
                ),
            }
            for d in discoveries
        ],
        "embedded_drift_comparisons": comparisons,
        "actual_raw_export_reperformance": exports,
        "operation_versions": _pick(
            history.select("configuration-runtime-history", {"configuration_operation"}),
            [
                "operation",
                "operator_id",
                "comparison_basis",
                "prior_sha256",
                "current_sha256",
                "automatic_ticket_closure",
            ],
        ),
        "exceptions": exceptions,
        "enterprise_discovery_denominator_established": False,
        "historic_originals_not_reconstructed_from_latest_or_equal_digest": True,
    }


def selected_calculations(history):
    results = {}
    for row in history.select("sec005operated"):
        for field in (
            "selected_asset_ids",
            "agent_required_asset_ids",
            "agent_covered_asset_ids",
            "publisher_probe_record_ids",
            "received_probe_record_ids",
            "observed_agent_asset_ids",
            "observed_interface_ids",
            "reviewed_probe_record_ids",
        ):
            if field in row["document"]:
                _ids(row["document"][field])
    for row in history.select("sec003vuln"):
        d = detail(row)
        for field in (
            "observed_asset_ids",
            "finding_asset_ids",
            "covered_asset_ids",
            "scheduled_asset_ids",
        ):
            if field in d:
                _ids(d[field])
        for field in ("observed_count", "reported_count", "reported_asset_count"):
            require(
                field not in d or type(d[field]) is int and d[field] >= 0,
                "Strict native vulnerability census/count required",
            )
    required = {
        "SEC005": [
            ("sec005operated", "security_inventory", SEC005_PLAN["inventory_record"]),
            ("sec005operated", "security_baseline", SEC005_PLAN["baseline_record"]),
            ("sec005operated", "security_application", SEC005_PLAN["application_record"]),
            *[
                ("sec005operated", "security_approval", r)
                for r in SEC005_PLAN["initial_approval_records"]
            ],
        ],
        "SEC003": [
            ("sec005operated", "security_inventory", SEC003_PLAN["inventory_record"]),
            ("sec005operated", "security_baseline", SEC003_PLAN["baseline_record"]),
            *[
                ("sec003vuln", role, SEC003_PLAN[name])
                for name, role in [
                    ("census_record", "vulnerability_inventory"),
                    ("scan_record", "vulnerability_scan"),
                    ("scan_baseline_record", "vulnerability_baseline"),
                    ("schedule_record", "vulnerability_schedule"),
                    ("reconciliation_record", "vulnerability_reconciliation"),
                    ("advisory_record", "vulnerability_advisory"),
                ]
            ],
        ],
    }
    for label, needed in required.items():
        missing = [
            f"{f}.{role}/{record}"
            for f, role, record in needed
            if len([r for r in history.select(f, {role}) if r["source"]["record"] == record]) != 1
        ]
        relevant = {"sec005operated"} if label == "SEC005" else {"sec005operated", "sec003vuln"}
        unavailable = [
            j
            for j in history.joins
            if j["origin"]["system"].split(".", 1)[0] in relevant
            and j["status"] != "EXACT_AVAILABLE_ORIGINAL"
        ]
        unsupported_formats = history.format_limitations(relevant)
        if missing or unavailable or unsupported_formats:
            results[label] = {
                "status": "SUPPORT_UNAVAILABLE",
                "missing_exact_originals": missing,
                "unavailable_native_dependencies": unavailable,
                "retained_format_limitations": unsupported_formats,
                "actual_execution_performed": False,
            }
        else:
            try:
                results[label] = (
                    analyze_security_publishers(
                        [r for r in history.rows if isinstance(r["document"], dict)], SEC005_PLAN
                    )
                    if label == "SEC005"
                    else analyze_vulnerability(
                        [r for r in history.rows if isinstance(r["document"], dict)], SEC003_PLAN
                    )
                )
            except (ProcedureError, KeyError, TypeError, ValueError) as error:
                # Custody has already been checked centrally. Missing/ambiguous
                # selected trace support cannot confer a completed calculation.
                results[label] = {
                    "status": "SELECTED_TRACE_UNPERFORMED",
                    "diagnostic": str(error),
                    "actual_execution_performed": False,
                }
    return results


def component_lifecycle(history):
    populations, exceptions = [], []
    for inventory in history.select("sec001component", {"component_inventory"}):
        d = detail(inventory)
        ids = _ids(d.get("component_ids", []))
        origin = inventory["document"].get("exercise_id")
        related = [
            r
            for r in _effective(
                history.select("sec001component"), inventory["source"]["event_at"], history
            )
            if isinstance(origin, str) and origin
            if r["document"].get("exercise_id") == origin
            and _time(r["source"]["available_at"]) <= _time(inventory["source"]["event_at"])
        ]
        owners = {
            i
            for r in related
            if r["logical_system"] == "ownership"
            for i in detail(r).get("owner_ids", {})
        }
        mapped = {
            i
            for r in related
            if r["logical_system"] == "control_mapping"
            for i in detail(r).get("mapped_component_ids", [])
        }
        challenges = [r for r in related if r["logical_system"] == "challenge"]
        challenged = {
            detail(r).get("component_id") for r in challenges if detail(r).get("component_id")
        }
        fact = {
            "source": custody(inventory),
            "historical_cutoff": inventory["source"]["event_at"],
            "component_ids": sorted(ids),
            "unowned": sorted(ids - owners),
            "unmapped": sorted(ids - mapped),
            "challenged_outside_inventory": sorted(challenged - ids),
            "supplier_support": _pick(
                [r for r in related if r["logical_system"] == "supplier_risk"],
                [
                    "component_id",
                    "named_vendor",
                    "support_state",
                    "contract_or_entitlement",
                    "received",
                ],
            ),
            "challenge_history": _pick(
                challenges, ["component_id", "challenge_result", "deployment_allowed"]
            ),
            "native_roles_and_clocks_checked_separately": True,
            "later_ownership_or_mapping_does_not_repair_earlier_snapshot": True,
            "full_lifecycle_or_supplier_assurance": False,
        }
        if ids - owners or ids - mapped or challenged - ids:
            exceptions.append(fact)
        populations.append(fact)
    return {
        "populations": populations,
        "exceptions": exceptions,
        "historical_exception_versions": _pick(
            history.select("sec001component", {"exception_register"}),
            ["exception_id", "open_exception_ids", "exception_open"],
        ),
    }


def logging(history):
    populations, exceptions = [], []
    for family in ("logging-history", "baseline-logging"):
        publishers = history.select(family, {"publisher_events"})
        received = history.select(family, {"ingestion_journal"})
        inventories = history.select(family, {"source_inventory"})
        for checkpoint in history.select(family, {"publisher_checkpoints"}):
            source_id = checkpoint["document"].get("local_source_id")
            cutoff = checkpoint["source"]["event_at"]

            def relevant_inventory(r, source_id=source_id):
                d = detail(r)
                explicit = r["document"].get("local_source_id", d.get("local_source_id"))
                if explicit is not None:
                    require(
                        isinstance(explicit, str) and explicit, "Typed lag-policy source required"
                    )
                    return explicit == source_id
                if "required_sources" not in d:
                    return True  # An expressly unscoped local declaration remains global.
                declared = d["required_sources"]
                require(isinstance(declared, list), "Typed required-source policy scope required")
                names = [
                    item
                    if isinstance(item, str)
                    else item.get("source_id", item.get("local_source_id"))
                    if isinstance(item, dict)
                    else None
                    for item in declared
                ]
                require(
                    all(isinstance(name, str) and name for name in names),
                    "Explicit required-source identifiers required",
                )
                return source_id in names

            effective_inventories = [
                r for r in _effective(inventories, cutoff, history) if relevant_inventory(r)
            ]
            lag_limits = {
                detail(r).get("local_max_ingestion_lag_seconds")
                for r in effective_inventories
                if "local_max_ingestion_lag_seconds" in detail(r)
            }
            require(
                all(type(v) in {int, float} and v >= 0 for v in lag_limits),
                "Typed local ingestion lag limit required",
            )
            lag_limit = next(iter(lag_limits)) if len(lag_limits) == 1 else None
            lag_limit_status = (
                "EXACT_EFFECTIVE_UNAMBIGUOUS_LOCAL_LIMIT"
                if len(lag_limits) == 1
                else "AMBIGUOUS_EFFECTIVE_LOCAL_DECLARATIONS"
                if len(lag_limits) > 1
                else "EFFECTIVE_LOCAL_LIMIT_UNAVAILABLE"
            )
            published = [
                r
                for r in publishers
                if r["document"].get("local_source_id") == source_id
                and _time(r["source"]["available_at"]) <= _time(cutoff)
            ]
            ingestion = [
                r
                for r in received
                if r["document"].get("local_source_id") == source_id
                and _time(r["source"]["available_at"]) <= _time(cutoff)
            ]
            sequences = []
            for r in published:
                event = r["document"]["event"]
                require(
                    type(event["sequence"]) is int and event["sequence"] > 0,
                    "Strict publisher sequence required",
                )
                sequences.append(event["sequence"])
            require(len(set(sequences)) == len(sequences), "Ambiguous publisher sequence originals")
            observed, lags, mismatches = [], [], []
            for r in ingestion:
                e = r["document"]["event"]
                require(
                    type(e["sequence"]) is int and e["sequence"] > 0,
                    "Strict ingestion sequence required",
                )
                observed.append(e["sequence"])
                matching = [
                    p for p in published if p["document"]["event"]["sequence"] == e["sequence"]
                ]
                agrees = len(matching) == 1 and _json(matching[0]["document"]["event"]) == _json(e)
                try:
                    lag = (
                        datetime.fromisoformat(_time(r["document"]["received_at"]))
                        - datetime.fromisoformat(_time(e["source_event_at"]))
                    ).total_seconds()
                    chronology = (
                        _observed_at(r, r["document"].get("received_at"))
                        and _time(e["source_event_at"]) <= _time(r["document"]["received_at"])
                        and all(
                            _observed_at(p, p["document"]["event"]["source_event_at"])
                            for p in matching
                        )
                    )
                except (ValueError, TypeError, KeyError):
                    lag, chronology = None, False
                require(
                    "ingestion_lag_seconds" not in r["document"]
                    or type(r["document"]["ingestion_lag_seconds"]) in {int, float},
                    "Typed reported ingestion lag required",
                )
                lags.append(
                    {
                        "source": custody(r),
                        "sequence": e["sequence"],
                        "calculated_ingestion_lag_seconds": lag if chronology else None,
                        "unsupported_reported_interval_arithmetic": lag if not chronology else None,
                        "reported_lag_seconds": r["document"].get("ingestion_lag_seconds"),
                        "claim_agrees": lag == r["document"].get("ingestion_lag_seconds")
                        if chronology
                        else None,
                        "observed_interval_chronology_supported": chronology,
                        "effective_local_lag_limit_seconds": lag_limit,
                        "effective_local_lag_limit_status": lag_limit_status,
                        "exceeds_effective_lag_limit": lag > lag_limit
                        if chronology and lag_limit is not None
                        else None,
                        "clock_skew_measured": False,
                    }
                )
                if (
                    not agrees
                    or not chronology
                    or lag < 0
                    or lag != r["document"].get("ingestion_lag_seconds")
                    or lag_limit is not None
                    and lag > lag_limit
                ):
                    mismatches.append(
                        {"source": custody(r), "publisher_event_bytes_agree": agrees, "lag": lag}
                    )
            declared = checkpoint["document"].get("sequences", [])
            require(
                isinstance(declared, list) and all(type(i) is int and i > 0 for i in declared),
                "Typed declared checkpoint sequences required",
            )
            fact = {
                "source": custody(checkpoint),
                "source_id": source_id,
                "cutoff": cutoff,
                "lag_limit_status": lag_limit_status,
                "effective_inventory_originals": [custody(r) for r in effective_inventories],
                "retained_inventory_versions_not_overwritten": [custody(r) for r in inventories],
                "required_sources": _pick(
                    effective_inventories,
                    ["required_sources", "required_detections", "local_max_ingestion_lag_seconds"],
                ),
                "publisher_sequences": sorted(sequences),
                "checkpoint_claim": declared,
                "checkpoint_claim_agrees": set(declared) == set(sequences),
                "collector_sequences": sorted(observed),
                "unreceived_publisher_sequences": sorted(set(sequences) - set(observed)),
                "collector_without_publisher": sorted(set(observed) - set(sequences)),
                "event_or_lag_mismatches": mismatches,
                "lag_observations": lags,
                "publisher_originals": [custody(r) for r in published],
                "full_period_or_clock_synchronization_tested": False,
            }
            if (
                fact["unreceived_publisher_sequences"]
                or fact["collector_without_publisher"]
                or mismatches
                or not fact["checkpoint_claim_agrees"]
            ):
                exceptions.append(fact)
            populations.append(fact)
    return {
        "checkpoint_populations_before_selection": populations,
        "exceptions": exceptions,
        "alert_routing": _pick(
            [
                r
                for f in ("logging-history", "baseline-logging")
                for r in history.select(f, {"detection_alerts"})
            ],
            ["rule_id", "severity", "owner_id", "source_event_sha256"],
        ),
        "response_and_review": _pick(
            [
                r
                for f in ("logging-history", "baseline-logging")
                for r in history.select(f, {"response_tickets", "review_records"})
            ],
            ["owner_id", "reviewer_id", "status", "action", "review_procedure"],
        ),
        "healthy_collector_does_not_prove_anomaly_examination": True,
        "no_stored_query_or_company_script_executed": True,
    }


def permission_checks(history):
    results, exceptions = [], []
    for row in history.select("supplementalops", {"access_operation"}):
        d = detail(row)
        if not _observed_at(row, d.get("evaluated_at")):
            results.append(
                {"source": custody(row), "status": "RECORDED_ACCESS_EVALUATION_TIME_UNAVAILABLE"}
            )
            continue
        policies = []
        for ref in d.get("native_dependencies", []):
            target, status = history.resolve(
                row,
                ref,
                expected={"supplementalops.identity_permission"},
                at=d.get("evaluated_at", row["source"]["event_at"]),
            )
            if target and status == "EXACT_AVAILABLE_ORIGINAL":
                policies.append(target)
        if len(policies) != 1:
            results.append(
                {
                    "source": custody(row),
                    "status": "EXACT_CONTEMPORANEOUS_PERMISSION_ORIGINAL_NOT_COLLECTED",
                }
            )
            continue
        policy, request = detail(policies[0])["model_policy"], d["request"]
        require(
            all(k not in request or type(request[k]) is bool for k in ("mfa", "privileged")),
            "Strict local authentication and privilege flags required",
        )
        who = policy["principals"].get(request["principal"])
        checks = {
            "issuer": request.get("issuer") == policy.get("issuer"),
            "audience": request.get("audience") == policy.get("audience"),
            "credential_current": _time(request["expires_at"]) > _time(d["evaluated_at"]),
            "principal_known": who is not None,
            "principal_kind_known": who is not None and who.get("kind") in {"HUMAN", "SERVICE"},
            "resource_permission": who is not None
            and request.get("resource") in who.get("resources", [])
            and request.get("operation") in who.get("operations", []),
            "human_mfa": who is not None
            and (who.get("kind") != "HUMAN" or request.get("mfa") is True),
        }
        if request.get("privileged"):
            approval = policy.get("privilege_approvals", {}).get(request.get("approval"))
            checks["privileged_approval"] = (
                bool(approval)
                and who is not None
                and who.get("privilege_eligible") is True
                and all(
                    approval.get(k) == request.get(k)
                    for k in ("principal", "resource", "operation")
                )
                and _time(approval["valid_from"])
                <= _time(d["evaluated_at"])
                < _time(approval["valid_until"])
                and all(
                    isinstance(approval.get(k), str) and approval[k]
                    for k in ("approved_by", "challenged_by")
                )
                and approval["approved_by"] != approval["challenged_by"]
            )
        restriction = policy.get("temporary_restrictions", {}).get(request["principal"])
        if restriction and _time(restriction["valid_from"]) <= _time(d["evaluated_at"]) < _time(
            restriction["valid_until"]
        ):
            checks["temporary_peer_initiation"] = (
                request.get("initiated_by") in restriction["permitted_peer_initiators"]
            )
        decision = "ALLOW" if all(checks.values()) else "DENY"
        fact = {
            "source": custody(row),
            "policy": custody(policies[0]),
            "boundary_checks": checks,
            "independent_local_decision": decision,
            "reported_decision": d.get("decision"),
            "claim_agrees": decision == d.get("decision"),
            "actual_identity_provider_login": False,
        }
        if not fact["claim_agrees"]:
            exceptions.append(fact)
        results.append(fact)
    return {
        "selected_attempts": results,
        "exceptions": exceptions,
        "key_custody_declarations": _pick(
            history.select("supplementalops", {"key_custody"}),
            [
                "key_id",
                "custodian",
                "custody_controls",
                "production_use",
                "credential_lifecycle",
                "private_material_in_receipt",
            ],
        ),
        "production_secret_retrieval_or_crypto_execution_performed": False,
    }


def addressable(history):
    decisions = history.select("supplementalops", {"risk_decision"})
    settings = history.select("supplementalops", {"security_configuration"})
    cases, exceptions = [], []
    for spec in sorted(ADDRESSABLE):
        matches = [r for r in decisions if detail(r).get("specification") == spec]
        occurrences = []
        for row in matches:
            d = detail(row)
            assessment = d.get("assessment", {})
            fields = (
                "size_complexity_capability",
                "infrastructure",
                "cost",
                "probability_and_criticality",
            )
            assessment_present = isinstance(assessment, dict) and all(
                isinstance(assessment.get(k), str) and assessment[k].strip() for k in fields
            )
            reasoning = isinstance(d.get("reasoned_treatment"), str) and bool(
                d["reasoned_treatment"].strip()
            )
            configured = []
            for setting in settings:
                sd = detail(setting)
                pointer = sd.get("implementation_decision_original")
                target, status = (
                    history.resolve(
                        setting,
                        pointer,
                        expected={"supplementalops.risk_decision"},
                        at=sd.get("applied_at", setting["source"]["event_at"]),
                    )
                    if isinstance(pointer, dict)
                    else (None, "EXACT_DECISION_REFERENCE_ABSENT")
                )
                if target and key(target["source"]) == key(row["source"]):
                    configured.append(
                        {
                            "source": custody(setting),
                            "reference_status": status,
                            "approved_observed_equal": isinstance(sd.get("approved_values"), dict)
                            and bool(sd["approved_values"])
                            and _json(sd["approved_values"]) == _json(sd.get("observed_values")),
                            "specification_matches_decision": sd.get("specification") == spec,
                            "recorded_application_time_supported": _observed_at(
                                setting, sd.get("applied_at")
                            ),
                            "activation_scope": sd.get("activation_scope"),
                        }
                    )
            fact = {
                "source": custody(row),
                "assessment_fields_present": assessment_present,
                "specific_reasoning_present": reasoning,
                "decision": d.get("decision"),
                "equivalent_alternative": d.get("equivalent_alternative"),
                "exact_implemented_setting_versions": configured,
                "missing_implemented_setting": d.get("decision") == "IMPLEMENT_IN_LOCAL_MODEL"
                and not configured,
                "actual_environment_reasonableness_accepted": False,
            }
            if (
                not assessment_present
                or not reasoning
                or fact["missing_implemented_setting"]
                or any(
                    not s["approved_observed_equal"]
                    or not s["specification_matches_decision"]
                    or not s["recorded_application_time_supported"]
                    for s in configured
                )
            ):
                exceptions.append(fact)
            occurrences.append(fact)
        cases.append(
            {
                "specification": spec,
                "decision_versions": occurrences,
                "missing_decision": not matches,
            }
        )
    return {
        "authored_baseline_22_specification_census": cases,
        "exceptions": exceptions,
        "missing_specifications": [c["specification"] for c in cases if c["missing_decision"]],
        "generic_waiver_not_substituted_for_assessment": True,
        "actual_legal_applicability_accepted": False,
    }


def transfers(history):
    cases, exceptions = [], []
    for row in history.select("sec001transfer", {"transfer_operations"}):
        d = detail(row)
        declared, resolved, by_label, unavailable = {}, [], {}, []
        pending, visited = [row], {key(row["source"])}
        while pending:
            consumer = pending.pop()
            for label, ref in consumer["document"].get("record_links", {}).items():
                target, status = history.resolve(
                    consumer, ref, expected=expected_role(consumer, "$.record_links." + label)
                )
                if target is None:
                    unavailable.append(
                        {"consumer": custody(consumer), "label": label, "status": status}
                    )
                    continue
                by_label.setdefault(label, []).append(target)
                if key(target["source"]) not in visited:
                    visited.add(key(target["source"]))
                    resolved.append(target)
                    pending.append(target)
        for label, roles in {
            "PURPOSE": {"sec001transfer.transfer_authority"},
            "RECIPIENT": {"sec001transfer.transfer_authority"},
            "CHANNEL": {"sec001transfer.security_path"},
            "ENDPOINT": {"sec001transfer.security_path"},
        }.items():
            candidates = {
                key(r["source"]): r
                for r in by_label.get(label, [])
                if r["source"]["system"] in roles
            }
            declared[label] = (
                "EXACT_AVAILABLE_ORIGINAL"
                if len(candidates) == 1
                else ("EXACT_PATH_ORIGINAL_ABSENT_OR_AMBIGUOUS")
            )
        recipient = {key(r["source"]): r for r in by_label.get("RECIPIENT", [])}
        endpoint = {key(r["source"]): r for r in by_label.get("ENDPOINT", [])}
        recipient = next(iter(recipient.values())) if len(recipient) == 1 else None
        endpoint = next(iter(endpoint.values())) if len(endpoint) == 1 else None
        payloads = {detail(r).get("payload_sha256") for r in [row, *resolved]}
        fact = {
            "source": custody(row),
            "declared_path_status": declared,
            "path_originals": [custody(r) for r in resolved],
            "declared_payload_digests_agree": len(payloads) == 1 and None not in payloads,
            "actor_id": row["document"].get("actor_id"),
            "self_approval_allowed": d.get("self_approval_allowed"),
            "indirect_path_support": unavailable,
            "recorded_endpoint_matches_recipient_authorization": (
                detail(recipient).get("approved_fixture_endpoint")
                == detail(endpoint).get("endpoint_fixture")
                if recipient and endpoint
                else None
            ),
            "observed_recipient_matches_authority": (
                d.get("recipient_fixture") == detail(recipient).get("recipient_id")
                if recipient and "recipient_fixture" in d
                else None
            ),
            "real_network_transfer_reperformed": False,
            "transport_description_is_not_recipient_authorization": True,
        }
        if (
            not fact["declared_payload_digests_agree"]
            and resolved
            or fact["recorded_endpoint_matches_recipient_authorization"] is False
            or fact["observed_recipient_matches_authority"] is False
            or d.get("self_approval_allowed") is True
        ):
            exceptions.append(fact)
        cases.append(fact)
    return {
        "selected_operations": cases,
        "exceptions": exceptions,
        "purpose_recipient_channels": _pick(
            history.select("sec001transfer", {"transfer_authority", "security_path"}),
            ["purpose", "recipient_id", "local_decision", "channel_fixture", "endpoint_fixture"],
        ),
        "receipt_handling": _pick(
            history.select("sec001transfer", {"receipt_handling"}),
            [
                "received_payload_sha256",
                "payload_sha256",
                "retention_label",
                "actual_receipt",
                "actual_storage_or_deletion",
            ],
        ),
    }


def integrity_movement(history):
    population = history.select("supplementalops", {"workstation_inventory"})
    movements = []
    for row in history.select("supplementalops", {"media_movement"}):
        d = detail(row)
        effective = _effective(population, row["source"]["event_at"], history)
        ids = {a["asset_id"] for r in effective for a in detail(r).get("resources", [])}
        assets = d.get("assets", d.get("asset_ids", [d["asset_id"]] if "asset_id" in d else []))
        declared = {a["asset_id"] if isinstance(a, dict) else a for a in assets}
        movements.append(
            {
                "source": custody(row),
                "unjoined_assignment_assets": sorted(declared - ids),
                "effective_assignment_originals": [custody(r) for r in effective],
                "departure": d.get("departed_at"),
                "received_at": d.get("received_at"),
                "copy_receipt_id": d.get("exact_copy_receipt_id"),
                "preserved_sha256_claim": d.get("preserved_sha256"),
                "exact_pre_movement_source_copy_retrieved": False,
            }
        )
    return {
        "independent_assignment_population": _pick(
            population, ["resources", "source_of_population", "scope_exclusion"]
        ),
        "movement_and_reuse_versions": movements,
        "maintenance": _pick(
            history.select("supplementalops", {"facility_maintenance"}),
            ["asset_id", "repair", "problem", "authorized_by"],
        ),
        "alteration_authority_and_company_observations": _pick(
            history.select("supplementalops", {"integrity_operation"}),
            [
                "permitted_action",
                "test_scope",
                "expected_source_sha256",
                "expected_authenticator",
                "response_requirement",
                "detected",
                "response",
                "verification",
            ],
        ),
        "independent_unauthorized_alteration_injection_and_transfer_performed": False,
        "fixture_path_or_digest_claim_does_not_supply_collected_original_bytes": True,
    }


def incidents(history, permissions):
    rows = history.select("supplementalops", {"incident_intake"})
    attempts = []
    for row in rows:
        d = detail(row)
        support = []
        for ref in d.get("native_dependencies", []):
            target, status = history.resolve(
                row, ref, expected={"supplementalops.access_operation"}
            )
            if target:
                calculated = next(
                    (
                        p.get("independent_local_decision")
                        for p in permissions["selected_attempts"]
                        if key(p["source"]) == key(target["source"])
                    ),
                    None,
                )
                support.append(
                    {
                        "source": custody(target),
                        "role": target["logical_system"],
                        "reported_access_decision": detail(target).get("decision"),
                        "independent_local_access_decision": calculated,
                    }
                )
        includes_attempts = d.get("security_incident_definition_includes_attempts")
        require(
            includes_attempts is None or type(includes_attempts) is bool,
            "Strict incident attempted-access rule flag required",
        )
        denied = any(s["independent_local_access_decision"] == "DENY" for s in support)
        attempts.append(
            {
                "source": custody(row),
                "intake_type": d.get("intake_type"),
                "includes_attempts": includes_attempts,
                "bounded_rule_reperformance": (
                    "ATTEMPT_INCLUDED_BY_DECLARED_LOCAL_INTAKE_RULE"
                    if includes_attempts is True and denied
                    else "SUPPORTED_ACCESS_ATTEMPT_NOT_CLASSIFIED_WITHOUT_RULE_OR_DECISION"
                ),
                "triage_statement": d.get("triage"),
                "response_statement": d.get("response"),
                "original_support": support,
                "enterprise_severity_classification_reperformed": False,
                "independent_containment_actions_performed": False,
            }
        )
    return {
        "dated_intakes": attempts,
        "dismissed_event_denominator_established": False,
        "closed_alerts_not_automatically_accepted_as_incidents_or_resolved_risk": True,
    }


def boundary_checks(history):
    results, exceptions = [], []
    for row in history.select("sec005", {"local_boundary_decision"}):
        d = detail(row)
        # Native source_previous is a preserved original pointer; never choose a latest rule.
        target, status = _joined(
            history, row, "source_previous", {"sec005.local_boundary_definition"}
        )
        fact = {
            "source": custody(row),
            "rule_original_status": status,
            "actual_connection_attempted": False,
        }
        if target:
            rule = detail(target)
            intended = _ids(rule.get("intended_permitted_interface_ids", []))
            staged = _ids(rule.get("staged_rule_permitted_interface_ids", []))
            request = d.get("requested_interface_id")
            fact.update(
                rule=custody(target),
                requested_interface=request,
                intended_permitted=request in intended,
                staged_permitted=request in staged,
                rule_drift=intended != staged,
                company_decision=d.get("decision"),
            )
            if intended != staged or (request in staged) != (request in intended):
                exceptions.append(fact)
        results.append(fact)
    endpoint = []
    for row in history.select("sec005", {"local_endpoint_decision"}):
        d = detail(row)
        digests = [d.get(k) for k in ("fixture_sha256", "approved_fixture_sha256")]
        typed = all(
            isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)
            for v in digests
        )
        fact = {
            "source": custody(row),
            "typed_fixture_and_approved_digests_present": typed,
            "declared_fixture_digest_equals_approved": digests[0] == digests[1] if typed else None,
            "company_decision": d.get("decision"),
            "actual_executable_bytes_created_or_run": False,
        }
        if typed and not fact["declared_fixture_digest_equals_approved"]:
            exceptions.append(fact)
        endpoint.append(fact)
    return {
        "symbolic_interface_attempts": results,
        "inert_digest_decisions": endpoint,
        "exceptions": exceptions,
        "full_external_interface_discovery_reconciled": False,
    }


def approvals(history):
    rows = history.select("sec005operated", {"security_approval"})
    facts = []
    for application in history.select("sec005operated", {"security_application"}):
        approved = []
        pending, visited, unavailable = [application], set(), []
        while pending:
            consumer = pending.pop()
            for _, pointer in pointers(consumer["document"].get("source_refs", {})):
                target, status = history.resolve(consumer, pointer)
                if target is None:
                    unavailable.append({"consumer": custody(consumer), "status": status})
                    continue
                target_key = key(target["source"])
                if target_key in visited:
                    continue
                visited.add(target_key)
                if target["source"]["system"] == "sec005operated.security_approval":
                    approved.append(target)
                    pending.append(target)
                elif target["source"]["system"] == "sec005operated.security_baseline":
                    pending.append(target)
        actors = [r["document"].get("actor_id") for r in approved]
        facts.append(
            {
                "source": custody(application),
                "exact_prior_approval_originals": [custody(r) for r in approved],
                "recorded_approvers": actors,
                "distinct_named_approvers": all(isinstance(a, str) and a for a in actors)
                and len(set(actors)) == len(actors)
                and len(actors) > 1,
                "unavailable_approval_chain_support": unavailable,
                "operator_distinct_from_approvers": application["document"].get("actor_id")
                not in actors
                if actors
                else None,
                "canon_scoped_professional_approval_accepted": False,
            }
        )
    return {
        "application_authority_attributes": facts,
        "approval_versions": _pick(
            rows,
            [
                "actor_id",
                "decision",
                "technology_approver_person_id",
                "security_reviewer_person_id",
            ],
        ),
        "recorded_approval_does_not_appoint_an_independent_assurance_reviewer": True,
    }


def physical_conditions(history):
    """Recompute selected recorded site attributes; no real controller is read."""
    badge, visits, environment, exceptions = [], [], [], []

    def prior(row, role, record):
        candidates = [
            r
            for r in history.select("physicalsite", {role})
            if r["source"]["record"] == record
            and _time(r["source"]["available_at"]) <= _time(row["source"]["event_at"])
        ]
        return candidates[0] if len(candidates) == 1 else None

    for row in history.select("physicalsite", {"badge_lifecycle"}):
        d = detail(row)
        if "badge" not in d:
            badge.append({"source": custody(row), "attributes": d, "kind": "ISSUANCE"})
            continue
        original = prior(row, "badge_lifecycle", d["badge"])
        fact = {
            "source": custody(row),
            "issuance": custody(original) if original else None,
            "kind": "BADGE_REVOCATION",
            "effective_at": d.get("effective_at"),
            "recorded_controller_state": d.get("controller_state"),
            "recorded_revocation_disabled": d.get("controller_state") == "DISABLED",
            "actual_controller_state_verified": False,
        }
        if "effective_at" in d:
            fact["effective_before_recorded_observation"] = _time(d["effective_at"]) <= _time(
                row["source"]["event_at"]
            )
        if not fact["recorded_revocation_disabled"]:
            exceptions.append(fact)
        badge.append(fact)
    for row in history.select("physicalsite", {"visitor_access"}):
        d = detail(row)
        if "authorization" not in d:
            visits.append({"source": custody(row), "attributes": d, "kind": "AUTHORIZATION"})
            continue
        original = prior(row, "visitor_access", d["authorization"])
        valid = (
            _time(row["source"]["event_at"]) <= _time(detail(original)["valid_until"])
            if original and "valid_until" in detail(original)
            else None
        )
        entry = d.get("entry", d.get("controller_entry"))
        escorted = entry == "ESCORTED" or (
            d.get("escort") is not None and d.get("escort") != "NONE"
        )
        fact = {
            "source": custody(row),
            "authorization_original": custody(original) if original else None,
            "kind": "VISITOR_ENTRY",
            "recorded_entry": entry,
            "authorization_current_at_recorded_entry": valid,
            "explicit_recorded_escort": escorted,
            "recorded_exit_confirmed": d.get("exit_confirmed"),
            "actual_badge_reader_or_person_observed": False,
        }
        if entry in {"ALLOWED", "REPORTED_ESCORTED", "ESCORTED"} and (
            valid is False or not escorted
        ):
            exceptions.append(fact)
        visits.append(fact)
    for row in history.select("physicalsite", {"environment_monitor"}):
        d = detail(row)
        if "observed_c" not in d:
            continue
        original = prior(row, "environment_monitor", d.get("point"))
        limit = detail(original).get("threshold_c") if original else None
        observed = d["observed_c"]
        typed = type(observed) in {int, float} and type(limit) in {int, float}
        fact = {
            "source": custody(row),
            "point_definition": custody(original) if original else None,
            "kind": "ENVIRONMENTAL_THRESHOLD",
            "recorded_temperature_c": observed,
            "effective_point_threshold_c": limit,
            "recorded_threshold_breach": observed > limit if typed else None,
            "company_recorded_alarm_state": d.get("state"),
            "company_reported_alarm_cleared": d.get("local_alarm_cleared"),
            "actual_sensor_or_provider_recovery_tested": False,
        }
        if fact["recorded_threshold_breach"]:
            exceptions.append(fact)
        environment.append(fact)
    return {
        "zoning_and_delegation_versions": _pick(
            history.select("physicalsite", {"site_zoning", "site_authority"}),
            ["site", "zone", "entry_rule", "scope", "delegated_to", "expires_at"],
        ),
        "badge_issuance_and_revocation_occurrences": badge,
        "visitor_authorization_entry_exit_occurrences": visits,
        "environmental_threshold_occurrences": environment,
        "environmental_response_versions": _pick(
            history.select("physicalsite", {"environment_response"}),
            ["alarm", "action", "actual_provider_action", "authorized_entry"],
        ),
        "exceptions": exceptions,
        "access_exceptions": [e for e in exceptions if e["kind"] != "ENVIRONMENTAL_THRESHOLD"],
        "environmental_exceptions": [
            e for e in exceptions if e["kind"] == "ENVIRONMENTAL_THRESHOLD"
        ],
        "provider_perimeter_and_full_site_population_established": False,
        "earlier_breach_not_erased_by_later_alarm_recheck": True,
    }


def vulnerability_attributes(history):
    snapshots, corrections = [], []
    for row in history.select("sec003vuln", {"vulnerability_scan"}):
        d = detail(row)
        observed, found = (
            _ids(d.get("observed_asset_ids", [])),
            _ids(d.get("finding_asset_ids", [])),
        )
        for field in ("observed_count", "reported_count"):
            require(
                field not in d or type(d[field]) is int and d[field] >= 0,
                "Strict recorded vulnerability count required",
            )
        snapshots.append(
            {
                "source": custody(row),
                "observed_asset_ids": sorted(observed),
                "finding_asset_ids": sorted(found),
                "findings_outside_scan": sorted(found - observed),
                "count_claims": {
                    k: {
                        "reported": d[k],
                        "recomputed": len(observed),
                        "agrees": d[k] == len(observed),
                    }
                    for k in ("observed_count", "reported_count")
                    if k in d
                },
            }
        )
    for row in history.select(
        "sec003vuln",
        {
            "vulnerability_triage",
            "vulnerability_approval",
            "vulnerability_remediation",
            "vulnerability_exception",
        },
    ):
        d = detail(row)
        corrections.append(
            {
                "source": custody(row),
                "asset_id": d.get("asset_id"),
                "advisory_id": d.get("advisory_id"),
                "disposition": d.get("disposition"),
                "expires_at": d.get("expires_at"),
                "severity_sla_due_at": (
                    "UNPERFORMED_WITHOUT_EXACT_APPROVED_SEVERITY_EXPLOITABILITY_SLA_ORIGINAL"
                ),
                "historical_failures_not_erased_by_latest_retest": True,
            }
        )
    return {
        "dated_scan_populations": snapshots,
        "correction_acceptance_and_sla_attributes": corrections,
        "independent_live_scanner_or_severity_assignment_performed": False,
    }


def _evidence(rows, locator="$"):
    require(0 < len(rows) <= 20, "Explicit complete citation part must fit writer limit")
    return [
        {"artifact_id": r["artifact_id"], "sha256": r["artifact_sha256"], "locator": locator}
        for r in rows
    ]


def _observation(label, facts, rows, status="OBSERVED"):
    return {"id": label, "facts": facts, "status": status, "evidence": _evidence(rows)}


def _aggregate(label, facts, rows, status="OBSERVED"):
    """All direct citations extend the same aggregate; none are silently omitted."""
    chunks = [rows[n : n + 20] for n in range(0, len(rows), 20)]
    ids = [label] + [f"{label}-CITE-{n + 1:04d}" for n in range(1, len(chunks))]
    observations = []
    for n, chunk in enumerate(chunks):
        linked = {
            "aggregate_observation_id": label,
            "citation_part_index": n + 1,
            "citation_part_count": len(chunks),
            "all_citation_part_ids": ids,
            "this_part_extends_aggregate_direct_citations": True,
        }
        part_facts = (
            {**facts, "citation_group": linked}
            if n == 0
            else {
                "citation_group": linked,
                "source_custody_subset": [custody(r) for r in chunk],
                "aggregate_facts_held_in_observation": label,
            }
        )
        observations.append(_observation(ids[n], part_facts, chunk, status))
    require(
        observations and all(len(o["id"]) <= 128 for o in observations),
        "Complete aggregate citations and bounded IDs required",
    )
    return observations


def _sec005_exceptions(result):
    if result.get("schema") != "SH_LIBRARY_SEC005_PUBLISHER_REPERFORMANCE_V1":
        return []
    failures = [
        r
        for r in result["monitor_reconciliations"]
        if r["unreceived_publisher_ids"]
        or r["collector_without_publisher_ids"]
        or r["missing_required_agent_assets"]
        or r["unjoined_agent_assets"]
        or r["publisher_claim_disagrees"] is True
    ] + [
        r
        for r in result["company_review_reconciliations"]
        if r["unreviewed_publisher_ids"] or r["reviewed_unjoined_ids"]
    ]
    if (
        not result["initial_application_matches_approved_rules"]
        or result["initial_missing_required_agent_assets"]
        or not result["selected_approvals_available_before_application"]
    ):
        failures.append(
            {
                "source": result["application"],
                "initial_application_matches_approved_rules": result[
                    "initial_application_matches_approved_rules"
                ],
                "missing_agent_assets": result["initial_missing_required_agent_assets"],
                "approval_clock_supported": result[
                    "selected_approvals_available_before_application"
                ],
            }
        )
    return failures


def _sec003_exceptions(result):
    if result.get("schema") != "SH_LIBRARY_SEC003_REPERFORMANCE_V1":
        return []
    failures = list(result["count_contradictions"])
    if (
        result["omitted_scan_assets"]
        or result["causal_discrepancy"]["disposition"]
        in {"UNEXPLAINED_FALSE_CLEAN", "MISSED_ADVISORY_AND_COVERAGE_GAP_NO_PROVEN_CAUSE"}
        or not result["approval_fix_retest_chronology_supported"]
    ):
        failures.append(
            {
                "source": result["upstream_inventory"],
                "omitted_scan_assets": result["omitted_scan_assets"],
                "advisory_discrepancy": result["causal_discrepancy"],
                "approval_fix_retest_chronology_supported": result[
                    "approval_fix_retest_chronology_supported"
                ],
            }
        )
    return failures


def _task_facts(task, calculations):
    control, clause = task["control_id"], task["task_id"].split("-corporate-", 1)[1]
    (
        cfg,
        selected,
        comp,
        logs,
        permissions,
        addr,
        transfer,
        movement,
        intake,
        boundary,
        authority,
        vuln,
        physical,
    ) = calculations
    if control == "SH-CFG-001":
        return (
            {
                "TOD": {
                    "owned_inventory_design": cfg["inventory_versions"],
                    "independent_discovery_design": cfg["independent_selected_discoveries"],
                },
                "IMPLEMENTATION": {
                    "dated_inventory_versions": cfg["inventory_versions"],
                    "actual_exported_targets": cfg["actual_raw_export_reperformance"],
                    "independent_component_discovery": comp["populations"],
                },
                "TOE": {
                    "inventory_discovery_reconciliation": cfg["independent_selected_discoveries"],
                    "component_ownership_mapping_census": comp["populations"],
                    "full_year_onboarding_change_retirement_denominator": "UNPERFORMED",
                },
            }[clause],
            [],
            {
                "configuration-history",
                "configuration-runtime-history",
                "sec001component",
                "sec005operated",
            },
        )
    if control == "SH-CFG-002":
        return (
            {
                "TOD": {
                    "baseline_versions_and_authority": authority,
                    "effective_local_configuration_design": cfg["inventory_versions"],
                },
                "IMPLEMENTATION": {
                    "exact_native_embedded_drift": cfg["embedded_drift_comparisons"],
                    "raw_runtime_exports": cfg["actual_raw_export_reperformance"],
                    "local_operation_history": cfg["operation_versions"],
                },
                "TOE": {
                    "dated_drift_and_export_occurrences": cfg,
                    "late_corrections_do_not_recreate_earlier_originals": True,
                },
                "CHECK-SOC2:CC5.2": {"technology_component_lifecycle_reconciliation": comp},
                "CHECK-SOC2:CC6.8": {
                    "selected_endpoint_publisher_reconciliation": selected["SEC005"],
                    "local_inert_digest_tests": boundary["inert_digest_decisions"],
                    "actual_unapproved_executable_test": "UNPERFORMED",
                },
                "CHECK-SOC2:CC7.1": {
                    "inventory_scan_baseline_calculation": selected["SEC003"],
                    "drift_and_source_availability": cfg["embedded_drift_comparisons"],
                },
            }[clause],
            cfg["exceptions"]
            if clause in {"IMPLEMENTATION", "TOE"}
            else comp["exceptions"]
            if clause.endswith("CC5.2")
            else [],
            {
                "configuration-history",
                "configuration-runtime-history",
                "sec005operated",
                "sec003vuln",
                "sec001component",
            },
        )
    if control == "SH-SEC-001":
        return (
            {
                "TOD": {
                    "architecture_component_and_transfer_declarations": comp,
                    "trust_and_key_design": permissions["key_custody_declarations"],
                    "addressable_environmental_design": addr,
                },
                "IMPLEMENTATION": {
                    "dated_transfer_and_component_implementation": transfer,
                    "local_trust_boundary_reperformance": permissions,
                    "implemented_addressable_setting_links": addr,
                },
                "TOE": {
                    "dated_permission_attempts": permissions["selected_attempts"],
                    "dated_transfer_versions": transfer["selected_operations"],
                    "component_exception_history": comp["historical_exception_versions"],
                },
                "ACTION-H-ADDRESSABLE": {
                    "independent_authored_22_specification_reconciliation": addr
                },
                "ACTION-H-INTEGRITY": {
                    "authorized_alteration_and_response_declarations": movement[
                        "alteration_authority_and_company_observations"
                    ],
                    "actual_copy_and_transfer_injection": (
                        "UNPERFORMED_WITHOUT_COLLECTED_SOURCE_PAYLOAD_AND_VERIFICATION_MATERIAL"
                    ),
                },
                "ACTION-H-PHYSICAL-MOVEMENT": {
                    "independent_assignments_movement_and_pre_copy_retrieval": movement
                },
                "CHECK-SOC2:A1.2": {
                    "independent_dated_environmental_threshold_analysis": {
                        k: physical[k]
                        for k in (
                            "environmental_threshold_occurrences",
                            "environmental_response_versions",
                            "environmental_exceptions",
                            "earlier_breach_not_erased_by_later_alarm_recheck",
                        )
                    },
                    "site_failure_backup_recoverability_capacity": "UNPERFORMED",
                },
                "CHECK-SOC2:CC5.2": {
                    "selected_technology_and_outsourced_component_lifecycle": comp
                },
                "CHECK-SOC2:CC6.1": {
                    "independent_local_human_service_and_privilege_checks": permissions
                },
                "CHECK-SOC2:CC6.4": {
                    "site_zoning_visitors_escort_revocation_and_provider_sources": {
                        k: physical[k]
                        for k in (
                            "zoning_and_delegation_versions",
                            "badge_issuance_and_revocation_occurrences",
                            "visitor_authorization_entry_exit_occurrences",
                            "access_exceptions",
                            "provider_perimeter_and_full_site_population_established",
                        )
                    },
                    "logical_iam_does_not_establish_physical_assurance": True,
                },
                "CHECK-SOC2:CC6.7": {
                    "purpose_recipient_channel_endpoint_and_receipt_trace": transfer
                },
            }[clause],
            addr["exceptions"]
            if clause.endswith("ADDRESSABLE")
            else permissions["exceptions"]
            if clause.endswith("CC6.1")
            else comp["exceptions"]
            if clause.endswith("CC5.2")
            else transfer["exceptions"]
            if clause.endswith("CC6.7")
            else physical["environmental_exceptions"]
            if clause == "CHECK-SOC2:A1.2"
            else physical["access_exceptions"]
            if clause == "CHECK-SOC2:CC6.4"
            else [],
            {
                "sec001component",
                "sec001transfer",
                "supplementalops",
                "physicalsite",
                "transition",
                "integrity",
            },
        )
    if control == "SH-SEC-002":
        return (
            {
                "TOD": {
                    "required_source_detection_collector_and_clock_design": logs[
                        "checkpoint_populations_before_selection"
                    ]
                },
                "IMPLEMENTATION": {"actual_native_publisher_ingestion_and_alert_routing": logs},
                "TOE": {
                    "dated_checkpoint_and_gap_populations": logs,
                    "selected_publisher_vs_collector_review": selected["SEC005"],
                },
                "ACTION-H-ACTIVITY-REVIEW": {
                    "independently_recomputed_dated_local_activity_gaps": logs,
                    "actual_anomaly_disposition": intake,
                    "no_stored_SQL_execution": True,
                },
                "CHECK-SOC2:CC7.2": {
                    "source_loss_and_detection_rule_analysis": logs,
                    "healthy_collection_does_not_imply_examined_alerts": True,
                },
            }[clause],
            logs["exceptions"] if clause != "TOD" else [],
            {"logging-history", "baseline-logging", "sec005operated", "supplementalops"},
        )
    if control == "SH-SEC-003":
        return (
            {
                "TOD": {
                    "inventory_scan_schedule_and_advisory_design": selected["SEC003"],
                    "severity_exploitability_and_expiry_attributes": vuln[
                        "correction_acceptance_and_sla_attributes"
                    ],
                },
                "IMPLEMENTATION": {
                    "coverage_finding_fix_approval_and_rescan": selected["SEC003"],
                    "original_scan_and_correction_versions": vuln,
                },
                "TOE": {
                    "selected_asset_census_and_dated_scan_populations": selected["SEC003"],
                    "dated_correction_sla_and_exception_tests": vuln,
                },
                "CHECK-SOC2:CC7.1": {
                    "accepted_pure_selected_inventory_scan_baseline_reperformance": selected[
                        "SEC003"
                    ],
                    "independent_severity_SLA_and_live_scanner_testing": "UNPERFORMED",
                },
            }[clause],
            _sec003_exceptions(selected["SEC003"]),
            {"sec003vuln", "sec005operated"},
        )
    if control == "SH-SEC-005":
        return (
            {
                "TOD": {
                    "effective_rules_approvals_and_declared_external_interfaces": authority,
                    "selected_security_baseline_and_application": selected["SEC005"],
                },
                "IMPLEMENTATION": {
                    "actual_raw_configuration_exports_and_local_model_probes": cfg[
                        "actual_raw_export_reperformance"
                    ],
                    "selected_enforcement_populations": selected["SEC005"],
                    "symbolic_boundary_reperformance": boundary,
                },
                "TOE": {
                    "dated_publisher_monitor_review_and_exception_history": selected["SEC005"],
                    "raw_configuration_drift_history": cfg["embedded_drift_comparisons"],
                    "symbolic_decision_history": boundary,
                },
                "CHECK-SOC2:CC6.6": {
                    "approved_intended_vs_staged_interface_attempts": boundary,
                    "selected_publisher_coverage": selected["SEC005"],
                    "actual_unauthorized_network_connection": "UNPERFORMED",
                },
                "CHECK-SOC2:CC6.8": {
                    "inert_executable_digest_decisions": boundary["inert_digest_decisions"],
                    "required_agent_and_publisher_coverage": selected["SEC005"],
                    "representative_updates_and_actual_unapproved_executable": "UNPERFORMED",
                },
            }[clause],
            _sec005_exceptions(selected["SEC005"]) + boundary["exceptions"]
            if clause in {"IMPLEMENTATION", "TOE", "CHECK-SOC2:CC6.6"}
            else _sec005_exceptions(selected["SEC005"])
            if clause == "CHECK-SOC2:CC6.8"
            else [],
            {"sec005", "sec005operated", "configuration-runtime-history", "configuration-history"},
        )
    return (
        {
            "TOD": {"incident_including_attempted_access_and_preservation_design": intake},
            "IMPLEMENTATION": {
                "dated_alert_ingestion_routing_and_intake": logs["alert_routing"],
                "native_impact_and_response_evidence": intake,
            },
            "TOE": {
                "selected_alert_responses_and_review_versions": logs["response_and_review"],
                "dated_incident_intakes": intake["dated_intakes"],
                "closed_alert_and_dismissed_event_denominator": "UNPERFORMED",
            },
            "CHECK-SOC2:CC7.3": {
                "original_impact_attempted_access_and_response_attributes": intake,
                "accepted_escalation_criteria_and_authority_classification": (
                    "UNPERFORMED_WITHOUT_COMPLETE_SCOPED_CRITERIA_AND_DISMISSED_EVENT_POPULATION"
                ),
            },
        }[clause],
        [],
        {"logging-history", "baseline-logging", "supplementalops"},
    )


def examine(records, *, as_of, scratch_root):
    """Data-only callback. scratch_root is intentionally not opened or written."""
    tasks, task_contracts = task_plan(), contracts()
    history = History(records, as_of=as_of)
    permissions = permission_checks(history)
    calculations = (
        configuration(history),
        selected_calculations(history),
        component_lifecycle(history),
        logging(history),
        permissions,
        addressable(history),
        transfers(history),
        integrity_movement(history),
        incidents(history, permissions),
        boundary_checks(history),
        approvals(history),
        vulnerability_attributes(history),
        physical_conditions(history),
    )
    outputs = []
    for task in tasks:
        facts, exceptions, families = _task_facts(task, calculations)
        rows = history.supported_rows(facts)
        missing = not rows
        formats = history.format_limitations(families)
        if not rows:
            rows = [r for r in history.rows if r["logical_family"] in families]
        else:
            included = {key(r["source"]) for r in rows}
            rows.extend(
                r
                for r in history.rows
                if r["logical_family"] in families
                and not isinstance(r["document"], dict)
                and key(r["source"]) not in included
            )
        rows = rows or history.rows[:1]
        while True:
            included = {key(r["source"]) for r in rows}
            joins = [j for j in history.joins if key(j["origin"]) in included]
            targets = {
                key(ref)
                for j in joins
                for ref in (j["target"], j.get("retained_unstructured_original"))
                if ref is not None
            }
            linked = [r for r in history.rows if key(r["source"]) in targets - included]
            if not linked:
                break
            rows.extend(linked)
        formats = history.format_limitations(None, rows=rows)
        observations = _aggregate(
            "EXACT-TASK-ATTRIBUTES",
            {
                "authored_instruction": task["authored_instruction"],
                "task_kind_rule": task["task_kind_rule"],
                "examined_attributes": facts,
                "bounded_exceptions": exceptions,
                "retained_format_limitations": formats,
                "full_clause_performed": False,
            },
            rows,
            "EXCEPTION_RECORDED"
            if exceptions
            else "SUPPORT_UNAVAILABLE"
            if missing
            else "OBSERVED",
        )
        # Every selected native version is a separate bounded documentary occurrence.
        for number, row in enumerate(rows):
            observations.append(
                _observation(
                    f"ACQUISITION-CONTEXT-{number + 1:04d}"
                    if missing
                    else f"NATIVE-OCCURRENCE-{number + 1:04d}",
                    {
                        "source": custody(row),
                        "native_role": row["source"]["system"],
                        "actual_retained_bytes_reparsed": True,
                        "full_period_completeness_not_asserted": True,
                        "document_format": row["document_format"],
                        "task_specific_attributes_supported": not missing
                        and isinstance(row["document"], dict),
                        "structured_attribute_examination": "UNPERFORMED"
                        if not isinstance(row["document"], dict)
                        else "BOUNDED_BY_EXACT_TASK_FACTS",
                    },
                    [row],
                    "SUPPORT_UNAVAILABLE" if not isinstance(row["document"], dict) else "OBSERVED",
                )
            )
        if joins:
            observations.extend(
                _aggregate(
                    "EXACT-NATIVE-SUPPORT",
                    {"joins": joins},
                    rows,
                    "SUPPORT_UNAVAILABLE"
                    if any(j["status"] != "EXACT_AVAILABLE_ORIGINAL" for j in joins)
                    else "OBSERVED",
                )
            )
        c = task_contracts[task["task_id"]]
        outputs.append(
            {
                "task_id": task["task_id"],
                "artifact_ids": [r["artifact_id"] for r in rows],
                "observations": observations,
                "performed": c["performed"],
                "unperformed": c["unperformed"],
                "result": {
                    "schema": "SH_COLLECTED_SECURITY_CONFIGURATION_TASK_EXAMINATION_V1",
                    "task_id": task["task_id"],
                    "authored_procedure": task["authored_procedure"],
                    "examined_attributes": facts,
                    "exceptions": exceptions,
                    "native_support": joins,
                    "retained_format_limitations": formats,
                    "selected_native_population_before_selection": [
                        custody(r) for r in rows if isinstance(r["document"], dict)
                    ]
                    if not missing
                    else [],
                    "acquisition_context_witnesses": [
                        custody(r) for r in rows if missing or not isinstance(r["document"], dict)
                    ],
                    "required_task_attribute_population_available": not missing,
                    "source_applicability_or_professional_assurance_accepted": False,
                    "prior_audit_or_Key_outcomes_used": False,
                    "broader_unperformed": BROAD,
                },
                "disposition": {
                    "status": "IN_PROGRESS",
                    "conclusion": "FAIL" if exceptions else "LIMITATION",
                    "rationale": (
                        "Bounded original-source exceptions and explicit broader "
                        "coverage limitations remain."
                    )
                    if exceptions
                    else (
                        "Exact retained source attributes examined with explicit "
                        "missing or broader unperformed scope."
                    ),
                },
            }
        )
    return outputs
