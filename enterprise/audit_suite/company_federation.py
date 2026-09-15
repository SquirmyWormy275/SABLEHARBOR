"""Trusted read-through portfolios of original company stores; no source/history union."""

import json
import os
import sqlite3
import stat
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _id
from .store import DomainError, digest

SCHEMA = "COMPANY_SOURCE_PORTFOLIO_V1"
QUALIFICATION = "QUALIFIED_SOURCE_PORTFOLIO_NOT_COHERENT_OPERATING_YEAR"
CAPABILITIES = {
    "source_discovery": True,
    "exact_version_collection": True,
    "cross_store_populations": False,
    "company_populations": False,
    "source_impact": True,
    "explanation_binding": True,
    "global_snapshot": False,
    "source_mutation": False,
}


def _private(path, directory=False):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise CompanyStoreError("Company registry/source aliases forbidden")
    info = path.stat()
    if info.st_mode & 0o077 or not (
        stat.S_ISDIR(info.st_mode)
        if directory
        else stat.S_ISREG(info.st_mode) and info.st_nlink == 1
    ):
        raise CompanyStoreError("Private regular company registry/source required")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CompanyStoreError("Duplicate registry field")
        result[key] = value
    return result


def load_profile(path: Path, profile_id: str):
    """Return a private normalized manifest; never expose its filesystem paths to learners."""
    path = Path(path).absolute()
    _id(profile_id)
    try:
        _private(path.parent, True)
        _private(path)
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_nlink != 1:
                raise CompanyStoreError("Private regular company registry required")
            raw = stream.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise CompanyStoreError("Company registry exceeds size limit")
        config = json.loads(raw, object_pairs_hook=_pairs)
        if not isinstance(config, dict) or set(config) != {"schema", "components", "profiles"}:
            raise CompanyStoreError("Exact company portfolio registry required")
        if (
            config["schema"] != SCHEMA
            or not isinstance(config["components"], dict)
            or not isinstance(config["profiles"], dict)
        ):
            raise CompanyStoreError("Invalid company portfolio registry")
        profile = config["profiles"].get(profile_id)
        if not isinstance(profile, dict) or set(profile) != {
            "company",
            "components",
            "qualification",
        }:
            raise CompanyStoreError("Company portfolio profile unavailable")
        _id(profile["company"])
        selected = profile["components"]
        if (
            not isinstance(selected, list)
            or not 1 <= len(selected) <= 32
            or any(not isinstance(c, str) for c in selected)
            or len(set(selected)) != len(selected)
            or profile["qualification"] != QUALIFICATION
        ):
            raise CompanyStoreError("Explicit distinct qualified portfolio components required")
        components, aliases, physical, namespaces = {}, set(), set(), set()
        for source_id in sorted(selected):
            _id(source_id)
            component = config["components"].get(source_id)
            if not isinstance(component, dict) or set(component) != {
                "root",
                "company",
                "branch",
                "namespace",
                "systems",
            }:
                raise CompanyStoreError("Exact company component routing required")
            for field in ("company", "branch", "namespace"):
                _id(component[field])
            if ":" in component["namespace"] or component["namespace"] in namespaces:
                raise CompanyStoreError("Distinct colon-free source namespaces required")
            namespaces.add(component["namespace"])
            if not isinstance(component["root"], str) or not Path(component["root"]).is_absolute():
                raise CompanyStoreError("Explicit absolute company source root required")
            root = Path(component["root"])
            if str(root) != component["root"] or ".." in root.parts:
                raise CompanyStoreError("Canonical company source root required")
            _private(root, True)
            _private(root / "company.sqlite3")
            systems = component["systems"]
            if not isinstance(systems, list) or not 1 <= len(systems) <= 512:
                raise CompanyStoreError("Bounded explicit source system inventory required")
            for system in systems:
                _id(system)
                alias = component["namespace"] + ":" + system
                target = (str(root), component["company"], component["branch"], system)
                if alias in aliases or target in physical:
                    raise CompanyStoreError("Duplicate source alias or physical route")
                aliases.add(alias)
                physical.add(target)
            components[source_id] = {**component, "systems": sorted(systems)}
        return {
            "schema": SCHEMA,
            "profile_id": profile_id,
            "profile": {**profile, "components": sorted(selected)},
            "components": components,
        }
    except (OSError, TypeError, ValueError) as exc:
        if isinstance(exc, CompanyStoreError):
            raise
        raise CompanyStoreError("Company portfolio configuration unavailable or invalid") from exc


class _ExistingCompanyStore(CompanyStore):
    """Open the existing native schema without constructor DDL or empty-file repair."""

    def __init__(self, root):
        self.path = root / "company.sqlite3"
        _private(root, True)
        _private(self.path)
        try:
            with sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True) as db:
                db.execute("PRAGMA query_only=ON")
                for table, columns in {
                    "systems": "company,branch,system,owner",
                    "versions": (
                        "company,branch,system,record,version,event_at,available_at,imported_at,"
                        "origin,provenance,content,sha256,command_id,input_digest"
                    ),
                    "grants": "principal,engagement,company,branch,system,active",
                    "collections": "command_id,input_digest,receipt",
                }.items():
                    db.execute(f"SELECT {columns} FROM {table} LIMIT 0")
        except sqlite3.Error as exc:
            raise CompanyStoreError("Existing company source schema unavailable") from exc


class FederatedCompanyStore:
    """Route fixed namespace aliases to exact original stores, branches and systems.

    Reads and collection journals use original current grants, principals and clocks.
    Each operation has its own backend transaction; no cross-store atomicity is implied.
    Operators grant each physical system separately. No grant propagation API exists.
    """

    capabilities = CAPABILITIES
    is_federated = True

    def __init__(self, registry_path: Path, profile_id: str):
        self.registry_path = Path(registry_path).absolute()
        self.profile_id = profile_id
        self._manifest = load_profile(self.registry_path, profile_id)
        self.registry_sha256 = digest(self._manifest)
        self._stores, self._routes = {}, {}
        for source_id, component in self._manifest["components"].items():
            store = _ExistingCompanyStore(Path(component["root"]))
            with store._db() as db:
                registered = {
                    r[0]
                    for r in db.execute(
                        "SELECT system FROM systems WHERE company=? AND branch=?",
                        (component["company"], component["branch"]),
                    )
                }
            if not set(component["systems"]) <= registered:
                raise CompanyStoreError("Configured source systems are not registered")
            self._stores[source_id] = store
            for system in component["systems"]:
                self._routes[component["namespace"] + ":" + system] = (source_id, system)

    @property
    def binding(self):
        return {
            "company": self._manifest["profile"]["company"],
            "branch": self.profile_id,
            "registry_sha256": self.registry_sha256,
        }

    def _check(self, company, branch):
        if company != self.binding["company"] or branch != self.profile_id:
            raise CompanyStoreError("Company portfolio binding mismatch")
        if digest(load_profile(self.registry_path, self.profile_id)) != self.registry_sha256:
            raise CompanyStoreError("Company portfolio changed; explicit reconciliation required")

    def validate_binding(self, selected):
        if selected != self.binding:
            raise CompanyStoreError("Frozen company portfolio manifest mismatch")
        self._check(selected["company"], selected["branch"])

    def _route(self, company, branch, alias):
        self._check(company, branch)
        if not isinstance(alias, str) or alias not in self._routes:
            raise CompanyStoreError("Company source namespace unavailable")
        source_id, system = self._routes[alias]
        component = self._manifest["components"][source_id]
        return source_id, system, component, self._stores[source_id]

    def _metadata(self, original, source_id, alias):
        return {
            **original,
            "source_store_id": source_id,
            "source_system_alias": alias,
            "registry_sha256": self.registry_sha256,
            "portfolio_qualification": QUALIFICATION,
        }

    def _authorized(self, actor, engagement, source_id, system, company, branch):
        component = self._manifest["components"][source_id]
        allowed = self._stores[source_id].list_systems(
            actor, engagement, component["company"], component["branch"]
        )
        if system not in {r["system"] for r in allowed["systems"]}:
            raise CompanyStoreError("Company source unavailable or unauthorized")
        self._check(company, branch)

    def list_systems(self, principal_id, engagement_id, company_id, branch_id):
        self._check(company_id, branch_id)
        result = []
        for source_id, component in self._manifest["components"].items():
            systems = self._stores[source_id].list_systems(
                principal_id, engagement_id, component["company"], component["branch"]
            )
            for row in systems["systems"]:
                if row["system"] in component["systems"]:
                    result.append(
                        {
                            "system": component["namespace"] + ":" + row["system"],
                            "owner": row["owner"],
                            "source_store_id": source_id,
                            "portfolio_qualification": QUALIFICATION,
                        }
                    )
        # Reevaluate earlier component grants after the remaining sources were read.
        # This is still per-source authorization, not a global database snapshot.
        current_aliases = set()
        for source_id, component in self._manifest["components"].items():
            current = self._stores[source_id].list_systems(
                principal_id, engagement_id, component["company"], component["branch"]
            )
            current_aliases.update(
                component["namespace"] + ":" + row["system"]
                for row in current["systems"]
                if row["system"] in component["systems"]
            )
        result = [row for row in result if row["system"] in current_aliases]
        self._check(company_id, branch_id)
        return {
            "systems": sorted(result, key=lambda r: r["system"]),
            "registry_sha256": self.registry_sha256,
            "snapshot_isolation": "PER_SOURCE_NOT_GLOBAL",
            "capabilities": dict(CAPABILITIES),
        }

    def list_records(
        self,
        principal_id,
        engagement_id,
        company_id,
        branch_id,
        system_id,
        *,
        as_of,
        after_record=None,
        limit=100,
    ):
        source_id, system, component, store = self._route(company_id, branch_id, system_id)
        page = store.list_records(
            principal_id,
            engagement_id,
            component["company"],
            component["branch"],
            system,
            as_of=as_of,
            after_record=after_record,
            limit=limit,
        )
        self._authorized(principal_id, engagement_id, source_id, system, company_id, branch_id)
        return {
            **page,
            "records": [self._metadata(r, source_id, system_id) for r in page["records"]],
            "registry_sha256": self.registry_sha256,
            "snapshot_isolation": "ONE_SOURCE_PAGE_ONLY",
        }

    def read_version(
        self,
        principal_id,
        engagement_id,
        company_id,
        branch_id,
        system_id,
        record_id,
        *,
        version,
        as_of,
    ):
        source_id, system, component, store = self._route(company_id, branch_id, system_id)
        row = store.read_version(
            principal_id,
            engagement_id,
            component["company"],
            component["branch"],
            system,
            record_id,
            version=version,
            as_of=as_of,
        )
        self._authorized(principal_id, engagement_id, source_id, system, company_id, branch_id)
        return self._metadata(row, source_id, system_id)

    def collect(
        self,
        principal_id,
        engagement_id,
        company_id,
        branch_id,
        system_id,
        record_id,
        *,
        version,
        as_of,
        command_id,
    ):
        _id(command_id)
        source_id, system, component, store = self._route(company_id, branch_id, system_id)
        receipt = store.collect(
            principal_id,
            engagement_id,
            component["company"],
            component["branch"],
            system,
            record_id,
            version=version,
            as_of=as_of,
            command_id="FED-" + digest([self.registry_sha256, source_id, command_id]),
        )
        self._authorized(principal_id, engagement_id, source_id, system, company_id, branch_id)
        return {
            **receipt,
            "source": self._metadata(receipt["source"], source_id, system_id),
            "upstream_receipt": receipt,
            "portfolio_command_id": command_id,
            "idempotency_scope": "SOURCE_COMPONENT_AND_PROFILE",
            "registry_sha256": self.registry_sha256,
        }

    def resolve_source_identity(self, identity):
        """Validate an immutable retained physical identity and return its lookup alias.

        This only resolves a configured route; the subsequent read must check grants
        and simulated availability for the authenticated audit principal.
        """
        if (
            not isinstance(identity, dict)
            or identity.get("registry_sha256") != self.registry_sha256
        ):
            raise CompanyStoreError("Retained source portfolio pin differs")
        alias = identity.get("source_system_alias")
        source_id, system, component, _ = self._route(
            self.binding["company"], self.binding["branch"], alias
        )
        if (
            identity.get("source_store_id") != source_id
            or identity.get("company") != component["company"]
            or identity.get("branch") != component["branch"]
            or identity.get("system") != system
        ):
            raise CompanyStoreError("Retained source identity differs from its configured route")
        return alias

    def _db(self):
        raise DomainError(
            (
                "Portfolio operations require a concrete source transaction; "
                "no cross-store snapshot is available"
            ),
            code="FEDERATION_OPERATION_UNSUPPORTED",
            status=409,
        )
