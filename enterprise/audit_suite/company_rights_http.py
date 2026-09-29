"""Bounded HTTP disclosure adapter for explicitly classified company records.

This adapter does not infer per-record rights from CompanyStore system grants.
It serves only the complete, exact source population registered in the trusted
producer. Legacy audit-training collection remains a separate authority path.
"""

from __future__ import annotations

import hashlib

from .company_rights_producer import CompanyRightsProducer, RightsUnavailable, _text

MAX_RECORDS = 512
MAX_TOTAL_BYTES = 25 * 1024 * 1024


class CompanyRightsHTTP:
    def __init__(self, producer: CompanyRightsProducer):
        if not isinstance(producer, CompanyRightsProducer):
            raise ValueError("Trusted company-rights producer required")
        self.producer = producer

    def _snapshot(self, token: str, engagement_id: str):
        snap = self.producer.snapshot(session_token=token, engagement_id=engagement_id)
        checkpoint = self.producer.checkpoint()
        if snap["revocation_epoch"] != checkpoint["epoch"]:
            raise RightsUnavailable("Company rights changed")
        return snap

    def _complete_population(self, token: str, engagement_id: str):
        snap = self._snapshot(token, engagement_id)
        records = snap["records"]
        if len(records) > MAX_RECORDS:
            raise RightsUnavailable("Company record population exceeds boundary")
        candidates, identities, size = [], {}, 0
        for record_id, row in sorted(records.items()):
            path = row["repository_path"]
            try:
                content = self.producer.source_bytes(path)
            except Exception as exc:
                raise RightsUnavailable("Exact company source unavailable") from exc
            if not isinstance(content, bytes):
                raise RightsUnavailable("Exact company source unavailable")
            digest = hashlib.sha256(content).hexdigest()
            if digest != row["source_sha256"]:
                raise RightsUnavailable("Exact company source changed")
            size += len(content)
            if size > MAX_TOTAL_BYTES:
                raise RightsUnavailable("Company record population exceeds boundary")
            key = (path, digest)
            if key in identities:
                raise RightsUnavailable("Ambiguous company source identity")
            identities[key] = record_id
            candidates.append({"path": path, "content": content})
        return snap, candidates, identities

    def _recheck(self, token: str, engagement_id: str, original: dict):
        latest = self._snapshot(token, engagement_id)
        if (
            latest["rights_revision"] != original["rights_revision"]
            or latest["revocation_epoch"] != original["revocation_epoch"]
        ):
            raise RightsUnavailable("Company rights changed")

    def direct(self, *, token: str, engagement_id: str, record_id: str, action: str) -> bytes:
        record_id = _text(record_id)
        snap = self._snapshot(token, engagement_id)
        row = snap["records"].get(record_id)
        if row is None:
            raise RightsUnavailable("Company record unavailable")
        try:
            content = self.producer.source_bytes(row["repository_path"])
        except Exception as exc:
            raise RightsUnavailable("Company record unavailable") from exc
        if not isinstance(content, bytes) or len(content) > MAX_TOTAL_BYTES:
            raise RightsUnavailable("Company record unavailable")
        authorized = self.producer.authorize_disclosure(
            session_token=token,
            engagement_id=engagement_id,
            path=row["repository_path"],
            content=content,
            action=action,
        )
        if authorized != record_id:
            raise RightsUnavailable("Company record changed")
        self._recheck(token, engagement_id, snap)
        return content

    def visible(self, *, token: str, engagement_id: str, action: str, query: str):
        if not isinstance(query, str) or len(query) > 160:
            raise RightsUnavailable("Bounded search query required")
        snap, candidates, identities = self._complete_population(token, engagement_id)
        allowed = self.producer.visible_population(
            session_token=token,
            engagement_id=engagement_id,
            candidates=candidates,
            action=action,
            complete=True,
        )
        query = query.casefold()
        result = []
        for item in allowed:
            if query in item["content"].decode("utf-8", errors="replace").casefold():
                key = (item["path"], hashlib.sha256(item["content"]).hexdigest())
                result.append(identities[key])
        self._recheck(token, engagement_id, snap)
        return sorted(result)
