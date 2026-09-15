"""Actual isolated disk backup/restore of public reference fixtures, not a portal backup."""

import copy
import hashlib
import json
import tempfile
from pathlib import Path

from enterprise.runtime.security import authorize, restore, revoke_graph


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def run():
    now = "2026-09-15T12:00:00+00:00"
    principal = {"id": "SYN-RESTORE-READER", "tenant": "SHI", "purpose": "review"}
    template = {
        "tenant": "SHI",
        "classification": "OPEN",
        "rights": "INTERNAL_REUSE",
        "purposes": ["review"],
        "payload": "Public synthetic restore fixture",
    }
    records = {
        "source": dict(template),
        "derived": dict(template, sources=["source"]),
        "held": dict(template, sources=["source"], legal_hold=True),
        "ordinary": dict(template),
    }
    history = [
        {"sequence": 1, "action": "CREATE", "ids": list(records)},
        {"sequence": 2, "action": "REVIEW", "ids": ["ordinary"]},
    ]
    before = {"records": copy.deepcopy(records), "history": history}
    with tempfile.TemporaryDirectory(prefix="sh-reference-restore-") as raw:
        root = Path(raw)
        source = root / "source.json"
        backup = root / "backup.json"
        source.write_bytes(encoded(before))
        backup.write_bytes(source.read_bytes())
        digest = hashlib.sha256(backup.read_bytes()).hexdigest()
        affected = revoke_graph(records, "source")
        # Authority changes after the backup must be replayed from a separate current log.
        authority = {
            "revoked_principals": [principal["id"]],
            "suppressed_records": sorted(affected),
        }
        (root / "authority.json").write_bytes(encoded(authority))
        restored_dir = root / "isolated-restored"
        restored_dir.mkdir()
        snapshot = json.loads(backup.read_bytes())
        if hashlib.sha256(encoded(snapshot)).hexdigest() != digest:
            raise ValueError("Backup bytes did not survive restore")
        current = json.loads((root / "authority.json").read_bytes())
        live = restore(snapshot["records"], set(current["suppressed_records"]))
        restored_principal = dict(
            principal, revoked=principal["id"] in current["revoked_principals"]
        )
        if authorize(live["ordinary"], restored_principal, "read", now) != "DENY":
            raise ValueError("Restore resurrected revoked principal")
        if any(key in live for key in affected):
            raise ValueError("Restore resurrected suppressed content")
        # Held bytes survive in a restricted archive; they are not ordinary restored records.
        archive = {key: row for key, row in records.items() if row.get("legal_hold")}
        for row in archive.values():
            if "payload" not in row or authorize(row, principal, "read", now) != "DENY":
                raise ValueError("Hold bytes lost or became disclosable")
        restored = {
            "records": live,
            "history": snapshot["history"],
            "protected_hold_archive": archive,
        }
        (restored_dir / "store.json").write_bytes(encoded(restored))
        reopened = json.loads((restored_dir / "store.json").read_bytes())
        if reopened["history"] != history:
            raise ValueError("History changed across disk restore")
        if (
            authorize(reopened["records"]["ordinary"], dict(principal, id="SYN-VALID"), "read", now)
            != "ALLOW"
        ):
            raise ValueError("Legitimate retained access lost")
        return {
            "scope": "ACTUAL_LOCAL_SOFTWARE_REFERENCE_FIXTURE_REHEARSAL",
            "backup_sha256": digest,
            "history_sha256": hashlib.sha256(encoded(history)).hexdigest(),
            "source_records": len(records),
            "retained_live_records": len(live),
            "suppressed_records": len(affected),
            "held_records": len(archive),
            "history_entries": len(history),
            "revoked_principal_denied": True,
            "held_disclosure_denied": True,
            "valid_access_retained": True,
            "isolated_disk_restore": "PASS",
            "portal_or_production_restore": "NOT_ASSERTED",
        }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
