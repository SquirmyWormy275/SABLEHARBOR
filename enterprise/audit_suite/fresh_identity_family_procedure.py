"""Fresh paired IAM-family performance from company-owned source histories.

Only authored methods/task membership transfer from historical indices. Company
sources remain original ordinary-byte copies; no old audit evidence or Key is read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .company_federation import QUALIFICATION, load_profile
from .company_federation import SCHEMA as PORTFOLIO_SCHEMA
from .company_store import CompanyStore, CompanyStoreError, _time
from .documentary_283_route_reconciliation_v6 import _p1_inventory
from .engine import Engine
from .fictional_2027_candidate_registry import _private
from .fictional_2027_collection_probe import _ordinary_copy
from .fresh_sec003_procedure import (
    CLOCK_ID,
    FREEZE,
    NATIVE_ID,
    PROGRAM_PACK,
    PROGRAM_PACK_SHA,
    ProcedureError,
    _baseline,
    business_digest,
    discover_history,
    read_only,
    require,
    sha,
    verify_audit_journal,
    write,
)
from .organization import snapshot
from .population_lifecycle import population, selection
from .store import digest

SCHEMA = "SH_FRESH_IDENTITY_FAMILY_PROCEDURE_V1"
SPEC = "enterprise/audit_suite/fresh_identity_family_spec_v1.json"
SPEC_SHA = "a78d293a45d450e4202ddc535b8cd60d30aecf80f90c0e4f92e91c813f722b35"
INITIAL = "2027-12-31T09:00:00+00:00"
AS_OF = "2028-01-15T09:00:00+00:00"
COMPANY = "SABLEHARBOR-FRESH-IDENTITY"
SOURCE_CENSUS_PURPOSE = (
    "Exact authored task visible native history census; no enterprise extrapolation"
)
CROSSWALK = (
    "enterprise/generated/audit-suite/procedure-method-crosswalk-2026-10-01/main-run-v1/REPORT.json"
)
CROSSWALK_SHA = "8f7933dd06ffdd80a60d559e06725bbeda22575f9ac9c4d10b7c43c16874ad04"
HISTORICAL = (
    "enterprise/generated/audit-suite/acceptance-audit-2026-09-22/operating"
    "-actual-coverage-final-v1/RECEIPT.json"
)
HISTORICAL_SHA = "88550a25478253867a4ed85fd3ff5aca3537c88807349e682ab10b0e91f9d908"
CRITERIA = "enterprise/ccf/assurance/design_data/control_procedures.json"
CRITERIA_SHA = "258f5c868e16f3dc197594857dc86a4f2b3ef11e3e5a36dd0a80a9fc6d40c679"
UPSTREAM = {"phi", "bcm", "security"}
METHOD_FIELDS = (
    "id",
    "title",
    "kind",
    "test",
    "control_id",
    "boundary_id",
    "owner_id",
    "requirement_ids",
)
CHANNELS = {
    "directory_account",
    "application_account",
    "application_session",
    "api_token",
    "remote_session",
    "physical_badge",
}
COMMON_LIMITS = [
    (
        "Visible component populations are fictional local histories, not an "
        "authoritative enterprise workforce census."
    ),
    (
        "52 canonical people and 15 proposed contacts are separate from the "
        "two declared mover subjects and synthetic identities."
    ),
    (
        "No actual employment, usable credential, vendor deployment, real ePHI "
        "or external opinion is established."
    ),
    (
        "Historical due-window failures remain after later corrections; no "
        "missing review or authority is supplied by audit authorship."
    ),
    (
        "Independent substantive reviewer acceptance remains pending; "
        "source/import/custody verification is not professional sufficiency."
    ),
]


def command(engine, actor, eid, kind, payload, serial):
    state = engine.store.get(actor, eid)
    return engine.command(
        actor,
        eid,
        {
            "command_id": f"IAM-FRESH-{serial}-{kind}",
            "expected_revision": state["revision"],
            "kind": kind,
            "payload": payload,
        },
    )


def discover_components(store, auditor, eid, profile, components, selected, *, as_of):
    """Keep distinct physical stores even when they share one local object tuple."""
    rows, pages = [], []
    for key in sorted(selected):
        c = components[key]
        found, paged = discover_history(
            store,
            auditor,
            eid,
            COMPANY,
            profile,
            as_of=as_of,
            systems=[c["namespace"] + ":" + s for s in c["systems"]],
            page_size=10,
        )
        for r in found:
            r["component"] = key
        rows.extend(found)
        pages.extend({"component": key, **p} for p in paged)
    return rows, pages


def projected(row, artifact=None):
    try:
        doc = json.loads(row["content"])
    except (ValueError, UnicodeError):
        doc = None  # The native local object is bytes, not an invented JSON document.
    item = {
        "source": {k: row[k] for k in CLOCK_ID},
        "document": doc,
        "content_bytes": len(row["content"]),
        "component": row["component"],
    }
    if artifact:
        item.update(
            artifact_id=artifact["id"],
            artifact_sha256=artifact["sha256"],
            receipt=artifact["source"]["receipt"],
            artifact_version=artifact.get("version"),
            artifact_status=artifact["status"],
        )
        # Custody/provenance is retained once in receipt. Repeat only the exact
        # native identity/clocks in each population item and attribute trace.
        # Producer provenance can include a large recipe and is not a sample
        # observation; repeating it can exceed the supported command bound.
        item["source"] = {k: artifact["source"]["receipt"]["source"][k] for k in CLOCK_ID}
    return item


def one(rows, component, system, record, version=1):
    found = [
        r
        for r in rows
        if r["component"] == component
        and r["source"]["system"] == system
        and r["source"]["record"] == record
        and r["source"]["version"] == version
    ]
    require(
        len(found) == 1, f"Exact source row unavailable: {component}/{system}/{record}/{version}"
    )
    return found[0]


def body(rows, component, system, record, version=1):
    return one(rows, component, system, record, version)["document"]


def native_refs(value):
    if isinstance(value, dict):
        if {"company", "branch", "system", "record", "version", "sha256"} <= value.keys():
            yield value
        for child in value.values():
            yield from native_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from native_refs(child)


def check_links(rows):
    """Resolve exact observed native joins; never substitute a similarly named row."""
    index = {}
    for r in rows:
        index.setdefault(tuple(r["source"][k] for k in NATIVE_ID), []).append(r)
    checked, missing = [], []
    for row in rows:
        for ref in native_refs(row["document"]):
            key = tuple(ref[k] for k in NATIVE_ID)
            candidates = index.get(key, [])
            if len(candidates) > 1:
                candidates = [r for r in candidates if r["component"] == row["component"]]
            require(len(candidates) <= 1, "Ambiguous physical native join")
            target = candidates[0] if candidates else None
            if target is None:
                missing.append(
                    {
                        "from": row["source"],
                        "reference": ref,
                        "disposition": "UNRESOLVED_SOURCE_JOIN_NOT_ASSUMED",
                    }
                )
                continue
            require(target["source"]["sha256"] == ref["sha256"], "Native join byte hash differs")
            for name in ("event_at", "available_at", "imported_at"):
                if name in ref:
                    require(target["source"][name] == ref[name], "Native join clock differs")
            require(
                _time(target["source"]["available_at"]) <= _time(row["source"]["event_at"]),
                "Native join uses a future source",
            )
            checked.append({"from": row["source"], "to": target["source"]})
        doc = row["document"] or {}
        # Some producers expose predecessor locators without company/branch.
        for name in ("source_previous", "previous_source"):
            ref = doc.get(name)
            if not ref:
                continue
            found = [
                r
                for r in rows
                if r["component"] == row["component"]
                and r["source"]["record"] == ref["record"]
                and r["source"]["sha256"] == ref["sha256"]
                and ("system" not in ref or r["source"]["system"] == ref["system"])
            ]
            if not found and row["component"] in UPSTREAM:
                missing.append(
                    {
                        "from": row["source"],
                        "reference": ref,
                        "disposition": "UPSTREAM_PREDECESSOR_OUTSIDE_EXACT_JOIN_SELECTION",
                    }
                )
                continue
            require(len(found) == 1, "Native predecessor is absent or ambiguous")
            require(
                _time(found[0]["source"]["available_at"]) <= _time(row["source"]["event_at"]),
                "Future native predecessor",
            )
    return {"checked": checked, "unresolved": missing}


def analyze(rows, canon, *, as_of):
    """Recalculate approvals, permissions and four quarter windows from originals."""
    require(
        len(rows) == len({(r["component"], *(r["source"][k] for k in NATIVE_ID)) for r in rows}),
        "Duplicate observed native version",
    )
    for row in rows:
        s = row["source"]
        require(
            _time(s["event_at"]) <= _time(s["available_at"]) <= _time(as_of),
            "Future/invalid source clocks",
        )
    people = {p["person_id"]: p for p in canon["canonical_people"]}
    require(len(people) == len(canon["canonical_people"]), "Duplicate canonical membership")
    identity = [r for r in rows if r["component"] == "identity"]
    humans = sorted({r["document"]["person_id"] for r in identity if r["source"]["system"] == "hr"})
    require(all(p in people for p in humans), "Human source subject outside canonical membership")
    declared = {
        tuple(r["document"]["declared_employee_ids"])
        for r in identity
        if r["source"]["system"] == "review_population"
    }
    require(
        len(declared) == 1 and set(next(iter(declared))) == set(humans),
        "Declared native cohort differs from HR subjects",
    )
    movers = []
    for hr in [
        r for r in identity if r["source"]["system"] == "hr" and r["source"]["version"] == 3
    ]:
        d = hr["document"]
        cause = d["cause_id"]
        auth = d["transfer_authorization"]
        pending = body(rows, "identity", "hr", cause + "-hr", 2)["pending_transfer"]
        require(pending["approval_id"] == auth["approval_id"], "Mover prior authorization differs")
        require(
            _time(auth["approved_at"]) < _time(auth["effective_at"]), "Mover approval is not prior"
        )
        attributes = []
        for system, field, added, removed in (
            ("directory", "groups", "add_right", "remove_right"),
            ("application", "rights", "add_right", "remove_right"),
            ("site_access", "sites", "add_site", "remove_site"),
        ):
            old = one(rows, "identity", system, cause + "-" + system, 1)
            new = one(rows, "identity", system, cause + "-" + system, 2)
            require(
                new["document"]["person_id"] == d["person_id"]
                and new["document"]["authorization_id"] == auth["approval_id"],
                "Mover subject/approval join differs",
            )
            expected = (set(old["document"][field]) - {auth[removed]}) | {auth[added]}
            observed = set(new["document"][field])
            require(
                _time(auth["effective_at"]) <= _time(new["source"]["event_at"]),
                "Provisioning precedes effective time",
            )
            attributes.append(
                {
                    "system": system,
                    "expected": sorted(expected),
                    "observed": sorted(observed),
                    "excess": sorted(observed - expected),
                    "missing": sorted(expected - observed),
                    "before": old["source"],
                    "after": new["source"],
                }
            )
        review = body(rows, "identity", "access_review", cause + "-access_review")
        actual_excess = next(a["excess"] for a in attributes if a["system"] == "application")
        require(
            actual_excess == sorted(review["unapproved_remaining_rights"]),
            "Mover review contradicts effective application rights",
        )
        movers.append(
            {
                "id": cause,
                "person_id": d["person_id"],
                "role": d["role"],
                "approval": auth,
                "attributes": attributes,
                "reviewer_distinct": review["reviewed_by"] != auth["approved_by"],
                "review_followup": review["followup_status"],
                "exception": any(a["excess"] or a["missing"] for a in attributes),
            }
        )
    quarters = []
    for q, cutoff in enumerate(
        (
            "2027-04-01T00:00:00Z",
            "2027-07-01T00:00:00Z",
            "2027-10-01T00:00:00Z",
            "2028-01-01T00:00:00Z",
        ),
        1,
    ):
        rec = f"PRIV-2027-Q{q}"
        triples = [r for r in identity if r["source"]["record"] == rec]
        if _time(as_of) < _time(cutoff):
            require(not triples, "Future quarter review leaked into earlier audit")
            quarters.append(
                {
                    "id": rec,
                    "cutoff": cutoff,
                    "state": "NOT_YET_DUE_RIGHT_CENSORED",
                    "expected_people": None,
                }
            )
            continue
        require(
            {r["source"]["system"] for r in triples}
            == {"review_population", "review_decisions", "review_reconciliation"},
            "Due quarter triple is missing",
        )
        pop = body(rows, "identity", "review_population", rec)
        decisions = body(rows, "identity", "review_decisions", rec)
        recon = body(rows, "identity", "review_reconciliation", rec)
        latest = {}
        for r in identity:
            if r["source"]["system"] != "application" or _time(
                r["source"]["available_at"]
            ) >= _time(cutoff):
                continue
            key = r["document"]["person_id"]
            if key not in latest or r["source"]["version"] > latest[key]["source"]["version"]:
                latest[key] = r
        expected = sorted(latest)
        supplied = [m["person_id"] for m in pop["members"]]
        require(len(supplied) == len(set(supplied)), "Duplicate review member")
        for m in pop["members"]:
            app = latest.get(m["person_id"])
            require(
                app is not None
                and all(m[k] == app["source"][k] for k in ("record", "version", "sha256"))
                and m["rights"] == app["document"]["rights"],
                "Review member does not join latest actual application",
            )
        require(
            digest(pop["members"]) == pop["membership_sha256"], "Review membership hash differs"
        )
        require(
            decisions["population_sha256"]
            == one(rows, "identity", "review_population", rec)["source"]["sha256"]
            == recon["population_sha256"],
            "Review triple population hash differs",
        )
        missing = sorted(set(expected) - set(supplied))
        require(
            missing == recon["missing_person_ids"],
            "Company count reconciliation conceals missing actual account",
        )
        require(
            {d["person_id"] for d in decisions["decisions"]} == set(supplied),
            "Owner decisions do not cover supplied population",
        )
        excess, removals = [], []
        for decision in decisions["decisions"]:
            app = latest[decision["person_id"]]
            auth = body(rows, "identity", "hr", app["document"]["cause_id"] + "-hr", 3)[
                "transfer_authorization"
            ]
            expected_rights = {auth["add_right"]}
            observed = set(app["document"]["rights"])
            require(
                decision["observed_rights"] == app["document"]["rights"]
                and set(decision["authorized_rights"]) == expected_rights,
                "Review decision misstates permission/authority",
            )
            extra = sorted(observed - expected_rights)
            require(
                extra == decision["remove_rights"],
                "Review removal decision differs from excess rights",
            )
            if extra:
                excess.append({"person_id": decision["person_id"], "rights": extra})
                removals.append(
                    {
                        "person_id": decision["person_id"],
                        "confirmation": decision["removal_confirmation"],
                        "state": "NOT_CONFIRMED_IN_THIS_SOURCE_COMPONENT",
                    }
                )
        quarters.append(
            {
                "id": rec,
                "cutoff": cutoff,
                "state": "OBSERVED_WITH_EXCEPTION"
                if missing or excess
                else "OBSERVED_SELECTED_COHORT",
                "expected_people": expected,
                "supplied_people": sorted(supplied),
                "missing_people": missing,
                "excess": excess,
                "removals": removals,
                "population": one(rows, "identity", "review_population", rec)["source"],
                "reviewer": recon["reviewed_by"],
            }
        )
    request = body(rows, "lifecycle", "worker_requests", "REQUEST")
    create = body(rows, "lifecycle", "identity_events", "CREATE")
    approval = body(rows, "lifecycle", "access_approvals", "APPROVAL")
    catalogue = body(rows, "lifecycle", "access_approvals", "LOCAL-CATALOG")
    provision = body(rows, "lifecycle", "identity_events", "PROVISION")
    require(
        request["approved"] is True
        and create["request_id"] == request["request_id"]
        and create["created_identity"] == request["subject_id"],
        "Unapproved/mismatched worker creation",
    )
    require(
        _time(request["recorded_at"]) < _time(create["recorded_at"])
        and _time(approval["recorded_at"]) < _time(provision["recorded_at"]),
        "Worker pre-issue approval differs",
    )
    require(
        approval["reviewer_id"] != approval["provisioner_id"] and approval["approved"] is True,
        "Provisioning independent approval absent",
    )
    granted = set(provision["entitlement_diff"]["after"])
    approved = set(approval["rights"])
    conflicts = [pair for pair in catalogue["conflicting_rights"] if set(pair) <= granted]
    checkpoint = body(rows, "lifecycle", "access_reconciliation", "CHECKPOINT")
    final = body(rows, "lifecycle", "access_reconciliation", "FINAL-PROBES")
    require(
        set(checkpoint["probes"]) == set(final["probes"]) == CHANNELS,
        "Incomplete expiry channel probes",
    )
    active = sorted(k for k, v in checkpoint["probes"].items() if v == "ALLOW")
    final_active = sorted(k for k, v in final["probes"].items() if v == "ALLOW")
    revocation = body(rows, "lifecycle", "revocation_events", "EXPIRY-REVOCATION")
    require(
        active == sorted(k for k, v in revocation["after"].items() if v),
        "Expiry probe contradicts actual channel state",
    )
    worker = {
        "id": request["subject_id"],
        "sponsor": request["sponsor_person_id"],
        "proofing": request["proofing_check"],
        "unique_selected_request_identity": create["created_identity"] == request["subject_id"],
        "approved": sorted(approved),
        "granted": sorted(granted),
        "excess_grants": sorted(granted - approved),
        "conflicts": conflicts,
        "expiry": request["expires_at"],
        "checkpoint_active_channels": active,
        "final_active_channels": final_active,
        "correction_delay_seconds": int(
            (
                datetime.fromisoformat(_time(final["recorded_at"]))
                - datetime.fromisoformat(_time(request["expires_at"]))
            ).total_seconds()
        ),
        "no_real_identity_document_validation": True,
    }
    nonhuman = []
    for r in rows:
        if r["component"] != "nonhuman" or r["source"]["system"] != "copy_attempts":
            continue
        d = r["document"]
        if "status" in d:
            matched = d["configured_version"] == d["current_credential_version"]
            require(
                (d["status"] == "COPIED") == matched,
                "Copy authorization contradicts credential versions",
            )
            if d["status"] == "COPIED":
                out = one(rows, "nonhuman", "copied_dataset", d["output_ref"]["record"])
                require(
                    out["source"]["sha256"] == d["output_sha256"] == d["input_sha256"]
                    and out["content_bytes"] == d["copied_bytes"],
                    "Service output bytes/hash do not match actual copy",
                )
            else:
                require(
                    d["copied_bytes"] == 0 and d["output_ref"] is None,
                    "Denied service copy emitted bytes",
                )
            nonhuman.append(
                {
                    "id": r["source"]["record"],
                    "status": d["status"],
                    "configured_version": d["configured_version"],
                    "active_version": d["current_credential_version"],
                    "copied_bytes": d["copied_bytes"],
                }
            )
        else:
            require(
                d["authorization"] == "DENY" and d["output_ref"] is None,
                "Forbidden service operation was not denied",
            )
            nonhuman.append(
                {
                    "id": r["source"]["record"],
                    "authorization": d["authorization"],
                    "operation": d["operation"],
                }
            )
    inventory = body(rows, "nonhuman", "identity_inventory", "IDENTITY")
    local = []
    for component, system in (("human", "human_review"), ("service", "service_review")):
        d = body(rows, component, system, "REVIEW-01")
        row = one(rows, component, system, "REVIEW-01")
        timely = _time(row["source"]["event_at"]) <= _time(d["review_due_at"])
        require(
            timely == d["review_timely"] and d["reviewer_id"] != d["operator_id"],
            "Local review timing/objectivity claim contradicts source",
        )
        local.append(
            {
                "component": component,
                "timely": timely,
                "reviewer_distinct": True,
                "open_exception": d["open_timing_exception_id"],
            }
        )
    hobj = one(rows, "human", "local_object", "LOCAL-IAM005-TRACE-OBJECT")
    sobj = one(rows, "service", "local_object", "LOCAL-IAM005-TRACE-OBJECT")
    require(
        hobj["source"]["sha256"] == sobj["source"]["sha256"],
        "Human/service exact-object boundary differs",
    )
    reads = []
    for r in rows:
        if r["component"] not in {"human", "service"}:
            continue
        d = r["document"] or {}
        if "read_bytes" not in d:
            continue
        if d["result"] == "AUTHORIZED":
            require(
                d["read_sha256"] == hobj["source"]["sha256"]
                and d["read_bytes"] == hobj["content_bytes"],
                "Authorized read differs from exact object",
            )
        else:
            require(
                d["result"] == "DENIED" and d["read_bytes"] == 0 and d["read_sha256"] is None,
                "Denied local read emitted bytes",
            )
        reads.append(
            {
                "component": r["component"],
                "id": r["source"]["record"],
                "result": d["result"],
                "bytes": d["read_bytes"],
            }
        )
    emergency = [r for r in rows if r["component"] == "emergency"]
    approver = body(rows, "emergency", "emergency_authority", "APPROVE-EMERGENCY-EXERCISE-01")[
        "actor_person_or_inert_identity_id"
    ]
    er = body(rows, "emergency", "access_review", "REVIEW-ACCESS-01")
    emergency_result = {
        "approved_by": approver,
        "reviewed_by": er["actor_person_or_inert_identity_id"],
        "self_review": approver == er["actor_person_or_inert_identity_id"],
        "decisions": [
            {"id": r["source"]["record"], "decision": r["document"]["decision"]}
            for r in emergency
            if r["source"]["system"] in {"access_decision", "service_activity"}
        ],
        "open_exceptions": [
            r["source"]
            for r in emergency
            if r["source"]["system"] == "exception_register" and r["document"]["decision"] == "OPEN"
        ],
        "marker_not_ephi_flow_or_restored_permission_state": True,
    }
    return {
        "canonical_membership": {
            "people": sorted(people),
            "selected_humans": humans,
            "uncovered_people": sorted(set(people) - set(humans)),
            "enterprise_census_accepted": False,
        },
        "movers": movers,
        "quarters": quarters,
        "worker": worker,
        "service_inventory": inventory,
        "service_attempts": nonhuman,
        "local_review": local,
        "local_reads": reads,
        "emergency": emergency_result,
        "native_links": check_links(rows),
        "audit_support": {
            "quarantined_sources": [
                {"component": r["component"], "native": r["source"]}
                for r in rows
                if r.get("artifact_status") == "QUARANTINED"
            ],
            "quarantine_is_available_evidence": False,
            "source_permission_byte_checks_are_parsed_usability": False,
        },
        "as_of": as_of,
        "limits": COMMON_LIMITS,
    }


def sample_observation(row, result, task_id):
    """An actual per-item attribute observation; failure status survives correction."""
    source, doc = row["source"], row["document"] or {}
    details = {"native": source, "task_id": task_id, "component": row["component"]}
    exception = False
    if row["component"] == "identity":
        matching = [m for m in result["movers"] if source["record"].startswith(m["id"])]
        if matching:
            m = matching[0]
            attributes = [a for a in m["attributes"] if a["system"] == source["system"]]
            details["mover_attributes"] = attributes or {
                "approval": m["approval"],
                "review_followup": m["review_followup"],
            }
            exception = bool(
                attributes
                and any(a["excess"] or a["missing"] for a in attributes)
                and source["version"] == 2
            )
        quarter = next((q for q in result["quarters"] if q["id"] == source["record"]), None)
        if quarter:
            details["quarter_recalculation"] = quarter
            exception = bool(quarter.get("missing_people") or quarter.get("excess"))
    elif row["component"] == "lifecycle":
        details["worker_attribute_test"] = result["worker"]
        exception = source["record"] in {"CHECKPOINT", "EXPIRY-REVOCATION"} and bool(
            result["worker"]["checkpoint_active_channels"]
        )
    elif row["component"] == "nonhuman":
        matching = next(
            (a for a in result["service_attempts"] if a["id"] == source["record"]), None
        )
        details["service_attribute_test"] = matching or {
            "owner": doc.get("owner_id"),
            "identity_id": doc.get("identity_id"),
            "credential_version": doc.get("version", doc.get("credential_version")),
            "purpose": doc.get("purpose"),
        }
        exception = bool(matching and matching.get("status") == "AUTHORIZATION_DENIED")
    elif row["component"] in {"human", "service"}:
        matching = next(
            (
                a
                for a in result["local_reads"]
                if a["component"] == row["component"] and a["id"] == source["record"]
            ),
            None,
        )
        details["local_attribute_test"] = matching or next(
            a for a in result["local_review"] if a["component"] == row["component"]
        )
        exception = (
            source["record"] == "REVIEW-01" and not details["local_attribute_test"]["timely"]
        )
    elif row["component"] == "emergency":
        details["decision"] = doc.get("decision")
        details["actor"] = doc.get("actor_person_or_inert_identity_id")
        exception = (
            source["system"] == "exception_register"
            or source["system"] == "access_review"
            and result["emergency"]["self_review"]
        )
    else:
        details["exact_upstream_join"] = {
            "record": source["record"],
            "sha256": source["sha256"],
            "bounded_only": True,
        }
    return {
        "observation": json.dumps(details, sort_keys=True),
        "status": "SUPPORT_UNAVAILABLE"
        if row.get("artifact_status") == "QUARANTINED"
        else "EXCEPTION_RECORDED"
        if exception
        else "OBSERVED",
    }


def population_rows(evidence):
    return [
        {
            "id": r["component"]
            + "/"
            + r["source"]["system"]
            + "/"
            + r["source"]["record"]
            + "/v"
            + str(r["source"]["version"]),
            "native": r["source"],
        }
        for r in evidence
    ]


def sample_items(evidence, result, task_id):
    return [
        {
            "item_id": p["id"],
            **sample_observation(r, result, task_id),
            "evidence": [
                {
                    "artifact_id": r["artifact_id"],
                    "sha256": r["artifact_sha256"],
                    "locator": "Native whole object bytes"
                    if r["document"] is None
                    else "$; named attribute calculations in linked workpaper",
                }
            ]
            if r["artifact_status"] == "AVAILABLE"
            else [],
        }
        for r, p in zip(evidence, population_rows(evidence), strict=True)
    ]


def verify_sample_trace(final, trace, paper, evidence, result, evaluation, task_digest):
    """Reperform actual item membership, attributes, digests and unavailable support."""
    pop = next(p for p in final["populations"] if p["id"] == trace["population_id"])
    obj = population(pop)
    chosen = selection(next(s for s in final["selections"] if s["id"] == trace["selection_id"]))
    expected_rows = population_rows(evidence)
    require(
        list(obj.rows) == expected_rows
        and pop["rows"] == expected_rows
        and obj.status == "READY_FOR_PURPOSE"
        and obj.scope
        == {
            "boundary_id": "corporate",
            "unit": "SVC-identity",
            "timezone": "UTC",
            "period_start": "2027-01-01T00:00:00Z",
            "period_end": "2027-12-31T23:59:59.999999Z",
        },
        "Exact task population rows/scope differs",
    )
    available = [r["artifact_id"] for r in evidence if r["artifact_status"] == "AVAILABLE"]
    require(
        obj.source["observable_source_ref"].split(", ") == available
        and obj.source["excluded_ids"] == []
        and chosen.method == "ENTIRE"
        and chosen.purpose == obj.source["reliability_purpose"]
        and set(chosen.all_ids) == set(obj.ids)
        and not chosen.targeted_ids
        and not chosen.provisional
        and chosen.population_digest == obj.sha256,
        "Task population support/entire selection differs",
    )
    annotated = []
    for item, p in zip(
        sample_items(evidence, result, trace["task_id"]), expected_rows, strict=True
    ):
        annotated.append(
            {
                **item,
                "item_digest": digest(p),
                "selection_basis": "SAMPLED",
                "locator_validation": "AUTHOR_SUPPLIED_NOT_CONTENT_MATCH_VERIFIED",
            }
        )
    require(trace["items"] == annotated, "Exact sampled observations/support differs")
    require(
        trace["population_digest"] == obj.sha256
        and trace["selection_digest"] == chosen.sha256
        and trace["task_digest"] == task_digest
        and trace["workpaper_id"] == paper["id"]
        and trace["workpaper_version"] == 1
        and trace["workpaper_digest"] == digest(paper["versions"][0])
        and trace["procedure"] == evaluation["performed_procedure"]
        and trace["scope_digest"] == digest(final["scope"])
        and trace["scope"] == final["scope"]
        and trace["independent_review"] == "NOT_PERFORMED"
        and trace["automatic_testing_credit"] is False
        and trace["predecessor_id"] is None
        and trace["revision"] == 1
        and trace["parent_lineage"] == [],
        "Pinned task/procedure/workpaper/sample trace differs",
    )


def immutable_schema(path):
    expected = {}
    for table, label in (("versions", "source"), ("collections", "collection")):
        noun = "version" if table == "versions" else "collection"
        for action in ("update", "delete"):
            name = f"no_{noun}_{action}"
            expected[name] = (
                f"CREATE TRIGGER {name} BEFORE {action.upper()} ON {table} "
                f"BEGIN SELECT RAISE(ABORT, 'Immutable {label}'); END"
            )

    def normalize(value):
        return "".join(value.split()).replace('"', "").lower()

    with read_only(path) as db:
        actual = dict(db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'"))
    require(
        set(actual) == set(expected)
        and all(normalize(actual[n]) == normalize(v) for n, v in expected.items()),
        "Exact immutable source/collection triggers differ",
    )


def task_evaluation(task, result, criteria):
    number = int(task["control_id"][-3:])
    kind = task["kind"]
    analyses = {
        1: ["worker", "canonical_membership", "service_inventory"],
        2: ["worker", "movers", "local_reads"],
        3: ["movers"],
        4: ["worker"],
        5: ["local_review", "local_reads", "emergency"],
        6: ["service_inventory", "service_attempts", "local_review"],
        7: ["quarters", "movers"],
    }
    observed = {name: result[name] for name in analyses[number]}
    limits = list(COMMON_LIMITS)
    blocked = [
        r
        for r in result.get("audit_support", {}).get("quarantined_sources", [])
        if r["component"] in task_components(task)
    ]
    if blocked:
        limits.append(
            "The raw local object was collected with missing filename/type provenance "
            "and quarantined by the ordinary parser. Native permission/byte checks "
            "do not establish auditor parsed usability; that object is unavailable "
            "as learner evidence. The original quarantine is preserved."
        )
    if kind == "TOD":
        procedure = (
            "Inspect every available declared design rule, authority/sponsor "
            "field, revocation/review cadence and its realization; compare to the "
            "exact registered control procedure."
        )
        status, conclusion = "COMPLETE", "LIMITATION"
        limits.append(
            "Design examination finished over the visible declared corpus; "
            "accepted enterprise policy/delegations and wider system inventory "
            "were not present in this source corpus. This conclusion is a "
            "limitation, not proof that no such policy exists elsewhere."
        )
    elif kind == "IMPLEMENTATION":
        procedure = (
            "Trace the instantiated local configuration, prior approval and actual "
            "source/probe states for this control; retain initial and later "
            "versions separately."
        )
        status, conclusion = "COMPLETE", "LIMITATION"
        exceptions = (
            (number == 3 and any(m["exception"] for m in result["movers"]))
            or (number == 4 and bool(result["worker"]["checkpoint_active_channels"]))
            or (
                number == 6
                and any(
                    a.get("status") == "AUTHORIZATION_DENIED" for a in result["service_attempts"]
                )
            )
            or (
                number == 7
                and any(q.get("missing_people") or q.get("excess") for q in result["quarters"])
            )
        )
        if exceptions:
            conclusion = "FAIL"
        if number == 5:
            status = "IN_PROGRESS"
            limits.append(
                "Privileged/emergency marker and local object paths lack a complete "
                "privileged corporate population and approval/vault scope."
            )
    elif kind == "TOE":
        procedure = (
            "Census all visible native operating histories and closed due windows, "
            "inspect failed/denied and corrected cases, and challenge population "
            "completeness before extrapolation."
        )
        status, conclusion = "IN_PROGRESS", "LIMITATION"
        limits.append(
            "Full enterprise operating denominator remains unestablished. All "
            "visible selected events/windows are examined; other workforce/local "
            "accounts, systems, ownership changes and review histories are not "
            "inferred."
        )
    else:
        procedure = task["test"]
        status, conclusion = "IN_PROGRESS", "LIMITATION"
        if task["id"].endswith("CC6.2"):
            limits.append(
                "Cross-component identities are explicit independent exercise cohorts; "
                "there is no common authoritative whole-enterprise "
                "HR/contractor/service directory census, and initial two-human "
                "creation requests are unavailable."
            )
        elif task["id"].endswith("CC6.3"):
            limits.append(
                "Local role approval and actual application rights are examined; "
                "enterprise job-duty entitlement catalogue, conflict matrix and "
                "corporate delegation acceptance remain unestablished."
            )
        elif task["id"].endswith("CC6.1"):
            limits.append(
                "Human and service exact-object reads/denials are examined; each real "
                "corporate trust boundary, credential/key protection and full "
                "privileged path are unperformed."
            )
        else:
            limits.append(
                "The approved marker exercise is observed through company-native "
                "records; no live ePHI application usability or restored "
                "permission/session state across recovery is demonstrated."
            )
    return {
        "task_id": task["id"],
        "kind": kind,
        "criterion": criteria[task["control_id"]]["procedure"],
        "authored_clause": task.get("test", task["title"]),
        "performed_procedure": procedure,
        "observations": observed,
        "status": status,
        "conclusion": conclusion,
        "limitations": limits,
        "independent_review": "RESERVED_NOT_PERFORMED",
    }


def task_components(task):
    number = int(task["control_id"][-3:])
    chosen = {
        1: {"lifecycle", "identity", "nonhuman"},
        2: {"lifecycle", "identity", "human", "service"},
        3: {"identity"},
        4: {"lifecycle"},
        5: {"human", "service", "emergency", "phi", "bcm", "security"},
        6: {"nonhuman", "service"},
        7: {"identity"},
    }[number]
    if task["id"].endswith("CC6.2"):
        chosen = {"identity", "lifecycle", "nonhuman", "service"}
    return chosen


def audit_only_method_inputs(private, baseline):
    require(
        sha(private / CROSSWALK) == CROSSWALK_SHA and sha(private / HISTORICAL) == HISTORICAL_SHA,
        "Historical method/membership index pin differs",
    )
    raw = json.loads((private / CROSSWALK).read_text())
    methods = [
        {
            k: r[k]
            for k in (
                "side",
                "task_id",
                "kind",
                "current_title",
                "current_test_clause",
                "prior_authored_method_text",
            )
        }
        for r in raw["rows"]
    ]
    require(
        len(methods) == 818 and len({(r["side"], r["task_id"]) for r in methods}) == 818,
        "Exact crosswalk membership differs",
    )
    historical = json.loads((private / HISTORICAL).read_text())
    # Deliberate projection: historical statuses, observations and evidence are never inputs.
    members = sorted([r["profile"], r["task_id"]] for r in historical["rows"])
    require(
        len(members) == 236 and len({tuple(m) for m in members}) == 236,
        "Historical 236 task membership differs",
    )
    taskmap = {t["id"]: t for t in baseline["tasks"]}
    require(
        set(p for p, _ in members) == {"full-integrated-a-v1", "full-integrated-b-v1"},
        "Historical profile identity differs",
    )
    for _profile, tid in members:
        require(
            tid in taskmap and taskmap[tid]["kind"] in {"IMPLEMENTATION", "TOE"},
            "Historical task is outside exact current programme/method scope",
        )
    require(
        all(sum(p == profile for p, _ in members) == 118 for profile in {p for p, _ in members}),
        "Historical per-profile membership differs",
    )
    return {
        "methods": methods,
        "historical_operating_task_membership": members,
        "historical_membership_sha256": digest(members),
        "person_count_inference": False,
        "historical_result_or_evidence_transferred": False,
    }


def seal(destination):
    files = []
    for path in sorted(destination.rglob("*")):
        if path.is_dir():
            path.chmod(0o700)
        elif path.is_file():
            path.chmod(0o600)
            require(
                path.stat().st_nlink == 1 and not path.is_symlink(),
                "Private ordinary output required",
            )
            files.append(
                {
                    "path": path.relative_to(destination).as_posix(),
                    "sha256": sha(path),
                    "bytes": path.stat().st_size,
                }
            )
    write(
        destination / "MANIFEST.json",
        {"schema": SCHEMA + "_MANIFEST", "files": files, "inventory_sha256": digest(files)},
    )


def run(repository, private_repository, destination):
    repo = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    destination = Path(destination).absolute()
    require(not destination.exists(), "Fresh destination required")
    _private(destination.parent, directory=True)
    require(_p1_inventory(private) == FREEZE, "Frozen P1 differs")
    require(
        sha(repo / SPEC) == SPEC_SHA
        and sha(repo / CRITERIA) == CRITERIA_SHA
        and sha(private / PROGRAM_PACK) == PROGRAM_PACK_SHA,
        "Specification/criterion/programme pin differs",
    )
    spec = json.loads((repo / SPEC).read_text())
    criteria = {r["control_id"]: r for r in json.loads((repo / CRITERIA).read_text())}
    pins = {
        str(repo / SPEC): SPEC_SHA,
        str(repo / CRITERIA): CRITERIA_SHA,
        str(private / PROGRAM_PACK): PROGRAM_PACK_SHA,
        str(private / CROSSWALK): CROSSWALK_SHA,
        str(private / HISTORICAL): HISTORICAL_SHA,
    }
    for source in spec["sources"].values():
        p = private / source["relative_database"]
        _private(p)
        require(sha(p) == source["sha256"], "Original company source pin differs")
        require(
            not any(Path(str(p) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")),
            "Source not quiescent",
        )
        pins[str(p)] = source["sha256"]
    destination.mkdir(mode=0o700)
    write(destination / "IMPLEMENTATION.py", Path(__file__).read_bytes())
    report = {
        "schema": SCHEMA,
        "repository": str(repo),
        "private_repository": str(private),
        "implementation_sha256": sha(destination / "IMPLEMENTATION.py"),
        "source_pins": pins,
        "p1_before": FREEZE,
        "branches": {},
        "professional_acceptance": False,
        "historical_evidence_or_key_used": False,
    }
    canon = snapshot(repo, as_of="2027-12-31")
    write(destination / "CANON.json", canon)
    methods = audit_only_method_inputs(private, _baseline(private, "A"))
    write(destination / "METHODS.json", methods)
    for side, mode in [("A", "CLEAN"), ("B", "MESSY")]:
        root = destination / side
        root.mkdir(mode=0o700)
        components = {}
        copies = {}
        for key, source in spec["sources"].items():
            origin = private / source["relative_database"]
            copy = root / key / "company.sqlite3"
            _ordinary_copy(origin, copy)
            immutable_schema(copy)
            with read_only(copy) as db:
                systems = sorted(
                    r[0]
                    for r in db.execute(
                        "SELECT system FROM systems WHERE company=? AND branch=?",
                        (source["company"], source["branches"][side]),
                    )
                )
                journal_counts = {
                    t: db.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
                    for t in ("grants", "collections", "access_events")
                }
            require(systems, "Source system inventory empty")
            components[key] = {
                "root": str(copy.parent),
                "company": source["company"],
                "branch": source["branches"][side],
                "namespace": source["namespace"],
                "systems": systems,
            }
            copies[key] = {
                "origin": str(origin),
                "copy": str(copy),
                "initial_sha256": sha(copy),
                "business_sha256": business_digest(copy),
                "inherited_journal_counts_opaque": journal_counts,
            }
        profile = "FRESH-IAM-" + side
        write(
            root / "REGISTRY.json",
            {
                "schema": PORTFOLIO_SCHEMA,
                "components": components,
                "profiles": {
                    profile: {
                        "company": COMPANY,
                        "components": sorted(components),
                        "qualification": QUALIFICATION,
                    }
                },
            },
        )
        _ordinary_copy(private / PROGRAM_PACK, root / "program-pack.json")
        engine = Engine(
            root / "audit-state",
            repository=repo,
            program_pack=root / "program-pack.json",
            company_registry=root / "REGISTRY.json",
            company_profile=profile,
        )
        operator = engine.store.provision("Fresh IAM source operator " + side, ["instructor"])["id"]
        auditor = engine.store.provision("Fresh IAM performer " + side, ["learner"])["id"]
        reviewer = engine.store.provision(
            "Reserved independent IAM reviewer " + side, ["reviewer"]
        )["id"]
        baseline = _baseline(private, side)
        state = engine.create(
            operator,
            {
                "command_id": "fresh-iam-create",
                "title": "Fresh IAM family " + side,
                "discipline": baseline["discipline"],
                "mode": mode,
                "scope": baseline["scope"],
                "configuration": {"selections": []},
            },
        )
        eid = state["id"]
        require(_time(state["simulated_at"]) == _time(INITIAL), "Initial simulated clock differs")
        fresh = {t["id"]: t for t in state["tasks"]}
        frozen = {t["id"]: t for t in baseline["tasks"]}
        require(
            len(fresh) == 409 and fresh.keys() == frozen.keys(), "Programme task membership differs"
        )
        require(
            all(
                all(t.get(k) == frozen[tid].get(k) for k in METHOD_FIELDS)
                for tid, t in fresh.items()
            ),
            "Exact authored task/owner/method differs",
        )
        empty = {
            k: len(state[k])
            for k in (
                "artifacts",
                "workpapers",
                "populations",
                "selections",
                "reviews",
                "findings",
                "requests",
                "sample_executions",
                "artifact_inspections",
            )
        }
        require(not any(empty.values()), "Fresh audit inherited work")
        engine.store.grant(eid, auditor, "learn")
        engine.store.grant(eid, reviewer, "review")
        engine.company_bindings[eid] = dict(engine.company_store.binding)
        start = {
            "engagement_id": eid,
            "operator_id": operator,
            "auditor_id": auditor,
            "reviewer_id": reviewer,
            "zero_workroom_counts": empty,
            "initial_simulated_at": state["simulated_at"],
            "scope": state["scope"],
        }
        write(root / "START.json", start)
        taskids = spec["selected_task_ids"]
        require(
            len(taskids) == 30 and all(t in fresh for t in taskids), "Selected task vector differs"
        )
        plan = {
            "task_ids": taskids,
            "task_methods": [{k: fresh[t].get(k) for k in METHOD_FIELDS} for t in taskids],
            "selection_sealed_at": datetime.now(UTC).isoformat(),
            "initial_as_of": INITIAL,
            "final_as_of": AS_OF,
            "period": ["2027-01-01", "2027-12-31"],
            "method": "ENTIRE_VISIBLE_NATIVE_COMPONENT_HISTORY_AND_EXACT_CITED_UPSTREAM_JOINS",
            "sampling": "ENTIRE_DECLARED_COHORT; no statistical extrapolation",
            "exclusions": spec["excluded_task_ids"],
            "scope_limit": (
                "Independent exercise cohorts retained; no enterprise source/history union"
            ),
            "performer_id": auditor,
        }
        write(root / "PLAN.json", plan)
        state = command(engine, operator, eid, "company.activate", {}, "activate")
        state = command(engine, auditor, eid, "kickoff.start", {}, "kickoff")
        state = command(
            engine,
            auditor,
            eid,
            "pbc.create",
            {
                "title": "Identity and HR source histories with due-window and permission joins",
                "purpose": (
                    "Direct native discovery and exact source-version collection for the "
                    "sealed IAM family methods"
                ),
                "control_id": "SH-IAM-001",
                "person_id": "AS-P007",
                "boundary_id": "corporate",
            },
            "request",
        )
        request = state["requests"][-1]["id"]
        state = command(engine, auditor, eid, "pbc.issue", {"request_id": request}, "issue")

        def grant(key, systems, active, components=components, auditor=auditor, eid=eid):
            c = components[key]
            store = CompanyStore(Path(c["root"]))
            for system in systems:
                store.grant(auditor, eid, c["company"], c["branch"], system, active=active)

        for key in set(components) - UPSTREAM:
            grant(key, components[key]["systems"], True)
        first, first_pages = discover_components(
            engine.company_store,
            auditor,
            eid,
            profile,
            components,
            set(components) - UPSTREAM,
            as_of=INITIAL,
        )
        for row in first:
            row["component"] = next(
                k
                for k, c in components.items()
                if row["discovery_system"].startswith(c["namespace"] + ":")
            )
        initial_rows = [projected(r) for r in first]
        write(
            root / "INITIAL_DISCOVERY.json",
            {
                "clock": INITIAL,
                "pages": first_pages,
                "observed_sources": [r["source"] for r in initial_rows],
                "quarter4_state": "NOT_YET_DUE_RIGHT_CENSORED",
                "q4_read_or_collection_performed": False,
            },
        )
        require(
            not any(r["source"]["record"] == "PRIV-2027-Q4" for r in initial_rows),
            "Q4 source leaked before availability",
        )
        try:
            engine.company_store.read_version(
                auditor,
                eid,
                COMPANY,
                profile,
                "IAMIDENTITY:review_population",
                "PRIV-2027-Q4",
                version=1,
                as_of=INITIAL,
            )
        except CompanyStoreError:
            pass
        else:
            raise ProcedureError("Future Q4 read allowed")
        state = command(
            engine,
            auditor,
            eid,
            "clock.advance",
            {"mode": "TARGET_DATE", "target": AS_OF},
            "advance-full-period",
        )
        require(
            _time(state["simulated_at"]) == _time(AS_OF) and state["scope"] == baseline["scope"],
            "Clock advance changed period/scope",
        )
        discovered, pages = discover_components(
            engine.company_store,
            auditor,
            eid,
            profile,
            components,
            set(components) - UPSTREAM,
            as_of=AS_OF,
        )
        for row in discovered:
            row["component"] = next(
                k
                for k, c in components.items()
                if row["discovery_system"].startswith(c["namespace"] + ":")
            )
        refs = {}
        for row in discovered:
            for ref in native_refs(projected(row)["document"]):
                key = tuple(ref[k] for k in NATIVE_ID)
                if ref["company"] == "SABLE-HARBOR-REFERENCE" and ref["branch"].startswith(
                    ("PHI-", "BCM-", "SEC005-")
                ):
                    refs[key] = ref
        upstream_rows = []
        upstream_pages = []
        for key in UPSTREAM:
            c = components[key]
            chosen = sorted(
                {
                    ref["system"]
                    for ref in refs.values()
                    if ref["company"] == c["company"] and ref["branch"] == c["branch"]
                }
            )
            if not chosen:
                continue
            require(set(chosen) <= set(c["systems"]), "Upstream join system unavailable")
            grant(key, chosen, True)
            found, pg = discover_history(
                engine.company_store,
                auditor,
                eid,
                COMPANY,
                profile,
                as_of=AS_OF,
                systems=[c["namespace"] + ":" + s for s in chosen],
                page_size=10,
            )
            upstream_pages.extend(pg)
            for row in found:
                row["component"] = key
                ident = tuple(row[k] for k in NATIVE_ID)
                if ident in refs:
                    require(row["sha256"] == refs[ident]["sha256"], "Exact upstream source differs")
                    upstream_rows.append(row)
        require(
            set(refs) == {tuple(r[k] for k in NATIVE_ID) for r in upstream_rows},
            "Cited upstream join absent",
        )
        selected = sorted(
            discovered + upstream_rows,
            key=lambda r: (r["component"], r["system"], r["record"], r["version"]),
        )
        collected = []
        for n, row in enumerate(selected):
            state = command(
                engine,
                auditor,
                eid,
                "company.collect",
                {
                    "system_id": row["discovery_system"],
                    "record_id": row["record"],
                    "version": row["version"],
                    "request_id": request,
                },
                "collect" + str(n),
            )
            artifact = state["artifacts"][-1]
            require(
                engine.artifacts.read(artifact) == row["content"]
                and all(artifact["source"]["receipt"]["source"][k] == row[k] for k in CLOCK_ID),
                "Exact retained source custody differs",
            )
            collected.append(projected(row, artifact))
        for key, c in components.items():
            grant(key, c["systems"], False)
        require(
            not engine.company_store.list_systems(auditor, eid, COMPANY, profile)["systems"],
            "Fresh grants remained active",
        )
        result = analyze(collected, canon, as_of=AS_OF)
        discovery = {
            "sources": copies,
            "initial_pages": first_pages,
            "final_pages": pages,
            "upstream_pages": upstream_pages,
            "selected_members": [r["source"] for r in collected],
            "as_of": AS_OF,
            "snapshot_isolation": (
                "Frozen ordinary copies; per-API transactions; no global source "
                "transaction asserted"
            ),
            "future_payloads_read": False,
        }
        write(root / "COLLECTION.json", collected)
        write(root / "DISCOVERY.json", discovery)
        write(root / "REPERFORMANCE.json", result)
        papers = []
        for n, tid in enumerate(taskids):
            task = fresh[tid]
            evaluation = task_evaluation(task, result, criteria)
            evidence = [r for r in collected if r["component"] in task_components(task)]
            text = (
                json.dumps(evaluation, sort_keys=True, indent=2)
                + "\n\nExact observed source locators:\n"
                + json.dumps([r["source"] for r in evidence], sort_keys=True, indent=2)
            )
            state = command(
                engine,
                auditor,
                eid,
                "workpaper.add",
                {
                    "title": tid + " native procedure examination",
                    "control_id": task["control_id"],
                    "task_ids": [tid],
                    "text": text,
                    "objective": evaluation["authored_clause"],
                    "procedures": evaluation["performed_procedure"],
                    "evidence_ids": [r["artifact_id"] for r in evidence],
                    "conclusion": evaluation["conclusion"],
                },
                "paper" + str(n),
            )
            paper = state["workpapers"][-1]
            anchor = evidence[0]
            state = command(
                engine,
                auditor,
                eid,
                "artifact.inspection.record",
                {
                    "artifact_id": anchor["artifact_id"],
                    "sha256": anchor["artifact_sha256"],
                    "version": anchor["artifact_version"],
                    "locator": "Exact native source "
                    + anchor["source"]["system"]
                    + "/"
                    + anchor["source"]["record"]
                    + "; detailed attributes and cross-system joins in linked workpaper",
                    "observation": json.dumps(
                        {
                            "task_id": tid,
                            "performed": evaluation["performed_procedure"],
                            "limit": evaluation["limitations"][-1],
                        },
                        sort_keys=True,
                    ),
                    "task_id": tid,
                },
                "inspect" + str(n),
            )
            # Full observed version census for this task, not the producer's claimed count.
            poprows = population_rows(evidence)
            state = command(
                engine,
                auditor,
                eid,
                "population.import",
                {
                    "artifact_id": anchor["artifact_id"],
                    "title": tid + " visible native version census",
                    "rows": poprows,
                    "scope": {
                        "boundary_id": "corporate",
                        "unit": "SVC-identity",
                        "timezone": "UTC",
                        "period_start": "2027-01-01T00:00:00Z",
                        "period_end": "2027-12-31T23:59:59.999999Z",
                    },
                    "source": {
                        "source_id": "FRESH-IAM-SNAPSHOT-" + side,
                        "query": (
                            "Granted list_systems/list_records plus exact contiguous read_version; "
                            "census of retained immutable versions for declared components at "
                        )
                        + AS_OF,
                        "completeness_representation": (
                            "Full visible selected source history only; wider enterprise "
                            "workforce/system denominator unestablished"
                        ),
                        "excluded_ids": [],
                    },
                },
                "pop" + str(n),
            )
            pop = state["populations"][-1]
            state = command(
                engine,
                auditor,
                eid,
                "population.assess",
                {
                    "population_id": pop["id"],
                    "status": "READY_FOR_PURPOSE",
                    "purpose": SOURCE_CENSUS_PURPOSE,
                    "rationale": (
                        "Exact paginated API history and byte custody joined to ordinary "
                        "isolated company snapshots; visible scope limitations retained"
                    ),
                    "observable_artifact_ids": [
                        r["artifact_id"] for r in evidence if r["artifact_status"] == "AVAILABLE"
                    ],
                },
                "assess" + str(n),
            )
            pop = state["populations"][-1]
            state = command(
                engine,
                auditor,
                eid,
                "population.select",
                {
                    "population_id": pop["id"],
                    "method": "ENTIRE",
                    "purpose": SOURCE_CENSUS_PURPOSE,
                    "rationale": (
                        "No outcome exclusion or statistical extrapolation; all observed "
                        "versions retained including initial failure/correction"
                    ),
                },
                "select" + str(n),
            )
            chosen = state["selections"][-1]
            items = sample_items(evidence, result, tid)
            # Every item remains within the ordinary Engine payload/observation bounds.
            state = command(
                engine,
                auditor,
                eid,
                "sample.execution.record",
                {
                    "task_id": tid,
                    "task_digest": digest(next(t for t in state["tasks"] if t["id"] == tid)),
                    "population_id": pop["id"],
                    "population_digest": population(pop).sha256,
                    "selection_id": chosen["id"],
                    "selection_digest": selection(chosen).sha256,
                    "workpaper_id": paper["id"],
                    "workpaper_version": 1,
                    "workpaper_digest": digest(paper["versions"][0]),
                    "purpose": SOURCE_CENSUS_PURPOSE,
                    "procedure": evaluation["performed_procedure"],
                    "items": items,
                },
                "samples" + str(n),
            )
            state = command(
                engine,
                auditor,
                eid,
                "task.update",
                {
                    "task_id": tid,
                    "status": evaluation["status"],
                    "conclusion": evaluation["conclusion"],
                    "rationale": evaluation["limitations"][-1]
                    + (
                        " Exact source examination, observations and limits are in the "
                        "task-specific workpaper; no PASS, external opinion or wider "
                        "population acceptance."
                    ),
                },
                "task" + str(n),
            )
            papers.append(
                {
                    "task_id": tid,
                    "workpaper_id": paper["id"],
                    "evaluation": evaluation,
                    "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                }
            )
        findings = [
            (
                "Enterprise identity population is unestablished",
                "SH-IAM-001",
                result["canonical_membership"],
                "SCOPE_LIMITATION",
            ),
            (
                "Emergency approval is reviewed by the same company signer",
                "SH-IAM-005",
                result["emergency"],
                "SELF_REVIEW_LIMITATION",
            ),
        ]
        if any(m["exception"] for m in result["movers"]):
            findings.append(
                (
                    "Obsolete mover application rights remain",
                    "SH-IAM-003",
                    result["movers"],
                    "SELECTED_OPERATING_EXCEPTION",
                )
            )
        if result["worker"]["checkpoint_active_channels"]:
            findings.append(
                (
                    "Application session survives authorized expiry",
                    "SH-IAM-004",
                    result["worker"],
                    "SELECTED_OPERATING_EXCEPTION",
                )
            )
        if any(q.get("missing_people") or q.get("excess") for q in result["quarters"]):
            findings.append(
                (
                    "Quarterly review omits existing account and removal remains unconfirmed",
                    "SH-IAM-007",
                    result["quarters"],
                    "SELECTED_OPERATING_EXCEPTION",
                )
            )
        if any(not r["timely"] for r in result["local_review"]):
            findings.append(
                (
                    "Local privileged review occurred after declared deadline",
                    "SH-IAM-005",
                    result["local_review"],
                    "SELECTED_OPERATING_EXCEPTION",
                )
            )
        if any(a.get("status") == "AUTHORIZATION_DENIED" for a in result["service_attempts"]):
            findings.append(
                (
                    "Credential rotation broke the consumer copy until correction",
                    "SH-IAM-006",
                    result["service_attempts"],
                    "SELECTED_OPERATING_EXCEPTION",
                )
            )
        for n, (title, cid, condition, classification) in enumerate(findings):
            state = command(
                engine,
                auditor,
                eid,
                "finding.create",
                {
                    "title": title,
                    "condition": json.dumps(condition, sort_keys=True),
                    "classification": classification,
                    "control_id": cid,
                    "criterion": criteria[cid]["procedure"],
                    "evidence_ids": [
                        r["artifact_id"]
                        for r in collected
                        if r["component"] in task_components({"control_id": cid, "id": ""})
                    ],
                },
                "finding" + str(n),
            )
        require(not state["reviews"], "Performer manufactured independent review")
        require(
            all(
                t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN"
                for t in state["tasks"]
                if t["id"] not in taskids
            ),
            "Unrelated task credit changed",
        )
        for copy in copies.values():
            require(
                business_digest(copy["copy"]) == copy["business_sha256"]
                and sha(copy["origin"]) == copy["initial_sha256"],
                "Source business history/original changed",
            )
        write(root / "WORKPAPERS.json", papers)
        # Engine.command returns an authorized UI projection. Preserve the
        # supported Store state for exact independent journal comparison.
        write(root / "FINAL_STATE.json", engine.store.get(auditor, eid))
        with engine.store.connect() as db:
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        report["branches"][side] = {
            "engagement_id": eid,
            "collected_versions": len(collected),
            "workpapers": len(papers),
            "samples": len(state["sample_executions"]),
            "inspection_assertions": len(state["artifact_inspections"]),
            "findings": len(state["findings"]),
            "task_statuses": {
                tid: {
                    "status": next(t for t in state["tasks"] if t["id"] == tid)["status"],
                    "conclusion": next(t for t in state["tasks"] if t["id"] == tid)["conclusion"],
                }
                for tid in taskids
            },
            "reviewer_id": reviewer,
            "independent_review": "NOT_PERFORMED",
            "final_simulated_at": state["simulated_at"],
        }
    require(
        _p1_inventory(private) == FREEZE and all(sha(p) == h for p, h in pins.items()),
        "Frozen original sources changed",
    )
    report["p1_after"] = FREEZE
    write(destination / "REPORT.json", report)
    seal(destination)
    return report


def verify(destination):
    """Read-only independent re-performance of custody, methods and real journals."""
    root = Path(destination).resolve(strict=True)
    _private(root, directory=True)
    manifest = json.loads((root / "MANIFEST.json").read_text())
    require(
        manifest["schema"] == SCHEMA + "_MANIFEST"
        and digest(manifest["files"]) == manifest["inventory_sha256"],
        "Manifest differs",
    )
    actual = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p.name != "MANIFEST.json"
    }
    require(actual == {r["path"] for r in manifest["files"]}, "Exact output inventory differs")
    for r in manifest["files"]:
        _private(root / r["path"])
        require(
            sha(root / r["path"]) == r["sha256"]
            and (root / r["path"]).stat().st_size == r["bytes"],
            "Output hash differs",
        )
    report = json.loads((root / "REPORT.json").read_text())
    require(
        report["schema"] == SCHEMA
        and sha(root / "IMPLEMENTATION.py") == report["implementation_sha256"]
        and report["historical_evidence_or_key_used"] is False
        and report["professional_acceptance"] is False,
        "Qualification differs",
    )
    private = Path(report["private_repository"])
    repo = Path(report["repository"])
    spec = json.loads((repo / SPEC).read_text())
    criteria = {r["control_id"]: r for r in json.loads((repo / CRITERIA).read_text())}
    expected_pins = {
        str(repo / SPEC): SPEC_SHA,
        str(repo / CRITERIA): CRITERIA_SHA,
        str(private / PROGRAM_PACK): PROGRAM_PACK_SHA,
        str(private / CROSSWALK): CROSSWALK_SHA,
        str(private / HISTORICAL): HISTORICAL_SHA,
        **{str(private / s["relative_database"]): s["sha256"] for s in spec["sources"].values()},
    }
    require(
        _p1_inventory(private) == FREEZE
        and report["source_pins"] == expected_pins
        and all(sha(p) == h for p, h in report["source_pins"].items()),
        "Original source pin differs",
    )
    require(
        json.loads((root / "METHODS.json").read_text())
        == audit_only_method_inputs(private, _baseline(private, "A")),
        "Method-only historical projection differs",
    )
    canon = json.loads((root / "CANON.json").read_text())
    expectedcanon = snapshot(repo, as_of="2027-12-31")
    require(
        canon["snapshot_digest"]
        == digest({k: v for k, v in canon.items() if k != "snapshot_digest"}),
        "Canon retained digest differs",
    )
    require(
        {k: v for k, v in canon.items() if k not in {"source_revision", "snapshot_digest"}}
        == {
            k: v
            for k, v in expectedcanon.items()
            if k not in {"source_revision", "snapshot_digest"}
        },
        "Canon membership/roles changed",
    )
    summaries = {}
    for side in "AB":
        folder = root / side
        start = json.loads((folder / "START.json").read_text())
        final = json.loads((folder / "FINAL_STATE.json").read_text())
        plan = json.loads((folder / "PLAN.json").read_text())
        discovery = json.loads((folder / "DISCOVERY.json").read_text())
        rows = json.loads((folder / "COLLECTION.json").read_text())
        papers = json.loads((folder / "WORKPAPERS.json").read_text())
        verify_audit_journal(folder / "audit-state/engagements.sqlite3", final, start)
        require(
            _time(start["initial_simulated_at"]) == _time(INITIAL)
            and _time(final["simulated_at"]) == _time(AS_OF)
            and start["scope"] == final["scope"],
            "Full-period clock/scope differs",
        )
        with read_only(folder / "audit-state/engagements.sqlite3") as db:
            advances = [
                json.loads(r[0])
                for r in db.execute(
                    "SELECT command FROM events WHERE engagement=? ORDER BY revision",
                    (final["id"],),
                )
                if json.loads(r[0])["kind"] == "clock.advance"
            ]
            performed_digests = {}
            for event in db.execute(
                "SELECT command,state FROM events WHERE engagement=? "
                "AND json_extract(command,'$.kind')='sample.execution.record' ORDER BY revision",
                (final["id"],),
            ):
                cmd = json.loads(event["command"])
                event_state = json.loads(event["state"])
                tid = cmd["payload"]["task_id"]
                require(tid not in performed_digests, "Duplicate task sample command")
                task = next(t for t in event_state["tasks"] if t["id"] == tid)
                performed_digests[tid] = digest(task)
                require(
                    cmd["payload"]["task_digest"] == performed_digests[tid],
                    "Executed task digest differs from actual Engine command state",
                )
        require(
            len(advances) == 1
            and advances[0]["payload"] == {"mode": "TARGET_DATE", "target": AS_OF},
            "Ordinary clock transition differs",
        )
        require(
            plan["task_ids"] == spec["selected_task_ids"]
            and len(papers) == 30
            and {p["task_id"] for p in papers} == set(plan["task_ids"]),
            "Exact task/workpaper membership differs",
        )
        initial = json.loads((folder / "INITIAL_DISCOVERY.json").read_text())
        registry_sha = digest(load_profile(folder / "REGISTRY.json", "FRESH-IAM-" + side))
        require(
            initial["q4_read_or_collection_performed"] is False
            and not any(r["record"] == "PRIV-2027-Q4" for r in initial["observed_sources"]),
            "Initial snapshot has future review",
        )
        artifacts = {a["id"]: a for a in final["artifacts"]}
        require(len(artifacts) == len(rows), "Artifact/version census differs")
        for row in rows:
            source = row["source"]
            component = spec["sources"][row["component"]]
            copy = folder / row["component"] / "company.sqlite3"
            require(
                source["company"] == component["company"]
                and source["branch"] == component["branches"][side],
                "Source crossed branch/cohort",
            )
            with read_only(copy) as db:
                native = db.execute(
                    (
                        "SELECT * FROM versions WHERE company=? AND branch=? AND system=? AND "
                        "record=? AND version=?"
                    ),
                    tuple(source[k] for k in NATIVE_ID),
                ).fetchone()
                require(
                    native is not None
                    and all(native[k] == source[k] for k in CLOCK_ID)
                    and hashlib.sha256(native["content"]).hexdigest() == source["sha256"],
                    "Exact native custody differs",
                )
                projected_native = projected({**dict(native), "component": row["component"]})
                require(
                    projected_native["document"] == row["document"]
                    and len(native["content"]) == row["content_bytes"],
                    "Auditor observation differs from company bytes",
                )
                journal = db.execute(
                    "SELECT receipt FROM collections WHERE command_id=?",
                    (row["receipt"]["upstream_receipt"]["command_id"],),
                ).fetchone()
                require(
                    journal and json.loads(journal[0]) == row["receipt"]["upstream_receipt"],
                    "Fresh collection journal differs",
                )
                require(
                    db.execute(
                        (
                            "SELECT count(*) FROM grants WHERE principal=? AND engagement=? AND "
                            "active=1"
                        ),
                        (start["auditor_id"], final["id"]),
                    ).fetchone()[0]
                    == 0,
                    "Fresh source grant remains active",
                )
            artifact = artifacts[row["artifact_id"]]
            require(
                artifact["source"]["receipt"] == row["receipt"]
                and artifact["sha256"] == source["sha256"]
                and artifact["status"] == row["artifact_status"]
                and artifact.get("version") == row["artifact_version"]
                and sha(folder / "audit-state/artifacts" / artifact["sha256"]) == source["sha256"],
                "Retained bytes/receipt differs",
            )
            require(
                _time(source["event_at"]) <= _time(source["available_at"]) <= _time(AS_OF)
                and _time(source["imported_at"]) <= _time(row["receipt"]["collected_at"])
                and _time(plan["selection_sealed_at"]) <= _time(row["receipt"]["collected_at"]),
                "Source/import/collection/plan clock differs",
            )
            require(
                _time(row["receipt"]["simulated_as_of"]) == _time(AS_OF)
                and row["receipt"]["principal_id"] == start["auditor_id"]
                and row["receipt"]["engagement_id"] == final["id"]
                and row["receipt"]["registry_sha256"] == registry_sha
                and _time(artifact["simulated_at"]) == _time(AS_OF)
                and artifact["received_at"] == artifact["recorded_at"],
                "Ordinary collection authority/simulated clock differs",
            )
        expected_initial = []
        for key, copy in discovery["sources"].items():
            immutable_schema(folder / key / "company.sqlite3")
            require(
                business_digest(folder / key / "company.sqlite3") == copy["business_sha256"]
                and copy["initial_sha256"] == spec["sources"][key]["sha256"]
                and sha(copy["origin"]) == copy["initial_sha256"],
                "Original/copy business history differs",
            )
            # Inherited journal rows are opaque integrity inputs only. They
            # never supply a fieldwork observation or historical result.
            with (
                read_only(Path(copy["origin"])) as original,
                read_only(folder / key / "company.sqlite3") as cloned,
            ):
                for table in ("grants", "collections", "access_events"):
                    inherited = [
                        list(r)
                        for r in original.execute("SELECT * FROM " + table + " ORDER BY rowid")
                    ]
                    prefix = [
                        list(r)
                        for r in cloned.execute(
                            "SELECT * FROM " + table + " ORDER BY rowid LIMIT ?", (len(inherited),)
                        )
                    ]
                    require(
                        len(inherited) == copy["inherited_journal_counts_opaque"][table]
                        and digest(inherited) == digest(prefix),
                        "Inherited opaque company journal rows changed",
                    )
            # Independently check complete selected native member vector, not only claimed counts.
            if key in UPSTREAM:
                continue
            c = spec["sources"][key]
            with read_only(folder / key / "company.sqlite3") as db:
                expected_initial.extend(
                    tuple(r[k] for k in CLOCK_ID)
                    for r in db.execute(
                        "SELECT * FROM versions WHERE company=? AND branch=? "
                        "AND available_at<=? AND event_at<=?",
                        (c["company"], c["branches"][side], _time(INITIAL), _time(INITIAL)),
                    )
                )
                expected = {
                    tuple(r)
                    for r in db.execute(
                        (
                            "SELECT company,branch,system,record,version FROM versions WHERE "
                            "company=? AND branch=? AND available_at<=? AND event_at<=?"
                        ),
                        (c["company"], c["branches"][side], _time(AS_OF), _time(AS_OF)),
                    )
                }
            observed = {
                tuple(r["source"][k] for k in NATIVE_ID) for r in rows if r["component"] == key
            }
            require(expected == observed, "Native full visible population membership differs")
        require(
            sorted(expected_initial)
            == sorted(tuple(r[k] for k in CLOCK_ID) for r in initial["observed_sources"]),
            "Initial right-censored native member vector differs",
        )
        result = analyze(rows, canon, as_of=AS_OF)
        require(
            result == json.loads((folder / "REPERFORMANCE.json").read_text()),
            "Independent audit arithmetic differs",
        )
        require(
            len(final["workpapers"])
            == len(final["sample_executions"])
            == len(final["artifact_inspections"])
            == 30
            and not final["reviews"],
            "Performed/reviewer trace differs",
        )
        taskmap = {t["id"]: t for t in final["tasks"]}
        frozen = {t["id"]: t for t in _baseline(private, side)["tasks"]}
        require(
            taskmap.keys() == frozen.keys()
            and all(
                all(t.get(k) == frozen[tid].get(k) for k in METHOD_FIELDS)
                for tid, t in taskmap.items()
            ),
            "Exact programme method/owner membership differs",
        )
        for p in papers:
            tid = p["task_id"]
            task = taskmap[tid]
            evaluation = task_evaluation(frozen[tid], result, criteria)
            require(
                p["evaluation"] == evaluation
                and task["status"] == evaluation["status"]
                and task["conclusion"] == evaluation["conclusion"],
                "Exact per-task disposition differs",
            )
            wp = next(w for w in final["workpapers"] if w["id"] == p["workpaper_id"])
            version = wp["versions"][0]
            evidence = [r for r in rows if r["component"] in task_components(task)]
            text = (
                json.dumps(evaluation, sort_keys=True, indent=2)
                + "\n\nExact observed source locators:\n"
                + json.dumps([r["source"] for r in evidence], sort_keys=True, indent=2)
            )
            require(
                version["text"] == text
                and version["task_ids"] == [tid]
                and set(version["evidence_ids"]) == {r["artifact_id"] for r in evidence},
                "Task-specific workpaper bytes/locators differ",
            )
            samples = [s for s in final["sample_executions"] if s["task_id"] == tid]
            require(len(samples) == 1, "Task exact sample trace absent")
            verify_sample_trace(
                final, samples[0], wp, evidence, result, evaluation, performed_digests[tid]
            )
            anchor = next(r for r in evidence if r["artifact_status"] == "AVAILABLE")
            inspections = [r for r in final["artifact_inspections"] if r["task_id"] == tid]
            expected_inspection = {
                "artifact_id": anchor["artifact_id"],
                "sha256": anchor["artifact_sha256"],
                "version": anchor["artifact_version"],
                "locator": "Exact native source "
                + anchor["source"]["system"]
                + "/"
                + anchor["source"]["record"]
                + "; detailed attributes and cross-system joins in linked workpaper",
                "observation": json.dumps(
                    {
                        "task_id": tid,
                        "performed": evaluation["performed_procedure"],
                        "limit": evaluation["limitations"][-1],
                    },
                    sort_keys=True,
                ),
                "task_id": tid,
            }
            require(
                len(inspections) == 1
                and all(inspections[0][k] == v for k, v in expected_inspection.items())
                and inspections[0]["actor"] == start["auditor_id"]
                and inspections[0]["classification"] == "SELF_REPORTED_INSPECTION"
                and inspections[0]["payload_sha256"] == digest(expected_inspection),
                "Exact authored inspection differs",
            )
        require(
            all(
                t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN"
                for tid, t in taskmap.items()
                if tid not in plan["task_ids"]
            ),
            "Unrelated task credit differs",
        )
        summaries[side] = {
            "versions": len(rows),
            "tasks": 30,
            "quarters": len(result["quarters"]),
            "complete": sum(t["status"] == "COMPLETE" for t in taskmap.values()),
            "in_progress": sum(t["status"] == "IN_PROGRESS" for t in taskmap.values()),
            "professional_acceptance": False,
        }
    return {
        "status": "VERIFIED_FRESH_NATIVE_FAMILY_EXECUTION_NOT_PROFESSIONAL_ACCEPTANCE",
        "branches": summaries,
        "p1_inventory": FREEZE,
    }


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("run")
    p.add_argument("--repository", required=True)
    p.add_argument("--private-repository", required=True)
    p.add_argument("--destination", required=True)
    p = sub.add_parser("verify")
    p.add_argument("--destination", required=True)
    args = parser.parse_args()
    result = (
        run(args.repository, args.private_repository, args.destination)
        if args.action == "run"
        else verify(args.destination)
    )
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
