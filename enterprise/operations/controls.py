"""Reperformed synthetic control evidence; no claim of production effectiveness.

The registry is the existing business-interface registry. Expected occurrences are
scheduled independently of evidence availability. Population manifests identify
the complete scoped source slice by table, count and hash; the exported source
tables supply the underlying rows. Nothing here writes a ledger or approves a
real waiver, access grant, valuation, or business decision.
"""

from __future__ import annotations

import calendar
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNITS = (
    "foundry-field",
    "atlas-meridian",
    "advisory",
    "willow",
    "project-cradle",
    "pale-sun",
    "american-resource-utility",
    "corporate",
)
TABLES = (
    "control_registry",
    "control_occurrences",
    "control_population",
    "control_evidence",
    "control_results",
    "control_completeness",
    "control_exceptions",
    "control_actions",
    "control_retests",
)
REQUIRED = {
    "LC-REVENUE": ("journal", "events", "subledger_rollforward"),
    "LC-CREDIT": ("credit_history", "credit_allowance", "subledger_rollforward"),
    "LC-RECOVERY": ("recovery_run_assays", "recovery_genealogy", "inventory_rollforward"),
    "LC-TRANSFER": ("research_gate_evidence",),
    "LC-WORKFORCE": ("workforce_positions_history", "workforce_assignments", "journal", "events"),
    "LC-ESTIMATE": ("forecast_variance_contributions",),
    "LC-CONSOLIDATION": ("enterprise_unit_trial_balance", "enterprise_unit_statements"),
    "LC-ATLAS": ("matter_gate_decisions", "matter_controls"),
    "LC-INDUSTRIAL": (
        "industrial_service_detail",
        "industrial_shift_capacity",
        "industrial_detail_reconciliation",
    ),
    "LC-ADVISORY-VALUE": ("value_certifications", "matter_determinations"),
}
OPTIONAL = {
    "LC-REVENUE": ("invoices", "commercial_deferred_rollforward", "contract_versions"),
    "LC-CREDIT": ("credit_notes", "receivable_aging"),
    "LC-RECOVERY": ("recovery_custody", "host_collection_settlements"),
    "LC-TRANSFER": ("asset_rollforward",),
    "LC-WORKFORCE": ("workforce_changes",),
    "LC-ESTIMATE": (),
    "LC-CONSOLIDATION": ("replacement_bridge", "management_cost_reconciliation"),
    "LC-ATLAS": ("matter_handover_evidence",),
    "LC-INDUSTRIAL": ("industrial_maintenance_jobs",),
    "LC-ADVISORY-VALUE": ("matter_controls",),
}


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def date_for(month):
    year, m = 2027 + (month - 1) // 12, (month - 1) % 12 + 1
    return f"{year}-{m:02}-{calendar.monthrange(year, m)[1]}"


def _scope(row):
    scope = row["scope"]
    if scope == "all":
        return UNITS
    if scope == "commercial businesses":
        return tuple(u for u in UNITS if u not in {"corporate", "willow"})
    return tuple(scope.split(","))


def _registry():
    rows = json.loads((ROOT / "docs/structured/business-lines/interfaces.json").read_text())[
        "local_controls"
    ]
    if {r["id"] for r in rows} != set(REQUIRED) or len(rows) != len(REQUIRED):
        raise ValueError("Local control registry changed; review the executable mapping")
    return rows


def _period(row):
    if row.get("period"):
        return str(row["period"])[:7]
    if row.get("year") and row.get("month"):
        return f"{int(row['year'])}-{int(row['month']):02}"
    for key in ("month_index", "issue_month", "accrual_month", "capture_month"):
        if row.get(key):
            return date_for(int(row[key]))[:7]
    return ""


def _sources(model, result, extras):
    sources = {name: rows for name, rows in model.tables.items() if not name.startswith("control_")}
    sources["enterprise_unit_trial_balance"] = result.get("unit_rows", [])
    sources["enterprise_unit_statements"] = result.get("unit_monthly_rows", [])
    for name, rows in (extras or {}).items():
        if isinstance(rows, list):
            sources[name] = rows
    return sources


def _index(sources):
    """Index once; repeated monthly tests must not scan entire workforce/journals."""
    indexed = defaultdict(list)
    names = set(REQUIRED_NAME for v in REQUIRED.values() for REQUIRED_NAME in v)
    names.update(n for v in OPTIONAL.values() for n in v)
    for name in sorted(names):
        for row in sources.get(name, []):
            unit = row.get("reporting_unit", row.get("unit", ""))
            if unit not in UNITS:
                continue
            scenario, period = row.get("scenario", ""), _period(row)
            if scenario and period:
                indexed[name, str(scenario), period, unit].append(row)
    return indexed


def _slice(indexed, control, scenario, period, unit):
    return {
        name: indexed.get((name, scenario, period[:7], unit), [])
        for name in REQUIRED[control] + OPTIONAL[control]
    }


def _number(row, key):
    if key not in row or row[key] in (None, ""):
        raise KeyError(key)
    value = D(str(row[key]))
    if not value.is_finite():
        raise ValueError("Non-finite numeric evidence")
    return value


def _true(value):
    return value is True or str(value).lower() in {"true", "1"}


def _check(control, pops):
    """Return assertion failures and performed assertion count from source values.

    Unknown or incomplete enhanced-source schemas are NOT_RUN, never a fabricated
    PASS. Results carried in source rows are not accepted as test conclusions.
    """
    failures, checked = [], 0

    def require(condition, reason):
        nonlocal checked
        checked += 1
        if not condition:
            failures.append(reason)

    if control == "LC-REVENUE":
        balances = defaultdict(D)
        events = {r["event_id"]: r for r in pops["events"]}
        postings = defaultdict(D)
        for r in pops["journal"]:
            balances[r["journal_id"]] += _number(r, "signed_usd")
            require(r["source_id"] in events, "Journal lacks its originating event")
            if r["account"] == "BIZ_AR":
                postings[r["source_id"]] += _number(r, "signed_usd")
        require(
            all(v == 0 for v in balances.values()), "Revenue close contains an unbalanced journal"
        )
        for r in pops["events"]:
            if r["kind"] == "INVOICE":
                require(
                    postings[r["event_id"]] == _number(r, "amount_usd"),
                    "Invoice event does not match AR posting",
                )
                source = r.get("performance_source", "")
                contracts = {v["contract_id"] for v in pops["contract_versions"]}
                require(
                    source in events or any(source.startswith(cid + "-") for cid in contracts),
                    "Invoice lacks a scoped performance or versioned subscription-billing source",
                )
        for r in pops["subledger_rollforward"]:
            require(
                _number(r, "gross_ar_usd") >= 0 and _number(r, "deferred_revenue_usd") >= 0,
                "Negative AR or deferred revenue",
            )
        for r in pops["commercial_deferred_rollforward"]:
            if "difference_usd" in r:
                require(
                    _number(r, "difference_usd") == 0, "Deferred revenue reconciliation differs"
                )
    elif control == "LC-CREDIT":
        for r in pops["credit_history"]:
            # The core reconciliation is rederived, not accepted from a fixture PASS.
            if "invoice_amount_usd" in r:
                remaining = (
                    _number(r, "remaining_usd")
                    + _number(r, "collected_usd")
                    - _number(r, "refunded_usd")
                    + _number(r, "writtenoff_usd")
                    - _number(r, "recovered_usd")
                    - _number(r, "writtenoff_credit_usd")
                    + _number(r, "credit_usd")
                )
                require(
                    _number(r, "invoice_amount_usd") == remaining,
                    "Invoice claim/collection/writeoff/credit equation differs",
                )
                require(_number(r, "remaining_usd") >= 0, "Negative open invoice balance")
            elif all(
                k in r
                for k in (
                    "opening_ar_usd",
                    "invoiced_usd",
                    "collected_usd",
                    "credited_usd",
                    "written_off_usd",
                    "closing_ar_usd",
                )
            ):
                delta = (
                    _number(r, "opening_ar_usd")
                    + _number(r, "invoiced_usd")
                    - _number(r, "collected_usd")
                    - _number(r, "credited_usd")
                    - _number(r, "written_off_usd")
                    - _number(r, "closing_ar_usd")
                )
                require(delta == 0, "Invoice AR rollforward differs")
            elif "remaining_usd" in r:
                require(_number(r, "remaining_usd") >= 0, "Negative open invoice balance")
            else:
                raise KeyError("credit history arithmetic")
            if "due_date" in r:
                require(
                    date.fromisoformat(r["due_date"]) >= date(2027, 1, 1),
                    "Invalid contractual due date",
                )
            require(_number(r, "amount_usd") >= 0, "Negative credit action amount")
        for r in pops["credit_allowance"]:
            exposure = "exposure_usd" if "exposure_usd" in r else "gross_ar_usd"
            if all(k in r for k in (exposure, "rate", "allowance_usd")):
                require(0 <= _number(r, "rate") <= 1, "Invalid credit-loss rate")
                require(
                    abs(_number(r, exposure) * _number(r, "rate") - _number(r, "allowance_usd"))
                    <= D("0.0001"),
                    "Allowance does not follow exposure and rate",
                )
            else:
                raise KeyError("credit allowance exposure/rate")
        allowance = sum((_number(r, "allowance_usd") for r in pops["credit_allowance"]), D(0))
        exposure = sum((_number(r, "gross_ar_usd") for r in pops["credit_allowance"]), D(0))
        require(
            allowance
            == sum((_number(r, "allowance_usd") for r in pops["subledger_rollforward"]), D(0)),
            "Invoice allowances differ from monthly close",
        )
        require(
            exposure
            == sum((_number(r, "gross_ar_usd") for r in pops["subledger_rollforward"]), D(0)),
            "Graded exposure differs from AR close",
        )
    elif control == "LC-WORKFORCE":
        people, positions = set(), set()
        for r in pops["workforce_positions_history"]:
            require(r["position_id"] not in positions, "Duplicate position in monthly population")
            positions.add(r["position_id"])
            if _true(r["occupied"]):
                require(
                    _true(r["authorized"]) and bool(r["person_id"]),
                    "Occupied billet lacks authorization or person",
                )
                require(r["person_id"] not in people, "Person occupies duplicate billets")
                people.add(r["person_id"])
        ftes, payroll = defaultdict(D), D(0)
        for r in pops["workforce_assignments"]:
            ftes[r["person_id"]] += _number(r, "assignment_fte")
            payroll += _number(r, "loaded_cost_usd")
            require(
                not (r["unit"] == "advisory" and r["home_group"] in {"j2", "atlas-meridian"}),
                "Prohibited Advisory staffing reserve",
            )
        require(
            all(0 < v <= 1 for v in ftes.values()),
            "Paid assignments duplicate or omit FTE within unit",
        )
        requests = {r["event_id"] for r in pops["events"] if r["kind"] == "PAYROLL_REQUEST"}
        posted = sum(
            (
                _number(r, "signed_usd")
                for r in pops["journal"]
                if r["account"] == "BIZ_PAYROLL" and r["source_id"] in requests
            ),
            D(0),
        )
        require(posted == payroll, "Payroll request differs from assignments")
    elif control == "LC-ESTIMATE":
        for r in pops["forecast_variance_contributions"]:
            prior = "previous_usd" if "previous_usd" in r else "prior_usd"
            suffix = "_contribution_usd" if "price_contribution_usd" in r else "_usd"
            parts = sum(
                (_number(r, k + suffix) for k in ("price", "volume", "timing", "workforce")), D(0)
            )
            require(
                _number(r, "revised_usd") - _number(r, prior) == parts,
                "Forecast variance decomposition does not reconcile",
            )
            require(
                bool(r.get("revision", r.get("vintage_id"))), "Missing forecast revision identity"
            )
    elif control == "LC-CONSOLIDATION":
        require(
            sum((_number(r, "signed_usd") for r in pops["enterprise_unit_trial_balance"]), D(0))
            == 0,
            "Unit trial balance is unbalanced",
        )
        for r in pops["enterprise_unit_statements"]:
            require(
                _number(r, "assets_usd")
                == _number(r, "liabilities_usd") + _number(r, "equity_usd"),
                "Unit balance sheet does not balance",
            )
            flows = sum(
                (
                    _number(r, k)
                    for k in (
                        "opening_cash_usd",
                        "operating_cash_flow_usd",
                        "investing_cash_flow_usd",
                        "financing_cash_flow_usd",
                        "opening_or_noncash_cash_bridge_usd",
                    )
                ),
                D(0),
            )
            require(
                flows == _number(r, "ending_cash_usd"), "Unit cash-flow statement does not roll"
            )
        for r in pops["management_cost_reconciliation"]:
            require(_number(r, "difference_usd") == 0, "Management allocation does not reconcile")
    elif control == "LC-ADVISORY-VALUE":
        for r in pops["value_certifications"]:
            require(
                _number(r, "total_fee_usd")
                == _number(r, "committed_fee_usd") + _number(r, "variable_fee_usd"),
                "Certified fee does not reconcile",
            )
            require(
                bool(r.get("value_officer")) and len(r.get("baseline_sha256", "")) == 64,
                "Missing value officer or frozen baseline",
            )
            require(_number(r, "variable_fee_usd") >= 0, "Negative certified variable fee")
        for r in pops["matter_determinations"]:
            if "preparer" in r and "reviewer" in r:
                require(
                    bool(r["reviewer"]) and r["reviewer"] != r["preparer"],
                    "Value determination lacks independent review",
                )
    else:
        # These domain adapters are explicit below; no general status==PASS shortcut.
        return _domain_check(control, pops)
    return failures, checked


def _domain_check(control, pops):
    failures, checks = [], 0

    def check(condition, reason):
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(reason)

    if control == "LC-RECOVERY":
        for row in pops["recovery_run_assays"]:
            recovered = _number(row, "recovered_kg")
            check(
                0 <= recovered <= _number(row, "contained_kg"), "Recovery exceeds contained mineral"
            )
            check(
                not _true(row.get("bypass", False)) or recovered == 0,
                "Hard bypass produces material",
            )
        assays = {row["run_id"]: row for row in pops["recovery_run_assays"]}
        captured = {key for key, row in assays.items() if _number(row, "recovered_kg") > 0}
        seen = set()
        for row in pops["recovery_genealogy"]:
            if row["edge_type"] == "CAPTURE_MERGE":
                run_id = row["parent_id"]
                check(run_id not in seen, "Duplicate capture genealogy edge")
                seen.add(run_id)
                check(run_id in assays, "Capture genealogy lacks an assay run")
                if run_id in assays:
                    check(
                        row["mass_basis"] == "RECOVERED_KG"
                        and _number(row, "quantity") == _number(assays[run_id], "recovered_kg"),
                        "Genealogy mass does not reconcile",
                    )
                    check(
                        _number(row, "cost_usd") == _number(assays[run_id], "allocated_cost_usd"),
                        "Genealogy cost does not reconcile",
                    )
        check(captured <= seen, "Recovered run omitted from genealogy")
    elif control == "LC-TRANSFER":
        for row in pops["research_gate_evidence"]:
            if row.get("decision") == "TRANSFER":
                check(
                    _true(row["qualified"])
                    and bool(row["receiver"])
                    and bool(row["maintenance_owner"]),
                    "Production transfer lacks qualification, receiver or maintenance owner",
                )
            elif "decision" in row:
                check(
                    row["decision"]
                    in {"HOLD", "STOP", "CONTINUE", "FAIL", "PASS", "REWORK", "NOT_TRANSFERRED"},
                    "Unrecognized research gate decision",
                )
            else:
                raise KeyError("research gate decision")
    elif control == "LC-ATLAS":
        controls = defaultdict(dict)
        for row in pops["matter_controls"]:
            controls[row["engagement_id"]][row["control"]] = row
        required_controls = {
            "acceptance",
            "scope",
            "competence",
            "conflicts",
            "rights",
            "economics",
            "review",
            "stop",
        }
        for row in pops["matter_gate_decisions"]:
            source = controls[row["engagement_id"]]
            check(set(source) == required_controls, "Matter lacks complete gate evidence")
            allowed = set(source) == required_controls and all(
                r["result"] == "PASS" for r in source.values()
            )
            check(
                row["gate_status"] == ("ALLOWED" if allowed else "BLOCKED"),
                "Matter gate does not follow determinations",
            )
            check(
                all(
                    _true(row[field]) == allowed
                    for field in ("work_allowed", "billing_allowed", "recognition_allowed")
                ),
                "Matter activities bypass a failed or absent gate",
            )
            check(bool(row["client_id"]), "Matter lacks client scope")
            if allowed:
                check(
                    all(r["source_id"] != "PENDING_ACCEPTANCE" for r in source.values()),
                    "Allowed matter lacks accepted determination source",
                )
    elif control == "LC-INDUSTRIAL":
        services = defaultdict(D)
        for row in pops["industrial_service_detail"]:
            hours = _number(row, "required_resource_hours")
            check(hours >= 0, "Negative industrial resource request")
            if row["provider"] == "OWNED":
                services[row["segment"], row["service_date"]] += hours
        seen = set()
        for row in pops["industrial_shift_capacity"]:
            key = row["segment"], row["service_date"]
            check(key not in seen, "Duplicate industrial shift")
            seen.add(key)
            available = max(
                min(_number(row, "crew_hours_available"), _number(row, "equipment_hours_available"))
                - _number(row, "interface_hours_reserved")
                - _number(row, "maintenance_downtime_hours"),
                D(0),
            )
            requested = _number(row, "service_hours_requested")
            check(
                available == _number(row, "net_available_hours"),
                "Shift capacity is not derived from labor/equipment/downtime",
            )
            check(
                requested == services.get(key, D(0)),
                "Service population does not reconstruct shift demand",
            )
            check(
                requested <= available, "Dated operating demand exceeds staffed/qualified capacity"
            )
            check(
                max(requested - available, D(0)) == _number(row, "over_capacity_hours"),
                "Capacity exception magnitude differs",
            )
        check(set(services) <= seen, "Owned service omitted from shift capacity")
        for row in pops["industrial_detail_reconciliation"]:
            check(
                _number(row, "source_quantity") == _number(row, "detail_quantity"),
                "Industrial detail quantity differs from monthly source",
            )
            check(
                _number(row, "source_amount_usd") == _number(row, "detail_amount_usd"),
                "Industrial detail amount differs from monthly source",
            )
            if row.get("kind") == "MINE_PRODUCTION_COST_ALLOCATION":
                check(
                    _number(row, "maintenance_amount_usd")
                    + _number(row, "remaining_production_amount_usd")
                    == _number(row, "source_amount_usd"),
                    "Mine maintenance and remaining production cost do not reconcile",
                )
    return failures, checks


def evaluate(control, populations):
    missing = [name for name in REQUIRED[control] if not populations.get(name)]
    if missing:
        return "NOT_RUN", "Missing required monthly population: " + ", ".join(missing), 0
    try:
        failures, assertions = _check(control, populations)
    except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
        return "NOT_RUN", "Evidence lacks supported, well-formed test fields: " + str(exc), 0
    if not assertions:
        return "NOT_RUN", "No supported assertions were performed", 0
    return (
        ("FAIL", "; ".join(sorted(set(failures))), assertions)
        if failures
        else ("PASS", "Reperformed scoped source assertions", assertions)
    )


def _config(model):
    config = model.operations_inputs.get("controls", {})
    if config.get("classification") != "PUBLIC_SYNTHETIC_CONTROL_EXERCISE":
        raise ValueError("Control exercise must be explicitly public synthetic")
    ids = []
    for row in config.get("exception_exercises", []):
        ids.append(row["exception_id"])
        if row["local_control_id"] not in REQUIRED or row["unit"] not in UNITS:
            raise ValueError("Unknown exception control or unit")
        if not (
            1
            <= row["original_month"]
            <= row["waiver_end_month"]
            < row["remediation_month"]
            < row["independent_retest_month"]
            <= model.policy.get("years", 5) * 12
        ):
            raise ValueError("Invalid waiver, remediation or retest chronology")
        if row["withheld_table"] not in REQUIRED[row["local_control_id"]]:
            raise ValueError("Exercise must withhold a required evidence artifact")
        if not row["reviewer"] or row["reviewer"] == row["preparer"]:
            raise ValueError("Exception requires an independent reviewer")
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate exception identity")
    return config


def build_controls(model, result, extras=None):
    config = _config(model)
    registry = _registry()
    indexed = _index(_sources(model, result, extras))
    tables = {name: [] for name in TABLES}
    exercises = {
        (r["local_control_id"], r["scenario"], date_for(r["original_month"]), r["unit"]): r
        for r in config.get("exception_exercises", [])
    }
    if len(exercises) != len(config.get("exception_exercises", [])):
        raise ValueError("Multiple exercises cannot rewrite one occurrence")
    occurrence_lookup = {}
    for item in registry:
        cid = item["id"]
        for unit in _scope(item):
            tables["control_registry"].append(
                {
                    "local_control_id": cid,
                    "common_control_id": item["control_id"],
                    "unit": unit,
                    "owner_role": item["owner"],
                    "source_frequency": item["frequency"],
                    "exercise_frequency": "MONTHLY_EXPECTED_OCCURRENCE",
                    "procedure": item["procedure"],
                    "required_population_tables": ";".join(REQUIRED[cid]),
                    "classification": config["classification"],
                    "production_effectiveness": "NOT_ASSERTED",
                }
            )
            for scenario in sorted(model.policy["cases"]):
                for month in range(1, model.policy.get("years", 5) * 12 + 1):
                    period = date_for(month)
                    oid = f"SYN-CONTROL-{scenario}-{month:02}-{unit}-{cid}"
                    common = {
                        "occurrence_id": oid,
                        "scenario": scenario,
                        "period": period,
                        "month_index": month,
                        "unit": unit,
                        "local_control_id": cid,
                    }
                    preparer, reviewer = f"SYN-{unit}-preparer", f"SYN-{unit}-independent-reviewer"
                    tables["control_occurrences"].append(
                        common
                        | {
                            "scheduled": True,
                            "due_date": period,
                            "preparer": preparer,
                            "reviewer": reviewer,
                            "classification": config["classification"],
                        }
                    )
                    pops = _slice(indexed, cid, scenario, period, unit)
                    exercise = exercises.get((cid, scenario, period, unit))
                    expected, attached = 0, 0
                    for name, rows in pops.items():
                        required = name in REQUIRED[cid]
                        if not required and not rows:
                            continue
                        expected += int(required)
                        pophash = digest(rows)
                        pid = f"{oid}:{name}"
                        tables["control_population"].append(
                            common
                            | {
                                "population_id": pid,
                                "source_table": name,
                                "required": required,
                                "row_count": len(rows),
                                "population_sha256": pophash,
                                "selection": "EXACT_SCENARIO_MONTH_REPORTING_UNIT",
                                "scope_state": "POPULATED" if rows else "NO_SOURCE_ROWS",
                            }
                        )
                        if rows and not (exercise and name == exercise["withheld_table"]):
                            attached += int(required)
                            tables["control_evidence"].append(
                                common
                                | {
                                    "evidence_id": f"EVIDENCE:{pid}",
                                    "population_id": pid,
                                    "source_table": name,
                                    "row_count": len(rows),
                                    "artifact_sha256": pophash,
                                    "preparer": preparer,
                                    "reviewer": reviewer,
                                    "evidence_state": "GENERATED_SYNTHETIC_SOURCE_MANIFEST",
                                }
                            )
                    outcome, reason, checks = evaluate(cid, pops)
                    if exercise:
                        outcome = "FAIL" if outcome == "PASS" else outcome
                        reason = (
                            "Required evidence attachment withheld for exception exercise; "
                            + reason
                        )
                    tables["control_results"].append(
                        common
                        | {
                            "result_id": f"RESULT:{oid}",
                            "result": outcome,
                            "outcome": outcome,
                            "assertions_performed": checks,
                            "reason": reason,
                            "preparer": preparer,
                            "reviewer": reviewer,
                            "population_sha256": digest(pops),
                            "original_result_preserved": True,
                            "production_effectiveness": "NOT_ASSERTED",
                        }
                    )
                    tables["control_completeness"].append(
                        common
                        | {
                            "expected_occurrences": 1,
                            "recorded_occurrences": 1,
                            "required_population_count": expected,
                            "attached_population_count": attached,
                            "missing_population_count": expected - attached,
                            "complete": expected == attached,
                            "outcome": outcome,
                        }
                    )
                    occurrence_lookup[cid, scenario, period, unit] = (common, pops, outcome)
    _lifecycle(tables, config, occurrence_lookup, indexed)
    model.tables.update(tables)
    model._control_context = (result, extras)
    return tables


def _lifecycle(tables, config, occurrences, indexed):
    for exercise in config.get("exception_exercises", []):
        cid, scenario, unit = (exercise[k] for k in ("local_control_id", "scenario", "unit"))
        original_date = date_for(exercise["original_month"])
        key = cid, scenario, original_date, unit
        if key not in occurrences:
            raise ValueError("Exception does not resolve to a scheduled occurrence")
        original, population, original_outcome = occurrences[key]
        if original_outcome == "PASS":
            raise ValueError("Exception cannot be attached to a passing result")
        exid = exercise["exception_id"]
        common = {
            "exception_id": exid,
            "scenario": scenario,
            "unit": unit,
            "local_control_id": cid,
            "original_occurrence_id": original["occurrence_id"],
            "original_outcome": original_outcome,
        }
        tables["control_exceptions"].append(
            common
            | {
                "period": original_date,
                "opened_date": original_date,
                "reason": exercise["reason"],
                "waiver_expires": date_for(exercise["waiver_end_month"]),
                "preparer": exercise["preparer"],
                "reviewer": exercise["reviewer"],
                "classification": config["classification"],
            }
        )
        for month, state, actor in (
            (exercise["original_month"], "OPEN_WITH_TEMPORARY_WAIVER", exercise["reviewer"]),
            (exercise["waiver_end_month"] + 1, "WAIVER_EXPIRED_ESCALATED", exercise["reviewer"]),
            (exercise["remediation_month"], "REMEDIATION_SUBMITTED", exercise["preparer"]),
        ):
            tables["control_actions"].append(
                common
                | {
                    "action_id": f"{exid}:{state}",
                    "period": date_for(month),
                    "month_index": month,
                    "state": state,
                    "actor": actor,
                    "detail": "Synthetic lifecycle record; original result is immutable",
                }
            )
        # Both attempts re-read the original month's population. A PASS label in
        # configuration or the current month cannot close an older finding.
        original_hash = digest(population)
        for month, reviewer in (
            (exercise["remediation_month"], exercise["preparer"]),
            (exercise["independent_retest_month"], exercise["reviewer"]),
        ):
            current = _slice(indexed, cid, scenario, original_date, unit)
            outcome, reason, assertions = evaluate(cid, current)
            independent = reviewer != exercise["preparer"]
            restored = (
                all(current.get(n) for n in REQUIRED[cid]) and digest(current) == original_hash
            )
            closed = independent and restored and outcome == "PASS"
            state = (
                "CLOSED_BY_INDEPENDENT_RETEST"
                if closed
                else ("SELF_REVIEW_REJECTED" if not independent else "RETEST_FAILED_REMAINS_OPEN")
            )
            tables["control_retests"].append(
                common
                | {
                    "retest_id": f"{exid}:{month}",
                    "period": date_for(month),
                    "month_index": month,
                    "original_period": original_date,
                    "preparer": exercise["preparer"],
                    "reviewer": reviewer,
                    "independent": independent,
                    "original_population_sha256": original_hash,
                    "reperformed_population_sha256": digest(current),
                    "restored_required_evidence": restored,
                    "assertions_performed": assertions,
                    "reperformed_outcome": outcome,
                    "state": state,
                    "reason": reason,
                }
            )
            tables["control_actions"].append(
                common
                | {
                    "action_id": f"{exid}:{state}:{month}",
                    "period": date_for(month),
                    "month_index": month,
                    "state": state,
                    "actor": reviewer,
                    "detail": "Reperformed original-period source assertions and verified complete source hashes",
                }
            )


def validate(model):
    """Rebuild expected records from live source evidence, then compare all fields."""
    if not hasattr(model, "_control_context"):
        raise ValueError("Controls were not built")
    saved = {name: model.tables.get(name, []) for name in TABLES}
    result, extras = model._control_context
    expected = build_controls(model, result, extras)
    # Preserve the supplied output on failure; validation must not silently repair it.
    model.tables.update(saved)
    for name in TABLES:
        if saved[name] != expected[name]:
            raise ValueError(f"Control output or source evidence changed: {name}")
    ids = [r["occurrence_id"] for r in saved["control_occurrences"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate control occurrence")
    results = Counter(r["outcome"] for r in saved["control_results"])
    if set(results) - {"PASS", "FAIL", "NOT_RUN"}:
        raise ValueError("Unsupported control result")
    for result_row, completeness in zip(saved["control_results"], saved["control_completeness"]):
        if result_row["outcome"] == "PASS" and not completeness["complete"]:
            raise ValueError("Incomplete evidence cannot pass")
    return {
        "scheduled_occurrences": len(ids),
        "outcomes": dict(sorted(results.items())),
        "production_effectiveness": "NOT_ASSERTED",
        "source_population_integrity": "EXACT_REPERFORMANCE",
    }
