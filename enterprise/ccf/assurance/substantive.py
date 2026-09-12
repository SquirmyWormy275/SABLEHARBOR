"""Source-anchored engineering findings, corrective designs and explicit review limits."""

import argparse
import hashlib
import json
import re
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

import yaml

from enterprise.ccf.registry import compile_registry, digest

from .__main__ import read_json, write_json
from .completion import TARGETS, build_completion, review_packet
from .engine import data
from .iso import iso_inputs, write_csv
from .preparation import indexed
from .reference import validate_source_inventory

DATA = Path(__file__).with_name("review_data")
HIPAA_HASH = "36081016f4d49c0856cb9e28f5d2deab5f49c8440a6c3d9a184577ea59a4f1f3"
C5_HASH = "ab906417ae2a4f210b0f23b0edaafd77cb20bc944af1aeeccfd8257eab59727a"


def finding_bindings(native):
    """Authoring helper only: persisted bindings must be reconsidered, never auto-refreshed by build."""
    c, _ = iso_inputs(native, TARGETS)
    packet = review_packet(native)
    controls = {r["control_id"]: r["design_digest"] for r in packet["controls"]}
    reqs = {r.id: r for r in c.requirements}
    sources = {s.id: s.content_sha256 for s in c.sources}
    result = {}
    rows = read_json(DATA / "findings.json")
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate finding")
    for row in rows:
        if (
            not set(row["requirement_ids"]) <= reqs.keys()
            or not set(row["control_ids"]) <= controls.keys()
        ):
            raise ValueError("Unknown finding requirement or control")
        if any(
            not row[k]
            for k in ("duties", "observed_design_gap", "corrective_procedure", "test_procedure")
        ):
            raise ValueError("Incomplete substantive finding")
        result[row["id"]] = dict(
            finding_digest=digest(row),
            requirement_digests={rid: digest(data(reqs[rid])) for rid in row["requirement_ids"]},
            source_hashes={
                reqs[rid].source_id: sources[reqs[rid].source_id] for rid in row["requirement_ids"]
            },
            design_digests={cid: controls[cid] for cid in row["control_ids"]},
        )
    domains = read_json(DATA / "c5_domain_review.json")
    if (
        len(domains) != 17
        or len({r["domain"] for r in domains}) != 17
        or any(not set(r["control_ids"]) <= controls.keys() for r in domains)
    ):
        raise ValueError("C5 domain review inventory differs")
    return dict(
        findings=result,
        catalog_digest=digest(data(c)),
        draft_designs=controls,
        c5_domain_review_digest=digest(domains),
        iso_checks_digest=digest(read_json(DATA / "iso_condition_checks.json")),
        addressable_inventory_digest=digest(read_json(DATA / "addressable_specifications.json")),
        baseline_analysis_digest=digest(
            [indexed("soc2_analysis.json", "locator"), indexed("hipaa_analysis.json", "locator")]
        ),
    )


def source_details(source_root):
    """Enumerate source units; fingerprints/segmentation are not semantic acceptance."""
    source_root = Path(source_root)
    xml = ET.parse(source_root / HIPAA_HASH)
    sections = {}
    for section in xml.iter():
        if section.get("TYPE") == "SECTION":
            sid = section.get("N", "").replace("§ ", "")
            if sid.startswith(("160.", "164.")):
                sections[sid] = [" ".join("".join(p.itertext()).split()) for p in section.iter("P")]
    specs = read_json(DATA / "addressable_specifications.json")
    if len(specs) != 22 or len({r["locator"] for r in specs}) != 22:
        raise ValueError("Addressable specification inventory differs")
    seen = set()
    resolved = []
    for row in specs:
        sid = row["requirement_id"].split(":")[1]
        needle = row["source_label"] + " (Addressable)."
        matches = [(i, text) for i, text in enumerate(sections[sid], 1) if needle in text]
        if len(matches) != 1:
            raise ValueError("Addressable specification does not resolve uniquely")
        number, text = matches[0]
        if (sid, number) in seen:
            raise ValueError("Duplicate addressable source paragraph")
        seen.add((sid, number))
        resolved.append(
            dict(
                **row,
                source_sha256=HIPAA_HASH,
                paragraph_number=number,
                paragraph_sha256=hashlib.sha256(text.encode()).hexdigest(),
            )
        )
    expected = {
        (sid, i)
        for sid, ps in sections.items()
        for i, text in enumerate(ps, 1)
        if "(Addressable)." in text
    }
    if expected != seen:
        raise ValueError("Unaccounted addressable source paragraph")
    parents, children = [], []
    with ZipFile(source_root / C5_HASH) as archive:
        for member in sorted(archive.namelist()):
            stem = Path(member).stem
            if not member.endswith(".yml") or stem in {"GC", "version_and_license"}:
                continue
            for parent in yaml.safe_load(archive.read(member)):
                pid = stem + "-" + parent["identifier"]
                info = parent.get("information") or []
                context = []
                child_ids = {
                    x["identifier"]
                    for kind in ("basic", "additional_sharpen", "additional_complement")
                    for x in parent.get(kind) or []
                }
                for idx, block in enumerate(info, 1):
                    if not set(block["applicable_criteria"]) <= child_ids:
                        raise ValueError("Unknown C5 information-to-child link")
                    context.append(
                        dict(
                            id=f"{pid}:INFO:{idx}",
                            applicable_children=[
                                pid + "." + cid for cid in block["applicable_criteria"]
                            ],
                            text_sha256=hashlib.sha256(
                                block["information_text"].encode()
                            ).hexdigest(),
                        )
                    )
                corresponding = parent.get("corresponding")
                parents.append(
                    dict(
                        parent_id=pid,
                        member=member,
                        source_sha256=C5_HASH,
                        parent_digest=digest(parent),
                        information=context,
                        customer_corresponding_sha256=hashlib.sha256(
                            corresponding.encode()
                        ).hexdigest()
                        if corresponding
                        else None,
                        responsibility_review="PENDING_ACTUAL_CUSTOMER_PROVIDER_SPLIT",
                    )
                )
                for kind in ("basic", "additional_sharpen", "additional_complement"):
                    for child in parent.get(kind) or []:
                        cid = pid + "." + child["identifier"]
                        # Publisher YAML uses literal backslash-n; retain original hash and disclose segmentation method.
                        normalized = child["criterion"].replace("\\n", "\n")
                        units = [line.strip() for line in normalized.splitlines() if line.strip()]
                        children.append(
                            dict(
                                requirement_id="C5:" + cid,
                                kind=kind,
                                source_sha256=C5_HASH,
                                text_sha256=hashlib.sha256(child["criterion"].encode()).hexdigest(),
                                parent_digest=digest(parent),
                                source_units=[
                                    dict(
                                        ordinal=i,
                                        text_sha256=hashlib.sha256(t.encode()).hexdigest(),
                                        lexical_conditional=bool(
                                            re.search(r"\b(if|unless|except|where)\b", t, re.I)
                                        ),
                                    )
                                    for i, t in enumerate(units, 1)
                                ],
                                information_ids=[
                                    b["id"] for b in context if cid in b["applicable_children"]
                                ],
                                customer_corresponding_present=bool(corresponding),
                                semantic_review="NOT_INFERRED_FROM_SEGMENTATION",
                            )
                        )
    if (
        len(children) != 623
        or len({r["requirement_id"] for r in children}) != 623
        or len(parents) != 168
    ):
        raise ValueError("C5 context population differs")
    return dict(
        addressable_specifications=resolved,
        c5_parents=parents,
        c5_children=children,
        c5_segmentation="Nonempty publisher lines after decoding literal newline escapes; line units may contain multiple duties and are not a normative decomposition.",
    )


def analysis(native, source_root):
    c, a = iso_inputs(native, TARGETS)
    validate_source_inventory(c, source_root)
    bindings = finding_bindings(native)
    if bindings != read_json(DATA / "finding_bindings.json"):
        raise ValueError(
            "Substantive findings are stale: source, requirement, design or author analysis changed"
        )
    findings = [
        dict(
            **r, bindings=bindings["findings"][r["id"]], review=None, implementation="NOT_ASSERTED"
        )
        for r in read_json(DATA / "findings.json")
    ]
    soc = indexed("soc2_analysis.json", "locator")
    hipaa = indexed("hipaa_analysis.json", "locator")
    domains = {r["domain"]: r for r in read_json(DATA / "c5_domain_review.json")}
    iso_checks = read_json(DATA / "iso_condition_checks.json")
    expected_iso = {
        r.id
        for r in c.requirements
        if r.framework_id in {"ISO27001", "ISO42001"}
        and "PREP-" not in r.id
        and "AMD1-" not in r.id
    }
    if set(iso_checks) != expected_iso or any(not v for v in iso_checks.values()):
        raise ValueError("ISO condition-check population differs")
    design_rows = {r["control_id"]: r for r in review_packet(native)["controls"]}
    selected = {x.requirement_id for x in a.applicability}
    rows = []
    for req in c.requirements:
        if req.id not in selected:
            continue
        related = [f for f in findings if req.id in f["requirement_ids"]]
        note = (
            soc if req.framework_id == "SOC2" else hipaa if req.framework_id == "HIPAA" else {}
        ).get(req.id.split(":", 1)[1], {})
        domain = (
            domains.get(req.id.split(":", 1)[1].split("-")[0]) if req.framework_id == "C5" else None
        )
        candidate_ids = sorted({m.control_id for m in c.mappings if m.requirement_id == req.id})
        rows.append(
            dict(
                requirement_id=req.id,
                framework_id=req.framework_id,
                source_id=req.source_id,
                locator=req.locator,
                requirement_digest=digest(data(req)),
                prior_section_analysis=note.get("design_analysis"),
                author_finding_ids=[f["id"] for f in related],
                source_condition_check=iso_checks.get(req.id),
                domain_comparison=domain,
                existing_candidate_procedures={
                    cid: design_rows[cid]["procedure"] for cid in candidate_ids
                },
                proposed_domain_control_ids=domain["control_ids"] if domain else [],
                review_depth="TARGETED_DUTY_COMPARISON"
                if related
                else "OBJECTIVE_CONDITION_COMPARISON"
                if req.id in iso_checks
                else "DOMAIN_CONDITION_COMPARISON"
                if domain
                else "PRIOR_SECTION_ANALYSIS_ONLY"
                if note
                else "NOT_SUBSTANTIVELY_REVIEWED",
                conclusion="OPEN_FINDING_AND_ACCEPTANCE_REQUIRED"
                if related
                else "NO_COVERAGE_CONCLUSION",
                remaining_work="Compare every exact condition, exception and linked context with scoped measures; absence of a finding is not a pass.",
                review=None,
            )
        )
    detail = source_details(source_root)
    return dict(
        schema_version="CCF-SUBSTANTIVE-REVIEW-1",
        status="AUTHOR_REVIEW_WITH_EXPLICIT_REMAINING_SCOPE",
        findings=findings,
        c5_domain_review=list(domains.values()),
        requirement_review=rows,
        source_detail=detail,
        summary=dict(
            findings=len(findings),
            requirements=len(rows),
            review_depth=dict(Counter(r["review_depth"] for r in rows)),
            addressable_specifications=len(detail["addressable_specifications"]),
            c5_parents=len(detail["c5_parents"]),
            c5_children=len(detail["c5_children"]),
            independent_acceptances=0,
        ),
    )


def members(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and p != root / "REVIEW_MANIFEST.json"
    }


def build_review(output, native, source_root):
    output = Path(output)
    if output.exists():
        raise ValueError("Review output must be a new directory")
    report = analysis(native, source_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ccf-review-", dir=output.parent) as tmp:
        staged = Path(tmp) / "bundle"
        staged.mkdir(mode=0o700)
        build_completion(staged / "draft-library", native, source_root)
        write_json(staged / "SUBSTANTIVE_REVIEW.json", report)
        write_csv(staged / "FINDINGS.csv", report["findings"])
        write_csv(staged / "REVIEW_DEPTH.csv", report["requirement_review"])
        write_csv(staged / "C5_DOMAIN_COMPARISON.csv", report["c5_domain_review"])
        write_csv(
            staged / "ADDRESSABLE_DECISIONS.csv",
            report["source_detail"]["addressable_specifications"],
        )
        (staged / "FINDINGS.md").write_text(
            "# Source comparison findings\n\nAuthor engineering analysis; independent acceptance and actual implementation remain pending.\n\n"
            + "\n\n".join(
                f"## {f['id']}\n\nSource: {f['source_locator']}\n\nRequirements: {', '.join(f['requirement_ids'])}\n\nObserved gap: {f['observed_design_gap']}\n\nCorrective procedure: {f['corrective_procedure']}\n\nTest: {f['test_procedure']}\n\nRemaining decision: {f['remaining_decision']}"
                for f in report["findings"]
            )
            + "\n"
        )
        (staged / "START_HERE.md").write_text(
            "# Substantive CCF review\n\n[Findings and corrective procedures](FINDINGS.md) · [Review depth](REVIEW_DEPTH.csv) · [Addressable decisions](ADDRESSABLE_DECISIONS.csv) · [Draft library](draft-library/START_HERE.md) · [Review limits and sources](REVIEW_NOTES.md)\n\n"
            + json.dumps(report["summary"], indent=2)
            + "\n\nTargeted findings are source comparisons, not acceptance of an entire requirement. Requirements without findings remain explicitly unreviewed or at prior section-analysis depth. No review, mapping or evidence approval was entered into the assurance engine.\n"
        )
        (staged / "REVIEW_NOTES.md").write_bytes((DATA / "REVIEW_NOTES.md").read_bytes())
        write_json(
            staged / "REVIEW_MANIFEST.json",
            dict(schema_version="CCF-SUBSTANTIVE-BUNDLE-1", files=members(staged)),
        )
        for p in staged.rglob("*"):
            p.chmod(0o700 if p.is_dir() else 0o600)
        staged.rename(output)
    return report["summary"]


def verify_review(output, native, source_root):
    output = Path(output)
    if output.is_symlink() or any(p.is_symlink() for p in output.rglob("*")):
        raise ValueError("Review bundle cannot contain symlinks")
    if read_json(output / "REVIEW_MANIFEST.json")["files"] != members(output):
        raise ValueError("Review member/hash mismatch")
    with tempfile.TemporaryDirectory() as tmp:
        expected = Path(tmp) / "bundle"
        build_review(expected, native, source_root)
        if (expected / "REVIEW_MANIFEST.json").read_bytes() != (
            output / "REVIEW_MANIFEST.json"
        ).read_bytes():
            raise ValueError("Review differs from source re-performance")
    return dict(verified=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "verify"])
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        result = (build_review if args.command == "build" else verify_review)(
            args.output, compile_registry(), args.source_root
        )
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"CCF review error: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
