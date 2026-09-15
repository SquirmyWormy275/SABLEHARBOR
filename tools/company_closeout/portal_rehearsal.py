"""Exercise public edition originals through a pinned existing portal CompanyStore.

Loads only the committed company_store module, never live private databases or server state.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sqlite3
import subprocess
from datetime import timedelta
from itertools import zip_longest
from pathlib import Path

from .edition import EditionError, encoded, sha, timestamp, verify
from .transport import MAX_BYTES, prepare, verify_original


def exercise(edition: Path, portal: Path, revision: str, destination: Path) -> dict:
    verified = verify(edition)
    module_path = "enterprise/audit_suite/company_store.py"
    source = subprocess.check_output(
        ["git", "-C", str(portal), "show", f"{revision}:{module_path}"]
    )
    commit = subprocess.check_output(
        ["git", "-C", str(portal), "rev-parse", f"{revision}^{{commit}}"], text=True
    ).strip()
    if destination.exists():
        raise EditionError("New isolated rehearsal destination required")
    destination.mkdir(parents=True, mode=0o700)
    module_file = destination / "pinned_company_store.py"
    module_file.write_bytes(source)
    spec = importlib.util.spec_from_file_location("closeout_pinned_company_store", module_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    store_root = destination / "company"
    store_root.mkdir(mode=0o700)
    store = module.CompanyStore(store_root)
    contract = json.loads((edition / "CONTRACT.json").read_bytes())
    records = []
    originals = []
    for component in contract["components"]:
        system = component["id"]
        store.register_system("SH", contract["edition_id"], system, "SH-COMPANY-RECORDS-CUSTODIAN")
        for member in component["members"]:
            content = (edition / "content" / member["path"]).read_bytes()
            parts = prepare(member["path"], content)
            originals.append(
                (
                    system,
                    member["path"],
                    component["available_at"],
                    member["sha256"],
                    len(content),
                    [{"record": p["record"], "kind": p["kind"]} for p in parts],
                )
            )
            for part in parts:
                metadata = store.append_version(
                    "SH",
                    contract["edition_id"],
                    system,
                    part["record"],
                    expected_version=0,
                    command_id="IMPORT-" + sha((system + part["record"]).encode())[:40],
                    event_at=None,
                    available_at=component["available_at"],
                    content=part["content"],
                    origin="REPOSITORY_SYNTHETIC_DOCUMENT",
                    provenance={
                        "source_reference": member["path"],
                        "source_sha256": member["sha256"],
                        "source_bytes": len(content),
                        "transport_kind": part["kind"],
                        "edition_id": contract["edition_id"],
                        "component_fact_status": component["fact_status"],
                        "population_definition": component["population_definition"],
                        "qualification": (
                            "Public repository byte transport; not a native business event "
                            "or independent bank/regulator confirmation"
                        ),
                    },
                )
                digest = sha(part["content"])
                if metadata["sha256"] != digest:
                    raise EditionError("Transport content changed on import")
                records.append((system, part["record"], component["available_at"], digest))
    checks = {
        "originals": len(originals),
        "transport_records": len(records),
        "originals_reassembled": 0,
        "future_denials": 0,
        "ungranted_denials": 0,
        "revoked_denials": 0,
        "restored_revoked_denials": 0,
    }
    actor, engagement = "SH-REHEARSAL-AUDITOR", "SH-CLOSEOUT-IMPORT-REHEARSAL"
    for system, record, available, digest in records:

        def read(as_of, system=system, record=record):
            return store.read_version(
                actor,
                engagement,
                "SH",
                contract["edition_id"],
                system,
                record,
                version=1,
                as_of=as_of,
            )

        # Each system is revoked after its prior member, so the next member starts denied.
        try:
            read(available)
        except module.CompanyStoreError:
            checks["ungranted_denials"] += 1
        else:
            raise EditionError("Ungrant/revoked source unexpectedly readable")
        store.grant(actor, engagement, "SH", contract["edition_id"], system)
        before = (timestamp(available) - timedelta(microseconds=1)).isoformat()
        try:
            read(before)
        except module.CompanyStoreError:
            checks["future_denials"] += 1
        else:
            raise EditionError("Future source became available early")
        if sha(read(available)["content"]) != digest:
            raise EditionError("Read original content mismatch")
        store.grant(actor, engagement, "SH", contract["edition_id"], system, active=False)
        try:
            read(available)
        except module.CompanyStoreError:
            checks["revoked_denials"] += 1
        else:
            raise EditionError("Revoked source unexpectedly readable")
    # Readback reconstructs each logical original; transport parts are not extra company records.
    for system, path, available, digest, size, parts in originals:
        store.grant(actor, engagement, "SH", contract["edition_id"], system)

        def read_original(record, system=system, available=available):
            return store.read_version(
                actor,
                engagement,
                "SH",
                contract["edition_id"],
                system,
                record,
                version=1,
                as_of=available,
            )["content"]

        verify_original(path, digest, size, parts, read_original)
        checks["originals_reassembled"] += 1
        store.grant(actor, engagement, "SH", contract["edition_id"], system, active=False)
    # Actual SQLite backup/restore of this isolated source runtime, including revocations.
    restored_root = destination / "restored"
    restored_root.mkdir(mode=0o700)
    restored_path = restored_root / "company.sqlite3"
    with sqlite3.connect(store.path) as current, sqlite3.connect(restored_path) as backup:
        current.backup(backup)
    restored_path.chmod(0o600)
    restored = module.CompanyStore(restored_root)
    for system, record, available, _digest in records:
        try:
            restored.read_version(
                actor,
                engagement,
                "SH",
                contract["edition_id"],
                system,
                record,
                version=1,
                as_of=available,
            )
        except module.CompanyStoreError:
            checks["restored_revoked_denials"] += 1
        else:
            raise EditionError("Restore resurrected revoked access")

    # Compare every original byte and history row without materializing both
    # complete enterprise BLOB populations in memory.
    with sqlite3.connect(store.path) as original_db, sqlite3.connect(restored.path) as restored_db:
        missing = object()
        for table in ["systems", "versions", "grants", "access_events", "collections"]:
            original_rows = original_db.execute(f"SELECT * FROM {table} ORDER BY rowid")
            restored_rows = restored_db.execute(f"SELECT * FROM {table} ORDER BY rowid")
            for original_row, restored_row in zip_longest(
                original_rows, restored_rows, fillvalue=missing
            ):
                if original_row != restored_row:
                    raise EditionError("Restore changed history/content")
    result = {
        "schema_version": "1.0.0",
        "result": "PASS",
        "edition_verification": verified,
        "portal_commit": commit,
        "portal_module_path": module_path,
        "portal_module_sha256": sha(source),
        "checks": checks,
        "backup_history_equality": True,
        "transport_contract": "SH-EXACT-BYTE-PARTS-1",
        "existing_store_max_record_bytes": MAX_BYTES,
        "scope": (
            "Actual isolated CompanyStore import/read/revocation/SQLite restore "
            "of public repository originals"
        ),
        "limits": [
            "No live portal or private company source was modified",
            "No engagement, audit opinion, instructor key or grading material was created",
            "Document import is not a complete company year or external confirmation",
            "Multipart and empty originals require the explicit transport reconstruction adapter",
            "Immutable CompanyStore lacks class-based deletion/hold; that gate remains open",
            "HTTP indirect-disclosure and model inference evaluations remain separate",
        ],
    }
    (destination / "RECEIPT.json").write_bytes(encoded(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition", type=Path, required=True)
    parser.add_argument("--portal", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(exercise(args.edition, args.portal, args.revision, args.output), indent=2))


if __name__ == "__main__":
    main()
