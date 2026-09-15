"""Paired local release-authorization logging exercise, generated before any audit."""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .company_change_activity import QUALIFICATION as CHANGE_QUALIFICATION
from .company_configuration_activity import read_originals
from .company_store import CompanyStore, CompanyStoreError, _id, _time
from .operating_source_bridge import encoded, sha
from .organization import snapshot
from .private_publication import publish

CONTROL = "SH-SEC-002"
QUALIFICATION = "LOCAL_SECURITY_LOG_COLLECTION_EXERCISE_NOT_DEPLOYED_SIEM_OR_CORPORATE_COVERAGE"


@dataclass(frozen=True)
class LoggingRecipe:
    company_id: str
    source_store_id: str
    source_versions_sha256: str
    source_branch: str
    complete_branch: str
    omission_branch: str
    local_source_id: str
    local_max_ingestion_lag_seconds: int = 120
    source_scenario: str = "OVERRIDE_THEN_ALLOWED"


def event_chain(inputs):
    """Assign a local exercise publisher sequence; never assert upstream native sequence."""
    events, previous = [], ""
    for index, item in enumerate(inputs, 1):
        value = {"sequence": index, "previous_event_sha256": previous, **item}
        previous = sha(encoded(value))
        events.append({**value, "event_sha256": previous})
    return events


def reconcile(publisher_events, received):
    """Compute missing and mismatched hashes from the independent publisher and collector sets."""
    expected, observed = {}, {}
    invalid_claims = set()
    previous = ""
    for index, event in enumerate(publisher_events, 1):
        body = {k: v for k, v in event.items() if k != "event_sha256"}
        if (
            event["sequence"] != index
            or event["previous_event_sha256"] != previous
            or sha(encoded(body)) != event["event_sha256"]
        ):
            raise CompanyStoreError("Publisher sequence/hash chain invalid")
        expected[index] = event["event_sha256"]
        previous = event["event_sha256"]
    for item in received:
        sequence = item["event"]["sequence"]
        if sequence in observed:
            raise CompanyStoreError("Duplicate collected sequence")
        event_body = {k: v for k, v in item["event"].items() if k != "event_sha256"}
        computed = sha(encoded(event_body))
        observed[sequence] = computed
        if computed != item["event"]["event_sha256"]:
            invalid_claims.add(sequence)
    return {
        "publisher_sequences": sorted(expected),
        "collector_sequences": sorted(observed),
        "missing_sequences": sorted(set(expected) - set(observed)),
        "unexpected_sequences": sorted(set(observed) - set(expected)),
        "hash_mismatches": sorted(
            k
            for k in expected.keys() & observed.keys()
            if expected[k] != observed[k] or k in invalid_claims
        ),
        "invalid_collector_hash_claims": sorted(invalid_claims),
        "publisher_chain_head_sha256": previous,
        "publisher_membership_sha256": sha(encoded(expected)),
        "collector_membership_sha256": sha(encoded(observed)),
    }


def ingest(events, *, excluded_decisions, received_at=None):
    """Actually apply the declared local collector filter to existing publisher events."""
    if not isinstance(excluded_decisions, list) or any(
        x not in {"OVERRIDE_USED", "BLOCKED"} for x in excluded_decisions
    ):
        raise CompanyStoreError("Explicit bounded collector filter required")
    result = []
    for event in events:
        if event["authorization_decision"] in excluded_decisions:
            continue
        source_time = datetime.fromisoformat(event["source_event_at"])
        arrival = (
            datetime.fromisoformat(_time(received_at))
            if received_at
            else source_time + timedelta(seconds=60)
        )
        if arrival < source_time:
            raise CompanyStoreError("Collection cannot precede source event")
        result.append(
            {
                "event": event,
                "received_at": _time(arrival.isoformat()),
                "ingestion_lag_seconds": int((arrival - source_time).total_seconds()),
            }
        )
    return result


def generate_pair(destination, *, repository, source_root, recipe: LoggingRecipe):
    destination, repository = Path(destination).absolute(), Path(repository)
    if (
        destination.exists()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(p.is_symlink() for p in (destination, *destination.parents))
    ):
        raise CompanyStoreError("New private nonsymlink destination required")
    if destination.resolve().is_relative_to(Path(source_root).resolve()):
        raise CompanyStoreError("Logging output must be outside original source tree")
    for value in (
        recipe.company_id,
        recipe.source_store_id,
        recipe.source_branch,
        recipe.complete_branch,
        recipe.omission_branch,
        recipe.local_source_id,
    ):
        _id(value)
    if (
        recipe.complete_branch == recipe.omission_branch
        or type(recipe.local_max_ingestion_lag_seconds) is not int
        or not 30 <= recipe.local_max_ingestion_lag_seconds <= 600
    ):
        raise CompanyStoreError(
            "Distinct branches and explicit bounded local lag threshold required"
        )
    scenarios = {
        "OVERRIDE_THEN_ALLOWED": (
            "OVERRIDE_USED",
            "LOCAL-AUTHORIZATION-OVERRIDE",
            "LOCAL_EXERCISE_HIGH",
            "AUTH-ALERT",
        ),
        "BLOCKED_THEN_ALLOWED": (
            "BLOCKED",
            "LOCAL-AUTHORIZATION-BLOCKED",
            "LOCAL_EXERCISE_INFORMATIONAL",
            "BLOCKED-OBS",
        ),
    }
    if not isinstance(recipe.source_scenario, str) or recipe.source_scenario not in scenarios:
        raise CompanyStoreError("Explicit supported native authorization scenario required")
    first_decision, detection_rule, detection_severity, detection_prefix = scenarios[
        recipe.source_scenario
    ]
    originals, source_pin = read_originals(source_root)
    if source_pin != recipe.source_versions_sha256:
        raise CompanyStoreError("Pinned input source versions changed")
    selected = [
        r
        for r in originals
        if r["company"] == recipe.company_id and r["branch"] == recipe.source_branch
    ]
    indexed = {(r["system"], r["record"], r["version"]): r for r in selected}
    gates = sorted(
        [r for r in selected if r["system"] == "release_gate"],
        key=lambda r: (r["event_at"], r["record"]),
    )
    if len(gates) != 2:
        raise CompanyStoreError(
            "This bounded exercise requires two explicitly selected release gates"
        )
    inputs = []
    for row in gates:
        native = json.loads(row["content"])
        if (
            row["origin"] != "AUTHORED_TRAINING_SOURCE"
            or native.get("classification") != CHANGE_QUALIFICATION
            or row["event_at"] is None
            or _time(row["available_at"]) != _time(row["event_at"])
        ):
            raise CompanyStoreError("Expected qualified contemporaneous local authorization source")
        for name in ("artifact", "tests", "peer_review"):
            link = native.get(name)
            if link is None and name == "peer_review":
                continue
            if not isinstance(link, dict):
                raise CompanyStoreError("Exact original authorization support link required")
            support = indexed.get(
                (link.get("system_id"), link.get("record_id"), link.get("version"))
            )
            if (
                support is None
                or support["sha256"] != link.get("sha256")
                or _time(support["available_at"]) > _time(row["event_at"])
            ):
                raise CompanyStoreError("Original authorization support unavailable or changed")
        inputs.append(
            {
                "local_source_id": recipe.local_source_id,
                "source_event_at": _time(row["event_at"]),
                "authorization_decision": native["decision"],
                "upstream": {
                    "source_store_id": recipe.source_store_id,
                    **{
                        k: row[k]
                        for k in (
                            "company",
                            "branch",
                            "system",
                            "record",
                            "version",
                            "sha256",
                            "available_at",
                        )
                    },
                },
                "source_support": {k: native.get(k) for k in ("artifact", "tests", "peer_review")},
            }
        )
    if [x["authorization_decision"] for x in inputs] != [first_decision, "ALLOWED"]:
        raise CompanyStoreError(
            "Selected originals do not support the explicit authorization scenario"
        )
    if first_decision == "BLOCKED":
        releases = [r for r in selected if r["system"] == "local_releases"]
        if len(releases) != 1:
            raise CompanyStoreError("Blocked scenario requires only its later allowed release")
        release = json.loads(releases[0]["content"])
        allowed = gates[1]
        expected_gate = {
            "system_id": allowed["system"],
            "record_id": allowed["record"],
            "version": allowed["version"],
            "sha256": allowed["sha256"],
            "available_at": _time(allowed["available_at"]),
        }
        if (
            releases[0]["origin"] != "AUTHORED_TRAINING_SOURCE"
            or release.get("classification") != CHANGE_QUALIFICATION
            or release.get("artifact") != json.loads(allowed["content"]).get("artifact")
            or _time(releases[0]["available_at"]) < _time(releases[0]["event_at"])
        ):
            raise CompanyStoreError("Qualified release must use exact authorized native artifact")
        release_gate = release.get("gate")
        if not isinstance(release_gate, dict) or set(release_gate) != set(expected_gate):
            raise CompanyStoreError("Exact native release gate reference required")
        normalized_gate = {**release_gate, "available_at": _time(release_gate["available_at"])}
        if normalized_gate != expected_gate or _time(releases[0]["event_at"]) < _time(
            allowed["available_at"]
        ):
            raise CompanyStoreError(
                "Blocked gate cannot release; exact available allowed gate required"
            )
    events = event_chain(inputs)
    first = datetime.fromisoformat(events[0]["source_event_at"])
    last = datetime.fromisoformat(events[-1]["source_event_at"])
    org = snapshot(repository, as_of=first.date().isoformat())
    assignment = next(a for a in org["control_assignments"] if a["control_id"] == CONTROL)
    owner, reviewer = assignment["primary_person_id"], assignment["operating_reviewer_person_id"]
    if not owner or not reviewer or owner == reviewer:
        raise CompanyStoreError("Distinct current scoped logging owner/reviewer required")
    pins = dict(org["source_sha256"])
    for path in (
        "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
        "enterprise/ccf/assurance/design_data/control_procedures.json",
        "enterprise/audit_suite/company_security_logging_activity.py",
    ):
        pins[path] = sha((repository / path).read_bytes())
    recipe_pin = sha(encoded(asdict(recipe)))
    common = {
        "classification": QUALIFICATION,
        "control_ids": [CONTROL],
        "boundary_id": "corporate",
        "local_source_id": recipe.local_source_id,
        "source_sequence_basis": (
            "LOCALLY_ASSIGNED_EXERCISE_PUBLISHER_SEQUENCE_NOT_NATIVE_UPSTREAM_SEQUENCE"
        ),
        "policy_status": "LOCAL_EXERCISE_RULE_NOT_ACCEPTED_ENTERPRISE_POLICY",
        "appointment_status": "SCOPED_CONTACT_ASSIGNMENTS_NOT_EMPLOYMENT_OR_NEW_APPOINTMENT",
        "clock_synchronization_status": "NOT_MEASURED_INGESTION_LAG_IS_NOT_CLOCK_SKEW",
        "coverage_limit": "ONE_PINNED_LOCAL_RELEASE_AUTHORIZATION_SOURCE_NOT_ALL_MATERIAL_SYSTEMS",
        "service_reference": "SVC-developer",
        "service_status": "DESIGN_REFERENCE_NOT_DEPLOYMENT",
        "site_references_only": json.loads(gates[0]["content"]).get("site_references_only", []),
        "professional_sufficiency": "NOT_ASSESSED",
    }
    receipts, summaries = [], []
    with tempfile.TemporaryDirectory(prefix="security-logging-", dir=destination.parent) as temp:
        store = CompanyStore(Path(temp))
        for branch in (recipe.complete_branch, recipe.omission_branch):
            for system in (
                "source_inventory",
                "publisher_originals",
                "publisher_events",
                "collector_configuration",
                "ingestion_journal",
                "publisher_checkpoints",
                "coverage_reconciliation",
                "detection_alerts",
                "response_tickets",
                "review_records",
            ):
                store.register_system(
                    recipe.company_id,
                    branch,
                    system,
                    reviewer if system == "review_records" else owner,
                )
            versions = {}

            def emit(system, identity, at, body, *, raw=None, branch=branch, versions=versions):
                stamp = _time(at.isoformat() if isinstance(at, datetime) else at)
                version = versions.get((system, identity), 0)
                data = (
                    raw
                    if raw is not None
                    else encoded({**common, "record_id": identity, "recorded_at": stamp, **body})
                )
                row = store.append_version(
                    recipe.company_id,
                    branch,
                    system,
                    identity,
                    expected_version=version,
                    command_id="LOG-"
                    + sha(encoded([recipe_pin, branch, system, identity, version])),
                    event_at=stamp,
                    available_at=stamp,
                    content=data,
                    provenance={
                        "name": identity + ".json",
                        "source_reference": identity,
                        "control_ids": [CONTROL],
                        "classification": QUALIFICATION,
                        "operational_fact_status": "LOCAL_EXERCISE_ONLY",
                        "source_versions_sha256": source_pin,
                        "source_store_id": recipe.source_store_id,
                        "source_sha256": pins,
                        "recipe_sha256": recipe_pin,
                        "scoped_assignment": assignment,
                        "custody_basis": (
                            "LOCAL_COPY_OR_DERIVATION_NOT_HISTORICAL_SOURCE_AUTHORSHIP"
                        ),
                        **common,
                    },
                )
                versions[system, identity] = version + 1
                receipts.append(row)
                return {
                    k: row[k]
                    for k in (
                        "company",
                        "branch",
                        "system",
                        "record",
                        "version",
                        "sha256",
                        "available_at",
                    )
                }

            emit(
                "source_inventory",
                "SOURCE-INVENTORY",
                first - timedelta(minutes=5),
                {
                    "required_sources": [
                        {
                            "source_id": recipe.local_source_id,
                            "upstream_system": "release_gate",
                            "upstream_branch": recipe.source_branch,
                            "event_type": "release_authorization_decision",
                        }
                    ],
                    "required_detections": [detection_rule, "LOCAL-COLLECTION-GAP"],
                    "owner_id": owner,
                    "local_max_ingestion_lag_seconds": recipe.local_max_ingestion_lag_seconds,
                    "inventory_basis": "EXPLICIT_LOCAL_EXERCISE_INVENTORY_NOT_ENTERPRISE_CENSUS",
                },
            )
            for row, event in zip(gates, events, strict=True):
                emit(
                    "publisher_originals",
                    row["record"],
                    event["source_event_at"],
                    {},
                    raw=row["content"],
                )
                emit(
                    "publisher_events",
                    f"EVENT-{event['sequence']}",
                    event["source_event_at"],
                    {"event": event},
                )
            checkpoint = emit(
                "publisher_checkpoints",
                "PUBLISHER-CHECKPOINT",
                last + timedelta(seconds=30),
                {
                    "sequences": [e["sequence"] for e in events],
                    "event_hashes": [e["event_sha256"] for e in events],
                    "head_sha256": events[-1]["event_sha256"],
                },
            )
            exclusions = [first_decision] if branch == recipe.omission_branch else []
            config = emit(
                "collector_configuration",
                "COLLECTOR-CONFIG",
                first - timedelta(minutes=2),
                {"excluded_authorization_decisions": exclusions, "config_author_id": owner},
            )
            received = ingest(events, excluded_decisions=exclusions)
            alerts = []

            def retain_ingestion(items, config_ref, alerts=alerts, emit=emit):
                for item in items:
                    event = item["event"]
                    receipt = emit(
                        "ingestion_journal",
                        f"INGEST-{event['sequence']}",
                        item["received_at"],
                        {**item, "collector_configuration": config_ref},
                    )
                    if event["authorization_decision"] == first_decision:
                        alerts.append(
                            emit(
                                "detection_alerts",
                                f"{detection_prefix}-{event['sequence']}",
                                item["received_at"],
                                {
                                    "rule_id": detection_rule,
                                    "severity": detection_severity,
                                    "owner_id": owner,
                                    "ingestion": receipt,
                                    "source_event_sha256": event["event_sha256"],
                                },
                            )
                        )

            retain_ingestion(received, config)
            initial = reconcile(events, received)
            report = emit(
                "coverage_reconciliation",
                "COVERAGE-INITIAL",
                last + timedelta(minutes=2),
                {
                    **initial,
                    "publisher_checkpoint": checkpoint,
                    "checked_by_id": owner,
                    "ingestion_lag_observations": [
                        {
                            "sequence": r["event"]["sequence"],
                            "lag_seconds": r["ingestion_lag_seconds"],
                        }
                        for r in received
                    ],
                },
            )
            gap = bool(
                initial["missing_sequences"]
                or initial["hash_mismatches"]
                or initial["unexpected_sequences"]
            )
            if gap:
                alerts.append(
                    emit(
                        "detection_alerts",
                        "COLLECTION-GAP",
                        last + timedelta(minutes=2),
                        {
                            "rule_id": "LOCAL-COLLECTION-GAP",
                            "severity": "LOCAL_EXERCISE_HIGH",
                            "owner_id": owner,
                            "coverage_report": report,
                            "missing_sequences": initial["missing_sequences"],
                        },
                    )
                )
            initial_alerts = list(alerts)
            for index, alert in enumerate(initial_alerts, 1):
                when = datetime.fromisoformat(alert["available_at"]) + timedelta(minutes=1)
                emit(
                    "response_tickets",
                    f"RESPONSE-{index}",
                    when,
                    {
                        "alert": alert,
                        "owner_id": owner,
                        "status": "ACKNOWLEDGED",
                        "action": (
                            "Inspect pinned local source and collector configuration; no "
                            "enterprise incident conclusion."
                        ),
                    },
                )
            corrected_config = emit(
                "collector_configuration",
                "COLLECTOR-CONFIG",
                last + timedelta(minutes=8),
                {
                    "excluded_authorization_decisions": [],
                    "config_author_id": owner,
                    "previous_configuration": config,
                    "change_basis": (
                        "Explicit local collector reconciliation; no production configuration "
                        "change"
                    ),
                },
            )
            missing = [e for e in events if e["sequence"] in initial["missing_sequences"]]
            backfill = ingest(
                missing,
                excluded_decisions=[],
                received_at=(last + timedelta(minutes=10)).isoformat(),
            )
            retain_ingestion(backfill, corrected_config)
            for index, alert in enumerate(alerts[len(initial_alerts) :], 1):
                emit(
                    "response_tickets",
                    f"RESPONSE-BACKFILL-{index}",
                    datetime.fromisoformat(alert["available_at"]) + timedelta(minutes=1),
                    {
                        "alert": alert,
                        "owner_id": owner,
                        "status": "ACKNOWLEDGED",
                        "action": (
                            "Inspect late-arriving authorization record; "
                            "preserve original detection delay."
                        ),
                    },
                )
            final = reconcile(events, received + backfill)
            recovered = emit(
                "coverage_reconciliation",
                "COVERAGE-BACKFILL",
                last + timedelta(minutes=11),
                {
                    **final,
                    "prior_coverage_report": report,
                    "backfilled_sequences": [r["event"]["sequence"] for r in backfill],
                    "late_ingestion": [
                        {
                            "sequence": r["event"]["sequence"],
                            "lag_seconds": r["ingestion_lag_seconds"],
                            "exceeds_local_lag_threshold": r["ingestion_lag_seconds"]
                            > recipe.local_max_ingestion_lag_seconds,
                        }
                        for r in backfill
                    ],
                    "historical_gap_report_superseded": False,
                },
            )
            emit(
                "review_records",
                "COVERAGE-REVIEW",
                last + timedelta(minutes=12),
                {
                    "reviewer_id": reviewer,
                    "owner_id": owner,
                    "initial_report": report,
                    "later_report": recovered,
                    "review_procedure": (
                        "Compare publisher sequence/hash set, collected originals and later "
                        "backfill; retain original timing differences."
                    ),
                    "observed_initial_missing_sequences": initial["missing_sequences"],
                    "observed_later_missing_sequences": final["missing_sequences"],
                    "whole_control_conclusion": "NOT_MADE",
                },
            )
            summaries.append(
                {
                    "branch": branch,
                    "publisher_events": len(events),
                    "initial_collected": len(received),
                    "initial_missing_sequences": initial["missing_sequences"],
                    "backfilled": len(backfill),
                    "later_missing_sequences": final["missing_sequences"],
                    "source_original_hashes": [r["sha256"] for r in gates],
                }
            )
        if read_originals(source_root)[1] != source_pin:
            raise CompanyStoreError("Original change source changed during logging generation")
        result = {
            "schema": "LOCAL_SECURITY_LOGGING_PAIR_V1",
            "recipe": asdict(recipe),
            "recipe_sha256": recipe_pin,
            "source_versions_sha256": source_pin,
            "source_sha256": pins,
            "assignment": assignment,
            "qualification": QUALIFICATION,
            "records": receipts,
            "summaries": summaries,
        }
        path = Path(temp) / "SOURCE_RECEIPT.json"
        path.write_bytes(encoded(result))
        path.chmod(0o600)
        publish(Path(temp), destination)
    return result
