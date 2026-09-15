"""Current working-capital populations inside retained source books."""

import json
from collections import defaultdict
from decimal import Decimal as D


def extend(source, tables):
    from industrial.planning.enterprise import load_anchor

    from .completed_period import money, read, stamp
    from .current_records import allocate

    journal = load_anchor()
    finance = read("industrial/source/finance.json")
    ratios = finance["legal_book_policy"]["bst_balance_allocation_pct"]
    grouped = defaultdict(list)
    for row in journal:
        grouped[row["entity"]].append(row)
    controls, customers, suppliers, inventory = [], [], [], []
    for group, rows in grouped.items():
        for account in ("1100", "1200", "2000"):
            opening = sum(
                D(r["signed_usd"]) for r in rows if r["account"] == account and int(r["month"]) <= 7
            )
            activity = [r for r in rows if r["account"] == account and int(r["month"]) == 8]
            debit = sum(max(D(r["signed_usd"]), D(0)) for r in activity)
            credit = sum(max(-D(r["signed_usd"]), D(0)) for r in activity)
            closing = opening + debit - credit
            control_id = f"SH-CURRENT-{group}-{account}-202608"
            controls.append(
                stamp(
                    source,
                    control_id=control_id,
                    financial_group=group,
                    account=account,
                    opening_signed_usd=money(opening),
                    debit_activity_usd=money(debit),
                    credit_activity_usd=money(credit),
                    closing_signed_usd=money(closing),
                    source_journal_ids=json.dumps(sorted({r["journal_id"] for r in activity})),
                    basis="Retained group journal; legal management allocation shown separately",
                )
            )
            if account == "1100":
                candidates = sorted(
                    {
                        r["customer_id"]
                        for r in tables["current_contracts"]
                        if r["legal_entity"]
                        in ({"ARU", "BST"} if group == "ARU_GROUP" else {"RWH"})
                    }
                )
                if not candidates:
                    raise ValueError("Receivable customer population missing")
                values = [allocate(v, len(candidates)) for v in (opening, debit, credit, closing)]
                for i, customer in enumerate(candidates):
                    # Collections bridge opening, billed and closing amounts.
                    op, bill, close = values[0][i], values[1][i], values[3][i]
                    collection = op + bill - close
                    allowance = D("80000") if customer == "ARU-C-025" else D(0)
                    customers.append(
                        stamp(
                            source,
                            balance_id=control_id + "-" + customer,
                            control_id=control_id,
                            financial_group=group,
                            customer_id=customer,
                            opening_net_usd=money(op),
                            billed_usd=money(bill),
                            collected_usd=money(collection),
                            closing_net_usd=money(close),
                            opening_allowance_usd=money(allowance),
                            closing_allowance_usd=money(allowance),
                            closing_gross_usd=money(close + allowance),
                            allowance_provision_usd="0.00",
                            allowance_writeoff_usd="0.00",
                            allocation_basis="New synthetic equal customer allocation; "
                            "not a change to contract issuer or an asserted invoice aging file",
                        )
                    )
            elif account == "2000":
                for i, name in enumerate(
                    ("Operating supplies", "Facilities and utilities", "Specialist services")
                ):
                    op, billed, paid, close = [
                        allocate(v, 3)[i] for v in (-opening, credit, debit, -closing)
                    ]
                    # Cent residual retained in the payment bridge.
                    paid = op + billed - close
                    suppliers.append(
                        stamp(
                            source,
                            balance_id=f"{control_id}-V{i + 1}",
                            control_id=control_id,
                            vendor_id=f"SYN-{group}-SUPPLIER-{i + 1:02d}",
                            vendor_name=name,
                            financial_group=group,
                            opening_payable_usd=money(op),
                            purchases_and_services_usd=money(billed),
                            payments_usd=money(paid),
                            closing_payable_usd=money(close),
                            basis="New synthetic supplier pool allocation; "
                            "unchanged balances/payment; no new terms or independent confirmation",
                        )
                    )
            elif group == "ARU_GROUP":
                for item in finance["working_capital_support"]["inventory_classes"]:
                    fraction = D(item["value_allocation_pct"]) / 100
                    unit_cost = D(str(item["average_unit_cost_usd"]))
                    inventory.append(
                        stamp(
                            source,
                            inventory_id=control_id + "-" + str(len(inventory) + 1),
                            control_id=control_id,
                            financial_group=group,
                            inventory_class=item["class"],
                            quantity_unit=item["unit"],
                            opening_quantity=str(opening * fraction / unit_cost),
                            received_quantity=str(debit * fraction / unit_cost),
                            issued_quantity=str(credit * fraction / unit_cost),
                            closing_quantity=str(closing * fraction / unit_cost),
                            unit_cost_usd=money(unit_cost),
                            closing_value_usd=money(closing * fraction),
                            basis=finance["working_capital_support"]["inventory_basis"],
                        )
                    )
    legal = []
    for row in controls:
        account = row["account"]
        key = {"1100": "receivables", "1200": "inventory", "2000": "payables"}[account]
        if row["financial_group"] == "ARU_GROUP":
            from industrial.tools.build_financials import usd

            bst = D(usd(D(row["closing_signed_usd"]) * D(ratios[key]) / 100))
            allocation = {"BST": bst, "ARU": D(row["closing_signed_usd"]) - bst}
        else:
            allocation = {"RWH": D(row["closing_signed_usd"])}
        for entity, value in allocation.items():
            legal.append(
                stamp(
                    source,
                    balance_id=f"SH-CURRENT-{entity}-{account}-202608",
                    control_id=row["control_id"],
                    legal_entity=entity,
                    account=account,
                    closing_signed_usd=money(value),
                    basis="Accepted legal-management balance allocation; customer/supplier "
                    "centralized pool remains separately identified",
                )
            )
    for entity in ("SHI", "PS"):
        for account in ("1100", "1200", "2000"):
            legal.append(
                stamp(
                    source,
                    balance_id=f"SH-CURRENT-{entity}-{account}-202608",
                    control_id="NO_BALANCE_IN_RETAINED_CURRENT_SOURCE",
                    legal_entity=entity,
                    account=account,
                    closing_signed_usd="0.00",
                    basis="Source cash-service model; no invented trade balance",
                )
            )
    current = read("enterprise/operations/source/current_company_2026_08.json")
    tables["current_core_asset_carrying_components"] = [
        stamp(
            source,
            asset_id=f"SH-CORE-ASSET-POOL-{i + 1:02d}",
            legal_entity="SHI",
            unit=row["unit"],
            asset_nature=row["asset_nature"],
            carrying_usd=row["carrying_usd"],
            basis=current["core_ppe_basis"],
        )
        for i, row in enumerate(current["core_ppe_carrying_components"])
    ]
    assets = []
    operations = read("industrial/source/operations.json")
    for population in (
        "facilities",
        "track_segments",
        "structures",
        "locomotives",
        "railcars",
        "road_equipment",
        "handling_equipment",
    ):
        for row in operations[population]:
            assets.append(
                stamp(
                    source,
                    asset_id=row["id"],
                    population=population,
                    source_path=f"industrial/source/operations.json#{population}/{row['id']}",
                    source_record=json.dumps(row, sort_keys=True),
                    source_period="2025_BASELINE_WITH_SOURCE_DATED_UPDATES",
                    active_at_cutoff="RETAIN_SOURCE_STATUS_NOT_AUTOMATIC_ACTIVATION",
                )
            )
    tables.update(
        current_balance_controls=controls,
        current_receivable_customers=customers,
        current_supplier_balances=suppliers,
        current_inventory_classes=inventory,
        current_legal_balance_bridges=legal,
        current_asset_source_population=assets,
    )
    validate(tables)


def validate(tables):
    from .completed_period import read

    controls = {r["control_id"]: r for r in tables["current_balance_controls"]}
    if len(controls) != 6:
        raise ValueError("Working capital control population incomplete")
    if sum(D(r["carrying_usd"]) for r in tables["current_core_asset_carrying_components"]) != D(
        "9000000"
    ):
        raise ValueError("Core asset carrying components differ from retained source")
    for table in (
        "current_balance_controls",
        "current_receivable_customers",
        "current_supplier_balances",
        "current_inventory_classes",
        "current_legal_balance_bridges",
    ):
        if any(r["effective_period"] != "2026-08" for r in tables[table]):
            raise ValueError("Current balance wrong effective period")
    for row in controls.values():
        if D(row["opening_signed_usd"]) + D(row["debit_activity_usd"]) - D(
            row["credit_activity_usd"]
        ) != D(row["closing_signed_usd"]):
            raise ValueError("Working capital rollforward mismatch")
    for table, fields in (
        (
            "current_receivable_customers",
            ("opening_net_usd", "billed_usd", "collected_usd", "closing_net_usd"),
        ),
        (
            "current_supplier_balances",
            (
                "opening_payable_usd",
                "purchases_and_services_usd",
                "payments_usd",
                "closing_payable_usd",
            ),
        ),
    ):
        sums = defaultdict(lambda: [D(0)] * 4)
        ids = set()
        for row in tables[table]:
            if row["balance_id"] in ids:
                raise ValueError("Duplicate balance population member")
            ids.add(row["balance_id"])
            values = [D(row[f]) for f in fields]
            if values[0] + values[1] - values[2] != values[3] or min(values) < 0:
                raise ValueError("Customer/supplier balance rollforward mismatch")
            if (
                table == "current_receivable_customers"
                and D(row["closing_gross_usd"]) - D(row["closing_allowance_usd"]) != values[3]
            ):
                raise ValueError("Receivable gross allowance net mismatch")
            sums[row["control_id"]] = [
                a + b for a, b in zip(sums[row["control_id"]], values, strict=True)
            ]
        account = "1100" if table == "current_receivable_customers" else "2000"
        if set(sums) != {k for k, r in controls.items() if r["account"] == account}:
            raise ValueError("Omitted customer or supplier population")
        for key, totals in sums.items():
            parent = controls[key]
            expected = [
                D(parent[f])
                for f in (
                    "opening_signed_usd",
                    "debit_activity_usd",
                    "credit_activity_usd",
                    "closing_signed_usd",
                )
            ]
            if table == "current_supplier_balances":
                expected = [-expected[0], expected[2], expected[1], -expected[3]]
            if totals != expected:
                raise ValueError("Customer/supplier population differs from source book")
    inv_sum = defaultdict(D)
    for row in tables["current_inventory_classes"]:
        q = [
            D(row[k])
            for k in (
                "opening_quantity",
                "received_quantity",
                "issued_quantity",
                "closing_quantity",
            )
        ]
        if abs(q[0] + q[1] - q[2] - q[3]) > D("0.000000000001"):
            raise ValueError("Inventory quantity rollforward mismatch")
        if abs(q[3] * D(row["unit_cost_usd"]) - D(row["closing_value_usd"])) > D("0.000001"):
            raise ValueError("Inventory quantity and valuation mismatch")
        inv_sum[row["control_id"]] += D(row["closing_value_usd"])
    if len(tables["current_inventory_classes"]) != 3 or any(
        value != D(controls[key]["closing_signed_usd"]) for key, value in inv_sum.items()
    ):
        raise ValueError("Inventory class population differs from source")
    source = read("industrial/source/operations.json")
    expected = {
        r["id"]
        for k in (
            "facilities",
            "track_segments",
            "structures",
            "locomotives",
            "railcars",
            "road_equipment",
            "handling_equipment",
        )
        for r in source[k]
    }
    actual = [r["asset_id"] for r in tables["current_asset_source_population"]]
    if set(actual) != expected or len(actual) != len(expected):
        raise ValueError("Asset population omitted or duplicated")


def verify_legal_balances(tables, legal_trial_balance_rows):
    selected = {
        (r["entity"], r["account"]): D(r["signed_usd"])
        for r in legal_trial_balance_rows
        if r["scenario"] == "base" and str(r["year"]) == "2026" and str(r["month"]) == "8"
    }
    for row in tables["current_legal_balance_bridges"]:
        if D(row["closing_signed_usd"]) != selected.get(
            (row["legal_entity"], row["account"]), D(0)
        ):
            raise ValueError("Current balance differs from independent legal trial balance")
    return {
        "legal_balance_rows": len(tables["current_legal_balance_bridges"]),
        "additional_journal_usd": "0.00",
    }
