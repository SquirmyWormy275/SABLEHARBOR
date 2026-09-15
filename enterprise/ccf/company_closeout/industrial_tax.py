"""Validate bounded August industrial transaction-tax facts against current invoices."""

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from decimal import Decimal as D
from pathlib import Path

SOURCE = Path(__file__).with_name("industrial_transaction_tax.json")
ROOT = SOURCE.resolve().parents[3]


def validate(data, tables, root=ROOT, *, verify_source_bytes=True):
    if data["event_period"] != "2026-08" or data["available_at"] < "2026-09-15T00:00:00Z":
        raise ValueError("Wrong tax period or backdated availability")
    if set(data["source_hashes"]) != {
        "industrial/source/finance.json",
        "industrial/source/operations.json",
        "red_wash/source/core_operating_data.json",
        "enterprise/operations/source/current_company_2026_08.json",
    }:
        raise ValueError("Source binding population missing")
    for path, digest in data["source_hashes"].items():
        if verify_source_bytes and hashlib.sha256((root / path).read_bytes()).hexdigest() != digest:
            raise ValueError("Industrial tax source changed; review required")
    contracts = {
        r["contract_id"]: r
        for r in tables["current_contracts"]
        if r["unit"] not in {"foundry-field", "atlas-meridian", "advisory"}
    }
    invoices = {r["contract_id"]: r for r in tables["current_invoices"]}
    rows = data["rows"]
    if len(rows) != 34 or {r["contract_id"] for r in rows} != set(contracts):
        raise ValueError("Missing duplicate or substituted industrial contract")
    certs = {r["certificate_id"]: r for r in data["certificates"]}
    if len(certs) != 5 or len(data["certificates"]) != 5:
        raise ValueError("Wrong certificate population")
    ops = json.loads((root / "industrial/source/operations.json").read_text())
    for row in rows:
        contract = contracts[row["contract_id"]]
        invoice = invoices[row["contract_id"]]
        for field in ["customer_id", "legal_entity", "unit", "kind"]:
            if row[field] != contract[field]:
                raise ValueError("Wrong contract identity")
        if (
            row["invoice_id"] != invoice["invoice_id"]
            or D(row["principal_usd"]) != D(invoice["principal_usd"])
            or D(row["principal_usd"]) != D(contract["monthly_fee_usd"])
            or row["event_period"] != "2026-08"
            or row["available_at"] < data["available_at"]
            or D(row["sales_tax_usd"]) != 0
        ):
            raise ValueError("Invoice amount period or availability changed")
        facts = row["facts"]
        if row["legal_entity"] in {"ARU", "BST"}:
            prefix = row["contract_id"].split("-")[0]
            classes = {
                "BST": "WY_FREIGHT",
                "TRK": "WY_FREIGHT",
                "TRM": "WY_HANDLING",
                "WHS": "WY_CUSTODY_STORAGE",
            }
            if (
                row["classification"] != classes[prefix]
                or row["service_jurisdiction"] != "US-WY"
                or row["state"] != "NOT_ENUMERATED_TAXABLE_SERVICE"
                or row["certificate_id"]
            ):
                raise ValueError("Wrong Wyoming service treatment")
            expected = {
                a["id"]
                for a in ops["contract_facility_assignments"]
                if a["contract_id"] == row["contract_id"]
            }
            if (
                len(row["facility_assignment_ids"]) != len(expected)
                or set(row["facility_assignment_ids"]) != expected
            ):
                raise ValueError("Wrong facility allocation")
            if not facts["customer_retains_cargo_title"] or any(
                facts[k]
                for k in [
                    "seller_transfers_cargo_title",
                    "cargo_repair_or_alteration",
                    "well_site_production_service",
                    "equipment_possession_transferred_to_customer",
                    "passenger_transport",
                    "materials_sold",
                ]
            ):
                raise ValueError("Service factual screen failed; tax must be reassessed")
        else:
            cert = certs.get(row["certificate_id"])
            if cert is None or row["state"] != "EXEMPT_DECLARED_RESALE":
                raise ValueError("Resale evidence missing")
            if (
                cert["contract_id"] != row["contract_id"]
                or cert["invoice_id"] != row["invoice_id"]
                or cert["purchaser_id"] != row["customer_id"]
                or cert["seller_legal_entity"] != row["legal_entity"]
                or cert["period"] != "2026-08"
                or cert["reason"] != "RESALE"
                or cert["canceled"]
                or not "2026-08-01"
                <= cert["signed_on"]
                <= cert["received_on"]
                <= cert["reviewed_on"]
                <= "2026-08-25"
                or cert["available_at"] < data["available_at"]
                or cert["real_government_identifier"]
            ):
                raise ValueError("Resale certificate identity chronology or scope invalid")
            for field in [
                "seller_name",
                "seller_address",
                "purchaser_name",
                "purchaser_address",
                "item_description",
                "signer_id",
                "signer_role",
                "reviewed_by",
            ]:
                if not isinstance(cert[field], str) or not cert[field].strip():
                    raise ValueError("Certificate field missing")
            if cert["signature_state"] != "NEWLY_AUTHORED_SYNTHETIC_PURCHASER_SIGNATURE":
                raise ValueError("Fictional signature state lost")
            if row["legal_entity"] == "SHI":
                if (
                    row["classification"] != "WV_REFINER_INPUT_RESALE"
                    or row["service_jurisdiction"] != "US-WV"
                    or not facts["refiner_resells_recovered_material"]
                    or not facts["title_passes_to_buyer"]
                    or facts["consumed_as_fuel_or_office_supply"]
                    or facts["installed_in_real_property"]
                    or not cert["synthetic_tax_identity"].startswith("SH-SYN-")
                ):
                    raise ValueError("WV refiner resale factual screen failed")
            else:
                if (
                    row["classification"] != "IL_YELLOWCAKE_RESALE"
                    or row["service_jurisdiction"] != "US-IL"
                    or facts["delivery_point"] != "licensed conversion facility, Illinois"
                    or not all(
                        facts[k]
                        for k in [
                            "purchaser_out_of_state",
                            "purchaser_resells_only_to_out_of_state_buyers",
                            "onward_title_transfer_before_consumption",
                        ]
                    )
                    or facts["buyer_consumes_this_intermediate_without_resale"]
                    or facts["wyoming_customer_receipt"]
                    or cert["illinois_registration_number"] is not None
                    or cert["out_of_state_purchaser_statement"]
                    != (
                        "Purchaser is outside Illinois and will sell only to "
                        "purchasers located outside Illinois."
                    )
                ):
                    raise ValueError(
                        "Illinois resale factual screen failed; no automatic utility exemption"
                    )
    if any(
        D(data["accounting"][k])
        for k in ["additional_revenue_usd", "additional_cash_usd", "additional_sales_tax_usd"]
    ):
        raise ValueError("Annotation cannot post or plug finance")
    return {
        "contracts": len(rows),
        "certificates": len(certs),
        "classifications": dict(Counter(r["classification"] for r in rows)),
        "principal_usd": str(sum(D(r["principal_usd"]) for r in rows)),
        "sales_tax_usd": "0.00",
        "posting_mode": "ANNOTATION_ONLY",
        "scope": "AUGUST_AUTHORED_FACTUAL_SCREEN_NOT_ACTUAL_EXTERNAL_VERIFICATION",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=ROOT)
    args = parser.parse_args()
    tables = json.loads(
        subprocess.run(
            [
                sys.executable,
                "-c",
                "from enterprise.operations.completed_period import build; import json; "
                'print(json.dumps(build()["tables"]))',
            ],
            cwd=args.repository,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    print(json.dumps(validate(json.loads(SOURCE.read_text()), tables, args.repository), indent=2))


if __name__ == "__main__":
    main()
