"""Build and re-perform the approved reference design and its unexecuted workpapers."""

import argparse
import csv
import hashlib
import json
import tempfile
from pathlib import Path

from enterprise.ccf.registry import ROOT, compile_registry, digest

from .__main__ import build, read_json, verify, verify_sources, write_json
from .catalog import HIPAA, starter
from .engine import data, plan
from .hipaa import SECURITY_ATTRIBUTES
from .models import Assessment, Catalog
from .reporting import cell

DATA = Path(__file__).with_name("reference_data")
AS_OF = "2026-09-11"
BOUNDARIES = ["corporate", "RUNTIME-RENO-COLO", "RUNTIME-BOISE-DR"]
UNREVIEWED = "Candidate support only; source context, implementation sufficiency and independent review remain open."
LEGAL_STATUS = (
    "Reconcile the downloaded volume-2 amendment date 2026-08-28 with live eCFR and HHS legal-status notices. "
    "HHS reports most of the 2024 reproductive-health rule vacated, including specified notice provisions. "
    "Do not implement a parsed provision merely because it remains printed in an XML source."
)
HHS_STATUS_URL = "https://www.hhs.gov/hipaa/for-professionals/special-topics/reproductive-health/final-rule-fact-sheet/index.html"

# Original workpaper topics. These are scoped engineering proposals, not legal conclusions.
EXTRA_HIPAA = {
    "164.306": [
        ("a", "Protect ePHI and address foreseeable threats and impermissible use", "SH-SEC-001"),
        ("b", "Document risk-based safeguards for the service", "SH-ERM-001"),
        (
            "d",
            "Analyze each addressable measure and document any equivalent alternative",
            "SH-POL-003",
        ),
        ("e", "Maintain safeguards as the service changes", "SH-ASS-002"),
    ],
    "164.314": [
        (
            "a(2)(i)",
            "Specify associate security, reporting and subcontractor obligations",
            "SH-TPR-003",
        ),
        ("a(2)(iii)", "Carry security obligations through subcontractor agreements", "SH-TPR-003"),
    ],
    "164.316": [
        ("a", "Maintain the security policy and procedure set", "SH-POL-001"),
        ("b(1)", "Retain written security decisions and required records", "SH-REC-001"),
        ("b(2)(i)", "Apply the six-year security documentation retention rule", "SH-DAT-003"),
        ("b(2)(ii)", "Make documentation available to responsible personnel", "SH-POL-001"),
        ("b(2)(iii)", "Review and update security documentation", "SH-POL-001"),
    ],
    "164.402": [
        ("DEFINITION", "Evaluate breach exceptions and documented compromise risk", "SH-INC-002"),
    ],
    "164.410": [
        (
            "a",
            "Identify associate breach discovery and the upstream notification duty",
            "SH-INC-001",
        ),
        ("b", "Track discovery and notification timing against law and contract", "SH-INC-002"),
        (
            "c",
            "Provide affected-person and available breach details to the upstream entity",
            "SH-TPR-003",
        ),
    ],
    "164.412": [
        ("CONTEXT", "Document any lawful notification delay and its duration", "SH-LEG-001")
    ],
    "164.414": [
        (
            "CONTEXT",
            "Retain breach-decision evidence and required administrative measures",
            "SH-REC-001",
        )
    ],
    "164.502": [
        ("a(3)", "Restrict associate uses and disclosures to permitted purposes", "SH-DAT-002"),
        ("a(4)", "Support required associate disclosures and regulator access", "SH-LEG-001"),
        ("b", "Assess minimum-necessary constraints and exceptions", "SH-DAT-002"),
        ("e", "Establish documented assurances across the associate chain", "SH-TPR-003"),
    ],
    "164.504": [
        ("e(1)", "Address known material agreement violations", "SH-TPR-004"),
        ("e(2)(i)", "Define permitted contract uses and disclosures", "SH-LEG-002"),
        ("e(2)(ii)(A)", "Restrict associate use and disclosure", "SH-DAT-002"),
        ("e(2)(ii)(B)", "Specify safeguards and Security Rule compliance", "SH-SEC-001"),
        ("e(2)(ii)(C)", "Report impermissible disclosures and breaches", "SH-INC-001"),
        ("e(2)(ii)(D)", "Flow restrictions through subcontractors", "SH-TPR-003"),
        ("e(2)(ii)(E)", "Support individual-access obligations", "SH-DAT-002"),
        ("e(2)(ii)(F)", "Support amendment obligations", "SH-DAT-004"),
        ("e(2)(ii)(G)", "Support disclosure-accounting obligations", "SH-REC-001"),
        ("e(2)(ii)(H)", "Apply requirements to delegated covered-entity functions", "SH-LEG-001"),
        ("e(2)(ii)(I)", "Make relevant records available to the Secretary", "SH-REC-002"),
        (
            "e(2)(ii)(J)",
            "Return or destroy information or document continuing safeguards",
            "SH-TPR-005",
        ),
        ("e(2)(iii)", "Preserve contract termination rights", "SH-LEG-002"),
        ("e(5)", "Apply subcontractor agreement requirements", "SH-TPR-003"),
    ],
    "164.514": [
        (
            "CONTEXT",
            "Validate de-identification, limited-data-set and minimum-necessary conditions",
            "SH-DAT-002",
        )
    ],
    "164.524": [
        (
            "CONTEXT",
            "Route access requests and support the contracted designated record set",
            "SH-DAT-002",
        )
    ],
    "164.526": [
        ("CONTEXT", "Preserve traceable amendment requests and downstream updates", "SH-DAT-004")
    ],
    "164.528": [("CONTEXT", "Maintain disclosure-accounting support where required", "SH-REC-001")],
}


def source_inventory():
    return read_json(DATA / "hipaa_inventory.json")


def reference_inputs(native, include_c5=True):
    c = data(starter(native))
    c["id"], c["version"] = "SH-CCF-REFERENCE-RENO-BOISE", "0.3.0-reference"
    c["requirements"] = [
        r for r in c["requirements"] if r["framework_id"] in {"ISO27001", "ISO42001"}
    ]
    c["mappings"] = []
    c["sources"] = [s for s in c["sources"] if s["id"] in {"SOURCE-ISO27001", "SOURCE-ISO42001"}]
    c["frameworks"] = [f for f in c["frameworks"] if f["id"] in {"ISO27001", "ISO42001"}]
    controls = {r["id"]: r for r in native["records"] if r["kind"] == "control"}
    inv = source_inventory()
    for sid, publisher, edition, url, content_hash in [
        (
            "SOURCE-SOC2-TSC",
            "AICPA",
            "2017 TSC; revised points of focus 2022; retrieved 75-page variant",
            "https://assets.ctfassets.net/rb9cdnjh59cm/5jT1narHNQNzt4JGlkd1gr/248661d08e42531329d147782a6f8854/Trust-services-criteria.pdf",
            "23a099dd1dc273b7a45fda2351f376344c33fcb2911d586036c0e0d631b8ad69",
        ),
        (
            "SOURCE-SOC2-DC",
            "AICPA",
            "2018 DC; revised guidance 2022; 335512-byte variant",
            "https://assets.ctfassets.net/rb9cdnjh59cm/1vCduR1U2OnhIvFFaDBjMv/836050054707e9afb65adeb30d2e95d8/92317096_dc_section_200_clean_version.pdf",
            "81286ab2afbf98ede900366bd36b461fd0ca554e18342c403fcea3a33d2a6d98",
        ),
        (
            "SOURCE-HIPAA",
            "GPO / GovInfo eCFR bulk data",
            "45 CFR Parts 160 and 164; volume 2 amendment date 2026-08-28; legal reconciliation pending",
            inv["source_url"],
            inv["source_sha256"],
        ),
    ]:
        c["sources"].append(
            dict(
                id=sid,
                publisher=publisher,
                edition=edition,
                url=url,
                retrieved_on=AS_OF,
                effective_from=None,
                access="AVAILABLE",
                content_sha256=content_hash,
                rights_note="Original outside exports; references and original planning notes only. Acquisition is not source or mapping approval.",
            )
        )

    def add(fid, ref, cat, summary, source, attrs, routes, locator=None):
        rid = f"{fid}:{ref}"
        c["requirements"].append(
            dict(
                id=rid,
                framework_id=fid,
                source_id=source,
                locator=locator or ref,
                category=cat,
                summary=summary,
                attributes=attrs,
            )
        )
        for aid, ids in routes.items():
            for cid in ids:
                c["mappings"].append(
                    dict(
                        id=f"REF-{rid}-{aid}-{cid}",
                        requirement_id=rid,
                        control_id=cid,
                        control_digest=digest(controls[cid]),
                        attribute_ids=[aid],
                        rationale=f"Candidate native design for {summary}; test the exact source objective and every uncovered aspect.",
                        uncovered=UNREVIEWED,
                    )
                )

    def attr(aid, objective, kind="CONTROL", specification="UNRESOLVED"):
        return dict(
            id=aid,
            objective=objective,
            kind=kind,
            specification=specification,
            evidence_expectation=f"Source-anchored workpaper, accountable role, scoped design and reconciled evidence population for: {objective}. No operating records supplied.",
        )

    for r in read_json(DATA / "soc2.json"):
        ref = r["locator"]
        cat = (
            "SECURITY"
            if ref.startswith(("CC", "DC"))
            else "AVAILABILITY"
            if ref.startswith("A")
            else "CONFIDENTIALITY"
            if ref.startswith("C")
            else "PROCESSING_INTEGRITY"
            if ref.startswith("PI")
            else "PRIVACY"
        )
        add(
            "SOC2",
            ref,
            cat,
            r["summary"],
            "SOURCE-SOC2-" + r["source"],
            [
                attr("OBJECTIVE", r["summary"], "DOCUMENT" if r["source"] == "DC" else "CONTROL"),
                attr(
                    "SOURCE_CONTEXT",
                    "Analyze exact criterion, guidance and applicable points of focus without treating every point as a separate mandatory control",
                    "ASSESSMENT",
                ),
            ],
            {"OBJECTIVE": r["controls"]},
            locator=f"{ref}; PDF page(s) {','.join(map(str, r['pdf_pages']))}",
        )

    old_routes = {ref: cid for ref, _, _, cid in HIPAA}
    for s in inv["sections"]:
        ref = s["locator"]
        number = int(ref.split(".")[1])
        cat = (
            "GENERAL"
            if ref.startswith("160.") or number < 300
            else "SECURITY"
            if number < 400
            else "BREACH"
            if number < 500
            else "PRIVACY"
        )
        attrs = [
            attr(
                "SOURCE_CONTEXT",
                f"Reconcile {len(s['paragraphs'])} paragraph records, definitions, exceptions, legal status and scoped responsibility for {ref}",
                "ASSESSMENT",
            )
        ]
        routes = {"SOURCE_CONTEXT": [old_routes.get(ref, "SH-LEG-001")]}
        for aid, label, cid, spec in SECURITY_ATTRIBUTES.get(ref, []):
            # The prior route was too narrow: security evaluation is broader than vulnerability SLAs.
            cid = "SH-ASS-004" if ref == "164.308" and aid == "a(8)" else cid
            attrs.append(attr(aid, label, specification=spec))
            routes[aid] = [cid]
        for aid, label, cid in EXTRA_HIPAA.get(ref, []):
            attrs.append(attr(aid, label))
            routes[aid] = [cid]
        add("HIPAA", ref, cat, s["title"], "SOURCE-HIPAA", attrs, routes)

    for fid, title, cats, mandatory, sources in [
        (
            "SOC2",
            "SOC 2 criteria and description workplan",
            ["SECURITY", "AVAILABILITY", "CONFIDENTIALITY", "PROCESSING_INTEGRITY", "PRIVACY"],
            ["SECURITY"],
            ["SOURCE-SOC2-TSC", "SOURCE-SOC2-DC"],
        ),
        (
            "HIPAA",
            "HIPAA scoped obligation workplan",
            ["GENERAL", "SECURITY", "PRIVACY", "BREACH"],
            ["GENERAL"],
            ["SOURCE-HIPAA"],
        ),
    ]:
        c["frameworks"].append(
            dict(
                id=fid,
                title=title,
                edition="Source-bound reference preparation",
                source_ids=sources,
                categories=cats,
                required_categories=mandatory,
                expected_requirement_ids=[
                    r["id"] for r in c["requirements"] if r["framework_id"] == fid
                ],
                inventory_complete=False,
                limitation="Extracted source population; requirement semantics, legal applicability, source context and independent inventory review remain open.",
            )
        )
    if include_c5:
        extension = read_json(DATA / "c5_discovery.json")
        for key in ("sources", "frameworks", "requirements"):
            c[key].extend(extension[key])
        for row in read_json(DATA / "c5_workpapers.json"):
            r = next(r for r in c["requirements"] if r["id"] == "C5:" + row["locator"])
            r["locator"] = row["locator"] + "; PDF page(s) " + ",".join(map(str, row["pdf_pages"]))
            r["summary"] = "Continuity extension workpaper: " + row["attributes"][0]
            for i, objective in enumerate(row["attributes"], 1):
                aid = f"OBJECTIVE-{i}"
                r["attributes"].append(attr(aid, objective))
                cid = row["control_id"]
                c["mappings"].append(
                    dict(
                        id=f"REF-{r['id']}-{aid}-{cid}",
                        requirement_id=r["id"],
                        control_id=cid,
                        control_digest=digest(controls[cid]),
                        attribute_ids=[aid],
                        rationale="Original source-anchored continuity extension candidate; validate all specified conditions and customer dependencies.",
                        uncovered=UNREVIEWED,
                    )
                )
    catalog = Catalog.model_validate(c)
    selected = {
        "SOC2": {"SECURITY", "AVAILABILITY", "CONFIDENTIALITY"},
        "HIPAA": {"GENERAL", "SECURITY", "PRIVACY", "BREACH"},
    }
    if include_c5:
        selected["C5"] = {"BASIC", "ADDITIONAL"}
    requirements = [
        r for r in catalog.requirements if r.category in selected.get(r.framework_id, set())
    ]
    used = {
        m.control_id
        for m in catalog.mappings
        if any(r.id == m.requirement_id for r in requirements)
    }
    implementations = [
        dict(
            id=f"REF-{boundary}-{cid}",
            version="REFERENCE-DESIGN-1",
            control_id=cid,
            control_digest=digest(controls[cid]),
            boundary_id=boundary,
            owner_role_id=controls[cid]["data"]["owner_role_id"],
            state="PROPOSED",
            effective_from=AS_OF,
            effective_to=None,
        )
        for boundary in BOUNDARIES
        for cid in sorted(used)
    ]
    assessment = Assessment.model_validate(
        dict(
            schema_version="0.2.0",
            catalog_digest=digest(data(catalog)),
            scope=dict(
                id="SH-REFERENCE-RENO-BOISE-2026-09-11",
                boundaries=BOUNDARIES,
                baseline=[
                    dict(framework_id=f, categories=sorted(selected[f])) for f in ["SOC2", "HIPAA"]
                ],
                targets=[dict(framework_id="C5", categories=sorted(selected["C5"]))]
                if include_c5
                else [],
                period_start=AS_OF,
                period_end=AS_OF,
                known_on=AS_OF,
                assessment_mode="DESIGN",
                origin="SYNTHETIC",
                assumptions=[
                    "Owner-approved reference planning scope; approval does not attest to these unreviewed assessment records.",
                    "Type 2 readiness is the destination; no operating examination period or examiner appointed.",
                    "Business-associate/subcontractor scenario; no actual PHI processing or contract execution asserted.",
                    "No inherited corporate or supplier control is assumed effective at either site; document responsibility and obtain separate scoped evidence.",
                    LEGAL_STATUS,
                ],
            ),
            implementations=implementations,
            evidence=[],
            tests=[],
            applicability=[
                dict(
                    requirement_id=r.id,
                    boundary_id=b,
                    disposition="UNRESOLVED",
                    rationale=(
                        "Owner selected the reference categories; requirement-level applicability and source context need review."
                        if r.framework_id == "SOC2"
                        else "Determine direct duty, delegated customer support, supplier performance or conditional/nonapplicable provision; no automatic exclusion. "
                        + (
                            LEGAL_STATUS
                            if r.framework_id == "HIPAA"
                            else "C5 source inventory is not yet decomposed into reviewed obligations."
                        )
                    ),
                )
                for r in requirements
                for b in BOUNDARIES
            ],
            disclosures=[],
        )
    )
    plan(catalog, assessment, native)
    return catalog, assessment


PROCEDURES = {
    "IAM": [
        "Reconcile authoritative worker, contractor and non-human identity populations to application and privileged-account exports, including both sites.",
        "For joiners, movers, leavers and privileged exceptions, trace the initiating event to approval, assigned rights, timestamps and independent review; investigate orphaned and late actions.",
        "Inspect authentication, session and emergency-access settings against the approved requirement; document any missing authentication-specific control design.",
    ],
    "BCM": [
        "Reconcile critical services, datasets and supplier dependencies to the BIA and documented recovery objectives; objectives require management acceptance.",
        "Inspect backup execution, failure alerts, retention and isolation, then observe a restore or recovery exercise and reconcile recovered data and timing to the approved objectives.",
        "Test Reno loss and Boise recovery dependencies, capacity, access and communications; track failed steps and retest results without deleting earlier failures.",
    ],
    "SEC": [
        "Reconcile asset and data-flow inventories to security architecture, endpoint/network configurations, log sources and physical supplier boundaries.",
        "Inspect configured safeguards and independently select events to trace detection, triage, escalation and closure; missing collection is an exception, not evidence of no incidents.",
        "For physical access and environmental safeguards, obtain site-specific provider commitments and operational evidence; a generic architecture policy alone is insufficient.",
    ],
    "TPR": [
        "Reconcile all in-scope providers and subcontractors to criticality, access, data flows and current contracts; identify incomplete or unsigned agreements.",
        "Inspect required service, privacy, incident, assurance, subcontractor and exit clauses and identify customer versus supplier obligations explicitly.",
        "Reconcile provider evidence scope and period, exceptions and complementary controls to each dependent service; trace monitoring and remediation rather than inheriting a report opinion.",
    ],
    "DAT": [
        "Trace representative data classes through collection, access, storage, sharing, backup, recovery, retention and destruction; reconcile to approved purpose and obligations.",
        "For the health-data scenario, document the designated record set, upstream/downstream roles and contract duties; inspect request handling, minimum-necessary analysis and disclosure records where applicable.",
        "Test authorization, retention, deletion and legal-hold behavior against the scoped requirement, preserving failures and unsupported cases.",
    ],
    "INC": [
        "Reconcile detection sources and service tickets to the incident population, including events initially dismissed and supplier notifications.",
        "Trace selected cases through discovery, classification, command, evidence preservation, impact, communication and closure; exercise missing real scenarios as explicitly synthetic.",
        "For associate breaches, test the upstream notification clock and required content against the source and any shorter contract deadline; do not substitute customer notification duties for the associate's duty.",
    ],
    "ENG": [
        "Reconcile deployed artifacts and configuration histories to the complete change population, including emergency and out-of-pipeline changes.",
        "Trace selected changes through authorization, peer review, risk-appropriate testing, release identity and deployment permissions.",
        "Inspect rollback or recovery proof, emergency retrospective review and separation of duties; preserve rejected, failed and bypassed changes in the test population.",
    ],
    "REC": [
        "Re-perform the evidence query/export using recorded source, parameters, timezone, transformations and period; reconcile counts to an independent source population.",
        "Verify raw and transformed hashes, access restrictions, actor/time/scope fields and links to approvals or test results.",
        "Inspect retention and disposal against specific obligations and legal holds; record incomplete populations rather than imputing missing records.",
    ],
    "LEG": [
        "Reconcile each source citation, edition, effective date, exception and court-status notice to the scoped entity, service, data and agreement.",
        "Classify the obligation as direct, delegated/customer-support, supplier-performed, conditional or not applicable with recorded rationale; obtain appropriate review before exclusion.",
        "Trace applicable duties to clauses, control designs, documentation and evidence; unresolved legal context blocks a compliance conclusion.",
    ],
}
DEFAULT_PROCEDURE = [
    "Inspect the approved control design, source obligation, accountable authority, operating trigger, evidence requirements and exception route.",
    "Reconcile the complete activity population to an independent source; select occurrences using documented risk, frequency and period coverage rather than an invented fixed sample size.",
    "Trace selected occurrences to execution, approval, recorded exceptions and remediation; retain the evidence chain and distinguish management self-assessment from independent assurance.",
]


def workpapers(catalog, assessment, native):
    controls = {r["id"]: r for r in native["records"] if r["kind"] == "control"}
    selected = {
        s.framework_id: set(s.categories)
        for s in assessment.scope.baseline + assessment.scope.targets
    }
    requirement_map = {
        r.id: r for r in catalog.requirements if r.category in selected.get(r.framework_id, set())
    }
    mappings = {}
    for m in catalog.mappings:
        mappings.setdefault((m.requirement_id, m.attribute_ids[0]), []).append(m.control_id)
    roles = {r["id"]: r["data"]["title"] for r in native["records"] if r["kind"] == "role"}
    tests = []
    for r in requirement_map.values():
        for boundary in assessment.scope.boundaries:
            for a in r.attributes:
                cids = sorted(set(mappings.get((r.id, a.id), [])))
                steps = []
                for domain in sorted({controls[c]["data"]["domain_id"] for c in cids}):
                    for step in PROCEDURES.get(domain, DEFAULT_PROCEDURE):
                        if step not in steps:
                            steps.append(step)
                tests.append(
                    dict(
                        id=f"PLAN-{r.id}-{a.id}-{boundary}",
                        requirement_id=r.id,
                        attribute_id=a.id,
                        source_id=r.source_id,
                        locator=r.locator,
                        boundary_id=boundary,
                        objective=a.objective,
                        specification=a.specification,
                        candidate_control_ids=cids,
                        candidate_implementation_ids=[f"REF-{boundary}-{c}" for c in cids],
                        accountable_role_ids=sorted(
                            {controls[c]["data"]["owner_role_id"] for c in cids}
                        ),
                        state="PLANNED_NOT_EXECUTED",
                        design_as_of=AS_OF,
                        operating_period=None,
                        responsibility="Establish corporate/provider/customer split and this boundary's local or explicitly inherited implementation; no automatic inheritance.",
                        evidence_request=a.evidence_expectation,
                        prerequisites=[
                            "Validate source context and applicability",
                            "Accept detailed implementation design and appoint personnel",
                            "Approve operating period and independent population source before operating tests",
                        ],
                        procedure=[
                            f"Read {r.locator}; document how {a.objective} applies at {boundary}."
                        ]
                        + (
                            steps
                            or [
                                "Decompose the source obligation and identify a suitable native control or a separately reviewed new-control proposal."
                            ]
                        ),
                        population_and_selection="Record source/query/parameters/timezone and reconcile an independent complete population. Establish a risk-based sample and coverage rationale before testing. No population hashes exist yet.",
                        acceptance="Every applicable objective must have adequate scoped design and independently reviewed evidence; record partial coverage, absent evidence and failures separately. This plan has no test result.",
                        review_state="PENDING",
                        evidence_ids=[],
                        findings=[],
                    )
                )
    impls = []
    for impl in assessment.implementations:
        control = controls[impl.control_id]["data"]
        impls.append(
            dict(
                id=impl.id,
                control_id=impl.control_id,
                boundary_id=impl.boundary_id,
                owner_role_id=impl.owner_role_id,
                owner_role_label=roles[impl.owner_role_id],
                appointment_status="NOT_ASSERTED",
                proposed_design=control["statement"],
                trigger=control["frequency_or_trigger"],
                native_evidence_expectation=control["evidence_expectation"],
                state="PROPOSED",
                deployment_status="NOT_ASSERTED",
                enhancements_needed=[
                    "Translate the enterprise statement into this service's actors, systems, frequency, thresholds, exceptions and evidence.",
                    "Record upstream and supplier responsibilities, local execution and any inherited design with boundary-specific validation.",
                    "Reconcile every mapped source objective; a broad native statement may need additional measures or a new control.",
                ],
            )
        )
    return dict(
        schema_version="REFERENCE-PLAN-1",
        origin="SYNTHETIC_REFERENCE_DESIGN",
        scope_id=assessment.scope.id,
        operating_period=None,
        implementations=impls,
        test_plans=tests,
    )


def validate_source_inventory(catalog, source_root):
    """Reconcile every retained HIPAA paragraph fingerprint to the pinned original XML."""
    import xml.etree.ElementTree as ET

    verify_sources(catalog, source_root)
    inv = source_inventory()
    root = ET.fromstring((Path(source_root) / inv["source_sha256"]).read_bytes())
    actual = {}
    for part in root.iter():
        if part.attrib.get("TYPE") != "PART" or part.attrib.get("N") not in {"160", "164"}:
            continue
        for section in part.iter():
            if section.attrib.get("TYPE") != "SECTION":
                continue
            locator = section.attrib["N"].replace("§ ", "")
            actual[locator] = [
                hashlib.sha256(" ".join("".join(p.itertext()).split()).encode()).hexdigest()
                for p in section.iter("P")
            ]
    expected = {s["locator"]: [p["text_sha256"] for p in s["paragraphs"]] for s in inv["sections"]}
    if len(expected) != len(inv["sections"]) or actual != expected:
        raise ValueError("HIPAA section/paragraph inventory differs from pinned source")


def bundle_files(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and p != root / "BUNDLE_MANIFEST.json"
    }


def build_reference(output, native, source_root, include_c5=True, repository=ROOT):
    output = Path(output)
    if output.exists():
        raise ValueError("Reference output must be a new directory")
    catalog, assessment = reference_inputs(native, include_c5)
    validate_source_inventory(catalog, source_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ccf-reference-", dir=output.parent) as tmp:
        staged = Path(tmp) / "bundle"
        staged.mkdir(mode=0o700)
        result = build(staged / "assessment", catalog, assessment, native, repository, source_root)
        papers = workpapers(catalog, assessment, native)
        write_json(staged / "WORKPAPERS.json", papers)
        for filename, rows in [
            ("IMPLEMENTATION_PLAN.csv", papers["implementations"]),
            ("TEST_PLAN.csv", papers["test_plans"]),
        ]:
            with (staged / filename).open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                for row in rows:
                    writer.writerow(
                        {
                            k: cell(
                                json.dumps(v)
                                if isinstance(v, (list, dict))
                                else ""
                                if v is None
                                else v
                            )
                            for k, v in row.items()
                        }
                    )
        write_json(staged / "HIPAA_SOURCE_INVENTORY.json", source_inventory())
        write_json(staged / "SOC2_SOURCE_INVENTORY.json", read_json(DATA / "soc2.json"))
        unmapped = [p for p in papers["test_plans"] if not p["candidate_control_ids"]]
        write_json(
            staged / "MAPPING_REVIEW_QUEUE.json",
            dict(unmapped_attributes=unmapped, all_mappings_pending_review=True),
        )
        (staged / "REFERENCE_SCOPE.md").write_text(
            "# Approved reference design\n\nCorporate shared controls supporting Reno primary colocation and Boise recovery. SOC 2 Security, Availability and Confidentiality; HIPAA business-associate/subcontractor scenario. Type 2 readiness is the destination.\n\n"
            "The design as-of date is 2026-09-11. No operating examination period, deployed implementation, PHI processing, personnel appointment or examiner opinion is asserted. The owner approved this planning boundary, not the unreviewed assessment record or every legal applicability decision.\n\n"
            "Corporate governance and shared technology need documented linkage to each site. Reno primary and Boise recovery need local configuration, capacity, recovery and provider evidence. Customer duties and subcontractor duties require explicit contract/data-flow analysis. The owned Northern Nevada data center and other operating businesses remain outside this first assessment.\n\n"
            "## Responsibility and data-flow work\n\nDocument the proposed customer-to-service-to-provider chain, ingestion/administration, production storage, recovery replication, backup, support access, incident communications, disclosure/individual-rights support and deletion. For each flow record data classes, role, location, authority, encryption/key owner, logging and retention. These are design questions, not assertions that those flows exist.\n\n"
            "Do not duplicate corporate execution merely to populate a site row. Record inheritance explicitly and validate each dependent boundary before accepting support. Neither provider certification nor a shared evidence file automatically satisfies our obligation.\n"
        )
        (staged / "READINESS.md").write_text(
            "# Reference readiness workplan\n\n"
            f"{len(papers['implementations'])} proposed implementation workpapers; {len(papers['test_plans'])} unexecuted attribute/boundary test plans; {len(unmapped)} plans lack a candidate native-control route. These are planning counts, not control failures or compliance percentages.\n\n"
            "## Sequence\n\n1. Reconcile sources, requirement semantics, applicability and responsibility.\n2. Review candidate mappings and uncovered aspects.\n3. Complete local implementation designs and new-control proposals where needed.\n4. Approve actual operating scope, period, personnel and evidence populations when ready.\n5. Execute tests, preserve findings, remediate and independently review.\n6. Obtain examiner acceptance before external claims; authorize customer disclosures separately.\n\n"
            "## Specific engineering gaps to resolve\n\n- Physical access, visitor controls and environmental resilience need site/provider-specific designs; generic security architecture is insufficient.\n- Capacity forecasting, headroom and alert thresholds need explicit service requirements, beyond a BIA alone.\n- Authentication, encryption/key custody and data-transfer protections need explicit technical specifications.\n- BA agreements, breach discovery/notification, subcontractor flow-down, minimum necessary and individual-rights support need scoped workflows.\n- Description criteria need a service description, commitment inventory, component/data-flow model, customer/provider dependencies, incident history and period changes.\n- Eight C5 continuity criteria have source-anchored candidate workpapers; other C5 discovery criteria still require exact objective decomposition. No mapping is approved. ISO source gates remain available but are not selected in this first package.\n\n"
            f"## Source limits\n\n61 TSC identifiers and nine DC identifiers are present with original PDF page locators. Guidance/points-of-focus and engagement-source review remain open. HIPAA contains 102 section records and 1,697 source-paragraph fingerprints; ordinal paragraph IDs are not legal citations. {LEGAL_STATUS}\n\n"
            f"[HHS legal-status notice]({HHS_STATUS_URL}). The DC PDF variant is not byte-confirmed against the account-download variant. Acquisition, extraction, mapping review, implementation and operating evidence are separate gates.\n\n"
            "The assessment engine correctly leaves source/inventory/applicability/review blockers visible. No reviews were fabricated to turn reference planning into demonstrated compliance. Use WORKPAPERS.json for implementation/test work and assessment/explorer.html or workbench.xlsx for the scoped delta.\n"
        )
        write_json(
            staged / "BUNDLE_MANIFEST.json",
            dict(
                version="REFERENCE-PLAN-1",
                include_c5=include_c5,
                native_snapshot_id=digest(native),
                files=bundle_files(staged),
            ),
        )
        for p in staged.rglob("*"):
            if p.is_file():
                p.chmod(0o600)
        staged.rename(output)
    return dict(
        output=str(output),
        implementation_workpapers=len(papers["implementations"]),
        test_plans=len(papers["test_plans"]),
        assessment_summary=result,
    )


def verify_reference(output, native, source_root, repository=ROOT):
    output = Path(output)
    if output.is_symlink() or any(p.is_symlink() for p in output.rglob("*")):
        raise ValueError("Reference bundle cannot contain symlinks")
    manifest = read_json(output / "BUNDLE_MANIFEST.json")
    if manifest["files"] != bundle_files(output):
        raise ValueError("Reference bundle member/hash mismatch")
    if type(manifest.get("include_c5")) is not bool:
        raise ValueError("Reference extension flag must be boolean")
    verify(output / "assessment", repository, source_root)
    with tempfile.TemporaryDirectory() as tmp:
        expected = Path(tmp) / "expected"
        build_reference(expected, native, source_root, manifest["include_c5"], repository)
        if (output / "BUNDLE_MANIFEST.json").read_bytes() != (
            expected / "BUNDLE_MANIFEST.json"
        ).read_bytes() or bundle_files(output) != bundle_files(expected):
            raise ValueError("Reference bundle differs from source re-performance")
    return dict(verified=True, native_snapshot_id=digest(native))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "verify"])
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--baseline-only", action="store_true")
    args = parser.parse_args()
    try:
        native = compile_registry()
        result = (
            build_reference(args.output, native, args.source_root, not args.baseline_only)
            if args.command == "build"
            else verify_reference(args.output, native, args.source_root)
        )
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"CCF reference error: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
