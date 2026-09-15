"""Dated synthetic customer invoices and cash allocations inside source AR."""

from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP
from decimal import Decimal as D


def extend(source, tables):
    from .completed_period import money, stamp

    balances = tables["current_receivable_customers"]
    invoices, receipts, aging = [], [], []
    group_totals = defaultdict(D)
    for b in balances:
        group_totals[b["financial_group"]] += D(b["billed_usd"])
    older = {}
    selected = [b for b in balances if b["financial_group"] == "ARU_GROUP"]
    for bucket, amount in (("31_60", D("700000")), ("61_90", D("300000"))):
        used = D(0)
        for i, b in enumerate(selected):
            value = (
                (amount * D(b["billed_usd"]) / group_totals["ARU_GROUP"]).quantize(
                    D(".01"), rounding=ROUND_HALF_UP
                )
                if i < len(selected) - 1
                else amount - used
            )
            older[b["customer_id"], bucket] = value
            used += value
    for b in balances:
        customer = b["customer_id"]
        parent_id = b["balance_id"]
        allowance = D(b["closing_allowance_usd"])
        old31 = older.get((customer, "31_60"), D(0))
        old61 = older.get((customer, "61_90"), D(0))
        other_open = D(b["opening_net_usd"]) - old31 - old61
        if other_open < 0:
            raise ValueError("Historical invoice allocation exceeds source opening AR")
        to_collect = D(b["collected_usd"])
        linked = sorted(
            [r for r in tables["current_invoices"] if r["customer_id"] == customer],
            key=lambda r: r["invoice_id"],
        )
        # Existing issuer remains intact; group cash is centrally administered.
        historical_issuer = linked[0]["legal_entity"]
        specs = [
            (parent_id + "-OPEN-CURRENT", "2026-07-01", "2026-08-15", other_open, D(0), True),
            (parent_id + "-OPEN-31-60", "2026-05-15", "2026-07-15", old31, D(0), True),
            (parent_id + "-OPEN-61-90", "2026-04-15", "2026-06-15", old61, D(0), True),
            (parent_id + "-DISPUTE", "2026-04-01", "2026-05-15", allowance, allowance, True),
        ]
        specs += [
            (r["invoice_id"], r["issued_on"], "2026-09-30", D(r["principal_usd"]), D(0), False)
            for r in linked
        ]
        for invoice_id, issued, due, amount, reserve, opening in specs:
            if amount == 0:
                continue
            # Retain aged balances/dispute; collect the ordinary opening first.
            eligible = invoice_id.endswith("OPEN-CURRENT") or not opening
            paid = min(amount, to_collect) if eligible else D(0)
            to_collect -= paid
            closing = amount - paid
            issuer = (
                historical_issuer
                if opening
                else next(r["legal_entity"] for r in linked if r["invoice_id"] == invoice_id)
            )
            invoices.append(
                stamp(
                    source,
                    invoice_id=invoice_id,
                    customer_id=customer,
                    balance_id=parent_id,
                    legal_issuer=issuer,
                    financial_group=b["financial_group"],
                    issued_on=issued,
                    due_on=due,
                    amount_usd=money(amount),
                    opening_outstanding_usd=money(amount if opening else D(0)),
                    august_billed_usd=money(D(0) if opening else amount),
                    paid_august_usd=money(paid),
                    closing_gross_usd=money(closing),
                    closing_allowance_usd=money(reserve),
                    closing_net_usd=money(closing - reserve),
                    fact_origin=(
                        "New retrospective invoice dates/opening allocation; "
                        "August ID/issuer/principal retained from current contract source"
                    ),
                    performance_basis=(
                        "Opening source allocation; historical service acceptance "
                        "newly authored within existing source book"
                    )
                    if opening
                    else "Linked current_delivery_evidence",
                    status="FULLY_RESERVED_DISPUTE"
                    if reserve
                    else "PAID"
                    if not closing
                    else "PART_PAID"
                    if paid
                    else "UNPAID",
                    followup_due="2026-09-20"
                    if closing and date.fromisoformat(due) < date(2026, 8, 31)
                    else None,
                    independent_bank_confirmation=False,
                )
            )
            if paid:
                receipts.append(
                    stamp(
                        source,
                        receipt_id=invoice_id + "-RECEIPT-20260828",
                        invoice_id=invoice_id,
                        customer_id=customer,
                        balance_id=parent_id,
                        financial_group=b["financial_group"],
                        paid_on="2026-08-28",
                        amount_usd=money(paid),
                        cash_allocation_state="MODELED_CLEARED_SOURCE_COLLECTION",
                        statement_reference=f"SYN-{b['financial_group']}-TREASURY-202608-28",
                        independent_bank_confirmation=False,
                    )
                )
            dpd = max(0, (date(2026, 8, 31) - date.fromisoformat(due)).days)
            bucket = (
                "CURRENT_0_30_DAYS_PAST_DUE"
                if dpd <= 30
                else "31_60"
                if dpd <= 60
                else "61_90"
                if dpd <= 90
                else "OVER_90"
            )
            aging.append(
                stamp(
                    source,
                    aging_id=invoice_id + "-AGING",
                    invoice_id=invoice_id,
                    customer_id=customer,
                    financial_group=b["financial_group"],
                    as_of="2026-08-31",
                    days_past_due=dpd,
                    bucket=bucket,
                    closing_gross_usd=money(closing),
                    allowance_usd=money(reserve),
                    basis=(
                        "Explicit days past due, not invoice age. "
                        "Current includes not-due and0-30pastdue."
                    ),
                )
            )
        if to_collect:
            raise ValueError("Customer collection exceeds eligible invoice population")
        for r in linked:
            r["due_on"] = "2026-09-30"
            record = next(x for x in invoices if x["invoice_id"] == r["invoice_id"])
            cash = next(x for x in tables["current_receipts"] if x["invoice_id"] == r["invoice_id"])
            cash.update(
                cash_usd=record["paid_august_usd"],
                paid_on="2026-08-28" if D(record["paid_august_usd"]) else None,
                state="MODELED_UNPAID"
                if not D(record["paid_august_usd"])
                else "MODELED_ALLOCATED_SOURCE_COLLECTION",
            )
    tables.update(
        current_customer_invoice_aging=aging,
        current_customer_invoice_ledger=invoices,
        current_customer_cash_allocations=receipts,
    )
    validate(tables)


def validate(tables):
    by_balance = defaultdict(lambda: [D(0)] * 5)
    cash = defaultdict(D)
    invoice_by_id = {r["invoice_id"]: r for r in tables["current_customer_invoice_ledger"]}
    if len(invoice_by_id) != len(tables["current_customer_invoice_ledger"]):
        raise ValueError("Duplicate customer invoice")
    receipt_ids = [r["receipt_id"] for r in tables["current_customer_cash_allocations"]]
    if len(receipt_ids) != len(set(receipt_ids)):
        raise ValueError("Duplicate cash receipt")
    current = {r["invoice_id"]: r for r in tables["current_invoices"]}
    for invoice in invoice_by_id.values():
        if D(invoice["august_billed_usd"]):
            parent = current.get(invoice["invoice_id"])
            if (
                parent is None
                or parent["customer_id"] != invoice["customer_id"]
                or parent["legal_entity"] != invoice["legal_issuer"]
                or D(parent["principal_usd"]) != D(invoice["august_billed_usd"])
            ):
                raise ValueError("Invoice ledger differs from current contract invoice")
    for receipt in tables["current_customer_cash_allocations"]:
        invoice = invoice_by_id.get(receipt["invoice_id"])
        if (
            invoice is None
            or receipt["customer_id"] != invoice["customer_id"]
            or not invoice["issued_on"] <= receipt["paid_on"] <= "2026-08-31"
        ):
            raise ValueError("Cash allocation identity or chronology mismatch")
        cash[receipt["invoice_id"]] += D(receipt["amount_usd"])
    for invoice in invoice_by_id.values():
        values = [
            D(invoice[k])
            for k in (
                "opening_outstanding_usd",
                "august_billed_usd",
                "paid_august_usd",
                "closing_net_usd",
                "closing_allowance_usd",
            )
        ]
        if (
            values[0] + values[1] - values[2] != values[3] + values[4]
            or cash[invoice["invoice_id"]] != values[2]
        ):
            raise ValueError("Invoice cash/allowance rollforward mismatch")
        if invoice["due_on"] < invoice["issued_on"]:
            raise ValueError("Invoice due date precedes issue")
        by_balance[invoice["balance_id"]] = [
            a + b for a, b in zip(by_balance[invoice["balance_id"]], values, strict=True)
        ]
    expected_ids = {b["balance_id"] for b in tables["current_receivable_customers"]}
    if set(by_balance) != expected_ids:
        raise ValueError("Invoice balance population omitted")
    for b in tables["current_receivable_customers"]:
        expected = [
            D(b["opening_net_usd"]) + D(b["opening_allowance_usd"]),
            D(b["billed_usd"]),
            D(b["collected_usd"]),
            D(b["closing_net_usd"]),
            D(b["closing_allowance_usd"]),
        ]
        if by_balance[b["balance_id"]] != expected:
            raise ValueError("Dated invoices differ from customer source balance")
    aged = set()
    totals = defaultdict(D)
    for row in tables["current_customer_invoice_aging"]:
        invoice = invoice_by_id[row["invoice_id"]]
        days = max(0, (date(2026, 8, 31) - date.fromisoformat(invoice["due_on"])).days)
        expected_bucket = (
            "CURRENT_0_30_DAYS_PAST_DUE"
            if days <= 30
            else "31_60"
            if days <= 60
            else "61_90"
            if days <= 90
            else "OVER_90"
        )
        if (
            row["bucket"] != expected_bucket
            or row["invoice_id"] in aged
            or row["days_past_due"] != days
            or D(row["closing_gross_usd"]) != D(invoice["closing_gross_usd"])
        ):
            raise ValueError("Aging population/date/amount mismatch")
        aged.add(row["invoice_id"])
        if row["financial_group"] == "ARU_GROUP":
            totals[row["bucket"]] += D(row["closing_gross_usd"])
    if (
        aged != set(invoice_by_id)
        or totals["31_60"] != 700000
        or totals["61_90"] != 300000
        or totals["OVER_90"] != 80000
    ):
        raise ValueError("Aging population differs from retained older source buckets")
