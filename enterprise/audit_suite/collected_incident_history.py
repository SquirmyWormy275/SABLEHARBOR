"""Strict byte custody and dated native pointers for pure B09 examinations."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from .company_store import _json, _time
from .fresh_sec003_procedure import CLOCK_ID, NATIVE_ID, require
from .source_library_audit import BUSINESS_REFERENCE

FAMILIES = {
    "assurance",
    "baseline-logging",
    "incident-history",
    "logging-history",
    "phi_ba",
    "prdconcern",
    "supplementalops",
}
LONG_ID = {
    "company_id": "company",
    "branch_id": "branch",
    "system_id": "system",
    "record_id": "record",
}


def key(source):
    return tuple(source[k] for k in NATIVE_ID)


def custody(row):
    return {k: row["source"][k] for k in BUSINESS_REFERENCE}


def detail(row):
    value = row["document"].get("detail", row["document"])
    require(isinstance(value, dict), "Typed incident detail object required")
    return value


def pointers(value, path="$"):
    if isinstance(value, dict):
        if set(NATIVE_ID) <= value.keys() or set(LONG_ID) | {"version"} <= value.keys():
            yield path, value
        else:
            for name, child in value.items():
                yield from pointers(child, path + "." + name)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from pointers(child, f"{path}[{i}]")


def pointer_header(ref):
    return {LONG_ID.get(k, k): v for k, v in ref.items()}


def expected_role(row, path):
    field = path.rsplit(".", 1)[-1]
    if row["logical_family"] == "incident-history":
        targets = {
            "inventory": "inventory",
            "ticket": "incident_ticket",
            "monitoring": "monitoring",
            "escalation": "escalation",
            "recovery": "recovery",
            "corrective_action": "corrective_action",
            "dispatch_replay": "dispatch_replay",
            "action_validation": "action_validation",
        }
        return {"incident-history." + targets[field]} if field in targets else None
    return None


class History:
    """Caller separately proves Engine membership; no company database is read."""

    def __init__(self, records, *, as_of):
        self.as_of = _time(as_of)
        self.rows, self.index, self.joins, self.action_chronology = [], {}, [], []
        now = _time(datetime.now(UTC).isoformat())
        for record in records:
            source, receipt, raw = record["source"], record["receipt"], record["retained_bytes"]
            require(
                set(CLOCK_ID) <= source.keys()
                and type(source["version"]) is int
                and source["version"] > 0
                and all(isinstance(source[k], str) and source[k] for k in NATIVE_ID[:-1])
                and isinstance(record["artifact_id"], str)
                and record["artifact_id"]
                and isinstance(raw, bytes)
                and raw
                and _json(source) == _json(receipt["source"])
                and type(receipt["content_bytes"]) is int
                and receipt["content_bytes"] == len(raw)
                and all(
                    isinstance(receipt.get(k), str) and receipt[k]
                    for k in ("engagement_id", "principal_id", "command_id")
                )
                and _time(source["event_at"])
                <= _time(source["available_at"])
                <= _time(receipt["simulated_as_of"])
                <= self.as_of
                and _time(source["imported_at"]) <= _time(receipt["collected_at"]) <= now
                and hashlib.sha256(raw).hexdigest() == source["sha256"] == record["artifact_sha256"]
                and record["content_type"]
                == source["provenance"].get("content_type")
                == "application/json",
                "Actual incident custody, version, bytes or receipt clocks differ",
            )
            family, role = record["logical_family"], record["logical_system"]
            require(
                family in FAMILIES and source["system"] == family + "." + role,
                "Incident role differs from actual native physical system",
            )
            document = json.loads(raw)
            require(isinstance(document, dict), "Structured native incident original required")
            require(
                all(
                    k not in document or _time(document[k]) == _time(source[k])
                    for k in ("event_at", "available_at")
                ),
                "Incident document clock differs from native custody",
            )
            row = {**record, "content": raw, "document": document}
            require(
                key(source) not in self.index,
                "Distinct actual native incident versions required",
            )
            self.index[key(source)] = row
            self.rows.append(row)
            for name in (
                "recorded_at",
                "approved_at",
                "released_at",
                "applied_at",
                "observed_at",
                "performed_at",
                "occurred_at",
            ):
                body = detail(row)
                if name in body:
                    supported = (
                        isinstance(body[name], str)
                        and bool(body[name])
                        and _time(body[name]) <= _time(source["event_at"])
                    )
                    self.action_chronology.append(
                        {
                            "source": custody(row),
                            "body_field": name,
                            "body_timestamp": body[name],
                            "supported_by_native_occurrence": supported,
                        }
                    )
        require(
            self.rows and len({r["artifact_id"] for r in self.rows}) == len(self.rows),
            "Distinct actually collected incident artifacts required",
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
            "One collected company branch, engagement and principal required",
        )
        for row in self.rows:
            for path, ref in pointers(row["document"]):
                target, status = self.resolve(row, ref, expected=expected_role(row, path))
                self.joins.append(
                    {
                        "origin": custody(row),
                        "path": path,
                        "declared_reference": ref,
                        "status": status,
                        "target": custody(target) if target else None,
                    }
                )
            metadata = row["source"]["provenance"].get("operational_metadata", {})
            for path, ref in pointers(metadata, "$.provenance.operational_metadata"):
                target, status = self.resolve(row, ref)
                self.joins.append(
                    {
                        "origin": custody(row),
                        "path": path,
                        "declared_reference": ref,
                        "status": status,
                        "target": custody(target) if target else None,
                    }
                )

    def action_supported(self, row):
        return row is not None and not any(
            key(c["source"]) == key(row["source"]) and not c["supported_by_native_occurrence"]
            for c in self.action_chronology
        )

    def select(self, family, roles=None):
        return [
            r
            for r in self.rows
            if r["logical_family"] == family and (roles is None or r["logical_system"] in roles)
        ]

    def resolve(self, origin, raw_ref, *, expected=None, at=None):
        ref = pointer_header(raw_ref)
        require(
            type(ref.get("version")) is int and ref["version"] > 0,
            "Strict positive native incident reference version required",
        )
        if str(ref.get("status", "")).startswith("RESTRICTED"):
            return None, "RESTRICTED_REFERENCE_NOT_REBASED"
        if (ref["company"], ref["branch"]) != (
            origin["source"]["company"],
            origin["source"]["branch"],
        ):
            return None, "OUTSIDE_ACTUAL_COLLECTED_BRANCH"
        if not set(BUSINESS_REFERENCE) <= ref.keys():
            return None, "INCOMPLETE_ORIGINAL_REFERENCE_NO_ALIAS_FALLBACK"
        target = self.index.get(key(ref))
        if target is None:
            return None, "ORIGINAL_NOT_COLLECTED"
        fields = (
            (*BUSINESS_REFERENCE, "imported_at") if "imported_at" in ref else BUSINESS_REFERENCE
        )
        require(
            all(_json(ref[k]) == _json(target["source"][k]) for k in fields),
            "Native incident reference digest or original clocks differ",
        )
        if expected is not None and target["source"]["system"] not in expected:
            return None, "ACTUAL_NATIVE_ROLE_DIFFERS"
        cutoff = origin["source"]["event_at"] if at is None else at
        if _time(target["source"]["available_at"]) > _time(cutoff):
            return None, "ORIGINAL_UNAVAILABLE_AT_COMPANY_OCCURRENCE"
        if not self.action_supported(origin) or not self.action_supported(target):
            return None, "RECORDED_ACTION_UNSUPPORTED_AT_NATIVE_OCCURRENCE"
        return target, "EXACT_AVAILABLE_ORIGINAL"

    def supported_rows(self, value, fallback=()):
        keys = {key(pointer_header(ref)) for _, ref in pointers(value)}
        return [r for r in self.rows if key(r["source"]) in keys] or list(fallback)

    def ancestors(self, origin):
        if not self.action_supported(origin):
            return []
        found, pending = {}, [origin]
        while pending:
            row = pending.pop()
            for join in self.joins:
                if key(join["origin"]) != key(row["source"]) or join["target"] is None:
                    continue
                identity = key(join["target"])
                if identity not in found and identity != key(origin["source"]):
                    found[identity] = self.index[identity]
                    pending.append(found[identity])
        return list(found.values())

    def scalar(self, origin, *, record, family, roles, sha256=None):
        """Explicit record/digest witness; never a name or equal-digest alias."""
        if not isinstance(record, str) or not record:
            return None, "TYPED_SCALAR_RECORD_ABSENT"
        if sha256 is not None and (
            not isinstance(sha256, str)
            or len(sha256) != 64
            or any(c not in "0123456789abcdef" for c in sha256)
        ):
            return None, "TYPED_SCALAR_DIGEST_UNAVAILABLE"
        candidates = [
            r
            for r in self.select(family, roles)
            if r["source"]["record"] == record
            and (sha256 is None or r["source"]["sha256"] == sha256)
        ]
        if len(candidates) != 1:
            return None, "EXACT_TYPED_SCALAR_ORIGINAL_ABSENT_OR_AMBIGUOUS"
        target = candidates[0]
        if _time(target["source"]["available_at"]) > _time(origin["source"]["event_at"]):
            return None, "ORIGINAL_UNAVAILABLE_AT_COMPANY_OCCURRENCE"
        if not self.action_supported(origin) or not self.action_supported(target):
            return None, "RECORDED_ACTION_UNSUPPORTED_AT_NATIVE_OCCURRENCE"
        return target, "EXACT_AVAILABLE_SCALAR_WITNESS_NO_NATIVE_VERSION_POINTER"
