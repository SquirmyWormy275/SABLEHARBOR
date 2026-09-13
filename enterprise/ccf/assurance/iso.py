"""Source-bound ISO extension planning over the approved SOC 2/HIPAA reference baseline."""

import argparse
import csv
import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path

from enterprise.ccf.registry import ROOT, compile_registry, digest

from .__main__ import build, read_json, verify, write_json
from .engine import data, plan
from .models import Assessment, Catalog
from .reference import AS_OF, reference_inputs, validate_source_inventory
from .reporting import cell

DATA = Path(__file__).with_name("iso_data")
COMMON_CLAUSES = set(
    "4.1 4.2 4.3 4.4 5.1 5.2 5.3 6.1.1 6.1.2 6.1.3 6.2 6.3 "
    "7.1 7.2 7.3 7.4 7.5.1 7.5.2 7.5.3 8.1 8.2 8.3 9.1 9.2.1 9.2.2 "
    "9.3.1 9.3.2 9.3.3 10.1 10.2".split()
)


def validate_authored_inventory(rows):
    """Independent identifier expectations prevent matching counts hiding omissions."""
    ai_groups = {
        "2": 4,
        "3": 3,
        "4": 6,
        "5": 5,
        "6.1": 3,
        "6.2": 8,
        "7": 6,
        "8": 5,
        "9": 4,
        "10": 4,
    }
    expected = {
        ("ISO27001", "ISMS"): COMMON_CLAUSES,
        ("ISO42001", "AIMS"): COMMON_CLAUSES | {"6.1.4", "8.4"},
        ("ISO27001", "ANNEX_A"): {
            f"A.{group}.{n}"
            for group, count in [(5, 37), (6, 8), (7, 14), (8, 34)]
            for n in range(1, count + 1)
        },
        ("ISO42001", "ANNEX_A"): {
            f"A.{group}.{n}" for group, last in ai_groups.items() for n in range(2, last + 1)
        },
    }
    if len(rows) != sum(map(len, expected.values())):
        raise ValueError("ISO source inventory size differs")
    for key, locators in expected.items():
        selected = [r for r in rows if (r["framework_id"], r["category"]) == key]
        if len(selected) != len(locators) or {r["locator"] for r in selected} != locators:
            raise ValueError("ISO source locator/category population differs")
        for row in selected:
            if not row["pdf_pages"] or any(
                type(p) is not int or not 1 <= p <= (26 if key[0] == "ISO27001" else 61)
                for p in row["pdf_pages"]
            ):
                raise ValueError("Invalid ISO page locator")
            if key == ("ISO42001", "ANNEX_A") and (
                row.get("guidance_locator") != "B." + row["locator"][2:]
                or not row.get("guidance_pdf_pages")
            ):
                raise ValueError("Missing or mismatched ISO42001 guidance link")


FRAMEWORKS = {
    "ISO27001": ("ISMS", "2022 + Amd 1:2024"),
    "ISO42001": ("AIMS", "2023; user-provided BS adoption scan"),
}
SOURCES = [
    (
        "SOURCE-ISO27001",
        "ISO/IEC",
        "ISO/IEC 27001:2022; user-provided 26-page copy",
        "https://www.iso.org/standard/27001",
        "843a6728009540947b2c5531f94b4cf1fb698d5bf3b51b324c8801e3e01c5b78",
    ),
    (
        "SOURCE-ISO42001",
        "BSI / ISO/IEC",
        "BS ISO/IEC 42001:2023; user-provided 61-page scan",
        "https://www.iso.org/standard/42001",
        "d50103cc0af6d2322c60753ab4a6d9cc54594bc78163481322bf80ee2f75a896",
    ),
    (
        "SOURCE-ISO27001-AMD1",
        "ISO/IEC",
        "ISO/IEC 27001:2022/Amd 1:2024; six-page distributor copy",
        "https://www.iso.org/standard/88435.html",
        "43c8e4bbc525b247579b133334f2f52ee306ec26007007f9f99f64f95b72e05c",
    ),
]


def source_rows():
    return [
        dict(
            id=sid,
            publisher=publisher,
            edition=edition,
            url=url,
            retrieved_on=AS_OF,
            effective_from=None,
            access="AVAILABLE",
            content_sha256=h,
            rights_note="Original retained outside generated exports. User-supplied base reference copies; no new distribution right or independent authenticity review asserted.",
        )
        for sid, publisher, edition, url, h in SOURCES
    ]


def iso_inputs(native, targets):
    targets = list(targets)
    if (
        not targets
        or len(targets) != len(set(targets))
        or not set(targets) <= {"ISO27001", "ISO42001", "C5"}
    ):
        raise ValueError("Select distinct supported extension targets")
    catalog, assessment = reference_inputs(native, include_c5="C5" in targets)
    c, a = data(catalog), data(assessment)
    c.update(id="SH-CCF-ISO-EXTENSION-REFERENCE", version="0.4.0-iso-reference")
    c["requirements"] = [r for r in c["requirements"] if r["framework_id"] not in FRAMEWORKS]
    c["frameworks"] = [f for f in c["frameworks"] if f["id"] not in FRAMEWORKS]
    c["sources"] = [
        s for s in c["sources"] if s["id"] not in {"SOURCE-ISO27001", "SOURCE-ISO42001"}
    ] + source_rows()
    controls = {r["id"]: r for r in native["records"] if r["kind"] == "control"}
    authored = read_json(DATA / "requirements.json")
    validate_authored_inventory(authored)
    seen = set()
    for row in authored:
        rid = row["framework_id"] + ":" + row["locator"]
        if rid in seen:
            raise ValueError("Duplicate ISO source locator")
        seen.add(rid)
        attrs = [
            dict(
                id="OBJECTIVE",
                objective=row["objective"],
                kind=row["kind"],
                evidence_expectation="Scoped procedure, accountable role, complete source population and separately reviewed attribute test.",
            ),
            dict(
                id="SOURCE_CONTEXT",
                objective="Validate exact clause conditions, definitions, cross-references and scope-specific applicability",
                kind="ASSESSMENT",
                evidence_expectation="Source-anchored rationale and independent review; original text/OCR is not exported.",
            ),
        ]
        if row.get("guidance_locator"):
            attrs.append(
                dict(
                    id="IMPLEMENTATION_GUIDANCE",
                    objective="Evaluate relevant normative Annex B guidance for "
                    + row["guidance_locator"],
                    kind="ASSESSMENT",
                    evidence_expectation="Document consideration of the linked guidance, applicable conditions and any needed additional measures.",
                )
            )
        c["requirements"].append(
            dict(
                id=rid,
                framework_id=row["framework_id"],
                source_id="SOURCE-" + row["framework_id"],
                locator=row["locator"] + "; PDF page(s) " + ",".join(map(str, row["pdf_pages"])),
                category=row["category"],
                summary=row["objective"],
                attributes=attrs,
            )
        )
        for cid in row["control_ids"]:
            c["mappings"].append(
                dict(
                    id="ISO-CANDIDATE-" + rid + "-" + cid,
                    requirement_id=rid,
                    control_id=cid,
                    control_digest=digest(controls[cid]),
                    attribute_ids=["OBJECTIVE"],
                    rationale="Candidate native procedure to develop for: " + row["objective"],
                    uncovered="Topic overlap only. Validate every condition, actor, outcome and evidence requirement; source context and any Annex B guidance remain separate gaps.",
                )
            )
    # Complete-document context stays visible rather than disappearing outside selected leaf clauses.
    for fid, (category, edition) in FRAMEWORKS.items():
        context_id = fid + ":PREP-DOCUMENT-CONTEXT"
        c["requirements"].append(
            dict(
                id=context_id,
                framework_id=fid,
                source_id="SOURCE-" + fid,
                locator="Introduction; clauses 1-3; parent clauses; Annex A introduction/objectives; "
                + ("Annexes B-D" if fid == "ISO42001" else "normative references"),
                category=category,
                summary="Review complete-document context and management-system scope",
                attributes=[
                    dict(
                        id="CONTEXT",
                        objective="Reconcile omitted parent text, terms, normative references and annex objectives; classify informative material without converting it into mandatory controls.",
                        kind="ASSESSMENT",
                        evidence_expectation="Complete source inventory and scope-specific interpretation; this internal gate is not a publisher clause.",
                    )
                ],
            )
        )
        if fid == "ISO27001":
            c["requirements"].append(
                dict(
                    id=fid + ":AMD1-4.1-4.2",
                    framework_id=fid,
                    source_id="SOURCE-ISO27001-AMD1",
                    locator="Amd 1:2024; 4.1 and 4.2; PDF page 5",
                    category=category,
                    summary="Assess climate relevance and relevant interested-party expectations",
                    attributes=[
                        dict(
                            id="RELEVANCE",
                            objective="Determine whether climate change matters to the ISMS context",
                            kind="ASSESSMENT",
                            evidence_expectation="Recorded context analysis and rationale; climate relevance does not automatically require a separate climate programme.",
                        ),
                        dict(
                            id="PARTY_NOTE",
                            objective="Consider whether relevant interested parties have climate-related requirements",
                            kind="ASSESSMENT",
                            evidence_expectation="Interested-party analysis; preserve the distinction between the added requirement and explanatory note.",
                        ),
                    ],
                )
            )
        c["frameworks"].append(
            dict(
                id=fid,
                title=fid + " scoped extension planning",
                edition=edition,
                source_ids=["SOURCE-" + fid]
                + (["SOURCE-ISO27001-AMD1"] if fid == "ISO27001" else []),
                categories=[category, "ANNEX_A"],
                required_categories=[category, "ANNEX_A"],
                expected_requirement_ids=[
                    r["id"] for r in c["requirements"] if r["framework_id"] == fid
                ],
                inventory_complete=False,
                limitation="Leaf-clause and Annex A candidate inventory; source context, full semantic decomposition and independent inventory review remain open. Annex A controls require risk-based selection and a justified Statement of Applicability.",
            )
        )
    c = Catalog.model_validate(c)
    a["catalog_digest"] = digest(data(c))
    a["scope"]["targets"] = [
        dict(framework_id=f, categories=list(FRAMEWORKS[f][:1]) + ["ANNEX_A"])
        if f in FRAMEWORKS
        else dict(framework_id="C5", categories=["BASIC", "ADDITIONAL"])
        for f in targets
    ]
    a["scope"]["assumptions"] += [
        "ISO targets are reference planning extensions, not approved certification scopes.",
        "ISO42001 needs actual AI systems, uses, affected parties and lifecycle roles before applicability or impact conclusions.",
        "Annex A is considered through risk treatment and a Statement of Applicability; selection here does not make every reference control mandatory.",
        "Corporate execution and site evidence remain distinct; no automatic inheritance or independent review is asserted.",
    ]
    existing = {(i["boundary_id"], i["control_id"]) for i in a["implementations"]}
    for r in c.requirements:
        if r.framework_id not in targets or r.framework_id not in FRAMEWORKS:
            continue
        for b in a["scope"]["boundaries"]:
            a["applicability"].append(
                dict(
                    requirement_id=r.id,
                    boundary_id=b,
                    disposition="UNRESOLVED",
                    rationale="Proposed extension; determine scope, use, role, obligations and risk-based necessity before accepting inclusion or exclusion.",
                )
            )
            for m in [m for m in c.mappings if m.requirement_id == r.id]:
                if (b, m.control_id) in existing:
                    continue
                existing.add((b, m.control_id))
                a["implementations"].append(
                    dict(
                        id=f"ISO-REF-{b}-{m.control_id}",
                        version="ISO-DESIGN-1",
                        control_id=m.control_id,
                        control_digest=m.control_digest,
                        boundary_id=b,
                        owner_role_id=controls[m.control_id]["data"]["owner_role_id"],
                        state="PROPOSED",
                        effective_from=AS_OF,
                        effective_to=None,
                    )
                )
    a = Assessment.model_validate(a)
    plan(c, a, native)
    return c, a


def extension_work(c, a, native):
    """Separate reused candidates, additional native controls and unmapped assessment work."""
    baseline = {
        m.control_id for m in c.mappings if m.requirement_id.startswith(("SOC2:", "HIPAA:"))
    }
    native_controls = {r["id"]: r for r in native["records"] if r["kind"] == "control"}
    authored = {
        r["framework_id"] + ":" + r["locator"]: r for r in read_json(DATA / "requirements.json")
    }
    targets = {s.framework_id for s in a.scope.targets}
    rows = []
    for r in c.requirements:
        if r.framework_id not in targets:
            continue
        mappings = [m for m in c.mappings if m.requirement_id == r.id]
        ids = sorted({m.control_id for m in mappings})
        note = authored.get(r.id, {})
        for b in a.scope.boundaries:
            rows.append(
                dict(
                    requirement_id=r.id,
                    framework_id=r.framework_id,
                    category=r.category,
                    boundary_id=b,
                    objective=r.summary,
                    source_id=r.source_id,
                    locator=r.locator,
                    candidate_baseline_controls=sorted(set(ids) & baseline),
                    additional_native_candidates=sorted(set(ids) - baseline),
                    unmapped_attribute_ids=[
                        attr.id
                        for attr in r.attributes
                        if not any(attr.id in m.attribute_ids for m in mappings)
                    ],
                    proposed_owner_role_ids=sorted(
                        {native_controls[cid]["data"]["owner_role_id"] for cid in ids}
                    ),
                    guidance_locator=note.get("guidance_locator"),
                    guidance_pdf_pages=note.get("guidance_pdf_pages", []),
                    action="SOURCE_AND_DESIGN_REVIEW_REQUIRED",
                    procedure="Compare each exact source condition with the native procedure; document missing actor, trigger, system setting, evidence and outcome. Evaluate linked guidance. Design additional measures, then plan an independent scoped test.",
                    acceptance="No compliance conclusion until applicable objectives, source context, implemented design and scoped evidence are independently reviewed.",
                    operating_fact_needed="Actual AI use case, lifecycle role, affected people and impact/risk criteria"
                    if r.framework_id == "ISO42001"
                    else "Actual cloud-service scope, customer/provider responsibilities and C5 assessment period"
                    if r.framework_id == "C5"
                    else "Actual ISMS scope, interested parties, risk criteria and treatment decisions",
                    review=None,
                )
            )
    soa = [
        dict(
            requirement_id=r["requirement_id"],
            framework_id=r["framework_id"],
            boundary_id=r["boundary_id"],
            necessity="UNRESOLVED",
            inclusion_justification="",
            exclusion_justification="",
            implemented="NOT_ASSERTED",
            candidate_controls=r["candidate_baseline_controls"] + r["additional_native_candidates"],
            review="PENDING",
        )
        for r in rows
        if r["category"] == "ANNEX_A" and r["framework_id"] in FRAMEWORKS
    ]
    return dict(
        origin="REFERENCE_DESIGN_NOT_ASSURANCE",
        rows=rows,
        statement_of_applicability=soa,
        additional_native_control_ids=sorted(
            {cid for r in rows for cid in r["additional_native_candidates"]}
        ),
    )


def members(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and p != root / "ISO_MANIFEST.json"
    }


def write_csv(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        for r in rows:
            writer.writerow(
                {
                    k: cell(
                        json.dumps(v) if isinstance(v, (list, dict)) else "" if v is None else v
                    )
                    for k, v in r.items()
                }
            )


def build_iso(output, native, source_root, targets, repository=ROOT):
    output = Path(output)
    if output.exists():
        raise ValueError("ISO output must be a new directory")
    c, a = iso_inputs(native, targets)
    validate_source_inventory(c, source_root)
    work = extension_work(c, a, native)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ccf-iso-", dir=output.parent) as temp:
        staged = Path(temp) / "bundle"
        staged.mkdir(mode=0o700)
        summary = build(staged / "assessment", c, a, native, repository, source_root)
        write_json(staged / "EXTENSION_WORK.json", work)
        (staged / "IMPLEMENTATION_PLAN.md").write_bytes(
            (DATA / "IMPLEMENTATION_PLAN.md").read_bytes()
        )
        write_json(staged / "SOURCE_INVENTORY.json", read_json(DATA / "source_inventory.json"))
        write_csv(staged / "DELTA_ACTIONS.csv", work["rows"])
        if work["statement_of_applicability"]:
            write_csv(staged / "STATEMENT_OF_APPLICABILITY.csv", work["statement_of_applicability"])
        (staged / "START_HERE.md").write_text(
            "# ISO extension design work\n\n"
            "[Assessment explorer](assessment/explorer.html) · [Implementation plan](IMPLEMENTATION_PLAN.md) · [Delta actions](DELTA_ACTIONS.csv) · [Structured work](EXTENSION_WORK.json)\n\n"
            "Selected extensions: "
            + ", ".join(targets)
            + ". The SOC 2/HIPAA baseline remains visible. All conclusions remain unresolved.\n\n"
            "Candidate reuse is separated from additional native controls and unmapped source/assessment work. Counts are planning records, not controls proven effective. "
            "The Statement of Applicability rows require justified necessity/inclusion/exclusion decisions; all Annex A controls are considered, not automatically mandated.\n\n"
            "The source-backed inventory contains 30 ISMS leaf clauses and 93 Annex A controls, plus a document-context gate and the 27001 climate amendment. "
            "The AIMS inventory contains 32 leaf clauses and 38 Annex A controls with links to normative Annex B guidance, plus a document-context gate covering terms, parent clauses and annex objectives. "
            "Annexes C/D are informative context. Whole-document semantics and independent inventory review remain open.\n\n"
            "The 42001 scan was OCR-processed without altering the original. Annex A identifiers were visually checked; OCR wording is not accepted normative text. "
            "Original PDFs and extracted full text remain outside this generated package and outside implementation Git commits.\n\n"
            "No actual AI deployment, certification scope, personnel, operating period or reviewer approval is asserted. Supply actual service/AI use-case and risk-treatment facts to finalize these designs.\n"
        )
        write_json(
            staged / "ISO_MANIFEST.json",
            dict(version="ISO-EXTENSION-1", targets=list(targets), files=members(staged)),
        )
        for p in staged.rglob("*"):
            if p.is_file():
                p.chmod(0o600)
        staged.rename(output)
    return dict(
        summary=summary,
        targets=list(targets),
        extension_rows=len(work["rows"]),
        soa_rows=len(work["statement_of_applicability"]),
        additional_native_control_ids=work["additional_native_control_ids"],
        framework_rows=dict(Counter(r["framework_id"] for r in work["rows"])),
    )


def verify_iso(output, native, source_root, repository=ROOT):
    output = Path(output)
    if output.is_symlink() or any(p.is_symlink() for p in output.rglob("*")):
        raise ValueError("ISO bundle cannot contain symlinks")
    manifest = read_json(output / "ISO_MANIFEST.json")
    if manifest["files"] != members(output):
        raise ValueError("ISO bundle member/hash mismatch")
    verify(output / "assessment", repository, source_root)
    with tempfile.TemporaryDirectory() as tmp:
        expected = Path(tmp) / "expected"
        build_iso(expected, native, source_root, manifest["targets"], repository)
        if (expected / "ISO_MANIFEST.json").read_bytes() != (
            output / "ISO_MANIFEST.json"
        ).read_bytes():
            raise ValueError("ISO bundle differs from source re-performance")
    return dict(verified=True, targets=manifest["targets"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "verify"])
    parser.add_argument("--target", action="append", choices=["ISO27001", "ISO42001", "C5"])
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-root", required=True)
    args = parser.parse_args()
    if args.command == "verify" and args.target:
        parser.error("Verification uses the targets in the bundle manifest")
    try:
        native = compile_registry()
        result = (
            build_iso(
                args.output, native, args.source_root, args.target or ["ISO27001", "ISO42001"]
            )
            if args.command == "build"
            else verify_iso(args.output, native, args.source_root)
        )
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"CCF ISO error: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
