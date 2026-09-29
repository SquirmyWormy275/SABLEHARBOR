"""Actual older-copy backup/restore against the pinned portal disposal journal.

Run with the public_copy_disposal CLI arguments. Uses only new private fixture
copies from an accepted public release. Existing live portal data is untouched.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from . import public_copy_disposal as predecessor
from .working_copy_restore import RestoreError, capture, checkpoint, disclose, encoded, restore, sha

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portal", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--package-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.portal.resolve()))
    from enterprise.audit_suite import company_disposal_runtime as native
    from enterprise.audit_suite.company_backup_runtime import database
    from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError

    captured = {}
    original = native.initialize

    def initialize(destination, **kwargs):
        result = original(destination, **kwargs)
        cfg = json.loads((destination / "RUNTIME.json").read_bytes())
        state = native.inspect(
            destination, expected_runtime_sha256=result["runtime_sha256"], as_of=predecessor.AT
        )
        copies = {i: destination / "copies" / r["file"] for i, r in cfg["copies"].items()}
        backup = args.output / "older-copy-backup"
        digest = capture(
            backup,
            copies,
            state,
            expected_hashes={i: r["identity"]["sha256"] for i, r in cfg["copies"].items()},
        )
        captured.update(backup=backup, digest=digest, initial=checkpoint(state), cfg=cfg)
        return result

    with patch.object(native, "initialize", side_effect=initialize):
        predecessor.main()
    root = args.output / "runtime"
    cfg = captured["cfg"]
    runtime_hash = sha((root / "RUNTIME.json").read_bytes())
    at = "2027-05-01T00:03:00Z"
    company, branch = cfg["plan"]["company_id"], cfg["plan"]["branch_id"]
    principal = cfg["operator_id"]
    engagement = "copy-restore-inspection"
    store = CompanyStore(root)
    store.grant(principal, engagement, company, branch, "disposal_definition")

    def current():
        state = native.inspect(root, expected_runtime_sha256=runtime_hash, as_of=at)
        with database(root) as db:
            grants = [
                list(r)
                for r in db.execute(
                    "SELECT * FROM grants ORDER BY principal,engagement,company,branch,system"
                )
            ]
        return {**state, "current_native_grants_sha256": sha(encoded(grants))}

    # Load company-owned policy from this accepted/candidate checkout; portal source untouched.
    spec = importlib.util.spec_from_file_location(
        "company_policy_successor", ROOT / "enterprise/ccf/company_closeout/information_policy.py"
    )
    policy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(policy)
    records = {
        i: {
            "record_id": i,
            "tenant": "SH",
            "class_id": "PUBLIC_WORKING_COPY",
            "owner_id": principal,
            "source_version": "1",
            "source_sha256": r["identity"]["sha256"],
            "effective_at": predecessor.AT,
            "available_at": predecessor.AT,
            "purposes": ["inspection"],
            "sources": [],
        }
        for i, r in cfg["copies"].items()
    }
    subject = {"id": principal, "tenant": "SH", "purpose": "inspection"}

    def permitted(ident, action):
        try:
            store.read_version(
                principal,
                engagement,
                company,
                branch,
                "disposal_definition",
                "DEFINITION",
                version=1,
                as_of=at,
            )
        except CompanyStoreError:
            return False
        return (
            policy.decide(
                records, ident, subject, "memory" if action == "personal_memory" else action, at
            )
            == "ALLOW"
        )

    outcomes = {}

    def denial(name, fn):
        try:
            fn()
        except RestoreError as exc:
            outcomes[name] = {"result": "DENIED", "reason": str(exc)}
        else:
            raise ValueError("Required denial missing: " + name)

    denial(
        "older_checkpoint",
        lambda: restore(
            captured["backup"],
            args.output / "stale",
            backup_sha256=captured["digest"],
            current_reader=current,
            expected_checkpoint=captured["initial"],
        ),
    )
    good_pin = checkpoint(current())
    restored = args.output / "restored-working-copies"
    restored_receipt = restore(
        captured["backup"],
        restored,
        backup_sha256=captured["digest"],
        current_reader=current,
        expected_checkpoint=good_pin,
    )
    for action in [
        "read",
        "snippet",
        "citation",
        "export",
        "vector",
        "count",
        "graph",
        "tool_result",
        "answer",
        "search",
        "personal_memory",
    ]:
        for ident in ["CAPITAL", "EQUITY"]:
            denial(
                "deleted_" + ident + "_" + action,
                lambda i=ident, a=action: disclose(
                    restored,
                    i,
                    current_reader=current,
                    expected_checkpoint=good_pin,
                    authorized=permitted,
                    action=a,
                ),
            )
    payload = disclose(
        restored,
        "PAYROLL_BACKUP",
        current_reader=current,
        expected_checkpoint=good_pin,
        authorized=permitted,
    )
    assert sha(payload) == cfg["copies"]["PAYROLL_BACKUP"]["identity"]["sha256"]
    store.grant(principal, engagement, company, branch, "disposal_definition", active=False)
    denial(
        "revoked_after_restore",
        lambda: disclose(
            restored,
            "PAYROLL_BACKUP",
            current_reader=current,
            expected_checkpoint=good_pin,
            authorized=permitted,
        ),
    )
    revoked_pin = checkpoint(current())
    revoked = args.output / "restored-after-revocation"
    restore(
        captured["backup"],
        revoked,
        backup_sha256=captured["digest"],
        current_reader=current,
        expected_checkpoint=revoked_pin,
    )
    denial(
        "revoked_after_fresh_restore",
        lambda: disclose(
            revoked,
            "PAYROLL_BACKUP",
            current_reader=current,
            expected_checkpoint=revoked_pin,
            authorized=permitted,
        ),
    )
    store.grant(principal, engagement, company, branch, "disposal_definition")
    state = current()
    native.control(
        root,
        expected_runtime_sha256=runtime_hash,
        expected_revision=state["revision"],
        operator_id=principal,
        command_id="restore-later-hold",
        event_at=at,
        action="HOLD",
        payload={
            "copy_id": "PAYROLL_BACKUP",
            "hold_id": "LATER-HOLD",
            "active": True,
            "rationale": "Explicit working-copy software test; preserve bytes without disclosure",
        },
    )
    held_pin = checkpoint(current())
    held = args.output / "restored-held"
    held_receipt = restore(
        captured["backup"],
        held,
        backup_sha256=captured["digest"],
        current_reader=current,
        expected_checkpoint=held_pin,
    )
    assert (held / cfg["copies"]["PAYROLL_BACKUP"]["file"]).read_bytes() == payload
    denial(
        "later_hold_denies_read",
        lambda: disclose(
            held,
            "PAYROLL_BACKUP",
            current_reader=current,
            expected_checkpoint=held_pin,
            authorized=permitted,
        ),
    )
    outcomes["preserved_held_hash"] = sha(payload)
    result = {
        "result": "PASS",
        "observed_at": datetime.now(UTC).isoformat(),
        "portal_commit": predecessor.PIN,
        "package_sha256": args.package_sha256,
        "working_copy_backup_sha256": captured["digest"],
        "initial_checkpoint": captured["initial"],
        "current_checkpoint": held_pin,
        "restored": restored_receipt,
        "held_restore": held_receipt,
        "checks": outcomes,
        "source_hashes": {
            str(p.relative_to(ROOT)): sha(p.read_bytes())
            for p in [
                Path(__file__),
                ROOT / "tools/company_closeout/working_copy_restore.py",
                ROOT / "enterprise/ccf/company_closeout/information_policy.py",
            ]
        },
        "limits": [
            "Trusted local authenticated-operator adapter; no live portal deployment or HTTP boundary claim",
            "CompanyStore originals and prior releases remain immutable; only separately declared working copies restored",
            "Current portal journal and grant state must survive outside old backup; missing/stale checkpoint denies restore",
            "No secure erasure, real legal hold release, professional opinion or model-inference effectiveness assertion",
            "Logical May2027 fixture dates; actual observation is later-authored software evidence, not September2026 operations",
        ],
    }
    (args.output / "WORKING_COPY_RESTORE_RECEIPT.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "result": "PASS",
                "checks": len(outcomes),
                "receipt": str(args.output / "WORKING_COPY_RESTORE_RECEIPT.json"),
            }
        )
    )


if __name__ == "__main__":
    main()
