"""Documentary examination of ordinarily collected legal intake originals.

Reparse retained bytes and exact collection receipts. SQL text in a company
export is descriptive evidence, never executable input. Counts refer only to
the selected registered channels and collected original versions. The methods
do not decide legal applicability, enterprise nonoccurrence, or audit credit.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from .company_store import _time
from .fresh_sec003_procedure import CLOCK_ID, NATIVE_ID, require

SCHEMA = "SH_COLLECTED_LEGAL_INTAKE_EXAMINATION_V1"
SYSTEMS = {
    "legaloriginals": {
        "legal_channel_configuration",
        "legal_channel_export",
        "legal_inbound_message",
        "legal_inbound_attachment",
        "legal_archive_reconciliation",
    },
    "legint": {
        "intake_channel_register",
        "intake_channel_ledger",
        "monthly_intake_screening",
        "intake_tail_reconciliation",
        "legal_matter_classification",
        "quarterly_legal_review",
        "legal_exception_register",
        "period_legal_disposition",
        "independent_intake_review",
        "regulatory_response_playbook",
        "legal_response_exercise",
    },
}
LIMITS = (
    "Registered fictional company channels only; unregistered inboxes, other entities, "
    "real-world matters and enterprise-wide legal-event nonoccurrence are not established.",
    "An export's stored SQL and empty declared roster do not independently prove source "
    "completeness. Only collected original custody and retained company claims are reconciled.",
    "Recorded counsel classification, internal review and response exercises are documentary "
    "judgments; they are not external legal conclusions, regulator approval or auditor opinions.",
    "Source editions, legal applicability, amendments, judicial status and case-specific "
    "deadlines require separate authoritative examination; this method supplies no PASS or N/A.",
)


def _ref(row):
    return {key: row["source"][key] for key in CLOCK_ID}


def _identity(source):
    return tuple(source[key] for key in NATIVE_ID)


def _tokens(value, label):
    require(
        isinstance(value, list)
        and all(isinstance(v, str) and v.strip() for v in value)
        and len(set(value)) == len(value),
        f"Distinct string list required: {label}",
    )
    return value


def _count(value, label):
    require(type(value) is int and value >= 0, f"Nonnegative integer required: {label}")
    return value


def _dt(value):
    return datetime.fromisoformat(_time(value))


def _next_month(value):
    return value.replace(year=value.year + (value.month == 12), month=value.month % 12 + 1)


def _months(scope):
    start, inclusive_end = _dt(scope["period_start"]), _dt(scope["period_end"])
    end = inclusive_end + timedelta(seconds=1)
    require(
        start < end
        and start.day == end.day == 1
        and start.time() == end.time() == datetime.min.time(),
        "Selected scope must declare whole calendar months with second-precision end",
    )
    require(
        (end.year - start.year) * 12 + end.month - start.month <= 120,
        "Bounded selected legal examination period required",
    )
    result = []
    while start < end:
        stop = _next_month(start)
        result.append((start, stop))
        start = stop
    return result


def _prepare(records, as_of):
    rows, index = [], {}
    cutoff = _time(as_of)
    for record in records:
        source = record["source"]
        require(set(CLOCK_ID) <= source.keys(), "Exact collected legal custody required")
        require(
            type(source["version"]) is int and source["version"] > 0,
            "Positive native version required",
        )
        key = _identity(source)
        require(key not in index, "Duplicate collected native legal version")
        require(
            _time(source["event_at"]) <= _time(source["available_at"]) <= cutoff,
            "Legal source unavailable at examination clock",
        )
        require(
            _time(source["imported_at"]) <= _time(datetime.now(UTC).isoformat()),
            "Actual custody import is in the future",
        )
        require(
            all(record["receipt"]["source"].get(k) == source[k] for k in CLOCK_ID),
            "Ordinary legal collection receipt differs from exact source custody",
        )
        content = record["retained_bytes"]
        require(isinstance(content, bytes), "Actual retained legal artifact bytes required")
        require(
            hashlib.sha256(content).hexdigest() == source["sha256"] == record["artifact_sha256"],
            "Retained legal artifact hash differs",
        )
        require(record["content_type"] == "application/json", "Typed legal JSON required")
        family, system = record.get("logical_family"), record.get("logical_system")
        require(
            family in SYSTEMS and system in SYSTEMS[family],
            "Explicit supported legal original/intake route required",
        )
        require(
            source["system"] == family + "." + system,
            "Logical legal route differs from actual native system",
        )
        body = json.loads(content)
        require(isinstance(body, dict), "Structured legal business document required")
        require(
            body.get("record_id") == source["record"],
            "Legal business record identity differs from native custody",
        )
        for field in ("event_at", "available_at"):
            if field in body:
                require(
                    _time(body[field]) == _time(source[field]),
                    "Legal business publication clock differs from custody",
                )
        row = {**record, "document": body}
        rows.append(row)
        index[key] = row
    require(rows, "Collected legal originals/intake history required")
    require(
        len({(r["source"]["company"], r["source"]["branch"]) for r in rows}) == 1,
        "One authorized company branch per legal examination required",
    )
    return rows, index


def examine(records: list[dict], *, as_of: str) -> dict:
    """Reconcile every retained version without a mode, expected count or answer key.

    Required single registry defines the selected service/channel boundary.
    Locator-only references resolve to a collected version available at the
    consumer event; exact native references additionally bind bytes and clocks.
    Later corrections remain separate observations and cannot repair old events.
    """
    rows, index = _prepare(records, as_of)
    by_system, by_locator = defaultdict(list), defaultdict(list)
    for row in rows:
        by_system[row["logical_system"]].append(row)
        by_locator[(row["logical_system"], row["source"]["record"])].append(row)
    registries = by_system["intake_channel_register"]
    require(len(registries) == 1, "One retained channel registry version required")
    registry = registries[0]
    scope = registry["document"].get("scope")
    require(
        isinstance(scope, dict)
        and isinstance(scope.get("boundary"), str)
        and scope["boundary"].strip()
        and scope.get("company_id") == registry["source"]["company"],
        "Explicit selected company/service boundary required",
    )
    require(
        scope.get("unregistered_channel_completeness") == "NOT_ESTABLISHED",
        "Unregistered channel completeness is outside this examination",
    )
    _tokens(scope.get("excluded"), "scope exclusions")
    months = _months(scope)
    channels = set(_tokens(registry["document"].get("channels"), "registered channels"))
    require(channels, "Nonempty registered channel boundary required")
    for row in rows:
        if row["logical_family"] == "legint":
            require(
                row["document"].get("scope") == scope,
                "Intake operation lacks the selected company/service boundary",
            )
        for field in ("scope", "source_scope"):
            if field in row["document"]:
                require(
                    row["document"][field] == scope,
                    "Legal records cross the selected company/service boundary",
                )

    unresolved, joins, discrepancies = [], [], []

    def issue(row, kind, **details):
        discrepancies.append({"source": _ref(row), "kind": kind, **details})

    def locate(consumer, system, record_id, *, version=None, at=None):
        require(isinstance(record_id, str) and record_id.strip(), "Explicit legal locator required")
        require(
            version is None or (type(version) is int and version > 0),
            "Explicit legal locator version must be a positive integer",
        )
        cutoff = _time(at or consumer["source"]["event_at"])
        candidates = [
            r
            for r in by_locator.get((system, record_id), [])
            if (version is None or r["source"]["version"] == version)
            and _time(r["source"]["available_at"]) <= cutoff
        ]
        if not candidates:
            unresolved.append(
                {
                    "from": _ref(consumer),
                    "system": system,
                    "record": record_id,
                    "version": version,
                    "available_at_or_before": cutoff,
                    "basis": "COLLECTED_LOCATOR_UNAVAILABLE_OR_ABSENT",
                }
            )
            return None
        target = max(candidates, key=lambda r: r["source"]["version"])
        joins.append(
            {
                "from": _ref(consumer),
                "to": _ref(target),
                "basis": "RETAINED_RECORD_LOCATOR_AT_CONSUMER_CLOCK",
            }
        )
        return target

    def exact(consumer, ref):
        fields = set(CLOCK_ID) - {"imported_at"}
        require(
            isinstance(ref, dict) and fields <= ref.keys(),
            "Exact legal original reference required",
        )
        require(
            type(ref["version"]) is int and ref["version"] > 0,
            "Exact legal original reference version must be a positive integer",
        )
        require(
            (ref["company"], ref["branch"])
            == (consumer["source"]["company"], consumer["source"]["branch"]),
            "Legal reference crosses company or branch authority",
        )
        target = index.get(_identity(ref))
        if target is None:
            unresolved.append(
                {
                    "from": _ref(consumer),
                    "reference": ref,
                    "basis": "EXACT_NATIVE_ORIGINAL_NOT_COLLECTED",
                }
            )
            return None
        if "imported_at" in ref:
            fields.add("imported_at")
        require(
            all(ref[k] == target["source"][k] for k in fields),
            "Legal original reference hash or custody clock differs",
        )
        require(
            _time(target["source"]["available_at"]) <= _time(consumer["source"]["event_at"]),
            "Legal record cites original unavailable at its event",
        )
        joins.append({"from": _ref(consumer), "to": _ref(target), "basis": "EXACT_NATIVE_CUSTODY"})
        return target

    configurations, continuity_gaps = {}, []
    for row in by_system["legal_channel_configuration"]:
        body = row["document"]
        channel = body.get("channel_id")
        require(
            channel in channels and channel not in configurations,
            "One explicit configuration per registered channel required",
        )
        require(body.get("scope") == scope, "Channel configuration lacks selected service scope")
        require(
            body.get("retained_intake_registry_id") == registry["source"]["record"],
            "Channel configuration cites a different registry",
        )
        locate(row, "intake_channel_register", body["retained_intake_registry_id"])
        start = _dt(body["operation_established_from"])
        require(
            start >= _dt(registry["source"]["event_at"]),
            "Channel operation precedes retained registry authority",
        )
        configurations[channel] = (row, start)
        if start > months[0][0]:
            continuity_gaps.append(
                {
                    "channel_id": channel,
                    "start": months[0][0].isoformat(),
                    "end_exclusive": min(start, months[-1][1]).isoformat(),
                    "state": "EARLIER_RECEPTION_CONTINUITY_NOT_ESTABLISHED",
                    "source": _ref(row),
                }
            )
    missing_configurations = sorted(channels - configurations.keys())

    messages, attachments, linked_attachment_ids = defaultdict(list), [], set()
    for row in by_system["legal_inbound_message"]:
        body = row["document"]
        require(
            body.get("channel_id") in channels, "Original message is outside registered channels"
        )
        require(
            body.get("actual_external_message") is False,
            "Only explicitly fictional retained correspondence is selected",
        )
        received = _dt(body["received_at"])
        require(
            received == _dt(row["source"]["event_at"]),
            "Original receipt event differs from native message custody",
        )
        require(months[0][0] <= received < months[-1][1], "Message is outside selected period")
        for field in ("text", "subject", "sender_role"):
            require(
                isinstance(body.get(field), str) and body[field].strip(),
                "Retained original correspondence text and sender context required",
            )
        refs = body.get("attachment_refs")
        require(isinstance(refs, list), "Original message attachment references required")
        attachment_refs = []
        for ref in refs:
            target = exact(row, ref)
            if target is not None:
                require(
                    target["logical_system"] == "legal_inbound_attachment"
                    and target["document"].get("inbound_message_id") == row["source"]["record"]
                    and target["document"].get("channel_id") == body["channel_id"],
                    "Attachment/message native relationship differs",
                )
                attachment_refs.append(_ref(target))
                linked_attachment_ids.add(_identity(target["source"]))
        messages[row["source"]["record"]].append(row)
        attachments.append(
            {
                "message": _ref(row),
                "attachment_sources": attachment_refs,
                "unresolved_attachment_count": len(refs) - len(attachment_refs),
            }
        )

    orphan_attachments = []
    for row in by_system["legal_inbound_attachment"]:
        require(
            row["document"].get("channel_id") in channels,
            "Original attachment is outside registered channels",
        )
        if _identity(row["source"]) not in linked_attachment_ids:
            orphan_attachments.append(_ref(row))

    def census(channel, start, stop, cutoff):
        selected = {}
        for rid, versions in messages.items():
            available = [r for r in versions if _time(r["source"]["available_at"]) <= _time(cutoff)]
            if not available:
                continue
            row = max(available, key=lambda r: r["source"]["version"])
            body = row["document"]
            if body["channel_id"] == channel and start <= _dt(body["received_at"]) < stop:
                selected[rid] = row
        return selected

    export_observations, export_windows, export_index = [], set(), {}
    for row in by_system["legal_channel_export"]:
        body, before = row["document"], len(discrepancies)
        channel = body.get("channel_id")
        require(channel in channels, "Monthly export outside registered channels")
        start, stop = _dt(body["event_window_start"]), _dt(body["event_window_end_exclusive"])
        require((start, stop) in months, "Monthly export window differs from selected period")
        key = (channel, start, stop)
        require(key not in export_windows, "Export versions require an explicit disposition")
        export_windows.add(key)
        cutoff = body["source_available_as_of"]
        require(
            _time(cutoff) <= _time(row["source"]["event_at"]),
            "Monthly export queries a future source clock",
        )
        require(
            body.get("source_system") == "legal_inbound_message"
            and body.get("event_filter") == "received_at >= start AND received_at < end"
            and body.get("registered_channels_only") is True,
            "Selected export logical source/filter/boundary differs",
        )
        declared = set(_tokens(body.get("declared_message_ids"), "export message identifiers"))
        count = _count(body.get("record_count"), "export record count")
        observed = census(channel, start, stop, cutoff)
        if declared != observed.keys() or count != len(observed):
            issue(
                row,
                "EXPORT_ORIGINAL_COUNT_OR_ROSTER_MISMATCH",
                declared_count=count,
                observed_count=len(observed),
                missing_original_ids=sorted(declared - observed.keys()),
                undeclared_original_ids=sorted(observed.keys() - declared),
            )
        configuration = configurations.get(channel)
        continuity = False
        if configuration is not None:
            config, established = configuration
            require(
                _time(config["source"]["available_at"]) <= _time(row["source"]["event_at"]),
                "Monthly export uses future channel configuration",
            )
            continuity = established <= start
            require(
                _dt(body["channel_operation_start"]) == established
                and _dt(body["window_operational_coverage_start"]) == max(start, established),
                "Export operating window differs from retained channel configuration",
            )
        require(
            type(body.get("full_window_channel_continuity_established")) is bool,
            "Genuine channel continuity Boolean required",
        )
        if body["full_window_channel_continuity_established"] != continuity:
            issue(row, "EXPORT_CHANNEL_CONTINUITY_CLAIM_MISMATCH", derived_continuity=continuity)
        if _dt(row["source"]["event_at"]) < stop or _dt(cutoff) < stop:
            issue(row, "MONTHLY_EXPORT_WINDOW_STILL_OPEN", end_exclusive=stop.isoformat())
        observation = {
            "source": _ref(row),
            "channel_id": channel,
            "start": start.isoformat(),
            "end_exclusive": stop.isoformat(),
            "observed_original_ids": sorted(observed),
            "observed_original_sources": [_ref(observed[k]) for k in sorted(observed)],
            "recorded_query": body.get("query"),
            "query_executed": False,
            "count_roster_agrees": before == len(discrepancies),
            "full_window_channel_continuity": continuity,
        }
        export_observations.append(observation)
        export_index[key] = (row, observation)
    expected_windows = {(c, a, b) for c in channels for a, b in months}
    missing_exports = [
        {"channel_id": c, "start": a.isoformat(), "end_exclusive": b.isoformat()}
        for c, a, b in sorted(expected_windows - export_windows)
    ]

    ledger_observations, ledger_windows = {}, {}
    for row in by_system["intake_channel_ledger"]:
        body = row["document"]
        channel = body.get("channel_id")
        require(
            channel in channels and body.get("scope") == scope,
            "Ledger is outside registered scoped channels",
        )
        start, stop = _dt(body["window_start"]), _dt(body["window_end"]) + timedelta(seconds=1)
        require((start, stop) in months, "Ledger month differs from selected period")
        cutoff = _dt(body["export_cutoff"])
        require(
            start <= cutoff < stop and cutoff <= _dt(row["source"]["event_at"]),
            "Ledger cutoff outside its window or future publication",
        )
        require(
            type(body.get("remaining_day_followup_required")) is bool,
            "Genuine ledger follow-up Boolean required",
        )
        declared = body.get("intake_items")
        require(
            isinstance(declared, list) and all(isinstance(i, dict) for i in declared),
            "Ledger intake item list required",
        )
        ids = _tokens([i.get("item_id") for i in declared], "ledger item identifiers")
        count = _count(body.get("record_count"), "ledger record count")
        observed = census(channel, start, cutoff + timedelta(microseconds=1), body["export_cutoff"])
        before = len(discrepancies)
        if set(ids) != observed.keys() or count != len(observed):
            issue(
                row,
                "LEDGER_ORIGINAL_COUNT_OR_ROSTER_MISMATCH",
                declared_count=count,
                observed_count=len(observed),
                missing_original_ids=sorted(set(ids) - observed.keys()),
                undeclared_original_ids=sorted(observed.keys() - set(ids)),
            )
        for item in declared:
            original = observed.get(item["item_id"])
            if original is not None:
                for field in ("received_at", "subject", "sender_role"):
                    equal = (
                        _time(item[field]) == _time(original["document"][field])
                        if field == "received_at"
                        else item[field] == original["document"][field]
                    )
                    if not equal:
                        issue(
                            row,
                            "LEDGER_ORIGINAL_CONTEXT_MISMATCH",
                            item_id=item["item_id"],
                            field=field,
                        )
        ledger_observations[_identity(row["source"])] = {
            "source": _ref(row),
            "channel_id": channel,
            "start": start.isoformat(),
            "end_exclusive": stop.isoformat(),
            "cutoff": cutoff.isoformat(),
            "observed_original_ids": sorted(observed),
            "original_sources": [_ref(observed[k]) for k in sorted(observed)],
            "count_roster_agrees": before == len(discrepancies),
            "tail_required": cutoff < stop,
        }
        ledger_windows[_identity(row["source"])] = (start, stop, cutoff)

    classifications = []
    for row in by_system["legal_matter_classification"]:
        body = row["document"]
        require(
            body.get("scope") == scope and type(body.get("official_regulator_notice")) is bool,
            "Scoped genuine recorded counsel classification required",
        )
        original = locate(row, "legal_inbound_message", body["source_item_id"])
        playbooks = [
            p
            for p in by_system["regulatory_response_playbook"]
            if _time(p["source"]["available_at"]) <= _time(row["source"]["event_at"])
        ]
        classifications.append(
            {
                "source": _ref(row),
                "original": _ref(original) if original else None,
                "recorded_classification": body.get("classification"),
                "recorded_official_regulator_notice": body["official_regulator_notice"],
                "recorded_response_route": body.get("response_route"),
                "contemporaneously_available_playbook_sources": [_ref(p) for p in playbooks],
                "explicit_classification_to_playbook_link_established": False,
                "independent_legal_conclusion": False,
            }
        )

    screening_observations = {}
    for row in by_system["monthly_intake_screening"]:
        body = row["document"]
        locate(row, "intake_channel_register", body["registry_record_id"])
        require(
            body["registry_record_id"] == registry["source"]["record"],
            "Screening uses a different selected registry",
        )
        reviewed = set(_tokens(body.get("reviewed_channel_ids"), "screened channels"))
        require(reviewed <= channels, "Screening includes unregistered channel")
        ledgers = [
            locate(row, "intake_channel_ledger", rid)
            for rid in _tokens(body.get("ledger_record_ids"), "screening ledgers")
        ]
        retained = [r for r in ledgers if r is not None]
        require(
            len({r["document"]["channel_id"] for r in retained}) == len(retained),
            "Repeated screening channel ledger",
        )
        windows = {ledger_windows[_identity(r["source"])][:2] for r in retained}
        require(len(windows) <= 1, "Screening combines different monthly windows")
        joined_channels = {r["document"]["channel_id"] for r in retained}
        missing = sorted(channels - reviewed)
        if missing or joined_channels != reviewed:
            issue(
                row,
                "SCREENING_REGISTERED_CHANNEL_OMISSION",
                missing_channel_ids=missing,
                reviewed_without_retained_ledger=sorted(reviewed - joined_channels),
            )
        for rid in _tokens(body.get("classification_record_ids", []), "screening classifications"):
            locate(row, "legal_matter_classification", rid)
        known_through = body.get("reviewed_through")
        if known_through is not None:
            require(
                _time(known_through) <= _time(row["source"]["event_at"]),
                "Screening claims a future review cutoff",
            )
        window = next(iter(windows), None)
        ledger_census = sorted(
            {
                i
                for r in retained
                for i in ledger_observations[_identity(r["source"])]["observed_original_ids"]
            }
        )
        observation = {
            "source": _ref(row),
            "recorded_state": body.get("screening_state"),
            "reviewed_channel_ids": sorted(reviewed),
            "missing_channel_ids": missing,
            "joined_ledger_sources": [_ref(r) for r in retained],
            "original_ids_in_joined_ledgers": ledger_census,
            "reviewed_through": known_through,
            "month_window": {"start": window[0].isoformat(), "end_exclusive": window[1].isoformat()}
            if window
            else None,
            "historical_exception_id": body.get("historical_exception_id"),
            "month_tail_corroborated_at_screening": False,
        }
        # A screening is not itself a full-month extract, even if it says CLOSED.
        if window and _dt(row["source"]["event_at"]) < window[1]:
            issue(row, "SCREENING_MONTH_TAIL_STILL_OPEN", end_exclusive=window[1].isoformat())
        screening_observations[_identity(row["source"])] = observation

    tail_observations = {}
    for row in by_system["intake_tail_reconciliation"]:
        body = row["document"]
        tail_channels = set(_tokens(body.get("channel_ids"), "tail channels"))
        require(tail_channels <= channels, "Tail includes unregistered channel")
        start, stop = _dt(body["window_start"]), _dt(body["window_end"]) + timedelta(seconds=1)
        require(
            any(a <= start < stop == b for a, b in months), "Tail outside declared monthly window"
        )
        if _dt(row["source"]["event_at"]) < stop:
            issue(row, "TAIL_PUBLISHED_BEFORE_WINDOW_END", end_exclusive=stop.isoformat())
        screening = locate(
            row,
            "monthly_intake_screening",
            body["related_screening_id"],
            version=body.get("related_screening_version"),
        )
        require(
            isinstance(body.get("additional_intake_items"), list), "Tail intake item list required"
        )
        items = body["additional_intake_items"]
        require(all(isinstance(i, dict) for i in items), "Structured tail intake items required")
        declared = set(_tokens([i.get("item_id") for i in items], "tail item identifiers"))
        observed = {
            rid: original
            for c in tail_channels
            for rid, original in census(c, start, stop, row["source"]["event_at"]).items()
        }
        if declared != observed.keys():
            issue(
                row,
                "TAIL_ORIGINAL_ROSTER_MISMATCH",
                missing_original_ids=sorted(declared - observed.keys()),
                undeclared_original_ids=sorted(observed.keys() - declared),
            )
        missing = sorted(channels - tail_channels)
        if missing:
            issue(row, "TAIL_REGISTERED_CHANNEL_OMISSION", missing_channel_ids=missing)
        if screening is not None:
            sw = screening_observations[_identity(screening["source"])]["month_window"]
            require(
                sw is not None and _dt(sw["end_exclusive"]) == stop and _dt(sw["start"]) <= start,
                "Tail refers to screening for a different monthly window",
            )
            screen_ledgers = screening_observations[_identity(screening["source"])][
                "joined_ledger_sources"
            ]
            for ref in screen_ledgers:
                ledger = ledger_observations[_identity(ref)]
                if ledger["channel_id"] in tail_channels and _dt(ledger["cutoff"]) != start:
                    issue(
                        row,
                        "TAIL_LEDGER_BRIDGE_GAP",
                        channel_id=ledger["channel_id"],
                        ledger_cutoff=ledger["cutoff"],
                        tail_start=start.isoformat(),
                    )
        tail_observations[_identity(row["source"])] = {
            "source": _ref(row),
            "recorded_state": body.get("extract_state"),
            "start": start.isoformat(),
            "end_exclusive": stop.isoformat(),
            "channel_ids": sorted(tail_channels),
            "missing_channel_ids": missing,
            "original_ids": sorted(observed),
            "screening_source": _ref(screening) if screening else None,
            "retrospective": screening is not None and row["source"]["version"] > 1,
            "erases_prior_screening_observation": False,
        }

    exception_observations = []
    for row in by_system["legal_exception_register"]:
        body = row["document"]
        exception_observations.append(
            {
                "source": _ref(row),
                "recorded_status": body.get("status"),
                "affected_records": _tokens(
                    body.get("affected_records", []), "exception affected records"
                ),
            }
        )

    quarter_observations = []
    for row in by_system["quarterly_legal_review"]:
        body = row["document"]
        screens = [
            locate(row, "monthly_intake_screening", rid)
            for rid in _tokens(body.get("screening_record_ids", []), "quarter screenings")
        ]
        versions = body.get("tail_record_versions", {})
        require(
            isinstance(versions, dict)
            and all(
                isinstance(k, str) and k.strip() and type(v) is int and v > 0
                for k, v in versions.items()
            ),
            "Exact positive quarter tail versions required",
        )
        tails = [
            locate(row, "intake_tail_reconciliation", rid, version=v)
            for rid, v in sorted(versions.items())
        ]
        exception_id = body.get("historical_exception_id")
        exception = locate(row, "legal_exception_register", exception_id) if exception_id else None
        affected = [
            e
            for e in by_system["legal_exception_register"]
            if row["source"]["record"] in e["document"].get("affected_records", [])
            and _time(e["source"]["available_at"]) <= _time(row["source"]["event_at"])
        ]
        quarter_observations.append(
            {
                "source": _ref(row),
                "recorded_state": body.get("review_state"),
                "screening_sources": [_ref(r) for r in screens if r],
                "tail_sources": [_ref(r) for r in tails if r],
                "referenced_exception_source": _ref(exception) if exception else None,
                "referenced_exception_status": exception["document"].get("status")
                if exception
                else None,
                "contemporaneous_affected_exception_states": [
                    {"source": _ref(e), "recorded_status": e["document"].get("status")}
                    for e in affected
                ],
                "no_implicit_exception_closure": True,
            }
        )

    context_observations = []
    for system in (
        "period_legal_disposition",
        "independent_intake_review",
        "legal_archive_reconciliation",
    ):
        for row in by_system[system]:
            body = row["document"]
            if "prior_selected_contract_basis" in body:
                exact(row, body["prior_selected_contract_basis"])
            for rid in _tokens(body.get("monthly_screening_ids", []), "period screenings"):
                locate(row, "monthly_intake_screening", rid)
            for rid in _tokens(
                body.get("open_exception_ids", body.get("historical_exception_ids", [])),
                "period exceptions",
            ):
                locate(row, "legal_exception_register", rid)
            if "source_record_ids" in body:
                for rid in _tokens(body["source_record_ids"], "independent review source records"):
                    if rid == registry["source"]["record"]:
                        locate(row, "intake_channel_register", rid)
                    else:
                        locate(
                            row,
                            "period_legal_disposition",
                            rid,
                            version=body.get("period_disposition_version"),
                        )
            for rid, version in body.get("tail_record_versions", {}).items():
                require(
                    type(version) is int and version > 0, "Positive period tail version required"
                )
                locate(row, "intake_tail_reconciliation", rid, version=version)
            count_basis = {
                "declared_channel_count": len(channels),
                "monthly_ledger_count": len(
                    {
                        r["source"]["record"]
                        for r in by_system["intake_channel_ledger"]
                        if _time(r["source"]["available_at"]) <= _time(row["source"]["event_at"])
                    }
                ),
                "screening_record_count": len(
                    {
                        r["source"]["record"]
                        for r in by_system["monthly_intake_screening"]
                        if _time(r["source"]["available_at"]) <= _time(row["source"]["event_at"])
                    }
                ),
                "inbound_message_count": len(
                    {
                        r["source"]["record"]
                        for r in by_system["legal_inbound_message"]
                        if _time(r["source"]["available_at"]) <= _time(row["source"]["event_at"])
                    }
                ),
                "retained_attachment_count": len(
                    {
                        r["source"]["record"]
                        for r in by_system["legal_inbound_attachment"]
                        if _time(r["source"]["available_at"]) <= _time(row["source"]["event_at"])
                    }
                ),
                "monthly_export_count": len(
                    {
                        r["source"]["record"]
                        for r in by_system["legal_channel_export"]
                        if _time(r["source"]["available_at"]) <= _time(row["source"]["event_at"])
                    }
                ),
            }
            for field, observed in count_basis.items():
                if field in body and _count(body[field], field) != observed:
                    issue(
                        row,
                        "REVIEW_RETAINED_COUNT_MISMATCH",
                        field=field,
                        declared_count=body[field],
                        observed_count=observed,
                    )
            if system == "legal_archive_reconciliation":
                declared_channels = set(
                    _tokens(body.get("registered_channel_ids"), "archive registered channels")
                )
                if declared_channels != channels:
                    issue(
                        row,
                        "ARCHIVE_REGISTERED_CHANNEL_ROSTER_MISMATCH",
                        missing_channel_ids=sorted(channels - declared_channels),
                        unexpected_channel_ids=sorted(declared_channels - channels),
                    )
                require(
                    _dt(body["period_end_exclusive"]) == months[-1][1],
                    "Archive period boundary differs from selected registry",
                )
                declared_ids = set(
                    _tokens(body.get("retained_summary_item_ids"), "archive retained messages")
                )
                observed_ids = {
                    r["source"]["record"]
                    for r in by_system["legal_inbound_message"]
                    if _time(r["source"]["available_at"]) <= _time(row["source"]["event_at"])
                }
                if declared_ids != observed_ids:
                    issue(
                        row,
                        "ARCHIVE_RETAINED_ORIGINAL_ROSTER_MISMATCH",
                        missing_original_ids=sorted(declared_ids - observed_ids),
                        undeclared_original_ids=sorted(observed_ids - declared_ids),
                    )
            context_observations.append(
                {
                    "source": _ref(row),
                    "logical_system": system,
                    "recorded_statement": body.get("statement"),
                    "recorded_cutoff": body.get("review_cutoff"),
                    "recorded_period_end": body.get("reviewed_period_end"),
                    "later_period_tail": body.get("later_period_tail"),
                    "claims_not_external_assurance": True,
                }
            )

    playbook_observations, exercise_observations = [], []
    for row in by_system["regulatory_response_playbook"]:
        procedure = _tokens(row["document"].get("procedure"), "recorded response playbook steps")
        require(procedure, "Recorded response playbook procedure required")
        playbook_observations.append(
            {
                "source": _ref(row),
                "recorded_procedure": procedure,
                "recorded_authority_status": row["document"].get("2027_primary_authority_status"),
                "current_legal_authority_verified": False,
            }
        )
    for row in by_system["legal_response_exercise"]:
        body = row["document"]
        require(
            body.get("exercise_only") is True,
            "Live legal-response execution is outside selected method",
        )
        if body.get("prior_report_id") is not None:
            locate(row, "legal_response_exercise", body["prior_report_id"])
        exercise_observations.append(
            {
                "source": _ref(row),
                "exercise_only": True,
                "recorded_decision": body.get("decision"),
                "recorded_status": body.get("status"),
                "actual_regulator_response_performed": False,
            }
        )

    return {
        "schema": SCHEMA,
        "as_of": _time(as_of),
        "scope": scope,
        "registry_source": _ref(registry),
        "registered_channel_ids": sorted(channels),
        "source_count": len(rows),
        "original_message_identity_count": len(messages),
        "original_message_version_count": len(by_system["legal_inbound_message"]),
        "retained_attachment_version_count": len(by_system["legal_inbound_attachment"]),
        "expected_channel_month_count": len(expected_windows),
        "monthly_export_count": len(export_windows),
        "monthly_exports": export_observations,
        "missing_monthly_exports": missing_exports,
        "missing_channel_configurations": missing_configurations,
        "channel_continuity_gaps": continuity_gaps,
        "original_attachment_joins": attachments,
        "ledger_observations": list(ledger_observations.values()),
        "unmatched_retained_attachment_sources": orphan_attachments,
        "screening_history": list(screening_observations.values()),
        "tail_history": list(tail_observations.values()),
        "classification_history": classifications,
        "quarter_history": quarter_observations,
        "exception_history": exception_observations,
        "context_history": context_observations,
        "playbook_history": playbook_observations,
        "exercise_history": exercise_observations,
        "native_and_locator_joins": joins,
        "unresolved_source_links": unresolved,
        "documentary_discrepancies": discrepancies,
        "selected_export_original_roster_corroborated": not missing_exports
        and not missing_configurations
        and all(e["count_roster_agrees"] for e in export_observations),
        "original_attachment_custody_corroborated": (
            not orphan_attachments
            and all(a["unresolved_attachment_count"] == 0 for a in attachments)
        )
        if messages
        else None,
        "examined_source_links_resolved": not unresolved,
        "configuration_declares_whole_selected_period_continuity": not continuity_gaps
        and not missing_configurations,
        "whole_period_channel_continuity_established": False,
        "continuity_basis": (
            "Retained channel configuration and export claims; original communications-system "
            "operation was not independently queried"
        ),
        "enterprise_nonoccurrence_established": False,
        "independent_legal_conclusion": False,
        "audit_task_credit": None,
        "limits": list(LIMITS),
    }
