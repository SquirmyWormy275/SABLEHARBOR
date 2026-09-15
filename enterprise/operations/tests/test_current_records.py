"""Source mutations must not turn balanced fiction into unsupported completion."""

import copy
from decimal import Decimal as D

import pytest

from enterprise.operations.completed_period import (
    SOURCE,
    build,
    operating_records,
    read,
    validate,
    workforce_state,
)
from enterprise.operations.current_records import validate_current, verify_current_finance


@pytest.fixture(scope="module")
def edition():
    return build()


def test_commercial_populations_and_research_are_separate(edition):
    t = edition["tables"]
    assert len(t["current_contracts"]) == 92
    assert len(t["current_customers"]) == 88
    assert len({r["customer_id"] for r in t["current_customers"]}) == 88
    assert len(t["customer_sites"]) == 104
    assert sum(
        D(r["principal_usd"]) for r in t["current_invoices"] if r["legal_entity"] == "SHI"
    ) == D("11075500")
    assert all(D(p["revenue_usd"]) == 0 for p in t["current_projects"] if p["unit"] == "willow")
    cradle = next(p for p in t["current_projects"] if p["project_id"] == "SH-CRD-202608-STREAM17")
    assert cradle["direct_margin_usd"] == "500.01"
    assert (
        next(p for p in t["current_customers"] if p["customer_id"] == "ARU-C-001")["name"]
        == "Red Desert Alkali Products LLC"
    )


def test_benefits_and_ruia_close_without_creating_cash_savings(edition):
    t = edition["tables"]
    p = t["payroll"]
    assert sum(D(r["employer_ruia_usd"]) for r in p) == D("3117.50")
    assert all(
        D(r["state_incremental_taxable_wages_usd"]) == 0 for r in t["unemployment_workpapers"]
    )
    assert all(D(r["closing_payable_usd"]) == 0 for r in t["benefit_settlements"])
    cash = -sum(D(r["signed_usd"]) for r in t["journal"] if r["account"].startswith("CASH"))
    expense = sum(D(r["gross_usd"]) + D(r["employer_burden_usd"]) for r in p)
    assert cash == expense == D("8137074.52")


@pytest.mark.parametrize(
    "change", ["amount", "closing", "date", "entity", "omit", "duplicate", "gl"]
)
def test_tax_component_mutations_fail(edition, change):
    tables = copy.deepcopy(edition["tables"])
    row = tables["tax_liabilities"][0]
    if change == "amount":
        row["amount_usd"] = "999999999.00"
    elif change == "closing":
        row["closing_liability_usd"] = "123.00"
    elif change == "date":
        row["remitted_on"] = "2026-08-01"
    elif change == "entity":
        row["legal_entity"] = "BST"
    elif change == "omit":
        tables["tax_liabilities"].pop()
    elif change == "duplicate":
        tables["tax_liabilities"].append(copy.deepcopy(row))
    elif change == "gl":
        next(r for r in tables["journal"] if r["account"] == "CASH_TAX_REMITTANCE")[
            "signed_usd"
        ] = "0.00"
    with pytest.raises(ValueError, match="[Tt]ax|[Rr]emittance"):
        validate(read(SOURCE), tables)


def test_changing_source_and_derived_dispatch_order_fails(edition):
    source = read(SOURCE)
    chain = next(
        c for c in source["operating_chains"] if c["chain_id"] == "SH-CHAIN-202608-DISPATCH-01"
    )
    chain["stages"][:2] = ["DISPATCHED", "QUALIFICATION_CHECK"]
    tables = copy.deepcopy(edition["tables"])
    tables["operating_events"], tables["operating_quantities"] = operating_records(
        source, tables["people"]
    )
    with pytest.raises(ValueError, match="Dispatch precedes"):
        validate(source, tables)


def test_changing_source_asset_to_held_forklift_fails(edition):
    source = read(SOURCE)
    chain = next(
        c for c in source["operating_chains"] if c["chain_id"] == "SH-CHAIN-202608-WAREHOUSE-01"
    )
    chain["asset_id"] = "ARU-MH-01"
    tables = copy.deepcopy(edition["tables"])
    tables["operating_events"], tables["operating_quantities"] = operating_records(
        source, tables["people"]
    )
    with pytest.raises(ValueError, match="defect hold"):
        validate(source, tables)


def test_effective_and_known_on_event_state(edition):
    august = workforce_state(edition, as_of="2026-08-31", known_on="2026-09-15T23:59:59Z")
    gap = workforce_state(edition, as_of="2026-09-05", known_on="2026-09-15T23:59:59Z")
    final = workforce_state(edition, as_of="2026-09-15", known_on="2026-09-15T23:59:59Z")
    assert (august["active_employees"], august["active_principals"]) == (702, 702)
    assert (gap["active_employees"], gap["active_principals"]) == (701, 702)
    assert (final["active_employees"], final["active_principals"]) == (701, 701)
    assert (
        workforce_state(edition, as_of="2026-09-05", known_on="2026-09-05T23:59:59Z")["people"]
        == []
    )


@pytest.mark.parametrize(
    "table,field,value",
    [
        ("benefit_settlements", "paid_usd", "0.00"),
        ("current_invoices", "legal_entity", "BST"),
        ("current_book_cost_components", "amount_usd", "1.00"),
    ],
)
def test_current_source_mutations_fail(edition, table, field, value):
    tables = copy.deepcopy(edition["tables"])
    tables[table][0][field] = value
    with pytest.raises(ValueError):
        validate_current(read(SOURCE), tables)


def test_reperform_retained_journals(edition, tmp_path):
    # Real source builders provide independent book evidence rather than rereading our CSV.
    from industrial.planning.enterprise import load_anchor
    from industrial.planning.legacy_adapter import legacy_snapshot

    legacy = legacy_snapshot()
    anchor = load_anchor()
    receipt = verify_current_finance(edition, legacy, anchor)
    assert receipt["additional_journal_amount_usd"] == "0.00"
    assert receipt["paid_cost_parent_usd"] == {
        "SHI": "11968000.00",
        "PS": "233333.00",
        "RWH": "2329167.00",
    }
    broken = copy.deepcopy(edition)
    broken["tables"]["current_invoices"][0]["principal_usd"] = "1.00"
    with pytest.raises(ValueError, match="retained SHI revenue"):
        verify_current_finance(broken, legacy, anchor)


def test_duplicate_industrial_invoice_and_benefit_identity_fail(edition):
    tables = copy.deepcopy(edition["tables"])
    tables["current_invoices"].append(
        next(r for r in tables["current_invoices"] if r["legal_entity"] == "ARU")
    )
    with pytest.raises(ValueError, match="invoice population"):
        validate_current(read(SOURCE), tables)
    for field, value in (("paid_on", "2026-08-01"), ("legal_entity", "BST")):
        tables = copy.deepcopy(edition["tables"])
        tables["benefit_settlements"][0][field] = value
        with pytest.raises(ValueError, match="Benefit payment"):
            validate_current(read(SOURCE), tables)


@pytest.mark.parametrize(
    "table,field,value",
    [
        ("current_authorities", "authorized_on", "2026-09-01"),
        ("current_authorities", "legal_entity", "BST"),
        ("current_deliveries", "evidence_id", "MISSING"),
    ],
)
def test_authority_and_performance_links_fail_closed(edition, table, field, value):
    tables = copy.deepcopy(edition["tables"])
    tables[table][0][field] = value
    with pytest.raises(ValueError):
        validate_current(read(SOURCE), tables)


def test_current_august_tax_annotation_is_scoped():
    edition = build()
    invoices = edition["tables"]["current_invoices"]
    scoped = [r for r in invoices if r.get("tax_authority_id")]
    assert len(scoped) == 58
    assert all(r["tax_usd"] == "0.00" and r["tax_effective_period"] == "2026-08" for r in scoped)
    assert len([r for r in invoices if r["tax_usd"] is None]) == 34
    for field, value in (("tax_usd", "1.00"), ("tax_effective_period", "2027-08")):
        broken = copy.deepcopy(edition["tables"])
        broken["current_invoices"][0][field] = value
        with pytest.raises(ValueError, match="tax differs"):
            validate_current(read(SOURCE), broken)
