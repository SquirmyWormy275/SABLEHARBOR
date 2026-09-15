"""Join current company populations to the dated applicability successor."""

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import date
from decimal import Decimal as D
from pathlib import Path

SOURCE = Path(__file__).with_name("current_activity_successor.json")
ROOT = SOURCE.resolve().parents[3]


def validate(data, tables, root=ROOT, legacy_rows=None):
    if data["available_on"] < data["authored_on"] or data["effective_period"] != "2026-08":
        raise ValueError("Wrong period or premature availability")
    for path, digest in data["source_hashes"].items():
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != digest:
            raise ValueError("Current source changed; applicability review stale")
    counts = {}
    for name, pop in data["populations"].items():
        ids = [r[pop["primary_key"]] for r in tables[name]]
        if len(ids) != len(set(ids)) or sorted(ids) != pop["ids"] or len(ids) != pop["count"]:
            raise ValueError("Current population member omitted duplicated or substituted")
        counts[name] = len(ids)
    boundaries = data["boundaries"]
    if len(boundaries) != 8 or {r["unit"] for r in boundaries} != {
        "foundry-field",
        "atlas-meridian",
        "advisory",
        "willow",
        "project-cradle",
        "pale-sun",
        "american-resource-utility",
        "corporate",
    }:
        raise ValueError("Business/corporate boundary omitted")
    for boundary in boundaries:
        for table, key, field in [
            ("current_contracts", "contract_id", "contract_ids"),
            ("current_projects", "project_id", "project_ids"),
        ]:
            ids = {r[key] for r in tables[table] if r["unit"] == boundary["unit"]}
            if len(boundary[field]) != len(ids) or set(boundary[field]) != ids:
                raise ValueError("Contract/project assigned to wrong boundary")
    service_tax = data.get("august_core_transaction_tax")
    if service_tax:
        expected = {
            r["contract_id"]: r
            for r in tables["current_contracts"]
            if r["unit"] in {"foundry-field", "atlas-meridian", "advisory"}
        }
        supplied = service_tax["customers"]
        if len(supplied) != 58 or {r["contract_id"] for r in supplied} != set(expected):
            raise ValueError("Current service tax population incomplete")
        for row in supplied:
            contract = expected[row["contract_id"]]
            if row["customer_id"] != contract["customer_id"] or D(row["principal_usd"]) != D(
                contract["monthly_fee_usd"]
            ):
                raise ValueError("Current tax issuer/principal mismatch")
            if (
                row["billing_jurisdiction"] != "US-CA"
                or row["august_service_use_jurisdiction"] != "US-CA"
                or row["tangible_property_delivered"]
                or D(row["sales_tax_usd"]) != 0
            ):
                raise ValueError("Service tax factual premise changed; review required")
        if (
            service_tax["event_period"] != "2026-08"
            or service_tax["known_on"] < data["authored_on"]
        ):
            raise ValueError("Current service tax period/availability invalid")
    privacy = data["privacy"]
    if (
        sum(r["jurisdiction"] == "CA" for r in tables["people"])
        != privacy["california_employee_records"]
    ):
        raise ValueError("California employee privacy population mismatch")
    if (
        len(tables["people"]) + len(tables["current_customers"])
        != privacy["performance"]["notice_delivery_count"]
    ):
        raise ValueError("Privacy notice population incomplete")
    if D(privacy["shi_2025_gross_revenue_usd"]) <= D(
        privacy["adjusted_ccpa_threshold_usd"]
    ) or not all(
        privacy[k]
        for k in [
            "for_profit",
            "does_business_california",
            "determines_processing_purposes",
            "collects_california_personal_information",
        ]
    ):
        raise ValueError("CCPA factual trigger changed; new decision required")
    if legacy_rows is not None:
        revenue = [
            r
            for r in legacy_rows
            if r["entity"] == "SHI"
            and r["book"] == "PRIMARY_USD"
            and r["entry_date"].startswith("2025")
            and r["account_type"] == "revenue"
        ]
        if len(revenue) != privacy["revenue_rows"] or -sum(
            D(r["signed_usd"]) for r in revenue
        ) != D(privacy["shi_2025_gross_revenue_usd"]):
            raise ValueError("Prior-year revenue screen does not reconcile")
    late = privacy["performance"]["requests"][0]
    days = (date.fromisoformat(late["responded_on"]) - date.fromisoformat(late["received_on"])).days
    if days != 50 or late["state"] != "LATE_CORRECTED" or late["extension_notified"]:
        raise ValueError("Late request failure erased")
    return {
        "population_counts": counts,
        "activity_boundaries": 8,
        "contract_units": dict(Counter(r["unit"] for r in tables["current_contracts"])),
        "ccpa_shi": "APPLICABLE",
        "privacy_request_failures": 1,
        "prior_revenue_reperformed": legacy_rows is not None,
        "scope": "CURRENT_SOURCE_JOINS_AND_AUTHORED_FACTUAL_SCREENS_NOT_UNIVERSAL_COMPLIANCE",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--reperform-revenue", action="store_true")
    args = parser.parse_args()
    program = (
        "from enterprise.operations.completed_period import build; import json; "
        'print(json.dumps(build()["tables"]))'
    )
    tables = json.loads(
        subprocess.run(
            [sys.executable, "-c", program],
            cwd=args.repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    legacy = None
    if args.reperform_revenue:
        program = (
            "from industrial.planning.legacy_adapter import legacy_snapshot; import json; "
            'print(json.dumps(legacy_snapshot()["rows"]))'
        )
        legacy = json.loads(
            subprocess.run(
                [sys.executable, "-c", program],
                cwd=args.repository,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        )
    print(
        json.dumps(
            validate(json.loads(SOURCE.read_text()), tables, args.repository, legacy), indent=2
        )
    )


if __name__ == "__main__":
    main()
