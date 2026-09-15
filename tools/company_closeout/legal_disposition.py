"""Reconcile the existing legal review population to later scoped company decisions."""

from __future__ import annotations

import json
from pathlib import Path

from .edition import encoded, sha

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/legal/gap-instruments/review-support/decisions.json"

BILLING = {
    "SH-LEGAL-DRAFT-BILLING-U01",
    "SH-LEGAL-DRAFT-BILLING-U02",
    "SH-LEGAL-DRAFT-BILLING-U03",
    "SH-LEGAL-DRAFT-BILLING-U04",
    "SH-LEGAL-DRAFT-BILLING-T01",
    "SH-LEGAL-DRAFT-BILLING-T02",
    "BILLTAX-U01",
    "BILLTAX-U02",
    "BILLTAX-U03",
    "BILLTAX-U05",
    "BILLTAX-P02",
}
MATERIAL = {
    "FIN-U01",
    "FIN-U02",
    "FIN-U03",
    "FIN-U05",
    "DEBT-U01",
    "DEBT-U03",
    "DEBT-U05",
    "SH-LEGAL-DRAFT-HOST-RIGHTS-U03",
    "SH-LEGAL-DRAFT-HOST-RIGHTS-U04",
    "SH-LEGAL-DRAFT-CARRY-U01",
    "TAX-U01",
    "TAX-U04",
}
FUTURE_PACKAGES = {"colo", "tenure", "uranium-custody", "mark-clearance"}


def build(root=ROOT):
    source = root / SOURCE.relative_to(ROOT)
    original = json.loads(source.read_bytes())
    rows = []
    seen = set()
    for item in original["items"]:
        identity = item["id"]
        if identity in seen:
            raise ValueError("Duplicate legal decision identity")
        seen.add(identity)
        paths = [item["source_path"], item["clause_path"].split("#")[0]]
        status = "DRAFT_TERM_NOT_ADOPTED_NOT_AN_EXECUTED_OBLIGATION"
        explanation = (
            "The draft remains a proposal. Accepted facts in its stated basis retain their "
            "original authority; this disposition adds no term, right or deadline. "
            "The selected company edition does not rely on this proposed clause as executed."
        )
        if item["kind"] == "Unresolved field":
            status = "SOURCE_COMPLETION_REQUIRED_FOR_AFFECTED_INSTRUMENT"
            explanation = (
                "The precise field remains unsupported by this review item. Its next action "
                "is retained below; missing evidence does not create a new owner preference "
                "or establish real execution. Check later company record sources before use."
            )
        if identity in BILLING:
            status = "SUPERSEDED_IN_PART_BY_ACCEPTED_FF003_BILLING"
            explanation = (
                "The accepted FF-003 successor supplies Copperreach Fabrication, Inc., SHI "
                "as Foundry Field issuer, January 31 2027 base scenario and seller-borne "
                "$152,250 tax on $1,740,000 principal. Scope is issuance only; no later "
                "tax remittance, principal collection or income-tax deduction is inferred."
            )
            paths += [
                "docs/canon/FOUNDRY_FIELD_BILLING_ADOPTION_2026-09-13.md",
                "enterprise/closeout/source/adjustments.json",
            ]
        elif identity == "BILLTAX-U04":
            status = "OWNER_DIRECTION_RESOLVED_IMPLEMENTATION_RECONCILIATION_REQUIRED"
            explanation = (
                "C-corporation tax treatment of the Delaware LLC from formation is selected. "
                "The history is newly authored; use the adopted tax workpaper rather than "
                "borrowing ARU rates or treating missing tax as zero."
            )
            paths += ["docs/canon/COMPANY_CLOSEOUT_DIRECTIONS_2026-09-15.md"]
        elif identity in MATERIAL:
            status = "MATERIAL_SOURCE_OR_RIGHTS_BOUNDARY"
            explanation = (
                "This cannot be filled by a template or inferred from rounded financial "
                "figures. Preserve the exact unsupported party/right/eligibility field, "
                "current source economics and affected claim. No compulsory funding, "
                "new investor, collateral, host participation or tax election is invented."
            )
        elif item["package"] in FUTURE_PACKAGES:
            status = "FUTURE_OR_CONDITIONAL_INSTRUMENT_NOT_CURRENT_EXECUTION"
            explanation = (
                "Keep the represented service/site/external-clearance activation gate. "
                "Draft terms and future supporting evidence are not current operations. "
                "This remains an affected future claim, not a universal company-close blocker."
            )
        elif identity in {"FORM-U03", "LAND-U04"}:
            status = "REAL_EXTERNAL_EVIDENCE_OUTSIDE_SYNTHETIC_ASSIGNMENT"
            explanation = (
                "The assignment authorizes labeled synthetic records, not real incorporation, "
                "parcel acquisition or government issuance. Retain that external-evidence "
                "limit without making a real-world filing a prerequisite for fictional books."
            )
        elif identity == "SH-LEGAL-DRAFT-WORKFORCE-U02":
            status = "SCOPED_CURRENT_PAYROLL_SUCCESSOR_AVAILABLE"
            explanation = (
                "The retrospective August census/payroll defines legal employer, jurisdiction, "
                "withholding assumptions and known-on dates. It supplies that declared population "
                "only; consult its exact financial replacement bridge and limitations."
            )
            paths += [
                "enterprise/operations/source/completed_period_2026_08.json",
                "enterprise/operations/docs/completed-period.md",
            ]
        rows.append(
            {
                "id": identity,
                "package": item["package"],
                "field_or_term": item["text"],
                "original_status": item["status"],
                "original_next_action_or_basis": item["action_or_basis"],
                "current_disposition": status,
                "rationale": explanation,
                "original_json_pointer": item["json_pointer"],
                "clause_path": item["clause_path"],
                "source_hashes": {p: sha((root / p).read_bytes()) for p in paths},
            }
        )
    return {
        "record_id": "SH-C04-LEGAL-DISPOSITION-2026-09-15",
        "schema_version": "1.0.0",
        "prepared_on": "2026-09-15",
        "available_on": "2026-09-15",
        "status": "RECONCILIATION_NOT_BLANKET_ADOPTION",
        "source_path": str(source.relative_to(root)),
        "source_sha256": sha(source.read_bytes()),
        "population_count": len(rows),
        "package_count": len({r["package"] for r in rows}),
        "scope": "Complete existing review-item population; not certification of every legal instrument",
        "items": rows,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = ROOT / "docs/internal/company-closeout/LEGAL_DISPOSITIONS.json"
    result = encoded(build())
    if args.check:
        if path.read_bytes() != result:
            raise ValueError("Stale legal disposition source/derived reconciliation")
    else:
        path.write_bytes(result)
    print(f"PASS {json.loads(result)['population_count']} individually retained legal review items")
