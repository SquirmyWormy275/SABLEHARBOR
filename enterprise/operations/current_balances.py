"""Current working-capital populations inside retained source books."""

import json
from collections import defaultdict
from decimal import ROUND_HALF_UP
from decimal import Decimal as D


def mine_cost_layers():
    from enterprise.closeout.rwh_book import current_inventory_bridge
    from industrial.planning.enterprise import load_anchor

    row = current_inventory_bridge(load_anchor())[7]
    result = {}
    for account, kind, cogs_key in (
        ("1200", "cash", "corrected_cash_cost_cogs_usd"),
        ("1210", "dda", "corrected_dda_cogs_usd"),
    ):
        opening = D(row[f"opening_{kind}_inventory_usd"])
        closing = D(row[f"corrected_{kind}_inventory_usd"])
        cogs = D(row[cogs_key])
        result[account] = dict(
            opening_signed_usd=format(opening, ".4f"),
            debit_activity_usd=format(closing - opening + cogs, ".4f"),
            credit_activity_usd=format(cogs, ".4f"),
            closing_signed_usd=format(closing, ".4f"),
        )
    return result


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
    mine_layers = mine_cost_layers()
    for group, rows in grouped.items():
        for account in (
            ("1100", "1200", "1210", "2000") if group == "RWH_PS" else ("1100", "1200", "2000")
        ):
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
            if group == "RWH_PS" and account in mine_layers:
                controls[-1].update(mine_layers[account])
                controls[-1]["basis"] = (
                    "Corrected mine book carrying source: enterprise/closeout/rwh_book.py; "
                    "cash-production and DD&A cost layers share one physical stock population. "
                    "Activity includes four-decimal carrying rollforward rounding."
                )
                controls[-1]["source_correction_id"] = "CO-RWH-BOOK-202608"
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
                billings = {
                    c: sum(
                        D(r["principal_usd"])
                        for r in tables["current_invoices"]
                        if r["customer_id"] == c
                    )
                    for c in candidates
                }
                if sum(billings.values()) != debit:
                    raise ValueError("Actual invoice customer billings differ from source AR")

                def weighted(total, candidates=candidates, billings=billings, debit=debit):
                    result = []
                    used = D(0)
                    for index, customer in enumerate(candidates):
                        value = (
                            (total * billings[customer] / debit).quantize(
                                D(".01"), rounding=ROUND_HALF_UP
                            )
                            if index < len(candidates) - 1
                            else total - used
                        )
                        result.append(value)
                        used += value
                    return result

                openings, closings = weighted(opening), weighted(closing)
                for i, customer in enumerate(candidates):
                    op, bill, close = openings[i], billings[customer], closings[i]
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
                            allocation_basis=(
                                "New balances weighted by actual August invoices; "
                                "dated invoice/remittance rows reconcile without new GL"
                            ),
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
        key = {"1100": "receivables", "1200": "inventory", "1210": "inventory", "2000": "payables"}[
            account
        ]
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
                    closing_signed_usd=format(value, ".4f")
                    if entity == "RWH" and account in mine_layers
                    else money(value),
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
    cohort = current["core_ppe_book_cohort"]
    total_cost = D(cohort["gross_cost_usd"])
    accumulated = (
        D(cohort["opening_accumulated_depreciation_2026_usd"])
        + D(cohort["monthly_2026_depreciation_usd"]) * cohort["elapsed_current_year_months"]
    )
    asset_components = []
    used = D(0)
    for i, row in enumerate(current["core_ppe_carrying_components"]):
        gross = D(row["gross_cost_usd"])
        depreciation = (
            (accumulated * gross / total_cost).quantize(D(".0001"), rounding=ROUND_HALF_UP)
            if i < len(current["core_ppe_carrying_components"]) - 1
            else accumulated - used
        )
        used += depreciation
        asset_components.append(
            stamp(
                source,
                asset_id=f"SH-CORE-ASSET-POOL-{i + 1:02d}",
                legal_entity="SHI",
                unit=row["unit"],
                asset_nature=row["asset_nature"],
                gross_cost_usd=money(gross),
                accumulated_depreciation_usd=format(depreciation, ".4f"),
                net_carrying_usd=format(gross - depreciation, ".4f"),
                cohort_id=cohort["cohort_id"],
                placed_in_service=cohort["placed_in_service"],
                cost_account=cohort["cost_account"],
                accumulated_depreciation_account=cohort["accumulated_depreciation_account"],
                basis=current["core_ppe_basis"],
            )
        )
    tables["current_core_asset_carrying_components"] = asset_components
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
    tables["current_mine_inventory_cost_layers"] = [
        stamp(
            source,
            cost_layer_id=f"RWH-CURRENT-INVENTORY-{account}-202608",
            control_id=f"SH-CURRENT-RWH_PS-{account}-202608",
            legal_entity="RWH",
            account=account,
            cost_layer="CASH_PRODUCTION_COST" if account == "1200" else "CAPITALIZED_DDA",
            physical_population="Same mine inventory; cost layer is not additional quantity",
            source_path="enterprise/closeout/rwh_book.py#current_inventory_bridge",
            **values,
        )
        for account, values in mine_layers.items()
    ]
    tables.update(
        current_balance_controls=controls,
        current_receivable_customers=customers,
        current_supplier_balances=suppliers,
        current_inventory_classes=inventory,
        current_legal_balance_bridges=legal,
        current_asset_source_population=assets,
    )
    from .invoice_settlement import extend as extend_invoices

    extend_invoices(source, tables)
    validate(tables)


def validate(tables):
    from .invoice_settlement import validate as validate_invoices

    validate_invoices(tables)
    from .completed_period import read

    controls = {r["control_id"]: r for r in tables["current_balance_controls"]}
    if len(controls) != 7 or len(tables["current_balance_controls"]) != 7:
        raise ValueError("Working capital control population incomplete")
    expected_layers = mine_cost_layers()
    layers = tables["current_mine_inventory_cost_layers"]
    if len(layers) != 2 or {r["account"] for r in layers} != set(expected_layers):
        raise ValueError("Mine inventory cost-layer population incomplete")
    for row in layers:
        if row["legal_entity"] != "RWH" or row["effective_period"] != "2026-08":
            raise ValueError("Mine inventory cost-layer scope mismatch")
        expected = expected_layers[row["account"]]
        control = controls[row["control_id"]]
        legal = [
            r
            for r in tables["current_legal_balance_bridges"]
            if r["legal_entity"] == "RWH" and r["account"] == row["account"]
        ]
        if len(legal) != 1 or legal[0]["closing_signed_usd"] != expected["closing_signed_usd"]:
            raise ValueError("Mine legal carrying differs from corrected source")
        if any(row[k] != v or control[k] != v for k, v in expected.items()):
            raise ValueError("Mine inventory carrying differs from corrected source")
    if sum(D(r["gross_cost_usd"]) for r in tables["current_core_asset_carrying_components"]) != D(
        "9000000"
    ):
        raise ValueError("Core asset gross components differ from retained source")
    for row in tables["current_core_asset_carrying_components"]:
        if D(row["gross_cost_usd"]) - D(row["accumulated_depreciation_usd"]) != D(
            row["net_carrying_usd"]
        ):
            raise ValueError("Core gross accumulated depreciation net bridge mismatch")
    if sum(
        D(r["accumulated_depreciation_usd"])
        for r in tables["current_core_asset_carrying_components"]
    ) != D("4714285.7139"):
        raise ValueError("Core accumulated depreciation differs from finance cohort")
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


def verify_core_asset_balances(tables, legal_trial_balance_rows):
    selected = {
        r["account"]: D(r["signed_usd"])
        for r in legal_trial_balance_rows
        if r["scenario"] == "base"
        and r["entity"] == "SHI"
        and str(r["year"]) == "2026"
        and str(r["month"]) == "8"
    }
    gross = sum(D(r["gross_cost_usd"]) for r in tables["current_core_asset_carrying_components"])
    accumulated = sum(
        D(r["accumulated_depreciation_usd"])
        for r in tables["current_core_asset_carrying_components"]
    )
    if selected.get("LEG_1500") != gross or selected.get("LEG_1590") != -accumulated:
        raise ValueError("Core PPE gross/net differs from corrected finance successor")
    return {
        "gross_usd": str(gross),
        "accumulated_depreciation_usd": str(accumulated),
        "net_usd": str(gross - accumulated),
        "additional_operations_journal_usd": "0.00",
    }
