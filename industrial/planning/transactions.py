"""Linked public synthetic procurement and forecast-event evidence.

Procurement rows are quantity/rate inputs to the forward ledger. Other generated
vouchers reconstruct explicitly modeled journal events; they are not independent
external evidence. No network, real vendor, bank, worker or payment endpoint is used.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "industrial/planning/source/transaction_policy.json"
OLD_FINANCE = ROOT / "industrial/source/finance.json"
OUT = ROOT / "industrial/generated/planning/transactions"
D = Decimal
META = {
    "fact_state": "FORECAST",
    "record_origin": "PUBLIC_SYNTHETIC_PLANNING_MODEL",
    "available_at": "2026-09-06T00:00:00-07:00",
}


def money(value):
    return int(D(str(value)).quantize(D("1"), rounding=ROUND_HALF_UP))


def split_money(total, weights):
    """Allocate signed whole dollars using largest remainders, preserving totals."""
    if not weights or any(D(str(w)) < 0 for w in weights) or sum(map(D, map(str, weights))) <= 0:
        raise ValueError("nonnegative weights with positive sum are required")
    if total < 0:
        return [-v for v in split_money(-total, weights)]
    exact = [D(total) * D(str(w)) / sum(D(str(v)) for v in weights) for w in weights]
    result = [int(v) for v in exact]
    for i in sorted(range(len(weights)), key=lambda i: (-(exact[i] - result[i]), i))[
        : total - sum(result)
    ]:
        result[i] += 1
    return result


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, default=str) + "\n").encode()


def write_csv(path, rows):
    columns = list(dict.fromkeys(k for row in rows for k in row))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(
            {
                k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v
                for k, v in row.items()
            }
            for row in rows
        )


def policy_source(source=None):
    value = json.loads(POLICY.read_text()) if source is None else source
    if value["vendor_payment_days"] < 0 or value["bank_clearing_days"] < 0:
        raise ValueError("payment and clearing intervals must be nonnegative")
    categories = value["expense_categories"]
    if len({c["id"] for c in categories}) != len(categories):
        raise ValueError("duplicate procurement category")
    if any(not D("0") <= D(c["variable_fraction"]) <= D("1") for c in categories):
        raise ValueError("variable shares must be within zero and one")
    return value


def procurement_costs(operating_rows, source=None):
    """Return five segment totals per scenario-month, each with its item support.

    Rates start from disclosed 2025 expense-envelope calibration. Variable
    quantities follow physical operations; fixed service subscriptions continue
    during disruption. Salaries, expansion capex and incremental emergency/
    subcontractor costs are excluded here so the forecast books them once.
    """
    policy = policy_source(source)
    history = json.loads(OLD_FINANCE.read_text())
    payroll = defaultdict(int)
    for worker in history["employees"]:
        payroll[worker["segment"]] += worker["annual_salary_usd"] + money(
            D(worker["annual_salary_usd"]) * worker["annual_employer_burden_pct"] / 100
        )
    seen = set()
    results = []
    for row in sorted(operating_rows, key=lambda r: (r["scenario"], r["year"], r["month"])):
        key = row["scenario"], int(row["year"]), int(row["month"])
        if key in seen:
            raise ValueError("duplicate operating scenario-month")
        seen.add(key)
        scenario, year, month = key
        if not 2027 <= year <= 2031 or not 1 <= month <= 12:
            raise ValueError("procurement is scoped to prospective 2027–2031 months")
        index = D(str(row["assumptions"]["cash_cost_index"]))
        if index < 0:
            raise ValueError("negative cost index")
        for segment, basis in policy["segment_activity_bases"].items():
            envelope = history["segment_baseline"][segment]
            annual = envelope["opex"] - envelope["shared_allocation"] - payroll[segment]
            if annual < 0 or basis["annual_units_2025"] <= 0:
                raise ValueError("invalid calibrated cost or activity basis")
            weights = basis["weights"]
            if len(weights) != len(policy["expense_categories"]):
                raise ValueError("cost category weights do not match catalog")
            amounts = split_money(annual, weights)
            factor = (
                D("1")
                if segment == "ARU"
                else D(str(row["segments"][segment]["cost_volume_factor"]))
            )
            if factor < 0:
                raise ValueError("negative cost activity")
            seasonal_share = (
                D(1) / 12
                if segment == "ARU"
                else D(history["monthly_weights_2025"][month - 1])
                / sum(history["monthly_weights_2025"])
            )
            quantity = D(basis["annual_units_2025"]) * seasonal_share * factor
            items = []
            for category, annual_cost in zip(policy["expense_categories"], amounts, strict=True):
                variable = D(category["variable_fraction"])
                rate = D(annual_cost) * variable / D(basis["annual_units_2025"])
                variable_cost = money(quantity * rate * index)
                fixed_cost = split_money(money(D(annual_cost) * (1 - variable) * index), [1] * 12)[
                    month - 1
                ]
                item_id = f"PROC-{scenario}-{year}{month:02}-{segment}-{category['id']}"
                invoice_date = date(year, month, min(24, calendar.monthrange(year, month)[1]))
                items.append(
                    {
                        "item_id": item_id,
                        "source_id": item_id,
                        "scenario": scenario,
                        "year": year,
                        "month": month,
                        "segment": segment,
                        "category": category["id"],
                        "description": category["name"],
                        "quantity": str(quantity),
                        "unit": basis["unit"],
                        "calibrated_unit_rate_usd": str(rate),
                        "cost_index": str(index),
                        "variable_cost_usd": variable_cost,
                        "fixed_service_cost_usd": fixed_cost,
                        "amount_usd": variable_cost + fixed_cost,
                        "vendor_id": f"SYN-V-{policy['seed']}-{segment}-{category['id']}",
                        "purchase_order_id": f"PO-{item_id}",
                        "receipt_id": f"RCV-{item_id}",
                        "invoice_id": f"INV-{item_id}",
                        "work_order_id": f"WO-{item_id}" if category["work_order"] else "",
                        "invoice_date": invoice_date.isoformat(),
                        "due_date": (
                            invoice_date + timedelta(days=policy["vendor_payment_days"])
                        ).isoformat(),
                        "evidence_role": "INPUT_TO_FORECAST_PURCHASE_COST",
                        "rate_state": "CALIBRATED_SYNTHETIC_RATE_NOT_SUPPLIER_QUOTE",
                        **META,
                    }
                )
            results.append(
                {
                    "scenario": scenario,
                    "year": year,
                    "month": month,
                    "segment": segment,
                    "external_cost_usd": sum(i["amount_usd"] for i in items),
                    "items": items,
                }
            )
    return results


def procurement_documents(costs, source=None):
    policy = policy_source(source)
    tables = {
        name: []
        for name in ("vendors", "purchase_orders", "receipts", "supplier_invoices", "work_orders")
    }
    vendors = {}
    for group in costs:
        for item in group["items"]:
            invoice_day = date.fromisoformat(item["invoice_date"])
            common = {
                k: item[k]
                for k in ("scenario", "year", "month", "segment", "source_id", "vendor_id")
            }
            common.update(META)
            vendors[item["vendor_id"]] = {
                "vendor_id": item["vendor_id"],
                "name": f"Synthetic {item['segment']} {item['category']} supplier",
                "fictional": True,
                "evidence_role": "MODELED_COUNTERPARTY",
                **META,
            }
            tables["purchase_orders"].append(
                {
                    "purchase_order_id": item["purchase_order_id"],
                    **common,
                    "ordered_on": (
                        invoice_day - timedelta(days=policy["purchase_lead_days"])
                    ).isoformat(),
                    "description": item["description"],
                    "quantity": item["quantity"],
                    "unit": item["unit"],
                    "amount_usd": item["amount_usd"],
                    "rate_state": item["rate_state"],
                }
            )
            tables["receipts"].append(
                {
                    "receipt_id": item["receipt_id"],
                    "purchase_order_id": item["purchase_order_id"],
                    **common,
                    "received_on": invoice_day.isoformat(),
                    "quantity": item["quantity"],
                    "unit": item["unit"],
                    "accepted_amount_usd": item["amount_usd"],
                    "receipt_kind": "SERVICE_ACCEPTANCE"
                    if item["category"] != "MAT"
                    else "MATERIAL_CONSUMPTION_RECEIPT",
                }
            )
            tables["supplier_invoices"].append(
                {
                    **item,
                    **common,
                    "three_way_match_state": "MODELED_QUANTITY_AND_AMOUNT_MATCH",
                    "payment_state": "SETTLEMENT_LINKED_SEPARATELY_TO_FORECAST_LEDGER",
                }
            )
            if item["work_order_id"]:
                tables["work_orders"].append(
                    {
                        "work_order_id": item["work_order_id"],
                        **common,
                        "purchase_order_id": item["purchase_order_id"],
                        "receipt_id": item["receipt_id"],
                        "invoice_id": item["invoice_id"],
                        "asset_scope": f"{item['segment']}_EXISTING_EQUIPMENT",
                        "scheduled_date": invoice_day.isoformat(),
                        "planned_service_quantity": item["quantity"],
                        "expense_usd": item["amount_usd"],
                        "status": "FORECAST_SERVICE_NOT_COMPLETED_INSPECTION",
                    }
                )
    tables["vendors"] = list(vendors.values())
    return tables


def validate_procurement(tables):
    orders = {r["purchase_order_id"]: r for r in tables["purchase_orders"]}
    receipts = {r["receipt_id"]: r for r in tables["receipts"]}
    if len(orders) != len(tables["purchase_orders"]) or len(receipts) != len(tables["receipts"]):
        raise ValueError("duplicate procurement identifier")
    count = 0
    for invoice in tables["supplier_invoices"]:
        po = orders[invoice["purchase_order_id"]]
        receipt = receipts[invoice["receipt_id"]]
        if (
            invoice["amount_usd"] != po["amount_usd"]
            or invoice["amount_usd"] != receipt["accepted_amount_usd"]
        ):
            raise ValueError("invoice/PO/receipt amount mismatch")
        if invoice["quantity"] != po["quantity"] or invoice["quantity"] != receipt["quantity"]:
            raise ValueError("invoice/PO/receipt physical quantity mismatch")
        for record in (po, receipt):
            if any(record[k] != invoice[k] for k in ("scenario", "year", "month", "vendor_id")):
                raise ValueError("cross-scenario or counterparty procurement link")
        if (
            po["ordered_on"] > receipt["received_on"]
            or receipt["received_on"] > invoice["due_date"]
        ):
            raise ValueError("procurement timing contradiction")
        count += 1
    return count


def journal_evidence(journal_rows, source=None):
    """Reconstruct posting documents and independently timed cash settlement.

    The treasury scope follows the source ledger; a group cash scope is not
    misrepresented as an independently reconstructed legal-bank account.
    Clearing happens after the modeled posting date, creating real reconciling
    timing items rather than forcing bank and book closing cash to be identical.
    """
    policy = policy_source(source)
    journals = defaultdict(list)
    for original in journal_rows:
        row = dict(original)
        for field in ("year", "month", "debit_usd", "credit_usd", "signed_usd"):
            row[field] = int(row[field])
        if row["debit_usd"] - row["credit_usd"] != row["signed_usd"]:
            raise ValueError("journal debit/credit sign mismatch")
        key = row["scenario"], row["entity"], row["journal_id"]
        journals[key].append(row)
    events, cash, invoices, payroll, lineage = [], [], [], [], []
    initial = defaultdict(int)
    monthly_movements = defaultdict(int)
    scopes = set()
    first_year = min((int(r["year"]) for r in journal_rows), default=2027)
    last_year = max((int(r["year"]) for r in journal_rows), default=2031)
    for (scenario, entity, journal_id), rows in sorted(journals.items()):
        if sum(r["signed_usd"] for r in rows):
            raise ValueError("unbalanced source journal")
        if len({(r["year"], r["month"]) for r in rows}) != 1:
            raise ValueError("journal crosses accounting periods")
        first = rows[0]
        year, month = first["year"], first["month"]
        source_id = first.get("source_id", journal_id)
        event_id = f"EV-{scenario}-{journal_id}"
        common = {
            "scenario": scenario,
            "entity": entity,
            "year": year,
            "month": month,
            "journal_id": journal_id,
            "event_id": event_id,
            "source_id": source_id,
            **META,
        }
        scopes.add((scenario, entity))
        events.append(
            {
                **common,
                "description": first.get("description", ""),
                "source_type": first.get("source_type", "FORECAST_LEDGER_EVENT"),
                "counterparty": first.get("counterparty", ""),
                "total_debits_usd": sum(r["debit_usd"] for r in rows),
                "total_credits_usd": sum(r["credit_usd"] for r in rows),
                "evidence_role": "RECONSTRUCTED_FROM_FORECAST_JOURNAL",
            }
        )
        for line in rows:
            lineage.append(
                {
                    **common,
                    "account": str(line["account"]),
                    "signed_usd": line["signed_usd"],
                    "support_id": line.get("source_id", source_id),
                    "support_role": "INPUT_PROCUREMENT_ITEM"
                    if str(line.get("source_id", "")).startswith("PROC-")
                    else "DECLARED_FORECAST_EVENT",
                    "input_path": "industrial/planning/source/transaction_policy.json"
                    if str(line.get("source_id", "")).startswith("PROC-")
                    else "industrial/planning/source/forecast.json",
                }
            )
        movement = sum(r["signed_usd"] for r in rows if str(r["account"]) == "1000")
        if month == 0:
            if year == first_year:
                initial[(scenario, entity)] += movement
            continue
        if not 1 <= month <= 12:
            raise ValueError("invalid posting month")
        posting_date = date(year, month, calendar.monthrange(year, month)[1])
        if movement:
            clearing_date = posting_date + timedelta(days=policy["bank_clearing_days"])
            cash.append(
                {
                    **common,
                    "payment_id": f"PAY-{scenario}-{journal_id}",
                    "posting_date": posting_date.isoformat(),
                    "clearing_date": clearing_date.isoformat(),
                    "bank_reference": "SIMBANK-"
                    + hashlib.sha256(event_id.encode()).hexdigest()[:18],
                    "signed_cash_usd": movement,
                    "cash_flow": next(
                        (r.get("cash_flow", "") for r in rows if str(r["account"]) == "1000"), ""
                    ),
                    "treasury_scope": entity,
                    "evidence_role": "MODELED_BANK_CLEARING_OF_FORECAST_PAYMENT",
                }
            )
            monthly_movements[(scenario, entity, year, month)] += movement
        revenue_lines = [
            r for r in rows if str(r["account"]) in {"4000", "4100"} and r["signed_usd"] < 0
        ]
        for index, line in enumerate(revenue_lines, 1):
            invoice_id = f"SALE-{scenario}-{journal_id}-{index}"
            invoices.append(
                {
                    **common,
                    "invoice_id": invoice_id,
                    "counterparty": line.get("counterparty", first.get("counterparty", "")),
                    "amount_usd": -line["signed_usd"],
                    "invoice_date": posting_date.isoformat(),
                    "revenue_account": str(line["account"]),
                    "source_contract_or_service": line.get("source_id", source_id),
                    "evidence_role": "RECONSTRUCTED_SALES_INVOICE_FROM_FORECAST_RECOGNITION",
                }
            )
        wages = sum(r["signed_usd"] for r in rows if str(r["account"]) == "5000")
        if wages > 0:
            payroll.append(
                {
                    **common,
                    "payroll_batch_id": f"WAGE-{scenario}-{journal_id}",
                    "segment": first.get("segment", entity),
                    "gross_employer_cost_usd": wages,
                    "cash_payment_usd": max(-movement, 0),
                    "evidence_role": "FORECAST_PAYROLL_BATCH_WITH_EMPLOYEE_CENSUS_SUPPORT",
                    "employee_source": "industrial/source/finance.json",
                }
            )
    reconciliations = []
    for scenario, entity in sorted(scopes):
        scoped = [r for r in cash if r["scenario"] == scenario and r["entity"] == entity]
        book = initial[(scenario, entity)]
        previous_bank = book
        for year in range(first_year, last_year + 1):
            for month in range(1, 13):
                cutoff = date(year, month, calendar.monthrange(year, month)[1]).isoformat()
                month_start = date(year, month, 1).isoformat()
                book += monthly_movements[(scenario, entity, year, month)]
                bank = initial[(scenario, entity)] + sum(
                    r["signed_cash_usd"] for r in scoped if r["clearing_date"] <= cutoff
                )
                uncleared = [r for r in scoped if r["posting_date"] <= cutoff < r["clearing_date"]]
                deposits = sum(max(r["signed_cash_usd"], 0) for r in uncleared)
                payments = -sum(min(r["signed_cash_usd"], 0) for r in uncleared)
                receipts = sum(
                    max(r["signed_cash_usd"], 0)
                    for r in scoped
                    if month_start <= r["clearing_date"] <= cutoff
                )
                withdrawals = -sum(
                    min(r["signed_cash_usd"], 0)
                    for r in scoped
                    if month_start <= r["clearing_date"] <= cutoff
                )
                if (
                    previous_bank + receipts - withdrawals != bank
                    or bank + deposits - payments != book
                ):
                    raise ValueError("bank/book reconciliation failed")
                reconciliations.append(
                    {
                        "scenario": scenario,
                        "entity": entity,
                        "year": year,
                        "month": month,
                        "opening_bank_cash_usd": previous_bank,
                        "cleared_receipts_usd": receipts,
                        "cleared_payments_usd": withdrawals,
                        "closing_bank_cash_usd": bank,
                        "deposits_in_transit_usd": deposits,
                        "outstanding_payments_usd": payments,
                        "adjusted_bank_cash_usd": bank + deposits - payments,
                        "ledger_cash_usd": book,
                        "difference_usd": bank + deposits - payments - book,
                        "treasury_scope": entity,
                        "evidence_role": "SYNTHETIC_CLEARING_TIMING_RECONCILIATION",
                        **META,
                    }
                )
                previous_bank = bank
    return {
        "ledger_events": events,
        "sales_invoices": invoices,
        "payroll_batches": payroll,
        "bank_transactions": cash,
        "bank_reconciliations": reconciliations,
        "document_journal_lineage": lineage,
    }


def attach_procurement_postings(tables, journal_rows):
    expenses = defaultdict(int)
    payments = defaultdict(int)
    for row in journal_rows:
        ident = row.get("source_id", "")
        if str(row["account"]) == "5100":
            expenses[(row["scenario"], ident)] += int(row["signed_usd"])
        if str(row["account"]) == "1000":
            payments[(row["scenario"], ident)] -= int(row["signed_usd"])
    matched = 0
    for invoice in tables["supplier_invoices"]:
        key = invoice["scenario"], invoice["source_id"]
        if key not in expenses:
            raise ValueError(f"procurement invoice not posted to forecast: {key}")
        if expenses[key] != invoice["amount_usd"]:
            raise ValueError(f"procurement/forecast expense mismatch: {key}")
        invoice["ledger_expense_usd"] = expenses[key]
        invoice["ledger_cash_settlement_usd"] = max(payments.get(key, 0), 0)
        invoice["unpaid_at_forecast_end_usd"] = (
            invoice["amount_usd"] - invoice["ledger_cash_settlement_usd"]
        )
        if invoice["unpaid_at_forecast_end_usd"] < 0:
            raise ValueError("invoice overpayment")
        matched += 1
    return matched


def detailed_service_and_payroll(tables, operating_rows, journal_rows):
    """Allocate explicitly modeled activity and employer cost to source records.

    These are monthly manifest/role allocations, not observed car movements or
    payroll tax filings. Cash support follows settlement source IDs, including
    later payments; an expense recognition journal is not a payment voucher.
    """
    history = json.loads(OLD_FINANCE.read_text())
    policy = json.loads((ROOT / "industrial/planning/source/forecast.json").read_text())
    operations = {(r["scenario"], int(r["year"]), int(r["month"])): r for r in operating_rows}
    contracts = {r["contract_id"]: r for r in history["contracts"]}
    payments = defaultdict(int)
    for row in journal_rows:
        if str(row["account"]) == "1000":
            payments[(row["scenario"], row.get("source_id", ""))] -= int(row["signed_usd"])
    details = []
    for batch in tables["payroll_batches"]:
        segment = batch["segment"]
        workers = [dict(w) for w in history["employees"] if w["segment"] == segment]
        if not workers:
            raise ValueError("payroll batch lacks employee census support")
        weights = [
            D(w["annual_salary_usd"]) * (1 + D(str(w["annual_employer_burden_pct"])) / 100)
            for w in workers
        ]
        paid = max(payments[(batch["scenario"], batch["source_id"])], 0)
        if paid > batch["gross_employer_cost_usd"]:
            raise ValueError("payroll settlement exceeds accrued employer cost")
        op = operations[(batch["scenario"], batch["year"], batch["month"])]
        fte = (
            policy["payroll"]["corporate_fte"]
            if segment == "ARU"
            else op["segments"][segment]["fte"]
        )
        base_fte = sum(D(str(w["fte"])) for w in workers)
        extra = D(str(fte)) - base_fte
        capacities = [D(str(w["fte"])) for w in workers]
        role = policy_source()["incremental_staffing_roles"][segment]
        if extra > 0:
            weights.append(sum(weights) / base_fte * extra)
            capacities.append(extra)
            workers.append(
                {
                    "employee_id": f"PLAN-POSITIONS-{segment}",
                    "role": role,
                    "fte": 0,
                    "planned_pool": True,
                }
            )
        elif extra < 0:
            eligible = [i for i, w in enumerate(workers) if w["role"] == role]
            frontline = sum(capacities[i] for i in eligible)
            if frontline + extra < 0:
                raise ValueError("staffing reduction exceeds modeled frontline roles")
            for i in eligible:
                capacities[i] *= (frontline + extra) / frontline
                weights[i] *= capacities[i] / D(str(workers[i]["fte"]))
        gross = split_money(batch["gross_employer_cost_usd"], weights)
        cash = split_money(paid, weights)
        batch["cash_payment_usd"] = paid
        batch["unpaid_at_forecast_end_usd"] = batch["gross_employer_cost_usd"] - paid
        batch["planned_segment_fte"] = fte
        for worker, capacity, cost, settled in zip(workers, capacities, gross, cash, strict=True):
            details.append(
                {
                    k: batch[k]
                    for k in (
                        "scenario",
                        "entity",
                        "year",
                        "month",
                        "source_id",
                        "journal_id",
                        "payroll_batch_id",
                        "segment",
                    )
                }
                | {
                    "payroll_detail_id": f"{batch['payroll_batch_id']}-{worker['employee_id']}",
                    "census_employee_id": ""
                    if worker.get("planned_pool")
                    else worker["employee_id"],
                    "planned_position_pool_id": worker["employee_id"]
                    if worker.get("planned_pool")
                    else "",
                    "census_role": worker["role"],
                    "census_fte": worker["fte"],
                    "modeled_role_capacity_fte": str(capacity),
                    "employer_cost_usd": cost,
                    "allocated_settlement_usd": settled,
                    "evidence_role": "MODELED_CENSUS_ROLE_ALLOCATION_NOT_INDIVIDUAL_PAYSLIP",
                    **META,
                }
            )
        if sum(gross) != batch["gross_employer_cost_usd"] or sum(cash) != paid:
            raise ValueError("payroll detail allocation failed")
    tables["payroll_role_details"] = details
    groups = defaultdict(list)
    for invoice in tables["sales_invoices"]:
        ident = invoice["source_id"]
        prefix = f"SALE-{invoice['scenario']}-{invoice['year']}{invoice['month']:02}-"
        contract = contracts.get(ident.removeprefix(prefix)) if ident.startswith(prefix) else None
        if contract is not None:
            key = (invoice["scenario"], invoice["year"], invoice["month"], contract["segment"])
            groups[key].append((invoice, contract))
    manifests = []
    for (scenario, year, month, segment), items in sorted(groups.items()):
        served = D(str(operations[(scenario, year, month)]["segments"][segment]["served_units"]))
        # Railcars and dispatches stay integral; other units retain millesimal
        # precision with an explicit conservation check at that reporting scale.
        scale = 1 if segment in {"BST", "TRUCKING"} else 1000
        reported = money(served * scale)
        allocations = split_money(reported, [c["annual_units"] for _, c in items])
        for (invoice, contract), units in zip(items, allocations, strict=True):
            manifests.append(
                {
                    "service_manifest_id": f"MANIFEST-{invoice['source_id']}",
                    "scenario": scenario,
                    "year": year,
                    "month": month,
                    "segment": segment,
                    "invoice_id": invoice["invoice_id"],
                    "source_id": invoice["source_id"],
                    "journal_id": invoice["journal_id"],
                    "contract_id": contract["contract_id"],
                    "customer_id": contract["customer_id"],
                    "origin_destination": contract.get("origin_destination", ""),
                    "allocated_realized_units": str(D(units) / scale),
                    "unit": contract["unit"],
                    "segment_realized_units": str(served),
                    "revenue_usd": invoice["amount_usd"],
                    "allocation_basis": (
                        "Active invoiced contract annual physical units; largest remainders"
                    ),
                    "evidence_role": (
                        "FORECAST_MONTHLY_SERVICE_MANIFEST_NOT_OBSERVED_INDIVIDUAL_WAYBILL"
                    ),
                    **META,
                }
            )
        if sum(allocations) != reported:
            raise ValueError("service manifest volume allocation failed")
    tables["service_manifests"] = manifests


def build(output=OUT, operating_rows=None, forecast=None, source=None):
    if operating_rows is None:
        from industrial.planning.operating_model import calculate

        operating_rows = calculate()
    costs = procurement_costs(operating_rows, source)
    tables = procurement_documents(costs, source)
    checks = validate_procurement(tables)
    journal_rows = []
    if forecast is not None:
        if isinstance(forecast, (str, Path)):
            with (Path(forecast) / "journal.csv").open() as stream:
                journal_rows = list(csv.DictReader(stream))
        elif "tables" in forecast:
            journal_rows = forecast["tables"].get(
                "journal", forecast["tables"].get("journal.csv", [])
            )
        else:
            journal_rows = forecast.get("journal", forecast.get("journal_rows", []))
        if not journal_rows:
            raise ValueError("forecast supplied without journal rows")
        tables.update(journal_evidence(journal_rows, source))
        matched = attach_procurement_postings(tables, journal_rows)
        detailed_service_and_payroll(tables, operating_rows, journal_rows)
    else:
        matched = 0
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    tables["procurement_monthly_costs"] = [
        {k: v for k, v in r.items() if k != "items"} for r in costs
    ]
    for name, rows in tables.items():
        write_csv(output / f"{name}.csv", rows)
    report = {
        "status": "PASS",
        "procurement_matches": checks,
        "procurement_posting_matches": matched,
        "forecast_postings_included": bool(journal_rows),
        "table_counts": {name: len(rows) for name, rows in tables.items()},
        "cost_basis": (
            "Calibrated starting rates; physical activity and cost index drive future purchases."
        ),
        "evidence_boundary": policy_source(source)["evidence_boundary"],
    }
    (output / "summary.json").write_bytes(encoded(report))
    return {"summary": report, "tables": tables, "costs": costs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    print(json.dumps(build(args.output)["summary"], indent=2))


if __name__ == "__main__":
    main()
