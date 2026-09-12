"""Build reviewable baseline designs and a separately labelled fictional workflow."""

import argparse
import csv
import hashlib
import json
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from enterprise.ccf.registry import ROOT, compile_registry, digest

from .__main__ import build, read_json, verify, write_json
from .reference import (
    AS_OF,
    BOUNDARIES,
    HHS_STATUS_URL,
    build_reference,
    reference_inputs,
    source_inventory,
    validate_source_inventory,
)
from .reference import (
    DATA as REFERENCE_DATA,
)
from .reference_exercise import exercise
from .reporting import cell

DATA = Path(__file__).with_name("design_data")


def indexed(filename, key):
    rows = read_json(DATA / filename)
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError("Duplicate design record: " + filename)
    return result


def designs(native):
    """No reviews, appointments, operating evidence or legal dispositions are manufactured."""
    c, a = reference_inputs(native, False)
    controls = {r["id"]: r for r in native["records"] if r["kind"] == "control"}
    procedures = indexed("control_procedures.json", "control_id")
    soc = indexed("soc2_analysis.json", "locator")
    hipaa = indexed("hipaa_analysis.json", "locator")
    supplements = list(indexed("supplements.json", "id").values())
    used = {i.control_id for i in a.implementations}
    selected = {x.requirement_id for x in a.applicability}
    if set(procedures) != used:
        raise ValueError("Control procedure population differs from selected baseline")
    if {"SOC2:" + r for r in soc} | {"HIPAA:" + r for r in hipaa} != selected:
        raise ValueError("Requirement analysis population differs from selected baseline")
    for s in supplements:
        if (
            not set(s["native_control_ids"]) <= controls.keys()
            or not set(s["requirement_ids"]) <= selected
        ):
            raise ValueError("Unknown supplement control or requirement")
    requirements = []
    for r in c.requirements:
        if r.id not in selected:
            continue
        ref = r.id.split(":", 1)[1]
        note = (soc if r.framework_id == "SOC2" else hipaa)[ref]
        requirements.append(
            dict(
                requirement_id=r.id,
                source_id=r.source_id,
                locator=r.locator,
                summary=r.summary,
                design_analysis=note["design_analysis"],
                proposed_role_treatment=note.get("proposed_role_treatment", "SELECTED_CRITERION"),
                mapping_limit=note.get(
                    "mapping_limit",
                    "Section routing is not coverage of every paragraph, exception or actor; validate exact attributes and contractual delegation.",
                ),
                candidate_control_ids=sorted(
                    {m.control_id for m in c.mappings if m.requirement_id == r.id}
                ),
                supplement_ids=[s["id"] for s in supplements if r.id in s["requirement_ids"]],
                source_review="PENDING_INDEPENDENT_REVIEW",
                applicability="PROPOSED_ANALYSIS_ONLY",
                source_context=(
                    "Points of focus and guidance inform context; they are not automatically separate mandatory controls."
                    if r.framework_id == "SOC2"
                    else "Read cross-references, definitions and exceptions with the legal-status overlay. No automatic exclusion."
                ),
                operating_inputs_needed=[
                    "Actual entity/service/data/contract facts",
                    "Authorized owner and reviewer appointments",
                    "Accepted reporting period and evidence populations",
                ],
            )
        )
    work = []
    for cid in sorted(used):
        control = controls[cid]["data"]
        work.append(
            dict(
                **procedures[cid],
                control_digest=digest(controls[cid]),
                native_owner_role_id=control["owner_role_id"],
                native_trigger=control["frequency_or_trigger"],
                status="PROPOSED_NOT_DEPLOYED",
                appointment_status="NOT_ASSERTED",
                requirement_ids=sorted(
                    {
                        m.requirement_id
                        for m in c.mappings
                        if m.control_id == cid and m.requirement_id in selected
                    }
                ),
                supplement_ids=[s["id"] for s in supplements if cid in s["native_control_ids"]],
                boundary_execution=[
                    dict(
                        boundary_id=b,
                        responsibility=(
                            "Own the enterprise procedure and shared execution; retain records linking the service and both sites."
                            if b == "corporate"
                            else "Validate local accounts, assets, data and provider duties; link shared corporate execution to this boundary without duplicating or assuming it."
                        ),
                    )
                    for b in BOUNDARIES
                ],
                exception_route="Open a finding with severity, accountable role and due date; record authorized compensating measures and expiry. Missing evidence is not a passing result.",
                acceptance="Reconcile the complete occurrence population; trace procedure steps to evidence and independent review; document every omitted objective and failed step.",
                operating_inputs_needed=[
                    "Actual system instance and authorized executor",
                    "Approved risk-based thresholds where the procedure depends on them",
                    "Independent source population and record retention settings",
                ],
            )
        )
    by_req = {r["requirement_id"]: r for r in requirements}
    mapping_work = []
    for m in c.mappings:
        if m.requirement_id not in by_req:
            continue
        r = by_req[m.requirement_id]
        mapping_work.append(
            dict(
                mapping_id=m.id,
                requirement_id=m.requirement_id,
                attribute_ids=m.attribute_ids,
                control_id=m.control_id,
                control_digest=m.control_digest,
                analysis=r["design_analysis"],
                uncovered=r["mapping_limit"],
                supplement_ids=r["supplement_ids"],
                decision="CANDIDATE_ENHANCEMENT_REVIEW_REQUIRED",
                review=None,
            )
        )
    return dict(
        schema_version="BASELINE-DESIGN-1",
        native_snapshot_id=digest(native),
        as_of=AS_OF,
        status="AUTHOR_DESIGN_ANALYSIS_PENDING_ACCEPTANCE",
        requirements=requirements,
        controls=work,
        supplements=supplements,
        mapping_workpapers=mapping_work,
    )


def source_context(catalog, source_root):
    """Reperform paragraph/bullet fingerprints, keeping source text out of exported notes."""
    validate_source_inventory(catalog, source_root)
    inv = source_inventory()
    xml = ET.fromstring((Path(source_root) / inv["source_sha256"]).read_bytes())
    paragraphs = []
    for part in xml.iter():
        if part.attrib.get("TYPE") != "PART" or part.attrib.get("N") not in {"160", "164"}:
            continue
        for section in part.iter():
            if section.attrib.get("TYPE") != "SECTION":
                continue
            ref = section.attrib["N"].replace("§ ", "")
            for ordinal, p in enumerate(section.iter("P"), 1):
                text = " ".join("".join(p.itertext()).split())
                markers = re.match(r"^(?:\([A-Za-z0-9]+\)\s*)+", text)
                paragraphs.append(
                    dict(
                        requirement_id="HIPAA:" + ref,
                        source_paragraph_id=f"P{ordinal:04}",
                        text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                        leading_markers=markers.group(0).strip() if markers else None,
                        semantic_state="SECTION_ANALYSIS_AVAILABLE_PARAGRAPH_REVIEW_PENDING",
                        citation_limit="Ordinal fingerprint and leading markers; not a reconstructed legal citation.",
                    )
                )
    source = next(s for s in catalog.sources if s.id == "SOURCE-SOC2-TSC")
    text = subprocess.check_output(
        ["pdftotext", "-layout", str(Path(source_root) / source.content_sha256), "-"], text=True
    )
    headings = list(
        re.finditer(
            r"^\s*((?:CC\d|A1|C1|PI1|P[1-8])\.\d)\s+(?:COSO|The entity|Prior to|To meet|Personal information|For information)",
            text,
            re.M,
        )
    )
    expected = {
        r["locator"] for r in read_json(REFERENCE_DATA / "soc2.json") if r["source"] == "TSC"
    }
    observed = {m.group(1) for m in headings}
    if observed != expected or len(headings) != len(expected):
        raise ValueError(
            "TSC source heading population differs; inspect extraction before using focus locators"
        )
    focus = []
    for i, m in enumerate(headings):
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        section = text[m.end() : end]
        bullets = list(re.finditer("•", section))
        for j, bullet in enumerate(bullets):
            stop = bullets[j + 1].start() if j + 1 < len(bullets) else len(section)
            body = " ".join(section[bullet.end() : stop].split())
            focus.append(
                dict(
                    requirement_id="SOC2:" + m.group(1),
                    source_id=source.id,
                    candidate_id=f"BULLET-{j + 1:03}",
                    pdf_page=1 + text[: m.end() + bullet.start()].count("\f"),
                    text_sha256=hashlib.sha256(body.encode()).hexdigest(),
                    disposition="GUIDANCE_CANDIDATE_NOT_MANDATORY_ATTRIBUTE",
                    review="Check continuation, category-specific relevance and footnotes against original; bullet spans may contain page furniture.",
                )
            )
    return dict(
        hipaa_paragraphs=paragraphs,
        soc2_focus_candidates=focus,
        limitations=[
            "Fingerprint reconciliation does not independently approve source semantics.",
            "Source bullet spans are review locators, not an authoritative point-of-focus count.",
        ],
    )


def csv_file(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    k: cell(
                        json.dumps(v) if isinstance(v, (dict, list)) else "" if v is None else v
                    )
                    for k, v in row.items()
                }
            )


def members(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and p != root / "PREPARATION_MANIFEST.json"
    }


def build_preparation(output, native, source_root, repository=ROOT):
    output = Path(output)
    if output.exists():
        raise ValueError("Preparation output must be a new directory")
    design = designs(native)
    c, _ = reference_inputs(native)
    context = source_context(c, source_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ccf-design-", dir=output.parent) as tmp:
        staged = Path(tmp) / "package"
        staged.mkdir(mode=0o700)
        write_json(staged / "DESIGNS.json", design)
        write_json(staged / "SOURCE_CONTEXT.json", context)
        (staged / "SERVICE_DESCRIPTION.md").write_bytes(
            (DATA / "SERVICE_DESCRIPTION.md").read_bytes()
        )
        csv_file(
            staged / "OPERATING_INPUTS.csv",
            [
                dict(
                    control_id=control["control_id"],
                    boundary_id=boundary,
                    native_owner_role_id=control["native_owner_role_id"],
                    actual_executor="",
                    actual_reviewer="",
                    system_instance="",
                    approved_parameters="",
                    population_source="",
                    inherited_control_reference="",
                    provider_responsibility="",
                    acceptance_state="AWAITING_OPERATING_FACTS",
                )
                for control in design["controls"]
                for boundary in BOUNDARIES
            ],
        )
        for key, name in [
            ("requirements", "REQUIREMENT_ANALYSIS"),
            ("controls", "CONTROL_PROCEDURES"),
            ("mapping_workpapers", "MAPPING_ANALYSIS"),
        ]:
            csv_file(staged / (name + ".csv"), design[key])
        lines = [
            "# Proposed baseline control procedures",
            "",
            "Author design work only. Roles are native role labels; systems are proposed record locations. No appointments or deployed safeguards are asserted.",
            "",
        ]
        for control in design["controls"]:
            lines.extend(
                [
                    f"## {control['control_id']}",
                    "",
                    f"Owner role: {control['native_owner_role_id']}. Trigger: {control['native_trigger']}.",
                    "",
                    "Proposed record location: " + control["proposed_system_of_record"] + ".",
                    "",
                    control["procedure"],
                    "",
                    "Evidence: " + ", ".join(control["evidence_outputs"]) + ".",
                    "",
                    "Reviewer: " + control["reviewer_role_description"] + ".",
                    "",
                    "Supplements: "
                    + (
                        ", ".join(control["supplement_ids"])
                        or "None identified in this design pass"
                    )
                    + ".",
                    "",
                ]
            )
        (staged / "CONTROL_PROCEDURES.md").write_text("\n".join(lines))
        lines = [
            "# Proposed technical supplements",
            "",
            "These expand existing native control designs; no new native IDs or deployed configurations are claimed.",
            "",
        ]
        for s in design["supplements"]:
            lines.extend(
                ["## " + s["id"], "", "Native controls: " + ", ".join(s["native_control_ids"]), ""]
            )
            lines.extend(f"{i}. {step}" for i, step in enumerate(s["procedure"], 1))
            lines.extend(
                [
                    "",
                    "Evidence: " + ", ".join(s["evidence_outputs"]),
                    "",
                    "Inputs: " + ", ".join(s["operating_inputs_needed"]),
                    "",
                ]
            )
        (staged / "TECHNICAL_SUPPLEMENTS.md").write_text("\n".join(lines))
        build_reference(staged / "reference", native, source_root, True, repository)
        stages, ledger = exercise(native)
        summaries = []
        for name, cat, assessment, result in stages:
            build(staged / "exercise" / name, cat, assessment, native, repository)
            summaries.append(dict(stage=name, origin="SYNTHETIC", summary=result["summary"]))
        write_json(staged / "exercise" / "FINDING.json", ledger)
        write_json(staged / "exercise" / "STAGES.json", summaries)
        (staged / "START_HERE.md").write_text(
            "# Baseline design delivery\n\n"
            "149 requirement analyses (47 selected SOC 2/DC and 102 HIPAA sections), 64 proposed control procedures, five technical supplements, mapping workpapers and a five-stage fictional assessment.\n\n"
            "[Control procedures](CONTROL_PROCEDURES.md) · [Technical supplements](TECHNICAL_SUPPLEMENTS.md) · [Service description](SERVICE_DESCRIPTION.md) · [Operating inputs](OPERATING_INPUTS.csv) · [Requirement analysis](REQUIREMENT_ANALYSIS.csv) · [Real-framework reference workbench](reference/assessment/explorer.html)\n\n"
            "The real-framework assessment remains unresolved. Author analysis is available for every selected baseline record; independent source, paragraph semantics, mapping and applicability decisions remain pending. Reserved, definitional, enforcement and customer duties remain identifiable rather than being counted as operating controls.\n\n"
            "## Exercise\n\n"
            "All exercise criteria, reviewers and records are invented. SOC/HIPAA share scoped evidence but use distinct tests. Each site validates its connection to corporate records. Selecting C5 creates new test and implementation gaps. A Boise failure stays a gap after a same-period passing retest. A later implementation version passes only for its prospective one-day period, with the prior failure retained. This is software acceptance, not assurance.\n\n"
            + "\n".join(
                f"- [{x['stage']}](exercise/{x['stage']}/explorer.html): {x['summary']}"
                for x in summaries
            )
            + "\n\n## Source reconciliation\n\n"
            "Atlas research revision 96bda5ef06a1e8b3469704c55b71ff2aae05e830 identified 29 missing C5 sharpened children. This build reconciles all 623 children with pinned publisher YAML; six general conditions and assessment context remain explicit review work. Older delivered packages are historical and unchanged. Full ISO/IEC 27001 and 42001 source access remains outstanding.\n\n"
            f"[HHS legal-status notice]({HHS_STATUS_URL}) governs the court-affected overlay; printed XML alone is insufficient. "
            "The source-paragraph and focus-candidate registers preserve hashes and locators; they are not independent legal or inventory approvals.\n\n"
            "## Ready for operating inputs\n\n"
            "Management supplies actual service/data flows and contracts, accepted objectives and thresholds, authorized executors/reviewers, actual systems/providers and a proposed examination period. Those inputs permit final local designs, evidence collection and independent assessment. Examiner acceptance and authorized customer disclosures are later gates. No purchase or deployment is required to read or reproduce this design package.\n"
        )
        write_json(
            staged / "PREPARATION_MANIFEST.json",
            dict(
                version="BASELINE-DESIGN-1",
                native_snapshot_id=digest(native),
                files=members(staged),
            ),
        )
        for p in staged.rglob("*"):
            if p.is_file():
                p.chmod(0o600)
        staged.rename(output)
    return dict(
        output=str(output),
        requirements=len(design["requirements"]),
        controls=len(design["controls"]),
        hipaa_paragraphs=len(context["hipaa_paragraphs"]),
        focus_candidates=len(context["soc2_focus_candidates"]),
        stages=summaries,
    )


def verify_preparation(output, native, source_root, repository=ROOT):
    output = Path(output)
    if output.is_symlink() or any(p.is_symlink() for p in output.rglob("*")):
        raise ValueError("Preparation bundle cannot contain symlinks")
    manifest = read_json(output / "PREPARATION_MANIFEST.json")
    if manifest["files"] != members(output):
        raise ValueError("Preparation member/hash mismatch")
    verify(output / "reference" / "assessment", repository, source_root)
    for name, _, _, _ in exercise(native)[0]:
        verify(output / "exercise" / name, repository)
    with tempfile.TemporaryDirectory() as tmp:
        expected = Path(tmp) / "expected"
        build_preparation(expected, native, source_root, repository)
        if (output / "PREPARATION_MANIFEST.json").read_bytes() != (
            expected / "PREPARATION_MANIFEST.json"
        ).read_bytes():
            raise ValueError("Preparation differs from source re-performance")
    return dict(verified=True, native_snapshot_id=digest(native))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "verify"])
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-root", required=True)
    args = parser.parse_args()
    try:
        result = (build_preparation if args.command == "build" else verify_preparation)(
            args.output, compile_registry(), args.source_root
        )
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"CCF preparation error: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
