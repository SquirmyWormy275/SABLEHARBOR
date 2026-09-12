"""Generate proposed shared-control enhancements and selectable implementation deltas."""

import argparse
import json
import tempfile
from collections import Counter
from pathlib import Path

from enterprise.ccf.registry import compile_registry, digest

from . import substantive
from .__main__ import read_json, write_json
from .completion import review_packet
from .iso import write_csv
from .preparation import indexed

DATA = Path(__file__).with_name("action_data")
TARGETS = {"ISO27001", "ISO42001", "C5"}
GATES = [
    dict(
        id="GATE-SERVICE-FACTS",
        title="Confirm actual service and operating facts",
        owner="Service owner",
        acceptance="Approved entity, boundary, data flows, agreements, system populations, execution owners and evidence period; preserve reference facts separately.",
    ),
    dict(
        id="GATE-QUALIFIED-REVIEW",
        title="Resolve source interpretation and independent design review",
        owner="Qualified source reviewer and independent assurance reviewer",
        acceptance="Source edition/status, exact conditions and exceptions, scoped applicability and design sufficiency have recorded, attributable decisions.",
    ),
    dict(
        id="GATE-C5-SELECTION",
        title="Choose C5 criteria and confirm capability facts",
        owner="Service owner with assessor",
        acceptance="Record selected basic/additional criteria, applicability, parent guidance and customer/provider split. Reno/Boise remains the reference; no third site or product capability is presumed.",
    ),
    dict(
        id="GATE-AI-FACTS",
        title="Confirm AI systems, roles and intended uses",
        owner="AIMS accountable management",
        acceptance="Approved AI inventory, use context, provider/user roles, affected parties, lifecycle boundaries and impact/risk criteria.",
    ),
]


def author_bindings(native):
    """Explicit author snapshot; callers must reconsider changes before persisting it."""
    return dict(
        previous_review=substantive.finding_bindings(native),
        baseline_checks=digest(read_json(DATA / "baseline_checks.json")),
        source_gates=digest(read_json(DATA / "source_gates.json")),
        finding_actions=digest(read_json(DATA / "finding_actions.json")),
        dependency_gates=digest(GATES),
        c5_child_checks=digest(read_json(DATA / "c5_child_checks.json")),
    )


def plan(native, source_root, targets):
    targets = list(targets)
    if len(targets) != len(set(targets)) or not set(targets) <= TARGETS:
        raise ValueError("Select distinct supported extension targets")
    # Reperform original findings and source verification before applying the new author layer.
    reviewed = substantive.analysis(native, source_root)
    if author_bindings(native) != read_json(DATA / "author_bindings.json"):
        raise ValueError("Action analysis is stale; author reconsideration required")
    all_rows = {r["requirement_id"]: r for r in reviewed["requirement_review"]}
    frameworks = {"SOC2", "HIPAA", *targets}
    selected = {rid for rid, r in all_rows.items() if r["framework_id"] in frameworks}
    checks = read_json(DATA / "baseline_checks.json")
    gates = read_json(DATA / "source_gates.json")
    expected = {
        rid for rid, r in all_rows.items() if r["review_depth"] == "PRIOR_SECTION_ANALYSIS_ONLY"
    }
    if len(checks) != len(expected) or {r["requirement_id"] for r in checks} != expected:
        raise ValueError("Baseline check population differs")
    expected_gates = {
        rid for rid, r in all_rows.items() if r["review_depth"] == "NOT_SUBSTANTIVELY_REVIEWED"
    }
    if len(gates) != len(expected_gates) or {r["requirement_id"] for r in gates} != expected_gates:
        raise ValueError("Source gate population differs")
    for row in checks + gates:
        if (
            not row["source_condition"]
            or not row["procedure_and_test"]
            or row["review"] is not None
        ):
            raise ValueError("Incomplete or improperly approved author check")
    finding_actions = read_json(DATA / "finding_actions.json")
    actions = {r["finding_id"]: r for r in finding_actions}
    findings = {r["id"]: r for r in reviewed["findings"]}
    if len(actions) != len(finding_actions) or actions.keys() != findings.keys():
        raise ValueError("Finding action population differs")
    controls = {r["control_id"]: dict(r) for r in review_packet(native)["controls"]}
    enhancements = {cid: [] for cid in controls}
    backlog, capabilities, expanded_checks = [], [], []
    dependency_ids = {g["id"] for g in GATES}
    for fid, action in actions.items():
        if action["work_type"] not in {"ASSESSMENT_ONLY", "ENHANCE_EXISTING_CONTROL"}:
            raise ValueError("Unknown action classification")
        if not set(action["dependencies"]) <= dependency_ids:
            raise ValueError("Unknown action dependency")
        finding = findings[fid]
        reqs = sorted(set(finding["requirement_ids"]) & selected)
        if not reqs:
            continue
        row = dict(
            id="ACTION-" + fid,
            finding_id=fid,
            requirement_ids=reqs,
            source_locator=finding["source_locator"],
            control_ids=finding["control_ids"],
            work_type=action["work_type"],
            priority=action["priority"],
            priority_basis=action["priority_basis"],
            dependencies=action["dependencies"],
            proposed_owner_roles=sorted(
                {controls[c]["native_owner_role_id"] for c in finding["control_ids"]}
            ),
            problem=finding["observed_design_gap"],
            procedure=finding["corrective_procedure"],
            evidence_required=action["evidence_required"],
            acceptance_test=finding["test_procedure"],
            remaining_decision=finding["remaining_decision"],
            status="PROPOSED_NOT_EXECUTED",
            review=None,
            activation="Resolve applicability for each listed requirement and boundary before execution. Retain conditional/basic/additional distinctions in the authored procedure.",
        )
        backlog.append(row)
        if action["work_type"] == "ENHANCE_EXISTING_CONTROL":
            for cid in finding["control_ids"]:
                enhancements[cid].append(row["id"])
        if "capability_candidate" in action:
            capabilities.append(
                dict(
                    **action["capability_candidate"],
                    action_id=row["id"],
                    requirement_ids=reqs,
                    implementation="NOT_ASSERTED",
                    review=None,
                )
            )
    hipaa = indexed("hipaa_analysis.json", "locator")
    for check in checks + gates:
        rid = check["requirement_id"]
        if rid not in selected:
            continue
        original = all_rows[rid]
        cids = sorted(
            original["existing_candidate_procedures"] or check.get("proposed_control_ids", [])
        )
        # Legal-role/context work stays outside the operating-control delta count.
        assessment_only = rid.startswith("HIPAA:") or rid in expected_gates
        if rid == "ISO27001:AMD1-4.1-4.2":
            assessment_only = False
        row = dict(
            id="CHECK-" + rid,
            requirement_ids=[rid],
            control_ids=cids,
            work_type="ASSESSMENT_ONLY" if assessment_only else "ENHANCE_EXISTING_CONTROL",
            priority=check.get("priority", "P0"),
            activation=check.get("activation", "Before relying on the selected framework context."),
            priority_basis="Resolve role, source and triggered legal-response treatment"
            if assessment_only
            else "Make baseline procedure and evidence test explicit before reliance",
            dependencies=["GATE-SERVICE-FACTS", "GATE-QUALIFIED-REVIEW"],
            proposed_owner_roles=sorted({controls[c]["native_owner_role_id"] for c in cids})
            or ["Qualified framework reviewer"],
            problem=check["source_condition"],
            procedure=check["procedure_and_test"],
            acceptance_test=check["procedure_and_test"],
            evidence_required=[
                dict(artifact="Scoped condition workpaper", must_show=check["procedure_and_test"])
            ],
            remaining_decision=check.get(
                "remaining_dependency",
                "Actual facts, exact exceptions and qualified applicability/design decision",
            ),
            status="PROPOSED_NOT_EXECUTED",
            review=None,
        )
        backlog.append(row)
        if not assessment_only:
            for cid in cids:
                enhancements[cid].append(row["id"])
        expanded_checks.append(
            dict(
                **check,
                requirement_digest=original["requirement_digest"],
                source_id=original["source_id"],
                existing_procedures=original["existing_candidate_procedures"],
                source_role=hipaa.get(rid.split(":", 1)[1], {}).get("proposed_role_treatment")
                if rid.startswith("HIPAA:")
                else None,
                action_id=row["id"],
                scope="Targeted check, not full paragraph/exception acceptance",
            )
        )
    child_checks = read_json(DATA / "c5_child_checks.json")
    child_check_map = {r["requirement_id"]: r for r in child_checks}
    source_children = {r["requirement_id"]: r for r in reviewed["source_detail"]["c5_children"]}
    if len(child_checks) != 623 or child_check_map.keys() != source_children.keys():
        raise ValueError("C5 child comparison population differs")
    for check in child_checks:
        if (
            check["control_id"] not in controls
            or not check["comparison_and_test"]
            or check["review"] is not None
            or check["work_type"]
            not in {"ASSESSMENT_ONLY", "REUSE_VALIDATION", "ENHANCE_EXISTING_CONTROL"}
        ):
            raise ValueError("Invalid C5 child comparison")
        rid = check["requirement_id"]
        if rid not in selected:
            continue
        cid = check["control_id"]
        row = dict(
            id="CHILD-" + rid,
            requirement_ids=[rid],
            control_ids=[cid],
            work_type=check["work_type"],
            priority="P1",
            priority_basis="Resolve the selected criterion against the actual proposed procedure before relying on C5 coverage",
            dependencies=["GATE-SERVICE-FACTS", "GATE-QUALIFIED-REVIEW", "GATE-C5-SELECTION"],
            proposed_owner_roles=[controls[cid]["native_owner_role_id"]],
            problem=check["comparison_and_test"],
            procedure=check["comparison_and_test"],
            acceptance_test=check["comparison_and_test"],
            evidence_required=[
                dict(
                    artifact="Criterion-specific execution and test record",
                    must_show=check["comparison_and_test"],
                )
            ],
            remaining_decision="Exact applicability, parent guidance, customer/provider split and independent sufficiency decision",
            publisher_kind=source_children[rid]["kind"],
            source_binding=source_children[rid],
            status="PROPOSED_NOT_EXECUTED",
            review=None,
        )
        backlog.append(row)
        if check["work_type"] == "ENHANCE_EXISTING_CONTROL":
            enhancements[cid].append(row["id"])
    by_action = {r["id"]: r for r in backlog}
    if len(by_action) != len(backlog):
        raise ValueError("Duplicate action")
    used = {cid for rid in selected for cid in all_rows[rid]["existing_candidate_procedures"]}
    used |= {cid for r in backlog for cid in r["control_ids"]}
    library = []
    for cid in sorted(used):
        base = controls[cid]
        steps = [by_action[aid] for aid in sorted(enhancements[cid])]
        library.append(
            dict(
                control_id=cid,
                native_owner_role_id=base["native_owner_role_id"],
                base_design_digest=base["design_digest"],
                base_procedure=base["procedure"],
                base_evidence=base["evidence_outputs"],
                base_test=base["test_procedure"],
                classification="ENHANCED_PROCEDURE_CANDIDATE"
                if steps
                else "REUSE_CANDIDATE_NOT_COVERAGE_ACCEPTANCE",
                proposed_steps=[
                    dict(
                        action_id=s["id"],
                        requirement_ids=s["requirement_ids"],
                        procedure=s["procedure"],
                        evidence_required=s["evidence_required"],
                        test=s["acceptance_test"],
                        dependencies=s["dependencies"],
                    )
                    for s in steps
                ],
                boundary_rule=base["inheritance"],
                population_rule=base["test_population"],
                failure_response=base["failure_response"],
                implementation="NOT_ASSERTED",
                review=None,
            )
        )
    # Individual comparison workpapers carry exact source fingerprints and exact candidate procedures.
    # Domain proposals remain visibly separate and cannot become child mappings by being joined.
    c5 = []
    if "C5" in targets:
        for child in reviewed["source_detail"]["c5_children"]:
            rid = child["requirement_id"]
            prior = all_rows[rid]
            matching = [r for r in backlog if rid in r["requirement_ids"]]
            cids = sorted(
                {
                    cid
                    for r in matching
                    if r["work_type"] != "ASSESSMENT_ONLY"
                    for cid in r["control_ids"]
                }
            )
            c5.append(
                dict(
                    **child,
                    requirement_digest=prior["requirement_digest"],
                    targeted_action_ids=[r["id"] for r in matching],
                    targeted_comparisons=[
                        dict(
                            action_id=r["id"],
                            observed_gap=r["problem"],
                            proposed_change=r["procedure"],
                            test=r["acceptance_test"],
                        )
                        for r in matching
                    ],
                    individually_proposed_procedures={
                        cid: dict(
                            procedure=controls[cid]["procedure"],
                            test=controls[cid]["test_procedure"],
                            design_digest=controls[cid]["design_digest"],
                        )
                        for cid in cids
                    },
                    domain_candidate_procedures={
                        cid: controls[cid]["procedure"]
                        for cid in prior["proposed_domain_control_ids"]
                    },
                    author_child_comparison=child_check_map[rid],
                    comparison_depth="AUTHOR_CHILD_CONDITION_COMPARISON_NOT_ACCEPTANCE",
                    remaining_work="Reconcile full parent guidance, all compound duties/exceptions, actual scope and customer responsibilities; independently challenge this first-pass author comparison. Domain routes are not child mappings.",
                    review=None,
                )
            )
    active_gates = [
        g
        for g in GATES
        if g["id"] not in {"GATE-C5-SELECTION", "GATE-AI-FACTS"}
        or (g["id"] == "GATE-C5-SELECTION" and "C5" in targets)
        or (g["id"] == "GATE-AI-FACTS" and "ISO42001" in targets)
    ]
    return dict(
        schema_version="CCF-ACTIONABLE-DELTA-1",
        targets=sorted(targets),
        baseline=["SOC2", "HIPAA"],
        status="PROPOSED_DESIGNS_AND_OPEN_IMPLEMENTATION_WORK",
        author_snapshot=author_bindings(native),
        dependency_gates=active_gates,
        controls=library,
        actions=sorted(backlog, key=lambda r: (r["priority"], r["id"])),
        capability_candidates=capabilities,
        baseline_and_context_checks=expanded_checks,
        c5_criterion_workpapers=c5,
        summary=dict(
            selected_requirements=len(selected),
            controls=len(library),
            procedure_classes=dict(Counter(r["classification"] for r in library)),
            actions=len(backlog),
            action_classes=dict(Counter(r["work_type"] for r in backlog)),
            capability_candidates=len(capabilities),
            baseline_checks=sum(r["requirement_id"] in expected for r in expanded_checks),
            source_context_checks=sum(
                r["requirement_id"] in expected_gates for r in expanded_checks
            ),
            c5_criterion_workpapers=len(c5),
            c5_comparison_depth=dict(Counter(r["comparison_depth"] for r in c5)),
            accepted_coverage=0,
            actual_implementations=0,
        ),
    )


def build(output, native, source_root, targets):
    output = Path(output)
    if output.exists():
        raise ValueError("Action output must be a new directory")
    result = plan(native, source_root, targets)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ccf-actions-", dir=output.parent) as tmp:
        staged = Path(tmp) / "bundle"
        staged.mkdir(mode=0o700)
        write_json(staged / "ACTION_PLAN.json", result)
        for name, key in [
            ("IMPLEMENTATION_BACKLOG", "actions"),
            ("SHARED_CONTROL_LIBRARY", "controls"),
            ("CAPABILITY_CANDIDATES", "capability_candidates"),
            ("BASELINE_AND_CONTEXT_CHECKS", "baseline_and_context_checks"),
            ("C5_CRITERION_WORKPAPERS", "c5_criterion_workpapers"),
        ]:
            fields = sorted({field for row in result[key] for field in row})
            if result[key]:
                write_csv(
                    staged / (name + ".csv"),
                    [{field: row.get(field) for field in fields} for row in result[key]],
                )
            else:
                # Empty target selections still have a valid, header-only CSV.
                (staged / (name + ".csv")).write_text(
                    "id\n" if key == "capability_candidates" else "requirement_id\n"
                )
        (staged / "SHARED_CONTROL_LIBRARY.md").write_text(
            "# Proposed shared control procedures\n\nEvery addition retains its source action and activation dependencies. No deployment or approval is asserted.\n\n"
            + "\n\n".join(
                f"## {c['control_id']}\n\nOwner role: {c['native_owner_role_id']}\n\nBase: {c['base_procedure']}\n\n"
                + "\n\n".join(
                    f"### {s['action_id']}\n\nRequirements: {', '.join(s['requirement_ids'])}\n\n{s['procedure']}\n\nTest: {s['test']}"
                    for s in c["proposed_steps"]
                )
                for c in result["controls"]
            )
            + "\n"
        )
        (staged / "IMPLEMENTATION_BACKLOG.md").write_text(
            "# Prioritized implementation backlog\n\nP0 resolves prerequisites; P1 implements/tests affected procedures before reliance; P2 retains contextual or event-triggered legal work until needed. Priorities are proposed sequencing, not invented deadlines or severity ratings.\n\n"
            + "\n\n".join(
                f"## {r['id']} — {r['priority']}\n\nType: {r['work_type']}\n\nOwners: {', '.join(r['proposed_owner_roles'])}\n\nDependencies: {', '.join(r['dependencies'])}\n\nProblem: {r['problem']}\n\nProcedure: {r['procedure']}\n\nAcceptance test: {r['acceptance_test']}\n\nRemaining input: {r['remaining_decision']}"
                for r in result["actions"]
            )
            + "\n"
        )
        (staged / "START_HERE.md").write_text(
            "# SABLEHARBOR actionable control deltas\n\n[Shared procedures](SHARED_CONTROL_LIBRARY.md) · [Implementation backlog](IMPLEMENTATION_BACKLOG.md) · [Capability candidates](CAPABILITY_CANDIDATES.csv) · [Baseline/context checks](BASELINE_AND_CONTEXT_CHECKS.csv) · [C5 individual workpapers](C5_CRITERION_WORKPAPERS.csv) · [Full data](ACTION_PLAN.json)\n\n"
            + "```json\n"
            + json.dumps(result["summary"], indent=2)
            + "\n```\n\n"
            + "Baseline remains SOC2/HIPAA. Extensions select proposed design work, not accepted certification scope. Reuse is a candidate, enhancements are proposed steps, and capability candidates require actual product facts before they become new controls. Legal/assessment work is counted separately.\n\n"
            + "All 116 prior section-only baseline entries now have targeted source conditions and tests; this does not establish exhaustive coverage. Three context/amendment entries have concrete procedures and explicit remaining dependencies. All 623 C5 children now have individually authored condition/procedure comparisons and test directions; full parent-guidance/exception reconciliation and independent acceptance remain open.\n\n"
            + "ISO27000:2026 and ISO22989:2022 full reference reconciliation and full AI Annex B review remain open. Actual appointments, systems, contracts, source judgments and evidence cannot be generated from the reference scenario. Atlas remains read-only.\n"
        )
        write_json(
            staged / "REVIEW_MANIFEST.json",
            dict(targets=sorted(targets), files=substantive.members(staged)),
        )
        for p in staged.rglob("*"):
            p.chmod(0o700 if p.is_dir() else 0o600)
        staged.rename(output)
    return result["summary"]


def verify(output, native, source_root):
    output = Path(output)
    if output.is_symlink() or any(p.is_symlink() for p in output.rglob("*")):
        raise ValueError("Action bundle cannot contain symlinks")
    manifest = read_json(output / "REVIEW_MANIFEST.json")
    if manifest["files"] != substantive.members(output):
        raise ValueError("Action member/hash mismatch")
    with tempfile.TemporaryDirectory() as tmp:
        expected = Path(tmp) / "bundle"
        build(expected, native, source_root, manifest["targets"])
        if (expected / "REVIEW_MANIFEST.json").read_bytes() != (
            output / "REVIEW_MANIFEST.json"
        ).read_bytes():
            raise ValueError("Action bundle differs from source re-performance")
    return dict(verified=True, targets=manifest["targets"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "verify"])
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--target", action="append", choices=sorted(TARGETS), default=[])
    args = parser.parse_args()
    if args.command == "verify" and args.target:
        parser.error("Verification uses targets from the bundle")
    try:
        native = compile_registry()
        result = (
            build(args.output, native, args.source_root, args.target)
            if args.command == "build"
            else verify(args.output, native, args.source_root)
        )
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"CCF action error: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
