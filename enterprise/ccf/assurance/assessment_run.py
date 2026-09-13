"""Source-backed reference assessment with isolated, computed synthetic workflow checks."""

import argparse
import json
import tempfile
from datetime import datetime
from pathlib import Path

from enterprise.ccf.registry import compile_registry, digest

from . import actions, substantive
from .__main__ import read_json, write_json
from .completion import review_packet
from .engine import data, plan
from .iso import write_csv
from .reference import BOUNDARIES, reference_inputs
from .reference_exercise import exercise

VARIANTS = {
    "baseline": [],
    "iso27001": ["ISO27001"],
    "iso42001": ["ISO42001"],
    "c5": ["C5"],
    "combined": ["ISO27001", "ISO42001", "C5"],
}


def delta(baseline, target):
    """Compare stable work IDs; sharing a control never approves an additional duty."""
    base_controls = {r["control_id"] for r in baseline["controls"]}
    target_controls = {r["control_id"] for r in target["controls"]}
    base_actions = {r["id"]: r for r in baseline["actions"]}
    target_actions = {r["id"]: r for r in target["actions"]}
    if (
        len(target_actions) != len(target["actions"])
        or not base_actions.keys() <= target_actions.keys()
    ):
        raise ValueError("Selection duplicated work or dropped baseline actions")
    if len(target_controls) != len(target["controls"]):
        raise ValueError("Selection duplicated controls")
    if not base_controls <= target_controls:
        raise ValueError("Selection dropped baseline controls")
    for aid, original in base_actions.items():
        if not set(original["requirement_ids"]) <= set(target_actions[aid]["requirement_ids"]):
            raise ValueError("Selection dropped baseline requirement support")
        for key in ("procedure", "acceptance_test", "work_type"):
            if original[key] != target_actions[aid][key]:
                raise ValueError("Selection changed baseline procedure semantics")
    extra = sorted(target_actions.keys() - base_actions.keys())
    return dict(
        targets=target["targets"],
        baseline_preserved=True,
        reused_control_ids=sorted(base_controls),
        additional_candidate_control_ids=sorted(target_controls - base_controls),
        additional_action_ids=extra,
        shared_actions_with_added_requirements={
            aid: sorted(set(row["requirement_ids"]) - set(base_actions[aid]["requirement_ids"]))
            for aid, row in target_actions.items()
            if aid in base_actions
            and set(row["requirement_ids"]) != set(base_actions[aid]["requirement_ids"])
        },
        additional_work_on_shared_controls=sorted(
            {
                cid
                for aid in extra
                for cid in target_actions[aid]["control_ids"]
                if cid in base_controls
            }
        ),
        assessment_only_action_ids=[
            aid for aid in extra if target_actions[aid]["work_type"] == "ASSESSMENT_ONLY"
        ],
        capability_candidate_ids=[r["id"] for r in target["capability_candidates"]],
        acceptance="UNRESOLVED; sharing a control or artifact does not establish framework coverage",
    )


def evidence_checklist(baseline, designs, native):
    controls = {r["id"]: r["data"] for r in native["records"] if r["kind"] == "control"}
    rows = []
    for control in baseline["controls"]:
        cid = control["control_id"]
        design = designs[cid]
        for boundary in BOUNDARIES:
            rows.append(
                dict(
                    id=f"COLLECT:{cid}:{boundary}",
                    control_id=cid,
                    boundary_id=boundary,
                    owner_role_id=control["native_owner_role_id"],
                    owner_appointment=None,
                    trigger=controls[cid]["frequency_or_trigger"],
                    proposed_source_system=design["proposed_system_of_record"],
                    required_records=control["base_evidence"],
                    procedure=control["base_procedure"],
                    baseline_test=control["base_test"],
                    added_steps=control["proposed_steps"],
                    population=control["population_rule"],
                    extraction="Retain source query/filter, period, time zone, source count, excluded IDs and independent reconciliation for the events required by this control's trigger.",
                    period_start=None,
                    period_end=None,
                    population_count=None,
                    shared_artifact_candidate="ARTIFACT:" + cid,
                    sharing_rule="One corporate artifact may support several frameworks/sites only after separate boundary, period and exact-duty checks; local execution records remain necessary.",
                    boundary_test=control["boundary_rule"],
                    acceptance="Run the base and each applicable added test against reconciled actual records; record PASS/FAIL/UNTESTED per duty. Missing evidence stays UNTESTED, never PASS.",
                    failure_response=control["failure_response"],
                    evidence_ids=[],
                    test_result="UNTESTED",
                    review=None,
                )
            )
    return rows


def synthetic_cases():
    """Invented thresholds and facts demonstrate computation, not regulatory acceptance."""
    return [
        dict(
            id="DEMO-LEAVER-RENO",
            rule="elapsed",
            control="SH-IAM-004",
            boundary=BOUNDARIES[1],
            start="2026-09-09T10:00:00+00:00",
            end="2026-09-09T10:05:00+00:00",
            limit_minutes=30,
            source_record="DEMO-CORPORATE-LEAVER",
            framework_checks=["SOC2", "HIPAA"],
        ),
        dict(
            id="DEMO-LEAVER-BOISE",
            rule="elapsed",
            control="SH-IAM-004",
            boundary=BOUNDARIES[2],
            start="2026-09-09T10:00:00+00:00",
            end="2026-09-09T11:30:00+00:00",
            limit_minutes=30,
            source_record="DEMO-CORPORATE-LEAVER",
            framework_checks=["SOC2", "HIPAA"],
        ),
        dict(
            id="DEMO-RESTORE-NORMAL",
            rule="elapsed",
            control="SH-BCM-003",
            boundary=BOUNDARIES[2],
            start="2026-09-09T10:00:00+00:00",
            end="2026-09-09T10:25:00+00:00",
            limit_minutes=30,
            source_record="DEMO-RESTORE-NORMAL",
            framework_checks=["SOC2", "HIPAA"],
        ),
        dict(
            id="DEMO-RESTORE-COLD",
            rule="elapsed",
            control="SH-BCM-003",
            boundary=BOUNDARIES[2],
            start="2026-09-09T10:00:00+00:00",
            end="2026-09-09T11:30:00+00:00",
            limit_minutes=30,
            source_record="DEMO-RESTORE-COLD",
            framework_checks=["C5"],
        ),
        dict(
            id="DEMO-ISMS-APPROVER",
            rule="same_actor",
            control="SH-ERM-003",
            boundary=BOUNDARIES[0],
            expected_actor="DEMO-RISK-OWNER",
            actual_actor="DEMO-PROJECT-LEAD",
            source_record="DEMO-TREATMENT-APPROVAL",
            framework_checks=["ISO27001"],
        ),
        dict(
            id="DEMO-AI-LATE-IMPACT",
            rule="before",
            control="SH-AIM-002",
            boundary=BOUNDARIES[0],
            start="2026-09-09T11:00:00+00:00",
            end="2026-09-09T10:00:00+00:00",
            source_record="DEMO-IMPACT-AND-RELEASE",
            framework_checks=["ISO42001"],
        ),
        dict(
            id="DEMO-AI-PROSPECTIVE",
            rule="before",
            control="SH-AIM-002",
            boundary=BOUNDARIES[0],
            start="2026-09-10T09:00:00+00:00",
            end="2026-09-10T10:00:00+00:00",
            source_record="DEMO-IMPACT-AND-RELEASE-V2",
            framework_checks=["ISO42001"],
        ),
    ]


def evaluate_cases(cases):
    if len({r["id"] for r in cases}) != len(cases):
        raise ValueError("Duplicate synthetic case")
    results = []
    for row in cases:
        if not row["id"].startswith("DEMO-") or not row["source_record"].startswith("DEMO-"):
            raise ValueError("Synthetic identities must use DEMO namespace")
        if row["rule"] == "same_actor":
            observed = row["actual_actor"]
            passed = observed == row["expected_actor"]
        elif row["rule"] in {"elapsed", "before"}:
            start, end = datetime.fromisoformat(row["start"]), datetime.fromisoformat(row["end"])
            if start.tzinfo is None or end.tzinfo is None:
                raise ValueError("Synthetic event time requires a time zone")
            observed = (end - start).total_seconds() / 60
            passed = (
                0 <= observed <= row["limit_minutes"] if row["rule"] == "elapsed" else observed > 0
            )
        else:
            raise ValueError("Unknown synthetic rule")
        results.append(
            dict(
                case_id=row["id"],
                origin="SYNTHETIC",
                raw_sha256=digest(row),
                observed=observed,
                result="PASS" if passed else "FAIL",
                framework_checks=row["framework_checks"],
                control_id=row["control"],
                limitation="Demonstration only; invented thresholds/facts do not establish any real requirement result.",
            )
        )
    return results


def run(native, source_root):
    variants = {
        name: actions.plan(native, source_root, targets) for name, targets in VARIANTS.items()
    }
    baseline, combined = variants["baseline"], variants["combined"]
    comparisons = {name: delta(baseline, value) for name, value in variants.items()}
    single_actions = set().union(
        *({r["id"] for r in variants[name]["actions"]} for name in ("iso27001", "iso42001", "c5"))
    )
    if single_actions != {r["id"] for r in combined["actions"]}:
        raise ValueError("Combined selection does not equal the union of individual work")
    c, a = reference_inputs(native, False)
    actual_plan = plan(c, a, native)
    if a.evidence or a.tests or any(i.state != "PROPOSED" for i in a.implementations):
        raise ValueError("Real reference draft contaminated with synthetic execution")
    stages, ledger = exercise(native)
    designs = {r["control_id"]: r for r in review_packet(native)["controls"]}
    checklist = evidence_checklist(baseline, designs, native)
    cases = synthetic_cases()
    source_dependencies = [
        dict(**g, blocks_framework=g["requirement_id"].split(":")[0])
        for g in read_json(actions.DATA / "source_gates.json")
    ]
    source_dependencies.extend(
        [
            dict(
                id="HIPAA-CURRENT-LAW",
                blocks_framework="HIPAA",
                status="QUALIFIED_STATUS_RECONCILIATION_REQUIRED",
                reason="Pinned XML is a historical source; reconcile judicial/amendment status before using printed provisions as operative law.",
                source="https://www.hhs.gov/hipaa/for-professionals/special-topics/reproductive-health/final-rule-fact-sheet/index.html",
            ),
            dict(
                id="C5-CONTEXT",
                acquired_reference=dict(
                    title="BSI Standard 200-4, German, 2023",
                    sha256="eb59cc6b0fe143f7911c4e273dde469d75291319d44f741183273a63e8cef9fb",
                    status="ACQUISITION_RECORDED_2026_09_12_NOT_CONTENT_ACCEPTANCE",
                    url="https://www.bsi.bund.de/SharedDocs/Downloads/DE/BSI/Grundschutz/BSI_Standards/standard_200_4.pdf?__blob=publicationFile&v=7",
                    limitation="Original retained in private SABLEHARBOR generated holdings; this bundle records provenance, not ongoing file availability or qualified interpretation.",
                ),
                blocks_framework="C5",
                status="FULL_CONTEXT_AND_REFERENCED_METHOD_REVIEW_REQUIRED",
                reason="Review linked information and separate customer responsibilities for 168 parents; reconcile BCM-01 with ISO22301 and/or BSI200-4. An old BSI100-4 translation is not a substitute.",
            ),
        ]
    )
    return dict(
        schema_version="CCF-REFERENCE-ASSESSMENT-RUN-1",
        status="PREPARATION_AND_SYNTHETIC_EXERCISE_NOT_ASSURANCE",
        source_backed_reference=dict(catalog=data(c), assessment=data(a), result=actual_plan),
        evidence_checklist=checklist,
        source_dependencies=source_dependencies,
        canonical_actions=combined["actions"],
        canonical_controls=combined["controls"],
        variant_comparisons=comparisons,
        variant_action_requirements={
            name: {r["id"]: r["requirement_ids"] for r in v["actions"]}
            for name, v in variants.items()
        },
        synthetic=dict(
            raw_cases=cases,
            computed_tests=evaluate_cases(cases),
            stages=[
                dict(name=name, catalog=data(cat), assessment=data(assessed), result=result)
                for name, cat, assessed, result in stages
            ],
            finding_ledger=ledger,
            boundary="Synthetic stage reviews and evidence use fictional catalogues and never enter the real reference assessment.",
        ),
        operating_inputs=[
            "Actual legal entities, service/system inventory and corporate/site responsibility split",
            "Actual PHI flows, BA/subcontractor agreements and permitted processing purposes",
            "Named owners, security official, risk authorities and independent reviewers",
            "Accepted evidence period, authoritative source systems and complete populations",
            "Actual service/recovery commitments, selected C5 criteria and product capabilities",
            "AI inventory, intended uses, lifecycle roles, affected parties and impact criteria when selecting ISO42001",
        ],
        summary=dict(
            baseline_controls=len(baseline["controls"]),
            checklist_rows=len(checklist),
            canonical_controls=len(combined["controls"]),
            canonical_actions=len(combined["actions"]),
            framework_variants=len(variants),
            combined_equals_union=True,
            synthetic_cases=len(cases),
            synthetic_stages=len(stages),
            real_evidence=0,
            real_tests=0,
            real_accepted_coverage=0,
        ),
    )


def build(output, native, source_root):
    output = Path(output)
    if output.exists():
        raise ValueError("Assessment output must be a new directory")
    result = run(native, source_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ccf-assessment-run-", dir=output.parent) as tmp:
        staged = Path(tmp) / "bundle"
        staged.mkdir(mode=0o700)
        write_json(staged / "ASSESSMENT_RUN.json", result)
        write_csv(staged / "EVIDENCE_CHECKLIST.csv", result["evidence_checklist"])
        write_json(staged / "SOURCE_DEPENDENCIES.json", result["source_dependencies"])
        write_json(staged / "FRAMEWORK_DELTAS.json", result["variant_comparisons"])
        write_json(staged / "SYNTHETIC_EXERCISE.json", result["synthetic"])
        (staged / "EVIDENCE_CHECKLIST.md").write_text(
            "# Baseline evidence collection\n\nNo actual evidence has been supplied. Every row remains untested.\n\n"
            + "\n\n".join(
                f"## {r['id']}\n\nSource: {r['proposed_source_system']}\n\nTrigger: {r['trigger']}\n\nRecords: {', '.join(r['required_records'])}\n\nPopulation: {r['population']}\n\nTest: {r['baseline_test']}\n\nBoundary: {r['boundary_test']}\n\nAdditional source-specific steps: {', '.join(s['action_id'] for s in r['added_steps']) or 'None in current author layer'}"
                for r in result["evidence_checklist"]
            )
            + "\n"
        )
        (staged / "START_HERE.md").write_text(
            "# Working reference assessment\n\n[Evidence checklist](EVIDENCE_CHECKLIST.md) · [Checklist CSV](EVIDENCE_CHECKLIST.csv) · [Framework deltas](FRAMEWORK_DELTAS.json) · [Synthetic exercise](SYNTHETIC_EXERCISE.json) · [Source dependencies](SOURCE_DEPENDENCIES.json) · [Complete assessment](ASSESSMENT_RUN.json)\n\n"
            + "```json\n"
            + json.dumps(result["summary"], indent=2)
            + "\n```\n\n"
            + "SOC2/HIPAA remains the approved reference baseline. Each extension preserves baseline controls and procedures; combined actions equal the union of single-framework selections with no duplicate work IDs. Shared control/evidence candidates still need separate requirement and boundary tests.\n\n"
            + "The synthetic exercise computes seven example results from raw events and preserves five assurance-engine lifecycle stages, including a failure, same-period retest and prospective correction. The engine stages use fictional objectives; computed examples do not certify ISO or any other framework. The source-backed reference retains its existing SYNTHETIC planning-scope label and contains no execution evidence, tests or approvals. It is not an actual operating assessment. All 210 collection rows remain untested.\n\n"
            + "Source/context reconciliation and actual operating inputs remain explicit dependencies. Neither the existence of a source nor an authored comparison is independent acceptance.\n\n"
            + "## Operating inputs\n\n"
            + "\n".join("- " + x for x in result["operating_inputs"])
            + "\n"
        )
        write_json(staged / "REVIEW_MANIFEST.json", dict(files=substantive.members(staged)))
        for p in staged.rglob("*"):
            p.chmod(0o700 if p.is_dir() else 0o600)
        staged.rename(output)
    return result["summary"]


def verify(output, native, source_root):
    output = Path(output)
    if output.is_symlink() or any(p.is_symlink() for p in output.rglob("*")):
        raise ValueError("Assessment bundle cannot contain symlinks")
    if read_json(output / "REVIEW_MANIFEST.json")["files"] != substantive.members(output):
        raise ValueError("Assessment member/hash mismatch")
    with tempfile.TemporaryDirectory() as tmp:
        expected = Path(tmp) / "bundle"
        build(expected, native, source_root)
        if (expected / "REVIEW_MANIFEST.json").read_bytes() != (
            output / "REVIEW_MANIFEST.json"
        ).read_bytes():
            raise ValueError("Assessment differs from source re-performance")
    return dict(verified=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "verify"])
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        result = (build if args.command == "build" else verify)(
            args.output, compile_registry(), args.source_root
        )
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"Reference assessment error: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
