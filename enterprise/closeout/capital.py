"""Ownership-preserving request preparation; never manufactures a participation basis."""

from decimal import ROUND_DOWN
from decimal import Decimal as D


def proportional_request(total, holders):
    """Largest remainder cents, holder-ID tie break; requires separately established rights.

    A request does not create a commitment, receipt, issuance or compulsory call.
    All holders use the same verified participation basis; economic/voting rights
    are carried through, never recalculated from dollars contributed.
    """
    total = D(total)
    if total < 0 or total != total.quantize(D(".01")) or not holders:
        raise ValueError("Nonnegative cash-facing cents and complete holder population required")
    if len({h["holder_id"] for h in holders}) != len(holders):
        raise ValueError("Duplicate holder")
    if len({h["participation_basis_source"] for h in holders}) != 1:
        raise ValueError("Mixed participation bases")
    if any(
        not h["participation_basis_source"] or h["basis_state"] != "ESTABLISHED" for h in holders
    ):
        raise ValueError("Unestablished participation rights")
    shares = {h["holder_id"]: D(h["participation_share"]) for h in holders}
    if any(v < 0 for v in shares.values()) or sum(shares.values()) != 1:
        raise ValueError("Complete shares must sum exactly to one")
    raw = {k: total * v for k, v in shares.items()}
    cents = {k: v.quantize(D(".01"), rounding=ROUND_DOWN) for k, v in raw.items()}
    remainder = int((total - sum(cents.values())) * 100)
    order = sorted(raw, key=lambda k: (-(raw[k] - cents[k]), k))
    for k in order[:remainder]:
        cents[k] += D(".01")
    return [
        dict(
            h,
            requested_usd=str(cents[h["holder_id"]]),
            commitment_usd=None,
            received_usd="0.00",
            interests_issued="0",
            event_state="PREPARED_VOLUNTARY_REQUEST",
            rights_after=h["rights_before"],
        )
        for h in sorted(holders, key=lambda h: h["holder_id"])
    ]
