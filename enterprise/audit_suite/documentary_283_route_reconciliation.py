"""Read-only exact 283-route candidate reconciliation; never grants audit credit."""

from __future__ import annotations

import hashlib
import json
import stat
from collections import Counter, defaultdict
from pathlib import Path

PINS = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_PINS_2026-09-29.json"
SCHEMA = "SH_DOCUMENTARY_283_PAIRED_ROUTE_CANDIDATE_RECONCILIATION_V2"
FAMILIES = {
    "architecture_configuration_and_change",
    "business_continuity_and_recovery",
    "data_record_and_phi_flow",
    "identity_lifecycle_and_nonhuman",
    "policy_and_hipaa_addressable",
    "product_customer_commitments",
    "provider_and_ba_contracts",
    "risk_assurance_governance",
    "training_workforce_and_ethics",
}
LIMITS = [
    "Classification is source-search triage, not a task disposition, "
    "population test or audit credit.",
    "Source targeting is shown separately from clause support; an exact task ID "
    "in a receipt does not satisfy its authored clause.",
    "Fictional 2027 event placement is not actual operation as of 2026-09-29; "
    "all current paired tasks remain NOT_STARTED/NOT_RUN.",
    "The frozen 13-component A/B registry, tasks, Key, workpapers and Atlas are untouched.",
    "The prospective SH-ENG-005 2027 source is excluded pending its sealed run "
    "and independent review.",
]
SOURCE_KEYS = (
    "transition",
    "phi_ba",
    "provider",
    "stagegate",
    "findings",
    "critical_role",
    "dataset",
    "controlled_record",
    "extraction",
    "processing",
    "contract_triage",
    "retention",
    "integrity",
    "bcm",
    "policy",
)


class ReconciliationError(ValueError):
    """A frozen route, reviewed source, or no-credit boundary changed."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> object:
    return json.loads(path.read_bytes())


def _selected(value: object) -> set[str]:
    if isinstance(value, str):
        return {value} if value.startswith("TASK-") else set()
    if isinstance(value, list):
        return set().union(*(_selected(item) for item in value)) if value else set()
    if isinstance(value, dict):
        return set().union(*(_selected(item) for item in value.values())) if value else set()
    return set()


def _reviewed_receipt_sha(review: dict) -> str:
    """Extract the reviewed run receipt across the sealed cohort receipt schemas."""
    candidates = []
    direct = review.get("run_receipt_sha256")
    if direct is not None:
        candidates.append(direct)
    for key in ("run_sha256", "run_v1_sha256", "run_v2_sha256", "run_v3_sha256"):
        run = review.get(key)
        if run is not None:
            if not isinstance(run, dict):
                raise ReconciliationError("Reviewed run hash map is invalid")
            candidates.append(run.get("RECEIPT.json"))
    if len(candidates) != 1 or not isinstance(candidates[0], str):
        raise ReconciliationError("Unique reviewed receipt hash is missing")
    value = candidates[0]
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ReconciliationError("Reviewed receipt hash is malformed")
    return value


def _require_review_receipt_join(review: dict, pinned_sha256: str, name: str) -> None:
    if _reviewed_receipt_sha(review) != pinned_sha256:
        raise ReconciliationError(f"Review/receipt join differs: {name}")


def _pin_inputs(repository: Path, private_repository: Path) -> tuple[dict, dict]:
    pin_file = repository / PINS
    pins = _json(pin_file)
    if pins.get("schema") != "SH_DOCUMENTARY_283_ROUTE_RECONCILIATION_PINS_V1":
        raise ReconciliationError("Reconciliation pin schema differs")
    loaded = {}
    for name, entry in pins["inputs"].items():
        root = repository if entry["scope"] == "repo" else private_repository
        path = root / entry["path"]
        if any(part.is_symlink() for part in (path, *path.parents)):
            raise ReconciliationError("Input aliases forbidden")
        before = path.stat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ReconciliationError("Ordinary input file required")
        if entry["scope"] == "private" and stat.S_IMODE(before.st_mode) != 0o600:
            raise ReconciliationError("Private input mode differs")
        if _sha(path) != entry["sha256"]:
            raise ReconciliationError(f"Pinned input differs: {name}")
        loaded[name] = _json(path) if path.suffix == ".json" else path.read_text()
        after = path.stat()
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            stat.S_IMODE(before.st_mode),
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            stat.S_IMODE(after.st_mode),
        ) or _sha(path) != entry["sha256"]:
            raise ReconciliationError("Input changed during read")
    matrix_review = loaded["matrix_review_v2"]
    if (
        matrix_review.get("verdict") != "PASS_READ_ONLY_CANDIDATE_MATRIX_FOR_INTEGRATION"
        or matrix_review.get("matrix_sha256") != pins["inputs"]["matrix_v2"]["sha256"]
        or matrix_review.get("audit_task_credit") is not False
        or matrix_review.get("active_P1_mutated") is not False
    ):
        raise ReconciliationError("Reviewed matrix authority differs")
    native_versions = 0
    for name in SOURCE_KEYS:
        review = loaded[name + "_review"]
        if not str(review.get("verdict", "")).startswith("PASS"):
            raise ReconciliationError(f"Source review is not PASS: {name}")
        _require_review_receipt_join(review, pins["inputs"][name + "_receipt"]["sha256"], name)
        receipt = loaded[name + "_receipt"]
        if receipt.get("audit_task_credit") is True:
            raise ReconciliationError(f"Source claims task credit: {name}")
        records = receipt.get("records")
        if not isinstance(records, dict) or set(records) != {"CLEAN", "MESSY"}:
            raise ReconciliationError(f"Selected source branches differ: {name}")
        if not all(isinstance(records[side], list) for side in ("CLEAN", "MESSY")):
            raise ReconciliationError(f"Selected native row list differs: {name}")
        native_versions += sum(len(records[side]) for side in ("CLEAN", "MESSY"))
    if len(SOURCE_KEYS) != 15 or native_versions != 256:
        raise ReconciliationError("Reviewed partial 15-cohort/256-version roster differs")
    return pins, loaded


def _targets(inputs: dict) -> dict[tuple[str, str], set[str]]:
    targeted = defaultdict(set)
    source_names = {
        "dataset": "DATASET_V1",
        "controlled_record": "CONTROLLED_RECORD_V1",
        "extraction": "SOURCE_EXTRACTION_V1",
        "stagegate": "ERM_STAGEGATE_V2",
        "findings": "ASSURANCE_FINDINGS_V1",
        "retention": "RETENTION_HOLD_GATE_V1",
        "integrity": "INTEGRITY_CHAIN_V1",
        "bcm": "BCM_SHARED_V2",
    }
    for key, label in source_names.items():
        selected = inputs[key + "_receipt"].get("selected_route_task_ids")
        if not isinstance(selected, dict) or set(selected) != {"A", "B"}:
            raise ReconciliationError(f"Exact selected route map missing: {key}")
        for side in "AB":
            for task_id in _selected(selected[side]):
                targeted[side, task_id].add(label)
    provider = inputs["provider_85_v2"]
    for route in provider["routes"]:
        if route["candidate_touch"] != "NO_DIRECT_SOURCE":
            targeted[route["side"], route["task_id"]].add("PROVIDER_BA_V2")
    for side in "AB":
        disposition = inputs["contract_triage_receipt"]["separate_read_only_72_route_disposition"][
            side
        ]
        if len(disposition["routes"]) != 72:
            raise ReconciliationError("Contract term triage route denominator differs")
        for route in disposition["routes"]:
            if route["term_inventory_context"] != "UNSUPPORTED_NO_DIRECT_SOURCE":
                targeted[side, route["task_id"]].add("CONTRACT_TRIAGE_V1")
        for cid in ("SH-PPL-005", "SH-TRN-003"):
            for route in inputs["matrix_v2"]["sides"][side]["families"]:
                for control in route["controls"]:
                    if control["control_id"] == cid:
                        for task in control["tasks"]:
                            targeted[side, task["task_id"]].add("CRITICAL_ROLE_V3")
        targeted[side, "TASK-SH-DAT-002-corporate-ACTION-H-PRIVACY-PURPOSE"].add(
            "PROCESSING_PURPOSE_V1"
        )
    for row in inputs["policy_22"]["rows"]:
        if row["proposed_source_scope"].startswith("PARTIAL_"):
            targeted[row["side"], row["task_id"]].add("POLICY_EXCEPTION_V1")
    return targeted


def _lookup(inputs: dict) -> dict[str, dict]:
    lookup = {}
    for name, key, target in (
        ("data", "data_50", "task_rows"),
        ("provider", "provider_85_v2", "routes"),
        ("risk", "risk_50", "routes"),
        ("bcm", "bcm_11", "routes"),
        ("policy", "policy_22", "rows"),
    ):
        result = {}
        for row in inputs[key][target]:
            if name == "data":
                for side in "AB":
                    result[side, row["task_ids"][side]] = row
            else:
                result[row["side"], row["task_id"]] = row
        lookup[name] = result
    return lookup


def _classify(
    family: str, control_id: str, task: dict, specific: dict | None
) -> tuple[str, list[str], str]:
    kind = task["procedure_type"]
    generic = kind != "ADDITIONAL_DUTY"
    if family == "data_record_and_phi_flow":
        source_class = specific["source_class"]
        sources = list(specific["candidate_native_source_ids"])
        if task["task_id"] == "TASK-SH-DAT-004-corporate-ACTION-H-INTEGRITY":
            return (
                "SOURCE_CANDIDATE_PARTIAL",
                ["INTEGRITY_CHAIN_V1"],
                (
                    "One nonpersonal disposable-copy alteration; no transfer or "
                    "enterprise integrity population."
                ),
            )
        if source_class in {
            "SCOPED_FUTURE_NATIVE",
            "LOCAL_FIXTURE_NATIVE",
            "LOCAL_OR_FUTURE_NATIVE_NOT_DEPLOYMENT",
        }:
            return "SOURCE_CANDIDATE_PARTIAL", sources, specific["source_limitation"]
        if source_class == "DESIGN_REFERENCE_ONLY":
            return "DESIGN_CONTEXT_ONLY", [], specific["source_limitation"]
        return "UNSUPPORTED_EXACT_CLAUSE", [], specific["source_limitation"]
    if family == "provider_and_ba_contracts":
        touch = specific["candidate_touch"]
        if touch not in {"NO_DIRECT_SOURCE", "SCENARIO_ROLE_CONTEXT_ONLY"}:
            return (
                "SOURCE_CANDIDATE_PARTIAL",
                list(specific["candidate_source_anchor_ids"]),
                (specific["exact_clause_limit"]),
            )
        if touch == "SCENARIO_ROLE_CONTEXT_ONLY" or generic:
            return "DESIGN_CONTEXT_ONLY", [], specific["exact_clause_limit"]
        return "UNSUPPORTED_EXACT_CLAUSE", [], specific["exact_clause_limit"]
    if family == "risk_assurance_governance":
        if specific["candidate_support"] == "BOUNDED_SELECTED_CONDITION_PARTIAL":
            return (
                "SOURCE_CANDIDATE_PARTIAL",
                list(specific["selected_2027_native_source_ids"]),
                (specific["missing_activity"]),
            )
        return (
            "DESIGN_CONTEXT_ONLY" if generic else "UNSUPPORTED_EXACT_CLAUSE",
            [],
            specific["missing_activity"],
        )
    if family == "business_continuity_and_recovery":
        if task["task_id"] == "TASK-SH-BCM-004-corporate-ACTION-H-EMERGENCY":
            return (
                "UNSUPPORTED_EXACT_CLAUSE",
                [],
                "The payload-free diagnostic recovery did not exercise approved "
                "emergency-mode ePHI access or replay for authorized operators.",
            )
        return (
            "SOURCE_CANDIDATE_PARTIAL",
            ["BCM_SHARED_V2"],
            (
                "One fictional shared-service BIA/exercise; full dependency, "
                "actual ePHI emergency use, "
                "independent period population and qualified objectives remain unproved."
            ),
        )
    if family == "policy_and_hipaa_addressable":
        scope = specific["proposed_source_scope"]
        if scope.startswith("PARTIAL_"):
            return (
                "SOURCE_CANDIDATE_PARTIAL",
                ["POLICY_EXCEPTION_V1"],
                (
                    "Approved design-standard bytes/local copy and pending draft/request only; "
                    "no approved revision, "
                    "human receipt, effective waiver or complete policy population."
                ),
            )
        if scope.startswith("SEPARATE_"):
            return (
                "DESIGN_CONTEXT_ONLY",
                ["ADDRESSABLE_PENDING_DOCKET"],
                (
                    "Twenty-two locator cases are pending; no environmental decision "
                    "or generic waiver."
                ),
            )
        return (
            "DESIGN_CONTEXT_ONLY" if generic else "UNSUPPORTED_EXACT_CLAUSE",
            [],
            "Proposed policy procedure/design exists; exact period duty or authority "
            "remains absent.",
        )
    if family == "training_workforce_and_ethics" and control_id in {
        "SH-PPL-005",
        "SH-TRN-003",
    }:
        return (
            "SOURCE_CANDIDATE_PARTIAL",
            ["CRITICAL_ROLE_V3"],
            (
                "Two proposed contacts and local training chronology; no verified "
                "qualification, backup, "
                "employment population or competency decision."
            ),
        )
    return (
        "DESIGN_CONTEXT_ONLY" if generic else "UNSUPPORTED_EXACT_CLAUSE",
        [],
        "Proposed design/search target only; exact 2027 activity and accepted "
        "authority are absent.",
    )


def build(repository: Path, private_repository: Path) -> dict:
    """Join reviewed inputs and classify source-search support for every exact task."""
    repository, private_repository = (
        Path(repository).absolute(),
        Path(private_repository).absolute(),
    )
    pins, inputs = _pin_inputs(repository, private_repository)
    matrix, screen, unmatched = inputs["matrix_v2"], inputs["screen_v3"], inputs["unmatched_v2"]
    if matrix["counts"]["tasks_per_side"] != 283 or matrix["counts"]["controls_per_side"] != 43:
        raise ReconciliationError("Reviewed 283/43 matrix denominator differs")
    screen_by_key = {(row["side"], row["task_id"]): row for row in screen["rows"]}
    unmatched_by_key = {
        (row["side"], row["task_id"]): row for row in unmatched if row.get("control_id") is not None
    }
    lookup, targets = _lookup(inputs), _targets(inputs)
    rows = []
    for side in "AB":
        families = matrix["sides"][side]["families"]
        if {family["family"] for family in families} != FAMILIES:
            raise ReconciliationError("Exact nine family partition differs")
        for family in families:
            family_id = family["family"]
            lookup_name = {
                "data_record_and_phi_flow": "data",
                "provider_and_ba_contracts": "provider",
                "risk_assurance_governance": "risk",
                "business_continuity_and_recovery": "bcm",
                "policy_and_hipaa_addressable": "policy",
            }.get(family_id)
            for control in family["controls"]:
                for task in control["tasks"]:
                    key = side, task["task_id"]
                    screen_row, unmatched_row = screen_by_key[key], unmatched_by_key[key]
                    if (
                        task["current_status"] != "NOT_STARTED"
                        or task["current_conclusion"] != "NOT_RUN"
                        or task["task_credit"] is not False
                        or screen_row["current_status"] != "NOT_STARTED"
                        or screen_row["current_conclusion"] != "NOT_RUN"
                        or screen_row["task_credit_from_screen"] is not False
                        or task["authored_test_clause"] != screen_row["test_clause"]
                        or control["control_id"] != screen_row["control_id"]
                        or control["control_id"] != unmatched_row["control_id"]
                        or task["procedure_type"] != screen_row["procedure_type"]
                        or task["procedure_type"] != unmatched_row["procedure_type"]
                    ):
                        raise ReconciliationError("Frozen exact task/status/clause join differs")
                    specific = lookup[lookup_name][key] if lookup_name else None
                    screen_digest = hashlib.sha256(
                        json.dumps(screen_row, sort_keys=True, separators=(",", ":")).encode()
                    ).hexdigest()
                    if specific is not None and (
                        specific.get("authored_test_clause") != task["authored_test_clause"]
                        or specific.get("screen_row_sha256", screen_digest) != screen_digest
                    ):
                        raise ReconciliationError("Reviewed family clause or screen pin differs")
                    classification, source_ids, limit = _classify(
                        family_id, control["control_id"], task, specific
                    )
                    rows.append(
                        {
                            "side": side,
                            "family": family_id,
                            "control_id": control["control_id"],
                            "task_id": task["task_id"],
                            "procedure_type": task["procedure_type"],
                            "authored_test_clause": task["authored_test_clause"],
                            "test_gate_basis": task["test_gate_basis"],
                            "requirement_ids": task["requirement_ids"],
                            "screen_row_sha256": screen_digest,
                            "targeted_integrated_source_ids": sorted(targets.get(key, set())),
                            "classification": classification,
                            "candidate_or_design_source_ids": source_ids,
                            "source_limit": limit,
                            "remaining_test_gate": task["remaining_test_gate"],
                            "current_status": "NOT_STARTED",
                            "current_conclusion": "NOT_RUN",
                            "actual_operation_eligibility_as_of_packet": False,
                            "audit_task_credit": False,
                        }
                    )
    if len(rows) != 566 or any(
        len({(row["side"], row["task_id"]) for row in rows if row["side"] == side}) != 283
        for side in "AB"
    ):
        raise ReconciliationError("Exact paired 283-route identity differs")
    keys = {(row["side"], row["task_id"]) for row in rows}
    if any(key not in keys for key in targets):
        raise ReconciliationError("Integrated cohort target escaped frozen 283 partition")
    counts = {
        side: {
            "classifications": dict(
                sorted(
                    Counter(row["classification"] for row in rows if row["side"] == side).items()
                )
            ),
            "targeted_integrated_route_count": sum(
                bool(row["targeted_integrated_source_ids"]) for row in rows if row["side"] == side
            ),
            "authored_clause_count": sum(
                row["test_gate_basis"] == "AUTHORED_TASK_CLAUSE"
                for row in rows
                if row["side"] == side
            ),
            "inferred_gate_count": sum(
                row["test_gate_basis"] == "GENERIC_PROCEDURE_GATE_NOT_AN_AUTHORED_CLAUSE"
                for row in rows
                if row["side"] == side
            ),
            "family_routes": dict(
                sorted(Counter(row["family"] for row in rows if row["side"] == side).items())
            ),
            "target_vs_classification": {
                target_state: {
                    classification: {
                        "count": len(selected),
                        "task_ids": sorted(row["task_id"] for row in selected),
                        "by_family": dict(
                            sorted(Counter(row["family"] for row in selected).items())
                        ),
                    }
                    for classification in (
                        "SOURCE_CANDIDATE_PARTIAL",
                        "DESIGN_CONTEXT_ONLY",
                        "UNSUPPORTED_EXACT_CLAUSE",
                    )
                    for selected in [
                        [
                            row
                            for row in rows
                            if row["side"] == side
                            and bool(row["targeted_integrated_source_ids"])
                            == (target_state == "TARGETED")
                            and row["classification"] == classification
                        ]
                    ]
                }
                for target_state in ("TARGETED", "UNTARGETED")
            },
        }
        for side in "AB"
    }
    if counts["A"] != counts["B"]:
        raise ReconciliationError("Paired source-search counts diverged")
    return {
        "schema": SCHEMA,
        "as_of": "2026-09-29",
        "base_commit": pins["base_commit"],
        "reviewed_partial_source_roster": {
            "cohorts": list(SOURCE_KEYS),
            "source_count": 15,
            "native_versions": 256,
            "source_complete": False,
        },
        "source_pins_sha256": _sha(repository / PINS),
        "source_pins": pins["inputs"],
        "counts": counts,
        "rows": sorted(rows, key=lambda row: (row["side"], row["control_id"], row["task_id"])),
        "limits": LIMITS,
        "audit_task_credit": False,
        "active_pair_mutated": False,
    }


def markdown(result: dict) -> str:
    """Render a concise review map; the JSON retains every exact clause and ID."""
    count = result["counts"]["A"]
    parts = [
        "# Paired 283-route source and clause reconciliation",
        "",
        "This is read-only source-search triage for the independently reviewed 43-control, "
        "283-route-per-side documentary/activity partition. The paired A/B audit workroom remains "
        "frozen, with every task `NOT_STARTED`/`NOT_RUN`; all fictional source events are future "
        "as of 2026-09-29. The [machine-readable ledger]"
        "(DOCUMENTARY_283_ROUTE_RECONCILIATION_2026-09-29.json) "
        "preserves every exact task ID, authored clause or inferred gate, targeted cohort ID, "
        "source limit and no-credit state.",
        "",
        "The pinned source roster contains 15 independently reviewed fictional cohorts and "
        "256 native versions, matching the separate partial portfolio V2 diagnostic "
        "(report SHA-256 `80ef78ff0368577269c7bba96683d76377000e09d32c14c60e5904cc9d24472f`, "
        "independent PASS review SHA-256 "
        "`c0af1a38bce0942f220c375fa0681b238b9915dcd9d8c3588e4b161895f05738`). "
        "That roster remains source-incomplete and outside the frozen pair.",
        "",
        "`SOURCE_CANDIDATE_PARTIAL` means an exact bounded native/source lead touches the route, "
        "not that the clause is satisfied. `DESIGN_CONTEXT_ONLY` means a proposed procedure, "
        "pending locator or role/design lead exists without a sufficient selected operation. "
        "`UNSUPPORTED_EXACT_CLAUSE` means the authored activity or authority has no direct "
        "support in the pinned cohort set. Targeted source IDs are a separate field because "
        "some producers name a task yet do not implement its specific duty.",
        "",
        "| Classification | Routes per side |",
        "| --- | ---: |",
    ]
    for name, value in count["classifications"].items():
        parts.append(f"| {name} | {value} |")
    parts.extend(
        [
            "",
            f"Integrated cohorts explicitly target "
            f"{count['targeted_integrated_route_count']} distinct task IDs "
            "per side. That is a discovery denominator, not a sufficiency or completion count.",
            "",
            "The two totals differ because source targeting and exact-clause support are "
            "independent decisions: **93 targeted = 78 partial-native + 10 design-only + "
            "5 unsupported; 84 partial-native = 78 targeted + 6 untargeted prior-native leads** "
            "per side. The 21 exception IDs below are exact and identical in A and B; "
            "the JSON records their separate side rows and family counts.",
            "",
            "| Source targeting | Partial native | Design only | Unsupported |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    cross = count["target_vs_classification"]
    for state in ("TARGETED", "UNTARGETED"):
        parts.append(
            f"| {state.lower()} | "
            f"{cross[state]['SOURCE_CANDIDATE_PARTIAL']['count']} | "
            f"{cross[state]['DESIGN_CONTEXT_ONLY']['count']} | "
            f"{cross[state]['UNSUPPORTED_EXACT_CLAUSE']['count']} |"
        )
    parts.extend(
        [
            "",
            "| Boundary set | By family | Exact task IDs (same IDs on A and B) |",
            "| --- | --- | --- |",
        ]
    )
    for state, classification, label in (
        ("TARGETED", "DESIGN_CONTEXT_ONLY", "Targeted, design-only"),
        ("TARGETED", "UNSUPPORTED_EXACT_CLAUSE", "Targeted, unsupported"),
        ("UNTARGETED", "SOURCE_CANDIDATE_PARTIAL", "Untargeted, partial-native"),
    ):
        group = cross[state][classification]
        family_counts = ", ".join(
            f"{family}: {value}" for family, value in group["by_family"].items()
        )
        task_ids = "<br>".join(f"`{task_id}`" for task_id in group["task_ids"])
        parts.append(f"| {label} ({group['count']}) | {family_counts} | {task_ids} |")
    parts.extend(
        [
            "",
            "| Family | Routes | Native candidate | Design only | Unsupported clause |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for name, value in count["family_routes"].items():
        classified = Counter(
            row["classification"]
            for row in result["rows"]
            if row["side"] == "A" and row["family"] == name
        )
        parts.append(
            f"| {name} | {value} | {classified['SOURCE_CANDIDATE_PARTIAL']} | "
            f"{classified['DESIGN_CONTEXT_ONLY']} | "
            f"{classified['UNSUPPORTED_EXACT_CLAUSE']} |"
        )
    parts.extend(
        [
            "",
            "The provider/BA V2 packet labels 19 routes as partial context, but three offer "
            "only fictional role context; this ledger places those three under design context. "
            "The data family keeps twelve authored clauses unsupported even when a producer "
            "targets some of their IDs: a negative retention gate is not retired-media "
            "sanitization or physical movement, and a source index is not a regulator response. "
            "The selected BCM marker recovery likewise does not prove emergency ePHI access.",
            "",
            "Next source inclusion priority is SH-ENG-005 emergency-change after its "
            "standalone verifier review passes; it can "
            "address bounded architecture/change chronology without implying the whole "
            "24-route family is covered. It remains excluded from this snapshot. Then pursue "
            "a narrow product/customer commitment "
            "register (12 routes now zero partial-native) and a remaining workforce/ethics "
            "event cohort (16 of 24 routes lack a partial-native lead), each only if exact "
            "fictional authority and native events can be pinned. IAM005's five routes also "
            "need a specific service-identity population rather than generic access design.",
            "",
            "Keep qualified-owner/legal gates separate from source generation: the 66 "
            "unsupported provider/BA clauses include real contract/obligation and "
            "independent provider-response facts; twelve data clauses include rights, "
            "regulator, media and authorization activity; thirteen risk clauses require "
            "accepted governance, independence or closure; eight policy clauses still "
            "require approval/effective operation. No fictional source may substitute for "
            "a qualified decision or an external response.",
            "",
            "HIPAA rights/authorization, legal applicability, provider responses, physical media "
            "and regulator-access clauses remain unsupported where the exact source and authority "
            "are absent. The pending 22-item HIPAA addressable docket is separate from the "
            "generic POL-003 exception request. Source associations cannot establish a complete "
            "2027 population, actual operation, qualified review or professional audit conclusion.",
            "",
            "The next gate is a separate reviewed source registry for a fresh zero-evidence pair, "
            "then ordinary scoped collection and exact procedure work. This reconciliation writes "
            "no company source, audit task, workpaper, Key, Atlas or active A/B state.",
            "",
        ]
    )
    return "\n".join(parts)
