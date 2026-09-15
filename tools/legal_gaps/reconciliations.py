"""Five bounded, public source-derived reconciliation exercises; no new postings."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
import subprocess
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import xlsxwriter

ROOT = Path(__file__).resolve().parents[2]
DEST = Path("docs/legal/gap-instruments/reconciliations")
STATUS = "DRAFT_FOR_EXACT_FILE_REVIEW"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def model(root=ROOT):
    evidence = []

    def select(family, table, where):
        path = f"docs/finance/evidence/{family}/source/{table}.csv"
        with (root / path).open() as stream:
            rows = [r for r in csv.DictReader(stream) if all(r[k] == v for k, v in where.items())]
        if not rows:
            raise ValueError(f"Empty selection: {path} {where}")
        if table not in {"receivable_aging", "journal"} and len(rows) != 1:
            raise ValueError(f"Expected one snapshot: {path} {where}; found {len(rows)}")
        ident = f"E{len(evidence) + 1:02}"
        evidence.append(
            dict(id=ident, path=path, sha256=sha(root / path), selector=where, rows=rows)
        )
        return ident, rows

    packets = []

    def packet(slug, title, scope, request, limitation):
        p = dict(
            id="SH-RECON-" + slug.upper(),
            slug=slug,
            title=title,
            scope=scope,
            scenario="base",
            period="2027-01-31",
            status=STATUS,
            inputs=[],
            checks=[],
            evidence_request=request,
            limitation=limitation,
        )
        packets.append(p)
        return p

    def inp(p, label, evid, row, field):
        e = next(x for x in evidence if x["id"] == evid)
        amount = e["rows"][row][field]
        Decimal(amount)
        p["inputs"].append(
            dict(label=label, amount=amount, evidence=evid, row_index=row, field=field)
        )
        return len(p["inputs"]) - 1

    def check(p, label, terms):
        value = sum((Decimal(p["inputs"][i]["amount"]) * sign for i, sign in terms), Decimal(0))
        p["checks"].append(dict(label=label, terms=terms, result=str(value), tolerance="0.02"))
        if abs(value) > Decimal(".02"):
            raise ValueError(f"Unreconciled source {p['id']}: {label} {value}")

    p = packet(
        "bank",
        "Bank clearing bridge",
        "ARU_GROUP | industrial forecast model | January 2027",
        "Obtain January bank-issued statement and subsequent clearing support for listed deposits and payments; compare dates and amounts with the model.",  # noqa: E501 -- reader-facing prose
        "This is a synthetic clearing schedule. A zero difference does not establish independent bank cash, ownership or actual payment.",  # noqa: E501 -- reader-facing prose
    )
    e, _ = select(
        "treasury",
        "industrial_bank_reconciliations",
        dict(scenario="base", entity="ARU_GROUP", year="2027", month="1"),
    )
    for label, field in [
        ("Opening modeled bank cash", "opening_bank_cash_usd"),
        ("Cleared receipts", "cleared_receipts_usd"),
        ("Cleared payments", "cleared_payments_usd"),
        ("Closing modeled bank cash", "closing_bank_cash_usd"),
        ("Deposits in transit", "deposits_in_transit_usd"),
        ("Outstanding payments", "outstanding_payments_usd"),
        ("Adjusted bank cash", "adjusted_bank_cash_usd"),
        ("Ledger cash", "ledger_cash_usd"),
    ]:
        inp(p, label, e, 0, field)
    check(p, "Opening + receipts − payments − closing", [(0, 1), (1, 1), (2, -1), (3, -1)])
    check(p, "Closing + deposits − outstanding − adjusted", [(3, 1), (4, 1), (5, -1), (6, -1)])
    check(p, "Adjusted bank cash − ledger cash", [(6, 1), (7, -1)])

    p = packet(
        "ar",
        "Receivables aging to subledger",
        "Atlas Meridian | Core forecast model | January 2027",
        "Obtain the two underlying customer invoices, delivery or license acceptance, and subsequent receipt support; assess collectability separately from the arithmetic tie.",  # noqa: E501 -- reader-facing prose
        "The complete selected month-end aging population is used. Terminal invoice-master balances are excluded; gross AR is before allowance.",  # noqa: E501 -- reader-facing prose
    )
    e, rows = select(
        "customer",
        "receivable_aging",
        dict(scenario="base", unit="atlas-meridian", period="2027-01-31"),
    )
    terms = []
    for n, r in enumerate(rows):
        terms.append((inp(p, r["invoice_id"], e, n, "outstanding_usd"), 1))
    e, _ = select(
        "customer",
        "subledger_rollforward",
        dict(scenario="base", unit="atlas-meridian", period="2027-01-31"),
    )
    terms.append((inp(p, "Month-end gross AR", e, 0, "gross_ar_usd"), -1))
    check(p, "Aging total − month-end gross AR", terms)

    p = packet(
        "ap",
        "Payables journal to subledger",
        "Atlas Meridian | Core forecast model | January 2027",
        "Obtain vendor invoices and service acceptance for both hosting accruals; inspect post-period payments and unmatched invoices for unrecorded liabilities.",  # noqa: E501 -- reader-facing prose
        "January is the first Core model period. All January BIZ_AP legs are selected, credits positive. A tied model does not test liability completeness; terminal payable-master balances are excluded.",  # noqa: E501 -- reader-facing prose
    )
    e, rows = select(
        "close",
        "journal",
        dict(scenario="base", unit="atlas-meridian", period="2027-01-31", account="BIZ_AP"),
    )
    terms = []
    for n, r in enumerate(rows):
        terms.extend(
            [
                (inp(p, r["journal_id"] + " credit", e, n, "credit_usd"), 1),
                (inp(p, r["journal_id"] + " debit", e, n, "debit_usd"), -1),
            ]
        )
    e, _ = select(
        "treasury",
        "subledger_rollforward",
        dict(scenario="base", unit="atlas-meridian", period="2027-01-31"),
    )
    terms.append((inp(p, "Month-end vendor AP", e, 0, "vendor_ap_usd"), -1))
    check(p, "Cumulative credits − debits − vendor AP", terms)

    p = packet(
        "debt",
        "Debt principal movements",
        "ARU_GROUP | industrial forecast model | January 2027",
        "Obtain lender and lessor statements, executed credit terms and payment confirmations. Test maturity, security and covenants from executed terms, not assumed thresholds.",  # noqa: E501 -- reader-facing prose
        "Legacy term debt, replacement term debt and retained leases stay separate. Scheduled and cash-paid principal are distinct fields; interest and issuance costs are outside these principal checks.",  # noqa: E501 -- reader-facing prose
    )
    e, _ = select(
        "supporting-schedules",
        "industrial_debt",
        dict(scenario="base", entity="ARU_GROUP", year="2027", month="1"),
    )
    for title, fields in [
        (
            "Legacy term",
            (
                "opening_legacy_term_usd",
                "principal_cash_paid_legacy_term_usd",
                "closing_legacy_term_usd",
            ),
        ),
        (
            "Replacement term",
            (
                "opening_replacement_term_usd",
                "replacement_debt_draw_usd",
                "principal_cash_paid_replacement_term_usd",
                "closing_replacement_term_usd",
            ),
        ),
        (
            "Retained leases",
            ("opening_lease_usd", "principal_cash_paid_lease_usd", "closing_lease_usd"),
        ),
    ]:
        terms = []
        for n, f in enumerate(fields):
            sign = 1 if n == 0 or f == "replacement_debt_draw_usd" else -1
            terms.append((inp(p, f.removesuffix("_usd").replace("_", " "), e, 0, f), sign))
        check(p, title + " principal rollforward difference", terms)

    p = packet(
        "fixed-assets",
        "Asset carrying value",
        "Willow / FORT-TEST-RIG | Core forecast model | January 2027",
        "Obtain purchase invoice, receipt, commissioning approval and physical inspection evidence for FORT-TEST-RIG; support useful life and depreciation commencement.",  # noqa: E501 -- reader-facing prose
        "A single identified asset is selected, not the enterprise asset population. Zero modeled accumulated depreciation does not establish that no depreciation should be recognized.",  # noqa: E501 -- reader-facing prose
    )
    e, _ = select(
        "supporting-schedules",
        "asset_rollforward",
        dict(scenario="base", unit="willow", period="2027-01-31", asset_id="FORT-TEST-RIG"),
    )
    for label, field in [
        ("Recorded cost", "cost_usd"),
        ("Accumulated depreciation", "accumulated_usd"),
        ("Net book value", "net_book_usd"),
    ]:
        inp(p, label, e, 0, field)
    check(p, "Cost − accumulated depreciation − net book value", [(0, 1), (1, -1), (2, -1)])
    return dict(
        id="SH-RECON-001",
        status=STATUS,
        classification="PUBLIC_SOURCE_DERIVED_PRACTICE",
        source_release="business-operations-v1.0.0",
        source_revision="57cfa1b1c483ccf1f8b15d82c4cbdadbeef8063e",
        scope="Five bounded selections; no cross-case aggregate and no new postings.",
        evidence=evidence,
        workpapers=packets,
    )


def workbook(data, path, worked):
    wb = xlsxwriter.Workbook(path)
    wb.set_properties(
        dict(title="Sable Harbor reconciliation practice", created=datetime(2026, 9, 12))
    )  # noqa: DTZ001 -- fixed document metadata
    dark = wb.add_format(
        dict(
            bg_color="#243238",
            font_color="white",
            bold=True,
            font_size=12,
            text_wrap=True,
            valign="vcenter",
        )
    )
    body = wb.add_format(dict(font_size=11, text_wrap=True, valign="top", align="left", indent=1))
    num = wb.add_format(
        dict(
            font_size=11,
            num_format="#,##0.00;[Red](#,##0.00);0.00",
            valign="top",
            align="right",
            indent=1,
        )
    )
    blank = wb.add_format(
        dict(bg_color="#FFF2CC", border=1, border_color="#D7D1C3", text_wrap=True, valign="top")
    )

    def sheet(name, title):
        ws = wb.add_worksheet(name)
        ws.hide_gridlines(2)
        ws.set_column(0, 0, 52)
        ws.set_column(1, 1, 22)
        ws.set_column(2, 2, 48)
        ws.merge_range("A1:C1", title, dark)
        ws.set_row(0, 30)
        ws.merge_range(
            "A2:C2",
            ("PUBLIC WORKED EXAMPLE" if worked else "PUBLIC PRACTICE — BLANK RESPONSES")
            + " | Draft design for review",
            body,
        )
        ws.set_row(1, 24)
        ws.set_landscape()
        ws.set_paper(8)
        ws.fit_to_pages(1, 1)
        ws.set_margins(0.35, 0.35, 0.35, 0.55)
        ws.set_footer("&CSH-RECON-001 | &A | &P of &N", {"margin": 0.2})
        ws.freeze_panes(5, 0)
        return ws

    ws = sheet("Read first", "SABLE HARBOR / Reconciliation practice")
    lines = [
        (
            "Purpose",
            "Reperform five bounded source checks. Separate public worked answers are supplied for self-study.",  # noqa: E501 -- reader-facing prose
        ),
        (
            "Scope",
            "Base scenario, January 2027; each worksheet names its source system and entity. Never add the cases together.",  # noqa: E501 -- reader-facing prose
        ),
        (
            "Working method",
            "Read the supplied inputs and native locators. Enter your own calculation in yellow cells; write a conclusion and evidence request before opening worked.xlsx.",  # noqa: E501 -- reader-facing prose
        ),
        (
            "Evidence access",
            "Exact complete selected rows, filters and source hashes are in source.json. Evidence IDs below match the Source register sheet. Native CSV links are in README.md.",  # noqa: E501 -- reader-facing prose
        ),
        (
            "Evidence boundary",
            "All supplied figures are public synthetic model records. Arithmetic consistency does not establish execution, valuation, completeness or independent corroboration.",  # noqa: E501 -- reader-facing prose
        ),
        (
            "Approval",
            "Draft workbook designs require exact-file owner review. No original legal instrument or accepted financial record is changed.",  # noqa: E501 -- reader-facing prose
        ),
    ]
    for n, (k, v) in enumerate(lines, 3):
        ws.write(n, 0, k, body)
        ws.merge_range(n, 1, n, 2, v, body)
        ws.set_row(n, 60)
    ws.print_area(0, 0, 8, 2)
    for p in data["workpapers"]:
        ws = sheet(p["slug"][:31], p["title"])
        ws.merge_range("A3:C3", p["scope"] + " | base | USD", body)
        ws.set_row(2, 25)
        ws.write_row(4, 0, ["Supplied source input", "Amount USD", "Native locator"], dark)
        ws.set_row(4, 25)
        for n, i in enumerate(p["inputs"], 5):
            ws.write(n, 0, i["label"], body)
            ws.write_number(n, 1, float(i["amount"]), num)
            ws.write(n, 2, f"{i['evidence']} / row {i['row_index'] + 1} / {i['field']}", body)
            ws.set_row(n, 30)
        row = 6 + len(p["inputs"])
        ws.merge_range(row, 0, row, 2, "Reperform — expected difference within $0.02", dark)
        ws.set_row(row, 26)
        for c in p["checks"]:
            row += 1
            ws.write(row, 0, c["label"], body)
            ws.set_row(row, 32)
            if worked:
                formula = "=" + "".join(
                    ("+" if sign == 1 else "-") + f"B{i + 6}" for i, sign in c["terms"]
                ).lstrip("+")
                ws.write_formula(row, 1, formula, num, float(c["result"]))
                ws.write(row, 2, "Source arithmetic reconciles; see limitations below.", body)
            else:
                ws.write_blank(row, 1, None, blank)
                ws.write_blank(row, 2, None, blank)
        row += 2
        ws.write(row, 0, "Conclusion and limits", body)
        ws.merge_range(row, 1, row, 2, p["limitation"] if worked else "", body if worked else blank)
        ws.set_row(row, 66)
        row += 1
        ws.write(row, 0, "Further evidence request", body)
        ws.merge_range(
            row, 1, row, 2, p["evidence_request"] if worked else "", body if worked else blank
        )
        ws.set_row(row, 66)
        ws.print_area(0, 0, row, 2)
    ws = sheet("Source register", "Exact source selections")
    ws.set_column(0, 0, 10)
    ws.set_column(1, 1, 74)
    ws.set_column(2, 2, 76)
    ws.write_row(3, 0, ["ID", "Repository CSV / selected rows", "SHA-256"], dark)
    for n, e in enumerate(data["evidence"], 4):
        ws.write(n, 0, e["id"], body)
        ws.write(n, 1, e["path"] + "\nSelected rows: " + str(len(e["rows"])), body)
        ws.write(n, 2, e["sha256"], body)
        ws.set_row(n, 52)
    ws.print_area(0, 0, 3 + len(data["evidence"]), 2)
    wb.close()


def db_write(path, data):
    if path.exists():
        path.unlink()
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE records(kind TEXT NOT NULL, id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
        )
        db.execute(
            "INSERT INTO records VALUES (?,?,?)",
            (
                "package",
                data["id"],
                json.dumps(
                    {k: v for k, v in data.items() if k not in ["evidence", "workpapers"]},
                    sort_keys=True,
                ),
            ),
        )
        for kind in ["evidence", "workpapers"]:
            db.executemany(
                "INSERT INTO records VALUES (?,?,?)",
                [(kind, x["id"], json.dumps(x, sort_keys=True)) for x in data[kind]],
            )


def generate(root, out):
    out.mkdir(parents=True, exist_ok=True)
    data = model(root)
    dump(out / "source.json", data)
    for mode in ["blank", "worked"]:
        workbook(data, out / (mode + ".xlsx"), mode == "worked")
    db_write(out / "reconciliations.sqlite3", data)
    readme = "# Reconciliation practice\n\nFive bounded checks using accepted public model rows. Start with [blank.xlsx](blank.xlsx); compare [worked.xlsx](worked.xlsx) only after completing your calculations and evidence requests. New designs remain draft for exact-file review.\n\n[Exact selected rows and source pins](source.json) · [SQLite mirror](reconciliations.sqlite3) · [Separate worked explanation](WORKED.md).\n\n| Case | Population | Checks |\n|---|---|---:|\n"  # noqa: E501 -- reader-facing prose
    worked = "# Public worked reconciliations\n\nThese are source-derived learning answers, not private assessment material or an audit opinion. No balancing plugs or new transactions are created. All checks use a $0.02 rounding tolerance.\n"  # noqa: E501 -- reader-facing prose
    for p in data["workpapers"]:
        scope_cell = p["scope"].replace("|", "\\|")
        readme += f"| {p['title']} | {scope_cell} | {len(p['checks'])} |\n"
        worked += f"\n## {p['title']}\n\n{p['scope']}; base scenario.\n\n"
        for c in p["checks"]:
            worked += f"- {c['label']}: ${Decimal(c['result']):,.2f}.\n"
        worked += f"\n{p['limitation']}\n\n**Request:** {p['evidence_request']} These originals are not supplied by this selected evidence set; this is not a claim of repository-wide absence.\n"  # noqa: E501 -- reader-facing prose
    readme += "\n## Source access\n\nFilters and every original selected column are preserved in source.json. Workbook locators use one-based row positions within those selections. Source hashes pin the complete accepted extracted CSVs. The [finance coverage record](../../../finance/evidence/coverage/README.md) identifies the immutable release.\n\n"  # noqa: E501 -- reader-facing prose
    for e in data["evidence"]:
        readme += f"- {e['id']}: [{e['path'].split('/')[-1]}](../../../../{e['path'].removeprefix('docs/')}) — {len(e['rows'])} selected rows.\n"  # noqa: E501 -- reader-facing prose
    readme += "\nCore and industrial systems remain separate. Terminal invoice/payable master values are not used as month-end balances. Bank evidence is modeled clearing, not an independent statement.\n\nBuild: `python tools/legal_gaps/reconciliations.py build`. Check complete regenerated JSON/Markdown/workbook bytes and SQLite schema/rows: `python tools/legal_gaps/reconciliations.py validate`. Render native workbooks: `python tools/legal_gaps/reconciliations.py render`. SQLite physical headers may vary across engines; complete logical contents must match.\n"  # noqa: E501 -- reader-facing prose
    # Three parent levels reach docs from the reconciliation directory.
    readme = readme.replace("](../../../../finance/", "](../../../finance/")
    (out / "README.md").write_text(readme)
    (out / "WORKED.md").write_text(worked)
    dump(
        out / "manifest.json",
        dict(
            status=STATUS,
            source_pins=[{k: e[k] for k in ["id", "path", "sha256"]} for e in data["evidence"]],
            files={
                p.name: sha(p)
                for p in sorted(out.iterdir())
                if p.is_file() and p.name != "manifest.json"
            },
        ),
    )


def db_contents(path):
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("SQLite integrity failure")
        return (
            db.execute(
                "SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name"
            ).fetchall(),
            db.execute("SELECT * FROM records ORDER BY kind,id").fetchall(),
            db.execute("PRAGMA user_version").fetchall(),
            db.execute("PRAGMA application_id").fetchall(),
        )


def validate(root=ROOT):
    target = root / DEST
    with tempfile.TemporaryDirectory() as temp:
        generated = Path(temp)
        generate(root, generated)
        expected = json.loads((generated / "manifest.json").read_text())
        saved = json.loads((target / "manifest.json").read_text())
        if (
            saved["source_pins"] != expected["source_pins"]
            or saved["status"] != STATUS
            or set(saved["files"]) != set(expected["files"])
        ):
            raise ValueError("Manifest source or coverage drift")
        for name in expected["files"]:
            if sha(target / name) != saved["files"][name]:
                raise ValueError("Saved hash drift " + name)
            if name.endswith(".sqlite3"):
                if db_contents(target / name) != db_contents(generated / name):
                    raise ValueError("SQLite full contents drift")
            elif (target / name).read_bytes() != (generated / name).read_bytes():
                raise ValueError("Generated drift " + name)
    print(
        "PASS: five bounded workpapers, nine checks, complete selected rows, source pins and all derivatives"  # noqa: E501 -- reader-facing prose
    )


def validate_qa(root=ROOT):
    target = root / DEST
    receipt = json.loads((target / "qa/REVIEW.json").read_text())
    if receipt["status"] != "MANUAL_REVIEW_PASS_DRAFT_DESIGN":
        raise ValueError("Manual visual review remains incomplete")
    if {r["mode"] for r in receipt["records"]} != {"blank", "worked"}:
        raise ValueError("Workbook review coverage incomplete")
    for record in receipt["records"]:
        if record["workbook_sha256"] != sha(target / (record["mode"] + ".xlsx")):
            raise ValueError("Visual review workbook drift")
        if len(record["pages"]) != 7:
            raise ValueError("Expected every worksheet as a reviewed native page")
        for page in record["pages"]:
            if sha(root / page["path"]) != page["sha256"]:
                raise ValueError("Retained visual evidence drift")
    print("PASS: exact two workbooks / 14 sheets / 14 manually reviewed native pages")


def render(root=ROOT):
    import fitz
    from PIL import Image

    qa = root / DEST / "qa"
    qa.mkdir(exist_ok=True)
    records = []
    with tempfile.TemporaryDirectory() as temp:
        for mode in ["blank", "worked"]:
            path = root / DEST / (mode + ".xlsx")
            subprocess.run(
                [
                    "libreoffice",
                    "-env:UserInstallation=" + Path(temp, "profile").as_uri(),
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    temp,
                    str(path),
                ],
                check=True,
                capture_output=True,
            )
            doc = fitz.open(Path(temp, mode + ".pdf"))
            pages = []
            for n, page in enumerate(doc):
                pix = page.get_pixmap(matrix=fitz.Matrix(1.3, 1.3))
                out = qa / f"{mode}-{n + 1:02}.png"
                Image.frombytes("RGB", [pix.width, pix.height], pix.samples).save(out)
                pages.append(dict(path=str(out.relative_to(root)), sha256=sha(out)))
            records.append(dict(mode=mode, workbook_sha256=sha(path), pages=pages))
    dump(qa / "REVIEW.json", dict(status="RENDERED_REQUIRES_MANUAL_REVIEW", records=records))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build", "validate", "render", "qa-check"])
    args = parser.parse_args()
    if args.command == "build":
        generate(ROOT, ROOT / DEST)
    elif args.command == "validate":
        validate()
    elif args.command == "qa-check":
        validate_qa()
    else:
        render()
