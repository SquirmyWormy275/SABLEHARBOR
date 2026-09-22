"""Prospective owner-approved designation rights; no units, cash or appointments posted."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "enterprise/closeout/source/capital_designation_rights.json"
CAPITAL = ROOT / "enterprise/closeout/source/capital_register.json"
BOARD = ROOT / "docs/governance/structured/board_and_committees.json"


def build(
    holdings=None, *, as_of="2026-09-22", split_numerator=1, split_denominator=1, source=None
):
    policy = source if source is not None else json.loads(SOURCE.read_text())
    capital = json.loads(CAPITAL.read_text())
    board = json.loads(BOARD.read_text())
    original = {h["holder_id"]: h["units"] for h in capital["holders"]}
    consents = [r["holder_id"] for r in policy["synthetic_member_assents"]]
    if len(consents) != 5 or set(consents) != set(original):
        raise ValueError("All five distinct holder assents required")
    if any(type(x) is not int or x <= 0 for x in (split_numerator, split_denominator)):
        raise ValueError("Split ratio requires positive integers")
    ratio = Fraction(split_numerator, split_denominator)
    values = original.copy() if holdings is None else holdings
    if set(values) != set(original) or any(type(v) is not int or v < 0 for v in values.values()):
        raise ValueError("Complete nonnegative five-holder unit population required")
    if sum(values.values()) != 100000000 * ratio:
        raise ValueError("Holdings differ from declared split-adjusted unit population")
    if len(board["directors"]) != 9 or len({d["id"] for d in board["directors"]}) != 9:
        raise ValueError("Existing nine-member board population changed")
    effective = date.fromisoformat(as_of) >= date.fromisoformat(policy["effective_date"])
    rows = []
    expected = {"SH-HOLDER-HV": ("DIR-MERCER", 9250000), "SH-HOLDER-WR": ("DIR-VOSS", 7500000)}
    if len(policy["designations"]) != 2 or {d["holder_id"] for d in policy["designations"]} != set(
        expected
    ):
        raise ValueError("Designation population changed")
    for d in policy["designations"]:
        holder = d["holder_id"]
        if (d["director_id"], d["threshold_units"]) != expected[holder] or d[
            "original_units"
        ] != original[holder]:
            raise ValueError("Approved original-unit designation terms changed")
        threshold = Fraction(d["threshold_units"]) * ratio
        rows.append(
            {
                "holder_id": holder,
                "director_id": d["director_id"],
                "units": values[holder],
                "threshold_numerator": threshold.numerator,
                "threshold_denominator": threshold.denominator,
                "eligible": values[holder] >= threshold if effective else None,
                "state": "PROSPECTIVE_SCHEDULE_EFFECTIVE" if effective else "NOT_YET_EFFECTIVE",
                "automatic_appointment_or_removal": False,
            }
        )
    return {
        "record_id": policy["document_id"],
        "effective_date": policy["effective_date"],
        "as_of": as_of,
        "rights": rows,
        "synthetic_assents": policy["synthetic_member_assents"],
        "board_director_ids": [d["id"] for d in board["directors"]],
        "unit_changes": 0,
        "additional_cash_usd": 0,
        "real_execution_claimed": False,
        "source_hashes": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (SOURCE, CAPITAL, BOARD)
        },
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
