"""Causal local configuration release exercise, independent of every audit."""

import json
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _id, _time
from .operating_source_bridge import encoded, sha
from .organization import snapshot
from .private_publication import publish

CONTROLS = [f"SH-ENG-{n:03}" for n in (1, 2, 3, 4, 6)]
QUALIFICATION = "LOCAL_SYNTHETIC_CONFIG_RELEASE_EXERCISE_NOT_LIVE_DEPLOYMENT"


@dataclass(frozen=True)
class ChangeRecipe:
    company_id: str
    gated_branch: str
    bypass_branch: str
    cycle_id: str
    period_start: str
    period_end_exclusive: str
    local_requirement_basis: str


def evaluate(config):
    """Actually evaluate this bounded data-only model; never execute supplied code."""
    if set(config) != {"timeout_ms", "attempts", "max_total_ms"} or any(
        type(v) is not int or not 1 <= v <= 10000 for v in config.values()
    ):
        raise CompanyStoreError("Exact positive integer local configuration required")
    total = config["timeout_ms"] * config["attempts"]
    return {
        "calculated_total_timeout_ms": total,
        "max_total_ms": config["max_total_ms"],
        "within_local_limit": total <= config["max_total_ms"],
    }


def gate_decision(artifact, test_record, review_record, *, override=False):
    tests_match = test_record.get("artifact") == artifact and test_record.get("passed") is True
    approved = (
        review_record is not None
        and review_record.get("artifact") == artifact
        and review_record.get("decision") == "APPROVED"
    )
    if tests_match and approved:
        return "ALLOWED"
    return "OVERRIDE_USED" if override and tests_match else "BLOCKED"


class LocalTarget:
    """In-memory configuration state only; no filesystem, service or network deployment."""

    def __init__(self, config):
        evaluate(config)
        self.config = dict(config)

    def apply(self, config, decision):
        if decision not in {"ALLOWED", "OVERRIDE_USED"}:
            raise CompanyStoreError("Local release gate blocked")
        evaluate(config)
        prior = sha(encoded(self.config))
        self.config = dict(config)
        return {
            "prior_configuration_sha256": prior,
            "active_configuration_sha256": sha(encoded(self.config)),
            "local_target_result": evaluate(self.config),
        }


def generate_pair(destination, *, repository, recipe: ChangeRecipe):
    """NEW private store only, staged publication; no grants or deployed software."""
    destination, repository = Path(destination).absolute(), Path(repository)
    if (
        destination.exists()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(p.is_symlink() for p in [destination, *destination.parents])
    ):
        raise CompanyStoreError("New change store under private nonsymlink parent required")
    for value in (recipe.company_id, recipe.gated_branch, recipe.bypass_branch, recipe.cycle_id):
        _id(value)
    if recipe.gated_branch == recipe.bypass_branch:
        raise CompanyStoreError("Distinct source branches required")
    start, end = [
        datetime.fromisoformat(_time(x)) for x in (recipe.period_start, recipe.period_end_exclusive)
    ]
    if not timedelta(hours=18) < end - start <= timedelta(days=31):
        raise CompanyStoreError("Local cycle must fit an 18-hour to31-day window")
    if (
        not isinstance(recipe.local_requirement_basis, str)
        or not 1 <= len(recipe.local_requirement_basis.strip()) <= 2000
    ):
        raise CompanyStoreError("Explicit local requirement basis required")
    org = snapshot(repository, as_of=start.date().isoformat())
    assignments = {a["control_id"]: a for a in org["control_assignments"]}
    selected = [assignments[c] for c in CONTROLS]
    owner = selected[0]["primary_person_id"]
    reviewer = selected[0]["operating_reviewer_person_id"]
    if (
        not owner
        or not reviewer
        or owner == reviewer
        or any(
            a["primary_person_id"] != owner or a["operating_reviewer_person_id"] != reviewer
            for a in selected
        )
    ):
        raise CompanyStoreError("Distinct consistent scoped operating owner/reviewer required")
    pins = dict(org["source_sha256"])
    for path in (
        "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
        "enterprise/runtime/docs/ARCHITECTURE_AND_RUNBOOKS.md",
        "enterprise/services/source/services.json",
        "enterprise/services/source/runtime_sites_2026-09-11.json",
        "enterprise/audit_suite/company_change_activity.py",
    ):
        pins[path] = sha((repository / path).read_bytes())
    sites = json.loads(
        (repository / "enterprise/services/source/runtime_sites_2026-09-11.json").read_bytes()
    )
    site_refs = [
        {k: site[k] for k in ("id", "status", "operating", "contract_executed")}
        for site in sites["sites"]
        if site["id"] in {"RUNTIME-RENO-COLO", "RUNTIME-BOISE-DR"}
    ]
    recipe_sha = sha(encoded(asdict(recipe)))
    common = {
        "cycle_id": recipe.cycle_id,
        "classification": QUALIFICATION,
        "boundary_id": "corporate",
        "period_start": start.isoformat(),
        "period_end_exclusive": end.isoformat(),
        "policy_status": "LOCAL_EXERCISE_RULE_NOT_ACCEPTED_ENTERPRISE_POLICY",
        "appointment_status": "SCOPED_CONTACT_ASSIGNMENTS_NOT_EMPLOYMENT_HISTORY",
        "local_requirement_basis": recipe.local_requirement_basis,
        "target": "IN_MEMORY_REFERENCE_CONFIGURATION_ONLY",
        "service_reference": "SVC-developer",
        "service_status": "CANONICAL_DESIGN_REFERENCE_NOT_DEPLOYMENT",
        "site_references_only": site_refs,
        "emergency_process": "NOT_EXERCISED_NO_EMERGENCY_AUTHORITY_ASSERTED",
    }
    all_receipts = []
    baseline = {"timeout_ms": 30, "attempts": 3, "max_total_ms": 120}
    candidate = {"timeout_ms": 50, "attempts": 3, "max_total_ms": 120}
    corrected = {"timeout_ms": 40, "attempts": 3, "max_total_ms": 120}
    with tempfile.TemporaryDirectory(prefix="change-stage-", dir=destination.parent) as temp:
        store = CompanyStore(Path(temp))
        for branch in (recipe.gated_branch, recipe.bypass_branch):
            systems = {
                "change_intents": owner,
                "configurations": owner,
                "builds": owner,
                "tests": owner,
                "peer_reviews": reviewer,
                "release_gate": owner,
                "local_releases": owner,
                "observations": owner,
                "recovery": owner,
            }
            for system, person in systems.items():
                store.register_system(recipe.company_id, branch, system, person)

            record_values = {}
            target = LocalTarget(baseline)

            def emit(
                system,
                identity,
                hour,
                body,
                controls=CONTROLS,
                branch=branch,
                record_values=record_values,
            ):
                stamp = (start + timedelta(hours=hour)).isoformat()
                data = encoded(
                    {
                        **common,
                        "record_id": identity,
                        "recorded_at": stamp,
                        "control_ids": controls,
                        **body,
                    }
                )
                row = store.append_version(
                    recipe.company_id,
                    branch,
                    system,
                    identity,
                    expected_version=0,
                    command_id="CHG-" + sha(encoded([recipe_sha, branch, system, identity])),
                    event_at=stamp,
                    available_at=stamp,
                    content=data,
                    provenance={
                        "name": identity + ".json",
                        "source_reference": identity,
                        "control_ids": controls,
                        "classification": QUALIFICATION,
                        "operational_fact_status": "LOCAL_MODEL_EXECUTION_ONLY",
                        "source_period_start": start.isoformat(),
                        "source_period_end": end.isoformat(),
                        "recipe_sha256": recipe_sha,
                        "source_sha256": pins,
                        "owner_assignment": selected,
                        "source_authority": "DESIGN_REFERENCE",
                        "policy_status": common["policy_status"],
                    },
                )
                record_values[identity] = json.loads(data)
                all_receipts.append(row)
                return {
                    "system_id": system,
                    "record_id": identity,
                    "version": 1,
                    "sha256": row["sha256"],
                    "available_at": stamp,
                }

            def config_record(identity, config, hour):
                return emit(
                    "configurations",
                    identity,
                    hour,
                    {"configuration": config, "configuration_sha256": sha(encoded(config))},
                )

            def build(identity, config, config_ref, hour):
                package = {"format": "LOCAL_CONFIG_PACKAGE_V1", "configuration": config}
                return emit(
                    "builds",
                    identity,
                    hour,
                    {
                        "source": config_ref,
                        "package": package,
                        "package_sha256": sha(encoded(package)),
                        "builder": "DATA_ONLY_CANONICAL_JSON_PACKAGER",
                        "executable_binary_compilation": False,
                    },
                )

            def tests(identity, config, build_ref, hour, combined):
                result = evaluate(config)
                checks = [{"name": "positive_integer_schema", "passed": True}]
                if combined:
                    checks.append(
                        {
                            "name": "combined_retry_timeout_limit",
                            "passed": result["within_local_limit"],
                            "calculation": result,
                        }
                    )
                return emit(
                    "tests",
                    identity,
                    hour,
                    {
                        "artifact": build_ref,
                        "tests": checks,
                        "passed": all(c["passed"] for c in checks),
                        "test_scope": "SCHEMA_AND_COMBINED_LIMIT" if combined else "SCHEMA_ONLY",
                        "omitted_checks": [] if combined else ["combined_retry_timeout_limit"],
                    },
                    ["SH-ENG-003"],
                )

            def review(identity, config, build_ref, hour):
                result = evaluate(config)
                return emit(
                    "peer_reviews",
                    identity,
                    hour,
                    {
                        "reviewer_id": reviewer,
                        "artifact": build_ref,
                        "calculation": result,
                        "decision": "APPROVED"
                        if result["within_local_limit"]
                        else "CHANGES_REQUESTED",
                    },
                    ["SH-ENG-002"],
                )

            original = config_record("CONFIG-BASELINE", baseline, 0)
            proposed = config_record("CONFIG-PROPOSED", candidate, 1)
            emit(
                "change_intents",
                "CHANGE-INTENT",
                1,
                {
                    "owner_id": owner,
                    "change_type": "NORMAL",
                    "emergency": False,
                    "requirement": (
                        "Increase per-attempt timeout while total retry time stays <=120ms."
                    ),
                    "baseline": original,
                    "candidate": proposed,
                    "planned_reviewer_id": reviewer,
                },
                ["SH-ENG-001"],
            )
            initial_build = build("BUILD-PROPOSED", candidate, proposed, 2)
            initial_tests = tests("TEST-PROPOSED", candidate, initial_build, 3, False)
            emit(
                "recovery",
                "ROLLBACK-PLAN",
                4,
                {
                    "restore_source": original,
                    "acceptance": evaluate(baseline),
                    "method": (
                        "Replace local in-memory configuration with pinned baseline; re-evaluate."
                    ),
                },
                ["SH-ENG-006"],
            )
            # Same candidate and structural tests; release differs solely at the peer-review gate.
            if branch == recipe.gated_branch:
                rejected = review("REVIEW-PROPOSED", candidate, initial_build, 5)
                emit(
                    "release_gate",
                    "GATE-PROPOSED",
                    6,
                    {
                        "artifact": initial_build,
                        "tests": initial_tests,
                        "peer_review": rejected,
                        "required_peer_review": "APPROVED_EXACT_ARTIFACT",
                        "decision": gate_decision(
                            initial_build,
                            record_values["TEST-PROPOSED"],
                            record_values["REVIEW-PROPOSED"],
                        ),
                        "reason": "Peer review requested changes; target remains baseline.",
                    },
                    ["SH-ENG-002", "SH-ENG-004"],
                )
                correction_hour = 7
            else:
                gate = emit(
                    "release_gate",
                    "GATE-PROPOSED",
                    6,
                    {
                        "artifact": initial_build,
                        "tests": initial_tests,
                        "peer_review": None,
                        "required_peer_review": "APPROVED_EXACT_ARTIFACT",
                        "decision": gate_decision(
                            initial_build, record_values["TEST-PROPOSED"], None, override=True
                        ),
                        "operator_id": owner,
                        "reason": "Operator explicitly bypassed the local peer-review gate.",
                        "emergency": False,
                        "approved_exception": None,
                    },
                    ["SH-ENG-002", "SH-ENG-004"],
                )
                release = emit(
                    "local_releases",
                    "RELEASE-PROPOSED",
                    7,
                    {
                        "artifact": initial_build,
                        "gate": gate,
                        "actor_id": owner,
                        **target.apply(candidate, record_values["GATE-PROPOSED"]["decision"]),
                    },
                    ["SH-ENG-004"],
                )
                emit(
                    "observations",
                    "OBSERVE-PROPOSED",
                    8,
                    {
                        "release": release,
                        "observed_local_calculation": evaluate(candidate),
                        "request": "Review combined retry budget and correct configuration.",
                    },
                )
                review("REVIEW-PROPOSED", candidate, initial_build, 9)
                correction_hour = 10
            fix = config_record("CONFIG-CORRECTED", corrected, correction_hour)
            fix_build = build("BUILD-CORRECTED", corrected, fix, correction_hour)
            fix_tests = tests("TEST-CORRECTED", corrected, fix_build, correction_hour + 1, True)
            approved = review("REVIEW-CORRECTED", corrected, fix_build, correction_hour + 2)
            gate = emit(
                "release_gate",
                "GATE-CORRECTED",
                correction_hour + 3,
                {
                    "artifact": fix_build,
                    "tests": fix_tests,
                    "peer_review": approved,
                    "decision": gate_decision(
                        fix_build,
                        record_values["TEST-CORRECTED"],
                        record_values["REVIEW-CORRECTED"],
                    ),
                    "required_peer_review": "APPROVED_EXACT_ARTIFACT",
                },
                ["SH-ENG-002", "SH-ENG-004"],
            )
            release = emit(
                "local_releases",
                "RELEASE-CORRECTED",
                correction_hour + 3,
                {
                    "artifact": fix_build,
                    "gate": gate,
                    "actor_id": owner,
                    **target.apply(corrected, record_values["GATE-CORRECTED"]["decision"]),
                },
                ["SH-ENG-004"],
            )
            rollback = target.apply(baseline, "ALLOWED")
            restored_release = target.apply(corrected, record_values["GATE-CORRECTED"]["decision"])
            emit(
                "recovery",
                "ROLLBACK-REHEARSAL",
                correction_hour + 4,
                {
                    "release": release,
                    "restored_source": original,
                    "restored_configuration_sha256": rollback["active_configuration_sha256"],
                    "restored_local_result": rollback["local_target_result"],
                    "rollback_from_configuration_sha256": rollback["prior_configuration_sha256"],
                    "subsequent_restored_release": release,
                    "subsequent_local_result": restored_release["local_target_result"],
                    "subsequent_configuration_sha256": restored_release[
                        "active_configuration_sha256"
                    ],
                    "environment": "ISOLATED_IN_MEMORY_REHEARSAL_NO_EXTERNAL_SIDE_EFFECT",
                },
                ["SH-ENG-006"],
            )
        receipt = {
            "status": "LOCAL_CHANGE_SOURCE_PAIR_CREATED",
            "recipe_sha256": recipe_sha,
            "recipe": asdict(recipe),
            "source_sha256": pins,
            "records": all_receipts,
            "control_ids": CONTROLS,
            "not_exercised": ["SH-ENG-005"],
            "qualification": QUALIFICATION,
            "organization_snapshot_sha256": org["snapshot_digest"],
            "owner_id": owner,
            "reviewer_id": reviewer,
            "limits": [
                "No production deployment, emergency approval, accepted policy "
                "or professional conclusion.",
                "Single local change; not a full-period or enterprise change population.",
            ],
        }
        path = Path(temp) / "SOURCE_RECEIPT.json"
        path.write_bytes(encoded(receipt))
        path.chmod(0o600)
        publish(Path(temp), destination)
    return receipt
