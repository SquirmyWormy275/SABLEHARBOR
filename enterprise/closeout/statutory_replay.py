"""Implementation replay guard; independent workpaper totals are a separate check."""

from collections import Counter

from industrial.planning.enterprise import Books

from .statutory_posting import TYPES

FIELDS = ("scenario", "entity", "year", "month", "source_id", "account", "signed_usd", "cash_flow")


def population(rows):
    return Counter(
        tuple(str(r[k]) for k in FIELDS) for r in rows if r["source_id"].startswith("CO-STAT-")
    )


def compare(expected, actual):
    left, right = population(expected), population(actual)
    if left != right:
        missing = list((left - right).elements())[:3]
        unexpected = list((right - left).elements())[:3]
        raise ValueError(f"Statutory replay differs: missing={missing}; unexpected={unexpected}")
    return {
        "statutory_legs_replayed": sum(left.values()),
        "scope": "SOURCE_PROVIDER_IMPLEMENTATION_REPLAY; INDEPENDENT_WORKPAPER_RECONCILIATION_SEPARATE",
    }


def verify(posting, journal_rows):
    expected = []
    account_types = {r["account"]: r["account_type"] for r in journal_rows} | TYPES
    original_payments = posting.payment_rows
    posting.payment_rows = []
    try:
        for scenario in ("base", "downside", "expansion"):
            books = Books(
                scenario,
                {
                    "segment_mapping": {},
                    "knowledge_cutoff": "2026-09-22",
                    "created_on": "2026-09-22",
                },
                account_types,
            )
            posting.post_opening(books)
            for year in range(2026, 2032):
                for month in range(1, 13):
                    posting.post_month(books, year, month)
            expected.extend(books.rows)
    finally:
        posting.payment_rows = original_payments
    return compare(expected, journal_rows)
