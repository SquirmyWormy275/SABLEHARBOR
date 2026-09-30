"""Selected fictional 2027 SVC-compute security operation, never real network I/O."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import tempfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from . import company_runtime_transition_exercise as transition
from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_SEC005_SELECTED_OPERATIONS_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
BRANCHES = {"CLEAN": "SEC005-OPERATED-CLEAN", "MESSY": "SEC005-OPERATED-MESSY"}
SPEC = "enterprise/audit_suite/sec005_operated_2027_spec_v1.json"
SOURCE_REFERENCE = "enterprise/audit_suite/company_sec005_operated_2027.py"
ROUTE_REVIEW = (
    "enterprise/generated/audit-suite/documentary-283-route-reconciliation-v3-2026-09-29/"
    "independent-review-v1/REVIEW.json"
)
ROUTE_REVIEW_SHA = "b671d3547670b5de9c7f714d51e44b6d2e65b02502dac752464b9f36d7ca1603"
TRANSITION_PINS = {
    "MANIFEST.json": "f7c6ec3ab460f204f69cf6b50df66399687034b3b63cb38aaee84841daedcbd4",
    "RECEIPT.json": "0a0a448f619e490870f69959d196eb6d5ca3747af0d4fb68056195910ce6cc11",
    "company.sqlite3": "428b5c740cb8fc627b38f2aa6847e450fd166e62be52a6309d4f5a7b284988fd",
}
TRANSITION_REVIEW_SHA = "f1acaeaea963055f99b0de120fd1b0347ee984edf085d353e7af1e427234d5a9"
SOURCE_PINS = {
    SPEC: "a1d848d411679159287c13f98f21ed87ef4641375a75262696472c1160ff4216",
    "docs/canon/RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md": (
        "fd309a9bdf596ea96498b7207b60ea3bea70a35d8c418371aa96c06d928bb17b"
    ),
    "docs/canon/THIRD_PARTY_SERVICES_SOURCING_DECISIONS_2026-09-09.md": (
        "53dc3c69be68cd66fe9fdd30048f8229416fd6bd6660272dfeae20f802f986d4"
    ),
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md": (
        "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496"
    ),
    "docs/internal/development/audit-suite/ORGANIZATION_APPOINTMENT_PROPOSALS_2026-09-13.json": (
        "53681cf60e85d130d04ef79ed437e70da9b3211896e2098f049bc9ff26f54681"
    ),
    "docs/organization/source/chartbook.json": (
        "6ba4f1ed1a14581455a62c3e79a29ca59dbaf1270dfb0db850c0376c15507b49"
    ),
    "docs/governance/BOARD_AND_CAPITAL_GOVERNANCE_v1.0.1.md": (
        "dc1e2e3ea6e7ea8d364eae87bd890a8c79a5a577a7554ed371cda3810ea945a8"
    ),
    "enterprise/services/source/services.json": (
        "f9cd08b7add29b7be6c51670bf0c92bcca4b582e9853d83d25d518171da75818"
    ),
    "enterprise/services/source/components.json": (
        "0d5e1fefa3e3286cae725a4b04241725fc2590dff4ccbdc7fde41a24740a0cd2"
    ),
    "enterprise/services/source/runtime_sites_2026-09-11.json": (
        "fa216f629762503865fd9f1a3207e87691cd484cec9885bf25ce045b4525519c"
    ),
    "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V3_2026-09-29.json": (
        "f7549eca0957a92d442cfabb385ae9eed4509fada804a3dfea5d371cfbbf4d33"
    ),
}
AUTHORED = {
    "CHECK-SOC2:CC6.6": (
        "Test approved ingress/egress paths, remote administration and boundary defenses "
        "against an unauthorized connection; reconcile rules to actual external interfaces."
    ),
    "CHECK-SOC2:CC6.8": (
        "Inspect installation restrictions, update coverage and detection response on "
        "representative assets; test an unapproved executable and exception path."
    ),
}
SYSTEM_OWNERS = {
    "security_authority": "AS-P007",
    "security_approval": "AS-P008",
    "security_inventory": "AS-P007",
    "security_baseline": "AS-P007",
    "security_application": "AS-P007",
    "security_probe": "AS-P007",
    "security_monitor": "AS-P007",
    "security_reconciliation": "AS-P008",
    "security_exception": "AS-P008",
}
LIMITS = [
    "Fictional 2027 company-operated selected SVC-compute footprint; actual import is in 2026.",
    "Four declared assets and six logical interfaces are this selected population, not the estate.",
    "Transition V3 release is prerequisite; 2026 canon and real provider state stay unchanged.",
    "P001 CEO identity/title is canon; this 2027 technical delegation is fictional and bounded.",
    "AS-P contacts are proposed; selected managed nodes establish no real device title.",
    "Probes are deterministic data-only evaluations; no socket, packet, executable, secret or PHI.",
    "October/November snapshots do not establish full-year monitoring or task sufficiency.",
    "No actual deployment, external communication, audit task credit, P1/Key/Atlas mutation.",
]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private(path: Path, *, directory: bool) -> Path:
    path = Path(path).absolute()
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise CompanyStoreError("Private alias forbidden")
    info = path.stat()
    if directory:
        if not path.is_dir() or stat.S_IMODE(info.st_mode) != 0o700:
            raise CompanyStoreError("Private 0700 directory required")
    elif (
        not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600
    ):
        raise CompanyStoreError("Private 0600 regular file required")
    return path


def _frozen(paths: dict[str, Path]) -> dict[str, tuple]:
    for path in paths.values():
        if path.name == "company.sqlite3" and any(
            Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
            for suffix in ("-wal", "-shm", "-journal")
        ):
            raise CompanyStoreError("Frozen native DB has sidecar")
    result = {}
    for name, path in paths.items():
        _private(path, directory=False)
        info = path.stat()
        result[name] = (
            info.st_dev,
            info.st_ino,
            stat.S_IMODE(info.st_mode),
            info.st_size,
            info.st_mtime_ns,
            _digest(path),
        )
    return result


def _route_authority(repository: Path, private_repository: Path) -> dict:
    review = private_repository / ROUTE_REVIEW
    _private(review, directory=False)
    if _digest(review) != ROUTE_REVIEW_SHA:
        raise CompanyStoreError("SEC-005 reviewed route receipt differs")
    review_data = json.loads(review.read_text())
    ledger_path = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V3_2026-09-29.json"
    if (
        review_data.get("verdict") != "PASS_READ_ONLY_PARTIAL_ROUTE_RECONCILIATION"
        or review_data.get("tracked_sha256", {}).get("ledger_json") != SOURCE_PINS[ledger_path]
    ):
        raise CompanyStoreError("SEC-005 route review is not accepted")
    ledger = json.loads((repository / ledger_path).read_text())
    expected_ids = {
        f"TASK-SH-SEC-005-corporate-{suffix}"
        for suffix in (*AUTHORED, "IMPLEMENTATION", "TOD", "TOE")
    }
    result = {}
    for side in "AB":
        rows = {
            row["task_id"]: row
            for row in ledger["rows"]
            if row["side"] == side and row["control_id"] == "SH-SEC-005"
        }
        if len(rows) != 5 or set(rows) != expected_ids:
            raise CompanyStoreError("Exact five SEC-005 routes differ")
        for task_id, row in rows.items():
            suffix = task_id.removeprefix("TASK-SH-SEC-005-corporate-")
            authored = suffix in AUTHORED
            if (
                row["authored_test_clause"] != (AUTHORED[suffix] if authored else None)
                or row["classification"]
                != ("UNSUPPORTED_EXACT_CLAUSE" if authored else "DESIGN_CONTEXT_ONLY")
                or row["procedure_type"] != ("ADDITIONAL_DUTY" if authored else suffix)
                or row["current_status"] != "NOT_STARTED"
                or row["current_conclusion"] != "NOT_RUN"
                or row["audit_task_credit"] is not False
                or row["actual_operation_eligibility_as_of_packet"] is not False
            ):
                raise CompanyStoreError("SEC-005 route clause/status/credit differs")
        result[side] = {"task_ids": sorted(rows), "authored_unsupported": 2, "inferred": 3}
    if result["A"] != result["B"]:
        raise CompanyStoreError("Paired SEC-005 route authority differs")
    return result


def _transition_context(repository: Path, root: Path) -> dict:
    root = _private(root, directory=True)
    paths = {name: root / name for name in TRANSITION_PINS}
    before = _frozen(paths)
    if {name: item[-1] for name, item in before.items()} != TRANSITION_PINS:
        raise CompanyStoreError("Reviewed transition V3 bytes differ")
    review_path = root.parent / "independent-review-v3/REVIEW.json"
    _private(review_path, directory=False)
    if _digest(review_path) != TRANSITION_REVIEW_SHA:
        raise CompanyStoreError("Reviewed transition V3 verdict differs")
    review = json.loads(review_path.read_text())
    if review.get("verdict") != "PASS_PRIVATE_FICTIONAL_SOURCE_FOR_INTEGRATION_REVIEW":
        raise CompanyStoreError("Transition V3 independent review is not PASS")
    transition.verify(root, repository=repository)
    receipt = json.loads(paths["RECEIPT.json"].read_text())
    if (
        receipt.get("schema") != "SH_FICTIONAL_2027_RUNTIME_TRANSITION_V3"
        or receipt.get("qualification") != transition.QUALIFICATION
    ):
        raise CompanyStoreError("Transition V3 source qualification differs")
    releases = {}
    for scenario in BRANCHES:
        found = {
            row["record"]: row
            for row in receipt["records"][scenario]
            if row["system"] == "site_release"
        }
        if set(found) != {"RL-RENO", "RL-BOISE"}:
            raise CompanyStoreError("Transition V3 site release population differs")
        releases[scenario] = {
            site: {
                key: found[record][key]
                for key in (
                    "company",
                    "branch",
                    "system",
                    "record",
                    "version",
                    "sha256",
                    "event_at",
                    "available_at",
                    "imported_at",
                )
            }
            for site, record in (("RENO", "RL-RENO"), ("BOISE", "RL-BOISE"))
        }
        if any(ref["available_at"] >= "2027-09-01" for ref in releases[scenario].values()):
            raise CompanyStoreError("SEC-005 operation precedes fictional site release")
    if _frozen(paths) != before:
        raise CompanyStoreError("Transition source changed during read")
    return releases


def _context(repository: Path, private_repository: Path, transition_root: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    for name, digest in SOURCE_PINS.items():
        path = repository / name
        if path.is_symlink() or not path.is_file() or _digest(path) != digest:
            raise CompanyStoreError("Pinned SEC-005 operated input differs")
    spec = json.loads((repository / SPEC).read_text())
    assets = spec["assets"]
    interfaces = spec["logical_interfaces"]
    rule_ids = {item["id"] for item in interfaces}
    if (
        spec["schema"] != "SH_FICTIONAL_2027_SEC005_SELECTED_OPERATIONS_SPEC_V1"
        or spec["qualification"]
        != "FICTIONAL_COMPANY_OPERATED_2027_SELECTED_POPULATION_NO_REAL_DEPLOYMENT"
        or spec["company"] != COMPANY
        or spec["service_id"] != "SVC-compute"
        or len(assets) != 4
        or len({item["id"] for item in assets}) != 4
        or {item["site"] for item in assets} != {"RUNTIME-RENO-COLO", "RUNTIME-BOISE-DR"}
        or len(interfaces) != 6
        or len(rule_ids) != 6
        or set(spec["approved_rule_intents"]) != rule_ids
        or any(item["asset_id"] not in {asset["id"] for asset in assets} for item in interfaces)
        or any(
            spec[field]
            for field in (
                "real_network_packets",
                "real_executable_bytes_or_runs",
                "real_deployment",
                "actual_phi",
                "audit_task_credit",
            )
        )
        or spec["delegation"]["real_corporate_delegation"] is not False
        or spec["delegation"]["issuer_person_id"] != "P001"
        or spec["delegation"]["issuer_name"] != "Daniel Mercer"
        or spec["delegation"]["issuer_title"] != "Chief Executive Officer"
        or spec["delegation"]["grantee_person_id"] != "AS-P007"
        or spec["delegation"]["security_reviewer_person_id"] != "AS-P008"
        or spec["delegation"]["effective_at"] != "2027-09-01T10:00:00+00:00"
        or spec["selected_period_start"] != "2027-09-06T10:01:00+00:00"
        or spec["selected_period_end"] != "2027-11-30T23:59:59+00:00"
        or spec["delegation"]["expires_at"] <= spec["selected_period_end"]
        or spec["unauthorized_egress_intent"] in spec["approved_rule_intents"]["IF-BOI-EGRESS"]
        or spec["unauthorized_admin_intent"] in spec["approved_rule_intents"]["IF-RNO-ADMIN"]
        or spec["inert_unapproved_executable_manifest"]["digest_sha256"]
        != sha(spec["inert_unapproved_executable_manifest"]["digest_basis_text"].encode())
    ):
        raise CompanyStoreError("Selected operated SEC-005 specification differs")
    chartbook = json.loads((repository / "docs/organization/source/chartbook.json").read_text())
    ceo = [node for node in chartbook["nodes"] if node.get("id") == "P001"]
    if (
        len(ceo) != 1
        or ceo[0].get("person_id") != spec["delegation"]["issuer_person_id"]
        or ceo[0].get("name") != spec["delegation"]["issuer_name"]
        or ceo[0].get("title") != spec["delegation"]["issuer_title"]
        or spec["asset_custody_limit"]
        != "Fictional company-managed selected nodes; no real device title or inventory assertion"
        or {item["kind"] for item in assets if item["id"].endswith("EDGE-01")}
        != {"SABLE_HARBOR_MANAGED_EDGE_POLICY_NODE"}
    ):
        raise CompanyStoreError("Canon CEO or selected asset custody boundary differs")
    sites = json.loads(
        (repository / "enterprise/services/source/runtime_sites_2026-09-11.json").read_text()
    )["sites"]
    if {
        site["id"]: (site["status"], site["contract_executed"], site["operating"])
        for site in sites
        if site["id"] in {"RUNTIME-RENO-COLO", "RUNTIME-BOISE-DR"}
    } != {
        site: ("PROVIDER_SELECTED_PROCUREMENT_PENDING", False, False)
        for site in ("RUNTIME-RENO-COLO", "RUNTIME-BOISE-DR")
    }:
        raise CompanyStoreError("2026 canon site state differs")
    services = json.loads((repository / "enterprise/services/source/services.json").read_text())
    if sum(row[0] == "SVC-compute" for row in services["services"]) != 1:
        raise CompanyStoreError("Selected company service differs")
    appointment_path = (
        "docs/internal/development/audit-suite/ORGANIZATION_APPOINTMENT_PROPOSALS_2026-09-13.json"
    )
    appointments = json.loads((repository / appointment_path).read_text())
    if appointments["repository_acceptance_status"] != "PROPOSED_NOT_ACCEPTED_CANON" or not {
        "AS-P007",
        "AS-P008",
    } <= {person["person_id"] for person in appointments["people"]}:
        raise CompanyStoreError("Proposed scenario contacts differ")
    return {
        "spec": spec,
        "routes": _route_authority(repository, private_repository),
        "releases": _transition_context(repository, transition_root),
    }


def evaluate_boundary(rules: dict[str, list[str]], interface_id: str, intent: str) -> str:
    """Evaluate a declared fictional rule in memory; never open a network interface."""
    if interface_id not in rules:
        raise CompanyStoreError("Selected logical interface not declared")
    return "WOULD_ALLOW_DATA_ONLY" if intent in rules[interface_id] else "DENIED_DATA_ONLY"


def evaluate_endpoint(covered_assets: list[str], asset_id: str) -> str:
    """Evaluate metadata-only unapproved executable policy, without executable bytes."""
    return (
        "DENIED_UNAPPROVED_MANIFEST_DATA_ONLY"
        if asset_id in covered_assets
        else "NO_POLICY_DECISION_COVERAGE_NO_EXECUTION"
    )


def _rows(context: dict, scenario: str) -> list[dict]:
    if scenario not in BRANCHES:
        raise CompanyStoreError("Unknown SEC-005 operated branch")
    spec = context["spec"]
    messy = scenario == "MESSY"
    baseline = spec["approved_rule_intents"]
    selected_assets = [item["id"] for item in spec["assets"]]
    selected_interfaces = [item["id"] for item in spec["logical_interfaces"]]
    degraded_rules = {key: list(values) for key, values in baseline.items()}
    degraded_rules["IF-BOI-EGRESS"].append(spec["unauthorized_egress_intent"])
    degraded_coverage = [x for x in selected_assets if x != "SIM-BOI-OPS-01"]
    releases = context["releases"][scenario]
    rows: list[dict] = []
    refs: dict[str, dict] = {}
    previous = None

    def emit(
        system: str,
        record: str,
        at: str,
        actor: str,
        body: dict,
        depends: tuple[str, ...] = (),
    ) -> dict:
        nonlocal previous
        event = _time(at)
        available = _time((datetime.fromisoformat(event) + timedelta(minutes=1)).isoformat())
        if previous and previous["available_at"] >= event:
            raise CompanyStoreError("SEC-005 business event predates predecessor availability")
        if any(record_id not in refs for record_id in depends):
            raise CompanyStoreError("SEC-005 native predecessor is missing")
        content = {
            "qualification": spec["qualification"],
            "scenario": scenario,
            "company": COMPANY,
            "service_id": spec["service_id"],
            "selected_period_start": _time(spec["selected_period_start"]),
            "selected_period_end": _time(spec["selected_period_end"]),
            "system": system,
            "record": record,
            "event_at": event,
            "available_at": available,
            "actor_id": actor,
            "source_previous": previous,
            "source_refs": {key: refs[key] for key in depends},
            "actual_network_packets": 0,
            "actual_executable_bytes_or_runs": 0,
            "real_deployment": False,
            "actual_phi": False,
            "real_corporate_authority": False,
            "audit_task_credit": False,
            **body,
        }
        raw = encoded(content)
        row = {
            "system": system,
            "record": record,
            "version": 1,
            "event_at": event,
            "available_at": available,
            "sha256": sha(raw),
            "content": raw,
        }
        rows.append(row)
        previous = {
            key: row[key]
            for key in ("system", "record", "version", "sha256", "event_at", "available_at")
        }
        refs[record] = previous
        return previous

    emit(
        "security_authority",
        spec["delegation"]["record_id"],
        spec["delegation"]["effective_at"],
        "P001",
        {
            "action": "BOUNDED_FICTIONAL_TECHNICAL_DELEGATION",
            "delegation": spec["delegation"],
            "selected_asset_ids": selected_assets,
            "selected_interface_ids": selected_interfaces,
            "asset_custody_limit": spec["asset_custody_limit"],
            "upstream_site_release_refs": releases,
            "authority_limit": "SCENARIO_ONLY_NOT_BOARD_APPETITE_OR_REAL_APPOINTMENT",
        },
    )
    emit(
        "security_approval",
        "APPROVE-TECH-01",
        "2027-09-02T10:00:00+00:00",
        "AS-P007",
        {
            "action": "FICTIONAL_TECHNOLOGY_SELECTED_BASELINE_APPROVAL",
            "decision": "APPROVED_FOR_DECLARED_FOUR_ASSETS_SIX_INTERFACES",
            "coverage": {"assets": selected_assets, "interfaces": selected_interfaces},
        },
        (spec["delegation"]["record_id"],),
    )
    emit(
        "security_approval",
        "APPROVE-SEC-01",
        "2027-09-03T10:00:00+00:00",
        "AS-P008",
        {
            "action": "DISTINCT_FICTIONAL_SECURITY_SELECTED_BASELINE_APPROVAL",
            "decision": "APPROVED_FOR_DECLARED_SELECTED_SCOPE",
            "technology_approver_person_id": "AS-P007",
            "security_reviewer_person_id": "AS-P008",
        },
        ("APPROVE-TECH-01",),
    )
    emit(
        "security_inventory",
        "INVENTORY-SELECTED-01",
        "2027-09-04T10:00:00+00:00",
        "AS-P007",
        {
            "action": "FICTIONAL_COMPANY_SELECTED_ASSET_AND_INTERFACE_INVENTORY",
            "assets": spec["assets"],
            "logical_interfaces": spec["logical_interfaces"],
            "population_complete_only_for_selected_footprint": True,
            "upstream_site_release_refs": releases,
        },
        ("APPROVE-TECH-01", "APPROVE-SEC-01"),
    )
    emit(
        "security_baseline",
        "BASELINE-01",
        "2027-09-05T10:00:00+00:00",
        "AS-P007",
        {
            "action": "FICTIONAL_SELECTED_NETWORK_AND_ENDPOINT_BASELINE",
            "approved_rule_intents": baseline,
            "selected_asset_ids": selected_assets,
            "agent_required_asset_ids": selected_assets,
            "unapproved_manifest_sha256": spec["inert_unapproved_executable_manifest"][
                "digest_sha256"
            ],
            "default_for_unlisted_intent": "DENY",
            "approval_status": "FICTIONAL_TECHNOLOGY_AND_SECURITY_APPROVED",
        },
        ("INVENTORY-SELECTED-01", "APPROVE-TECH-01", "APPROVE-SEC-01"),
    )
    emit(
        "security_application",
        "APPLY-BASELINE-01",
        "2027-09-06T10:00:00+00:00",
        "AS-P007",
        {
            "action": "FICTIONAL_COMPANY_SELECTED_CONFIG_APPLIED",
            "applied_rule_intents": baseline,
            "agent_covered_asset_ids": selected_assets,
            "site_release_gate_satisfied": True,
            "real_device_write": False,
        },
        ("BASELINE-01", "APPROVE-SEC-01"),
    )
    active_rules = baseline
    covered = selected_assets
    config_record = "APPLY-BASELINE-01"
    coverage_record = "APPLY-BASELINE-01"
    if messy:
        emit(
            "security_application",
            "DRIFT-BOI-EGRESS-01",
            "2027-10-03T10:00:00+00:00",
            "AS-P007",
            {
                "action": "FICTIONAL_APPLIED_RULE_DRIFT_WITHOUT_CHANGE_APPROVAL",
                "affected_asset_id": "SIM-BOI-EDGE-01",
                "affected_interface_id": "IF-BOI-EGRESS",
                "applied_rule_intents": degraded_rules,
                "approved_change_record_id": None,
                "real_device_write": False,
            },
            ("APPLY-BASELINE-01", "BASELINE-01"),
        )
        emit(
            "security_application",
            "AGENT-COVERAGE-LOSS-01",
            "2027-10-04T10:00:00+00:00",
            "AS-P007",
            {
                "action": "FICTIONAL_MANAGED_ENDPOINT_AGENT_HEARTBEAT_MISSING",
                "affected_asset_id": "SIM-BOI-OPS-01",
                "agent_covered_asset_ids": degraded_coverage,
                "coverage_status": "THREE_OF_FOUR_SELECTED_ASSETS",
                "real_device_write": False,
            },
            ("DRIFT-BOI-EGRESS-01", "INVENTORY-SELECTED-01"),
        )
        active_rules = degraded_rules
        covered = degraded_coverage
        config_record = "DRIFT-BOI-EGRESS-01"
        coverage_record = "AGENT-COVERAGE-LOSS-01"
    intent = spec["unauthorized_egress_intent"]
    egress = evaluate_boundary(active_rules, "IF-BOI-EGRESS", intent)
    emit(
        "security_probe",
        "OCT-APPROVED-EGRESS-01",
        "2027-10-05T09:00:00+00:00",
        "AS-P007",
        {
            "action": "DATA_ONLY_APPROVED_INTENT_PROBE",
            "interface_id": "IF-RNO-EGRESS",
            "intent": "NONPERSONAL-METADATA-SERVICE",
            "decision": evaluate_boundary(
                active_rules, "IF-RNO-EGRESS", "NONPERSONAL-METADATA-SERVICE"
            ),
            "effect": "NO_NETWORK_IO",
        },
        (config_record, "INVENTORY-SELECTED-01"),
    )
    emit(
        "security_probe",
        "OCT-UNAUTHORIZED-EGRESS-01",
        "2027-10-05T09:10:00+00:00",
        "AS-P007",
        {
            "action": "DATA_ONLY_UNAUTHORIZED_EGRESS_PROBE",
            "interface_id": "IF-BOI-EGRESS",
            "intent": intent,
            "decision": egress,
            "effect": "NO_NETWORK_IO_EVEN_IF_RULE_WOULD_ALLOW",
            "config_drift_present": messy,
        },
        (config_record, "BASELINE-01"),
    )
    emit(
        "security_probe",
        "OCT-UNAUTHORIZED-ADMIN-01",
        "2027-10-05T09:20:00+00:00",
        "AS-P007",
        {
            "action": "DATA_ONLY_UNAUTHORIZED_REMOTE_ADMIN_PROBE",
            "interface_id": "IF-RNO-ADMIN",
            "intent": spec["unauthorized_admin_intent"],
            "decision": evaluate_boundary(
                active_rules, "IF-RNO-ADMIN", spec["unauthorized_admin_intent"]
            ),
            "effect": "NO_NETWORK_IO_OR_AUTHENTICATION_ATTEMPT",
        },
        (config_record, "INVENTORY-SELECTED-01"),
    )
    emit(
        "security_probe",
        "OCT-UNAPPROVED-EXEC-01",
        "2027-10-05T09:30:00+00:00",
        "AS-P007",
        {
            "action": "DATA_ONLY_UNAPPROVED_EXECUTABLE_MANIFEST_PROBE",
            "asset_id": "SIM-BOI-OPS-01",
            "manifest": spec["inert_unapproved_executable_manifest"],
            "decision": evaluate_endpoint(covered, "SIM-BOI-OPS-01"),
            "effect": "NO_EXECUTABLE_BYTES_INSTALL_OR_RUN",
        },
        (coverage_record, "BASELINE-01"),
    )
    oct_probes = (
        "OCT-APPROVED-EGRESS-01",
        "OCT-UNAUTHORIZED-EGRESS-01",
        "OCT-UNAUTHORIZED-ADMIN-01",
        "OCT-UNAPPROVED-EXEC-01",
    )
    received = (
        ["OCT-APPROVED-EGRESS-01", "OCT-UNAUTHORIZED-ADMIN-01"] if messy else list(oct_probes)
    )
    emit(
        "security_monitor",
        "MONITOR-OCT-01",
        "2027-10-06T10:00:00+00:00",
        "AS-P007",
        {
            "action": "FICTIONAL_SELECTED_MONITOR_COLLECTOR_SNAPSHOT",
            "received_probe_record_ids": received,
            "observed_agent_asset_ids": covered,
            "publisher_population_reconciled_at_collection": not messy,
            "collector_filter": "OMITS_TWO_ADVERSE_DECISIONS"
            if messy
            else "ALL_SELECTED_DECISIONS",
            "actual_external_log_source": False,
            **({"publisher_probe_record_ids": list(oct_probes)} if not messy else {}),
        },
        oct_probes if not messy else tuple(received),
    )
    emit(
        "security_reconciliation",
        "RECON-OCT-01",
        "2027-10-07T10:00:00+00:00",
        "AS-P008",
        {
            "action": "FICTIONAL_SELECTED_OCTOBER_RECONCILIATION",
            "reviewed_asset_ids": degraded_coverage if messy else selected_assets,
            "reviewed_interface_ids": selected_interfaces[:5] if messy else selected_interfaces,
            "reviewed_probe_record_ids": received,
            "recorded_result": (
                "RECORDED_PASS_ON_INCOMPLETE_INPUTS" if messy else "SELECTED_LOCAL_RECONCILED"
            ),
            "population_basis": (
                "STALE_COLLECTOR_REPORT_NOT_RECONCILED_TO_NATIVE_INVENTORY"
                if messy
                else "NATIVE_SELECTED_INVENTORY_AND_PUBLISHER_RECONCILED"
            ),
            "reviewed_native_selected_inventory": not messy,
        },
        ("MONITOR-OCT-01",) if messy else ("MONITOR-OCT-01", "INVENTORY-SELECTED-01"),
    )
    emit(
        "security_reconciliation",
        "INDEPENDENT-NOV-01",
        "2027-11-05T10:00:00+00:00",
        "AS-P008",
        {
            "action": "INDEPENDENT_SELECTED_POPULATION_AND_SOURCE_REPERFORMANCE",
            "selected_asset_ids": selected_assets,
            "selected_interface_ids": selected_interfaces,
            "actual_october_publisher_ids": list(oct_probes),
            "october_collector_ids": received,
            "late_missing_publisher_ids": sorted(set(oct_probes) - set(received)),
            "late_rule_drift_found": messy,
            "late_endpoint_agent_gap_found": messy,
            "october_reconciliation_invalid": messy,
            "finding_count": 2 if messy else 0,
        },
        ("RECON-OCT-01", "INVENTORY-SELECTED-01", *oct_probes, config_record, coverage_record),
    )
    if messy:
        emit(
            "security_exception",
            "EXC-SEC005-Q4-01",
            "2027-11-05T11:00:00+00:00",
            "AS-P008",
            {
                "action": "COMBINED_HISTORICAL_SELECTED_CONTROL_EXCEPTION",
                "finding_ids": ["DRIFT-BOI-EGRESS-01", "AGENT-COVERAGE-LOSS-01"],
                "original_october_reconciliation_id": "RECON-OCT-01",
                "status": "OPEN_HISTORICAL_CAUSE_AND_MONITORING_GAP",
                "separate_source_from_local_symbolic_exercise": True,
            },
            ("INDEPENDENT-NOV-01", "RECON-OCT-01"),
        )
        emit(
            "security_approval",
            "APPROVE-CORRECTION-01",
            "2027-11-06T10:00:00+00:00",
            "AS-P008",
            {
                "action": "DISTINCT_FICTIONAL_SECURITY_CORRECTION_APPROVAL",
                "scope": ["IF-BOI-EGRESS", "SIM-BOI-OPS-01"],
                "decision": "APPROVE_BASELINE_RESTORE_WITH_EXCEPTION_STILL_OPEN",
                "historical_exception_closed": False,
            },
            ("EXC-SEC005-Q4-01", "BASELINE-01"),
        )
        emit(
            "security_application",
            "CORRECT-BOI-EGRESS-01",
            "2027-11-07T10:00:00+00:00",
            "AS-P007",
            {
                "action": "FICTIONAL_SELECTED_RULE_BASELINE_RESTORED",
                "applied_rule_intents": baseline,
                "original_drift_retained": True,
                "real_device_write": False,
            },
            ("APPROVE-CORRECTION-01", "DRIFT-BOI-EGRESS-01"),
        )
        emit(
            "security_application",
            "RESTORE-AGENT-COVERAGE-01",
            "2027-11-07T11:00:00+00:00",
            "AS-P007",
            {
                "action": "FICTIONAL_SELECTED_ENDPOINT_AGENT_COVERAGE_RESTORED",
                "agent_covered_asset_ids": selected_assets,
                "original_gap_retained": True,
                "real_device_write": False,
            },
            ("APPROVE-CORRECTION-01", "AGENT-COVERAGE-LOSS-01"),
        )
        config_record = "CORRECT-BOI-EGRESS-01"
        coverage_record = "RESTORE-AGENT-COVERAGE-01"
    emit(
        "security_probe",
        "NOV-UNAUTHORIZED-EGRESS-01",
        "2027-11-08T10:00:00+00:00",
        "AS-P007",
        {
            "action": "DATA_ONLY_CORRECTED_UNAUTHORIZED_EGRESS_REPROBE",
            "interface_id": "IF-BOI-EGRESS",
            "intent": intent,
            "decision": evaluate_boundary(baseline, "IF-BOI-EGRESS", intent),
            "effect": "NO_NETWORK_IO",
        },
        (config_record, "INDEPENDENT-NOV-01"),
    )
    emit(
        "security_probe",
        "NOV-UNAPPROVED-EXEC-01",
        "2027-11-08T11:00:00+00:00",
        "AS-P007",
        {
            "action": "DATA_ONLY_RESTORED_ENDPOINT_POLICY_REPROBE",
            "asset_id": "SIM-BOI-OPS-01",
            "manifest": spec["inert_unapproved_executable_manifest"],
            "decision": evaluate_endpoint(selected_assets, "SIM-BOI-OPS-01"),
            "effect": "NO_EXECUTABLE_BYTES_INSTALL_OR_RUN",
        },
        (coverage_record, "INDEPENDENT-NOV-01"),
    )
    emit(
        "security_monitor",
        "MONITOR-NOV-01",
        "2027-11-09T10:00:00+00:00",
        "AS-P007",
        {
            "action": "FICTIONAL_SELECTED_NOVEMBER_MONITOR_SNAPSHOT",
            "publisher_probe_record_ids": ["NOV-UNAUTHORIZED-EGRESS-01", "NOV-UNAPPROVED-EXEC-01"],
            "received_probe_record_ids": ["NOV-UNAUTHORIZED-EGRESS-01", "NOV-UNAPPROVED-EXEC-01"],
            "observed_agent_asset_ids": selected_assets,
            "observed_interface_ids": selected_interfaces,
            "actual_external_log_source": False,
        },
        ("NOV-UNAUTHORIZED-EGRESS-01", "NOV-UNAPPROVED-EXEC-01"),
    )
    emit(
        "security_reconciliation",
        "RECON-NOV-01",
        "2027-11-10T10:00:00+00:00",
        "AS-P008",
        {
            "action": "DISTINCT_FICTIONAL_SELECTED_NOVEMBER_RECONCILIATION",
            "selected_assets_reconciled": 4,
            "selected_interfaces_reconciled": 6,
            "selected_probe_records_reconciled": 2,
            "current_selected_config_matches_approved_baseline": True,
            "historical_exception_open": messy,
            "historical_october_false_pass_retained": messy,
            "full_year_or_enterprise_population_claim": False,
        },
        ("MONITOR-NOV-01", "INDEPENDENT-NOV-01"),
    )
    return rows


def _provenance(scenario: str) -> dict:
    return {
        "source_reference": SOURCE_REFERENCE,
        "scenario": scenario,
        "qualification": "FICTIONAL_SELECTED_COMPANY_OPERATION_NO_REAL_DEPLOYMENT_OR_AUDIT_CREDIT",
        "source_pins": SOURCE_PINS,
        "route_review_path": ROUTE_REVIEW,
        "route_review_sha256": ROUTE_REVIEW_SHA,
        "transition_pins": TRANSITION_PINS,
        "transition_review_sha256": TRANSITION_REVIEW_SHA,
    }


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def create(
    destination: Path,
    *,
    repository: Path,
    private_repository: Path,
    transition_root: Path,
) -> dict:
    """Create one independent private CompanyStore; no audit access or real I/O."""
    destination = Path(destination).absolute()
    _private(destination.parent, directory=True)
    if destination.exists() or destination.is_symlink() or destination != destination.resolve():
        raise CompanyStoreError("New private operated SEC-005 destination required")
    context = _context(repository, private_repository, transition_root)
    with tempfile.TemporaryDirectory(
        prefix=".sec005-operated-stage-", dir=destination.parent
    ) as temp:
        stage = Path(temp)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in BRANCHES.items():
            for system, owner in SYSTEM_OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            records[scenario] = []
            for row in _rows(context, scenario):
                ref = store.append_version(
                    COMPANY,
                    branch,
                    row["system"],
                    row["record"],
                    expected_version=0,
                    command_id=f"S5O-{branch}-{row['record']}",
                    event_at=row["event_at"],
                    available_at=row["available_at"],
                    content=row["content"],
                    provenance=_provenance(scenario),
                )
                if ref["sha256"] != row["sha256"]:
                    raise CompanyStoreError("SEC-005 operated native bytes differ")
                records[scenario].append(ref)
        spec = context["spec"]
        receipt = {
            "schema": SCHEMA,
            "company": COMPANY,
            "branches": BRANCHES,
            "records": records,
            "selected_service_id": spec["service_id"],
            "selected_asset_ids": [item["id"] for item in spec["assets"]],
            "selected_logical_interface_ids": [item["id"] for item in spec["logical_interfaces"]],
            "selected_period": [spec["selected_period_start"], spec["selected_period_end"]],
            "source_pins": SOURCE_PINS,
            "route_review_path": ROUTE_REVIEW,
            "route_review_sha256": ROUTE_REVIEW_SHA,
            "selected_route_authority": context["routes"],
            "transition_pins": TRANSITION_PINS,
            "transition_review_sha256": TRANSITION_REVIEW_SHA,
            "upstream_transition_site_release_refs": context["releases"],
            "native_version_counts": {side: len(refs) for side, refs in records.items()},
            "open_exception_counts": {"CLEAN": 0, "MESSY": 1},
            "open_exception_ids": {"CLEAN": [], "MESSY": ["EXC-SEC005-Q4-01"]},
            "october_original_probe_counts": {"CLEAN": 4, "MESSY": 4},
            "october_collected_probe_counts": {"CLEAN": 4, "MESSY": 2},
            "network_packets_sent": 0,
            "executables_created_or_run": 0,
            "actual_operation_eligibility_as_of_2026_09_30": False,
            "fictional_selected_period_company_operation": True,
            "full_year_or_enterprise_population_complete": False,
            "authored_sec005_clause_satisfied": False,
            "audit_task_credit": False,
            "limits": LIMITS,
        }
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _digest(stage / "RECEIPT.json"),
            "db_sha256": _digest(stage / "company.sqlite3"),
            "module_sha256": _digest(Path(__file__)),
            "native_version_count": sum(len(refs) for refs in records.values()),
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return manifest


def verify(
    destination: Path,
    *,
    repository: Path,
    private_repository: Path,
    transition_root: Path,
) -> dict:
    """Reperform exact raw rows, clocks, authority, release pins and claim limits."""
    root = _private(destination, directory=True)
    paths = {
        "manifest": root / "MANIFEST.json",
        "receipt": root / "RECEIPT.json",
        "db": root / "company.sqlite3",
    }
    before = _frozen(paths)
    manifest = json.loads(paths["manifest"].read_text())
    receipt = json.loads(paths["receipt"].read_text())
    context = _context(repository, private_repository, transition_root)
    spec = context["spec"]
    expected_counts = {side: len(_rows(context, side)) for side in BRANCHES}
    if (
        manifest.get("schema") != SCHEMA + "_MANIFEST"
        or manifest.get("receipt_sha256") != before["receipt"][-1]
        or manifest.get("db_sha256") != before["db"][-1]
        or manifest.get("module_sha256") != _digest(Path(__file__))
        or manifest.get("native_version_count") != sum(expected_counts.values())
        or manifest.get("audit_task_credit") is not False
        or receipt.get("schema") != SCHEMA
        or receipt.get("company") != COMPANY
        or receipt.get("branches") != BRANCHES
        or receipt.get("selected_service_id") != spec["service_id"]
        or receipt.get("selected_asset_ids") != [item["id"] for item in spec["assets"]]
        or receipt.get("selected_logical_interface_ids")
        != [item["id"] for item in spec["logical_interfaces"]]
        or receipt.get("selected_period")
        != [spec["selected_period_start"], spec["selected_period_end"]]
        or receipt.get("source_pins") != SOURCE_PINS
        or receipt.get("route_review_path") != ROUTE_REVIEW
        or receipt.get("route_review_sha256") != ROUTE_REVIEW_SHA
        or receipt.get("selected_route_authority") != context["routes"]
        or receipt.get("transition_pins") != TRANSITION_PINS
        or receipt.get("transition_review_sha256") != TRANSITION_REVIEW_SHA
        or receipt.get("upstream_transition_site_release_refs") != context["releases"]
        or receipt.get("native_version_counts") != expected_counts
        or receipt.get("open_exception_counts") != {"CLEAN": 0, "MESSY": 1}
        or receipt.get("open_exception_ids") != {"CLEAN": [], "MESSY": ["EXC-SEC005-Q4-01"]}
        or receipt.get("october_original_probe_counts") != {"CLEAN": 4, "MESSY": 4}
        or receipt.get("october_collected_probe_counts") != {"CLEAN": 4, "MESSY": 2}
        or receipt.get("network_packets_sent") != 0
        or receipt.get("executables_created_or_run") != 0
        or receipt.get("actual_operation_eligibility_as_of_2026_09_30") is not False
        or receipt.get("fictional_selected_period_company_operation") is not True
        or receipt.get("full_year_or_enterprise_population_complete") is not False
        or receipt.get("authored_sec005_clause_satisfied") is not False
        or receipt.get("audit_task_credit") is not False
        or receipt.get("limits") != LIMITS
        or set(receipt.get("records", {})) != set(BRANCHES)
    ):
        raise CompanyStoreError("SEC-005 operated manifest/receipt scope differs")
    with closing(sqlite3.connect(paths["db"].as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("SEC-005 operated native DB integrity differs")
        if db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != sum(
            expected_counts.values()
        ) or any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "collections", "access_events")
        ):
            raise CompanyStoreError("SEC-005 operated source/audit-access count differs")
        expected_systems = {
            (COMPANY, branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in SYSTEM_OWNERS.items()
        }
        if {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        } != expected_systems:
            raise CompanyStoreError("SEC-005 operated source owners differ")
        for scenario, branch in BRANCHES.items():
            expected = _rows(context, scenario)
            refs = receipt["records"][scenario]
            if len(refs) != len(expected):
                raise CompanyStoreError("SEC-005 operated branch count differs")
            for row, ref in zip(expected, refs, strict=True):
                native = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=1",
                    (COMPANY, branch, row["system"], row["record"]),
                ).fetchone()
                if native is None or native["content"] != row["content"]:
                    raise CompanyStoreError("SEC-005 operated raw native content differs")
                if (
                    native["sha256"] != row["sha256"]
                    or native["event_at"] != row["event_at"]
                    or native["available_at"] != row["available_at"]
                    or json.loads(native["provenance"]) != _provenance(scenario)
                    or native["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or native["command_id"] != f"S5O-{branch}-{row['record']}"
                    or native["imported_at"] >= "2027-01-01"
                    or _time(native["imported_at"]) != native["imported_at"]
                ):
                    raise CompanyStoreError("SEC-005 operated native clocks/provenance differ")
                if ref != CompanyStore._metadata(native):
                    raise CompanyStoreError("SEC-005 operated receipt/native tuple differs")
    if _frozen(paths) != before:
        raise CompanyStoreError("SEC-005 operated source changed during read")
    return {
        "status": "VERIFIED_FICTIONAL_SELECTED_OPERATION_NO_AUDIT_CREDIT",
        "native_version_counts": expected_counts,
    }
