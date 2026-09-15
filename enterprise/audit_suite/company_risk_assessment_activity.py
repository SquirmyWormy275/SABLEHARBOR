"""Bounded management risk-input reconciliation; no appetite, acceptance or assurance."""

import json
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .company_lifecycle_activity import FIELDS, read_inputs
from .company_lifecycle_activity import LifecycleSourceRef as RiskSourceRef
from .company_store import CompanyStore, CompanyStoreError, _id, _time
from .operating_source_bridge import encoded, sha
from .organization import snapshot
from .private_publication import publish

CONTROL = "SH-ERM-001"
INPUTS = {"EXTERNAL_DEPENDENCY", "INTERNAL_CHANGE"}
GROUPS = {"incident", "provider", "log", "change"}
QUALIFICATION = "LOCAL_QUARTERLY_RISK_ASSESSMENT_NOT_ACCEPTANCE_OR_OPERATING_ASSURANCE"


@dataclass(frozen=True)
class RiskSourceGroup:
    id: str
    source_store_id: str
    source_refs: tuple[RiskSourceRef, ...]
    source_versions_sha256: str


@dataclass(frozen=True)
class RiskScenario:
    id: str
    input_id: str
    management_owner_id: str
    likelihood: int
    impact: int
    projected_likelihood: int
    projected_impact: int
    treatment_proposal: str
    assumption_rationale: str


@dataclass(frozen=True)
class RiskAssessmentRecipe:
    company_id: str
    branch_ids: tuple[str, str]
    source_groups: tuple[RiskSourceGroup, ...]
    scenarios: tuple[RiskScenario, ...]
    period_start: str
    input_at: str
    assessment_at: str
    review_at: str
    correction_at: str
    closeout_at: str
    period_end_exclusive: str
    local_method_basis: str


def score(scenario):
    for value in (
        scenario.likelihood,
        scenario.impact,
        scenario.projected_likelihood,
        scenario.projected_impact,
    ):
        if type(value) is not int or not 1 <= value <= 5:
            raise CompanyStoreError("Ordinal local factors must be integers one to five")
    return {
        "inherent_local_score": scenario.likelihood * scenario.impact,
        "projected_residual_local_score": scenario.projected_likelihood * scenario.projected_impact,
        "method": "LOCAL_ORDINAL_LIKELIHOOD_TIMES_IMPACT_NOT_EMPIRICAL_PROBABILITY",
        "residual_status": "CONDITIONAL_PROJECTION_NOT_DEMONSTRATED",
        "risk_acceptance": "NOT_PERFORMED",
    }


def assess(ledger, scenarios, included_ids):
    """Import only configured ledger inputs; does not infer absent company evidence."""
    if (
        not isinstance(included_ids, list)
        or len(set(included_ids)) != len(included_ids)
        or not set(included_ids) <= set(ledger)
    ):
        raise CompanyStoreError("Distinct declared input selection required")
    return [
        {
            **asdict(s),
            **score(s),
            "input_observations": ledger[s.input_id],
            "treatment_status": "PROPOSED_NOT_IMPLEMENTED_OR_AUTHORIZED",
        }
        for s in scenarios
        if s.input_id in included_ids
    ]


def reconcile_inputs(ledger, assessment):
    actual = {r["input_id"] for r in assessment}
    return {
        "declared_input_ids": sorted(ledger),
        "imported_input_ids": sorted(actual),
        "missing_declared_input_ids": sorted(set(ledger) - actual),
        "unexpected_input_ids": sorted(actual - set(ledger)),
        "basis": "EXPLICIT_LOCAL_INPUT_LEDGER_NOT_ENTERPRISE_RISK_COMPLETENESS",
    }


def _reference(link, row, fields=FIELDS):
    if (
        not isinstance(link, dict)
        or type(link.get("version")) is not int
        or link.get("version") != row["version"]
        or any(link.get(k) != row[k] for k in fields)
    ):
        raise CompanyStoreError("Exact native source linkage required")


def _sources(source_roots, recipe, at):
    if (
        not isinstance(recipe.source_groups, tuple)
        or len(recipe.source_groups) != 4
        or any(not isinstance(g, RiskSourceGroup) for g in recipe.source_groups)
        or {g.id for g in recipe.source_groups} != GROUPS
        or not isinstance(source_roots, dict)
        or set(source_roots) != GROUPS
        or len({g.source_store_id for g in recipe.source_groups}) != 4
    ):
        raise CompanyStoreError("Four explicit distinct source groups and store labels required")
    if len({Path(p).resolve() for p in source_roots.values()}) != 4:
        raise CompanyStoreError("Distinct physical source stores required")
    groups, bodies = {}, {}
    for group in recipe.source_groups:
        _id(group.source_store_id)
        rows, pin = read_inputs(source_roots[group.id], group.source_refs)
        if (
            pin != group.source_versions_sha256
            or len({(r["company"], r["branch"]) for r in rows}) != 1
        ):
            raise CompanyStoreError("Selected source metadata or branch differs")
        for row in rows:
            if (
                row["company"] != recipe.company_id
                or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                or row["event_at"] is None
                or datetime.fromisoformat(_time(row["event_at"])) > at
                or datetime.fromisoformat(_time(row["available_at"])) > at
            ):
                raise CompanyStoreError("Available exact original company sources required")
            value = json.loads(row["content"])
            if not isinstance(value, dict):
                raise CompanyStoreError("Native source object required")
            bodies[group.id, row["system"], row["record"]] = value
        groups[group.id] = (group, rows)

    def select(group, system, record=None):
        rows = [
            r
            for r in groups[group][1]
            if r["system"] == system and (record is None or r["record"] == record)
        ]
        if len(rows) != 1:
            raise CompanyStoreError("One exact source for each declared observation role required")
        row = rows[0]
        return row, bodies[group, system, row["record"]]

    if {g: len(rows) for g, (_, rows) in groups.items()} != {
        "incident": 2,
        "provider": 2,
        "log": 2,
        "change": 3,
    }:
        raise CompanyStoreError("Exactly nine declared reference originals required")
    monitoring_row, monitor = select("incident", "monitoring")
    review_row, incident = select("incident", "postincident_review")
    inventory_row, inventory = select("provider", "planned_dependency_inventory")
    provider_row, provider = select("provider", "vendor_register")
    event_row, publisher = select("log", "publisher_events")
    alert_row, alert = select("log", "detection_alerts")
    gate_row, gate = select("change", "release_gate", "GATE-PROPOSED")
    corrected_row, corrected = select("change", "release_gate", "GATE-CORRECTED")
    release_row, release = select("change", "local_releases", "RELEASE-PROPOSED")
    if (
        incident.get("outage_cause") != "NOT_ESTABLISHED_FROM_PROBE_RECORDS"
        or incident.get("incident_id") != monitor.get("incident_id")
        or monitor.get("origin") != "FICTIONAL_REFERENCE_RUNTIME_ACTIVITY_NOT_PRODUCTION_EVIDENCE"
        or incident.get("origin") != monitor.get("origin")
        or not isinstance(monitor.get("requests"), list)
        or not monitor["requests"]
        or any(
            not isinstance(r, dict) or type(r.get("http_status")) is not int
            for r in monitor["requests"]
        )
    ):
        raise CompanyStoreError("Explicit local probe observations and unknown cause required")
    native_provider = provider.get("provider", {})
    if (
        not isinstance(native_provider, dict)
        or not isinstance(inventory.get("dependencies"), list)
        or native_provider not in inventory["dependencies"]
        or native_provider.get("operating") is not False
        or native_provider.get("contract_executed") is not False
        or native_provider.get("status") != "PROVIDER_SELECTED_PROCUREMENT_PENDING"
    ):
        raise CompanyStoreError("Planned nonoperating provider source required")
    _reference(provider.get("source_inventory"), inventory_row)
    event = publisher.get("event", {})
    _reference(event.get("upstream"), gate_row)
    if (
        event["upstream"].get("source_store_id") != groups["change"][0].source_store_id
        or event.get("authorization_decision") != gate.get("decision")
        or event.get("event_sha256")
        != sha(encoded({k: v for k, v in event.items() if k != "event_sha256"}))
        or alert.get("source_event_sha256") != event.get("event_sha256")
        or alert.get("rule_id") != "LOCAL-AUTHORIZATION-OVERRIDE"
        or gate.get("decision") != "OVERRIDE_USED"
        or gate.get("peer_review") is not None
        or corrected.get("decision") != "ALLOWED"
        or datetime.fromisoformat(_time(corrected_row["event_at"]))
        <= datetime.fromisoformat(_time(gate_row["event_at"]))
    ):
        raise CompanyStoreError(
            "Correlated historical override, alert and later allowed gate required"
        )
    for earlier, later in (
        (monitoring_row, review_row),
        (inventory_row, provider_row),
        (gate_row, event_row),
        (event_row, alert_row),
        (gate_row, release_row),
    ):
        if datetime.fromisoformat(_time(earlier["event_at"])) > datetime.fromisoformat(
            _time(later["event_at"])
        ):
            raise CompanyStoreError("Referenced observation chronology is inconsistent")
    renamed = release.get("gate", {})
    _reference(
        {
            "system": renamed.get("system_id"),
            "record": renamed.get("record_id"),
            "version": renamed.get("version"),
            "sha256": renamed.get("sha256"),
        },
        gate_row,
        ("system", "record", "version", "sha256"),
    )

    def refs(group):
        return [
            {k: r[k] for k in FIELDS} | {"source_store_id": groups[group][0].source_store_id}
            for r in groups[group][1]
        ]

    ledger = {
        "EXTERNAL_DEPENDENCY": {
            "observations": {
                "probe_request_count": len(monitor["requests"]),
                "probe_error_count": sum(r["http_status"] >= 500 for r in monitor["requests"]),
                "incident_cause": incident["outage_cause"],
                "provider_id": native_provider["provider_id"],
                "provider_status": native_provider["status"],
                "provider_operating": False,
                "contract_executed": False,
                "observed_supplier_outage": "NOT_ESTABLISHED",
                "incident_and_provider_observations_are_separate": True,
            },
            "future_scenario": (
                "A future supplier disruption could impair planned runtime or recovery dependency"
            ),
            "scenario_status": "EXPLICIT_LOCAL_HYPOTHESIS_NOT_OBSERVED_SUPPLIER_OUTAGE",
            "source_records": refs("incident") + refs("provider"),
            "native_site_qualifiers": incident["sites"],
            "risk_family": "SH-RISK-TPR-001",
            "affected_controls": ["SH-TPR-001", "SH-BCM-001"],
        },
        "INTERNAL_CHANGE": {
            "observations": {
                "historical_gate_decision": gate["decision"],
                "historical_gate_at": gate_row["event_at"],
                "later_gate_decision": corrected["decision"],
                "later_gate_at": corrected_row["event_at"],
                "alert_rule": alert.get("rule_id"),
                "current_unremediated_failure": "NOT_ESTABLISHED_BY_HISTORICAL_EVENT",
            },
            "future_scenario": (
                "A future unauthorized change could bypass exact-artifact review "
                "and harm service reliability"
            ),
            "scenario_status": "HYPOTHETICAL_RECURRENCE_NOT_CURRENT_UNREMEDIATED_EVENT",
            "source_records": refs("log") + refs("change"),
            "native_site_qualifiers": gate["site_references_only"],
            "risk_family": "SH-RISK-TECH-002",
            "affected_controls": ["SH-ENG-002", "SH-ENG-004"],
        },
    }
    return groups, ledger


def generate_pair(destination, *, repository, source_roots, recipe: RiskAssessmentRecipe):
    destination, repository = Path(destination).absolute(), Path(repository)
    if (
        destination.exists()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(p.is_symlink() for p in (destination, *destination.parents))
        or not isinstance(source_roots, dict)
        or any(
            destination.resolve().is_relative_to(Path(p).resolve()) for p in source_roots.values()
        )
    ):
        raise CompanyStoreError("New private risk output outside original source stores required")
    _id(recipe.company_id)
    if (
        not isinstance(recipe.branch_ids, tuple)
        or len(recipe.branch_ids) != 2
        or len(set(recipe.branch_ids)) != 2
        or not isinstance(recipe.scenarios, tuple)
        or len(recipe.scenarios) != 2
        or any(not isinstance(s, RiskScenario) for s in recipe.scenarios)
        or {s.input_id for s in recipe.scenarios} != INPUTS
        or len({s.id for s in recipe.scenarios}) != 2
    ):
        raise CompanyStoreError(
            "Two branches and distinct explicitly linked local risk scenarios required"
        )
    for value in recipe.branch_ids:
        _id(value)
    for scenario in recipe.scenarios:
        _id(scenario.id)
        _id(scenario.management_owner_id)
        score(scenario)
        for value in (scenario.treatment_proposal, scenario.assumption_rationale):
            if not isinstance(value, str) or not 1 <= len(value.strip()) <= 2000:
                raise CompanyStoreError("Explicit bounded local treatment and assumptions required")
    if (
        not isinstance(recipe.local_method_basis, str)
        or not 1 <= len(recipe.local_method_basis.strip()) <= 2000
    ):
        raise CompanyStoreError("Explicit local risk method required")
    start, input_at, assessment_at, review_at, correction_at, closeout_at, end = [
        datetime.fromisoformat(_time(getattr(recipe, key)))
        for key in (
            "period_start",
            "input_at",
            "assessment_at",
            "review_at",
            "correction_at",
            "closeout_at",
            "period_end_exclusive",
        )
    ]
    if (
        start.month not in (1, 4, 7, 10)
        or start.day != 1
        or start.hour
        or start.minute
        or start.second
        or start.microsecond
        or not start <= input_at < assessment_at < review_at < correction_at < closeout_at < end
        or end
        != start.replace(year=start.year + (start.month == 10), month=(start.month + 2) % 12 + 1)
        or closeout_at.date() != (end - timedelta(days=1)).date()
    ):
        raise CompanyStoreError("One ordered local calendar-quarter refresh required")
    groups, ledger = _sources(source_roots, recipe, input_at)
    org = snapshot(repository, as_of=input_at.date().isoformat())
    assignments = {a["control_id"]: a for a in org["control_assignments"]}
    coordination = assignments[CONTROL]
    coordinator = coordination["primary_person_id"]
    reviewer = coordination["operating_reviewer_person_id"]
    assurance = coordination["reviewer_person_id"]
    expected = {
        "EXTERNAL_DEPENDENCY": assignments["SH-CFG-001"]["primary_person_id"],
        "INTERNAL_CHANGE": assignments["SH-ENG-002"]["primary_person_id"],
    }
    if len({coordinator, reviewer, assurance}) != 3 or any(
        s.management_owner_id != expected[s.input_id]
        or s.management_owner_id in {coordinator, reviewer, assurance}
        for s in recipe.scenarios
    ):
        raise CompanyStoreError(
            "Operating management ownership separate from coordination/review/assurance required"
        )
    pins = dict(org["source_sha256"])
    for name in [
        "docs/governance/ENTERPRISE_SUPPORT_SERVICES_AND_INDEPENDENCE.md",
        "docs/governance/ENTERPRISE_COORDINATION_2026-09-13.md",
        "docs/governance/ASSUMPTION_OF_RISK_DOCTRINE.md",
        "docs/governance/CCF_ENTERPRISE_OBJECTIVES_AND_RISK_UNIVERSE_v0.1.md",
        "enterprise/ccf/assurance/design_data/control_procedures.json",
        "enterprise/audit_suite/company_lifecycle_activity.py",
        "enterprise/audit_suite/company_risk_assessment_activity.py",
    ]:
        pins[name] = sha((repository / name).read_bytes())
    recipe_pin = sha(encoded(asdict(recipe)))
    common = {
        "classification": QUALIFICATION,
        "control_ids": [CONTROL],
        "boundary_id": "corporate",
        "coordinator_id": coordinator,
        "quality_reviewer_id": reviewer,
        "independent_assurance_contact_id": assurance,
        "assurance_activity": "NOT_PERFORMED",
        "role_basis": "EXPLICIT_LOCAL_MANAGEMENT_ASSIGNMENTS_WITH_CANON_COORDINATION_BOUNDARIES",
        "period_start": _time(recipe.period_start),
        "period_end_exclusive": _time(recipe.period_end_exclusive),
        "appetite_status": "NOT_ESTABLISHED",
        "risk_acceptance": "NOT_PERFORMED",
        "board_ratification": "NOT_ASSERTED",
        "signatures": "NONE_CREATED",
        "residual_status": "CONDITIONAL_PROJECTION_NOT_DEMONSTRATED",
        "coverage": "TWO_SELECTED_LOCAL_INPUTS_NOT_ENTERPRISE_RISK_UNIVERSE_COMPLETENESS",
    }
    records = []
    with tempfile.TemporaryDirectory(prefix=".risk-assessment-", dir=destination.parent) as temp:
        stage = Path(temp)
        store = CompanyStore(stage)
        upstream = stage / "upstream"
        upstream.mkdir(mode=0o700)
        source_files = {}
        for group, (_, rows) in groups.items():
            directory = upstream / group
            directory.mkdir(mode=0o700)
            for index, row in enumerate(rows):
                path = directory / f"{index:02d}.json"
                path.write_bytes(row["content"])
                path.chmod(0o600)
                source_files[str(path.relative_to(stage))] = row["sha256"]
        for branch_index, branch in enumerate(recipe.branch_ids):
            for system in [
                "risk_input_ledger",
                "risk_import_configuration",
                "risk_assessments",
                "risk_reconciliation",
                "risk_followup",
                "risk_reviews",
            ]:
                store.register_system(
                    recipe.company_id,
                    branch,
                    system,
                    reviewer if system in {"risk_reconciliation", "risk_reviews"} else coordinator,
                )
            versions = {}
            history = []

            def add(system, record, at, body, *, branch=branch, versions=versions, history=history):
                prior = versions.get((system, record), 0)
                raw = encoded(
                    {
                        **common,
                        **body,
                        "record_id": record,
                        "recorded_at": _time(at.isoformat()),
                        "previous_events": list(history),
                    }
                )
                row = store.append_version(
                    recipe.company_id,
                    branch,
                    system,
                    record,
                    expected_version=prior,
                    command_id=sha(encoded([recipe_pin, branch, system, record, prior + 1])),
                    event_at=_time(at.isoformat()),
                    available_at=_time(at.isoformat()),
                    content=raw,
                    provenance={
                        "name": record + ".json",
                        "source_reference": record,
                        "control_ids": [CONTROL],
                        "classification": QUALIFICATION,
                        "operational_fact_status": "COMPUTED_LOCAL_REFERENCE_ONLY",
                        "recipe_sha256": recipe_pin,
                        "source_sha256": pins,
                    },
                )
                versions[system, record] = prior + 1
                records.append(row)
                history.append({k: row[k] for k in ("system", "record", "version", "sha256")})

            add(
                "risk_input_ledger",
                "INPUT-LEDGER",
                input_at,
                {
                    "inputs": ledger,
                    "method_basis": recipe.local_method_basis,
                    "management_owners": {
                        s.input_id: s.management_owner_id for s in recipe.scenarios
                    },
                    "assumed_risk_scenarios": [asdict(s) for s in recipe.scenarios],
                    "likelihood_basis": "LOCAL_ASSUMPTION_NOT_INFERRED_FROM_SINGLE_OBSERVATION",
                },
            )
            selected = sorted(INPUTS) if branch_index == 0 else ["EXTERNAL_DEPENDENCY"]
            add(
                "risk_import_configuration",
                "IMPORT-CONFIG",
                assessment_at,
                {"included_input_ids": selected},
            )
            assessment = assess(ledger, recipe.scenarios, selected)
            add(
                "risk_assessments",
                "ASSESSMENT",
                assessment_at,
                {"risks": assessment, "prepared_by": coordinator},
            )
            comparison = reconcile_inputs(ledger, assessment)
            add("risk_reconciliation", "INPUT-CHECK", review_at, comparison)
            add(
                "risk_reviews",
                "QUALITY-REVIEW",
                review_at,
                {
                    **comparison,
                    "reviewed_by": reviewer,
                    "review_purpose": "INPUT_COMPLETENESS_AND_RECORD_QUALITY_NOT_RISK_ACCEPTANCE",
                },
            )
            add(
                "risk_followup",
                "FOLLOWUP",
                review_at,
                {
                    "requested_backfill_ids": comparison["missing_declared_input_ids"],
                    "assigned_to": coordinator,
                    "management_owners_unchanged": True,
                },
            )
            selected = sorted(set(selected) | set(comparison["missing_declared_input_ids"]))
            add(
                "risk_import_configuration",
                "IMPORT-CONFIG",
                correction_at,
                {
                    "included_input_ids": selected,
                    "change_basis": (
                        "Explicit reconciliation backfill; no risk acceptance"
                        if comparison["missing_declared_input_ids"]
                        else "Reaffirmed unchanged input selection; no backfill or risk acceptance"
                    ),
                },
            )
            assessment = assess(ledger, recipe.scenarios, selected)
            add(
                "risk_assessments",
                "ASSESSMENT",
                correction_at,
                {
                    "risks": assessment,
                    "prepared_by": coordinator,
                    "prior_assessment_preserved": True,
                },
            )
            final = reconcile_inputs(ledger, assessment)
            add("risk_reconciliation", "INPUT-CHECK", closeout_at, final)
            add(
                "risk_reviews",
                "QUALITY-CLOSEOUT",
                closeout_at,
                {
                    **final,
                    "reviewed_by": reviewer,
                    "review_purpose": "LOCAL_DECLARED_INPUT_RECONCILIATION_ONLY",
                },
            )
        for group in recipe.source_groups:
            if (
                read_inputs(source_roots[group.id], group.source_refs)[1]
                != group.source_versions_sha256
            ):
                raise CompanyStoreError("Selected upstream source changed during risk refresh")
        result = {
            "status": "LOCAL_RISK_REFRESH_CREATED",
            "qualification": QUALIFICATION,
            "recipe": asdict(recipe),
            "recipe_sha256": recipe_pin,
            "source_sha256": pins,
            "source_metadata": {
                g: [{k: v for k, v in row.items() if k != "content"} for row in rows]
                for g, (_, rows) in groups.items()
            },
            "upstream_files": source_files,
            "records": records,
            "coordination_assignment": coordination,
            "management_owner_bindings": expected,
            "snapshot_isolation": "PER_SOURCE_NOT_GLOBAL",
            "audit_created": False,
            "grants_created": False,
        }
        path = stage / "SOURCE_RECEIPT.json"
        path.write_bytes(encoded(result))
        path.chmod(0o600)
        publish(stage, destination)
    return result
