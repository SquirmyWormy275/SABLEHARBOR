"""Strict normalization of existing native sources; generated records create no canon."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
VERSION = "0.1.0"
KNOWN_ON = "2026-09-11"
SOURCES = {
    "domains": "docs/controls/CCF_DOMAIN_TAXONOMY_v0.1.md",
    "controls": "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
    "objectives": "docs/controls/CCF_CONTROL_OBJECTIVES_v0.1.md",
    "risks": "docs/governance/CCF_ENTERPRISE_OBJECTIVES_AND_RISK_UNIVERSE_v0.1.md",
    "trace": "docs/controls/CCF_RISK_CONTROL_TRACEABILITY_MATRIX_v0.1.md",
    "applicability": "docs/controls/CCF_BUSINESS_LINE_APPLICABILITY_MATRIX_v0.1.md",
    "business": "docs/structured/business-lines/interfaces.json",
    "runtime": "enterprise/services/source/runtime_capital_plan_2026-09-11.json",
    "sites": "enterprise/services/source/runtime_sites_2026-09-11.json",
    "services": "enterprise/services/source/services.json",
    "components": "enterprise/services/source/components.json",
    "counterparties": "enterprise/services/source/counterparties.json",
    "prep": "enterprise/ccf/source/preparation.json",
}
UNITS = {
    "CORP": ("corporate", "Corporate shared functions"),
    "FF": ("foundry-field", "Foundry / Foundry Field"),
    "ATL": ("atlas-meridian", "Atlas Meridian"),
    "WIL": ("willow", "Willow / R&D"),
    "ADV": ("advisory", "Advisory"),
    "PS": ("pale-sun", "Pale Sun"),
    "RW": ("red-wash", "Red Wash operating boundary"),
    "CRD": ("project-cradle", "Project Cradle"),
    "ARU": ("american-resource-utility", "American Resource Utility"),
    "BST": ("bst", "Blood, Sweat & Tears Railway"),
}
OPERATING_UNITS = {v[0] for k, v in UNITS.items() if k not in {"RW", "BST"}}


def canonical(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def rows(text):
    return [
        [c.strip() for c in line.strip().strip("|").split("|")]
        for line in text.splitlines()
        if line.startswith("|")
    ]


def expand(value, prefix=None):
    """Expand native ranges and abbreviated slash IDs; reject leftover syntax."""
    result = []
    for group in value.split(","):
        group = group.strip()
        if prefix:
            group = prefix + group
        match = re.fullmatch(r"(SH-(?:OBJ-|RISK-)?[A-Z]+-)(\d{3})(.*)", group)
        if not match:
            raise ValueError(f"Unsupported native reference: {group}")
        base, first, tail = match.groups()
        numbers = [int(first)]
        if tail.startswith("–") or tail.startswith("-"):
            if not re.fullmatch(r"[–-]\d{3}", tail) or int(tail[1:]) < int(first):
                raise ValueError(f"Invalid native range: {group}")
            numbers = list(range(int(first), int(tail[1:]) + 1))
        elif tail:
            if not re.fullmatch(r"(?:/\d{3})+", tail):
                raise ValueError(f"Invalid native slash reference: {group}")
            numbers += [int(n) for n in tail[1:].split("/")]
        result.extend(f"{base}{n:03}" for n in numbers)
    return sorted(set(result))


def record(kind, identifier, data, source, effective="2026-09-02", unresolved=None):
    return dict(
        kind=kind,
        id=identifier,
        version=VERSION,
        effective_from=effective,
        effective_to=None,
        recorded_on=KNOWN_ON,
        status="draft",
        origin="DERIVED_PREPARATION",
        source_refs=[source],
        data=data,
        unresolved_fields=sorted(unresolved or []),
    )


def compile_registry(repository=ROOT):
    repository = Path(repository)
    texts = {k: (repository / p).read_text() for k, p in SOURCES.items()}
    records = []

    def add(kind, identifier, data, source, effective="2026-09-02", unresolved=None):
        item = record(kind, identifier, data, SOURCES[source], effective, unresolved)
        records.append(item)
        return item

    domains = {}
    for cells in rows(texts["domains"]):
        if re.fullmatch(r"[A-Z]{3}", cells[0]):
            domains[cells[0]] = add(
                "domain", cells[0], {"title": cells[1], "scope": cells[2]}, "domains"
            )
    for code, (identifier, title) in UNITS.items():
        add(
            "boundary",
            identifier,
            {
                "title": title,
                "type": "business_boundary",
                "parent_id": None,
                "legal_entity_id": None,
            },
            "applicability",
            unresolved=["legal_entity_id"],
        )
    runtime_sites = json.loads(texts["sites"])["sites"]
    for site in runtime_sites:
        add(
            "boundary",
            site["id"],
            {
                "title": site["name"],
                "type": "runtime_site",
                "parent_id": "corporate",
                "legal_entity_id": site["entity_id"],
            },
            "sites",
            KNOWN_ON,
        )
    for cells in rows(texts["risks"]):
        if re.fullmatch(r"SH-EO-\d{3}", cells[0]):
            add("enterprise_objective", cells[0], {"statement": cells[1]}, "risks")
    objectives = {}
    for identifier, statement in re.findall(
        r"^- \*\*(SH-OBJ-[A-Z]+-\d{3}):\*\* (.+)$", texts["objectives"], re.M
    ):
        objectives[identifier] = add(
            "objective",
            identifier,
            {
                "domain_id": identifier.split("-")[2],
                "statement": statement,
                "business_basis": None,
                "risk_ids": [],
                "owner_role_id": None,
                "applicability": None,
            },
            "objectives",
            unresolved=["business_basis", "owner_role_id", "applicability"],
        )
    risks = {}
    for identifier, title, statement in re.findall(
        r"^- \*\*(SH-RISK-[A-Z]+-\d{3}) — (.+?):\*\* (.+)$", texts["risks"], re.M
    ):
        data = dict(
            title=title,
            category=identifier.split("-")[2],
            statement=statement,
            control_ids=[],
            enterprise_objective_ids=[],
            cause=None,
            event=None,
            impact=None,
            owner_role_id=None,
            challenge_role_id=None,
            applicability=None,
            inherent_likelihood=None,
            inherent_impact=None,
            residual_likelihood=None,
            residual_impact=None,
            tolerance=None,
            velocity=None,
            kris=None,
        )
        risks[identifier] = add(
            "risk", identifier, data, "risks", unresolved=[k for k, v in data.items() if v is None]
        )
    for cells in rows(texts["trace"]):
        if cells[0].startswith("SH-RISK-"):
            if cells[0] not in risks:
                raise ValueError("Unknown traceability risk")
            risks[cells[0]]["data"].update(
                control_ids=expand(cells[2]), enterprise_objective_ids=expand(cells[3], "SH-")
            )
            risks[cells[0]]["source_refs"].append(SOURCES["trace"])
    roles = {}

    def role(title, source):
        if not title:
            return None
        identifier = "ROLE-" + hashlib.sha256(title.encode()).hexdigest()[:16]
        if identifier not in roles:
            roles[identifier] = add(
                "role",
                identifier,
                {
                    "title": title,
                    "appointment_ids": [],
                    "authority_state": "SOURCE_ROLE_LABEL_ONLY",
                },
                source,
                unresolved=["appointment_ids"],
            )
        return identifier

    controls = {}
    for cells in rows(texts["controls"]):
        if re.fullmatch(r"SH-[A-Z]+-\d{3}", cells[0]):
            cid, statement, objective, owner, frequency, evidence = cells
            linked_risks = sorted(k for k, v in risks.items() if cid in v["data"]["control_ids"])
            data = dict(
                title=statement,
                statement=statement,
                domain_id=cid.split("-")[1],
                objective_ids=expand(objective, "SH-OBJ-"),
                risk_ids=linked_risks,
                enterprise_objective_ids=sorted(
                    {i for k in linked_risks for i in risks[k]["data"]["enterprise_objective_ids"]}
                ),
                owner_role_id=role(owner, "controls"),
                performer_role_id=None,
                challenge_role_id=None,
                frequency_or_trigger=frequency,
                evidence_expectation=evidence,
                business_rationale=None,
                applicability_rule={"basis": "DOMAIN_MATRIX", "control_level_approval": "PENDING"},
                control_nature=None,
                control_function=None,
                key_control=None,
                financial_reporting_relevance=None,
                customer_service_relevance=None,
                security_privacy_relevance=None,
                operational_safety_relevance=None,
                failure_modes=None,
                exception_process=None,
                upstream_control_ids=[],
                secondary_domain_ids=[],
                framework_mapping_ids=[],
            )
            controls[cid] = add(
                "control",
                cid,
                data,
                "controls",
                unresolved=[
                    k
                    for k, v in data.items()
                    if v is None or k in {"risk_ids", "enterprise_objective_ids"} and not v
                ],
            )
            for oid in data["objective_ids"]:
                if oid not in objectives:
                    raise ValueError(f"Unknown objective {oid}")
                objectives[oid]["data"]["risk_ids"] = sorted(
                    set(objectives[oid]["data"]["risk_ids"]) | set(linked_risks)
                )
    matrix = {c[0]: c[1:] for c in rows(texts["applicability"]) if c[0] in domains}
    for cid, item in controls.items():
        for n, (_, (boundary, _)) in enumerate(UNITS.items()):
            add(
                "applicability",
                f"APP-{cid}-{boundary}",
                dict(
                    control_id=cid,
                    boundary_id=boundary,
                    design_disposition=matrix[item["data"]["domain_id"]][n],
                    decision_state="PENDING_LOCAL_REVIEW",
                    rationale=matrix[item["data"]["domain_id"]][-1],
                    approver_role_id=None,
                    review_due=None,
                ),
                "applicability",
                unresolved=["approver_role_id", "review_due"],
            )
    business = json.loads(texts["business"])["local_controls"]

    def local(
        identifier, cid, owner, boundary_ids, description, evidence, source, effective, **extra
    ):
        data = dict(
            control_id=cid,
            boundary_ids=sorted(boundary_ids),
            owner_role_id=role(owner, source),
            performer_role_id=None,
            challenge_role_id=None,
            process=None,
            procedure_reference=None,
            description=description,
            implementation_state="DESIGN_ONLY",
            design_assessment="NOT_ASSESSED",
            operating_assessment="NOT_ASSERTED",
            evidence_origin="SYNTHETIC_REFERENCE",
            evidence_sources=evidence,
            population_definition=None,
            last_owner_review=None,
            next_review_due=None,
            inherits_from_id=None,
            local_variation_reason=None,
            exception_ids=[],
            remediation_ids=[],
            configuration_dependencies=[],
            known_limitations=[],
        )
        data.update(extra)
        return add(
            "implementation",
            identifier,
            data,
            source,
            effective,
            [k for k, v in data.items() if v is None],
        )

    for item in business:
        scope = item["scope"]
        boundaries = (
            OPERATING_UNITS
            if scope == "all"
            else (
                OPERATING_UNITS - {"corporate", "willow"}
                if scope == "commercial businesses"
                else set(scope.split(","))
            )
        )
        local(
            item["id"],
            item["control_id"],
            item["owner"],
            boundaries,
            item["procedure"],
            [item["evidence"]],
            "business",
            "2026-09-09",
            process=item["id"],
            procedure_reference=SOURCES["business"],
            known_limitations=[
                "Source scope retained; synthetic operations do not prove production effectiveness."
            ],
        )
    runtime = json.loads(texts["runtime"])["implementation_assumptions"]["control_implementations"]
    for item in runtime:
        local(
            item["implementation_id"],
            item["control_id"],
            item["implementation_owner_role"],
            [item["system_or_location"]],
            item["implementation_description"],
            item["evidence_sources"],
            "runtime",
            item["effective_date"],
            process=item["process"],
            procedure_reference=item["procedure_reference"],
            performer_role_id=role(item["performer_role"], "runtime"),
            challenge_role_id=role(item["challenge_role"], "runtime"),
            population_definition=item["population_definition"],
            exception_ids=item["exception_ids"],
            remediation_ids=item["remediation_ids"],
            last_owner_review=item["last_owner_review"],
            next_review_due=item["next_review_due"],
            configuration_dependencies=item["configuration_dependencies"],
            known_limitations=item["known_limitations"]
            + ([item["inheritance_source"]] if item["inheritance_source"] else []),
        )
    # Import native service/component/provider dependencies without inventing deployments.
    service_data = {
        name: json.loads(texts[name]) for name in ("services", "components", "counterparties")
    }
    for name, rows_key, columns_key in (
        ("services", "services", "columns"),
        ("counterparties", "dependencies", "dependency_columns"),
    ):
        table = service_data[name]
        columns = table[columns_key]
        if len(columns) != len(set(columns)) or any(
            len(row) != len(columns) for row in table[rows_key]
        ):
            raise ValueError("Invalid native service source width")
        table[rows_key] = [dict(zip(columns, row)) for row in table[rows_key]]
    from enterprise.runtime.model import apply_services

    apply_services(
        service_data, {"sites": json.loads(texts["sites"]), "capital": json.loads(texts["runtime"])}
    )
    for item in service_data["components"]["components"]:
        data = dict(
            title=item["name"],
            component_type=item["type"],
            owner_role_id=role(item["owner"], "components"),
            planned_boundary_id=item.get("runtime_id", item.get("planned_runtime_id")),
            deployment_state="NOT_VERIFIED",
        )
        add(
            "component",
            item["id"],
            data,
            "components",
            KNOWN_ON,
            [k for k, v in data.items() if v is None],
        )
    for item in service_data["counterparties"]["counterparties"]:
        add(
            "provider",
            item["id"],
            dict(
                title=item["name"],
                provider_kind=item["kind"],
                contract_state=item["contract_status"],
                scope=item["scope"],
            ),
            "counterparties",
            KNOWN_ON,
        )
    for item in service_data["counterparties"]["dependencies"]:
        data = dict(
            title=item["name"],
            owner_role_id=role(item["relationship_owner"], "counterparties"),
            provider_id=item["provider_id"],
            scope=item["scope"],
            lifecycle_state=item["lifecycle_state"],
        )
        add(
            "dependency",
            item["id"],
            data,
            "counterparties",
            KNOWN_ON,
            [k for k, v in data.items() if v is None],
        )
    for item in service_data["services"]["services"]:
        add(
            "service",
            item["id"],
            dict(
                title=item["name"],
                work=item["work"],
                owner_component_id=item["accountable_owner"],
                component_ids=item["components"],
                dependency_ids=item["dependencies"],
                control_ids=item["controls"],
                recipients=item["recipients"],
                sourcing=item["sourcing"],
                delivery_state="NOT_VERIFIED",
            ),
            "services",
            KNOWN_ON,
        )
    prep = json.loads(texts["prep"])
    for item in prep["implementations"]:
        local(
            item["id"],
            item["control_id"],
            item["owner"],
            item["boundary_ids"],
            item["description"],
            item["evidence_sources"],
            "prep",
            KNOWN_ON,
            process=item["process"],
            procedure_reference=item["procedure_reference"],
            performer_role_id=role(item["performer"], "prep"),
            challenge_role_id=role(item["reviewer"], "prep"),
            population_definition=item["population_definition"],
            known_limitations=["Engineering proposal; no deployed integration or new authority."],
        )
    for item in prep["policies"]:
        add(
            "policy_gap", item["id"], {k: v for k, v in item.items() if k != "id"}, "prep", KNOWN_ON
        )
    for item in prep["decisions"]:
        add("decision", item["id"], {k: v for k, v in item.items() if k != "id"}, "prep", KNOWN_ON)
    for normalized in records:
        kind, data = normalized["kind"], normalized["data"]
        if kind in {"control", "objective"}:
            normalized["source_refs"] += [SOURCES["trace"], SOURCES["controls"], SOURCES["risks"]]
        if kind in {"component", "provider", "dependency"}:
            normalized["source_refs"] += [SOURCES["sites"], SOURCES["runtime"]]
        if kind == "policy_gap":
            normalized["source_refs"].append(data["source"])
        if data.get("procedure_reference"):
            normalized["source_refs"].append(data["procedure_reference"].split("#")[0])
        if kind == "objective" and not data["risk_ids"]:
            normalized["unresolved_fields"].append("risk_ids")
        normalized["source_refs"] = sorted(set(normalized["source_refs"]))
        normalized["unresolved_fields"] = sorted(set(normalized["unresolved_fields"]))
    source_paths = set(SOURCES.values()) | {p for r in records for p in r["source_refs"]}
    records.sort(key=lambda r: (r["kind"], r["id"]))
    result = dict(
        schema_version=VERSION,
        classification="PUBLIC_SYNTHETIC_PREPARATION",
        source_manifest={
            p: hashlib.sha256((repository / p).read_bytes()).hexdigest()
            for p in sorted(source_paths)
        },
        records=records,
    )
    validate(result, repository)
    return result


def validate(registry, repository=None):
    schema = json.loads((ROOT / "enterprise/ccf/schema.json").read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(registry)
    index = {}
    for r in registry["records"]:
        key = (r["kind"], r["id"])
        if key in index:
            raise ValueError(f"Duplicate record {key}")
        index[key] = r
        if r["effective_to"] and r["effective_to"] <= r["effective_from"]:
            raise ValueError("Invalid effective interval")
        for name in r["unresolved_fields"]:
            if name not in r["data"] or r["data"][name] not in (None, []):
                raise ValueError(f"Invalid unresolved field {name}")
        if set(k for k, v in r["data"].items() if v is None and k not in {"parent_id"}) - set(
            r["unresolved_fields"]
        ):
            raise ValueError("Unreported unresolved field")
        if not r["source_refs"] or not set(r["source_refs"]) <= set(registry["source_manifest"]):
            raise ValueError("Missing source manifest reference")

    def ref(kind, identifier):
        if (kind, identifier) not in index:
            raise ValueError(f"Unknown {kind}: {identifier}")

    for r in registry["records"]:
        d, kind = r["data"], r["kind"]
        for key, target in (
            ("domain_id", "domain"),
            ("control_id", "control"),
            ("boundary_id", "boundary"),
            ("owner_role_id", "role"),
            ("performer_role_id", "role"),
            ("challenge_role_id", "role"),
            ("approver_role_id", "role"),
            ("inherits_from_id", "implementation"),
            ("planned_boundary_id", "boundary"),
            ("provider_id", "provider"),
            ("owner_component_id", "component"),
        ):
            if d.get(key):
                ref(target, d[key])
        for key, target in (
            ("objective_ids", "objective"),
            ("risk_ids", "risk"),
            ("enterprise_objective_ids", "enterprise_objective"),
            ("control_ids", "control"),
            ("upstream_control_ids", "control"),
            ("boundary_ids", "boundary"),
            ("secondary_domain_ids", "domain"),
            ("component_ids", "component"),
            ("dependency_ids", "dependency"),
        ):
            if len(d.get(key, [])) != len(set(d.get(key, []))):
                raise ValueError(f"Duplicate edge {key}")
            for identifier in d.get(key, []):
                ref(target, identifier)
        if kind == "boundary" and d["parent_id"]:
            ref("boundary", d["parent_id"])
        if kind == "implementation":
            if not d["boundary_ids"] or not d["evidence_sources"]:
                raise ValueError("Implementation lacks scope or evidence")
            if (
                d["operating_assessment"] != "NOT_ASSERTED"
                or d["evidence_origin"] != "SYNTHETIC_REFERENCE"
            ):
                raise ValueError("Preparation cannot assert production effectiveness")
            if (
                d["last_owner_review"]
                and d["next_review_due"]
                and d["next_review_due"] < d["last_owner_review"]
            ):
                raise ValueError("Review chronology")
            if (
                d["inherits_from_id"]
                and index["implementation", d["inherits_from_id"]]["data"]["control_id"]
                != d["control_id"]
            ):
                raise ValueError("Inheritance parent control mismatch")
        if kind == "control":
            if (
                not d["objective_ids"]
                or not d["risk_ids"]
                and "risk_ids" not in r["unresolved_fields"]
            ):
                raise ValueError("Control lacks objective/risk link")
            for oid in d["objective_ids"]:
                if index["objective", oid]["data"]["domain_id"] != d["domain_id"]:
                    raise ValueError("Control objective domain mismatch")
        if r["status"] == "approved":
            raise ValueError("Derived preparation lacks an approval record")
        if r["status"] == "effective":
            if (
                r["unresolved_fields"]
                or kind == "applicability"
                and d["decision_state"] != "APPROVED"
            ):
                raise ValueError("Incomplete draft cannot be effective")
            raise ValueError(
                "Effective status requires an accepted authority/activation record beyond preparation"
            )
        if repository:
            for source in r["source_refs"] + (
                [d["procedure_reference"].split("#")[0]] if d.get("procedure_reference") else []
            ):
                if not (Path(repository) / source).is_file():
                    raise ValueError(f"Missing source/procedure {source}")
    # Bidirectional traceability prevents individually valid but inconsistent graphs.
    for (kind, identifier), r in index.items():
        if kind == "control":
            expected = sorted(
                rid
                for (rk, rid), risk in index.items()
                if rk == "risk" and identifier in risk["data"]["control_ids"]
            )
            if r["data"]["risk_ids"] != expected:
                raise ValueError("Risk/control traceability disagreement")
    for kind, edge in (("implementation", "inherits_from_id"), ("boundary", "parent_id")):
        for k, identifier in index:
            if k != kind:
                continue
            seen, current = set(), identifier
            while current:
                if current in seen:
                    raise ValueError("Inheritance/boundary cycle")
                seen.add(current)
                current = index[k, current]["data"][edge]

    def visit_control(identifier, visiting, visited):
        if identifier in visiting:
            raise ValueError("Control dependency cycle")
        if identifier in visited:
            return
        visiting.add(identifier)
        for parent in index["control", identifier]["data"]["upstream_control_ids"]:
            visit_control(parent, visiting, visited)
        visiting.remove(identifier)
        visited.add(identifier)

    visited = set()
    for kind, identifier in index:
        if kind == "control":
            visit_control(identifier, set(), visited)
    if repository:
        for path, sha in registry["source_manifest"].items():
            if hashlib.sha256((Path(repository) / path).read_bytes()).hexdigest() != sha:
                raise ValueError(f"Source drift: {path}")
    return dict(sorted(Counter(r["kind"] for r in registry["records"]).items()))


def coverage(registry):
    validate(registry)
    implementations = [r for r in registry["records"] if r["kind"] == "implementation"]
    lines = [
        "# CCF preparation coverage",
        "",
        "Derived design inventory; no operating-effectiveness assertion.",
        "",
        "| Domain | Controls | Distinct parents with local designs | Unresolved field entries |",
        "|---|---:|---:|---:|",
    ]
    for domain in sorted(r["id"] for r in registry["records"] if r["kind"] == "domain"):
        controls = [
            r
            for r in registry["records"]
            if r["kind"] == "control" and r["data"]["domain_id"] == domain
        ]
        ids = {r["id"] for r in controls}
        local = {r["data"]["control_id"] for r in implementations} & ids
        lines.append(
            f"| {domain} | {len(ids)} | {len(local)} | {sum(len(r['unresolved_fields']) for r in controls)} |"
        )
    lines += [
        "",
        "Local-design counts do not measure approved applicability, completeness, or effectiveness.",
        "",
        "## Policy disposition",
        "",
        "| Workstream | State | Next work |",
        "|---|---|---|",
    ]
    for r in registry["records"]:
        if r["kind"] == "policy_gap":
            d = r["data"]
            lines.append(f"| {d['title']} | {d['state']} | {d['next_work']} |")
    lines += [
        "",
        "## Unmapped native risk relationships",
        "",
        "These controls have no explicit parent risk in the source traceability matrix. The matrix is partial; no mapping is invented here.",
        "",
    ]
    lines += [
        "- " + r["id"]
        for r in registry["records"]
        if r["kind"] == "control" and not r["data"]["risk_ids"]
    ]
    lines += [
        "",
        "## Local design inventory by boundary",
        "",
        "| Boundary | Local design records |",
        "|---|---:|",
    ]
    for boundary in sorted(r["id"] for r in registry["records"] if r["kind"] == "boundary"):
        lines.append(
            f"| {boundary} | {sum(boundary in r['data']['boundary_ids'] for r in implementations)} |"
        )
    lines += [
        "",
        "One business design can cover multiple boundaries; these counts must not be summed as distinct control definitions.",
    ]
    lines += ["", "## Decision queue", ""]
    for r in registry["records"]:
        if r["kind"] == "decision":
            d = r["data"]
            lines += [
                f"- **{r['id']} — {d['title']}** ({d['owner']}): {d['recommendation']} Blocks: {d['blocks']}. Work that can proceed: {d['can_proceed']}."
            ]
    return "\n".join(lines) + "\n"
