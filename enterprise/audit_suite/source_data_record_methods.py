"""Selected B05 examinations of ordinary collected company originals.

The callback consumes retained bytes, receipts and the current examination
clock only. It does not fetch files named inside business documents, open a
database, execute a company recipe or change a workroom. Documentary custody,
local arithmetic and selected exceptions remain separate from legal decisions,
complete populations, production enforcement and professional assurance.
"""

from __future__ import annotations

import calendar
import hashlib
import json
import re
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from . import source_privacy_methods as privacy
from .company_store import _time
from .fresh_sec003_procedure import CLOCK_ID, NATIVE_ID, require
from .inference import _json

CONTRACT_PATH = Path(__file__).with_name("source_data_record_method_contracts_v1.json")
CONTRACT_SHA256 = "db034d4da5b330eb35296c4c3541f30f65566f09048802acce49459cdc0ff8e8"
PRIVACY_SHA256 = "1b9b3127c5d40dbb5bf1cb79d160ad089ce84d175a8abed83e9976aaa9ffe7db"
FAMILIES = {
    "dataset",
    "processing",
    "dat002rights",
    "privacyops",
    "phi_ba",
    "retention",
    "controlled_record",
    "rec003",
    "integrity",
    "extraction",
    "supplementalops",
    "common-dq",  # Optional exact collected dependency; never substituted from rec003.
}
ARRAY_ROLES = {
    ("rec003", "quality_raw"),
    ("rec003", "quality_reference"),
    ("common-dq", "quality_raw"),
    ("common-dq", "quality_reference"),
    ("integrity", "test_copy"),
}
SHA = re.compile(r"[0-9a-f]{64}\Z")
BOOLEAN_FIELDS = {
    "real_phi_payload",
    "real_world_processing_or_transfer",
    "real_world_operation",
    "real_world_personal_data",
    "real_world_processing",
    "real_world_exposure",
    "fixture_contains_real_phi",
    "intake_control_verified",
    "retention_rule_approved",
    "deletion_rule_approved",
    "invalid_public_local_metadata_label",
    "local_label_quarantined",
    "invalid_label_history_open",
    "attempted_request_only",
    "new_flow_executed",
    "payload_copied_or_transferred",
    "external_request_or_response_sent",
    "copy_sent",
    "accepted_amendment",
    "accounting_complete",
    "complete_record_population",
    "record_copy_prepared",
    "premature_no_record_mark",
    "subject_exported",
    "class_trigger_obligation_accepted",
    "attempted_premature_disposition",
    "unlink_executed",
    "deletion_verified",
    "secure_erasure_claimed",
    "fixture_copy_retained",
    "current_effective",
    "hold",
    "actual_deletion",
    "actual_departure",
    "exact_bytes",
    "old_marker_present",
    "preserved_copy_retrievable",
    "source_originals_untouched",
    "retrieved_before_departure",
    "permitted_local_model_retrieval",
    "copy_in_recipient_scope",
    "export_page_truncated",
    "authority_verified_by_customer",
    "sender_relationship",
    "recipient_relationship",
    "information_relates_to_both_relationships",
    "ordinary_consent_present",
    "required_authorization",
    "plain_language",
    "right_to_revoke_statement",
    "conditioning_statement",
    "redisclosure_statement",
    "customer_copy_provided",
    "previous_reliance_before_revocation",
    "separate_notes_authorization",
    "combined_with_general_authorization",
    "remuneration",
    "remuneration_statement",
    "face_to_face_or_nominal_gift",
    "individual_available",
    "recipient_authority_verified",
    "notice_assurance_documented",
    "qualified_protective_order_assurance_documented",
    "reproductive_health_content",
    "enforceable_mandate",
    "actual_knowledge_of_identifiability",
    "reidentification_mechanism_released",
    "dua_executed_in_simulation",
    "no_reidentification_no_contact_terms",
    "deidentified_claim",
    "entire_record_requested",
    "entire_record_necessity_justified",
    "individual_agreed_to_termination",
    "paid_in_full_item",
    "paid_by_individual_not_plan",
    "solely_paid_in_full_item",
    "health_plan_disclosure",
    "otherwise_required_by_law",
    "reasonable_request",
    "default_contact_suppressed",
    "explanation_demanded",
    "checked_before_first_transform",
    "retrieved",
    "usable_JSON",
    "semantic_valid",
    "content_authentic",
    "earlier_acceptance_retained",
    "verified_customer_delegation",
    "verified_individual_authority",
}


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def integer(value, label, *, positive=False):
    require(type(value) is int and value >= int(positive), "Strict integer " + label + " required")
    return value


def tokens(value, label):
    require(
        isinstance(value, list)
        and all(isinstance(v, str) and v for v in value)
        and len(set(value)) == len(value),
        "Distinct explicit " + label + " required",
    )
    return set(value)


def strict_fields(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in BOOLEAN_FIELDS and child is not None:
                # usable_JSON is also an actual parsed document in recovery records.
                if key != "usable_JSON" or not isinstance(child, dict):
                    require(type(child) is bool, "Strict Boolean field " + key + " required")
            strict_fields(child)
    elif isinstance(value, list):
        for child in value:
            strict_fields(child)


def identity(source):
    return tuple(source[k] for k in NATIVE_ID)


def refs(value, path="$"):
    if isinstance(value, dict):
        if set(NATIVE_ID) <= value.keys():
            yield path, value
        else:
            for name, child in value.items():
                yield from refs(child, path + "." + name)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from refs(child, f"{path}[{index}]")


class History:
    """Typed native custody and date-effective joins, never a source fetcher."""

    def __init__(self, records, as_of):
        self.as_of, self.rows, self.index, self.links = _time(as_of), [], {}, []
        now = _time(datetime.now(UTC).isoformat())
        for record in records:
            source, receipt = record["source"], record["receipt"]
            require(set(CLOCK_ID) <= source.keys(), "Exact native clocks required")
            require(
                type(source["version"]) is int
                and source["version"] > 0
                and all(isinstance(source[k], str) and source[k] for k in NATIVE_ID[:-1])
                and isinstance(source["sha256"], str)
                and SHA.fullmatch(source["sha256"]),
                "Strict native identity/version/hash required",
            )
            require(
                source["event_at"] is not None
                and _time(source["event_at"]) <= _time(source["available_at"]) <= self.as_of
                and _time(source["imported_at"]) <= now,
                "Selected source chronology exceeds examination clock",
            )
            raw = record.get("retained_bytes", record.get("content"))
            require(isinstance(raw, bytes), "Actual retained bytes required")
            require(
                type(receipt["source"].get("version")) is int
                and all(receipt["source"].get(k) == source[k] for k in CLOCK_ID)
                and type(receipt.get("content_bytes")) is int
                and receipt["content_bytes"] == len(raw)
                and all(
                    isinstance(receipt.get(k), str) and receipt[k]
                    for k in ("engagement_id", "principal_id", "command_id")
                )
                and _time(source["available_at"]) <= _time(receipt["simulated_as_of"]) <= self.as_of
                and _time(source["imported_at"]) <= _time(receipt["collected_at"]) <= now,
                "Ordinary receipt identity/count/clocks differ",
            )
            require(
                sha(raw) == source["sha256"] == record["artifact_sha256"],
                "Retained artifact hash differs",
            )
            require(
                isinstance(record.get("artifact_id"), str) and record["artifact_id"],
                "Actual artifact identity required",
            )
            family, role = source["system"].split(".", 1)
            require(
                family in FAMILIES
                and record.get("logical_family") == family
                and record.get("logical_system") == role,
                "Native business routing differs",
            )
            media = record.get("content_type", source.get("provenance", {}).get("content_type"))
            require(media == "application/json", "Typed B05 JSON original required")
            document = _json(raw)
            require(
                isinstance(document, list if (family, role) in ARRAY_ROLES else dict),
                "Business document type differs from native role",
            )
            strict_fields(document)
            if isinstance(document, dict):
                for field in (
                    "real_phi_payload",
                    "real_world_processing_or_transfer",
                    "real_world_operation",
                    "real_world_personal_data",
                    "fixture_contains_real_phi",
                ):
                    if field in document:
                        require(
                            document[field] is False,
                            "Fictional nonpersonal source boundary differs",
                        )
                for field in ("event_at", "available_at"):
                    if field in document:
                        require(
                            _time(document[field]) == _time(source[field]),
                            "Business publication clock differs from native source",
                        )
            key = identity(source)
            require(key not in self.index, "Duplicate collected native version")
            row = {
                **{k: v for k, v in record.items() if k != "document"},
                "retained_bytes": raw,
                "content_type": media,
                "document": document,
                "family": family,
                "role": role,
            }
            self.rows.append(row)
            self.index[key] = row
        require(self.rows, "Collected B05 originals required")
        require(
            len({(r["source"]["company"], r["source"]["branch"]) for r in self.rows}) == 1
            and len(
                {(r["receipt"]["engagement_id"], r["receipt"]["principal_id"]) for r in self.rows}
            )
            == 1,
            "One company/branch/engagement/performer required",
        )
        for row in self.rows:
            for path, ref in refs(row["document"]):
                target, status = self.resolve(ref, at=row["source"]["event_at"])
                self.links.append(
                    {
                        "from_artifact_id": row["artifact_id"],
                        "locator": path,
                        "reference": ref,
                        "status": status,
                        "target_artifact_id": target["artifact_id"] if target else None,
                    }
                )

    def select(self, family, roles=None):
        return sorted(
            (
                r
                for r in self.rows
                if r["family"] == family and (roles is None or r["role"] in roles)
            ),
            key=lambda r: (r["source"]["event_at"], r["source"]["record"], r["source"]["version"]),
        )

    def resolve(self, ref, *, at=None):
        require(
            isinstance(ref, dict)
            and set(NATIVE_ID) <= ref.keys()
            and type(ref["version"]) is int
            and ref["version"] > 0,
            "Strict native dependency required",
        )
        if ref.get("status") == "RESTRICTED_UNREGISTERED_DEPENDENCY":
            require(
                ref.get("event_at") is None
                and "sha256" not in ref
                and isinstance(ref.get("custody_id"), str)
                and ref["custody_id"],
                "Restricted witness cannot impersonate native custody",
            )
            return None, "RESTRICTED_ORIGINAL_NOT_COLLECTED"
        if (ref["company"], ref["branch"]) != (
            self.rows[0]["source"]["company"],
            self.rows[0]["source"]["branch"],
        ):
            return None, "OUTSIDE_COLLECTED_BRANCH_AUTHORITY"
        require(
            set(CLOCK_ID) - {"imported_at"} <= ref.keys(), "Exact dependency hash/clocks required"
        )
        target = self.index.get(identity(ref))
        if target is None:
            return None, "ORIGINAL_NOT_COLLECTED"
        fields = set(CLOCK_ID) if "imported_at" in ref else set(CLOCK_ID) - {"imported_at"}
        require(all(ref[k] == target["source"][k] for k in fields), "Dependency hash/clocks differ")
        if at is not None and _time(target["source"]["available_at"]) > _time(at):
            return target, "UNAVAILABLE_AT_OPERATION"
        return target, "EXACT_COLLECTED_ORIGINAL"

    def shorthand(self, token, *, at=None):
        require(
            isinstance(token, str) and len(token.split("/")) == 3,
            "Explicit source shorthand required",
        )
        role, record, version = token.split("/")
        require(version.isdecimal() and int(version) > 0, "Positive shorthand version required")
        candidates = [
            r
            for r in self.select("supplementalops", {role})
            if r["source"]["record"] == record and r["source"]["version"] == int(version)
        ]
        if not candidates:
            return None, "ORIGINAL_NOT_COLLECTED"
        row = candidates[0]
        if at is not None and _time(row["source"]["available_at"]) > _time(at):
            return row, "UNAVAILABLE_AT_OPERATION"
        return row, "EXACT_COLLECTED_ORIGINAL"


def evidence(row, locator="$"):
    return {"artifact_id": row["artifact_id"], "sha256": row["artifact_sha256"], "locator": locator}


def observation(name, facts, rows=(), *, failure=False, limited=False, locator="$"):
    return {
        "id": name,
        "facts": facts,
        "status": "EXCEPTION"
        if failure
        else "LIMITATION"
        if limited
        else "CORROBORATED_SELECTED_ATTRIBUTE",
        "evidence": [evidence(r, locator) for r in rows],
    }


def selected_fields(rows, fields):
    return [
        {
            "artifact_id": r["artifact_id"],
            "native": {k: r["source"][k] for k in CLOCK_ID},
            "attributes": {k: r["document"][k] for k in fields if k in r["document"]},
        }
        for r in rows
        if isinstance(r["document"], dict)
    ]


def missing(name, roles, rows=()):
    return observation(
        name,
        {"required_original_roles": sorted(roles), "state": "SELECTED_ORIGINALS_NOT_COLLECTED"},
        rows,
        limited=True,
    )


def custody_observations(history, rows):
    ids = {r["artifact_id"] for r in rows}
    links = [link for link in history.links if link["from_artifact_id"] in ids]
    return observation(
        "exact-custody-and-effective-source",
        {
            "collected_version_count": len(rows),
            "joins": links,
            "import_clock_is_not_operating_clock": True,
            "missing_or_unavailable_dependencies": [
                link for link in links if link["status"] != "EXACT_COLLECTED_ORIGINAL"
            ],
            "complete_enterprise_population_established": False,
        },
        rows,
        limited=any(link["status"] != "EXACT_COLLECTED_ORIGINAL" for link in links),
    )


def quality(plan, raw, reference, *, at):
    """Reperform typed local transform, exclusions, joins and arithmetic."""
    require(
        isinstance(plan, dict) and isinstance(raw, list) and isinstance(reference, list),
        "Actual quality definition/raw/reference bytes required",
    )
    start, end = (_time(plan["event_window"][k]) for k in ("start", "end"))
    require(start < end <= _time(at), "Quality event window is not closed")
    expected = tokens(plan["expected_record_ids"], "expected record IDs")
    maximum = integer(plan["maximum_units"], "maximum units")
    mapping = {}
    for item in reference:
        require(
            isinstance(item, dict)
            and set(item) == {"entity_id", "category"}
            and all(isinstance(v, str) and v for v in item.values())
            and item["entity_id"] not in mapping,
            "Distinct typed reference entities required",
        )
        mapping[item["entity_id"]] = item["category"]
    require(plan["reference_rows"] == reference, "Collected reference differs from definition")
    candidates, failures, exclusions, accepted, seen = [], [], [], [], set()
    for index, row in enumerate(raw):
        require(isinstance(row, dict), "Structured raw quality row required")
        reasons = []
        if set(row) != {"record_id", "entity_id", "observed_at", "units"}:
            reasons.append("ROW_SCHEMA")
        for field in ("record_id", "entity_id"):
            if not isinstance(row.get(field), str) or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}", row[field]
            ):
                reasons.append("INVALID_" + field.upper())
        try:
            event = _time(row.get("observed_at"))
        except (ValueError, TypeError):
            event = None
            reasons.append("INVALID_EVENT_TIME")
        if not reasons and event is not None and not start <= event < end and event <= _time(at):
            exclusions.append(
                {
                    "index": index,
                    "row_sha256": sha(encoded(row)),
                    "reason": "OUTSIDE_DECLARED_EVENT_WINDOW",
                    "record_id": row["record_id"],
                }
            )
            continue
        if event is not None and event > _time(at):
            reasons.append("FUTURE_EVENT")
        candidates.append((index, row, event, reasons))
    counts = Counter(
        r.get("record_id") for _, r, _, _ in candidates if isinstance(r.get("record_id"), str)
    )
    for index, row, event, reasons in candidates:
        ident, entity = row.get("record_id"), row.get("entity_id")
        if isinstance(ident, str):
            if event is not None and start <= event < end:
                seen.add(ident)
            if ident not in expected:
                reasons.append("UNEXPECTED_IN_WINDOW_RECORD")
            if counts[ident] > 1:
                reasons.append("DUPLICATE_RECORD_ID")
        if not isinstance(entity, str) or entity not in mapping:
            reasons.append("REFERENCE_ENTITY_MISMATCH")
        units = row.get("units")
        if type(units) is not int or not 0 <= units <= maximum:
            reasons.append("INVALID_INTEGER_UNITS")
        if reasons:
            failures.append(
                {"index": index, "row_sha256": sha(encoded(row)), "reasons": sorted(set(reasons))}
            )
        else:
            accepted.append(
                {
                    "record_id": ident,
                    "entity_id": entity,
                    "category": mapping[entity],
                    "units": units,
                    "observed_at": event,
                    "source_index": index,
                    "source_row_sha256": sha(encoded(row)),
                }
            )
    missing_ids = sorted(expected - seen)
    missing_usable = sorted(expected - {r["record_id"] for r in accepted})
    status = (
        "PARTIAL_UNRELIABLE"
        if failures or missing_ids
        else "LOCAL_RULES_PASSED_NOT_SOURCE_ACCEPTANCE"
    )
    report = {
        "status": status,
        "input_rows": len(raw),
        "accepted_rows": len(accepted),
        "failed_rows": len(failures),
        "intentional_exclusions": len(exclusions),
        "expected_in_window_records": len(expected),
        "missing_expected_in_window_ids": missing_ids,
        "missing_usable_expected_ids": missing_usable,
        "failures": failures,
        "exclusions": exclusions,
        "query": {"start": start, "end": end},
        "timezone": "UTC",
        "source_acceptance": "NOT_ESTABLISHED",
    }
    derived = {"status": status, "records": accepted, "query": report["query"]}
    aggregate = {
        "status": status,
        "groups": [
            {
                "category": cat,
                "accepted_rows": sum(r["category"] == cat for r in accepted),
                "accepted_units": sum(r["units"] for r in accepted if r["category"] == cat),
            }
            for cat in sorted(set(mapping.values()))
        ],
        "accepted_rows_only_total": sum(r["units"] for r in accepted),
        "missing_usable_expected_ids": missing_usable,
    }
    require(
        len(raw) == len(accepted) + len(failures) + len(exclusions),
        "Quality row reconciliation differs",
    )
    return report, derived, aggregate


def compare(actual, expected):
    require(isinstance(actual, dict), "Structured recorded report required")
    return {
        k: {"recorded": actual.get(k), "recomputed": v}
        for k, v in expected.items()
        if encoded(actual.get(k)) != encoded(v)
    }


def quality_observations(history):
    observations = []
    for row in history.select("rec003", {"quality_operation"}):
        doc = row["document"]
        if doc.get("request", {}).get("operation") != "TRANSFORM":
            continue
        own = [row]
        inputs = {}
        for key in ("definition_pin", "input_pin", "reference_pin"):
            target, status = history.resolve(doc["observation"][key], at=row["source"]["event_at"])
            inputs[key] = target if status == "EXACT_COLLECTED_ORIGINAL" else None
            if target:
                role = {
                    "definition_pin": "quality_definition",
                    "input_pin": "quality_raw",
                    "reference_pin": "quality_reference",
                }[key]
                require(
                    target["family"] == "rec003" and target["role"] == role,
                    "Actual native quality input role required",
                )
                own.append(target)
        if not all(inputs.values()):
            observations.append(
                observation(
                    "quality-inputs-" + row["artifact_id"],
                    {
                        "operation": doc["request"],
                        "missing_effective_inputs": [k for k, v in inputs.items() if not v],
                    },
                    own,
                    limited=True,
                )
            )
            continue
        plan = inputs["definition_pin"]["document"]["plan"]
        report, derived, aggregate = quality(
            plan,
            inputs["input_pin"]["document"],
            inputs["reference_pin"]["document"],
            at=row["source"]["event_at"],
        )
        differences = {"report": compare(doc["observation"]["report"], report)}
        missing_outputs = []
        for pointer in doc.get("outputs", []):
            target, status = history.resolve(pointer)
            if not target:
                missing_outputs.append(pointer)
                continue
            own.append(target)
            expected = (
                derived
                if target["role"] == "quality_derived"
                else aggregate
                if target["role"] == "quality_aggregate"
                else None
            )
            require(expected is not None, "Exact transform output role required")
            require(
                target["family"] == "rec003"
                and _time(target["source"]["event_at"]) == _time(row["source"]["event_at"]),
                "Actual native transform output scope/occurrence differs",
            )
            differences[target["role"]] = compare(target["document"], expected)
        observations.append(
            observation(
                "quality-transform-" + row["artifact_id"],
                {
                    "input_native": inputs["input_pin"]["source"],
                    "recomputed_report": report,
                    "recomputed_derived": derived,
                    "recomputed_aggregate": aggregate,
                    "recorded_output_differences": differences,
                    "missing_outputs": missing_outputs,
                    "declared_local_plan_only": True,
                    "manager_source_acceptance_established": False,
                    "historical_failed_rows_preserved": bool(
                        report["failed_rows"] or report["missing_usable_expected_ids"]
                    ),
                },
                own,
                failure=any(differences.values())
                or bool(report["failed_rows"] or report["missing_usable_expected_ids"]),
                limited=bool(missing_outputs),
            )
        )
    return observations or [
        missing(
            "quality-transform",
            {"quality_operation", "quality_definition", "quality_raw", "quality_reference"},
        )
    ]


def add_years(value, years):
    day = date.fromisoformat(value)
    return day.replace(
        year=day.year + years, day=min(day.day, calendar.monthrange(day.year + years, day.month)[1])
    )


def retention_observations(history):
    rows = history.select("retention")
    observations = (
        [
            observation(
                "draft-retention-and-held-disposition",
                selected_fields(
                    rows,
                    {
                        "record_class",
                        "retention_trigger",
                        "obligation_mapping",
                        "class_trigger_obligation_accepted",
                        "data_owner_acceptance",
                        "legal_review",
                        "legal_hold_disposition",
                        "legal_hold_release",
                        "attempted_premature_disposition",
                        "attempt_disposition",
                        "unlink_executed",
                        "deletion_verified",
                        "fixture_copy_retained",
                        "fixture_copy_metadata",
                        "selected_source_refs",
                    },
                ),
                rows,
                limited=True,
            )
        ]
        if rows
        else []
    )
    for row in history.select("supplementalops", {"retention_register"}):
        doc, tests, used = row["document"], [], [row]
        entries = doc.get("required_records", [doc] if "created_date" in doc else [])
        for entry in entries:
            if entry.get("class") not in {
                None,
                "SECURITY_POLICY_PROCEDURE",
                "REQUIRED_SECURITY_ACTIVITY",
                "DELEGATED_PRIVACY_DOCUMENTATION",
            }:
                tests.append(
                    {
                        "id": entry.get("id"),
                        "exception": False,
                        "state": "CLASS_OBLIGATION_RULE_NOT_ESTABLISHED",
                        "actual_class": entry.get("class"),
                    }
                )
                continue
            created = date.fromisoformat(entry["created_date"])
            current, hold = entry["current_effective"], entry["hold"]
            require(type(current) is bool and type(hold) is bool, "Typed retention status required")
            last = (
                date.fromisoformat(entry["last_in_effect_date"])
                if entry.get("last_in_effect_date")
                else None
            )
            if current:
                require(last is None, "Current record cannot assert a last-in-effect date")
            require(
                created <= date.fromisoformat(row["source"]["event_at"][:10])
                and (
                    last is None
                    or created <= last <= date.fromisoformat(row["source"]["event_at"][:10])
                ),
                "Retention creation/effective-end chronology differs",
            )
            floor = add_years(max(created, last or created).isoformat(), 6)
            eligible = floor + timedelta(days=1)
            requested = date.fromisoformat(entry["requested_date"])
            deny = current or hold or requested <= floor
            differences = {}
            for field, expected in (
                ("minimum_retain_through", floor.isoformat()),
                ("release_eligible_on", eligible.isoformat()),
            ):
                if field in entry and entry[field] != expected:
                    differences[field] = {"recorded": entry[field], "recomputed": expected}
            actual_delete = entry.get("actual_deletion")
            require(type(actual_delete) is bool, "Strict actual-deletion status required")
            tests.append(
                {
                    "id": entry.get("id", row["source"]["record"]),
                    "created_date": created.isoformat(),
                    "last_in_effect_date": last.isoformat() if last else None,
                    "current_effective": current,
                    "hold": hold,
                    "requested_date": requested.isoformat(),
                    "recomputed_floor": floor.isoformat(),
                    "first_eligible_date": eligible.isoformat(),
                    "recomputed_denial": deny,
                    "recorded_decision": entry.get("decision"),
                    "actual_deletion": actual_delete,
                    "calendar_differences": differences,
                    "exception": bool(differences)
                    or (deny and (actual_delete or entry.get("decision") != "DENY")),
                }
            )
        retrievals = []
        recorded_retrieval = doc.get("superseded_original_retrieval", [])
        if isinstance(recorded_retrieval, dict):
            recorded_retrieval = [recorded_retrieval]
        for item in recorded_retrieval:
            target, status = history.shorthand(
                item["exact_original_ref"], at=row["source"]["event_at"]
            )
            if target:
                used.append(target)
            retrievals.append(
                {
                    "reference": item["exact_original_ref"],
                    "recorded_retrieved": item.get("retrieved"),
                    "actual_collected_status": status,
                    "actual_sha256": target["artifact_sha256"] if target else None,
                }
            )
        observations.append(
            observation(
                "retention-calendar-" + row["artifact_id"],
                {
                    "date_tests": tests,
                    "retrievable_superseded_originals": retrievals,
                    "declared_classes": doc.get("classes"),
                    "scope_exclusions": doc.get("scope_exclusion"),
                    "earlier_pending_legal_hold_not_closed": True,
                    "clinical_record_schedule_established": False,
                    "actual_media_sanitization_reperformed": False,
                },
                used,
                failure=any(t["exception"] for t in tests),
                limited=not tests
                or any(
                    r["actual_collected_status"] != "EXACT_COLLECTED_ORIGINAL" for r in retrievals
                ),
            )
        )
    return observations or [
        missing(
            "retention-and-disposition", {"retention_register", "mapping_draft", "disposition_gate"}
        )
    ]


def dataset_observations(history):
    rows = history.select("dataset")
    result = []
    for row in rows:
        doc = row["document"]
        fields = {
            "dataset_id",
            "source_marker_id",
            "actor_person_id",
            "custodian",
            "accountable_data_owner",
            "actor_authority_limit",
            "classification_recommendation",
            "decision_state",
            "enforcement_status",
            "propagation_status",
            "intake_control_verified",
            "real_contractual_obligations",
            "retention_rule_approved",
            "deletion_rule_approved",
            "legal_hold_disposition",
            "enterprise_dataset_completeness",
            "invalid_public_local_metadata_label",
            "local_label_quarantined",
            "invalid_label_history_open",
            "selected_marker_count",
        }
        invalid = doc.get("invalid_public_local_metadata_label") is True
        result.append(
            observation(
                "classification-" + row["artifact_id"],
                {
                    **{k: doc[k] for k in fields if k in doc},
                    "historical_invalid_local_label": invalid,
                    "quarantine_is_not_owner_acceptance_or_deployed_propagation": True,
                    "source_marker_bytes_collected": any(
                        r["artifact_sha256"] == doc.get("marker_metadata_sha256")
                        for r in history.rows
                    ),
                    "full_storage_sharing_retention_propagation_verified": False,
                },
                [row],
                failure=invalid,
                limited=not invalid,
            )
        )
    return result or [
        missing(
            "dataset-classification",
            {"dataset_inventory", "classification_review", "propagation_request"},
        )
    ]


def purpose_observations(history):
    rows = history.select("processing")
    observations = []
    for row in rows:
        doc = row["document"]
        refused = doc.get("decision") in {"REFUSE", "REFUSED", "REJECT", "REJECTED"}
        executed = (
            doc.get("new_flow_executed") is True or doc.get("payload_copied_or_transferred") is True
        )
        observations.append(
            observation(
                "purpose-" + row["artifact_id"],
                {
                    **{
                        k: doc[k]
                        for k in (
                            "requested_purpose",
                            "requested_recipient",
                            "attempted_request_only",
                            "decision",
                            "contract_purpose_match",
                            "contract_purpose_basis",
                            "reviewed_synthetic_terms_sha256",
                            "data_owner_acceptance",
                            "execution_gate",
                            "downstream_enforcement",
                            "new_flow_executed",
                            "real_world_legal_approval",
                            "case_status",
                            "legal_and_data_owner_review",
                            "payload_copied_or_transferred",
                            "external_request_or_response_sent",
                            "selected_request_count",
                            "refused_count",
                            "pending_count",
                            "approved_execution_count",
                            "actual_transfer_count",
                            "unresolved_authority_count",
                        )
                        if k in doc
                    },
                    "refused_request_is_not_executed_ai_reuse": refused and not executed,
                    "real_authority_accepted": False,
                },
                [row],
                failure=refused and executed,
                limited=True,
            )
        )
    return observations or [
        missing(
            "processing-purpose", {"purpose_request", "purpose_review", "purpose_reconciliation"}
        )
    ]


def rights_observations(history):
    rows = history.select("dat002rights")
    observations = []
    for row in rows:
        doc = row["document"]
        invalid_release = doc.get("copy_sent") is True and (
            doc.get("verified_customer_delegation") is not True
            or doc.get("complete_record_population") is not True
        )
        observations.append(
            observation(
                "rights-assistance-" + row["artifact_id"],
                {
                    **{
                        k: doc[k]
                        for k in (
                            "case_id",
                            "requested_action_scopes",
                            "requester",
                            "simulated_customer",
                            "external_message_received",
                            "verified_customer_delegation",
                            "verified_individual_authority",
                            "customer_instruction_status",
                            "requester_authority_status",
                            "ba_duty_applicability",
                            "release_decision",
                            "copy_sent",
                            "accepted_amendment",
                            "accounting_complete",
                            "designated_record_set_determination",
                            "scope_conclusion",
                            "unreconciled_locations",
                            "complete_record_population",
                            "record_copy_prepared",
                            "premature_no_record_mark",
                            "case_status",
                            "open_action_scopes",
                            "external_response_sent",
                            "shortcut_detected",
                            "subject_exported",
                            "detected_issue",
                            "corrective_owner",
                            "status",
                        )
                        if k in doc
                    },
                    "unverified_held_inquiry_is_not_completed_rights_exercise": True,
                    "electronic_copy_accepted_amendment_and_upstream_accounting_reperformed": False,
                },
                [row],
                failure=invalid_release or doc.get("premature_no_record_mark") is True,
                limited=True,
            )
        )
    return observations or [
        missing(
            "rights-assistance",
            {"rights_intake", "authority_review", "record_scope_review", "rights_queue"},
        )
    ]


def privacy_observations(history, calculation):
    rows = history.select("privacyops")
    if calculation is None:
        return [
            missing("privacy-case-reconciliation", {"privacy_request", "privacy_reconciliation"})
        ]
    failures = bool(
        calculation["recorded_mismatch_case_ids"] or calculation["month_close_discrepancies"]
    )
    return [
        observation(
            "privacy-census-and-delivery-chain",
            calculation,
            rows,
            failure=failures,
            limited=not calculation["selected_population_corroborated"],
        )
    ]


def privacy_documentary_observations(history, roles, name):
    rows = history.select("privacyops", roles)
    return [
        observation(
            name + "-" + row["artifact_id"],
            {
                "actual_native_role": row["role"],
                "actual_document_fields": row["document"],
                "effective_dependency_tests": [
                    link for link in history.links if link["from_artifact_id"] == row["artifact_id"]
                ],
                "executable_configuration_routing_or_channel_enforcement_reperformed": False,
                "source_publication_and_effective_version_are_separate_from_real_import": True,
            },
            [row],
            limited=True,
        )
        for row in rows
    ] or [missing(name, roles)]


def route_screen(row):
    """Selected fictional decision predicates; never a legal applicability opinion."""
    doc, reasons = row["document"], []
    route, facts = doc.get("route"), doc.get("request_facts")
    require(
        isinstance(route, str) and isinstance(facts, dict), "Explicit privacy route/facts required"
    )
    at = _time(row["source"]["event_at"])
    tested = True
    if route.startswith("164.506"):
        for key in (
            "sender_relationship",
            "recipient_relationship",
            "information_relates_to_both_relationships",
        ):
            if facts.get(key) is not True:
                reasons.append("UNESTABLISHED_" + key.upper())
        if facts.get("operation") != "QUALITY_ASSESSMENT":
            reasons.append("UNEXAMINED_OPERATION_CATEGORY")
    elif route == "164.508":
        for key in (
            "authorization_id",
            "authorized_discloser",
            "description",
            "purpose",
            "signature_token",
            "signature_date",
            "named_recipient",
        ):
            if not isinstance(facts.get(key), str) or not facts[key]:
                reasons.append("MISSING_" + key.upper())
        for key in (
            "authority_verified_by_customer",
            "plain_language",
            "right_to_revoke_statement",
            "conditioning_statement",
            "redisclosure_statement",
            "customer_copy_provided",
        ):
            if facts.get(key) is not True:
                reasons.append("UNESTABLISHED_" + key.upper())
        if facts.get("named_recipient") != doc.get("recipient_id"):
            reasons.append("AUTHORIZATION_RECIPIENT_DIFFERS")
        if not facts.get("expiration_at") or _time(facts["expiration_at"]) < at:
            reasons.append("AUTHORIZATION_EXPIRED_OR_UNSPECIFIED")
        if facts.get("revoked_at") is not None and _time(facts["revoked_at"]) <= at:
            reasons.append("AUTHORIZATION_REVOKED_AT_REQUEST")
        if facts.get("signature_date") and date.fromisoformat(
            facts["signature_date"]
        ) > date.fromisoformat(at[:10]):
            reasons.append("SIGNATURE_AFTER_REQUEST")
    elif route.startswith("164.508(a)(2)"):
        if (
            facts.get("separate_notes_authorization") is not True
            or facts.get("combined_with_general_authorization") is True
        ):
            reasons.append("SEPARATE_NOTES_AUTHORITY_NOT_ESTABLISHED")
    elif route.startswith(("164.508(a)(3)", "164.508(a)(4)")):
        if facts.get("remuneration") is True and facts.get("remuneration_statement") is not True:
            reasons.append("REMUNERATION_AUTHORITY_NOT_ESTABLISHED")
    elif route.startswith("164.510"):
        if facts.get("known_preference") == "OBJECTS":
            reasons.append("KNOWN_OBJECTION")
        requested = set(facts.get("requested_scope", []))
        relevant = set(facts.get("relevant_scope", []))
        if not requested <= relevant:
            reasons.append("REQUEST_EXCEEDS_RELEVANT_CARE_SCOPE")
        if facts.get("individual_available") is False and not facts.get("customer_clinical_actor"):
            reasons.append("CUSTOMER_CLINICAL_JUDGMENT_NOT_ESTABLISHED")
    elif route.startswith("164.512"):
        if facts.get("recipient_authority_verified") is not True:
            reasons.append("RECIPIENT_AUTHORITY_NOT_ESTABLISHED")
        kind = facts.get("process_kind")
        if kind == "COURT_ORDER":
            if not set(facts.get("scope_requested", [])) <= set(facts.get("scope_authorized", [])):
                reasons.append("REQUEST_EXCEEDS_ORDER_SCOPE")
        elif kind == "SUBPOENA_WITHOUT_ORDER":
            if not (
                facts.get("notice_assurance_documented") is True
                or facts.get("qualified_protective_order_assurance_documented") is True
            ):
                reasons.append("SUBPOENA_ASSURANCE_NOT_ESTABLISHED")
        else:
            reasons.append("QUALIFIED_LEGAL_DECISION_REQUIRED")
        if facts.get("reproductive_health_content") is True:
            reasons.append("PERIOD_SPECIFIC_LEGAL_OVERLAY_UNRESOLVED")
    elif route.startswith("164.514"):
        method = facts.get("method")
        if method and method.startswith("SAFE_HARBOR"):
            if facts.get("residual_identifier_categories"):
                reasons.append("RESIDUAL_IDENTIFIERS")
            if facts.get("actual_knowledge_of_identifiability") is True:
                reasons.append("ACTUAL_KNOWLEDGE_OF_LINKABILITY")
            if method == "SAFE_HARBOR_CUSTOMER_DETERMINATION":
                removal = facts.get("removal_screen", {})
                if (
                    type(facts.get("identifier_category_screen_count")) is not int
                    or facts["identifier_category_screen_count"] != 18
                    or len(removal) != 18
                ):
                    reasons.append("IDENTIFIER_SCREEN_INCOMPLETE")
                if facts.get("reidentification_mechanism_released") is not False:
                    reasons.append("REIDENTIFICATION_MECHANISM_NOT_WITHHELD")
        elif method == "LIMITED_DATA_SET":
            if (
                facts.get("dua_executed_in_simulation") is not True
                or facts.get("no_reidentification_no_contact_terms") is not True
            ):
                reasons.append("LDS_CUSTOMER_AGREEMENT_NOT_ESTABLISHED")
        elif route.startswith("164.514(d)"):
            if (
                facts.get("entire_record_requested") is True
                and facts.get("entire_record_necessity_justified") is not True
            ):
                reasons.append("ENTIRE_RECORD_MINIMUM_SCOPE_NOT_JUSTIFIED")
        else:
            tested = False
    elif route.startswith("164.522(b)"):
        if (
            facts.get("reasonable_request") is not True
            or facts.get("default_contact_suppressed") is not True
            or facts.get("explanation_demanded") is not False
        ):
            reasons.append("CONFIDENTIAL_CONTACT_INSTRUCTION_NOT_ESTABLISHED")
    elif route.startswith("164.522"):
        if (
            facts.get("solely_paid_in_full_item") is True
            and facts.get("paid_by_individual_not_plan") is True
            and facts.get("health_plan_disclosure") is True
            and facts.get("otherwise_required_by_law") is not True
        ):
            reasons.append("PAID_IN_FULL_RESTRICTION_REMAINS")
        if (
            facts.get("individual_agreed_to_termination") is False
            and facts.get("termination_basis") == "CUSTOMER_UNILATERAL_NOTICE"
        ):
            created, notice = (
                facts.get("token_created_received_at"),
                facts.get("termination_notice_at"),
            )
            if not created or not notice or _time(created) < _time(notice):
                reasons.append("PRENOTICE_RECORD_RESTRICTION_REMAINS")
    else:
        tested = False
    return {
        "case_id": doc.get("case_id"),
        "route": route,
        "actual_request_facts": facts,
        "selected_documentary_predicates_tested": tested,
        "hold_reasons": sorted(set(reasons)),
        "qualified_period_legal_decision_reperformed": False,
    }


def clause_privacy_observations(history, clause):
    suffix = clause.split(":")[-1]
    if suffix in {"164.506", "164.508", "164.510", "164.512", "164.514", "164.522"}:
        requests = [
            r
            for r in history.select("privacyops", {"privacy_request"})
            if r["document"].get("route", "").startswith(suffix)
        ]
        observations = []
        for row in requests:
            result = route_screen(row)
            cid = row["document"].get("case_id")
            related = [
                r
                for r in history.select("privacyops", set(privacy.CASE_SYSTEMS))
                if r["document"].get("case_id") == cid
            ]
            gates = [r for r in related if r["role"] == "privacy_gate_decision"]
            releases = [r for r in related if r["role"] == "privacy_release"]
            result["recorded_gate_decisions"] = [r["document"].get("decision") for r in gates]
            result["recorded_execution_statuses"] = [
                r["document"].get("execution_status") for r in releases
            ]
            result["delivery_despite_selected_hold_predicate"] = bool(
                result["hold_reasons"]
                and any(r["document"].get("execution_status") == "DELIVERED" for r in releases)
            )
            observations.append(
                observation(
                    "route-predicate-" + row["artifact_id"],
                    result,
                    related,
                    failure=result["delivery_despite_selected_hold_predicate"],
                    limited=not result["selected_documentary_predicates_tested"]
                    or not gates
                    or not releases,
                )
            )
        return observations or [
            missing(
                "privacy-route-" + suffix,
                {"privacy_request:" + suffix},
                history.select("privacyops", {"privacy_request", "privacy_reconciliation"}),
            )
        ]
    if suffix == "164.302":
        rows = history.select(
            "privacyops", {"privacy_dataset_inventory", "privacy_lifecycle"}
        ) + history.select("phi_ba", {"operation_scope", "flow_register"})
        requests = history.select("privacyops", {"privacy_request"})
        requested = {r["document"].get("logical_token_id") for r in requests}
        locations = []
        for row in rows:
            doc = row["document"]
            if "seen_logical_token_ids" not in doc:
                continue
            seen = tokens(doc["seen_logical_token_ids"], "location token IDs")
            recorded = integer(doc["logical_token_count"], "location token count")
            locations.append(
                {
                    "artifact_id": row["artifact_id"],
                    "location": doc.get("location"),
                    "recorded_count": recorded,
                    "recomputed_seen_count": len(seen),
                    "requested_tokens_missing_from_location": sorted(requested - seen),
                    "location_asserted_before_period_end": _time(row["source"]["event_at"])
                    < _time(doc["period"]["end"]),
                    "count_discrepancy": recorded != len(seen),
                }
            )
        return (
            [
                observation(
                    "ephi-location-and-activity-boundary",
                    {
                        "selected_locations": locations,
                        "declared_scope_records": selected_fields(
                            rows,
                            {
                                "service_id",
                                "dataset_id",
                                "sim_service_id",
                                "sim_customer_id",
                                "declared_responsibilities",
                                "dataclass",
                                "locations",
                                "location",
                                "fixture_contains_real_phi",
                            },
                        ),
                        "real_ephi_estate_and_subcontractor_population_established": False,
                    },
                    rows,
                    failure=any(r["count_discrepancy"] for r in locations),
                    limited=True,
                )
            ]
            if rows
            else [
                missing("ephi-location-boundary", {"operation_scope", "privacy_dataset_inventory"})
            ]
        )
    if suffix == "164.500":
        rows = history.select(
            "privacyops", {"privacy_legal_review", "privacy_authority", "privacy_contract"}
        )
        return (
            [
                observation(
                    "workflow-role-and-effective-authority",
                    selected_fields(
                        rows,
                        {
                            "role",
                            "reasoning",
                            "direct_ba_duties",
                            "delegated_customer_duties",
                            "not_sable_harbor_functions",
                            "effective_at",
                            "customer_authority_in_simulation",
                            "schedule_executed_in_simulation",
                            "law_basis_checked_as_of",
                            "period_specific_2027_law_not_asserted",
                            "reproductive_health_overlay",
                        },
                    ),
                    rows,
                    limited=True,
                )
            ]
            if rows
            else [missing("workflow-duty-boundary", {"privacy_legal_review"})]
        )
    if suffix == "164.501":
        rows = history.select(
            "privacyops", {"privacy_request", "privacy_dataset_inventory"}
        ) + history.select("dat002rights", {"record_scope_review"})
        return (
            [
                observation(
                    "actual-purpose-and-designated-record-set",
                    selected_fields(
                        rows,
                        {
                            "route",
                            "request_facts",
                            "location",
                            "designated_record_set_determination",
                            "scope_conclusion",
                            "unreconciled_locations",
                            "complete_record_population",
                        },
                    ),
                    rows,
                    limited=True,
                )
            ]
            if rows
            else [missing("purpose-and-record-set", {"privacy_request", "record_scope_review"})]
        )
    raise ValueError("Unknown authored HIPAA clause")


def extraction_observations(history):
    rows, observations = history.select("extraction"), []
    for row in rows:
        doc, own = row["document"], [row]
        if "returned_refs" not in doc:
            continue
        query = doc.get("query")
        require(
            isinstance(query, dict)
            and query.get("timezone") == "UTC"
            and query.get("transformation") == "NONE",
            "Explicit untransformed UTC query required",
        )
        require(
            (query.get("company"), query.get("branch"))
            == (row["source"]["company"], row["source"]["branch"]),
            "Query company/branch authority differs",
        )
        returned, declared, excluded = (
            doc.get(k, []) for k in ("returned_refs", "source_population_refs", "excluded_refs")
        )
        require(
            all(isinstance(v, list) for v in (returned, declared, excluded)),
            "Typed extraction reference populations required",
        )
        maps, missing_dependencies, timing = [], [], []
        for name, pointers in (
            ("returned", returned),
            ("declared", declared),
            ("excluded", excluded),
        ):
            keys = []
            for pointer in pointers:
                target, status = history.resolve(pointer, at=row["source"]["event_at"])
                keys.append(identity(pointer))
                if target:
                    own.append(target)
                if status != "EXACT_COLLECTED_ORIGINAL":
                    missing_dependencies.append(
                        {"population": name, "reference": pointer, "status": status}
                    )
                if target:
                    cutoff = _time(query["as_of"])
                    start, end = (
                        _time(query[k])
                        for k in ("event_window_start", "event_window_end_exclusive")
                    )
                    eligible = (
                        _time(target["source"]["available_at"]) <= cutoff
                        and start <= _time(target["source"]["event_at"]) < end
                    )
                    timing.append(
                        {
                            "population": name,
                            "artifact_id": target["artifact_id"],
                            "query_eligible": eligible,
                        }
                    )
            require(len(keys) == len(set(keys)), "Duplicate extraction native population member")
            maps.append(set(keys))
        returned_set, declared_set, excluded_set = maps
        counts = {
            "returned_count": len(returned_set),
            "excluded_count": len(excluded_set),
            "declared_source_population_count": len(declared_set),
        }
        discrepancies = {
            key: {"recorded": doc[key], "recomputed": value}
            for key, value in counts.items()
            if key in doc and integer(doc[key], key) != value
        }
        recorded_digest = doc.get("returned_refs_sha256")
        require(
            isinstance(recorded_digest, str) and SHA.fullmatch(recorded_digest),
            "Returned native digest required",
        )
        digest_differs = recorded_digest != sha(encoded(returned))
        omitted = sorted(declared_set - returned_set)
        unexpected = sorted(returned_set - declared_set)
        observations.append(
            observation(
                "extraction-" + row["artifact_id"],
                {
                    "query": query,
                    "recomputed_counts": counts,
                    "count_discrepancies": discrepancies,
                    "returned_reference_digest_differs": digest_differs,
                    "omitted_declared_native_members": [list(k) for k in omitted],
                    "unexpected_returned_native_members": [list(k) for k in unexpected],
                    "declared_exclusions_match_omissions": excluded_set == set(omitted),
                    "query_eligibility_tests": timing,
                    "missing_or_ineffective_originals": missing_dependencies,
                    "page_limit": integer(query["page_limit"], "page limit", positive=True),
                    "cursor": query.get("cursor"),
                    "next_cursor": doc.get("next_cursor"),
                    "recorded_truncation": doc.get("export_page_truncated"),
                    "declared_index_is_not_independent_enterprise_denominator": True,
                    "later_correction_does_not_erase_original_omission": True,
                },
                list({r["artifact_id"]: r for r in own}.values()),
                failure=bool(
                    discrepancies
                    or digest_differs
                    or omitted
                    or unexpected
                    or any(not t["query_eligible"] for t in timing)
                ),
                limited=bool(missing_dependencies),
            )
        )
    return observations or [
        missing("extraction-query-and-population", {"extract_attempt", "extract_reconciliation"})
    ]


def integrity_observations(history):
    observations = []
    for row in history.select("integrity", {"transform_report"}):
        doc, own = row["document"], [row]
        copy, status = history.resolve(doc["input_copy_ref"], at=row["source"]["event_at"])
        if copy:
            require(
                copy["family"] == "integrity" and copy["role"] == "test_copy",
                "Actual native integrity-copy role required",
            )
        source_refs = doc.get("source_refs", {})
        inputs = {}
        for name in ("definition", "raw", "reference"):
            target, state = history.resolve(source_refs[name], at=row["source"]["event_at"])
            inputs[name] = target if state == "EXACT_COLLECTED_ORIGINAL" else None
            if target:
                role = {
                    "definition": "quality_definition",
                    "raw": "quality_raw",
                    "reference": "quality_reference",
                }[name]
                require(
                    target["family"] == "common-dq" and target["role"] == role,
                    "Exact approved common quality native role required",
                )
                own.append(target)
        if copy:
            own.append(copy)
        check = None
        check_status = "NO_CHECK_AT_TRANSFORM"
        if isinstance(doc.get("integrity_check_ref"), dict):
            check, check_status = history.resolve(
                doc["integrity_check_ref"], at=row["source"]["event_at"]
            )
            if check:
                require(
                    check["family"] == "integrity" and check["role"] == "integrity_check",
                    "Actual native pre-transform integrity-check role required",
                )
                own.append(check)
        byte_match = (
            (sha(copy["retained_bytes"]) == sha(inputs["raw"]["retained_bytes"]))
            if copy and inputs["raw"]
            else None
        )
        check_tests = {}
        if check:
            checked, checked_status = history.resolve(
                check["document"]["checked_copy_ref"], at=check["source"]["event_at"]
            )
            check_tests = {
                "checked_native_copy_matches": checked is copy,
                "checked_copy_available_at_check": checked_status == "EXACT_COLLECTED_ORIGINAL",
                "expected_baseline_digest_matches": inputs["raw"] is not None
                and check["document"].get("expected_source_raw_sha256")
                == inputs["raw"]["artifact_sha256"],
                "observed_copy_digest_matches": copy is not None
                and check["document"].get("observed_copy_sha256") == copy["artifact_sha256"],
                "recorded_hash_result_matches": byte_match is not None
                and (
                    check["document"].get("result", "").startswith("MATCH")
                    if byte_match
                    else check["document"].get("result") == "MISMATCH_DETECTED"
                ),
            }
        tested, differences = None, {}
        if (
            copy
            and status == "EXACT_COLLECTED_ORIGINAL"
            and inputs["definition"]
            and inputs["reference"]
        ):
            tested, derived, aggregate = quality(
                inputs["definition"]["document"]["plan"],
                copy["document"],
                inputs["reference"]["document"],
                at=row["source"]["event_at"],
            )
            differences["report"] = compare(doc["dq_report"], tested)
            for role, expected in (("derived_report", derived), ("aggregate_report", aggregate)):
                products = [
                    r
                    for r in history.select("integrity", {role})
                    if r["source"]["record"] == row["source"]["record"]
                    and r["source"]["version"] == row["source"]["version"]
                ]
                for product in products:
                    own.append(product)
                    differences[role] = compare(
                        product["document"].get(
                            "dq_derived" if role == "derived_report" else "dq_aggregate"
                        ),
                        expected,
                    )
        precheck = check_status == "EXACT_COLLECTED_ORIGINAL" and all(check_tests.values())
        observations.append(
            observation(
                "integrity-at-transform-" + row["artifact_id"],
                {
                    "input_copy_status": status,
                    "actual_copy_matches_collected_baseline_bytes": byte_match,
                    "integrity_check_status_at_transform": check_status,
                    "effective_pretransform_check_collected": precheck,
                    "actual_pretransform_check_tests": check_tests,
                    "actual_check_claim": check["document"] if check else None,
                    "recomputed_quality_report": tested,
                    "recorded_report_differences": differences,
                    "missing_exact_common_inputs": [k for k, v in inputs.items() if not v],
                    "semantic_quality_is_separate_from_byte_authenticity": True,
                    "subsequent_match_does_not_cure_precheck_absence": True,
                },
                own,
                failure=byte_match is False or not precheck or any(differences.values()),
                limited=byte_match is None or tested is None,
            )
        )
    for row in history.select(
        "integrity",
        {
            "correction_lineage",
            "alteration_plan",
            "integrity_check",
            "copy_quarantine",
            "internal_visibility",
        },
    ):
        doc = row["document"]
        observations.append(
            observation(
                "integrity-lineage-" + row["artifact_id"],
                {
                    **{
                        k: v
                        for k, v in doc.items()
                        if k not in {"schema", "source_previous", "source_refs"}
                    },
                    "recorded_values_are_documentary_without_exact_collected_target_bytes": True,
                },
                [row],
                limited=True,
            )
        )
    for row in history.select("supplementalops", {"integrity_operation", "key_custody"}):
        doc = row["document"]
        expected, received = (
            doc.get("original_sha256", doc.get("original_sha")),
            doc.get("received_sha256", doc.get("received_sha")),
        )
        observations.append(
            observation(
                "copy-authenticity-" + row["artifact_id"],
                {
                    **{
                        k: doc[k]
                        for k in (
                            "authorizer",
                            "operator",
                            "challenger",
                            "test_scope",
                            "response",
                            "root_cause",
                            "handling",
                            "validator",
                            "original_sha256",
                            "received_sha256",
                            "expected_authenticator",
                            "actual_authenticator",
                            "expected_tag",
                            "actual_tag",
                            "semantic_valid",
                            "content_authentic",
                            "executed_scope",
                            "custodian",
                            "custody_controls",
                            "credential_lifecycle",
                            "purpose",
                            "production_use",
                            "private_material_in_receipt",
                        )
                        if k in doc
                    },
                    "recorded_copy_hashes_differ": expected != received
                    if expected and received
                    else None,
                    "actual_copy_bytes_and_authenticator_key_not_retrieved_from_document_paths": (
                        True
                    ),
                    "cryptographic_authentication_and_live_transfer_encryption_reperformed": False,
                    "real_ephi_or_production_key_use_established": False,
                },
                [row],
                failure=doc.get("handling") == "ACCEPT" and doc.get("content_authentic") is False,
                limited=True,
            )
        )
    return observations or [
        missing(
            "integrity-and-correction",
            {"test_copy", "transform_report", "integrity_check", "correction_lineage"},
        )
    ]


def movement_observations(history):
    rows = history.select(
        "supplementalops",
        {"media_movement", "workstation_inventory", "recovery_operation", "facility_maintenance"},
    )
    observations = []
    population = []
    for row in rows:
        if row["role"] == "workstation_inventory":
            population.extend(row["document"].get("assets", row["document"].get("resources", [])))
    for row in rows:
        doc = row["document"]
        if row["role"] != "media_movement":
            continue
        own, tests = [row], {}
        if "departed_at" in doc:
            require(
                _time(doc["departed_at"])
                <= _time(doc["received_at"])
                <= _time(row["source"]["event_at"]),
                "Movement receipt chronology differs",
            )
            candidates = [
                r
                for r in rows
                if r["role"] == "recovery_operation"
                and r["source"]["record"] == doc.get("exact_copy_receipt_id")
            ]
            if candidates:
                copied = candidates[0]
                own.append(copied)
                d = copied["document"]
                tests = {
                    "copy_receipt_available_before_departure": _time(
                        copied["source"]["available_at"]
                    )
                    <= _time(doc["departed_at"]),
                    "recorded_retrieval_before_departure": _time(d["retrieval_at"])
                    < _time(doc["departed_at"]),
                    "recorded_copy_hash_matches": d.get("retrieved_sha256")
                    == d.get("source_sha256"),
                    "exact_working_copy_bytes_collected": any(
                        r["artifact_sha256"] == d.get("retrieved_sha256") for r in history.rows
                    ),
                }
            else:
                tests = {"copy_receipt_original_not_collected": True}
        if "after_size" in doc:
            after_size = integer(doc["after_size"], "reuse after size")
            tests.update(
                {
                    "recorded_zero_size": after_size == 0,
                    "recorded_empty_digest": doc.get("after_sha256") == sha(b""),
                    "recorded_old_marker_absent": doc.get("old_marker_present") is False,
                    "actual_reused_working_file_bytes_collected": any(
                        r["artifact_sha256"] == doc.get("after_sha256") for r in history.rows
                    ),
                }
            )
        if doc.get("copy_receipt") == "MISSING":
            tests.update(
                {
                    "release_denied_when_copy_missing": doc.get("decision") == "DENY_RELEASE"
                    and doc.get("actual_departure") is False
                }
            )
        failure = any(
            v is False
            for k, v in tests.items()
            if k.startswith(
                (
                    "copy_receipt_available",
                    "recorded_retrieval",
                    "recorded_copy_hash",
                    "recorded_zero",
                    "recorded_empty",
                    "recorded_old",
                    "release_denied",
                )
            )
        )
        observations.append(
            observation(
                "media-custody-" + row["artifact_id"],
                {
                    "selected_asset_population_documentary": population,
                    "assets": doc.get("assets", [doc["asset_id"]] if "asset_id" in doc else []),
                    "requester": doc.get("requester"),
                    "approver": doc.get("approver"),
                    "operator": doc.get("operator"),
                    "source_custodian": doc.get("source_custodian"),
                    "destination_custodian": doc.get("destination_custodian"),
                    "source": doc.get("source"),
                    "destination": doc.get("destination"),
                    "status": doc.get("status"),
                    "tests": tests,
                    "all_active_backup_provider_copies_reconciled": False,
                    "working_copy_disposition_is_not_original_or_hardware_sanitization": True,
                },
                own,
                failure=failure,
                limited=True,
            )
        )
    return observations or [
        missing(
            "movement-and-media-disposition",
            {"workstation_inventory", "media_movement", "recovery_operation"},
        )
    ]


def record_observations(history):
    rows = history.select("controlled_record") + history.select("rec003", {"quality_operation"})
    observations = []
    for row in rows:
        doc = row["document"]
        actor = doc.get(
            "actor_person_id", doc.get("request", {}).get("actor_id", doc.get("custodian"))
        )
        observations.append(
            observation(
                "record-origin-and-actions-" + row["artifact_id"],
                {
                    "source_event_at": row["source"]["event_at"],
                    "source_available_at": row["source"]["available_at"],
                    "real_imported_at": row["source"]["imported_at"],
                    "actual_actor_or_custodian": actor,
                    **{
                        k: doc[k]
                        for k in (
                            "action",
                            "selected_record_kind",
                            "selected_record_count",
                            "source_original_locator",
                            "source_integrity_state",
                            "retrieval_uses_authoritative_original",
                            "invalid_alias_marker",
                            "history_version_hash_flag",
                            "classification_authority",
                            "retention_schedule",
                            "deletion_authority",
                            "legal_hold_disposition",
                            "disposition_executed",
                            "technical_enforcement",
                            "command_id",
                            "revision",
                            "request_sha256",
                            "prior_state_sha256",
                            "state_sha256",
                        )
                        if k in doc
                    },
                    "business_command_hash_recomputed": sha(encoded(doc["request"]))
                    if "request" in doc
                    else None,
                    "declared_request_hash_differs": sha(encoded(doc["request"]))
                    != doc.get("request_sha256")
                    if "request" in doc
                    else False,
                    "immutable_native_bytes_do_not_establish_all_operating_actions_recorded": True,
                    "independent_enterprise_event_omission_reconciliation_established": False,
                },
                [row],
                failure="request" in doc
                and sha(encoded(doc["request"])) != doc.get("request_sha256"),
                limited=actor is None,
            )
        )
    return observations or [
        missing(
            "records-actor-input-approval-outcome",
            {"record_registration", "controlled_retrieval", "quality_operation"},
        )
    ]


def activity_observations(history):
    rows = history.select(
        "supplementalops",
        {"procedure_calendar", "procedure_document", "procedure_operation", "period_register"},
    )
    reviews = [r for r in rows if r["role"] == "procedure_operation"]
    observations = []
    for calendar_row in [r for r in rows if r["role"] == "procedure_calendar"]:
        schedule, due_tests = calendar_row["document"].get("scheduled", []), []
        for due in schedule:
            require(
                _time(due["trigger_at"]) <= _time(due["due_at"]),
                "Review trigger/due chronology differs",
            )
            if _time(due["due_at"]) > history.as_of:
                continue
            matches = [r for r in reviews if r["document"].get("trigger_id") == due["trigger_id"]]
            due_tests.append(
                {
                    "trigger_id": due["trigger_id"],
                    "due_at": due["due_at"],
                    "selected_review_artifact_ids": [r["artifact_id"] for r in matches],
                    "missing_due_occurrence": not matches,
                    "declared_due_dates_match": all(
                        _time(r["document"]["due_at"]) == _time(due["due_at"]) for r in matches
                    ),
                    "original_before_due": any(
                        _time(r["source"]["available_at"]) <= _time(due["due_at"]) for r in matches
                    ),
                }
            )
        observations.append(
            observation(
                "activity-due-population-" + calendar_row["artifact_id"],
                {
                    "due_tests": due_tests,
                    "scope_excluded_interval": calendar_row["document"].get(
                        "not_scheduled_interval"
                    ),
                    "program_started": calendar_row["document"].get("program_started"),
                    "one_off_trigger_rule": calendar_row["document"].get("one_off_trigger_rule"),
                    "complete_activity_log_or_prior_candidate_history_not_established": True,
                },
                [calendar_row, *reviews],
                failure=any(
                    t["missing_due_occurrence"]
                    or not t["declared_due_dates_match"]
                    or not t["original_before_due"]
                    for t in due_tests
                ),
            )
        )
    for row in reviews:
        doc, own, retrievals = row["document"], [row], []
        expected_native, reported_native = set(), set()
        for token in doc.get("input_originals", []):
            target, status = history.shorthand(token, at=row["source"]["event_at"])
            if target:
                own.append(target)
                expected_native.add(identity(target["source"]))
            retrievals.append({"reference": token, "status": status})
        own_reports = []
        for item in doc.get("required_original_retrieval", []):
            target, status = history.resolve(item["original"], at=row["source"]["event_at"])
            if target:
                own.append(target)
                reported_native.add(identity(target["source"]))
            own_reports.append(
                {
                    "native": item["original"],
                    "status": status,
                    "reported_sha256": item.get("retrieved_sha256"),
                    "actual_sha256": target["artifact_sha256"] if target else None,
                    "reported_digest_matches": target is not None
                    and item.get("retrieved_sha256") == target["artifact_sha256"],
                }
            )
        late = "due_at" in doc and _time(row["source"]["event_at"]) > _time(doc["due_at"])
        missing_reported = sorted(expected_native - reported_native)
        reported_count_discrepancy = "retrieval_count" in doc and integer(
            doc["retrieval_count"], "retrieval count"
        ) != len(own_reports)
        observations.append(
            observation(
                "activity-review-" + row["artifact_id"],
                {
                    "performer": doc.get("performer"),
                    "due_at": doc.get("due_at"),
                    "late": late,
                    "operator_statement": doc.get("operator_statement"),
                    "factual_result": doc.get("factual_result"),
                    "required_originals": retrievals,
                    "actual_original_retrieval_reports": own_reports,
                    "required_originals_absent_from_recorded_review_retrieval": [
                        list(v) for v in missing_reported
                    ],
                    "recorded_retrieval_count_differs": reported_count_discrepancy,
                    "recorded_review_is_not_complete_activity_log_query": True,
                    "complete_access_security_incident_activity_denominator_established": False,
                },
                list({r["artifact_id"]: r for r in own}.values()),
                failure=late
                or bool(missing_reported)
                or reported_count_discrepancy
                or any(not r["reported_digest_matches"] for r in own_reports),
                limited=any(r["status"] != "EXACT_COLLECTED_ORIGINAL" for r in retrievals),
            )
        )
    return observations or [
        missing(
            "activity-review-period-and-disposition", {"procedure_calendar", "procedure_operation"}
        )
    ]


def regulator_observations(history):
    rows = history.select("supplementalops", {"privacy_responsibility", "communication_event"})
    # A responsibility record or ordinary disclosure is not an exercised urgent regulator request.
    return [
        observation(
            "regulator-authority-preservation-and-urgent-access",
            {
                "selected_responsibility_records": selected_fields(
                    rows,
                    {
                        "responsibility",
                        "responsibilities",
                        "delegated_duties",
                        "authority",
                        "recipient",
                        "purpose",
                        "decision",
                        "response",
                        "preservation",
                    },
                ),
                "actual_selected_regulator_request_originals": [],
                "urgent_retrieval_across_accessible_provider_locations_exercised": False,
                "ordinary_customer_disclosure_is_not_regulator_access_authority": True,
            },
            rows,
            limited=True,
        )
    ]


BASE_FACETS = {
    "SH-DAT-001": ("classification",),
    "SH-DAT-002": ("privacy", "purpose", "rights", "contracts"),
    "SH-DAT-003": ("retention", "disposition"),
    "SH-DAT-004": ("integrity", "quality", "record_origin"),
    "SH-REC-001": ("record_origin", "controlled_records", "activity"),
    "SH-REC-002": ("extraction", "activity"),
    "SH-REC-003": ("quality", "integrity", "record_origin"),
    "SH-REC-004": ("retention", "movement", "controlled_records"),
}
BASE_LIMITS = {
    "SH-DAT-001": (
        "Accountable-owner classification acceptance, contractual restriction "
        "interpretation and deployed storage/sharing/retention propagation across a "
        "reconciled material-dataset inventory."
    ),
    "SH-DAT-002": (
        "Real PHI/BA applicability and period-specific legal decisions; complete "
        "ePHI/designated-record-set populations; application routing, "
        "recipient/network verification and the unresolved September intake tail."
    ),
    "SH-DAT-003": (
        "Owner/legal acceptance of earlier draft classes and holds; service-specific "
        "clinical/contract schedules; deployed expiry/deletion across active, "
        "backup, provider and retained copies."
    ),
    "SH-DAT-004": (
        "Source-owner business accuracy/completeness acceptance, complete dataset "
        "lineage and all production integrity enforcement; independent "
        "authenticator/key/transfer-channel reperformance."
    ),
    "SH-REC-001": (
        "Independent reconciliation of all company actions to the complete event "
        "ledger, effective actor/approval authority and all required operating "
        "outcome/exception records."
    ),
    "SH-REC-002": (
        "Independent full-period accessible-system extraction denominator, all "
        "cursor/pages and excluded activities; complete security/access/incident log "
        "reviews and urgent regulator-request exercise."
    ),
    "SH-REC-003": (
        "Accepted upstream business population, transformation stewardship and "
        "authoritative source completeness/accuracy; production pipeline execution "
        "and downstream reliance census."
    ),
    "SH-REC-004": (
        "Complete disposal/exit due population, owner/legal holds and expiry "
        "decisions; all original/backup/provider-copy destruction and independent "
        "hardware sanitization/reassignment inspection."
    ),
}
ADDITIONAL = {
    ("SH-DAT-001", "CHECK-SOC2:C1.1"): (
        ("classification", "retention", "contracts"),
        (
            "Classification/contract restriction acceptance and deployed lifecycle "
            "protection over the complete actual dataset/copy estate."
        ),
    ),
    ("SH-DAT-002", "ACTION-H-PRIVACY-PURPOSE"): (
        ("privacy", "purpose", "contracts"),
        (
            "Qualified purpose/BA/minimum-necessary decisions and actual proposed "
            "AI-reuse enforcement; no permission inferred from possession or a BAA."
        ),
    ),
    ("SH-DAT-002", "ACTION-H-RIGHTS-ASSISTANCE"): (
        ("rights",),
        (
            "An exercised electronic copy, accepted amendment and accounting request on "
            "complete synthetic designated records, correct recipient and upstream "
            "completion; held unverified inquiries provide none of these completions."
        ),
    ),
    ("SH-DAT-002", "CHECK-SOC2:C1.1"): (
        ("privacy_lifecycle", "contracts", "retention"),
        (
            "Actual dataset/copy inventory and enforced classification, retention, "
            "restricted use and deletion; selected documentary lifecycle records do not "
            "establish full annual coverage."
        ),
    ),
    ("SH-DAT-002", "CHECK-SOC2:CC6.7"): (
        ("privacy", "integrity", "movement"),
        (
            "Live channel/endpoint encryption, protected authenticator/key inspection, "
            "approved destination protection and independent recipient/network transfer "
            "confirmation; documentary token release is not network execution."
        ),
    ),
    ("SH-DAT-003", "ACTION-H-RETENTION"): (
        ("retention",),
        (
            "Qualified obligation-class/trigger and earlier legal-hold acceptance; "
            "deployed retention and actual premature-disposition blocking outside the "
            "selected calendar and documentary originals."
        ),
    ),
    ("SH-DAT-003", "CHECK-SOC2:C1.2"): (
        ("retention", "disposition", "movement"),
        (
            "Expired confidential-data due census and actual authorized destruction "
            "across active/backups/provider/residual copies, including unresolved holds "
            "and contrary retention."
        ),
    ),
    ("SH-DAT-003", "CHECK-SOC2:CC6.5"): (
        ("movement", "disposition"),
        (
            "Complete retirement/reuse hardware population, accepted hold/disposition "
            "authority, independent sanitization verification and actual "
            "reassignment/copy-residual inspection."
        ),
    ),
    ("SH-DAT-004", "ACTION-H-INTEGRITY"): (
        ("integrity", "quality"),
        (
            "Cryptographic copy/transfer challenge using independently retrieved "
            "original bytes and authorized authenticator, production detection/response "
            "and complete downstream reliance; business-valid shape is not authentic "
            "content."
        ),
    ),
    ("SH-REC-002", "ACTION-H-ACTIVITY-REVIEW"): (
        ("activity", "extraction"),
        (
            "Independent due-period security/access/incident activity queries and "
            "complete exception review/disposition; the operating-procedure review "
            "records are only selected documentary inputs."
        ),
    ),
    ("SH-REC-002", "ACTION-H-REGULATOR"): (
        ("regulator", "extraction"),
        (
            "Authorized synthetic regulator request, preservation and exercised urgent "
            "retrieval across accessible provider systems; ordinary customer-disclosure "
            "constraints cannot substitute for regulator-access authority."
        ),
    ),
    ("SH-REC-002", "CHECK-SOC2:CC2.1"): (
        ("extraction", "quality", "record_origin"),
        (
            "Accepted information-quality requirements and independent "
            "report-origin/exclusion completeness against the real business population, "
            "beyond count/hash agreement."
        ),
    ),
    ("SH-REC-003", "CHECK-SOC2:CC2.1"): (
        ("quality", "integrity", "record_origin"),
        (
            "Source-owner acceptance of complete/accurate business inputs and report "
            "requirements, production transformation versions and downstream "
            "quality/reliance assessment."
        ),
    ),
    ("SH-REC-004", "ACTION-H-PHYSICAL-MOVEMENT"): (
        ("movement",),
        (
            "Complete independently reconciled workstation/facility movement population "
            "and actual exact-readable pre-move working-copy retrieval; fixture paths "
            "and documentary hashes are not collected copy bytes."
        ),
    ),
    ("SH-REC-004", "ACTION-H-RETENTION"): (
        ("retention", "controlled_records"),
        (
            "Accepted security/privacy documentation applicability, earlier held "
            "originals and complete retrievable superseded-document coverage beyond the "
            "selected six-year date tests."
        ),
    ),
    ("SH-REC-004", "CHECK-SOC2:C1.2"): (
        ("retention", "movement", "disposition"),
        (
            "Complete expiration/exit population and actual destruction or justified "
            "retained residual copies across active/backups/providers with accepted "
            "holds."
        ),
    ),
    ("SH-REC-004", "CHECK-SOC2:CC6.5"): (
        ("movement", "controlled_records", "disposition"),
        (
            "Independent sanitization/destruction and reassignment over all retired "
            "assets/copies; local empty-file receipt arithmetic is not hardware "
            "sanitization."
        ),
    ),
}
HIPAA_LIMITS = {
    "164.302": (
        "Complete actual created/received/maintained/transmitted ePHI systems, "
        "backups and subcontractor scope before safeguard selection; location "
        "snapshots do not cure the later September intake tail."
    ),
    "164.500": (
        "Qualified workflow-specific direct BA/delegated covered-entity/inapplicable "
        "duty decisions for the simulated period and actual legal status; dated "
        "fictional counsel reasoning is not a real applicability opinion."
    ),
    "164.501": (
        "Accepted actual designated-record-set and individual-decision purpose "
        "determination, complete payment/operations/research inventory and "
        "applicable legal definitions over each workflow."
    ),
    "164.506": (
        "Qualified cross-entity operations category and relationship/BAA decisions "
        "plus executable scope enforcement; ordinary consent is not a required "
        "authorization or broad cross-entity permission."
    ),
    "164.508": (
        "Qualified authorization validity and all "
        "expiry/revocation/reliance/conditioning exceptions, "
        "psychotherapy/marketing/sale categories and actual enforcement; selected "
        "fields are fictional documentary predicates only."
    ),
    "164.510": (
        "Qualified customer clinical judgment, prior preferences and "
        "direct-relevance decisions plus actual scoped family access; asserted "
        "relationship alone is insufficient."
    ),
    "164.512": (
        "Qualified demand-specific legal scope/recipient/assurance decisions and "
        "period-specific reproductive-health status; no current/future-law "
        "conclusion from printed clause or ordinary request."
    ),
    "164.514": (
        "Qualified de-identification/actual-knowledge and "
        "reidentification/LDS/minimum-necessary determinations plus independent "
        "transformed-content/recipient enforcement; metadata screens are not expert "
        "or legal acceptance."
    ),
    "164.522": (
        "Qualified restriction/confidential-contact decisions, valid termination "
        "timing and paid-in-full exceptions plus actual filter/contact enforcement "
        "over the complete population."
    ),
}
FACET_DESCRIPTIONS = {
    "privacy_design": (
        "dated authority/customer-instruction/contract/legal-review/dataset design "
        "fields and exact scope dependencies"
    ),
    "privacy_implementation": (
        "every collected configuration/change-approval/monitoring version, publication "
        "timing and exact effective dependencies without executable-enforcement credit"
    ),
    "classification": (
        "dataset/steward/classification intake, label history, quarantine and propagation fields"
    ),
    "privacy": (
        "once-calculated selected request/customer/gate/release/receipt census, "
        "native chronology, mismatch and premature-close tail"
    ),
    "purpose": (
        "requested reuse, actual synthetic contract purpose match, refusal/queue and "
        "no-execution fields"
    ),
    "rights": (
        "requester/customer authority, record scope, copy/amendment/accounting holds "
        "and premature no-record exception"
    ),
    "contracts": (
        "fictional dated BA/customer/subcontractor contracts, authority, flow scope "
        "and execution boundaries"
    ),
    "privacy_lifecycle": (
        "distinct privacy dataset/location/contract/lifecycle restrictions and "
        "effective version histories"
    ),
    "retention": (
        "class/hold/disposition histories, creation versus last-in-effect calendar "
        "floors and exact superseded-original retrieval"
    ),
    "disposition": (
        "recorded expiry/hold/disposition authority, blocked unlink and "
        "copy-residual documentary limits"
    ),
    "integrity": (
        "actual collected copy/base hashes, effective pre-transform checks, "
        "altered/corrected lineage and documentary authenticator failure"
    ),
    "quality": (
        "typed raw/reference/definition joins, exclusions, duplicate/invalid/missing "
        "rows, transform/aggregate arithmetic and historical partial outputs"
    ),
    "record_origin": (
        "actual actor/input/request digest, event/publication/import clocks and "
        "original action/outcome linkage"
    ),
    "controlled_records": (
        "authoritative retrieval versus local aliases, classification/hold/disposal "
        "fields and retained original scope"
    ),
    "extraction": (
        "UTC query/window/native population membership, omitted/excluded rows, "
        "counts, reference digests and accessible-original limits"
    ),
    "activity": (
        "due review timing and source-original retrieval/digest checks while "
        "separating review statements from full activity-log queries"
    ),
    "regulator": (
        "actual collected responsibility scope and explicit missing "
        "regulator-request/preservation/urgent-retrieval exercise"
    ),
}


def authored_contracts():
    raw = CONTRACT_PATH.read_bytes()
    require(sha(raw) == CONTRACT_SHA256, "Exact authored B05 contract pin differs")
    data = _json(raw)
    require(
        data.get("schema") == "SH_COLLECTED_B05_METHOD_CONTRACTS_V1"
        and len(data["selected_task_ids"]) == 50
        and data["selected_task_ids"] == sorted(set(data["selected_task_ids"]))
        and set(data["selected_task_ids"]) == set(data["tasks"]),
        "Exact selected 50 task vector required",
    )
    return data


def contract(task):
    control, kind, clause = task["control_id"], task["kind"], task["clause_group"]
    if kind == "ADDITIONAL_DUTY":
        if clause.startswith("CHECK-HIPAA:"):
            facets, unperformed = (
                ("hipaa:" + clause.split(":")[-1],),
                HIPAA_LIMITS[clause.split(":")[-1]],
            )
        else:
            facets, unperformed = ADDITIONAL[(control, clause)]
    else:
        facets, unperformed = BASE_FACETS[control], BASE_LIMITS[control]
        if control == "SH-DAT-002":
            facets = {
                "TOD": ("privacy_design", "contracts", "purpose", "rights"),
                "IMPLEMENTATION": ("privacy_implementation", "privacy", "purpose", "rights"),
                "TOE": ("privacy", "privacy_implementation", "purpose", "rights"),
            }[kind]
        unperformed += {
            "TOD": (
                " Full authored effective-design/authority and failure-path sufficiency "
                "review remains open."
            ),
            "IMPLEMENTATION": (
                " Independent full authored implementation walk and deployed enforcement "
                "outside these selected originals remain open."
            ),
            "TOE": (
                " Independent accepted full-period due/triggered population and every "
                "authored operating attribute remain open."
            ),
        }[kind]
    descriptions = [
        FACET_DESCRIPTIONS.get(
            f, "distinct " + f + " selected request predicates and recorded gate/release decisions"
        )
        for f in facets
    ]
    performed = (
        control
        + " "
        + clause
        + ": examine "
        + "; ".join(descriptions)
        + (
            ". Reparse ordinary retained bytes, resolve exact native sources at each "
            "operation and preserve historical exceptions. "
        )
        + {
            "TOD": (
                "Inspect declared design, decision authority and source-defined conditions "
                "without treating approval as enforcement."
            ),
            "IMPLEMENTATION": (
                "Trace selected dated action/input/outcome histories and recompute the "
                "available local implementation attributes."
            ),
            "TOE": (
                "Examine all actually collected selected occurrences, retain "
                "missing-period/population attributes and separate later corrections."
            ),
            "ADDITIONAL_DUTY": (
                "Perform these clause-specific selected attributes in addition to reused "
                "base facts; mapped control existence grants no credit."
            ),
        }[kind]
    )
    return {
        "performed": performed,
        "unperformed": unperformed,
        "allowed_dispositions": [
            {"status": "IN_PROGRESS", "conclusion": c} for c in ("LIMITATION", "FAIL")
        ],
        "facets": list(facets),
    }


def task_contracts():
    authored = authored_contracts()
    return {
        tid: {k: v for k, v in contract(authored["tasks"][tid]).items() if k != "facets"}
        for tid in authored["selected_task_ids"]
    }


def bounded_observations(observations):
    """Preserve complete calculations/custody within the reviewed 20-citation limit."""
    out = []
    for original in observations:
        evidence = original["evidence"]
        if len(evidence) <= 20:
            out.append(original)
            continue
        parts = [evidence[start : start + 20] for start in range(0, len(evidence), 20)]
        continuation_ids = [
            "CUSTODY-" + sha(original["id"].encode()) + f"-{number}"
            for number in range(2, len(parts) + 1)
        ]
        out.append(
            {
                **original,
                "evidence": parts[0],
                "facts": {
                    **(
                        original["facts"]
                        if isinstance(original["facts"], dict)
                        else {"selected_record_facts": original["facts"]}
                    ),
                    "continued_evidence_observation_ids": continuation_ids,
                    "complete_citation_count": len(evidence),
                    "custody_part": 1,
                    "custody_part_count": len(parts),
                },
            }
        )
        for number, part in enumerate(parts[1:], 2):
            out.append(
                {
                    "id": "CUSTODY-" + sha(original["id"].encode()) + f"-{number}",
                    "status": original["status"],
                    "evidence": part,
                    "facts": {
                        "supports_complete_calculation_observation_id": original["id"],
                        "custody_part": number,
                        "custody_part_count": len(parts),
                        "complete_citation_count": len(evidence),
                    },
                }
            )
    return out


def inspections(rows, *, as_of, scratch_root):
    """Full reviewed selected vector; no storage/database/Key/recipe access."""
    del scratch_root  # No working-copy paths or company document paths are followed.
    require(
        sha(Path(privacy.__file__).read_bytes()) == PRIVACY_SHA256,
        "Accepted pure privacy method pin differs",
    )
    authored, history = authored_contracts(), History(rows, as_of)
    privacy_rows = history.select("privacyops")
    calculation = (
        privacy.examine(privacy_rows, as_of=as_of)
        if any(r["role"] == "privacy_reconciliation" for r in privacy_rows)
        else None
    )
    contract_rows = history.select("phi_ba") + history.select(
        "privacyops", {"privacy_contract", "privacy_authority", "privacy_legal_review"}
    )
    lifecycle_rows = history.select(
        "privacyops", {"privacy_dataset_inventory", "privacy_lifecycle", "privacy_contract"}
    )
    controlled = history.select("controlled_record")
    disposition_rows = history.select(
        "retention", {"disposition_gate", "premature_attempt", "hold_review_marker"}
    ) + history.select("controlled_record", {"disposition_screen"})
    facets = {
        "privacy_design": privacy_documentary_observations(
            history,
            {
                "privacy_authority",
                "privacy_contract",
                "privacy_customer_instruction",
                "privacy_legal_review",
                "privacy_dataset_inventory",
            },
            "privacy-design",
        ),
        "privacy_implementation": privacy_documentary_observations(
            history,
            {"privacy_configuration", "privacy_change_approval", "privacy_monitoring"},
            "privacy-implementation",
        ),
        "classification": dataset_observations(history),
        "purpose": purpose_observations(history),
        "rights": rights_observations(history),
        "privacy": privacy_observations(history, calculation),
        "retention": retention_observations(history),
        "quality": quality_observations(history),
        "integrity": integrity_observations(history),
        "extraction": extraction_observations(history),
        "movement": movement_observations(history),
        "record_origin": record_observations(history),
        "activity": activity_observations(history),
        "regulator": regulator_observations(history),
        "contracts": [
            observation(
                "synthetic-effective-contract-and-flow-scope",
                selected_fields(
                    contract_rows,
                    {
                        "sim_service_id",
                        "sim_customer_id",
                        "sim_subcontractor_id",
                        "contracting_entity_id",
                        "service_id",
                        "dataset_id",
                        "declared_responsibilities",
                        "synthetic_terms",
                        "effective_at",
                        "contract_executed_in_simulation",
                        "simulated_signer",
                        "signature_status",
                        "decision",
                        "actual_ba_or_legal_status",
                        "actual_hipaa_applicability",
                        "scope",
                        "reasoning",
                    },
                ),
                contract_rows,
                limited=True,
            )
        ]
        if contract_rows
        else [
            missing(
                "synthetic-contracts", {"operation_scope", "contract_register", "legal_decision"}
            )
        ],
        "privacy_lifecycle": [
            observation(
                "privacy-dataset-and-lifecycle",
                selected_fields(
                    lifecycle_rows,
                    {
                        "service_id",
                        "dataset_id",
                        "location",
                        "locations",
                        "logical_token_count",
                        "permitted_operations",
                        "effective_at",
                        "delete_before_retention_expiry",
                        "independent_analytics_or_ai_reuse",
                        "retention",
                        "retention_rule",
                        "count_excludes_prior_marker_dataset",
                        "period",
                    },
                ),
                lifecycle_rows,
                limited=True,
            )
        ]
        if lifecycle_rows
        else [missing("privacy-lifecycle", {"privacy_dataset_inventory", "privacy_lifecycle"})],
        "controlled_records": [
            observation(
                "controlled-original-versus-alias",
                selected_fields(
                    controlled,
                    {
                        "selected_record_kind",
                        "source_original_locator",
                        "retrieval_uses_authoritative_original",
                        "invalid_alias_marker",
                        "source_integrity_state",
                        "classification_authority",
                        "retention_schedule",
                        "deletion_authority",
                        "legal_hold_disposition",
                        "disposition_executed",
                        "technical_enforcement",
                    },
                ),
                controlled,
                limited=True,
            )
        ]
        if controlled
        else [
            missing(
                "controlled-original-retrieval", {"controlled_retrieval", "record_registration"}
            )
        ],
        "disposition": [
            observation(
                "hold-and-disposal-authority",
                selected_fields(
                    disposition_rows,
                    {
                        "legal_hold_disposition",
                        "legal_hold_release",
                        "attempted_premature_disposition",
                        "attempt_disposition",
                        "unlink_executed",
                        "deletion_verified",
                        "fixture_copy_retained",
                        "fixture_copy_metadata",
                        "disposition_executed",
                        "deletion_authority",
                    },
                ),
                disposition_rows,
                limited=True,
            )
        ]
        if disposition_rows
        else [missing("hold-disposal", {"disposition_gate", "disposition_screen"})],
    }
    for suffix in HIPAA_LIMITS:
        facets["hipaa:" + suffix] = clause_privacy_observations(history, "CHECK-HIPAA:" + suffix)
    by_id, outputs = {r["artifact_id"]: r for r in history.rows}, []
    for tid in authored["selected_task_ids"]:
        task, specification = authored["tasks"][tid], contract(authored["tasks"][tid])
        selected = [
            {**o, "id": f"{number + 1}-{o['id']}"}
            for number, o in enumerate(o for f in specification["facets"] for o in facets[f])
        ]
        ids = sorted({e["artifact_id"] for o in selected for e in o["evidence"]})
        inputs = [by_id[i] for i in ids]
        selected.append(custody_observations(history, inputs))
        exception_ids = [o["id"] for o in selected if o["status"] == "EXCEPTION"]
        # Operational failures stay visible in TOD facts without inferring design failure.
        if task["kind"] == "TOD":
            selected = [
                {
                    **o,
                    "status": "LIMITATION",
                    "facts": {"observed_operational_exception": True, "details": o["facts"]},
                }
                if o["status"] == "EXCEPTION"
                else o
                for o in selected
            ]
            exception_ids = []
        conclusion = "FAIL" if exception_ids else "LIMITATION"
        selected = [
            {
                **o,
                "status": "EXCEPTION_RECORDED"
                if o["status"] == "EXCEPTION"
                else "SUPPORT_UNAVAILABLE"
                if isinstance(o["facts"], dict)
                and o["facts"].get("state") == "SELECTED_ORIGINALS_NOT_COLLECTED"
                else "OBSERVED",
            }
            for o in selected
        ]
        outputs.append(
            {
                "task_id": tid,
                "artifact_ids": ids,
                "observations": bounded_observations(selected),
                "performed": specification["performed"],
                "unperformed": specification["unperformed"],
                "result": {
                    "control_id": task["control_id"],
                    "kind": task["kind"],
                    "clause_group": task["clause_group"],
                    "authored_instruction": task["authored_instruction"],
                    "authored_procedure": task["authored_procedure"],
                    "selected_facets": specification["facets"],
                    "examined_as_of": history.as_of,
                    "population": {
                        "basis": (
                            "All actually collected selected native originals "
                            "for this task's facets"
                        ),
                        "native_version_count": len(ids),
                        "artifact_ids": ids,
                        "full_period_enterprise_denominator_established": False,
                    },
                    "sample": {
                        "basis": (
                            "Census of the collected selected originals; no invented random or "
                            "complete-population sample"
                        ),
                        "artifact_ids": ids,
                    },
                    "source_specific_exception_observation_ids": exception_ids,
                    "professional_pass_or_full_authored_task_completion_asserted": False,
                },
                "disposition": {
                    "status": "IN_PROGRESS",
                    "conclusion": conclusion,
                    "rationale": (
                        "Selected retained originals show the recorded exceptions: "
                        + ", ".join(exception_ids)
                        + ". "
                        if exception_ids
                        else "Selected attributes and unavailable originals remain bounded. "
                    )
                    + specification["unperformed"],
                },
            }
        )
    return outputs
