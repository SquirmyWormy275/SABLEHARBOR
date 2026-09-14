"""Export one authorized source census into a new private directory; no audit mutation."""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from enterprise.audit_suite.company_federation import (  # noqa: E402
    FederatedCompanyStore,
    _ExistingCompanyStore,
)
from enterprise.audit_suite.company_source_census import export_census, verify_export  # noqa: E402
from enterprise.audit_suite.company_source_census_collection import _period  # noqa: E402
from enterprise.audit_suite.private_publication import publish  # noqa: E402
from enterprise.audit_suite.source_readiness import _private, load_config  # noqa: E402
from enterprise.audit_suite.store import Store, canonical, digest  # noqa: E402


def run(config, destination):
    if not isinstance(config, dict) or set(config) != {
        "audit_root",
        "actor_id",
        "engagement_id",
        "source",
        "system_id",
        "query",
    }:
        raise ValueError("Exact operator census configuration required")
    audit_root = _private(config["audit_root"], directory=True)
    # Avoid Store constructor schema/permission mutations; get() still checks current membership.
    audit = Store.__new__(Store)
    audit.root = audit_root
    audit.db_path = _private(audit_root / "engagements.sqlite3")
    state = audit.get(config["actor_id"], config["engagement_id"])
    bound = state.get("company_source_binding")
    if not isinstance(bound, dict):
        raise ValueError("Explicit frozen engagement source binding required")
    selection = config["source"]
    if isinstance(selection, dict) and set(selection) == {"root"}:
        root = _private(selection["root"], directory=True)
        source = _ExistingCompanyStore(root)
        if set(bound) != {"company", "branch"}:
            raise ValueError("Concrete source requires concrete frozen binding")
        input_roots = [audit_root, root]
    elif isinstance(selection, dict) and set(selection) == {"registry", "profile"}:
        registry = _private(selection["registry"])
        source = FederatedCompanyStore(registry, selection["profile"])
        source.validate_binding(bound)
        input_roots = [
            audit_root,
            registry.parent,
            *[Path(c["root"]) for c in source._manifest["components"].values()],
        ]
    else:
        raise ValueError("Select one concrete store or a configured portfolio profile")
    destination = Path(destination)
    if not destination.is_absolute() or ".." in destination.parts:
        raise ValueError("Canonical absolute new output required")
    _private(destination.parent, directory=True)
    if (
        destination.exists()
        or destination.is_symlink()
        or any(destination == p or destination.is_relative_to(p) for p in input_roots)
    ):
        raise ValueError("New destination outside source and audit roots required")
    _period(state["scope"], config["query"])
    exported = export_census(
        source,
        principal_id=config["actor_id"],
        engagement_id=state["id"],
        company_id=bound["company"],
        branch_id=bound["branch"],
        system_id=config["system_id"],
        as_of=state["simulated_at"],
        query=config["query"],
    )
    pin = digest(exported["manifest"])
    verify_export(exported, expected_manifest_sha256=pin)
    stage = Path(tempfile.mkdtemp(prefix=".source-census-", dir=destination.parent))
    try:

        def write(name, content):
            fd = os.open(stage / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)

        originals = {}
        for member, content in zip(
            exported["manifest"]["members"], exported["originals"], strict=True
        ):
            sha = member["source"]["sha256"]
            if sha not in originals:
                name = "native-" + sha
                write(name, content)
                originals[sha] = name
        write("MANIFEST.json", canonical(exported["manifest"]).encode())
        write("CONFIG.json", canonical(config).encode())
        receipt = {
            "schema": "OPERATOR_SOURCE_CENSUS_EXPORT_V1",
            "manifest_sha256": pin,
            "audit_revision": state["revision"],
            "audit_snapshot_sha256": digest(state),
            "original_files": originals,
            "source_versions": len(exported["originals"]),
            "registration": "NOT_IMPORTED",
            "qualification": exported["manifest"]["qualification"],
            "module_sha256": hashlib.sha256(
                Path(sys.modules[export_census.__module__].__file__).read_bytes()
            ).hexdigest(),
        }
        write("RECEIPT.json", canonical(receipt).encode())
        if audit.get(config["actor_id"], state["id"]) != state:
            raise ValueError("Engagement changed during export; retry explicitly")
        systems = source.list_systems(
            config["actor_id"], state["id"], bound["company"], bound["branch"]
        )["systems"]
        if config["system_id"] not in {s["system"] for s in systems}:
            raise ValueError("Source grant revoked during export")
        publish(stage, destination)
        return receipt
    finally:
        shutil.rmtree(stage)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    receipt = run(load_config(args.config), args.output)
    print(
        json.dumps(
            {
                "source_versions": receipt["source_versions"],
                "manifest_sha256": receipt["manifest_sha256"],
                "registration": receipt["registration"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
