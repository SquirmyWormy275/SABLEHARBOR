"""Exercise public edition originals through a pinned existing portal CompanyStore.

Loads only the committed company_store module, never live private databases or server state.
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import sqlite3
import subprocess
import sys
import tarfile
from datetime import timedelta
from itertools import zip_longest
from pathlib import Path

from .edition import EditionError, encoded, sha, timestamp, verify
from .transport import MAX_BYTES, prepare, verify_original


def review_plan(destination, contract, originals, records, review_paths=None):
    """Select one smallest original per component, preserving the full population declaration."""
    lookup = {(system, record): digest for system, record, _available, digest in records}
    selected = []
    if review_paths is not None:
        known = {row[1] for row in originals}
        if (
            not review_paths
            or len(set(review_paths)) != len(review_paths)
            or not set(review_paths) <= known
        ):
            raise EditionError("Review paths must identify distinct existing edition originals")
    for component in contract["components"]:
        candidates = [row for row in originals if row[0] == component["id"]]
        if not candidates:
            raise EditionError("Selected review component has no original population")
        if review_paths is not None:
            choices = [r for r in candidates if r[1] in review_paths]
        else:
            choices = [min(candidates, key=lambda r: (r[4] == 0, r[4], r[1]))]
        for system, path, available, digest, size, parts in choices:
            selected.append(
                dict(
                    system=system,
                    path=path,
                    available_at=available,
                    sha256=digest,
                    bytes=size,
                    parts=[{**part, "sha256": lookup[system, part["record"]]} for part in parts],
                )
            )
    plan = dict(
        destination=str(destination.resolve()),
        edition_id=contract["edition_id"],
        components=[c["id"] for c in contract["components"]],
        selected=selected,
        available_at=max((r[2] for r in originals), key=timestamp),
        selection_rule=(
            "Explicit operator-selected paths; bounded API exercise, not audit sampling"
            if review_paths is not None
            else (
                "One minimum-byte nonempty original per component where available; "
                "ties lexical path; bounded API exercise, not audit sampling"
            )
        ),
        surrounding_population=[
            dict(
                component=c["id"],
                members=len(c["members"]),
                population_definition=c["population_definition"],
                fact_status=c["fact_status"],
            )
            for c in contract["components"]
        ],
    )
    return plan


def selected_review(portal, commit, destination, contract, originals, records, review_paths=None):
    plan = review_plan(destination, contract, originals, records, review_paths)
    snapshot = destination / "pinned-portal-code"
    snapshot.mkdir()
    archive = subprocess.check_output(["git", "-C", str(portal), "archive", commit])
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        source.extractall(snapshot, filter="data")
    plan_path = destination / "SELECTED_REVIEW_PLAN.json"
    plan_path.write_bytes(encoded(plan))
    output = destination / "SELECTED_REVIEW_RECEIPT.json"
    worker = Path(__file__).with_name("portal_engagement.py").resolve()
    command = [sys.executable, str(worker), str(plan_path.resolve()), str(output.resolve())]
    completed = subprocess.run(
        command,
        cwd=snapshot,
        env={**os.environ, "PYTHONPATH": str(snapshot.resolve())},
        capture_output=True,
        text=True,
    )
    (destination / "SELECTED_REVIEW.log").write_text(completed.stdout + completed.stderr)
    if completed.returncode:
        raise EditionError("Selected portal engagement failed; inspect SELECTED_REVIEW.log")
    result = json.loads(output.read_bytes())
    result.update(
        portal_commit=commit,
        adapter_sha256=sha(worker.read_bytes()),
        pinned_portal_archive_sha256=sha(archive),
        command=command,
    )
    output.write_bytes(encoded(result))
    return result


def exercise(
    edition: Path,
    portal: Path,
    revision: str,
    destination: Path,
    *,
    review=False,
    review_paths=None,
) -> dict:
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
    if review:
        result["selected_engagement_review"] = selected_review(
            portal, commit, destination, contract, originals, records, review_paths
        )
        result["limits"][1] = (
            "Synthetic software-role engagement only; no audit opinion, "
            "instructor key or grading material"
        )
    (destination / "RECEIPT.json").write_bytes(encoded(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition", type=Path, required=True)
    parser.add_argument("--portal", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--review-engagement", action="store_true")
    parser.add_argument(
        "--review-member",
        action="append",
        help="Exact edition member path; repeat for an explicit selection",
    )
    args = parser.parse_args()
    if args.review_member and not args.review_engagement:
        parser.error("--review-member requires --review-engagement")
    print(
        json.dumps(
            exercise(
                args.edition,
                args.portal,
                args.revision,
                args.output,
                review=args.review_engagement,
                review_paths=args.review_member,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
