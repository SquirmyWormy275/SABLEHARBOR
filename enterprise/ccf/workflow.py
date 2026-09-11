"""Reusable synthetic evidence/review/exception transitions with no production authority."""

from __future__ import annotations

import copy
from datetime import date, datetime, timezone

from enterprise.ccf.registry import digest
from enterprise.operations.controls import OPTIONAL
from enterprise.operations.controls import evaluate as finance_evaluate
from enterprise.runtime.security import restore

ORIGIN = "PUBLIC_SYNTHETIC_EXERCISE"
REQUIRED = {
    "finance": ("events", "journal", "subledger_rollforward"),
    "identity": ("hr", "accounts", "entitlements"),
    "recovery": ("services", "backups", "restores"),
}


def instant(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("Evidence timestamps require timezone offsets")
    return result.astimezone(timezone.utc)


def authorized(actors, actor, permission, boundary, at):
    date.fromisoformat(at)
    candidates = [r for r in actors if r["id"] == actor]
    if len(candidates) != 1:
        return False
    row = candidates[0]
    date.fromisoformat(row["effective_from"])
    if row["effective_to"] is not None:
        date.fromisoformat(row["effective_to"])
    return (
        permission in row["permissions"]
        and boundary in row["boundaries"]
        and row["effective_from"] <= at
        and (row["effective_to"] is None or at < row["effective_to"])
    )


def finance(tables, case):
    populations = {**tables, **{key: [] for key in OPTIONAL["LC-REVENUE"] if key not in tables}}
    outcome, reason, checks = finance_evaluate("LC-REVENUE", populations)
    return outcome, [reason], checks


def identity(tables, case):
    failures, checks = [], 0

    def check(condition, reason):
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(reason)

    hr = {r["worker_id"]: r for r in tables["hr"]}
    check(len(hr) == len(tables["hr"]), "Duplicate worker lifecycle state")
    for account in tables["accounts"]:
        check(account["worker_id"] in hr, "Orphan account without scoped worker authority")
        check(type(account["enabled"]) is bool, "Account enabled flag must be boolean")
    accounts = {r["id"]: r for r in tables["accounts"]}
    for grant in tables["entitlements"]:
        check(grant["account_id"] in accounts, "Orphan entitlement")
        check(type(grant["active"]) is bool, "Entitlement active flag must be boolean")
    for worker in hr.values():
        if worker["contract_end"] is not None:
            date.fromisoformat(worker["contract_end"])
        linked = [r for r in tables["accounts"] if r["worker_id"] == worker["worker_id"]]
        check(len(linked) == 1, "Worker/account correlation must be unique and complete")
        ended = worker["event"] == "terminate" or bool(
            worker["contract_end"] and worker["contract_end"] <= case["period_end"]
        )
        check(
            worker["event"] in {"join", "move", "terminate", "contract_expiry"},
            "Unsupported lifecycle event",
        )
        for account in linked:
            grants = [
                r
                for r in tables["entitlements"]
                if r["account_id"] == account["id"] and r["active"] is True
            ]
            if ended:
                check(account["enabled"] is False, "Ended worker has enabled account")
                check(not grants, "Ended worker retains entitlements")
                check(
                    account["changed_at"] is not None
                    and instant(account["changed_at"]) <= instant(worker["disable_due_at"]),
                    "Disablement exceeds exercise deadline",
                )
            else:
                check(account["enabled"] is True, "Active worker lacks enabled account")
                check(
                    set(r["entitlement"] for r in grants) == set(worker["approved_entitlements"]),
                    "Access differs from approved new role; mover removal required",
                )
                check(worker["approved"] is True, "Role/access request lacks approval")
    return ("FAIL" if failures else "PASS"), failures, checks


def recovery(tables, case):
    failures, checks = [], 0

    def check(condition, reason):
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(reason)

    restored_by_service = {r["service_id"]: r for r in tables["restores"]}
    services = {r["id"] for r in tables["services"]}
    check(
        all(r["service_id"] in services for name in ("backups", "restores") for r in tables[name]),
        "Orphan recovery evidence",
    )
    for service in tables["services"]:
        backups = [r for r in tables["backups"] if r["service_id"] == service["id"]]
        restorations = [r for r in tables["restores"] if r["service_id"] == service["id"]]
        check(
            len(backups) == len(restorations) == 1,
            "Required service lacks unique backup and restore evidence",
        )
        if len(backups) != 1 or len(restorations) != 1:
            continue
        backup, restored = backups[0], restorations[0]
        check(
            backup["artifact_sha256"] == digest(backup["records"]), "Backup artifact hash mismatch"
        )
        expected = restore(backup["records"], set(service["tombstones"]))
        check(
            restored["records"] == expected,
            "Restore differs from authorized content or resurrects suppressed data",
        )
        start, finish, point = (
            instant(restored[k]) for k in ("started_at", "completed_at", "recovery_point_at")
        )
        for field in ("rto_seconds", "rpo_seconds"):
            check(
                type(service[field]) is int and service[field] >= 0,
                "Invalid exercise recovery target",
            )
        check(
            0 <= (finish - start).total_seconds() <= service["rto_seconds"],
            "Restore exceeds exercise RTO or reverses time",
        )
        check(
            0 <= (start - point).total_seconds() <= service["rpo_seconds"],
            "Recovery point exceeds exercise RPO or is in future",
        )
        for dependency in service["dependency_ids"]:
            dep = restored_by_service.get(dependency)
            check(
                dependency in services
                and dep is not None
                and instant(dep["completed_at"]) <= start,
                "Recovery dependency incomplete at restore start",
            )
    return ("FAIL" if failures else "PASS"), failures, checks


ADAPTERS = {"finance": finance, "identity": identity, "recovery": recovery}


def collect(case, actors, actor, at, tables=None, attachments=None):
    """Expected IDs are declared by the schedule, independently of attached rows."""
    if case["origin"] != ORIGIN or case["kind"] not in REQUIRED:
        raise ValueError("Unsupported origin or control adapter")
    if not authorized(actors, actor, "prepare", case["boundary_id"], at):
        raise ValueError("Unauthorized preparer")
    date.fromisoformat(case["period_start"])
    date.fromisoformat(case["period_end"])
    if at < case["period_end"] or case["period_start"] > case["period_end"]:
        raise ValueError("Collection before period end or invalid period")
    tables = copy.deepcopy(case["tables"] if tables is None else tables)
    required = set(REQUIRED[case["kind"]])
    if set(tables) != required or set(case["expected_ids"]) != required:
        raise ValueError("Unknown/missing population table")
    attachments = required if attachments is None else set(attachments)
    if not attachments <= required:
        raise ValueError("Unknown attachment")
    manifests, limitations = [], []
    for name in sorted(required):
        rows = tables[name]
        for row in rows:
            date.fromisoformat(row["effective_on"])
        ids = [r["id"] for r in rows]
        expected = case["expected_ids"][name]
        if len(expected) != len(set(expected)) or not expected:
            raise ValueError("Expected population must have unique nonempty IDs")
        in_scope = all(
            r["boundary_id"] == case["boundary_id"]
            and r["scenario"] == case["scenario"]
            and case["period_start"] <= r["effective_on"] <= case["period_end"]
            for r in rows
        )
        complete = (
            len(ids) == len(set(ids))
            and set(ids) == set(expected)
            and in_scope
            and name in attachments
        )
        if not complete:
            limitations.append(f"Incomplete or wrong-scope population: {name}")
        manifests.append(
            dict(
                table=name,
                expected_ids=sorted(expected),
                observed_ids=sorted(ids),
                count=len(rows),
                sha256=digest(rows),
                attached=name in attachments,
                complete=complete,
                source=f"{case['id']}:{name}",
                period_start=case["period_start"],
                period_end=case["period_end"],
                timezone="UTC",
                filters={"boundary_id": case["boundary_id"], "scenario": case["scenario"]},
                pagination="FULL_DECLARED_FIXTURE_POPULATION",
                transformations=[],
                origin=ORIGIN,
            )
        )
    if limitations:
        outcome, reasons, assertions = "NOT_RUN", limitations, 0
    else:
        try:
            outcome, reasons, assertions = ADAPTERS[case["kind"]](tables, case)
        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
            outcome, reasons, assertions = (
                "NOT_RUN",
                [f"Unsupported evidence: {type(exc).__name__}"],
                0,
            )
    result = dict(
        case_id=case["id"],
        implementation_id=case["implementation_id"],
        boundary_id=case["boundary_id"],
        period_start=case["period_start"],
        period_end=case["period_end"],
        scenario=case["scenario"],
        collected_on=at,
        preparer=actor,
        outcome=outcome,
        reasons=reasons,
        assertions=assertions,
        manifests=manifests,
        contract={
            k: copy.deepcopy(case[k])
            for k in (
                "id",
                "kind",
                "implementation_id",
                "boundary_id",
                "period_start",
                "period_end",
                "scenario",
                "origin",
                "expected_ids",
            )
        },
        tables=tables,
        origin=ORIGIN,
        operating_effectiveness="NOT_ASSERTED",
    )
    result["evidence_id"] = digest(result)
    return result


def verify_evidence(evidence):
    body = {k: v for k, v in evidence.items() if k != "evidence_id"}
    if digest(body) != evidence["evidence_id"]:
        raise ValueError("Evidence content identity changed")
    if evidence["origin"] != ORIGIN or evidence["operating_effectiveness"] != "NOT_ASSERTED":
        raise ValueError("Synthetic evidence cannot be promoted")
    for manifest in evidence["manifests"]:
        if digest(evidence["tables"][manifest["table"]]) != manifest["sha256"]:
            raise ValueError("Population hash mismatch")

    # Reperform independently of supplied outcome and completeness labels.
    actor = dict(
        id=evidence["preparer"],
        permissions=["prepare"],
        boundaries=[evidence["boundary_id"]],
        effective_from=evidence["collected_on"],
        effective_to=None,
    )
    expected = collect(
        evidence["contract"],
        [actor],
        actor["id"],
        evidence["collected_on"],
        tables=evidence["tables"],
        attachments=[m["table"] for m in evidence["manifests"] if m["attached"]],
    )
    if expected != evidence:
        raise ValueError("Evidence assertion or manifest differs from re-performance")


def review(evidence, actors, actor, at):
    verify_evidence(evidence)
    if at < evidence["collected_on"]:
        raise ValueError("Review before collection")
    if actor == evidence["preparer"] or not authorized(
        actors, actor, "review", evidence["boundary_id"], at
    ):
        raise ValueError("Unauthorized or non-independent review")
    return dict(
        evidence_id=evidence["evidence_id"],
        reviewer=actor,
        reviewed_on=at,
        conclusion=evidence["outcome"],
        operating_effectiveness="NOT_ASSERTED",
    )


def open_exception(evidence, actors, actor, at, expires, reason, risk, compensation):
    verify_evidence(evidence)
    if evidence["outcome"] == "PASS" or not all((reason, risk, compensation)):
        raise ValueError(
            "Exception requires a nonpassing original result, reason, risk and compensation"
        )
    if actor == evidence["preparer"] or not authorized(
        actors, actor, "approve", evidence["boundary_id"], at
    ):
        raise ValueError("Unauthorized exception approver")
    date.fromisoformat(expires)
    if not evidence["collected_on"] <= at < expires:
        raise ValueError("Invalid exception chronology")
    return dict(
        exception_id="EX-" + evidence["evidence_id"][:16],
        original=copy.deepcopy(evidence),
        state="WAIVER_ACTIVE",
        waiver_state="ACTIVE",
        expires_on=expires,
        reason=reason,
        risk=risk,
        compensation=compensation,
        transitions=[dict(state="WAIVER_ACTIVE", actor=actor, at=at)],
        remediation=None,
        retest=None,
    )


def advance(exception, at):
    date.fromisoformat(at)
    result = copy.deepcopy(exception)
    if at < result["transitions"][-1]["at"]:
        raise ValueError("Lifecycle time cannot reverse")
    if (
        at >= result["expires_on"]
        and result["waiver_state"] == "ACTIVE"
        and result["state"] != "CLOSED"
    ):
        result["waiver_state"] = "EXPIRED"
        if result["state"] == "WAIVER_ACTIVE":
            result["state"] = "EXPIRED_ESCALATED"
        result["transitions"].append(dict(state="EXPIRED_ESCALATED", actor="SYSTEM", at=at))
    return result


def remediate(exception, actors, actor, at, change_reference):
    result = advance(exception, at)
    if result["state"] not in {"WAIVER_ACTIVE", "EXPIRED_ESCALATED"} or not change_reference:
        raise ValueError("Invalid remediation transition")
    if not authorized(actors, actor, "prepare", result["original"]["boundary_id"], at):
        raise ValueError("Unauthorized remediation")
    result["state"] = "VALIDATION_PENDING"
    result["remediation"] = dict(actor=actor, at=at, change_reference=change_reference)
    result["transitions"].append(dict(state=result["state"], actor=actor, at=at))
    return result


def close(exception, retest, actors, actor, at):
    result = advance(exception, at)
    if result["state"] != "VALIDATION_PENDING":
        raise ValueError("Closure requires submitted remediation")
    original = result["original"]
    verify_evidence(original)
    reviewed = review(retest, actors, actor, at)
    if actor in {original["preparer"], result["remediation"]["actor"]}:
        raise ValueError("Remediator/original preparer cannot close")
    for key in (
        "case_id",
        "implementation_id",
        "boundary_id",
        "period_start",
        "period_end",
        "scenario",
    ):
        if original[key] != retest[key]:
            raise ValueError("Retest must address original scope and period")
    if retest["collected_on"] < result["remediation"]["at"]:
        raise ValueError("Retest predates remediation")

    def expected(e):
        return {m["table"]: m["expected_ids"] for m in e["manifests"]}

    if expected(original) != expected(retest):
        raise ValueError("Retest changed the expected original population")
    result["state"] = (
        "CLOSED"
        if retest["outcome"] == "PASS" and all(m["complete"] for m in retest["manifests"])
        else "VALIDATION_PENDING"
    )
    result["retest"] = dict(
        review=reviewed,
        evidence=copy.deepcopy(retest),
        original_evidence_id=original["evidence_id"],
        corrected_evidence_id=retest["evidence_id"],
    )
    result["transitions"].append(dict(state=result["state"], actor=actor, at=at))
    return result
