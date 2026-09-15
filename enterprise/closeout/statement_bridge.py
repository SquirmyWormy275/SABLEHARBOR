"""Source-identified exact signed bridge, including tax-driven funding consequences."""

from collections import defaultdict
from decimal import Decimal as D


def bridge(before, after):
    keys = ("scenario", "entity", "year", "month", "account", "unit", "source_id", "source_type")
    old = defaultdict(D)
    new = defaultdict(D)
    for rows, target in [(before["journal_rows"], old), (after["journal_rows"], new)]:
        for r in rows:
            target[tuple(str(r[k]) for k in keys)] += D(r["signed_usd"])
    result = []
    for k in sorted(set(old) | set(new)):
        delta = new[k] - old[k]
        if delta:
            result.append(
                dict(
                    zip(keys, k),
                    action="SOURCE_IDENTIFIED_SUCCESSOR_DELTA",
                    signed_usd=str(delta),
                    predecessor_usd=str(old[k]),
                    successor_usd=str(new[k]),
                )
            )
    reconstructed = dict(old)
    for r in result:
        k = tuple(r[x] for x in keys)
        reconstructed[k] = reconstructed.get(k, D(0)) + D(r["signed_usd"])
    if {k: v for k, v in reconstructed.items() if v} != {k: v for k, v in new.items() if v}:
        raise ValueError("Source-identified bridge does not reconstruct successor")
    return result
