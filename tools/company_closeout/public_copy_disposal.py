"""Exercise pinned portal disposal on new copies of three public release members.

Never deletes release originals or CompanyStore source records. Logical 2027 fixture
operation dates do not backdate actual implementation/observation availability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

PIN = "5344bf76413ffe2cd378b957dbb5f7d56d04ea19"
MEMBERS = {
    "CAPITAL": "enterprise/closeout/source/capital_register.json",
    "EQUITY": "enterprise/generated/company-closeout-v1/capital_opening_equity_bridge.csv",
    "PAYROLL_BACKUP": "enterprise/generated/completed-period-2026-08/payroll_source_bridges.csv",
}
AT = "2027-05-01T00:00:00Z"
LATER = "2027-05-01T00:01:00Z"
RETRY = "2027-05-01T00:02:00Z"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def read_release(package, expected_sha256):
    require(file_digest(package) == expected_sha256, "Release package digest mismatch")
    with zipfile.ZipFile(package) as archive:
        manifest_raw = archive.read("MANIFEST.json")
        manifest = json.loads(manifest_raw)
        contract = archive.read("CONTRACT.json")
        require(digest(contract) == manifest["contract_sha256"], "Contract mismatch")
        require(manifest["status"] == "ACCEPTED_SCOPED_EDITION", "Expected accepted edition")
        indexed = {r["path"]: r for r in manifest["members"]}
        require(len(indexed) == len(manifest["members"]), "Duplicate manifest members")
        payloads = {}
        for ident, member in MEMBERS.items():
            data = archive.read("content/" + member)
            require(0 < len(data) <= 65536, "Selected original exceeds runtime byte bound")
            require(
                len(data) == indexed[member]["bytes"] and digest(data) == indexed[member]["sha256"],
                "Selected member mismatch",
            )
            payloads[ident] = data
    return manifest_raw, manifest, payloads


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portal", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--package-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    portal = args.portal.resolve(strict=True)

    def git(*args):
        return subprocess.check_output(["git", "-C", str(portal), *args], text=True).strip()

    require(git("rev-parse", "HEAD") == PIN, "Wrong portal revision")
    require(not git("status", "--porcelain", "--untracked-files=no"), "Dirty tracked portal source")
    manifest_raw, manifest, payloads = read_release(args.package, args.package_sha256)
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    sys.path.insert(0, str(portal))
    from enterprise.audit_suite import company_disposal_runtime as runtime
    from enterprise.audit_suite.company_backup_runtime import database, pin
    from enterprise.audit_suite.company_operating_period import create_period
    from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
    from enterprise.audit_suite.organization import snapshot

    require(
        Path(runtime.__file__).resolve().is_relative_to(portal), "Portal import provenance mismatch"
    )
    owner = next(
        a["primary_person_id"]
        for a in snapshot(portal, as_of="2027-05-01")["control_assignments"]
        if a["control_id"] == "SH-REC-004"
    )
    declaration = args.output / "declaration"
    declaration.mkdir(mode=0o700)
    ids = list(MEMBERS)
    create_period(
        CompanyStore(declaration),
        repository=portal,
        plan={
            "period_id": "PUBLIC-EDITION-COPIES",
            "company_id": "SH",
            "branch_id": "local-public-copy-disposal",
            "owner_id": owner,
            "control_ids": ["SH-REC-004"],
            "declared_at": "2027-04-30T00:00:00Z",
            "period_start": AT,
            "period_end_exclusive": "2027-05-02T00:00:00Z",
            "inventory": [
                {
                    "id": i,
                    "description": "New disposable copy of public synthetic edition member "
                    + MEMBERS[i],
                }
                for i in ids
            ],
            "local_basis": (
                "Selected public synthetic fixture copies only; "
                "no corporate retention or legal hold release"
            ),
            "schedule": [
                {
                    "id": "CHECK",
                    "inventory_ids": ids,
                    "control_id": "SH-REC-004",
                    "depends_on": [],
                    "window_start": AT,
                    "window_end_exclusive": "2027-05-02T00:00:00Z",
                    "due_at": "2027-05-01T02:00:00Z",
                }
            ],
        },
    )
    with database(declaration) as db:
        reference = pin(db.execute("SELECT * FROM versions").fetchone())
    root = args.output / "runtime"
    initialized = runtime.initialize(
        root,
        repository=portal,
        declaration_root=declaration,
        declaration_pin=reference,
        copies=[
            {
                "id": i,
                "kind": "BACKUP" if i == "PAYROLL_BACKUP" else "ACTIVE",
                "content": data,
                "not_before": LATER if i == "EQUITY" else AT,
                "holds": [],
            }
            for i, data in payloads.items()
        ],
        as_of=AT,
    )
    runtime_hash = initialized["runtime_sha256"]

    def view(at=AT):
        return runtime.inspect(root, expected_runtime_sha256=runtime_hash, as_of=at)

    def base(command, at=AT):
        return dict(
            expected_runtime_sha256=runtime_hash,
            expected_revision=view(at)["revision"],
            operator_id=owner,
            command_id=command,
            event_at=at,
        )

    def hold(active, command, at=AT):
        return runtime.control(
            root,
            **base(command, at),
            action="HOLD",
            payload={
                "copy_id": "CAPITAL",
                "hold_id": "LOCAL-ONLY",
                "active": active,
                "rationale": "Local disposable-copy constraint, not legal release",
            },
        )

    def deny(action, expected):
        try:
            action()
        except CompanyStoreError as error:
            require(expected in str(error).lower(), "Unexpected denial: " + str(error))
            return {"status": "DENIED", "reason": str(error)}
        raise ValueError("Expected denial was absent")

    runtime.control(
        root,
        **base("authorize"),
        action="AUTHORIZE",
        payload={
            "authorization_id": "LOCAL-AUTH",
            "copy_ids": ids,
            "expires_at": "2027-05-01T01:00:00Z",
            "rationale": "Voluntary local fixture exercise only",
        },
    )
    hold(True, "hold")
    checks = {}
    checks["held_copy"] = deny(
        lambda: runtime.dispose(
            root, **base("denied-held"), authorization_id="LOCAL-AUTH", copy_ids=["CAPITAL"]
        ),
        "hold",
    )
    hold(False, "unhold")
    checks["retained_copy"] = deny(
        lambda: runtime.dispose(
            root, **base("denied-retained"), authorization_id="LOCAL-AUTH", copy_ids=["EQUITY"]
        ),
        "retention",
    )
    # Fault injection changes no source file; it interrupts after durable intent and before unlink.
    with patch.object(
        runtime,
        "_continue",
        side_effect=KeyboardInterrupt("Explicit fixture interruption after intent"),
    ):
        try:
            runtime.dispose(
                root, **base("interrupted"), authorization_id="LOCAL-AUTH", copy_ids=["CAPITAL"]
            )
        except KeyboardInterrupt:
            pass
    pending = view()
    require(pending["pending"] is not None, "Durable intent missing")
    require(
        all(row["path_present"] for row in pending["inventory"]), "Unexpected pre-retry deletion"
    )
    hold(True, "hold-pending")

    def retry(at):
        state = view(at)
        return runtime.retry_pending(
            root,
            expected_runtime_sha256=runtime_hash,
            expected_revision=state["revision"],
            intent_sha256=state["pending"]["intent_sha256"],
            operator_id=owner,
            retry_at=at,
        )

    checks["hold_after_interruption"] = deny(lambda: retry(LATER), "hold")
    hold(False, "unhold-pending", LATER)
    checks["explicit_retry"] = retry(RETRY)
    checks["after_retention"] = runtime.dispose(
        root, **base("permitted-equity", RETRY), authorization_id="LOCAL-AUTH", copy_ids=["EQUITY"]
    )
    final = view(RETRY)
    states = {row["id"]: row for row in final["inventory"]}
    require(
        not states["CAPITAL"]["path_present"] and not states["EQUITY"]["path_present"],
        "Expected owned copies not unlinked",
    )
    require(states["PAYROLL_BACKUP"]["path_present"], "Unselected backup was removed")
    require(file_digest(args.package) == args.package_sha256, "Original release changed")
    receipt = {
        "status": "PASS",
        "observed_at": datetime.now(UTC).isoformat(),
        "portal_commit": PIN,
        "adapter_sha256": file_digest(Path(__file__)),
        "runtime_source_sha256": file_digest(Path(runtime.__file__)),
        "package_sha256": args.package_sha256,
        "manifest_sha256": digest(manifest_raw),
        "edition_source_commit": manifest["source_commit"],
        "edition_id": manifest["edition_id"],
        "selected": [
            {"id": i, "path": MEMBERS[i], "bytes": len(data), "sha256": digest(data)}
            for i, data in payloads.items()
        ],
        "surrounding_population": {
            "edition_members": len(manifest["members"]),
            "selected_copies": len(ids),
            "complete_enterprise_retention_population": False,
        },
        "checks": checks,
        "final_state": final,
        "logical_fixture_period": {"start": AT, "last_event": RETRY},
        "limits": [
            "New owned public synthetic copies only; release originals and "
            "CompanyStore source originals unchanged",
            "Local fixture hold/retention, not approved corporate retention or legal hold release",
            "Pending-intent recovery only, not restore of older company backup "
            "with later hold/deletion state",
            "No secure erasure, production deployment, external authority, "
            "professional audit opinion or full IT gate claim",
        ],
    }
    (args.output / "RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": "PASS",
                "copies": len(ids),
                "retained_backup": True,
                "receipt": str(args.output / "RECEIPT.json"),
            }
        )
    )


if __name__ == "__main__":
    main()
