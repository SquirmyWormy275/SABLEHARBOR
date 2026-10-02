"""Twenty distinct B03 examinations of actually retained company-native bytes.

The caller binds originals and the supplied clock to its current Engine. This
pure callback never opens a company database, consults a Key, executes company
scripts, creates company evidence, or borrows earlier auditor outcomes. Its only
write is the separately accepted, selected local JSON restore into new private
scratch. Local documentary checks do not establish full corporate effectiveness.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path

from .collected_byte_recovery_method import CollectionContext, examine_restore, reference
from .company_store import _json, _time
from .fresh_sec003_procedure import CLOCK_ID, NATIVE_ID, require
from .source_library_audit import BUSINESS_REFERENCE
from .source_library_security_methods import analyze_continuity_timestamps

PLAN_SHA = "85d52a4a040690401af81b79e82f09bcc55a9807a7755f3d2fe527b269aad2ee"
FAMILIES = {
    "bcm",
    "backup-runtime-history",
    "configuration-runtime-history",
    "period-history",
    "transition",
    "supplementalops",
}
PIN_ROLES = {
    "job_pin": {"backup-runtime-history.backup_job", "backup-runtime-history.restore_job"},
    "prior_attempt_pin": {
        "backup-runtime-history.backup_job",
        "backup-runtime-history.restore_job",
    },
    "lease_pin": {"backup-runtime-history.credential_event"},
    "comparison_source_pin": {"backup-runtime-history.source_dataset"},
    "source_job_pin": {"backup-runtime-history.backup_job", "backup-runtime-history.restore_job"},
    "source_ticket_pin": {
        "backup-runtime-history.failure_ticket",
        "backup-runtime-history.monitor_ticket",
    },
    "ticket_pin": {
        "backup-runtime-history.failure_ticket",
        "backup-runtime-history.monitor_ticket",
    },
}
SCALAR_ROLES = {
    "authority_decision",
    "service_inventory",
    "demand_forecast",
    "technical_objectives",
    "business_impact",
    "exercise_plan",
    "exercise_result",
    "exercise_review",
    "corrective_action",
    "closure_gate",
}
BROAD = (
    "Full-year corporate critical-service denominator and approved business/customer BIA; "
    "application usability and application data age; actual primary-site loss, recovery "
    "capacity and return; ePHI emergency access; supplier/customer participation; "
    "independent qualified assurance acceptance remain unperformed."
)


def task_plan():
    path = Path(__file__).with_name("continuity_collected_task_plan_v1.json")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PLAN_SHA, "Exact B03 task instruction plan required")
    plan = json.loads(raw)
    require(plan["task_count"] == len(plan["tasks"]) == 20, "Exact twenty B03 tasks required")
    return plan["tasks"]


def contracts():
    return {
        t["task_id"]: {
            "performed": (
                f"Examine retained {t['control_id']} {t['clause_group']} originals for: "
                + t["authored_instruction"]
                + " Record separately the attributes examined, contradicted, and unsupported."
            ),
            "unperformed": t["task_kind_rule"] + " " + BROAD,
            "allowed_dispositions": [
                {"status": "IN_PROGRESS", "conclusion": "LIMITATION"},
                {"status": "IN_PROGRESS", "conclusion": "FAIL"},
            ],
        }
        for t in task_plan()
    }


def _key(source):
    return tuple(source[k] for k in NATIVE_ID)


def _number(value):
    return type(value) in {int, float} and math.isfinite(value) and value >= 0


def _detail(row):
    doc = row["document"]
    detail = doc.get("detail", doc)
    require(isinstance(detail, dict), "Typed continuity detail object required")
    return detail


def _refs(value, path="$"):
    if isinstance(value, dict):
        if set(NATIVE_ID) <= value.keys():
            yield path, value
        else:
            for name, child in value.items():
                yield from _refs(child, path + "." + name)
    elif isinstance(value, list):
        for number, child in enumerate(value):
            yield from _refs(child, f"{path}[{number}]")


class History:
    def __init__(self, records, as_of):
        self.cutoff = _time(as_of)
        self.rows, self.index, self.joins = [], {}, []
        for record in records:
            source, receipt = record["source"], record["receipt"]
            raw = record["retained_bytes"]
            require(
                set(CLOCK_ID) <= source.keys()
                and type(source["version"]) is int
                and source["version"] > 0
                and all(isinstance(source[k], str) and source[k] for k in NATIVE_ID[:-1])
                and isinstance(record["artifact_id"], str)
                and record["artifact_id"]
                and isinstance(raw, bytes)
                and raw
                and _json(receipt["source"]) == _json(source)
                and type(receipt["content_bytes"]) is int
                and receipt["content_bytes"] == len(raw)
                and all(
                    isinstance(receipt.get(k), str) and receipt[k]
                    for k in ("engagement_id", "principal_id", "command_id")
                )
                and _time(source["event_at"])
                <= _time(source["available_at"])
                <= _time(receipt["simulated_as_of"])
                <= self.cutoff
                and _time(source["imported_at"])
                <= _time(receipt["collected_at"])
                <= _time(datetime.now(UTC).isoformat())
                and hashlib.sha256(raw).hexdigest() == source["sha256"] == record["artifact_sha256"]
                and record["content_type"] == "application/json"
                and source["provenance"].get("content_type") == "application/json",
                "Actual continuity custody, native version, byte count or clocks differ",
            )
            family, role = record["logical_family"], record["logical_system"]
            require(
                family in FAMILIES and source["system"] == family + "." + role,
                "Continuity role differs from actual native system",
            )
            doc = json.loads(raw)
            require(isinstance(doc, dict), "Actual structured continuity original required")
            if family == "backup-runtime-history" and role in {"backup_job", "restore_job"}:
                require(
                    doc.get("operation") == ("BACKUP" if role == "backup_job" else "RESTORE"),
                    "Actual continuity operation kind differs from native role",
                )
            require(
                all(k not in doc or doc[k] == source[k] for k in ("event_at", "available_at")),
                "Continuity body clock differs from native custody",
            )
            key = _key(source)
            require(key not in self.index, "Distinct exact continuity native versions required")
            row = {**record, "content": raw, "document": doc}
            self.rows.append(row)
            self.index[key] = row
        require(
            self.rows and len({r["artifact_id"] for r in self.rows}) == len(self.rows),
            "Distinct actually retained continuity originals required",
        )
        require(
            len(
                {
                    (
                        r["source"]["company"],
                        r["source"]["branch"],
                        r["receipt"]["engagement_id"],
                        r["receipt"]["principal_id"],
                    )
                    for r in self.rows
                }
            )
            == 1,
            "One collected company branch and engagement required",
        )
        for row in self.rows:
            for path, ref in _refs(row["document"]):
                expected = PIN_ROLES.get(path.rsplit(".", 1)[-1])
                if (
                    path.startswith("$.site_capacity_source_refs[")
                    and row["logical_family"] == "bcm"
                ):
                    expected = {
                        "service_inventory": {"transition.provider_contract"},
                        "exercise_plan": {"transition.site_release"},
                        "exercise_result": {
                            "transition.recovery_exercise",
                            "transition.exception_event",
                        },
                        "corrective_action": {"transition.exception_event"},
                        "closure_gate": {"transition.exception_event"},
                    }.get(row["logical_system"], set())
                if path.endswith(".source_pin") and row["logical_system"] in {
                    "backup_job",
                    "restore_job",
                }:
                    expected = {
                        "backup-runtime-history."
                        + (
                            "source_dataset"
                            if row["logical_system"] == "backup_job"
                            else "backup_object"
                        )
                    }
                if path.endswith(".object_pin") and row["logical_system"] in {
                    "backup_job",
                    "restore_job",
                }:
                    expected = {
                        "backup-runtime-history."
                        + (
                            "backup_object"
                            if row["logical_system"] == "backup_job"
                            else "restored_dataset"
                        )
                    }
                target, status = self.resolve(row, ref, expected)
                self.joins.append(
                    {
                        "origin": reference(row["source"]),
                        "path": path,
                        "reference": ref,
                        "status": status,
                        "target": reference(target["source"]) if target else None,
                    }
                )
            if row["logical_family"] == "bcm":
                for locator, digest in row["document"].get("local_prior_source_sha256", {}).items():
                    parts = locator.rsplit(":", 2)
                    typed_locator = (
                        len(parts) == 3
                        and bool(parts[0])
                        and parts[1] in SCALAR_ROLES
                        and parts[2].isascii()
                        and parts[2].isdigit()
                        and int(parts[2]) > 0
                    )
                    typed_digest = (
                        isinstance(digest, str)
                        and len(digest) == 64
                        and all(c in "0123456789abcdef" for c in digest)
                    )
                    candidates = (
                        [
                            r
                            for r in self.rows
                            if r["source"]["system"] == "bcm." + parts[1]
                            and r["source"]["record"] == parts[0]
                            and r["source"]["version"] == int(parts[2])
                        ]
                        if typed_locator and typed_digest
                        else []
                    )
                    target = candidates[0] if len(candidates) == 1 else None
                    if not typed_locator:
                        status = "UNRESOLVED_UNTYPED_SCALAR_LOCATOR_NO_ALIAS"
                    elif not typed_digest:
                        status = "UNRESOLVED_UNTYPED_SCALAR_DIGEST"
                    elif len(candidates) > 1:
                        status = "AMBIGUOUS_EXACT_SCALAR_ORIGINAL"
                    elif target is None:
                        status = "ORIGINAL_NOT_COLLECTED"
                    elif target["source"]["sha256"] != digest:
                        status = "SCALAR_ORIGINAL_DIGEST_DIFFERS"
                        target = None
                    elif _time(target["source"]["available_at"]) > _time(row["source"]["event_at"]):
                        status = "SOURCE_UNAVAILABLE_AT_COMPANY_EVENT"
                    else:
                        status = "EXACT_AVAILABLE_ORIGINAL"
                    self.joins.append(
                        {
                            "origin": reference(row["source"]),
                            "path": locator,
                            "reference": {"sha256": digest},
                            "status": status,
                            "target": reference(target["source"]) if target else None,
                        }
                    )

    def selected(self, family, roles):
        return [
            r for r in self.rows if r["logical_family"] == family and r["logical_system"] in roles
        ]

    def resolve(self, origin, ref, expected=None):
        if (ref.get("company"), ref.get("branch")) != (
            origin["source"]["company"],
            origin["source"]["branch"],
        ):
            return None, "OUTSIDE_COLLECTED_BRANCH_AUTHORITY"
        require(
            set(BUSINESS_REFERENCE) <= ref.keys()
            and type(ref["version"]) is int
            and ref["version"] > 0,
            "Exact positive-version continuity reference required",
        )
        target = self.index.get(_key(ref))
        if target is None:
            return None, "ORIGINAL_NOT_COLLECTED"
        fields = (
            (*BUSINESS_REFERENCE, "imported_at") if "imported_at" in ref else BUSINESS_REFERENCE
        )
        require(
            all(_json(ref[k]) == _json(target["source"][k]) for k in fields),
            "Exact continuity reference digest or clocks differ",
        )
        if expected is not None and target["source"]["system"] not in expected:
            return None, "ACTUAL_NATIVE_ROLE_DIFFERS"
        if _time(target["source"]["available_at"]) > _time(origin["source"]["event_at"]):
            return None, "SOURCE_UNAVAILABLE_AT_COMPANY_EVENT"
        return target, "EXACT_AVAILABLE_ORIGINAL"


def _evidence(rows, locator):
    return [
        {"artifact_id": r["artifact_id"], "sha256": r["artifact_sha256"], "locator": locator}
        for r in rows[:20]
    ]


def _observation(label, facts, rows, *, status="OBSERVED", locator="$"):
    return {"id": label, "facts": facts, "status": status, "evidence": _evidence(rows, locator)}


def _records(rows, fields):
    return [
        {
            "source": reference(r["source"]),
            "attributes": {k: _detail(r)[k] for k in fields if k in _detail(r)},
        }
        for r in rows
    ]


def _bia(history):
    inventory = history.selected("bcm", {"service_inventory"})
    impact = history.selected("bcm", {"business_impact"})
    technical = history.selected("bcm", {"technical_objectives"})
    authority = history.selected("bcm", {"authority_decision"})
    demand = history.selected("bcm", {"demand_forecast"})
    for row in [*impact, *technical]:
        d = _detail(row)
        for field in (
            "rto_minutes",
            "rpo_minutes",
            "tolerable_interruption_minutes",
            "proposed_rto_minutes",
            "proposed_rpo_minutes",
        ):
            require(field not in d or _number(d[field]), "Typed BIA objective value required")
    capacity, exceptions = [], []
    for forecast in demand:
        d = _detail(forecast)
        declared_inventory = {
            _key(j["target"])
            for j in history.joins
            if _key(j["origin"]) == _key(forecast["source"])
            and ":service_inventory:" in j["path"]
            and j["status"] == "EXACT_AVAILABLE_ORIGINAL"
        }
        matched = [r for r in inventory if _key(r["source"]) in declared_inventory]
        if len(matched) != 1:
            capacity.append(
                {
                    "forecast": reference(forecast["source"]),
                    "status": "UNIQUE_PRIOR_INVENTORY_MISSING",
                }
            )
            continue
        cap = _detail(matched[0]).get("usable_it_kw", {})
        for site, value in cap.items():
            expected = d.get("expected_kw", {}).get(site)
            peak = d.get("peak_kw", {}).get(site)
            threshold = d.get("action_threshold_kw", {}).get(site)
            typed = all(_number(v) for v in (value, expected, peak, threshold))
            facts = {
                "site": site,
                "forecast": reference(forecast["source"]),
                "inventory": reference(matched[0]["source"]),
                "capacity_kw": value,
                "expected_kw": expected,
                "peak_kw": peak,
                "action_threshold_kw": threshold,
                "typed_numeric_inputs": typed,
                "measurement_status": d.get("measurement_status"),
                "expected_exceeds_capacity": expected > value if typed else None,
                "peak_exceeds_capacity": peak > value if typed else None,
                "peak_exceeds_action_threshold": peak > threshold if typed else None,
                "actual_utilization_observed": False,
            }
            capacity.append(facts)
            if typed and (peak > value or peak > threshold):
                exceptions.append({"attribute": "FORECAST_CAPACITY_TREATMENT", "facts": facts})
    return {
        "inventory": _records(
            inventory, ["service_id", "dependencies", "population", "usable_it_kw"]
        ),
        "impact": _records(
            impact,
            [
                "rto_minutes",
                "rpo_minutes",
                "tolerable_interruption_minutes",
                "accepted_local_objectives",
                "business_unit_and_customer_objectives_accepted",
                "capacity_treatment_open",
            ],
        ),
        "technical": _records(
            technical,
            [
                "proposed_rto_minutes",
                "proposed_rpo_minutes",
                "recovery_priority",
                "capacity_action",
            ],
        ),
        "authority": _records(
            authority, ["scope", "delegate", "technical_owner", "qualification", "authority_limit"]
        ),
        "capacity": capacity,
        "exceptions": exceptions,
        "annual_business_acceptance_tested": False,
        "all_critical_service_inventory_established": False,
    }


def _fact_sources(history, facts, fallback):
    keys = {_key(ref) for _, ref in _refs(facts)}
    return [r for r in history.rows if _key(r["source"]) in keys] or fallback


def _occurrence_observations(task, history, backup, restore, timing, local_restore, fallback):
    control = task["control_id"]
    clause = task["task_id"].split("-corporate-", 1)[1]
    result = []
    if clause == "TOE" and control in {"SH-BCM-002", "SH-BCM-003"}:
        schedule = backup if control == "SH-BCM-002" else restore
        for number, occurrence in enumerate(schedule["population"]):
            errors = any(
                e["occurrence_id"] == occurrence["occurrence_id"] for e in schedule["exceptions"]
            )
            result.append(
                _observation(
                    f"DECLARED-DUE-{number + 1:03d}",
                    occurrence,
                    _fact_sources(history, occurrence, fallback),
                    status="EXCEPTION_RECORDED"
                    if errors
                    else ("OBSERVED" if occurrence["attempts"] else "SUPPORT_UNAVAILABLE"),
                    locator="$.plan.schedule / exact native job occurrence/version",
                )
            )
    if clause in {"TOE", "CHECK-SOC2:A1.3"} and control in {"SH-BCM-003", "SH-BCM-004"}:
        for number, occurrence in enumerate(
            timing.get("recorded_interval_chronology_exceptions", [])
        ):
            result.append(
                _observation(
                    f"UNAVAILABLE-EXERCISE-{number + 1:03d}",
                    occurrence,
                    _fact_sources(history, occurrence, fallback),
                    status="SUPPORT_UNAVAILABLE",
                    locator="$.reported interval outside native event/publication boundary",
                )
            )
        for number, occurrence in enumerate(timing.get("observations", [])):
            failed = (
                not occurrence["duration_claim_agrees"]
                or not occurrence["recorded_elapsed_within_declared_rto"]
            )
            result.append(
                _observation(
                    f"DATED-EXERCISE-{number + 1:03d}",
                    occurrence,
                    _fact_sources(history, occurrence, fallback),
                    status="EXCEPTION_RECORDED" if failed else "OBSERVED",
                    locator="$.detail.exercise_start_at / observed_finish_at / local targets",
                )
            )
    if clause == "TOE" and control == "SH-BCM-003":
        for number, occurrence in enumerate(local_restore["selected_occurrences"]):
            result.append(
                _observation(
                    f"LOCAL-BYTE-RESTORE-{number + 1:03d}",
                    occurrence,
                    _fact_sources(history, occurrence, fallback),
                    status="OBSERVED"
                    if occurrence.get("real_isolated_byte_restore_performed")
                    else "SUPPORT_UNAVAILABLE",
                    locator="$.exact selected local restore and original dependency headers",
                )
            )
    if clause == "TOE" and control == "SH-BCM-001":
        for number, row in enumerate(history.selected("bcm", {"business_impact"})):
            result.append(
                _observation(
                    f"DATED-LOCAL-BIA-{number + 1:03d}",
                    {
                        "source": reference(row["source"]),
                        "objectives": _records(
                            [row],
                            [
                                "rto_minutes",
                                "rpo_minutes",
                                "tolerable_interruption_minutes",
                                "accepted_local_objectives",
                                "business_unit_and_customer_objectives_accepted",
                            ],
                        ),
                        "annual_and_material_change_denominator_established": False,
                    },
                    [row],
                    locator="$.detail.local objectives and explicitly limited acceptance",
                )
            )
    return result


def _schedule(history, control):
    periods = history.selected("period-history", {"operating_period_ledger"})
    runtimes = history.selected("backup-runtime-history", {"runtime_definition"})
    jobs = history.selected(
        "backup-runtime-history", {"backup_job" if control == "SH-BCM-002" else "restore_job"}
    )
    population, exceptions, missing = [], [], []
    for period in periods:
        p = period["document"].get("plan", {})
        declared = p.get("schedule", [])
        require(
            isinstance(declared, list)
            and all(
                isinstance(d, dict) and isinstance(d.get("id"), str) and d["id"] for d in declared
            )
            and len({d["id"] for d in declared}) == len(declared),
            "Distinct typed declared schedule occurrences required",
        )
        matching = [
            r
            for r in runtimes
            if r["document"].get("declaration_original_sha256") == period["source"]["sha256"]
            and _json(r["document"].get("plan")) == _json(p)
        ]
        for due in declared:
            if due.get("control_id") != control or _time(due["due_at"]) > history.cutoff:
                continue
            require(
                isinstance(due["inventory_ids"], list)
                and due["inventory_ids"]
                and len(set(due["inventory_ids"])) == len(due["inventory_ids"])
                and all(isinstance(i, str) and i for i in due["inventory_ids"]),
                "Typed declared recovery occurrence required",
            )
            selected = [
                r
                for r in jobs
                if len(matching) == 1
                and r["document"].get("runtime_id") == matching[0]["document"].get("runtime_id")
                and r["source"]["record"] == due["id"]
                and r["document"].get("dataset_id") in due["inventory_ids"]
            ]
            facts = {
                "period": reference(period["source"]),
                "occurrence_id": due["id"],
                "due_at": due["due_at"],
                "window_start": due["window_start"],
                "window_end_exclusive": due["window_end_exclusive"],
                "inventory_ids": due["inventory_ids"],
                "runtime_originals": [reference(r["source"]) for r in matching],
                "attempts": [],
                "scope": "DECLARED_LOCAL_OCCURRENCES_ONLY",
            }
            for job in selected:
                d = job["document"]
                attempt = d.get("business_attempted_at")
                binding = (
                    matching[0]["document"].get("bindings", {}).get(job["source"]["record"], {})
                )
                valid = bool(binding) and all(
                    binding.get(k) == d.get(k) for k in ("dataset_id", "occurrence_id", "operation")
                )
                declared_match = (
                    d.get("occurrence_id") == due["id"]
                    and d.get("operation") == ("BACKUP" if control == "SH-BCM-002" else "RESTORE")
                    and ("operation" not in due or due["operation"] == d.get("operation"))
                )
                available = _time(period["source"]["available_at"]) <= _time(attempt) and _time(
                    matching[0]["source"]["available_at"]
                ) <= _time(attempt)
                in_window = (
                    _time(due["window_start"])
                    <= _time(attempt)
                    < _time(due["window_end_exclusive"])
                )
                obj, obj_status = (
                    history.resolve(
                        job,
                        d["object_pin"],
                        {
                            "backup-runtime-history.backup_object"
                            if control == "SH-BCM-002"
                            else "backup-runtime-history.restored_dataset"
                        },
                    )
                    if d.get("object_pin")
                    else (None, "NO_OUTPUT_ORIGINAL")
                )
                lease, lease_status = (
                    history.resolve(
                        job, d["lease_pin"], {"backup-runtime-history.credential_event"}
                    )
                    if d.get("lease_pin")
                    else (None, "NO_LEASE_ORIGINAL")
                )
                permitted = None
                if lease:
                    ld = lease["document"]
                    require(
                        type(ld.get("enabled")) is bool,
                        "Typed credential enabled attribute required",
                    )
                    permitted = (
                        ld["enabled"]
                        and ld.get("principal_id") == d.get("performed_by")
                        and _time(lease["source"]["available_at"]) <= _time(attempt)
                        and _time(ld["valid_from"]) <= _time(attempt) < _time(ld["expires_at"])
                    )
                source, source_status = (
                    history.resolve(
                        job,
                        d["source_pin"],
                        {
                            "backup-runtime-history.source_dataset"
                            if control == "SH-BCM-002"
                            else "backup-runtime-history.backup_object"
                        },
                    )
                    if d.get("source_pin")
                    else (None, "NO_INPUT_ORIGINAL")
                )
                source_available = (
                    _time(source["source"]["available_at"]) <= _time(attempt) if source else None
                )
                byte_agreement = source["content"] == obj["content"] if source and obj else None
                failed = d.get("object_pin") is None or d.get("error_code") is not None
                item = {
                    "source": reference(job["source"]),
                    "operation": d.get("operation"),
                    "business_attempted_at": attempt,
                    "status_claim": d.get("status"),
                    "error_code": d.get("error_code"),
                    "binding_matches": valid,
                    "matches_exact_declared_due_occurrence": declared_match,
                    "period_runtime_available_at_attempt": available,
                    "attempt_inside_declared_window": in_window,
                    "output_original_status": obj_status,
                    "lease_original_status": lease_status,
                    "lease_enabled_bound_and_current": permitted,
                    "recorded_failure": failed,
                    "native_output_bytes_retained": obj is not None,
                    "exact_input_original_status": source_status,
                    "input_available_at_business_attempt": source_available,
                    "input_output_bytes_equal": byte_agreement,
                }
                facts["attempts"].append(item)
                if (
                    failed
                    or not valid
                    or not declared_match
                    or not available
                    or not in_window
                    or permitted is False
                    or source_available is False
                    or byte_agreement is False
                ):
                    exceptions.append({"occurrence_id": due["id"], "attempt": item})
            if not selected:
                missing.append(
                    {
                        "occurrence_id": due["id"],
                        "period": reference(period["source"]),
                        "reason": "DECLARED_DUE_EXECUTION_ORIGINAL_NOT_COLLECTED",
                    }
                )
            population.append(facts)
    return {
        "population": population,
        "exceptions": exceptions,
        "missing_occurrences": missing,
        "denominator_basis": "EXACT_COLLECTED_DECLARED_LOCAL_SCHEDULE_BEFORE_SELECTION",
        "full_year_denominator_established": False,
        "approved_rpo_schedule_established": False,
        "historical_failures_retained_after_retry": True,
    }


def _monitor(history):
    jobs = history.selected("backup-runtime-history", {"backup_job", "restore_job"})
    tickets = history.selected("backup-runtime-history", {"failure_ticket", "monitor_ticket"})
    observations = history.selected("backup-runtime-history", {"monitor_observation"})
    failures = []
    for row in jobs:
        d = row["document"]
        if d.get("error_code") is None and d.get("object_pin") is not None:
            continue
        associated = []
        for ticket in tickets:
            pin = ticket["document"].get("job_pin") or ticket["document"].get("issue", {}).get(
                "source_job_pin"
            )
            if pin and _key(pin) == _key(row["source"]):
                target, status = history.resolve(ticket, pin, PIN_ROLES["job_pin"])
                if target:
                    associated.append(
                        {
                            "source": reference(ticket["source"]),
                            "status_claim": ticket["document"].get("status"),
                            "resolution_claim": ticket["document"].get("resolution"),
                            "join": status,
                        }
                    )
        failures.append(
            {
                "failed_attempt": reference(row["source"]),
                "error_code": d.get("error_code"),
                "exact_tickets": associated,
                "later_retry_erases_original_failure": False,
            }
        )
    return {
        "recorded_failures": failures,
        "monitor_scans": _records(
            history.selected("backup-runtime-history", {"monitor_scan"}),
            ["source_cutoff", "capture", "operating_review", "whole_period_effectiveness"],
        ),
        "observations": _records(
            observations, ["occurrence_id", "kind", "root_cause", "source_cutoff", "status"]
        ),
        "ticket_states": _records(tickets, ["status", "resolution", "root_cause", "issue"]),
        "continuous_monitoring_tested": False,
        "independent_operating_review_performed": False,
    }


def _timestamp(history):
    bcm = history.selected("bcm", SCALAR_ROLES)
    required = {
        "business_impact": "SVC-COMPUTE",
        "technical_objectives": "SVC-COMPUTE",
        "authority_decision": "SELECTED-SERVICE",
    }
    complete = all(
        len([r for r in bcm if r["logical_system"] == role and r["source"]["record"] == record])
        == 1
        for role, record in required.items()
    )
    results = [
        r
        for r in bcm
        if r["logical_system"] == "exercise_result" and r["source"]["record"] == "MARKER-RECOVERY"
    ]
    joins = [j for j in history.joins if j["origin"]["system"].startswith("bcm.")]
    if (
        not complete
        or not results
        or any(
            j["status"] != "EXACT_AVAILABLE_ORIGINAL"
            for j in joins
            if j["path"] and not j["path"].startswith("$")
        )
    ):
        return {
            "status": "SUPPORT_UNAVAILABLE",
            "reason": "EXACT_BIA_TECHNICAL_AUTHORITY_RESULT_PRIORS_NOT_COLLECTED",
            "actual_marker_restore_performed": False,
        }
    valid, chronology = [], []
    for row in results:
        d = _detail(row)
        require(
            all(
                _number(d.get(k))
                for k in (
                    "measured_restore_minutes_simulated",
                    "rto_target_minutes",
                    "rpo_target_minutes",
                    "measured_replay_gap_minutes_simulated",
                )
            ),
            "Typed nonnegative exercise timing values required",
        )
        try:
            require(
                isinstance(d.get("exercise_start_at"), str)
                and isinstance(d.get("observed_finish_at"), str),
                "Recorded interval required",
            )
            start, finish = _time(d["exercise_start_at"]), _time(d["observed_finish_at"])
            supported = (
                start
                <= finish
                <= _time(row["source"]["event_at"])
                <= _time(row["source"]["available_at"])
                <= history.cutoff
            )
        except (ValueError, TypeError):
            supported = False
        if supported:
            valid.append(row)
        else:
            chronology.append(
                {
                    "source": reference(row["source"]),
                    "reported_start_at": d.get("exercise_start_at"),
                    "reported_finish_at": d.get("observed_finish_at"),
                    "actual_examination_cutoff": history.cutoff,
                    "status": "SUPPORT_UNAVAILABLE",
                    "reason": (
                        "REPORTED_INTERVAL_UNKNOWN_OR_OUTSIDE_NATIVE_EVENT_PUBLICATION_BOUNDARY"
                    ),
                }
            )
    if not valid:
        return {
            "status": "SUPPORT_UNAVAILABLE",
            "recorded_interval_chronology_exceptions": chronology,
            "actual_marker_restore_performed": False,
        }
    valid_ids = {r["artifact_id"] for r in valid}
    analysis = analyze_continuity_timestamps(
        [r for r in bcm if r not in results or r["artifact_id"] in valid_ids],
        {
            "exercise_record": "MARKER-RECOVERY",
            "target_record": "SVC-COMPUTE",
            "authority_record": "SELECTED-SERVICE",
        },
    )
    analysis["recorded_interval_chronology_exceptions"] = chronology
    return analysis


def _restores(history, scratch_root):
    results = []
    context = CollectionContext(
        history.rows[0]["source"]["company"],
        history.rows[0]["source"]["branch"],
        history.rows[0]["receipt"]["engagement_id"],
        history.rows[0]["receipt"]["principal_id"],
        history.cutoff,
    )
    for number, row in enumerate(history.selected("backup-runtime-history", {"restore_job"})):
        d = row["document"]
        runtime = [
            r
            for r in history.selected("backup-runtime-history", {"runtime_definition"})
            if r["document"].get("runtime_id") == d.get("runtime_id")
        ]
        period = [
            r
            for r in history.selected("period-history", {"operating_period_ledger"})
            if len(runtime) == 1
            and r["source"]["sha256"] == runtime[0]["document"].get("declaration_original_sha256")
        ]
        if (
            d.get("source_pin") is None
            or d.get("object_pin") is None
            or len(runtime) != 1
            or len(period) != 1
        ):
            result = {
                "status": "SUPPORT_UNAVAILABLE",
                "selected_restore": reference(row["source"]),
                "real_isolated_byte_restore_performed": False,
                "reason": "FAILED_OR_MISSING_EXACT_RUNTIME_PERIOD_INPUT_OUTPUT_ORIGINALS",
            }
        else:
            result = examine_restore(
                history.rows,
                context=context,
                restore_ref=reference(row["source"]),
                runtime_ref=reference(runtime[0]["source"]),
                period_ref=reference(period[0]["source"]),
                scratch=Path(scratch_root) / f"BCM003-LOCAL-RESTORE-{number + 1:03d}",
            )
        results.append(result)
    return {
        "selected_occurrences": results,
        "selection_basis": "ALL_COLLECTED_LOCAL_RESTORE_JOB_VERSIONS",
        "august_marker_bytes_independently_restored": False,
        "application_rto_rpo_usability_tested": False,
        "local_configuration_copy_does_not_restore_august_marker": True,
    }


def _coverage(task, history, local_restore):
    """The authored steps retain individual boundaries instead of blanket credit."""
    control = task["control_id"]
    clause = task["task_id"].split("-corporate-", 1)[1]
    basis = {
        "SH-BCM-001": [
            (
                "critical-service and dependency inventory",
                "bcm",
                {"service_inventory"},
                "DECLARED_SELECTED_SERVICE_ONLY",
            ),
            (
                "outage impacts, tolerable interruption, recovery order, RTO and RPO",
                "bcm",
                {"business_impact", "technical_objectives"},
                "DECLARED_LOCAL_OBJECTIVES_ONLY",
            ),
            (
                "scoped authority and business acceptance",
                "bcm",
                {"authority_decision", "business_impact"},
                "SOURCE_DECLARATION_NOT_QUALIFIED_BUSINESS_ACCEPTANCE",
            ),
            (
                "required primary and recovery resources",
                "bcm",
                {"service_inventory", "demand_forecast"},
                "FORECAST_AND_CONTRACT_REFERENCES_NOT_OBSERVED_UTILIZATION",
            ),
        ],
        "SH-BCM-002": [
            (
                "protected datasets and scheduled local occurrences",
                "period-history",
                {"operating_period_ledger"},
                "DECLARED_LOCAL_SCHEDULE_NOT_APPROVED_RPO_OR_ENTERPRISE_INVENTORY",
            ),
            (
                "implemented job attempts and input/output bytes",
                "backup-runtime-history",
                {"backup_job", "backup_object", "source_dataset"},
                "EXACT_LOCAL_RECORDED_ATTEMPTS_ONLY",
            ),
            (
                "access configuration and original leases",
                "backup-runtime-history",
                {"credential_event"},
                "LOCAL_COPY_LEASE_NOT_OFFSITE_ISOLATION",
            ),
            (
                "monitor and failure ticket lineage",
                "backup-runtime-history",
                {"failure_ticket", "monitor_ticket", "monitor_observation", "monitor_scan"},
                "OPERATOR_TRIGGERED_SELECTED_SCANS_NOT_CONTINUOUS_COVERAGE",
            ),
        ],
        "SH-BCM-003": [
            (
                "critical dataset and recovery path risk selection",
                "bcm",
                {"exercise_plan", "business_impact"},
                "DECLARED_SELECTED_MARKER_PLAN_ONLY",
            ),
            (
                "recorded recovery time against local target",
                "bcm",
                {"exercise_result", "business_impact"},
                "RECORDED_BUSINESS_TIMESTAMP_ARITHMETIC_NOT_APPLICATION_RTO",
            ),
            (
                "recorded failure, corrective action and retest versions",
                "bcm",
                {"exercise_result", "corrective_action", "closure_gate"},
                "DATED_HISTORY_NOT_VALIDATED_CORRECTIVE_CLOSURE",
            ),
            (
                "declared local restore occurrence denominator",
                "period-history",
                {"operating_period_ledger"},
                "LOCAL_DECLARATION_NOT_FULL_YEAR_OR_CRITICAL_DATASET_CENSUS",
            ),
        ],
        "SH-BCM-004": [
            (
                "loss, recovery operation and return exercise design",
                "bcm",
                {"exercise_plan"},
                "SELECTED_MARKER_DESIGN_NOT_ALL_THREE_EXECUTED_SITE_PHASES",
            ),
            (
                "dated event timing and selected site exercise records",
                "transition",
                {"recovery_exercise", "site_release"},
                "COMPANY_REPORTED_LOCAL_SCENARIO_NOT_INDEPENDENT_FAILOVER",
            ),
            (
                "exercise results, lessons and revision/retest history",
                "bcm",
                {"exercise_result", "exercise_review", "corrective_action", "closure_gate"},
                "DATED_SOURCE_VERSIONS_NOT_FULL_YEAR_MATERIAL_CHANGE_CENSUS",
            ),
        ],
    }[control]
    rows = []
    for attribute, family, roles, limit in basis:
        originals = history.selected(family, roles)
        rows.append(
            {
                "attribute": attribute,
                "status": "DOCUMENTARY_ATTRIBUTE_EXAMINED" if originals else "SUPPORT_UNAVAILABLE",
                "basis": limit,
                "native_originals": [reference(r["source"]) for r in originals],
            }
        )
    additional = {
        "CHECK-SOC2:A1.1": (
            "peak/expected demand arithmetic is bounded to forecasts; measured "
            "utilization and accepted capacity treatment unperformed"
        ),
        "CHECK-SOC2:A1.2": (
            "monitored environmental protection and usable recovery capacity "
            "under site loss unperformed"
        ),
        "CHECK-SOC2:A1.3": (
            "recorded timing is recalculated where supported; accepted "
            "application RTO/RPO, application age/usability and failover "
            "unperformed"
        ),
        "CHECK-SOC2:CC7.5": (
            "validated restored service, stakeholder communications, root cause "
            "and preventive change unperformed"
        ),
        "CHECK-SOC2:CC9.1": (
            "declared dependencies and local treatment examined; authorized "
            "residual-risk acceptance unperformed"
        ),
        "ACTION-H-EMERGENCY": (
            "ePHI emergency access by authorized operators and preserved "
            "access/activity logs unperformed"
        ),
        "TOD": (
            "effective corporate design, all failure routes and source "
            "applicability acceptance unperformed beyond selected declarations"
        ),
        "IMPLEMENTATION": (
            "dated selected local settings/actions examined; all authored steps "
            "across scoped corporate services unperformed"
        ),
        "TOE": (
            "selected native history examined; full-year due/trigger denominator, "
            "independently accepted objectives and qualified operating "
            "effectiveness unperformed"
        ),
    }[clause]
    rows.append(
        {
            "attribute": task["authored_instruction"],
            "status": "PARTIAL_OR_UNPERFORMED_EXACT_TASK",
            "basis": additional,
            "native_originals": [],
        }
    )
    if control == "SH-BCM-003" and clause == "TOE":
        performed = [
            r
            for r in local_restore["selected_occurrences"]
            if r.get("real_isolated_byte_restore_performed")
        ]
        rows.append(
            {
                "attribute": (
                    "isolated selected configuration copy, byte comparisons, typed JSON "
                    "read and attributable checkpoint age"
                ),
                "status": "BOUNDED_REPERFORMANCE" if performed else "SUPPORT_UNAVAILABLE",
                "basis": (
                    "ACCEPTED_LOCAL_CONFIGURATION_PREDICATE_ONLY_NOT_AUGUST_MARKER_OR_APP"
                    "LICATION_RESTORE"
                ),
                "native_originals": [r["selected_restore"] for r in performed],
            }
        )
    return rows


def examine(records, *, as_of, scratch_root):
    selected_tasks, task_contracts = task_plan(), contracts()
    history = History(records, as_of)
    bia, backup, restore = (
        _bia(history),
        _schedule(history, "SH-BCM-002"),
        _schedule(history, "SH-BCM-003"),
    )
    monitor, timing = _monitor(history), _timestamp(history)
    local_restore = _restores(history, scratch_root)
    inspections = []
    anchors = history.rows[:1]
    for task in selected_tasks:
        control, clause, kind = (
            task["control_id"],
            task["task_id"].split("-corporate-", 1)[1],
            task["kind"],
        )
        if control == "SH-BCM-001":
            roles = {
                "TOD": {
                    "authority_decision",
                    "technical_objectives",
                    "business_impact",
                    "service_inventory",
                },
                "IMPLEMENTATION": {"business_impact", "technical_objectives", "service_inventory"},
                "TOE": {"business_impact", "exercise_review", "closure_gate"},
            }
            selected = history.selected(
                "bcm",
                roles.get(
                    clause,
                    {"demand_forecast", "service_inventory"}
                    if clause.endswith("A1.1")
                    else {
                        "service_inventory",
                        "technical_objectives",
                        "corrective_action",
                        "closure_gate",
                    },
                ),
            )
            facts = {
                "TOD": {k: bia[k] for k in ("authority", "impact", "technical", "inventory")},
                "IMPLEMENTATION": {k: bia[k] for k in ("impact", "technical", "inventory")},
                "TOE": {
                    "dated_business_impact_versions": bia["impact"],
                    "annual_business_acceptance_tested": False,
                    "material_change_review_denominator_established": False,
                },
                "CHECK-SOC2:A1.1": {
                    "forecast_capacity_arithmetic": bia["capacity"],
                    "utilization_measurement_tested": False,
                },
                "CHECK-SOC2:CC9.1": {
                    "dependencies": bia["inventory"],
                    "treatment": bia["technical"],
                    "authorized_residual_risk_acceptance_tested": False,
                },
            }[clause]
            exceptions = bia["exceptions"] if clause.endswith("A1.1") else []
        elif control == "SH-BCM-002":
            roles = {
                "TOD": {"runtime_definition", "credential_event"},
                "IMPLEMENTATION": {"runtime_definition", "credential_event", "backup_job"},
                "TOE": {
                    "backup_job",
                    "monitor_scan",
                    "failure_ticket",
                    "monitor_observation",
                    "monitor_ticket",
                },
            }
            selected = history.selected(
                "backup-runtime-history", roles.get(clause, {"runtime_definition", "backup_job"})
            )
            facts = {
                "TOD": {
                    "declarations": backup["population"],
                    "approved_rpo_schedule_established": False,
                    "retention_isolation_configuration": _records(
                        selected,
                        ["datasets", "qualification", "authority", "valid_from", "expires_at"],
                    ),
                },
                "IMPLEMENTATION": {
                    "dated_attempts": backup["population"],
                    "lease_settings": _records(
                        history.selected("backup-runtime-history", {"credential_event"}),
                        ["enabled", "principal_id", "valid_from", "expires_at", "authority"],
                    ),
                },
                "TOE": {
                    "denominator_before_selection": backup,
                    "failure_and_monitor_lineage": monitor,
                },
                "CHECK-SOC2:A1.2": {
                    "local_backup_occurrences": backup["population"],
                    "environmental_protection_and_recovery_capacity_tested": False,
                    "backup_success_does_not_establish_site_recoverability": True,
                },
            }[clause]
            exceptions = backup["exceptions"] if clause in {"IMPLEMENTATION", "TOE"} else []
        elif control == "SH-BCM-003":
            roles = {
                "TOD": {"exercise_plan", "technical_objectives", "business_impact"},
                "IMPLEMENTATION": {"exercise_plan", "exercise_result"},
                "TOE": {"exercise_result", "corrective_action", "closure_gate"},
            }
            selected = history.selected(
                "bcm",
                roles.get(
                    clause,
                    {"exercise_result", "exercise_review", "corrective_action", "closure_gate"},
                ),
            )
            if clause == "TOE":
                selected += history.selected(
                    "backup-runtime-history", {"restore_job", "runtime_definition"}
                )
            facts = {
                "TOD": {
                    "risk_selection_plan": _records(
                        selected,
                        [
                            "scope",
                            "rto_rpo_basis",
                            "approved_emergency_ephi_access",
                            "supplier_and_customer_participation",
                        ],
                    ),
                    "accepted_local_targets": bia["impact"],
                },
                "IMPLEMENTATION": {
                    "dated_plan_and_results": _records(
                        selected,
                        [
                            "scope",
                            "exercise_start_at",
                            "observed_finish_at",
                            "real_application_restored",
                        ],
                    ),
                    "isolated_august_marker_bytes_available": False,
                },
                "TOE": {
                    "local_denominator_before_selection": restore,
                    "actual_local_configuration_reperformance": local_restore,
                    "dated_failure_retest_history": monitor,
                    "recorded_marker_timing": timing,
                },
                "CHECK-SOC2:A1.3": {
                    "recorded_timestamp_reperformance": timing,
                    "accepted_BIA_application_age_usability_tested": False,
                },
                "CHECK-SOC2:CC7.5": {
                    "recovery_review_and_corrective_actions": _records(
                        selected,
                        [
                            "corrective_action_closure_claim",
                            "actions",
                            "historical_bypass_exception_open",
                            "corrective_action_validated",
                            "risk_acceptance",
                        ],
                    ),
                    "root_cause_preventive_change_and_stakeholder_communications_tested": False,
                },
            }[clause]
            exceptions = restore["exceptions"] if clause == "TOE" else []
            if clause.endswith("A1.3"):
                exceptions = [
                    o
                    for o in timing.get("observations", [])
                    if not o["duration_claim_agrees"]
                    or not o["recorded_elapsed_within_declared_rto"]
                ]
                exceptions += timing.get("recorded_interval_chronology_exceptions", [])
        else:
            selected = history.selected(
                "bcm",
                {
                    "exercise_plan",
                    "exercise_result",
                    "exercise_review",
                    "corrective_action",
                    "closure_gate",
                },
            )
            if clause == "ACTION-H-EMERGENCY":
                selected += history.selected(
                    "supplementalops", {"identity_permission", "security_configuration"}
                )
            elif clause in {"IMPLEMENTATION", "TOE"}:
                selected += history.selected(
                    "transition", {"recovery_exercise", "site_release", "site_commissioning"}
                )
            plan_rows = history.selected("bcm", {"exercise_plan"})
            results = history.selected(
                "bcm", {"exercise_result", "exercise_review", "corrective_action", "closure_gate"}
            )
            facts = {
                "TOD": {
                    "exercise_design": _records(
                        plan_rows,
                        [
                            "scope",
                            "supplier_and_customer_participation",
                            "approved_emergency_ephi_access",
                        ],
                    ),
                    "loss_recovery_return_dependencies_design_tested": False,
                },
                "IMPLEMENTATION": {
                    "dated_site_exercise_records": _records(
                        history.selected("transition", {"recovery_exercise"}),
                        ["site", "recorded_local_checks", "actual_phi_processing"],
                    ),
                    "supplier_customer_and_return_execution_tested": False,
                },
                "TOE": {
                    "recorded_selected_exercise_timing": timing,
                    "dated_result_review_correction_versions": _records(
                        results,
                        [
                            "exercise_start_at",
                            "observed_finish_at",
                            "actions",
                            "corrective_action_validated",
                            "historical_bypass_exception_open",
                        ],
                    ),
                    "annual_and_material_change_exercise_denominator_established": False,
                },
                "ACTION-H-EMERGENCY": {
                    "declared_emergency_scope": _records(
                        plan_rows, ["approved_emergency_ephi_access", "scope"]
                    ),
                    "local_policy_settings": _records(
                        history.selected(
                            "supplementalops", {"security_configuration", "identity_permission"}
                        ),
                        ["setting_id", "activation_scope", "approved_values", "observed_values"],
                    ),
                    "ephi_access_activity_and_authorized_operator_execution_tested": False,
                },
                "CHECK-SOC2:A1.3": {
                    "recorded_failover_exercise_timing": timing,
                    "site_failure_capacity_and_return_reperformed": False,
                },
                "CHECK-SOC2:CC9.1": {
                    "dependencies": bia["inventory"],
                    "exercise_treatments": _records(
                        results,
                        [
                            "actions",
                            "capacity_treatment_open",
                            "risk_acceptance",
                            "historical_bypass_exception_open",
                        ],
                    ),
                    "supplier_customer_residual_risk_acceptance_tested": False,
                },
            }[clause]
            exceptions = []
        support_missing = not selected
        selected = selected or anchors
        coverage = _coverage(task, history, local_restore)
        factual_keys = {_key(ref) for _, ref in _refs([facts, coverage])}
        supporting = [r for r in history.rows if _key(r["source"]) in factual_keys]
        selected = list({r["artifact_id"]: r for r in [*selected, *supporting]}.values())
        while True:
            native_keys = {_key(r["source"]) for r in selected}
            joins = [j for j in history.joins if _key(j["origin"]) in native_keys]
            targets = {_key(j["target"]) for j in joins if j["target"] is not None}
            linked = [r for r in history.rows if _key(r["source"]) in targets - native_keys]
            if not linked:
                break
            selected.extend(linked)
        observation = _observation(
            clause,
            {
                "exact_authored_attribute": task["authored_instruction"],
                "task_kind": kind,
                "examined_attributes": facts,
                "bounded_exceptions": exceptions,
                "full_clause_performed": False,
            },
            selected,
            status="EXCEPTION_RECORDED"
            if exceptions
            else ("SUPPORT_UNAVAILABLE" if support_missing else "OBSERVED"),
        )
        cited = {r["artifact_id"]: r for r in selected}
        observations = [
            observation,
            *_occurrence_observations(
                task, history, backup, restore, timing, local_restore, selected
            ),
        ]
        if joins:
            observations.append(
                _observation(
                    "EXACT-NATIVE-SUPPORT",
                    {"joins": joins},
                    selected,
                    status="SUPPORT_UNAVAILABLE"
                    if any(j["status"] != "EXACT_AVAILABLE_ORIGINAL" for j in joins)
                    else "OBSERVED",
                )
            )
        for start in range(20, len(selected), 20):
            chunk = selected[start : start + 20]
            observations.append(
                _observation(
                    f"SOURCE-SUPPORT-{start // 20 + 1}",
                    {"exact_support_originals": [reference(r["source"]) for r in chunk]},
                    chunk,
                )
            )
        contract = task_contracts[task["task_id"]]
        inspections.append(
            {
                "task_id": task["task_id"],
                "artifact_ids": list(cited),
                "observations": observations,
                "performed": contract["performed"],
                "unperformed": contract["unperformed"],
                "result": {
                    "schema": "SH_COLLECTED_CONTINUITY_TASK_EXAMINATION_V1",
                    "task_id": task["task_id"],
                    "examined_attributes": facts,
                    "attribute_coverage": coverage,
                    "exceptions": exceptions,
                    "native_support": joins,
                    "population_basis": (
                        "COLLECTED_EXACT_TASK_SPECIFIC_NATIVE_RECORDS_AND_DECLARED_OCCURRENCES"
                    ),
                    "selected_source_versions": [reference(r["source"]) for r in selected],
                    "broader_unperformed": BROAD,
                    "prior_auditor_outcomes_used": False,
                },
                "disposition": {
                    "status": "IN_PROGRESS",
                    "conclusion": "FAIL" if exceptions else "LIMITATION",
                    "rationale": (
                        "Bounded source attribute exceptions remain; "
                        "broader exact-clause coverage unperformed."
                    )
                    if exceptions
                    else (
                        "Selected original attributes examined; "
                        "explicit source and broader scope limitations remain."
                    ),
                },
            }
        )
    return inspections
