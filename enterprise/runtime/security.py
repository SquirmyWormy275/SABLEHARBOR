"""Executable boundary reference, not a deployed policy engine or model safety claim."""

from datetime import datetime

DISCLOSURES = {
    "read",
    "snippet",
    "citation",
    "export",
    "vector",
    "count",
    "graph",
    "tool_result",
    "answer",
}
FORBIDDEN = {
    "authoritative_write",
    "promote",
    "institutional_judgment",
    "share_memory",
    "train_shared",
}


def authorize(resource, principal, action, now):
    """Filter before retrieval/model context; protected discovery stays server-side."""
    instant = datetime.fromisoformat(now)
    if action in FORBIDDEN or action not in DISCLOSURES | {"existence"}:
        return "DENY"
    if (
        not principal.get("id")
        or principal.get("revoked")
        or resource.get("deleted")
        or resource.get("restore_suppressed")
        or resource.get("disclosure_enabled") is False
    ):
        return "DENY"
    if resource.get("memory_owner") not in (None, principal["id"]):
        return "DENY"
    if resource.get("tenant") != principal.get("tenant"):
        return "DENY"
    if resource.get("expires_at") and instant >= datetime.fromisoformat(
        resource["expires_at"]
    ):
        return "DENY"
    if principal.get("purpose") not in resource.get("purposes", []):
        return "DENY"
    # Existence permission is independent; never includes identity, count or title.
    if action == "existence":
        return (
            "EXISTS_RESTRICTED"
            if principal["id"] in resource.get("existence_readers", [])
            else "DENY"
        )
    if (
        resource.get("classification") == "OPEN"
        and resource.get("rights") == "INTERNAL_REUSE"
    ):
        return "ALLOW"
    if resource.get("rights") not in principal.get("rights", []):
        return "DENY"
    if not set(resource.get("compartments", [])) <= set(
        principal.get("compartments", [])
    ):
        return "DENY"
    if principal["id"] not in resource.get("detail_readers", []):
        return "DENY"
    if not all(
        resource.get(k)
        for k in (
            "restriction_owner",
            "restriction_reason",
            "review_due",
            "challenge_route",
        )
    ):
        return "DENY"
    return "ALLOW"


def disclosed_context(resources, principal, action, now):
    """No rejected text, embeddings, counts, titles or identifiers enter user context."""
    return [
        r["payload"]
        for r in resources
        if authorize(r, principal, action, now) == "ALLOW"
    ]


def delegate(parent, child):
    if child["tenant"] != parent["tenant"] or child["purpose"] != parent["purpose"]:
        raise ValueError("Delegation cannot widen tenant or purpose")
    for key in ("rights", "compartments"):
        if not set(child.get(key, [])) <= set(parent.get(key, [])):
            raise ValueError("Delegation cannot widen rights")
    return child


def revoke_graph(records, root, held=False):
    """Invalidate derived copies; holds retain protected bytes without restoring disclosure."""
    if root not in records:
        raise ValueError("Unknown record")
    affected = {root}
    while True:
        expanded = affected | {
            key
            for key, row in records.items()
            if affected.intersection(row.get("sources", []))
        }
        if expanded == affected:
            break
        affected = expanded
    for key in affected:
        row = records[key]
        row["restore_suppressed"] = True
        row["disclosure_enabled"] = False
        row["disposition"] = (
            "HOLD_RESTRICTED"
            if held or row.get("legal_hold")
            else "DELETE_PENDING_BACKUP_EXPIRY"
        )
        if row["disposition"] != "HOLD_RESTRICTED":
            row.pop("payload", None)
    return affected


def restore(records, tombstones):
    return {
        k: v
        for k, v in records.items()
        if k not in tombstones and not v.get("restore_suppressed")
    }


def assess_evidence(manifest, expected_count, now, actual_required=True):
    required = (
        "source",
        "period_start",
        "period_end",
        "timezone",
        "filters",
        "pagination",
        "transformations",
        "count",
        "hash",
        "reviewer",
        "preparer",
        "origin",
        "complete",
    )
    if not manifest or any(key not in manifest for key in required):
        return "NOT_RUN"
    if (
        not manifest["complete"]
        or manifest["count"] != expected_count
        or expected_count <= 0
    ):
        return "FAIL_INCOMPLETE_POPULATION"
    if manifest["reviewer"] == manifest["preparer"]:
        return "FAIL_SELF_REVIEW"
    if manifest.get("exception_expires") and manifest["exception_expires"] < now:
        return "FAIL_EXPIRED_EXCEPTION"
    if actual_required and manifest["origin"] != "ACTUAL_COLLECTED_EVIDENCE":
        return "NOT_ASSERTED_SYNTHETIC_ONLY"
    return "ELIGIBLE_FOR_REVIEW_NOT_AN_OPINION"


def sla(eligible_minutes, unavailable_minutes, recurring_base):
    if (
        eligible_minutes <= 0
        or not 0 <= unavailable_minutes <= eligible_minutes
        or recurring_base < 0
    ):
        raise ValueError("Invalid SLA measurement population")
    availability = (eligible_minutes - unavailable_minutes) / eligible_minutes
    credit = (
        0
        if unavailable_minutes == 0
        else 0.05
        if availability >= 0.999
        else 0.1
        if availability >= 0.99
        else 0.25
        if availability >= 0.95
        else 0.5
    )
    return {
        "availability": availability,
        "credit_fraction": credit,
        "credit": recurring_base * credit,
        "state": "CUSTOMER_PROPOSED_NOT_VENDOR_ACCEPTED",
    }
