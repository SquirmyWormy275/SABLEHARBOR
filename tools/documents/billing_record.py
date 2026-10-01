"""Build and validate the adopted FF-003 billing successor, never the frozen release."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
import tempfile
from collections import defaultdict
from datetime import datetime
from decimal import Decimal as D
from pathlib import Path

import xlsxwriter

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "docs/finance/evidence/billing/FF-003-v1"
SOURCE = ROOT / "docs/finance/evidence/SH-FIN-HUMAN-001/source.json"
PROPOSAL = ROOT / "docs/finance/evidence/billing-proposal/proposal.json"
PROTECTED = {
    "docs/finance/evidence/billing-proposal/manifest.json": "525792732c77ba0f08f0b1091251d8c25804b454ccca5341b11ae5a5e8748807",
    str(PROPOSAL.relative_to(ROOT)): "23d8d6080ad296468d6b649eda55593d49c33cde0e6b038343ce11e4973e23f8",
    str(SOURCE.relative_to(ROOT)): "c4833cfc6f28db6cd3edcae761b0e2d8f463a20de79f1d6fd5b0c517f8f829b7",
    "docs/finance/evidence/billing-proposal/README.md": "059ce8e77ff8b47c7d5f768f994bfb73525fb4dedf7c3e47e3fd87f656e01b73",
}
JOURNAL_FIELDS = ("journal_id", "period", "entity", "account", "debit_usd", "credit_usd")
ARTIFACTS = ("INVOICE.md", "invoice.pdf", "billing.xlsx", "journal.csv",
             "billing.sqlite3", "reconciliation.json")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def check(condition, message):
    if not condition:
        raise ValueError(message)


def reconcile(record, source, proposal):
    """Independent Decimal checks; no formula cache or declared total is trusted."""
    rows = source["rows"]
    invoice, contract = rows["invoices"][0], rows["contracts"][0]
    check(record["source"] == proposal["source"] and record["scope"] == proposal["scope"],
          "Source provenance or scope changed")
    check(proposal["preserved_source_values"]["invoice"] == invoice, "Source invoice changed")
    check(proposal["preserved_source_values"]["contract"] == contract, "Source contract changed")
    check(record["fact_state"] == "PUBLIC_SYNTHETIC_CONDITIONAL_FORECAST", "Future status lost")
    check(record["accounting_as_of"] == "2027-01-31", "Tax supplement scope changed")
    fields = {f["field_id"]: f for f in record["fields"]}
    check(len(fields) == len(record["fields"]) == 14, "Missing or duplicate field")
    check(set(fields) == {f["field_id"] for f in proposal["proposed_fields"]}, "Field coverage")
    replaced = {"customer.legal_name", "issuer.legal_name", "invoice.tax_presentation"}
    for old in proposal["proposed_fields"]:
        new = fields[old["field_id"]]
        check(new["decision_id"] == old["decision_id"], "Decision identity changed")
        check(new["value"] is not None, "Unresolved field")
        if old["field_id"] not in replaced:
            check(new["value"] == old["value"] and new["disposition"] == "ADOPTED_UNCHANGED",
                  "Undocumented field change")
        else:
            check(new["disposition"] == "REPLACED_BY_BILLING_DECISION", "Replacement not recorded")
    check(fields["issuer.legal_name"]["value"] == "Sable Harbor, LLC", "Wrong issuer")
    check(fields["customer.legal_name"]["value"] == "Copperreach Fabrication, Inc.", "Wrong party")
    i, tax = record["invoice"], record["tax"]
    check(i["invoice_id"] == invoice["invoice_id"] and i["customer_id"] == invoice["customer_id"]
          and i["contract_id"] == contract["contract_id"], "Cross-customer join")
    check(i["due_date"] == invoice["due_date"] and i["issue_date"] == "2027-01-31", "Date drift")
    principal = D(contract["monthly_subscription_usd"]) * D(contract["term_months"])
    check(D(i["monthly_subscription_usd"]) == D(contract["monthly_subscription_usd"])
          and D(i["term_months"]) == D(contract["term_months"]), "Contract terms changed")
    check(principal == D(invoice["amount_usd"]) == D(i["subscription_usd"])
          == D(i["customer_total_usd"]) == D(i["issue_date_customer_ar_usd"]), "Principal mismatch")
    check(D(i["customer_tax_reimbursement_usd"]) == 0, "Customer tax added")
    assumptions = record["commercial_assumptions"]
    check(assumptions["seats"] == assumptions["users_in_sacramento_city"] == int(contract["seats"])
          and assumptions["seller_entity"] == "SHI"
          and assumptions["purchaser_2027_digital_purchases_from_SHI_below_5000000"] is True
          and assumptions["exemption_claimed"] is False
          and assumptions["correspondence_addresses_are_geometry"] is False, "Tax/party basis changed")
    check(assumptions["service_period_start"] == "2027-01-01"
          and assumptions["service_period_end"] == "2027-12-31"
          and assumptions["billing_jurisdiction"] == "Sacramento city, California"
          and "PLANNING_ASSUMPTION" in tax["rate_state"], "Unsupported period or tax sourcing")
    check(tax["treatment"] == "SELLER_BORNE_SALES_TAX_NO_REIMBURSEMENT", "Wrong tax treatment")
    check(D(tax["taxable_gross_receipts_usd"]) == principal and D(tax["rate"]) == D("0.0875"),
          "Tax basis changed without successor")
    expense = (principal * D(tax["rate"])).quantize(D("0.01"))
    check(expense == D(tax["seller_expense_usd"]) == D(tax["initial_payable_usd"]), "Tax mismatch")
    check(D(tax["initial_cash_payment_usd"]) == 0, "Unsupported tax payment")
    journal = record["supplemental_journal"]
    check(len(journal) == 2 and {j["account"] for j in journal}
          == {"BILLING_SALES_TAX_EXPENSE", "BILLING_SALES_TAX_PAYABLE"}, "Supplemental journal scope")
    for j in journal:
        debit, credit = (expense, D(0)) if j["account"].endswith("EXPENSE") else (D(0), expense)
        check(D(j["debit_usd"]) == debit and D(j["credit_usd"]) == credit
              and j["entity"] == "SHI" and j["period"] == "2027-01-31"
              and j["journal_id"] == "SH-FIN-BILL-001-TAX-ISSUE", "Unbalanced/misclassified tax journal")
    totals = defaultdict(lambda: D(0))
    for movement in rows["credit_history"]:
        totals[movement["action"]] += D(movement["amount_usd"])
    collected = totals["RECEIPT"] + totals["RECOVERY"]
    credits = sum(D(c["amount_usd"]) for c in rows["credit_notes"])
    surviving = totals["WRITEOFF"] - credits - totals["RECOVERY"]
    ar = principal - totals["RECEIPT"] - totals["WRITEOFF"]
    check(credits == totals["CREDIT"] == D(invoice["credit_usd"])
          == D(invoice["writtenoff_credit_usd"]), "Credits mismatch")
    check(collected == D(invoice["collected_usd"])
          and totals["RECOVERY"] == D(invoice["recovered_usd"]), "Recovery double-counted")
    check(ar == D(invoice["remaining_usd"]) == 0 and principal == collected + credits + surviving + ar,
          "Principal claim bridge does not balance")
    groups = defaultdict(lambda: D(0))
    for line in rows["journal"]:
        check(line["fact_state"] == "CONDITIONAL_FORECAST" and line["entity"] == "SHI", "Source state")
        groups[line["source_id"]] += D(line["debit_usd"]) - D(line["credit_usd"])
    check(all(v == 0 for v in groups.values()), "Native journal imbalance")
    check(set(groups) == {e["event_id"] for e in rows["events"]}, "Native event linkage")
    check({m["source_id"] for m in rows["credit_history"]} <= set(groups), "Orphan movement")
    return {"scope": "January issuance supplement; legacy principal lifecycle shown separately",
            "principal_usd": str(principal), "initial_tax_expense_usd": str(expense),
            "initial_tax_payable_usd": str(expense), "supplemental_debits_usd": str(expense),
            "supplemental_credits_usd": str(expense), "customer_collected_usd": str(collected),
            "customer_credits_usd": str(credits), "surviving_writtenoff_claim_usd": str(surviving),
            "legacy_ending_customer_ar_usd": str(ar),
            "legacy_journal_debits_usd": str(sum(D(j["debit_usd"]) for j in rows["journal"])),
            "legacy_journal_credits_usd": str(sum(D(j["credit_usd"]) for j in rows["journal"])),
            "principal_difference_usd": str(principal - collected - credits - surviving - ar),
            "tax_journal_difference_usd": "0.00", "result": "PASS"}


def invoice_markdown(record):
    f = {r["field_id"]: r["value"] for r in record["fields"]}
    issuer_address = "\n\n".join(f["issuer.billing_address"])
    customer_address = "\n\n".join(f["customer.billing_address"])
    amount = f"${D(record["invoice"]["customer_total_usd"]):,.2f}"
    monthly = f"${D(record["invoice"]["monthly_subscription_usd"]):,.2f}"
    seats = record["commercial_assumptions"]["seats"]
    return f'''# Invoice

**Invoice:** {record["invoice"]["invoice_id"]}

**Issued:** January 31, 2027 · **Due:** February 28, 2027

**Contract:** FF-003 · **Purchase order:** {f["customer.purchase_order"]}

## From

**{f["issuer.legal_name"]} — operating as Foundry Field**

{issuer_address}

{f["issuer.display_contact"]}

## Bill to

**{f["customer.legal_name"]}** · Customer SYN-CUSTOMER-003

Accounts Payable

{customer_address}

{f["customer.display_contact"]}

## Subscription

| Description | Term | Monthly charge | Amount USD |
|---|---|---:|---:|
| Foundry Field subscription, {seats} seats | January–December 2027 | {monthly} | {amount} |

**Total due: {amount} USD**

Sable Harbor bears the applicable sales tax separately under the adopted FF-003 billing
terms. No sales-tax reimbursement is charged to the customer. This is not a tax exemption.

Reference this invoice ID in correspondence. Operational payment instructions are omitted
from this public fictional archive; the displayed contacts are inert.

**Public synthetic company record — 2027 conditional forecast.** Authored September 13,
2026 from the adopted billing record; not a real demand for payment or proof of delivery.
Addresses are fictional correspondence details. Later collections, credits and default
are excluded from this issuance-date invoice.
'''


def workbook(record, reconciliation):
    book = xlsxwriter.Workbook(HERE / "billing.xlsx", {"strings_to_formulas": False,
                                                        "strings_to_urls": False})
    book.set_properties({"title": "Foundry Field | FF-003 billing", "author": "Sable Harbor",
                         "created": datetime(2026, 9, 13)})
    title = book.add_format({"bold": True, "font_size": 19, "font_color": "#101214"})
    head = book.add_format({"bold": True, "bg_color": "#101214", "font_color": "white", "text_wrap": True})
    text = book.add_format({"font_size": 11, "text_wrap": True, "valign": "vcenter", "indent": 1,
                            "bottom": 1, "bottom_color": "#DDDDDD"})
    money = book.add_format({"font_size": 11, "num_format": "$#,##0.00;($#,##0.00);$0.00",
                             "valign": "vcenter", "bottom": 1, "bottom_color": "#DDDDDD"})

    def sheet(name, labels, widths):
        w = book.add_worksheet(name)
        w.hide_gridlines(2)
        w.set_landscape()
        w.set_paper(1)
        w.fit_to_pages(1, 1)
        w.set_margins(.4, .4, .4, .65)
        for col, width in enumerate(widths):
            w.set_column(col, col, width, text)
        w.merge_range(0, 0, 0, len(labels)-1, "FOUNDRY FIELD / " + name, title)
        w.set_row(0, 30)
        w.merge_range(1, 0, 1, len(labels)-1, "SH-FIN-BILL-001 · Synthetic 2027 forecast · FF-003", text)
        w.set_row(1, 26)
        w.write_row(3, 0, labels, head)
        w.set_row(3, 30)
        w.freeze_panes(4, 0)
        w.repeat_rows(0, 3)
        w.set_footer("SH-FIN-BILL-001 | Conditional forecast | &P of &N", {"margin": .25})
        return w

    monthly = float(record["invoice"]["monthly_subscription_usd"])
    term = record["invoice"]["term_months"]
    principal = float(reconciliation["principal_usd"])
    tax_amount = float(reconciliation["initial_tax_expense_usd"])
    rate = float(record["tax"]["rate"])
    source = json.loads(SOURCE.read_text())["rows"]
    movements = {action: float(sum(D(row["amount_usd"]) for row in source["credit_history"]
                 if row["action"] == action)) for action in ("RECEIPT", "WRITEOFF", "RECOVERY")}
    collected = float(reconciliation["customer_collected_usd"])
    credits = float(reconciliation["customer_credits_usd"])
    surviving = float(reconciliation["surviving_writtenoff_claim_usd"])
    w = sheet("Invoice and tax", ["Measure", "Value", "Meaning"], [38, 24, 65])
    values = [("Monthly subscription", monthly, "Contract FF-003; 140 seats."),
              ("Term months", term, "January–December 2027."),
              ("Subscription charge", principal, "Customer consideration; not cash or earned revenue."),
              ("Customer tax reimbursement", 0, "Seller bears sales tax separately; not exempt."),
              ("Customer total due", principal, "Due February 28, 2027."),
              ("Sales tax rate", rate, "8.75%; January 2027 planning assumption."),
              ("Seller tax expense and payable", tax_amount, "Separate issuance supplement; reduces pretax earnings."),
              ("Initial tax payment", 0, "No cash settlement represented."),
              ("Customer-total check", 0, "Must equal zero against the preserved source invoice.")]
    for n, (label, value, note) in enumerate(values, 4):
        w.write(n, 0, label); w.write_number(n, 1, value, money); w.write(n, 2, note); w.set_row(n, 38)
    w.write_number(5, 1, term, text)
    w.write_formula(6, 1, "=B5*B6", money, principal)
    w.write_formula(8, 1, "=B7+B8", money, principal)
    w.write_number(9, 1, rate, book.add_format({"num_format": "0.00%", "font_size": 11, "valign": "vcenter", "bottom": 1, "bottom_color": "#DDDDDD"}))
    w.write_formula(10, 1, "=ROUND(B7*B10,2)", money, tax_amount)
    w.write_formula(12, 1, f"=B9-{principal}", money, 0)
    w.print_area(0, 0, 12, 2)
    w = sheet("Principal history", ["Measure", "USD", "Meaning"], [38, 24, 65])
    vals = [("Original invoice", principal, "Preserved release principal."),
            ("February receipt", movements["RECEIPT"], "Pre-writeoff cash."),
            ("June gross writeoff", movements["WRITEOFF"], "Removed from AR; not a debt release."),
            ("July and August credits", credits, "Applied to written-off claim."),
            ("October recovery", movements["RECOVERY"], "Included once in collections."),
            ("Total collected", collected, "Receipt plus recovery."),
            ("Surviving written-off claim", surviving, "Unrecognized claim; not booked AR."),
            ("Remaining ledger AR", 0, "Zero does not mean paid in full."),
            ("Principal bridge difference", 0, "Principal less cash, credits, surviving claim and AR.")]
    for n, (label, value, note) in enumerate(vals, 4):
        w.write(n, 0, label); w.write_number(n, 1, value, money); w.write(n, 2, note); w.set_row(n, 38)
    for row, formula, value in [(9, "=B6+B9", collected), (10, "=B7-B8-B9", surviving),
                                (11, "=B5-B6-B7", 0), (12, "=B5-B10-B8-B11-B12", 0)]:
        w.write_formula(row, 1, formula, money, value)
    w.print_area(0, 0, 12, 2)
    w = sheet("Tax journal", ["Period", "Account", "Debit USD", "Credit USD"], [19, 48, 25, 25])
    for n, row in enumerate(record["supplemental_journal"], 4):
        w.write(n, 0, row["period"]); w.write(n, 1, row["account"])
        w.write_number(n, 2, float(row["debit_usd"]), money)
        w.write_number(n, 3, float(row["credit_usd"]), money); w.set_row(n, 50)
    w.write(7, 1, "TOTAL")
    w.write_formula(7, 2, "=SUM(C5:C6)", money, tax_amount)
    w.write_formula(7, 3, "=SUM(D5:D6)", money, tax_amount)
    w.write(8, 1, "BALANCE CHECK"); w.write_formula(8, 2, "=C8-D8", money, 0)
    w.merge_range(10, 0, 12, 3, "SHI / January 31 issuance only. These packet-scoped accounts supplement the unchanged release. No tax remittance, refund, bad-debt relief or later tax closing balance is represented.", text)
    w.print_area(0, 0, 12, 3)
    w = sheet("Source register", ["Reference", "Value"], [32, 98])
    refs = [("Decision", record["decision"]), ("Record", "record.json / SH-FIN-BILL-001"),
            ("Issuer", "Sable Harbor, LLC operating as Foundry Field; entity SHI."),
            ("Customer", "Copperreach Fabrication, Inc.; SYN-CUSTOMER-003."),
            ("Source SHA-256", record["source"]["packet_sha256"]),
            ("Legacy scope", "Invoice-linked events only; excludes full contract revenue and allowance allocations."),
            ("Status", "2027 conditional forecast; not September 2026 actuals."),
            ("Tax basis", "Seller bears sales tax. Full subscription is taxable receipts; no tax-inclusive divisor."),
            ("Reconciliation", "reconciliation.json: " + reconciliation["result"]),
            ("Research", "September 13, 2026; statutory and city source URLs in record.json.")]
    for n, (key, value) in enumerate(refs, 4):
        w.write(n, 0, key); w.write(n, 1, value); w.set_row(n, 38)
    w.print_area(0, 0, 13, 1)
    book.close()


def build():
    r = json.loads((HERE / "record.json").read_text())
    result = reconcile(r, json.loads(SOURCE.read_text()), json.loads(PROPOSAL.read_text()))
    dump(HERE / "reconciliation.json", result)
    (HERE / "INVOICE.md").write_text(invoice_markdown(r))
    workbook(r, result)
    with (HERE / "journal.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(JOURNAL_FIELDS), lineterminator="\n")
        writer.writeheader(); writer.writerows(r["supplemental_journal"])
    dbpath = HERE / "billing.sqlite3"
    if dbpath.exists():
        dbpath.unlink()
    with sqlite3.connect(dbpath) as db:
        db.execute("CREATE TABLE billing_record (record_id TEXT PRIMARY KEY, source_json TEXT NOT NULL)")
        db.execute("INSERT INTO billing_record VALUES (?,?)", (r["record_id"], json.dumps(r, sort_keys=True)))
        db.execute("CREATE TABLE tax_journal (journal_id TEXT, period TEXT, entity TEXT, account TEXT, debit_usd TEXT, credit_usd TEXT, PRIMARY KEY(journal_id, account))")
        db.executemany("INSERT INTO tax_journal VALUES (?,?,?,?,?,?)", [tuple(j[key] for key in JOURNAL_FIELDS) for j in r["supplemental_journal"]])
        db.execute("CREATE TABLE reconciliation (measure TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.executemany("INSERT INTO reconciliation VALUES (?,?)", sorted(result.items()))
    from tools.documents import build_controlled_publications as pub
    old = pub.BRANDS.copy()
    try:
        pub.BRANDS["foundry-field"] = {**pub.BRANDS["corporate"],
            "logo": "assets/brand/logos/foundry-field__primary-horizontal.svg",
            "logo_width": 220, "logo_height": 69}
        with tempfile.TemporaryDirectory() as tmp:
            pub.render_pdf(libreoffice="libreoffice", ghostscript="gs", qpdf=None, tmp=Path(tmp),
                           src_rel=str((HERE / "INVOICE.md").relative_to(ROOT)),
                           out_rel=str((HERE / "invoice.pdf").relative_to(ROOT)), brand="foundry-field")
    finally:
        pub.BRANDS.clear(); pub.BRANDS.update(old)
    dependencies = [HERE / "record.json", HERE / "README.md", ROOT / r["decision"], Path(__file__),
                    SOURCE, PROPOSAL, ROOT / "tools/documents/build_controlled_publications.py",
                    ROOT / "assets/brand/logos/foundry-field__primary-horizontal.svg"]
    dump(HERE / "manifest.json", {"record_id": r["record_id"], "version": r["version"],
        "status": r["acceptance"], "fact_state": r["fact_state"],
        "inputs": {str(p.relative_to(ROOT)): sha(p) for p in dependencies},
        "artifacts": {name: sha(HERE / name) for name in ARTIFACTS}})
    dump(HERE / "evidence-register.json", {"package_id": r["record_id"],
        "title": "Foundry Field / Copperreach adopted billing record", "status": r["acceptance"],
        "markdown": str((HERE / "README.md").relative_to(ROOT)),
        "reconciliation": str((HERE / "reconciliation.json").relative_to(ROOT)),
        "visual_manifest": str((HERE / "manifest.json").relative_to(ROOT)),
        "sources": [{"path": str(p.relative_to(ROOT)), "sha256": sha(p)}
                    for p in (HERE / "record.json", ROOT / r["decision"], SOURCE)],
        "artifacts": {str((HERE / n).relative_to(ROOT)): sha(HERE / n) for n in ARTIFACTS}})


def validate():
    for path, digest in PROTECTED.items():
        check(sha(ROOT / path) == digest, "Protected source changed: " + path)
    r = json.loads((HERE / "record.json").read_text())
    expected = reconcile(r, json.loads(SOURCE.read_text()), json.loads(PROPOSAL.read_text()))
    check(json.loads((HERE / "reconciliation.json").read_text()) == expected, "Stale reconciliation")
    check((HERE / "INVOICE.md").read_text() == invoice_markdown(r), "Stale invoice")
    manifest = json.loads((HERE / "manifest.json").read_text())
    check(set(manifest["artifacts"]) == set(ARTIFACTS), "Manifest coverage")
    for path, digest in manifest["inputs"].items():
        check(sha(ROOT / path) == digest, "Stale input: " + path)
    for path, digest in manifest["artifacts"].items():
        check(sha(HERE / path) == digest, "Stale artifact: " + path)
    with (HERE / "journal.csv").open() as stream:
        check(list(csv.DictReader(stream)) == r["supplemental_journal"], "CSV journal drift")
    with sqlite3.connect(f"file:{HERE / 'billing.sqlite3'}?mode=ro", uri=True) as db:
        check(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "Invalid database")
        check(json.loads(db.execute("SELECT source_json FROM billing_record").fetchone()[0]) == r,
              "Database source drift")
        check(dict(db.execute("SELECT * FROM reconciliation")) == expected, "Database reconciliation")
        saved = list(db.execute("SELECT journal_id,period,entity,account,debit_usd,credit_usd FROM tax_journal ORDER BY account"))
        check(saved == sorted(tuple(j[key] for key in JOURNAL_FIELDS) for j in r["supplemental_journal"]),
              "Database tax journal drift")
    from tools.documents.evidence_packages import records
    check(any(row[0] == r["record_id"] for row in records(ROOT)), "Missing catalog package")
    print("PASS: 14 billing fields, 3 decisions, principal/tax journals, protected sources and 6 artifacts")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "validate"))
    if parser.parse_args().command == "build":
        build()
    validate()
