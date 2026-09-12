"""Source-access work queue and original native mapping candidates, not a crosswalk."""

from enterprise.ccf.registry import digest

from .hipaa import SECURITY_ATTRIBUTES
from .models import Catalog

TODAY = "2026-09-11"

FRAMEWORKS = [
    (
        "SOC2",
        "SOC 2",
        "2017 TSC / 2022 points of focus; description criteria pending",
        "AICPA",
        "https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022",
        "METADATA_ONLY",
        ["SECURITY", "AVAILABILITY", "CONFIDENTIALITY", "PROCESSING_INTEGRITY", "PRIVACY"],
        ["SECURITY"],
    ),
    (
        "HIPAA",
        "HIPAA assessment",
        "45 CFR Part 164; eCFR displayed through 2026-09-10; scope review pending",
        "HHS / eCFR",
        "https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164",
        "METADATA_ONLY",
        ["GENERAL", "SECURITY", "PRIVACY", "BREACH"],
        ["GENERAL"],
    ),
    (
        "ISO27001",
        "ISO/IEC 27001",
        "2022; amendments and applicable edition to validate",
        "ISO",
        "https://www.iso.org/standard/27001",
        "LICENSED_COPY_REQUIRED",
        ["ISMS", "ANNEX_A"],
        ["ISMS", "ANNEX_A"],
    ),
    (
        "ISO42001",
        "ISO/IEC 42001",
        "2023; amendments and applicable edition to validate",
        "ISO",
        "https://www.iso.org/standard/42001",
        "LICENSED_COPY_REQUIRED",
        ["AIMS", "ANNEX_A"],
        ["AIMS", "ANNEX_A"],
    ),
    (
        "C5",
        "BSI C5",
        "Current edition/source validation pending",
        "BSI",
        "https://www.bsi.bund.de/EN/Topics/CloudComputing/Compliance_Criteria_Catalogue/Compliance_Criteria_Catalogue_node.html",
        "METADATA_ONLY",
        ["BASIC", "ADDITIONAL"],
        ["BASIC"],
    ),
]

# These are section-level discovery entries, not decomposed legal obligations. Each remains
# unreviewed, and the independent framework inventory gate prevents complete coverage claims.
HIPAA = [
    ("164.104", "GENERAL", "Entity and business-associate applicability", "SH-LEG-001"),
    ("164.105", "GENERAL", "Organizational arrangements and scope", "SH-GOV-003"),
    ("164.106", "GENERAL", "Relationship to other requirements", "SH-LEG-001"),
    ("164.302", "SECURITY", "Security-rule applicability", "SH-DAT-002"),
    ("164.304", "SECURITY", "Security definitions and scope vocabulary", "SH-POL-001"),
    (
        "164.306",
        "SECURITY",
        "Security standards and implementation-specification decisions",
        "SH-SEC-001",
    ),
    ("164.308", "SECURITY", "Administrative safeguards", "SH-ERM-001"),
    ("164.310", "SECURITY", "Physical safeguards", "SH-SEC-001"),
    ("164.312", "SECURITY", "Technical safeguards", "SH-IAM-002"),
    ("164.314", "SECURITY", "Organizational security requirements", "SH-TPR-003"),
    ("164.316", "SECURITY", "Security policies, procedures and documentation", "SH-POL-001"),
    ("164.318", "SECURITY", "Security compliance dates", "SH-LEG-001"),
    ("164.400", "BREACH", "Breach-notification applicability", "SH-INC-001"),
    ("164.402", "BREACH", "Breach definitions and assessment", "SH-INC-002"),
    ("164.404", "BREACH", "Individual notification", "SH-INC-001"),
    ("164.406", "BREACH", "Media notification", "SH-INC-001"),
    ("164.408", "BREACH", "Secretary notification", "SH-INC-001"),
    ("164.410", "BREACH", "Business-associate notification", "SH-TPR-003"),
    ("164.412", "BREACH", "Law-enforcement delay", "SH-LEG-001"),
    ("164.414", "BREACH", "Administrative requirements and burden of proof", "SH-REC-001"),
    ("164.500", "PRIVACY", "Privacy applicability", "SH-DAT-002"),
    ("164.501", "PRIVACY", "Privacy definitions", "SH-DAT-002"),
    ("164.502", "PRIVACY", "Uses and disclosures: general rules", "SH-DAT-002"),
    ("164.504", "PRIVACY", "Organizational requirements for uses and disclosures", "SH-TPR-003"),
    ("164.506", "PRIVACY", "Treatment, payment and healthcare operations", "SH-DAT-002"),
    ("164.508", "PRIVACY", "Uses and disclosures requiring authorization", "SH-DAT-002"),
    ("164.510", "PRIVACY", "Agreement or objection opportunities", "SH-DAT-002"),
    ("164.512", "PRIVACY", "Other permitted uses and disclosures", "SH-DAT-002"),
    ("164.514", "PRIVACY", "Other requirements for uses and disclosures", "SH-DAT-002"),
    ("164.520", "PRIVACY", "Notice of privacy practices", "SH-DAT-002"),
    ("164.522", "PRIVACY", "Restrictions and confidential communications", "SH-DAT-002"),
    ("164.524", "PRIVACY", "Access to protected health information", "SH-DAT-002"),
    ("164.526", "PRIVACY", "Amendment of protected health information", "SH-DAT-002"),
    ("164.528", "PRIVACY", "Accounting of disclosures", "SH-REC-001"),
    ("164.530", "PRIVACY", "Administrative privacy requirements", "SH-POL-001"),
    ("164.532", "PRIVACY", "Transition provisions", "SH-LEG-001"),
    ("164.534", "PRIVACY", "Privacy compliance dates", "SH-LEG-001"),
]


def starter(native):
    controls = {r["id"]: r for r in native["records"] if r["kind"] == "control"}
    sources, frameworks, requirements, mappings = [], [], [], []

    def add(fid, ref, cat, summary, control=None):
        rid = f"{fid}:{ref}"
        requirements.append(
            dict(
                id=rid,
                framework_id=fid,
                source_id=f"SOURCE-{fid}",
                locator=ref,
                category=cat,
                summary=summary,
                attributes=[
                    dict(
                        id="SOURCE_REVIEW",
                        objective="Validate exact source, decompose obligations and review scoped native support",
                        kind="ASSESSMENT",
                        evidence_expectation="Authorized source edition, requirement decomposition and reviewed scope/mapping workpaper",
                    )
                ],
            )
        )
        if control:
            mappings.append(
                dict(
                    id=f"CANDIDATE-{fid}-{ref}",
                    requirement_id=rid,
                    control_id=control,
                    control_digest=digest(controls[control]),
                    attribute_ids=["SOURCE_REVIEW"],
                    rationale="Original engineering routing suggestion for source review; not an exact requirement-level mapping.",
                    uncovered="All requirement attributes and legal/assessment scope remain unreviewed.",
                )
            )
        return rid

    for fid, title, edition, publisher, url, access, categories, mandatory in FRAMEWORKS:
        sources.append(
            dict(
                id=f"SOURCE-{fid}",
                publisher=publisher,
                edition=edition,
                url=url,
                retrieved_on=TODAY,
                effective_from=None,
                access=access,
                rights_note="Reference metadata only. Validate authorized full source and reuse rights before importing text or accepting mappings.",
            )
        )
        if fid == "SOC2":
            groups = [
                (f"CC{i}", count, "SECURITY")
                for i, count in enumerate([5, 3, 4, 2, 3, 8, 5, 1, 2], 1)
            ]
            groups += [
                ("A1", 3, "AVAILABILITY"),
                ("C1", 2, "CONFIDENTIALITY"),
                ("PI1", 5, "PROCESSING_INTEGRITY"),
            ]
            groups += [
                (f"P{i}", count, "PRIVACY") for i, count in enumerate([1, 1, 2, 3, 2, 7, 1, 1], 1)
            ]
            for prefix, count, cat in groups:
                for n in range(1, count + 1):
                    add(
                        fid,
                        f"{prefix}.{n}",
                        cat,
                        "Candidate criterion identifier; exact TSC text and points-of-focus analysis pending",
                    )
            add(
                fid,
                "PREP-DESCRIPTION-SCOPE",
                "SECURITY",
                "Internal preparation gate: populate description criteria, system boundary and assessment obligations",
            )
        elif fid == "HIPAA":
            for ref, cat, summary, control in HIPAA:
                add(fid, ref, cat, summary, control)
        else:
            for cat in categories:
                add(
                    fid,
                    f"PREP-SOURCE-{cat}",
                    cat,
                    "Internal preparation gate, not a publisher requirement: populate and review the complete source inventory",
                )
        frameworks.append(
            dict(
                id=fid,
                title=title,
                edition=edition,
                source_ids=[f"SOURCE-{fid}"],
                categories=categories,
                required_categories=mandatory,
                expected_requirement_ids=[
                    r["id"] for r in requirements if r["framework_id"] == fid
                ],
                inventory_complete=False,
                limitation="Discovery inventory only; exact source, completeness, applicability and mappings remain unreviewed. This cannot generate a complete compliance delta.",
            )
        )
    for section, attributes in SECURITY_ATTRIBUTES.items():
        requirement = next(r for r in requirements if r["id"] == f"HIPAA:{section}")
        for paragraph, label, control, specification in attributes:
            requirement["attributes"].append(
                dict(
                    id=paragraph,
                    objective=label,
                    kind="CONTROL",
                    specification=specification,
                    evidence_expectation=f"Scoped implementation and review records for {section}({paragraph[0]}){paragraph[1:]}; addressable decisions require documented analysis, not automatic exclusion",
                )
            )
            mappings.append(
                dict(
                    id=f"CANDIDATE-HIPAA-{section}-{paragraph}",
                    requirement_id=requirement["id"],
                    control_id=control,
                    control_digest=digest(controls[control]),
                    attribute_ids=[paragraph],
                    rationale="Paragraph-level source review routing to a native control; validate actual design coverage before acceptance.",
                    uncovered="Health-data scope, implementation detail, required/alternative measures, and assessment evidence remain unresolved.",
                )
            )
    return Catalog.model_validate(
        dict(
            schema_version="0.2.0",
            id="SH-CCF-ASSURANCE-STARTER",
            version="0.2.0",
            native_snapshot_id=digest(native),
            sources=sources,
            frameworks=frameworks,
            requirements=requirements,
            mappings=mappings,
        )
    )
