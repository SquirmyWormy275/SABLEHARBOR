"""Inspect independent exported populations; writes a compact retained evidence receipt."""

import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal as D
from pathlib import Path

from enterprise.closeout.finance import verify
from industrial.planning.enterprise import read_csv


def compare_protected(rows, predecessor, reviewed_source_ids=()):
    """Exact semantic native-leg comparison, including acquisition and carryforwards."""

    def population(records):
        return Counter(
            (
                r["scenario"],
                r["entity"],
                int(r["year"]),
                int(r["month"]),
                r["account"],
                D(r["signed_usd"]),
                r["source_id"],
            )
            for r in records
            if r["entity"] in {"ARU", "BST"} and r["source_id"] not in reviewed_source_ids
        )

    actual, expected = population(rows), population(predecessor)
    if actual != expected:
        raise ValueError(
            f"ARU/BST protected legal population changed; added={list((actual - expected).items())[:4]}; removed={list((expected - actual).items())[:4]}"
        )
    return sum(actual.values())


def run(out):
    rows = read_csv(out / "enterprise/enterprise_journal.csv")
    predecessor = read_csv(out / "predecessor/enterprise_journal.csv")
    result = verify(rows)
    # Preserve original acquisition and operating legs; separately validate the
    # reviewed employer-levy addition, without granting a broad source-prefix bypass.
    from enterprise.closeout.retention_tax import SOURCE_IDS, RetentionTax

    levy = RetentionTax()
    additions = [r for r in rows if r["source_id"] in SOURCE_IDS.values()]
    expected_additions = []
    for scenario in ("base", "downside", "expansion"):
        for entity, amount in levy.totals.items():
            for account, signed in (("5000", amount), ("CO_PAYROLL_EMP_TAX_PAY", -amount)):
                expected_additions.append(
                    (scenario, entity, "2026", "7", account, signed, SOURCE_IDS[entity])
                )
    actual_additions = [
        (
            r["scenario"],
            r["entity"],
            r["year"],
            r["month"],
            r["account"],
            D(r["signed_usd"]),
            r["source_id"],
        )
        for r in additions
    ]
    if sorted(actual_additions) != sorted(expected_additions):
        raise ValueError("Retention levy additions differ from independently reconstructed awards")
    result["protected_aru_bst_legal_legs"] = compare_protected(
        rows, predecessor, SOURCE_IDS.values()
    )
    funding = defaultdict(D)
    for row in predecessor:
        if (row["scenario"], row["entity"], row["year"], row["account"], row["source_type"]) == (
            "base",
            "SHI",
            "2027",
            "1000",
            "MEMBER_EQUITY",
        ):
            funding[row["source_id"]] += D(row["signed_usd"])
    result["pre_runtime_base_2027_member_cash"] = {k: str(v) for k, v in funding.items()}
    result["pre_runtime_base_2027_total_usd"] = str(sum(funding.values()))
    if sum(funding.values()) != D("13325751.3907") or len(funding) != 7:
        raise ValueError("Inherited seven-source funding population changed; investigate")
    result["scope"] = (
        "Targeted lane evidence; not a full tax provision, accepted edition or bank confirmation"
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.output), indent=2))
