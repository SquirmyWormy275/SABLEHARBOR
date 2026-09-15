"""Complete bounded August commercial and payroll cost-component populations."""

from collections import defaultdict
from decimal import Decimal as D

CURRENT_SOURCE = "enterprise/operations/source/current_company_2026_08.json"
TAX_SCOPE_SOURCE = "enterprise/ccf/company_closeout/current_activity_successor.json"


def allocate(total, count):
    from .completed_period import cents

    each = cents(D(total) / count)
    return [each] * (count - 1) + [D(total) - each * (count - 1)]


def read_current_tax_contract():
    from .completed_period import read

    return read(CURRENT_SOURCE)["unemployment"]


def extend(source, tables):
    from .completed_period import cents, money, read, stamp

    current = read(CURRENT_SOURCE)
    pay = tables["payroll"]
    benefits = []
    unemployment = []
    byperson = {p["person_id"]: p for p in tables["people"]}
    for row in pay:
        person = byperson[row["person_id"]]
        ui = current["unemployment"]
        railroad = row["legal_entity"] == "BST"
        base = D(ui["state_annual_wage_bases"][person["jurisdiction"]])
        excess = D(row["opening_ytd_wages_usd"]) - base
        if not railroad and excess < 0:
            raise ValueError("August unemployment wage base not exhausted; explicit rate needed")
        ruia = (
            cents(D(ui["bst_ruia_monthly_base"]) * D(ui["bst_ruia_rate"]))
            if railroad and row["pay_date"].endswith("14")
            else D(0)
        )
        row["employer_ruia_usd"] = money(ruia)
        row["employer_known_taxes_usd"] = money(D(row["employer_known_taxes_usd"]) + ruia)
        remainder = D(row["employer_burden_usd"]) - D(row["employer_known_taxes_usd"])
        row["remaining_benefit_and_employer_obligations_usd"] = money(remainder)
        row["benefit_settlement_state"] = "MODELED_PAID_2026_08_31"
        unemployment.append(
            stamp(
                source,
                workpaper_id=row["pay_id"] + "-UI",
                pay_id=row["pay_id"],
                person_id=row["person_id"],
                legal_entity=row["legal_entity"],
                jurisdiction=person["jurisdiction"],
                state_annual_base_usd=money(base) if not railroad else None,
                opening_ytd_usd=row["opening_ytd_wages_usd"],
                state_incremental_taxable_wages_usd="0.00",
                futa_incremental_taxable_wages_usd="0.00",
                employer_ruia_usd=money(ruia),
                ruia_monthly_base_usd=ui["bst_ruia_monthly_base"] if railroad else None,
                rate_notice=ui["bst_rate_notice_id"]
                if railroad
                else "ANNUAL_RATE_NOT_NEEDED_FOR_ZERO_AUGUST_BASE",
                outcome="RUIA_ONLY_NOT_FUTA_OR_STATE_UI"
                if railroad
                else "ANNUAL_BASE_ALREADY_EXHAUSTED",
            )
        )
        tables["tax_liabilities"].append(
            stamp(
                source,
                liability_id=row["pay_id"] + "-employer_ruia",
                pay_id=row["pay_id"],
                legal_entity=row["legal_entity"],
                jurisdiction=person["jurisdiction"],
                tax="employer_ruia",
                amount_usd=money(ruia),
                remitted_usd=money(ruia),
                closing_liability_usd="0.00",
                remitted_on=row["pay_date"],
                remittance_id=row["pay_id"] + "-employer_ruia-REMIT",
                remittance_state="NEWLY_AUTHORED_SYNTHETIC_PAYMENT_NOT_AGENCY_ACKNOWLEDGEMENT",
            )
        )
        allocated = D(0)
        for index, component in enumerate(current["benefits"]["components"]):
            amount = (
                cents(remainder * D(component["fraction"])) if index < 2 else remainder - allocated
            )
            allocated += amount
            benefits.append(
                stamp(
                    source,
                    benefit_id=row["pay_id"] + "-" + component["kind"],
                    pay_id=row["pay_id"],
                    person_id=row["person_id"],
                    legal_entity=row["legal_entity"],
                    component=component["kind"],
                    provider_id=component["provider_id"],
                    invoice_id=f"SH-BEN-202608-{row['legal_entity']}-{component['provider_id']}",
                    cost_usd=money(amount),
                    paid_usd=money(amount),
                    closing_payable_usd="0.00",
                    paid_on=current["benefits"]["settled_on"],
                    evidence_state=current["benefits"]["record_state"],
                )
            )
    # Replace the subledger's payment legs; the retained source aggregate cash is not posted again.
    journal = []
    for row in pay:
        gross = D(row["gross_usd"])
        burden = D(row["employer_burden_usd"])
        known = D(row["employer_known_taxes_usd"])
        deductions = D(row["withholding_usd"])
        net = D(row["net_usd"])
        other = burden - known
        entries = [
            ("WAGES_EXPENSE", gross),
            ("EMPLOYER_COST_EXPENSE", burden),
            ("EMPLOYEE_WITHHOLDING_PAYABLE", -deductions),
            ("EMPLOYER_TAX_PAYABLE", -known),
            ("BENEFITS_AND_OTHER_EMPLOYER_PAYABLE", -other),
            ("CASH", -net),
            ("EMPLOYEE_WITHHOLDING_PAYABLE", deductions),
            ("EMPLOYER_TAX_PAYABLE", known),
            ("CASH_TAX_REMITTANCE", -(deductions + known)),
            ("BENEFITS_AND_OTHER_EMPLOYER_PAYABLE", other),
            ("CASH_BENEFIT_SETTLEMENT", -other),
        ]
        for account, value in entries:
            journal.append(
                stamp(
                    source,
                    journal_id=row["pay_id"],
                    source_id=row["pay_id"],
                    legal_entity=row["legal_entity"],
                    unit=row["unit"],
                    account=account,
                    signed_usd=money(value),
                    posting_state="SOURCE_COMPONENT_REPLACEMENT_NOT_ADDITIVE",
                )
            )
    tables["journal"] = journal
    tables["benefit_settlements"] = benefits
    tables["unemployment_workpapers"] = unemployment
    tables.update(commercial(source, current, tables))
    tables["current_book_cost_components"] = cost_components(source, current, tables)
    return current


def commercial(source, current, tables):
    from industrial.tools.build_financials import alloc, customer_schedules, usd

    from .completed_period import money, read, stamp

    customers = []
    contracts = []
    deliveries = []
    invoices = []
    receipts = []
    projects = []
    sites = []
    authorities = []
    evidence = []

    def add(cid, pid, entity, unit, amount, owner, deliverable, kind, asset, origin, paid=True):
        customers.append(
            stamp(
                source,
                customer_id=pid,
                name=f"Synthetic current counterparty {pid}",
                legal_entity=entity,
                unit=unit,
                source_origin=origin,
            )
        )
        contracts.append(
            stamp(
                source,
                contract_id=cid,
                customer_id=pid,
                legal_entity=entity,
                unit=unit,
                valid_from="2026-08-01",
                valid_to="2026-08-31",
                term_date_basis="August service schedule; not original contract term",
                kind=kind,
                monthly_fee_usd=money(amount),
                accountable_person_id=owner,
                deliverable=deliverable,
                asset_pool_id=asset,
                source_origin=origin,
            )
        )
        authorities.append(
            stamp(
                source,
                authority_id=cid + "-AUTH",
                contract_id=cid,
                legal_entity=entity,
                unit=unit,
                accountable_person_id=owner,
                reviewer_person_id="SH-EMP-ESS-0002",
                authorized_on="2026-08-01",
                scope="August ordinary service/materials schedule within retained source revenue",
                amount_usd=money(amount),
                new_material_rights=False,
                state="NEWLY_AUTHORED_SYNTHETIC_INTERNAL_AUTHORIZATION",
                source_origin=origin,
            )
        )
        did = cid + "-PERFORM-202608"
        iid = cid + "-INV-202608"
        deliveries.append(
            stamp(
                source,
                delivery_id=did,
                contract_id=cid,
                customer_id=pid,
                legal_entity=entity,
                unit=unit,
                performed_on="2026-08-28",
                reviewed_on="2026-08-31",
                preparer_person_id=owner,
                reviewer_role_id="CUSTOMER_ACCEPTANCE_" + pid,
                state="NEWLY_AUTHORED_SYNTHETIC_ACCEPTANCE"
                if paid
                else "BOOKED_SOURCE_WITH_CUSTODY_EVIDENCE_OPEN",
                evidence_id=did + "-EVIDENCE",
                deliverable=deliverable,
            )
        )
        evidence.append(
            stamp(
                source,
                evidence_id=did + "-EVIDENCE",
                delivery_id=did,
                contract_id=cid,
                legal_entity=entity,
                unit=unit,
                performed_on="2026-08-28",
                reviewed_on="2026-08-31",
                population_unit="ONE_MONTHLY_CONTRACT_DELIVERABLE",
                deliverable=deliverable,
                source_origin=origin,
                evidence_basis="Newly authored counterpart monthly acceptance for synthetic service"
                if paid
                else "Retained monthly accounting source; custody evidence separately gated",
                independent_external_confirmation=False,
            )
        )
        invoices.append(
            stamp(
                source,
                invoice_id=iid,
                contract_id=cid,
                delivery_id=did,
                customer_id=pid,
                legal_entity=entity,
                unit=unit,
                issued_on="2026-08-31",
                principal_usd=money(amount),
                tax_usd=None,
                invoice_tax_basis=(
                    "No sales-tax determination inferred; "
                    "current tax applicability register controls"
                ),
                authority_id=cid + "-AUTH",
                source_id=cid,
                posting_mode="DECOMPOSE_EXISTING_REVENUE_NOT_ADDITIVE",
            )
        )
        receipts.append(
            stamp(
                source,
                receipt_id=iid + "-RECEIPT",
                invoice_id=iid,
                legal_entity=entity,
                customer_id=pid,
                paid_on="2026-08-31" if paid else None,
                cash_usd=money(amount) if paid else None,
                state="NEWLY_AUTHORED_SYNTHETIC_CLEARING"
                if paid
                else "COLLECTION_SOURCE_NOT_ALLOCATED_BY_CONTRACT",
                independent_confirmation=False,
            )
        )

    siteindex = 0
    for group in current["commercial_groups"]:
        for number, value in enumerate(allocate(group["revenue_usd"], group["customers"]), 1):
            pid = f"SH-CURRENT-{group['unit'].upper()}-{number:03d}"
            cid = pid + "-CONTRACT-202608"
            add(
                cid,
                pid,
                "SHI",
                group["unit"],
                value,
                group["accountable_person"],
                group["deliverable"],
                group["contract_type"],
                group["asset_pool"],
                "NEWLY_AUTHORED_CURRENT_CUSTOMER_NOT_2027_IDENTITY",
            )
            # 104 distinct customer environments, not owned physical company sites.
            count = 2 if siteindex < 92 else 1
            for _n in range(count):
                siteindex += 1
                sites.append(
                    stamp(
                        source,
                        customer_site_id=f"SH-CURRENT-CUSTOMER-SITE-{siteindex:03d}",
                        customer_id=pid,
                        site_type="CUSTOMER_SERVICE_ENVIRONMENT",
                        company_owned=False,
                        physical_geography="NOT_ASSERTED_BY_SERVICE_ENVIRONMENT",
                    )
                )
    cradle = current["cradle"]
    add(
        cradle["project_id"],
        cradle["customer_id"],
        "SHI",
        "project-cradle",
        D(cradle["revenue_usd"]),
        cradle["accountable_person"],
        "Accepted bounded Stream17-derived product at downstream refiner",
        "PILOT_RECOVERY_PRODUCT",
        "BEDFORD",
        "NEWLY_AUTHORED_HOST_PILOT_WITH_EXISTING_CANON_BOUNDARIES",
    )
    for row in current["research_projects"]:
        projects.append(
            stamp(
                source,
                **row,
                unit="willow",
                legal_entity="SHI",
                revenue_usd="0.00",
                transfer_authorized=False,
                available_to_operating_owner=False,
            )
        )
    direct = sum(
        D(r["gross_usd"]) + D(r["employer_burden_usd"])
        for r in tables["payroll"]
        if r["person_id"] in cradle["direct_labor_person_ids"]
    )
    margin = (
        D(cradle["revenue_usd"])
        - direct
        - D(cradle["materials_and_processing_usd"])
        - D(cradle["bedford_and_freight_usd"])
        - D(cradle["host_share_usd"])
    )
    projects.append(
        stamp(
            source,
            project_id=cradle["project_id"],
            unit="project-cradle",
            legal_entity="SHI",
            owner=cradle["accountable_person"],
            host=cradle["host"],
            host_ownership="EXTERNAL",
            feed_tonnes=cradle["feed_tonnes"],
            accepted_product_kg=cradle["accepted_product_kg"],
            revenue_usd=cradle["revenue_usd"],
            direct_payroll_usd=money(direct),
            direct_margin_usd=money(margin),
            genealogy=cradle["genealogy"],
            source_origin="NEWLY_AUTHORED_PHYSICAL_AND_COMMERCIAL_INSTANCE",
        )
    )
    projects.append(
        stamp(source, **cradle["failure_project"], unit="project-cradle", legal_entity="SHI")
    )
    finance = read("industrial/source/finance.json")
    _, _, monthly = customer_schedules(finance)
    for row in monthly:
        if row["month"] != 8:
            continue
        amount = D(usd(D(row["revenue_usd"]) * D("1.02")))
        add(
            row["contract_id"],
            row["customer_id"],
            "BST" if row["segment"] == "BST" else "ARU",
            "american-resource-utility",
            amount,
            "P029",
            "August source contract quantity and reservation",
            row["commodity"],
            "INDUSTRIAL_REGISTER",
            "industrial/source/finance.json monthly_contracts x 2026 pricefactor1.02",
            paid=False,
        )
    mine = read("red_wash/source/core_operating_data.json")
    annual = [D(r["pounds"]) * D(r["price_usd_lb"]) for r in mine["contract_book_2026"]]
    target = D(alloc(mine["finance_2026"]["revenue_usd"], [1] * 12)[7])
    allocated = D(0)
    for index, row in enumerate(mine["contract_book_2026"]):
        value = (
            (target * annual[index] / sum(annual)).quantize(D(".01"))
            if index < 3
            else target - allocated
        )
        allocated += value
        add(
            row["contract_id"],
            row["contract_id"] + "-BUYER",
            "RWH",
            "pale-sun",
            value,
            "P021",
            "Retained monthly book revenue allocation; external shipment "
            "authority/acceptance remains independently gated",
            row["structure"],
            "RED_WASH_PRODUCTION",
            "Accepted contractbook; equal-month integrated finance source "
            "distinct from physical-production month",
            paid=False,
        )
    tax_scope = read(TAX_SCOPE_SOURCE)["august_core_transaction_tax"]
    tax_customers = {r["customer_id"]: r for r in tax_scope["customers"]}
    if len(tax_customers) != 58 or tax_scope["event_period"] != "2026-08":
        raise ValueError("Current tax applicability population or period changed")
    for invoice in invoices:
        tax = tax_customers.get(invoice["customer_id"])
        if tax is None:
            continue
        if (
            tax["contract_id"] != invoice["contract_id"]
            or D(tax["principal_usd"]) != D(invoice["principal_usd"])
            or tax["tangible_property_delivered"]
            or tax["august_service_use_jurisdiction"] != "US-CA"
            or tax["sales_tax_usd"] != "0.00"
        ):
            raise ValueError("Current transaction differs from scoped tax facts")
        invoice.update(
            tax_usd=tax["sales_tax_usd"],
            invoice_tax_basis=tax["reason"],
            tax_authority_id=tax_scope["id"],
            billing_jurisdiction=tax["billing_jurisdiction"],
            service_use_jurisdiction=tax["august_service_use_jurisdiction"],
            tax_effective_period=tax_scope["event_period"],
        )
    actual_names = {r["customer_id"]: r["legal_name"] for r in finance["customers"]}
    actual_names.update(
        {r["contract_id"] + "-BUYER": r["buyer"] for r in mine["contract_book_2026"]}
    )
    unique = {}
    for row in customers:
        row["name"] = actual_names.get(row["customer_id"], row["name"])
        unique.setdefault(row["customer_id"], row)
    return dict(
        current_authorities=authorities,
        current_delivery_evidence=evidence,
        current_customers=list(unique.values()),
        current_contracts=contracts,
        current_deliveries=deliveries,
        current_invoices=invoices,
        current_receipts=receipts,
        current_projects=projects,
        customer_sites=sites,
    )


def cost_components(source, current, tables):
    from industrial.tools.build_financials import alloc

    from .completed_period import money, read, stamp

    result = []
    mine = read("red_wash/source/core_operating_data.json")["finance_2026"]
    parents = {
        "SHI": ("LEG_5000", D(current["core_operating_cost_usd"]), "SHI-PRIMARY_USD-COMMON-202608"),
        "PS": (
            "5100",
            D(alloc(mine["pale_sun_site_g_and_a_usd"], [1] * 12)[7]),
            "RW-FINANCE-SELECTED",
        ),
        "RWH": (
            "1200",
            D(alloc(mine["cash_production_cost_incurred_usd"], [1] * 12)[7]),
            "RW-COST",
        ),
    }
    for entity, (account, total, sourceid) in parents.items():
        selected = [r for r in tables["payroll"] if r["legal_entity"] == entity]
        used = D(0)
        for row in selected:
            value = D(row["gross_usd"]) + D(row["employer_burden_usd"])
            used += value
            result.append(
                stamp(
                    source,
                    component_id=row["pay_id"] + "-COMPONENT",
                    pay_id=row["pay_id"],
                    legal_entity=entity,
                    parent_account=account,
                    parent_source_id=sourceid,
                    component="EMPLOYEE_LOADED_COST",
                    amount_usd=money(value),
                    source_period_total_usd=money(total),
                    unit=row["unit"],
                    posting_policy="DETAIL_WITHIN_RETAINED_SOURCE_NOT_ADDITIVE",
                    measurement="PRODUCTION_COST_INCURRED_NOT_SECOND_COGS"
                    if entity == "RWH"
                    else "PAID_OPERATING_COST",
                )
            )
        if used > total:
            raise ValueError("Reconstructed labor exceeds retained source cost population")
        result.append(
            stamp(
                source,
                component_id=f"SH-COST-OTHER-{entity}-202608",
                pay_id=None,
                legal_entity=entity,
                parent_account=account,
                parent_source_id=sourceid,
                component="REMAINING_NONPAYROLL_COST",
                amount_usd=money(total - used),
                source_period_total_usd=money(total),
                unit="unallocated-nonpayroll",
                posting_policy="RETAIN_EXISTING_COST_NO_NEW_ENTRY",
                measurement="RETAINED_SOURCE_REMAINDER",
            )
        )
    return result


def validate_current(source, tables):
    from .completed_period import read

    current = read(CURRENT_SOURCE)
    people = {p["person_id"]: p for p in tables["people"]}
    invoices = tables["current_invoices"]
    contracts = tables["current_contracts"]
    if len({r["contract_id"] for r in contracts}) != len(contracts):
        raise ValueError("Duplicate current contract")
    if len(invoices) != len(contracts) or {r["contract_id"] for r in invoices} != {
        r["contract_id"] for r in contracts
    }:
        raise ValueError("Incomplete current contract invoice population")
    if len(tables["customer_sites"]) != current["commercial_policy"]["sites"]:
        raise ValueError("Customer site population incomplete")
    if sum(D(r["principal_usd"]) for r in invoices if r["legal_entity"] == "SHI") != D(
        current["core_revenue_usd"]
    ):
        raise ValueError("Current source revenue does not reconcile")
    bycontract = {r["contract_id"]: r for r in contracts}
    tax_source = read(TAX_SCOPE_SOURCE)["august_core_transaction_tax"]
    tax_by_customer = {r["customer_id"]: r for r in tax_source["customers"]}
    for invoice in invoices:
        if invoice["customer_id"] in tax_by_customer:
            tax = tax_by_customer[invoice["customer_id"]]
            if (
                invoice.get("tax_usd") != tax["sales_tax_usd"]
                or invoice.get("tax_effective_period") != "2026-08"
                or invoice.get("service_use_jurisdiction") != "US-CA"
                or invoice.get("tax_authority_id") != tax_source["id"]
            ):
                raise ValueError("Current invoice tax differs from applicable service scope")
    authorities = {r["authority_id"]: r for r in tables["current_authorities"]}
    evidence = {r["evidence_id"]: r for r in tables["current_delivery_evidence"]}
    if len(authorities) != len(contracts) or len(evidence) != len(contracts):
        raise ValueError("Authority or performance evidence population incomplete")
    for delivery in tables["current_deliveries"]:
        record = evidence.get(delivery["evidence_id"])
        if record is None or record["delivery_id"] != delivery["delivery_id"]:
            raise ValueError("Delivery evidence relationship missing")
    for invoice in invoices:
        authority = authorities.get(invoice["authority_id"])
        if (
            authority is None
            or authority["contract_id"] != invoice["contract_id"]
            or authority["legal_entity"] != invoice["legal_entity"]
            or authority["authorized_on"] > "2026-08-28"
            or authority["reviewer_person_id"] not in people
            or authority["reviewer_person_id"] == authority["accountable_person_id"]
            or D(authority["amount_usd"]) != D(invoice["principal_usd"])
        ):
            raise ValueError("Missing late or mismatched current authority")
    for row in invoices:
        parent = bycontract[row["contract_id"]]
        if any(row[k] != parent[k] for k in ("legal_entity", "customer_id", "unit")):
            raise ValueError("Current invoice wrong legal entity or customer")
        if D(row["principal_usd"]) != D(parent["monthly_fee_usd"]):
            raise ValueError("Current invoice differs from contract")
    for p in contracts:
        if p["accountable_person_id"] not in people:
            raise ValueError("Current contract owner not employed")
    benefits = defaultdict(D)
    pay_by_id = {p["pay_id"]: p for p in tables["payroll"]}
    components = {c["kind"]: c for c in current["benefits"]["components"]}
    benefit_keys = set()
    for r in tables["benefit_settlements"]:
        key = r["pay_id"], r["component"]
        if key in benefit_keys or r["pay_id"] not in pay_by_id or r["component"] not in components:
            raise ValueError("Duplicate or unknown benefit component")
        benefit_keys.add(key)
        parent = pay_by_id[r["pay_id"]]
        if (
            r["legal_entity"] != parent["legal_entity"]
            or r["person_id"] != parent["person_id"]
            or r["paid_on"] != current["benefits"]["settled_on"]
            or r["provider_id"] != components[r["component"]]["provider_id"]
            or D(r["closing_payable_usd"]) != 0
        ):
            raise ValueError("Benefit payment identity date or closing balance mismatch")
        if D(r["cost_usd"]) - D(r["paid_usd"]) != D(r["closing_payable_usd"]):
            raise ValueError("Benefit settlement rollforward mismatch")
        benefits[r["pay_id"]] += D(r["cost_usd"])
    if benefit_keys != {(pid, kind) for pid in pay_by_id for kind in components}:
        raise ValueError("Benefit component population incomplete")
    for p in tables["payroll"]:
        if benefits[p["pay_id"]] != D(p["remaining_benefit_and_employer_obligations_usd"]):
            raise ValueError("Benefit population does not reconcile to payroll")
    bysource = defaultdict(D)
    sourceamount = {}
    for r in tables["current_book_cost_components"]:
        key = r["legal_entity"], r["parent_source_id"]
        bysource[key] += D(r["amount_usd"])
        sourceamount[key] = D(r["source_period_total_usd"])
    if dict(bysource) != sourceamount:
        raise ValueError("Payroll plus other cost differs from retained source")
    return {
        "current_contracts": len(contracts),
        "current_customer_records": len(tables["current_customers"]),
        "customer_sites": len(tables["customer_sites"]),
        "current_projects": len(tables["current_projects"]),
        "cost_component_parents": len(bysource),
        "core_revenue_usd": current["core_revenue_usd"],
        "core_operating_cost_usd": current["core_operating_cost_usd"],
    }


def verify_current_finance(edition, legacy_snapshot, anchor_rows):
    """Reperform decomposition against independently rebuilt current source journals.

    Call from the composite builder using its already selected legacy and industrial
    snapshots. This function posts nothing and cannot serve as a cash funding plug.
    """
    from .completed_period import money

    tables = edition["tables"]
    core = [
        r
        for r in legacy_snapshot["rows"]
        if r["entity"] == "SHI"
        and r["book"] == "PRIMARY_USD"
        and r["entry_date"].startswith("2026-08")
    ]
    corecost = sum(D(r["signed_usd"]) for r in core if r["account"] == "5000")
    corerevenue = -sum(D(r["signed_usd"]) for r in core if r["account"] == "4000")
    inv = sum(
        D(r["principal_usd"]) for r in tables["current_invoices"] if r["legal_entity"] == "SHI"
    )
    if inv != corerevenue:
        raise ValueError("Current company invoices differ from retained SHI revenue")
    parents = {
        "SHI": corecost,
        "PS": sum(
            D(r["signed_usd"])
            for r in anchor_rows
            if int(r["year"]) == 2026
            and int(r["month"]) == 8
            and r["source_id"] == "RW-FINANCE-SELECTED"
            and r["segment"] == "PS"
            and r["account"] == "5100"
        ),
        "RWH": sum(
            D(r["signed_usd"])
            for r in anchor_rows
            if int(r["year"]) == 2026
            and int(r["month"]) == 8
            and r["source_id"] == "RW-COST"
            and r["account"] == "1200"
        ),
    }
    actual = defaultdict(D)
    for row in tables["current_book_cost_components"]:
        actual[row["legal_entity"]] += D(row["amount_usd"])
    if dict(actual) != parents:
        raise ValueError("Current payroll cost components differ from rebuilt source journals")
    bycontract = defaultdict(D)
    for row in anchor_rows:
        if (
            int(row["year"]) == 2026
            and int(row["month"]) == 8
            and row["entity"] == "ARU_GROUP"
            and row["account"] == "4000"
        ):
            bycontract[row["source_id"]] -= D(row["signed_usd"])
    invoices = {
        r["source_id"]: D(r["principal_usd"])
        for r in tables["current_invoices"]
        if r["legal_entity"] in {"ARU", "BST"}
    }
    if invoices != dict(bycontract):
        raise ValueError("Industrial current invoice population differs from source journal")
    return {
        "status": "RECONCILED_TO_INDEPENDENT_CURRENT_JOURNALS",
        "core_revenue_usd": money(corerevenue),
        "paid_cost_parent_usd": {k: money(v) for k, v in parents.items()},
        "industrial_external_invoices": len(invoices),
        "additional_journal_amount_usd": "0.00",
        "basis": "Cost-component attribution; original cash, P&L and inventory remain unchanged",
    }
