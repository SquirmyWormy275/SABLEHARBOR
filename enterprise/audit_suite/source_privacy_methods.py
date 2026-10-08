"""Examine collected privacy records without company recipes or audit answers.

Inputs are bytes read back from retained audit artifacts plus their ordinary
collection receipts. A recorded token delivery is documentary history; these
methods do not claim executable routing, legal applicability or a complete
enterprise population. They neither author sources nor update audit tasks.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime

from .company_store import _time
from .fresh_sec003_procedure import CLOCK_ID, NATIVE_ID, require

FAMILY = "privacyops"
CASE_SYSTEMS = (
    "privacy_request",
    "privacy_customer_decision",
    "privacy_gate_decision",
    "privacy_release",
    "privacy_receipt",
)
SERVICE_SCOPE = ("service_id", "dataset_id", "customer_id", "contracting_entity_id")
CAUSAL_EDGES = (
    ("privacy_request", "privacy_customer_decision"),
    ("privacy_request", "privacy_gate_decision"),
    ("privacy_customer_decision", "privacy_gate_decision"),
    ("privacy_customer_decision", "privacy_release"),
    ("privacy_gate_decision", "privacy_release"),
    ("privacy_release", "privacy_receipt"),
)
LIMITS = (
    "Selected customer-directed nonpersonal token histories only; no enterprise "
    "ePHI, designated-record-set or full audit-period population is established.",
    "Deliveries and recipient acknowledgments are authored documentary records; "
    "executable routing, network transfer and independent recipient confirmation "
    "have not been reperformed.",
    "This examination does not decide real HIPAA applicability, BA status or "
    "period-specific law, and does not close earlier held cases.",
)


def _identity(source: dict) -> tuple:
    return tuple(source[key] for key in NATIVE_ID)


def _reference(source: dict) -> dict:
    return {key: source[key] for key in CLOCK_ID}


def _prepare(records: list[dict], as_of: str) -> tuple[list[dict], dict]:
    """Reparse retained bytes; a cached parsed document cannot supply evidence."""
    cutoff = _time(as_of)
    prepared, index = [], {}
    for record in records:
        source = record["source"]
        require(set(CLOCK_ID) <= source.keys(), "Exact collected custody clocks required")
        key = _identity(source)
        require(key not in index, "Duplicate collected native version")
        require(
            _time(source["event_at"]) <= _time(source["available_at"]) <= cutoff,
            "Privacy source occurs or becomes available after examination clock",
        )
        require(
            _time(source["imported_at"]) <= _time(datetime.now(UTC).isoformat()),
            "Collected real import clock is in the future",
        )
        receipt = record["receipt"]
        require(
            all(receipt["source"].get(k) == source[k] for k in CLOCK_ID),
            "Ordinary collection receipt custody differs",
        )
        content = record["retained_bytes"]
        require(isinstance(content, bytes), "Actual retained artifact bytes required")
        actual = hashlib.sha256(content).hexdigest()
        require(
            actual == source["sha256"] == record["artifact_sha256"],
            "Retained privacy artifact hash differs",
        )
        require(record["content_type"] == "application/json", "Typed privacy JSON required")
        document = json.loads(content)
        require(isinstance(document, dict), "Structured privacy business document required")
        require(
            record.get("logical_family") == FAMILY,
            "Declared privacy business routing required",
        )
        require(
            source["system"] == FAMILY + "." + record["logical_system"],
            "Logical privacy routing differs from actual native system",
        )
        require(
            all(isinstance(document.get(k), str) and document[k] for k in SERVICE_SCOPE),
            "Explicit selected service/dataset/customer/entity scope required",
        )
        require(
            type(document.get("payload_bytes")) is int
            and document["payload_bytes"] == 0
            and document.get("real_phi_payload") is False
            and document.get("real_world_processing_or_transfer") is False,
            "Nonpersonal fictional privacy boundary differs",
        )
        require(
            document.get("event_at") == source["event_at"]
            and document.get("available_at") == source["available_at"],
            "Privacy document publication clocks differ from custody",
        )
        item = {**record, "document": document}
        prepared.append(item)
        index[key] = item
    require(prepared, "Collected privacy history required")
    require(
        len({(r["source"]["company"], r["source"]["branch"]) for r in prepared}) == 1,
        "One explicitly authorized company branch per examination required",
    )
    require(
        len({tuple(r["document"][k] for k in SERVICE_SCOPE) for r in prepared}) == 1,
        "Collected service/dataset/customer/entity scopes differ",
    )
    return prepared, index


def examine(records: list[dict], *, as_of: str) -> dict:
    """Reconcile the discovered case census and actual recorded release decisions.

    Completeness is tested against the retained month-close roster and source
    sequences, not a baked-in scenario count. Unknown wider populations remain
    unknown. The same method examines either branch without a mode argument.
    """
    rows, index = _prepare(records, as_of)
    systems, joins, unresolved = {}, [], []
    for row in rows:
        systems.setdefault(row["logical_system"], []).append(row)
        for ref in row["document"].get("dependencies", []):
            require(set(CLOCK_ID) - {"imported_at"} <= ref.keys(), "Exact dependency required")
            require(
                (ref["company"], ref["branch"])
                == (row["source"]["company"], row["source"]["branch"]),
                "Privacy dependency crosses company or branch authority",
            )
            target = index.get(_identity(ref))
            if target is None:
                unresolved.append({"from": _reference(row["source"]), "reference": ref})
                continue
            fields = set(CLOCK_ID) if "imported_at" in ref else set(CLOCK_ID) - {"imported_at"}
            require(
                all(ref[k] == target["source"][k] for k in fields),
                "Privacy dependency hash or publication clocks differ",
            )
            require(
                _time(target["source"]["available_at"]) <= _time(row["source"]["event_at"]),
                "Privacy operation cites a source unavailable at its event",
            )
            joins.append({"from": _reference(row["source"]), "to": _reference(target["source"])})

    case_maps = {}
    for system in CASE_SYSTEMS:
        items = systems.get(system, [])
        mapped = {}
        for row in items:
            cid = row["document"].get("case_id")
            require(isinstance(cid, str) and cid, "Explicit privacy case identity required")
            require(cid not in mapped, "Case history needs an explicit version disposition")
            mapped[cid] = row
        case_maps[system] = mapped
    requests = case_maps["privacy_request"]
    ids = set(requests)
    census_defects = {
        system: {
            "missing_requested_case_ids": sorted(ids - mapped.keys()),
            "unmatched_case_ids": sorted(mapped.keys() - ids),
        }
        for system, mapped in case_maps.items()
        if set(mapped) != ids
    }
    closes = systems.get("privacy_reconciliation", [])
    require(len(closes) == 1, "One explicit closed-window reconciliation required")
    close = closes[0]["document"]
    period = close["period"]
    require(_time(period["start"]) <= _time(period["end"]), "Invalid privacy period")
    closed_at = closes[0]["source"]["event_at"]
    window_finished_at_close = _time(period["end"]) <= _time(closed_at)
    declared = close["case_ids"]
    roster_matches = len(declared) == len(set(declared)) and set(declared) == ids
    sequence = [r["document"]["inlet_sequence"] for r in requests.values()]
    require(all(type(n) is int for n in sequence), "Integer inlet sequence required")
    first, last = close["inlet_sequence_first"], close["inlet_sequence_last"]
    require(
        type(first) is int and type(last) is int and 0 < first <= last,
        "Integer inlet bounds required",
    )
    sequence_matches = (
        len(sequence) == last - first + 1
        and all(n == first + i for i, n in enumerate(sorted(sequence)))
        and not close["inlet_sequence_gaps"]
    )
    out_of_period = sorted(
        cid
        for cid, row in requests.items()
        if not _time(period["start"]) <= _time(row["source"]["event_at"]) <= _time(period["end"])
    )
    releases = case_maps["privacy_release"]
    gates = case_maps["privacy_gate_decision"]
    totals = Counter()
    delivery_authority_ids, unknown_delivery_authority = [], []
    for cid, row in releases.items():
        status = row["document"]["execution_status"]
        require(status in {"DELIVERED", "WITHHELD"}, "Unknown release state")
        totals["delivered" if status == "DELIVERED" else "withheld"] += 1
        if status == "DELIVERED":
            if cid not in gates:
                unknown_delivery_authority.append(cid)
            elif gates[cid]["document"]["decision"] != "PERMIT":
                delivery_authority_ids.append(cid)
    cases, mismatch_ids = [], []
    for cid in sorted(ids):
        missing = [system for system in CASE_SYSTEMS if cid not in case_maps[system]]
        if missing:
            cases.append({"case_id": cid, "missing_collected_case_systems": missing})
            continue
        selected = {system: case_maps[system][cid] for system in CASE_SYSTEMS}
        request, customer, gate, release, receipt = (
            selected[system]["document"] for system in CASE_SYSTEMS
        )
        for document in (request, customer, gate, release, receipt):
            if "recipient_id" in document:
                require(
                    isinstance(document["recipient_id"], str) and document["recipient_id"],
                    "Nonempty string recipient identity required",
                )
        for document, field in ((gate, "allowed_scope"), (release, "released_scope")):
            scope = document[field]
            require(
                isinstance(scope, list)
                and all(isinstance(token, str) and token for token in scope),
                "Explicit string-list permission/release scope required",
            )
            require(len(scope) == len(set(scope)), "Duplicate permission/release token scope")
        require(
            type(receipt["copy_in_recipient_scope"]) is bool,
            "Genuine boolean recipient-copy state required",
        )
        reasons = []
        causal_violations = []
        for upstream, consumer in CAUSAL_EDGES:
            source_available = selected[upstream]["source"]["available_at"]
            consumer_event = selected[consumer]["source"]["event_at"]
            if _time(source_available) > _time(consumer_event):
                reasons.append(f"CAUSAL_SOURCE_UNAVAILABLE:{upstream}->{consumer}")
                causal_violations.append(
                    {
                        "source_system": upstream,
                        "source_available_at": source_available,
                        "consumer_system": consumer,
                        "consumer_event_at": consumer_event,
                    }
                )
        delivered = release["execution_status"] == "DELIVERED"
        require(release["execution_status"] in {"DELIVERED", "WITHHELD"}, "Unknown release state")
        require(gate["decision"] in {"PERMIT", "HOLD"}, "Unknown counsel gate state")
        if delivered:
            if gate["decision"] != "PERMIT":
                reasons.append("DELIVERY_WITHOUT_CURRENT_COUNSEL_PERMISSION")
            if customer["decision"] != "PERMIT":
                reasons.append("DELIVERY_WITHOUT_CURRENT_CUSTOMER_PERMISSION")
            if "recipient_id" in gate and release["recipient_id"] != gate["recipient_id"]:
                reasons.append("DELIVERY_RECIPIENT_DIFFERS_FROM_GATE")
            if (
                release["recipient_id"] != request["recipient_id"]
                or release["recipient_id"] != customer["recipient_id"]
            ):
                reasons.append("DELIVERY_RECIPIENT_DIFFERS_FROM_REQUEST_OR_CUSTOMER")
            if set(release["released_scope"]) != set(gate["allowed_scope"]):
                reasons.append("DELIVERY_SCOPE_DIFFERS_FROM_COUNSEL_PERMISSION")
            if "gate_record_id" in release:
                if (
                    release["gate_record_id"]
                    != selected["privacy_gate_decision"]["source"]["record"]
                ):
                    reasons.append("RELEASE_REFERENCES_DIFFERENT_GATE")
                expected_gate = selected["privacy_gate_decision"]["source"]
                if not any(
                    all(ref.get(k) == expected_gate[k] for k in NATIVE_ID)
                    for ref in release.get("dependencies", [])
                ):
                    reasons.append("CURRENT_COUNSEL_GATE_NOT_IN_RELEASE_DEPENDENCIES")
        else:
            if release["released_scope"]:
                reasons.append("WITHHELD_RELEASE_RETAINS_RELEASED_SCOPE")
        recipient_status_known = receipt["status"] in {"RECIPIENT_ACKNOWLEDGED", "NO_DELIVERY"}
        if not recipient_status_known:
            reasons.append("RECIPIENT_STATUS_UNDETERMINED")
        acknowledged = receipt["status"] == "RECIPIENT_ACKNOWLEDGED"
        if (recipient_status_known and acknowledged != delivered) or receipt[
            "copy_in_recipient_scope"
        ] != delivered:
            reasons.append("DELIVERY_AND_RECIPIENT_STATUS_DIFFER")
        if receipt["recipient_id"] != release["recipient_id"]:
            reasons.append("RECIPIENT_STATUS_IDENTITY_DIFFERS")
        if reasons:
            mismatch_ids.append(cid)
        cases.append(
            {
                "case_id": cid,
                "route": request["route"],
                "customer_decision": customer["decision"],
                "counsel_decision": gate["decision"],
                "execution_status": release["execution_status"],
                "worker_authority_source": release.get("worker_authority_source"),
                "recorded_mismatches": reasons,
                "causal_availability_violations": causal_violations,
                "recipient_status_known": recipient_status_known,
                "evidence": {
                    system: {"artifact_id": row["artifact_id"], "source": _reference(row["source"])}
                    for system, row in selected.items()
                },
            }
        )
    count_checks = {
        "customer_decision_count": len(case_maps["privacy_customer_decision"]),
        "counsel_gate_count": len(case_maps["privacy_gate_decision"]),
        "execution_journal_count": len(case_maps["privacy_release"]),
        "delivery_status_count": len(case_maps["privacy_receipt"]),
        "delivered_count": totals["delivered"],
        "withheld_count": totals["withheld"],
        "delivery_authority_mismatch_count": None
        if unknown_delivery_authority
        else len(delivery_authority_ids),
    }
    discrepancies = {
        key: {"claimed": close.get(key), "recomputed": value}
        for key, value in count_checks.items()
        if type(close.get(key)) is not int or close.get(key) != value
    }
    return {
        "schema": "SH_COLLECTED_PRIVACY_EXAMINATION_V1",
        "as_of": _time(as_of),
        "selected_period": period,
        "selected_service_scope": {k: rows[0]["document"][k] for k in SERVICE_SCOPE},
        "recorded_month_close_at": closed_at,
        "selected_window_finished_at_recorded_close": window_finished_at_close,
        "unestablished_period_tail": None
        if window_finished_at_close
        else {
            "after": closed_at,
            "through": period["end"],
            "basis": "RECONCILIATION_RECORDED_BEFORE_DECLARED_WINDOW_END",
        },
        "collected_native_versions": len(rows),
        "selected_request_count": len(ids),
        "case_system_membership_defects": census_defects,
        "declared_case_roster_matches": roster_matches,
        "inlet_sequence_matches": sequence_matches,
        "observed_inlet_sequence": sorted(sequence),
        "requests_outside_declared_period": out_of_period,
        "selected_population_corroborated": bool(ids)
        and not census_defects
        and roster_matches
        and sequence_matches
        and not out_of_period
        and window_finished_at_close,
        "recomputed_counts": count_checks,
        "month_close_discrepancies": discrepancies,
        "recorded_mismatch_case_ids": mismatch_ids,
        "delivery_authority_unknown_case_ids": sorted(unknown_delivery_authority),
        "cases": cases,
        "checked_dependency_joins": joins,
        "uncollected_dependency_references": unresolved,
        "enterprise_population_established": False,
        "executable_routing_reperformed": False,
        "legal_applicability_decided": False,
        "limits": list(LIMITS),
    }
