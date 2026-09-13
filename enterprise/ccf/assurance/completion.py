"""Build a source-bound control library and attribute-level review preparation packet."""

import argparse
import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path

from enterprise.ccf.registry import compile_registry, digest

from .__main__ import read_json, write_json
from .engine import data
from .iso import iso_inputs, write_csv
from .preparation import designs
from .reference import validate_source_inventory

DATA = Path(__file__).with_name("completion_data")
TARGETS = ["ISO27001", "ISO42001", "C5"]


def library(native, catalog, assessment):
    baseline = designs(native)
    controls = {r["id"]: r for r in native["records"] if r["kind"] == "control"}
    extra = read_json(DATA / "control_procedures.json")
    authored = {r["control_id"]: r for r in extra}
    base = {r["control_id"]: r for r in baseline["controls"]}
    used = {i.control_id for i in assessment.implementations}
    if len(authored) != len(extra) or set(authored) & set(base):
        raise ValueError("Duplicate completion control procedure")
    if set(base) | set(authored) != used:
        raise ValueError(
            "Control design population differs from selected implementation candidates"
        )
    required = {
        "procedure",
        "proposed_system_of_record",
        "evidence_outputs",
        "reviewer_role_description",
        "test_procedure",
        "operating_inputs_needed",
    }
    for row in extra:
        if not required <= row.keys() or any(not row[k] for k in required):
            raise ValueError("Incomplete extension procedure")
    result = []
    for cid in sorted(used):
        r = dict(base[cid] if cid in base else authored[cid])
        native_control = controls[cid]
        r.update(
            control_digest=digest(native_control),
            objective=native_control["data"]["statement"],
            native_owner_role_id=native_control["data"]["owner_role_id"],
            native_trigger=native_control["data"]["frequency_or_trigger"],
            status="DRAFT_DESIGN_NOT_DEPLOYED",
            review=None,
            requirement_ids=sorted(
                {m.requirement_id for m in catalog.mappings if m.control_id == cid}
            ),
            applicability_conditions="Determine actual service/system, obligations and risk treatment for each boundary; a candidate route is not an applicability decision.",
            execution_boundaries=list(assessment.scope.boundaries),
            inheritance="Corporate execution requires a documented responsibility split and evidence that it covers the site/system; retain local complementary measures.",
            test_population="Reconcile independent source records to all occurrences in the accepted period and boundary before risk-based selection. Record query, exclusions and selection rationale; no invented sample size.",
            failure_response="Record failed, missing and untested steps separately, preserve original evidence, assign remediation and independently retest. A later pass does not repair an earlier period.",
            acceptance="Every relevant step and evidence output must be tested against accepted source attributes and actual criteria. Draft availability is not design adequacy or effectiveness.",
        )
        if cid in base:
            r["test_procedure"] = (
                "For independently selected occurrences, walk the authored procedure in order and "
                "trace each action to dated, scoped records. Inspect these control-specific outputs: "
                + "; ".join(r["evidence_outputs"])
                + ". Reperform the recorded decision or reconciliation and inspect a failure/exception path. "
                "Resolve exact source-level acceptance criteria before using this proposed test."
            )
        r["design_digest"] = digest(r)
        result.append(r)
    return result


def review_packet(native):
    catalog, assessment = iso_inputs(native, TARGETS)
    controls = library(native, catalog, assessment)
    by_control = {r["control_id"]: r for r in controls}
    sources = {s.id: s for s in catalog.sources}
    selected = {a.requirement_id for a in assessment.applicability}
    measures = read_json(DATA / "additional_measures.json")
    if len({m["id"] for m in measures}) != len(measures) or any(
        m["requirement_id"] not in selected or not m["procedure"] or not m["test_procedure"]
        for m in measures
    ):
        raise ValueError("Invalid additional-measure inventory")
    mappings = {}
    for m in catalog.mappings:
        for aid in m.attribute_ids:
            mappings.setdefault((m.requirement_id, aid), []).append(m)
    rows = []
    for r in catalog.requirements:
        if r.id not in selected:
            continue
        source = sources[r.source_id]
        for attr in r.attributes:
            candidates = mappings.get((r.id, attr.id), [])
            ids = sorted({m.control_id for m in candidates})
            rows.append(
                dict(
                    workpaper_id=r.id + ":" + attr.id,
                    framework_id=r.framework_id,
                    requirement_id=r.id,
                    attribute_id=attr.id,
                    attribute_kind=attr.kind,
                    objective=attr.objective,
                    locator=r.locator,
                    source_id=source.id,
                    source_sha256=source.content_sha256,
                    requirement_digest=digest(data(r)),
                    candidate_control_ids=ids,
                    candidate_mapping_digests={m.id: digest(data(m)) for m in candidates},
                    candidate_design_digests={cid: by_control[cid]["design_digest"] for cid in ids},
                    routing="CANDIDATE_DESIGN_AVAILABLE"
                    if ids
                    else "NO_CONTROL_ROUTE_REVIEW_REQUIRED",
                    routing_limit="Assessment/context attributes may require review work instead of a new control. No route does not automatically mean a missing control; a route does not establish coverage.",
                    uncovered=[m.uncovered for m in candidates],
                    proposed_measure_ids=[m["id"] for m in measures if m["requirement_id"] == r.id],
                    source_condition_analysis=None,
                    design_sufficiency_analysis=None,
                    proposed_additional_measures=None,
                    reviewer_decision="PENDING",
                    review=None,
                    boundary_decisions=[
                        dict(
                            boundary_id=b, applicability="UNRESOLVED", implementation="NOT_ASSERTED"
                        )
                        for b in assessment.scope.boundaries
                    ],
                )
            )
    return dict(
        schema_version="CCF-COMPLETION-PREPARATION-1",
        status="DRAFT_LIBRARY_AND_REVIEW_WORK_NOT_ASSURANCE",
        native_snapshot_id=digest(native),
        catalog_digest=digest(data(catalog)),
        targets=TARGETS,
        controls=controls,
        additional_measures=measures,
        coverage_workpapers=rows,
        summary=dict(
            controls=len(controls),
            baseline_procedures=64,
            extension_procedures=len(controls) - 64,
            inventoried_requirements=len(selected),
            inventoried_attributes=len(rows),
            routing_counts=dict(Counter(r["routing"] for r in rows)),
            framework_attribute_counts=dict(Counter(r["framework_id"] for r in rows)),
            accepted_coverage=0,
            additional_measures=len(measures),
            normative_completeness="NOT_ESTABLISHED",
        ),
    )


def members(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and p != root / "MANIFEST.json"
    }


def build_completion(output, native, source_root):
    output = Path(output)
    if output.exists():
        raise ValueError("Completion output must be a new directory")
    catalog, _ = iso_inputs(native, TARGETS)
    validate_source_inventory(catalog, source_root)
    packet = review_packet(native)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ccf-completion-", dir=output.parent) as tmp:
        staged = Path(tmp) / "bundle"
        staged.mkdir(mode=0o700)
        write_json(staged / "REVIEW_PACKET.json", packet)
        write_csv(staged / "COVERAGE_REVIEW.csv", packet["coverage_workpapers"])
        write_csv(staged / "ADDITIONAL_MEASURES.csv", packet["additional_measures"])
        write_csv(
            staged / "CONTROL_LIBRARY.csv",
            [
                {
                    k: r[k]
                    for k in (
                        "control_id",
                        "objective",
                        "native_owner_role_id",
                        "native_trigger",
                        "procedure",
                        "evidence_outputs",
                        "test_population",
                        "test_procedure",
                        "operating_inputs_needed",
                        "applicability_conditions",
                        "inheritance",
                        "failure_response",
                        "status",
                        "design_digest",
                    )
                }
                for r in packet["controls"]
            ],
        )
        (staged / "DECISIONS.md").write_bytes((DATA / "DECISIONS.md").read_bytes())
        (staged / "START_HERE.md").write_text(
            "# CCF control library and coverage review\n\n"
            "[Control library](CONTROL_LIBRARY.csv) · [Coverage workpapers](COVERAGE_REVIEW.csv) · "
            "[Additional measures](ADDITIONAL_MEASURES.csv) · "
            "[Structured packet](REVIEW_PACKET.json) · [Operating decisions](DECISIONS.md)\n\n"
            "The selected SOC 2/HIPAA/ISO27001/ISO42001/C5 inventory has "
            f"{packet['summary']['controls']} draft control procedures and "
            f"{packet['summary']['inventoried_attributes']} attribute workpapers. "
            "These counts describe inventoried draft work, not normative completeness or accepted coverage.\n\n"
            "First decompose exact source conditions and linked context; compare candidate designs and "
            "record missing measures. Then resolve actual scope, risk and responsibility facts for each "
            "boundary. All source and mapping reviews remain pending. Do not edit this generated packet "
            "to assert approval: record accepted reviews in the version-bound assessment workflow.\n\n"
            "Original sources remain local. Atlas was used only as a reference guide. "
            "Verification checks source bytes and regenerates the packet; it does not conduct substantive review.\n"
        )
        write_json(
            staged / "MANIFEST.json",
            dict(
                schema_version="CCF-COMPLETION-BUNDLE-1",
                native_snapshot_id=digest(native),
                files=members(staged),
            ),
        )
        for p in staged.iterdir():
            p.chmod(0o600)
        staged.rename(output)
    return packet["summary"]


def verify_completion(output, native, source_root):
    output = Path(output)
    if output.is_symlink() or any(p.is_symlink() for p in output.rglob("*")):
        raise ValueError("Completion bundle cannot contain symlinks")
    manifest = read_json(output / "MANIFEST.json")
    if manifest["files"] != members(output):
        raise ValueError("Completion member/hash mismatch")
    with tempfile.TemporaryDirectory() as tmp:
        expected = Path(tmp) / "bundle"
        build_completion(expected, native, source_root)
        if (expected / "MANIFEST.json").read_bytes() != (output / "MANIFEST.json").read_bytes():
            raise ValueError("Completion bundle differs from source re-performance")
    return dict(verified=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "verify"])
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-root", required=True)
    args = parser.parse_args()
    try:
        action = build_completion if args.command == "build" else verify_completion
        result = action(args.output, compile_registry(), args.source_root)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"CCF completion error: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
