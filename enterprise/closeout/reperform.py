"""Inspect independent exported populations; writes a compact retained evidence receipt."""

import argparse
import json
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path

from enterprise.closeout.finance import verify
from industrial.planning.enterprise import read_csv


def run(out):
    rows = read_csv(out / "enterprise/enterprise_journal.csv")
    predecessor = read_csv(out / "predecessor/enterprise_journal.csv")
    result = verify(rows)
    # All ARU/BST legal economics must equal the recomputed accepted predecessor.
    fields = ("scenario", "entity", "year", "month", "account", "signed_usd", "source_id")

    def protected(records):
        return sorted(tuple(r[k] for k in fields) for r in records if r["entity"] in {"ARU", "BST"})

    if protected(rows) != protected(predecessor):
        raise ValueError("ARU/BST protected legal population changed")
    result["protected_aru_bst_legal_legs"] = len(protected(rows))
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
