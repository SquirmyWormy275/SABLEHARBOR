"""Explicit engagement semantics and versioned CCF mapping projections."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from enterprise.ccf.assurance.iso import iso_inputs
from enterprise.ccf.assurance.preparation import designs
from enterprise.ccf.registry import compile_registry, digest

from .store import DomainError

ROOT = Path(__file__).resolve().parents[2]

PROGRAMS = [
    {
        "id": "SOC1",
        "label": "SOC 1 — user entities' financial reporting controls",
        "version": "AT-C 320",
        "status": "TRAINING_METHOD",
        "source": "https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater-than-soc-1",
    },
    {
        "id": "SOC2",
        "label": "SOC 2 — Trust Services Criteria",
        "version": "2017 TSC / 2022 points of focus",
        "status": "CANDIDATE_MAPPINGS",
        "source": "https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022",
    },
    {
        "id": "HIPAA",
        "label": "HIPAA — scoped regulatory assessment",
        "version": "45 CFR 164 / source snapshot 2026-09-10",
        "status": "CANDIDATE_MAPPINGS",
        "source": "https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164",
    },
    {
        "id": "ISO27001",
        "label": "ISO/IEC 27001 — ISMS",
        "version": "2022 + Amd 1:2024",
        "status": "CANDIDATE_MAPPINGS",
        "source": "https://www.iso.org/standard/27001",
    },
    {
        "id": "ISO42001",
        "label": "ISO/IEC 42001 — AI management",
        "version": "2023",
        "status": "CANDIDATE_MAPPINGS",
        "source": "https://www.iso.org/standard/42001",
    },
    {
        "id": "C5",
        "label": "BSI C5 — cloud criteria",
        "version": "2026 v1.0.1 / source-pinned English criteria",
        "status": "CANDIDATE_MAPPINGS",
        "source": "https://www.bsi.bund.de/SharedDocs/Downloads/EN/BSI/CloudComputing/ComplianceControlsCatalogue/2026/C5_2026.html",
    },
    {
        "id": "HITRUST",
        "label": "HITRUST — authorized program content required",
        "version": "No authorized complete CSF edition installed",
        "status": "BLOCKED_SOURCE_OR_LICENSE",
        "reason": "The public download has eligibility/use restrictions and contains only "
        "portions of the CSF. An authorized assessment-specific source is required.",
        "source": "https://hitrustalliance.net/legal-agreements",
    },
    {
        "id": "IRAP",
        "label": "IRAP — scoped ISM assessment",
        "version": "ISM OSCAL 2026.09.4",
        "status": "SOURCE_PINNED_SCOPED_REQUIREMENTS",
        "reason": "Publisher non-classified profile; explicit requirement tailoring and "
        "supporting control selection. No automatic CCF equivalence or ASD certification.",
        "source": "https://www.cyber.gov.au/ism/oscal/v2026.09.4",
    },
    {
        "id": "SOC_CYBERSECURITY",
        "label": "SOC for Cybersecurity — enterprise risk management program",
        "version": "Description criteria source not installed",
        "status": "BLOCKED_SOURCE_OR_LICENSE",
        "reason": "The publisher requires account access for the description criteria; "
        "no authorized local copy has been established. SOC 2 description criteria are distinct.",
        "source": "https://www.aicpa-cima.com/resources/download/"
        "get-description-criteria-for-a-cybersecurity-risk-management-program",
    },
    {
        "id": "FINANCIAL",
        "label": "Financial statement audit — explicit jurisdiction",
        "version": "Training methodology 1",
        "status": "TRAINING_METHOD",
        "source": "docs/finance/READER_EXERCISES.md",
    },
]


def validate_scope(scope: dict, discipline: str, *, repository: Path = ROOT) -> dict:
    timezone = scope.get("timezone", "UTC")
    try:
        ZoneInfo(timezone)
    except (TypeError, ValueError, ZoneInfoNotFoundError) as exc:
        raise DomainError("Select a valid IANA assessment timezone") from exc
    if discipline not in {"IT", "FINANCIAL"}:
        raise DomainError("Select IT or Financial discipline")
    programs = scope.get("programs", [])
    if (
        not isinstance(programs, list)
        or not programs
        or len(set(programs)) != len(programs)
        or not set(programs) <= {p["id"] for p in PROGRAMS}
    ):
        raise DomainError("Select supported versioned program packs")
    for program in PROGRAMS:
        if program["id"] in programs and program["status"] in {
            "BLOCKED_SOURCE_OR_LICENSE",
            "SOURCE_AVAILABLE_ADAPTER_IN_PROGRESS",
        }:
            raise DomainError(program["reason"], code=program["status"])
    report = scope.get("report_type")
    if report not in {"Type 1", "Type 2", "Financial statement audit", "Internal assessment"}:
        raise DomainError("Specify engagement/report type")
    if report in {"Type 1", "Type 2"} and not {"SOC1", "SOC2", "C5"}.intersection(programs):
        raise DomainError(
            "Type 1/2 requires a SOC or C5 program; choose an assessment type for other programs"
        )
    try:
        start, end = (
            date.fromisoformat(scope["period_start"]),
            date.fromisoformat(scope["period_end"]),
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise DomainError("Scope requires valid start and end dates") from exc
    if start > end or (end - start).days > 3660:
        raise DomainError("Invalid or excessive engagement period")
    try:
        fieldwork = (
            date.fromisoformat(scope["fieldwork_start"])
            if scope.get("fieldwork_start")
            else end + timedelta(days=1)
        )
    except (ValueError, TypeError, OverflowError) as exc:
        raise DomainError("Fieldwork requires a valid start date") from exc
    if fieldwork < start or (fieldwork - end).days > 3660:
        raise DomainError("Fieldwork must start within the period or within ten years after it")
    if report == "Type 1" and start != end:
        raise DomainError("Type 1 requires one specified assessment date")
    if report == "Type 2" and start == end:
        raise DomainError("Type 2 requires a period, not one assessment date")
    if "C5" in programs and report in {"Type 1", "Type 2"}:
        transition = date(2027, 6, 1)
        if report == "Type 2" and start < transition <= end:
            raise DomainError(
                "This period crosses the C5 transition. The publisher specifies C5:2020 only; "
                "the installed pack is C5:2026. Select a supported period or import the 2020 pack.",
                code="BLOCKED_SOURCE_OR_LICENSE",
            )
        if start < transition and scope.get("c5_early_adoption") is not True:
            raise DomainError("Record explicit early adoption of the installed C5:2026 criteria")
    if report == "Financial statement audit":
        if discipline != "FINANCIAL" or "FINANCIAL" not in programs:
            raise DomainError(
                "A financial statement audit requires the Financial track and program"
            )
        if (
            not scope.get("reporting_basis")
            or not scope.get("accounts")
            or not scope.get("materiality_rationale")
        ):
            raise DomainError(
                "Financial scope requires reporting basis, accounts/assertions "
                "and materiality rationale"
            )
        from .organization import ASSERTIONS, financial_model

        if (
            not isinstance(scope.get("financial_audit_jurisdiction"), str)
            or not scope["financial_audit_jurisdiction"].strip()
        ):
            raise DomainError("Identify the financial audit jurisdiction and methodology")
        accounts = scope["accounts"]
        known_accounts = {row["id"] for row in financial_model(repository)["accounts"]}
        if not isinstance(accounts, list) or any(not isinstance(a, dict) for a in accounts):
            raise DomainError(
                "Accounts must be structured records with assertions and risk rationale"
            )
        if len({a.get("id") for a in accounts}) != len(accounts):
            raise DomainError("Select each financial account once")
        for account in accounts:
            if account.get("id") not in known_accounts:
                raise DomainError(
                    "Financial account must identify its source model and account code"
                )
            assertions = account.get("assertions")
            if (
                not isinstance(assertions, list)
                or not assertions
                or any(not isinstance(a, str) or a not in ASSERTIONS for a in assertions)
                or len(set(assertions)) != len(assertions)
            ):
                raise DomainError("Select distinct relevant assertions for each account")
            for field in ("name", "risk_rationale", "planned_procedures"):
                if not isinstance(account.get(field), str) or not account[field].strip():
                    raise DomainError("Each financial account requires " + field.replace("_", " "))
    native = compile_registry(repository)
    boundaries = scope.get("boundaries", [])
    known = {r["id"] for r in native["records"] if r["kind"] == "boundary"}
    aliases = {"reno": "SITE-RENO", "boise": "SITE-BOISE"}
    # Match canonical runtime names without inventing boundary aliases as IDs.
    for short in ("reno", "boise"):
        found = [
            r["id"]
            for r in native["records"]
            if r["kind"] == "boundary" and short in (r["id"] + " " + r["data"]["title"]).lower()
        ]
        if len(found) == 1:
            aliases[short] = found[0]
    boundaries = [aliases.get(b, b) for b in boundaries]
    if not boundaries or not set(boundaries) <= known or len(set(boundaries)) != len(boundaries):
        raise DomainError("Scope requires distinct known organizational boundaries")
    control_ids = scope.get("control_ids", [])
    known_controls = {r["id"] for r in native["records"] if r["kind"] == "control"}
    if not isinstance(control_ids, list) or not set(control_ids) <= known_controls:
        raise DomainError("Unknown scoped control")
    if "SOC1" in programs:
        for field in ("service_description", "user_entity_financial_reporting"):
            if not isinstance(scope.get(field), str) or not scope[field].strip():
                raise DomainError("SOC 1 requires " + field.replace("_", " "))
        objectives = scope.get("service_control_objectives")
        if (
            not isinstance(objectives, list)
            or not objectives
            or any(not isinstance(item, str) or not item.strip() for item in objectives)
        ):
            raise DomainError("SOC 1 requires explicit service control objectives")
        if not control_ids:
            raise DomainError(
                "Select the controls relevant to the service and user entities' financial reporting"
            )
    if "IRAP" in programs:
        from .programs import ism_tasks

        if not control_ids:
            raise DomainError("Select supporting controls for the scoped ISM system assessment")
        ism_tasks({**scope, "boundaries": boundaries}, repository)
    return {
        **scope,
        "programs": sorted(programs),
        "boundaries": boundaries,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "fieldwork_start": fieldwork.isoformat(),
        "timezone": timezone,
        "temporal_basis": "POINT_IN_TIME" if report == "Type 1" else "PERIOD",
        "control_ids": sorted(set(control_ids)),
        "organization_revision": digest(native),
        "program_versions": {p["id"]: p["version"] for p in PROGRAMS if p["id"] in programs},
        "professional_acceptance": "NOT_ASSERTED",
    }


def control_projection(
    scope: dict, *, repository: Path = ROOT, program_pack: dict | None = None
) -> list[dict]:
    native = compile_registry(repository)
    selected = set(scope["programs"])
    targets = sorted(selected.intersection({"ISO27001", "ISO42001", "C5"}))
    # The upstream compiler requires at least one extension target. Compile its
    # supported superset, then project only explicitly selected requirement links.
    catalog, _ = iso_inputs(native, targets or ["ISO27001", "ISO42001", "C5"])
    mappings = {}
    requirement_frameworks = {r.id: r.framework_id for r in catalog.requirements}
    for mapping in catalog.mappings:
        framework = requirement_frameworks[mapping.requirement_id]
        if framework in selected:
            mappings.setdefault(mapping.control_id, []).append(
                {
                    "requirement_id": mapping.requirement_id,
                    "framework": framework,
                    "status": "CANDIDATE_NOT_PROFESSIONALLY_ACCEPTED",
                }
            )
    requested = set(scope.get("control_ids", []))
    # Financial/SOC1 training includes the native financial and supporting controls;
    # callers may explicitly narrow control IDs after their risk assessment.
    broad = bool(selected.intersection({"SOC1", "FINANCIAL"}))
    baseline_ids = (
        {c["control_id"] for c in designs(native)["controls"]}
        if selected.intersection({"SOC2", "HIPAA"})
        else set()
    )
    packed_controls, packed_actions = {}, {}
    if program_pack:
        if program_pack["native_digest"] != digest(native):
            raise DomainError("Program pack is stale against the native control sources")
        names = (["baseline"] if selected.intersection({"SOC2", "HIPAA"}) else []) + targets
        for name in names:
            projection = program_pack["selections"][name]
            for control in projection["controls"]:
                packed_controls[control["control_id"]] = control
            for action in projection["actions"]:
                links = [r for r in action["requirement_ids"] if r.split(":")[0] in selected]
                if links:
                    old = packed_actions.get(action["id"], {**action, "requirement_ids": []})
                    old["requirement_ids"] = sorted(set(old["requirement_ids"] + links))
                    packed_actions[action["id"]] = old
        baseline_ids.update(packed_controls)
    result = []
    for r in native["records"]:
        if r["kind"] != "control" or (requested and r["id"] not in requested):
            continue
        if not requested and not broad and r["id"] not in mappings and r["id"] not in baseline_ids:
            continue
        result.append(
            {
                "id": r["id"],
                "title": r["data"]["title"],
                "description": r["data"]["statement"],
                "owner_role_id": r["data"]["owner_role_id"],
                "owner_ids": [],
                "frequency": r["data"]["frequency_or_trigger"],
                "evidence_expectation": r["data"]["evidence_expectation"],
                "frameworks": sorted({m["framework"] for m in mappings.get(r["id"], [])}),
                "requirement_links": mappings.get(r["id"], []),
                "source_refs": r["source_refs"],
                "additional_duties": [
                    a for a in packed_actions.values() if r["id"] in a["control_ids"]
                ],
                "procedure": packed_controls.get(r["id"], {}).get("base_procedure"),
                "base_test": packed_controls.get(r["id"], {}).get("base_test"),
                "status": "NOT_TESTED",
                "implementation_version": r["version"],
                "service_control_objectives": scope.get("service_control_objectives", [])
                if "SOC1" in selected
                else [],
                "financial_reporting_relationship": scope.get("user_entity_financial_reporting")
                if "SOC1" in selected
                else None,
            }
        )
    if not result:
        raise DomainError("No controls resolve for the selected scope")
    return sorted(result, key=lambda r: r["id"])
