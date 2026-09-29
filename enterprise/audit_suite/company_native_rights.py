"""Exact native-source identity closure for the opt-in company rights boundary.

The audit portal's system grant is only a prerequisite for reading a native
version. It never supplies a company record entitlement. This adapter accepts
only reviewed native-version-to-policy-record mappings with identical bytes.
Unmapped native versions and changed manifests fail closed.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .company_rights_producer import CompanyRightsProducer, RightsUnavailable, _path, _sha, _text

_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_FIELDS = frozenset(
    {
        "company",
        "branch",
        "system",
        "record",
        "version",
        "sha256",
        "policy_record_id",
        "repository_path",
    }
)


class NativeRecordClosure:
    """A pinned, immutable mapping from native versions to policy source IDs."""

    def __init__(
        self,
        *,
        producer: CompanyRightsProducer,
        manifest_file: Path,
        manifest_sha256: str,
    ):
        if not isinstance(producer, CompanyRightsProducer):
            raise RightsUnavailable("Trusted company-rights producer required")
        self.producer = producer
        self.manifest_file = Path(manifest_file).absolute()
        self.manifest_sha256 = _sha(manifest_sha256)
        manifest = self._read_manifest()
        if (
            not isinstance(manifest, dict)
            or set(manifest) != {"version", "source_commit", "policy_sha256", "records"}
            or manifest["version"] != 1
            or not isinstance(manifest["source_commit"], str)
            or not _COMMIT.fullmatch(manifest["source_commit"])
            or manifest["source_commit"] != producer.source_commit
            or manifest["policy_sha256"] != producer.policy_sha256
            or not isinstance(manifest["records"], list)
            or not manifest["records"]
            or len(manifest["records"]) > 512
        ):
            raise RightsUnavailable("Reviewed native source closure required")
        mapping = {}
        for entry in manifest["records"]:
            if not isinstance(entry, dict) or set(entry) != _FIELDS:
                raise RightsUnavailable("Exact native source mapping required")
            key = tuple(_text(entry[field]) for field in ("company", "branch", "system", "record"))
            version = entry["version"]
            if type(version) is not int or version < 1:
                raise RightsUnavailable("Positive native source version required")
            native_sha = _sha(entry["sha256"])
            policy_id = _text(entry["policy_record_id"])
            path = _path(entry["repository_path"])
            identity = (*key, version, native_sha)
            if identity in mapping:
                raise RightsUnavailable("Duplicate native source identity")
            mapping[identity] = (policy_id, path)
        self.mapping = mapping

    def _read_manifest(self) -> dict:
        path = self.manifest_file
        if path.is_symlink() or not path.is_file():
            raise RightsUnavailable("Reviewed native source manifest unavailable")
        data = path.read_bytes()
        if len(data) > 1024 * 1024:
            raise RightsUnavailable("Reviewed native source manifest exceeds limit")
        if hashlib.sha256(data).hexdigest() != self.manifest_sha256:
            raise RightsUnavailable("Reviewed native source manifest changed")
        try:
            return json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RightsUnavailable("Reviewed native source manifest invalid") from exc

    def authorize_version(
        self,
        *,
        session_token: str,
        engagement_id: str,
        native: dict,
        action: str,
    ) -> str:
        """Recheck the native tuple, exact bytes and current record decision."""
        self._read_manifest()  # A changed reviewed input invalidates a running service.
        if not isinstance(native, dict) or not isinstance(native.get("content"), bytes):
            raise RightsUnavailable("Exact native source version required")
        try:
            identity = (
                *(_text(native[field]) for field in ("company", "branch", "system", "record")),
                native["version"],
                _sha(native["sha256"]),
            )
        except (KeyError, TypeError) as exc:
            raise RightsUnavailable("Exact native source identity required") from exc
        if type(identity[4]) is not int or identity[4] < 1:
            raise RightsUnavailable("Exact native source version required")
        expected = self.mapping.get(identity)
        if expected is None or hashlib.sha256(native["content"]).hexdigest() != identity[5]:
            raise RightsUnavailable("Native source has no reviewed policy closure")
        record_id, path = expected
        snapshot = self.producer.snapshot(
            session_token=session_token, engagement_id=engagement_id
        )
        policy_row = snapshot["records"].get(record_id)
        if (
            policy_row is None
            or policy_row.get("repository_path") != path
            or policy_row.get("source_sha256") != identity[5]
        ):
            raise RightsUnavailable("Native policy source changed")
        if (
            self.producer.authorize_disclosure(
                session_token=session_token,
                engagement_id=engagement_id,
                path=path,
                content=native["content"],
                action=action,
            )
            != record_id
        ):
            raise RightsUnavailable("Native policy identity changed")
        self._read_manifest()
        return record_id
