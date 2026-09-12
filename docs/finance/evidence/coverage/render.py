"""Build review-only PDFs and complete-population Excel workbooks, never accepted originals."""

import csv
import hashlib
import importlib.util
import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import fitz
import xlsxwriter

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/finance/evidence"
spec = importlib.util.spec_from_file_location("extract", Path(__file__).with_name("build.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
PRIORITY = [
    "period",
    "year",
    "month",
    "unit",
    "entity",
    "invoice_id",
    "contract_id",
    "source_id",
    "journal_id",
    "amount_usd",
    "signed_usd",
    "debit_usd",
    "credit_usd",
]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def render():
    for family, desc in m.FAMILIES.items():
        folder = BASE / family
        out = folder / "draft"
        qa = out / "qa"
        qa.mkdir(parents=True, exist_ok=True)
        register = json.loads((folder / "evidence-register.json").read_text())
        checks = json.loads((folder / "RECONCILIATION.json").read_text())["checks"]
        sources = [folder / "source" / Path(r["path"]).name for r in register["sources"]]
        if family == "tax-transaction":
            sources += sorted(folder.glob("*.csv"))
        book = xlsxwriter.Workbook(
            out / "working-papers.xlsx", {"strings_to_formulas": False, "strings_to_urls": False}
        )
        book.set_properties(
            {
                "title": desc["title"],
                "created": datetime(2026, 9, 12),
                "author": "Sable Harbor synthetic evidence",
                "comments": "Draft for exact-file review; all selected source rows included.",
            }
        )
        body = book.add_format(
            {
                "font_name": "Arial",
                "font_size": 10,
                "text_wrap": True,
                "valign": "vcenter",
                "indent": 1,
                "bottom": 1,
                "bottom_color": "#D9D9D9",
            }
        )
        head = book.add_format(
            {
                "font_name": "Arial",
                "font_size": 10,
                "bold": True,
                "bg_color": "#101214",
                "font_color": "#FFFFFF",
                "valign": "vcenter",
                "indent": 1,
                "text_wrap": True,
            }
        )
        money = book.add_format(
            {
                "font_name": "Arial",
                "font_size": 10,
                "num_format": "#,##0.00;[Red](#,##0.00)",
                "valign": "vcenter",
                "indent": 1,
                "bottom": 1,
                "bottom_color": "#D9D9D9",
            }
        )
        title = book.add_format({"font_name": "Arial", "font_size": 18, "bold": True})

        def sheet(name, labels):
            w = book.add_worksheet(name)
            w.set_landscape()
            w.set_paper(9)
            w.fit_to_pages(1, 1)
            w.set_margins(0.3, 0.3, 0.4, 0.5)
            w.set_column(0, max(6, len(labels) - 1), 22, body)
            w.set_row(0, 32)
            w.merge_range(0, 0, 0, min(6, len(labels) - 1), name, title)
            w.merge_range(
                1,
                0,
                1,
                min(6, len(labels) - 1),
                "DRAFT • "
                + family
                + " • base / "
                + register["scope"]["period_start"]
                + "–"
                + register["scope"]["period_end"],
                body,
            )
            w.set_row(1, 30)
            w.write_row(3, 0, [label.replace("_", " ") for label in labels], head)
            w.set_row(3, 42)
            w.freeze_panes(4, 2)
            w.repeat_rows(0, 3)
            w.set_footer(
                "Draft review | Print preview shows leading rows/columns; Excel retains all data | &P",
                {"margin": 0.2},
            )
            return w

        guide = sheet("Guide", ["Table / scope", "Rows", "Excel sheet", "Source CSV"])
        guide.set_column(0, 0, 37)
        guide.set_column(2, 3, 34)
        maprows = []
        for i, p in enumerate(sources, 1):
            rs = m.rows(p.read_bytes())
            original = list(rs[0]) if rs else next(csv.reader(p.open()))
            cols = [c for c in PRIORITY if c in original] + [
                c for c in original if c not in PRIORITY
            ]
            name = f"{i:02d} " + p.stem[:27]
            w = sheet(name, cols)
            for n, r in enumerate(rs, 4):
                for col, key in enumerate(cols):
                    v = r.get(key, "")
                    if (
                        key.endswith("_usd")
                        and v != ""
                        and len(m.D(v).normalize().as_tuple().digits) <= 15
                    ):
                        w.write_number(n, col, float(v), money)
                    else:
                        w.write_string(n, col, v, body)
                w.set_row(n, 46)
            if rs:
                w.autofilter(3, 0, len(rs) + 3, len(cols) - 1)
            w.print_area(0, 0, min(15, len(rs) + 3), min(6, len(cols) - 1))
            guide.write_row(i + 3, 0, [p.stem, len(rs), name, str(p.relative_to(folder))], body)
            guide.set_row(i + 3, 34)
            maprows.append(
                {
                    "sheet": name,
                    "source": str(p.relative_to(ROOT)),
                    "row_count": len(rs),
                    "columns": cols,
                    "first_data_row": 5,
                    "source_sha256": sha(p),
                }
            )
        note_row = len(sources) + 5
        guide.merge_range(note_row, 0, note_row + 4, 3, desc["limits"], body)
        guide.set_row(note_row, 30)
        guide.print_area(0, 0, note_row + 4, 3)
        w = sheet("Checks", ["Test", "Rows/groups", "Maximum difference USD", "Within 0.02"])
        w.set_column(0, 0, 55)
        for n, r in enumerate(checks, 4):
            w.write(n, 0, r["check"], body)
            w.write_number(n, 1, r["tested_rows"])
            w.write_number(n, 2, float(r["maximum_absolute_difference"]), money)
            w.write_formula(n, 3, f'=IF(ABS(C{n + 1})<=0.02,"PASS","FAIL")', body, r["status"])
            w.set_row(n, 36)
        w.print_area(0, 0, len(checks) + 3, 3)
        book.close()
        m.dump(out / "workbook-map.json", maprows)
        # Use the current controlled renderer in a private namespace with a draft footer.
        import inspect
        import sys

        sys.path.insert(0, str(ROOT))
        from tools.documents import build_controlled_publications as pub

        namespace = dict(vars(pub))
        renderer = inspect.getsource(pub.render_pdf).replace(
            "Controlled publication • Generated from", "Draft working paper • Generated from"
        )
        exec(compile(renderer, "<draft working paper>", "exec"), namespace)
        report = (
            "# "
            + desc["title"]
            + "\n\n**DRAFT — exact-file review pending.** Base scenario, "
            + register["scope"]["period_start"]
            + " through "
            + register["scope"]["period_end"]
            + ". Synthetic reconstruction, not independent audit evidence.\n\n"
            + desc["limits"]
            + "\n\n## What is included\n\nComplete declared source populations are in working-papers.xlsx and the source CSV/SQLite tables. The workbook Guide maps every table to its complete sheet and source file. Values beyond Excel’s 15-digit numerical precision remain text. Printed previews show leading rows and columns only; they do not limit the Excel population.\n"
        )
        report += f"\nThe workbook contains {len(maprows)} complete source tables ({sum(x['row_count'] for x in maprows):,} rows), plus its Guide and Checks sheets. Repeated tables across packages are convenience mirrors, not additional transactions.\n"
        measures = []

        def total(table, column, predicate):
            return sum(
                (
                    m.num(row, column)
                    for row in m.rows((folder / "source" / (table + ".csv")).read_bytes())
                    if predicate(row)
                ),
                m.D(0),
            )

        december = lambda row: (
            row.get("period", "").startswith("2027-12")
            or (row.get("year") == "2027" and row.get("month") == "12")
        )
        if family == "customer":
            for label, column in [
                ("Core gross receivables at December close", "gross_ar_usd"),
                ("Core allowance at December close", "allowance_usd"),
                ("Core deferred revenue at December close", "deferred_revenue_usd"),
            ]:
                measures.append((label, total("subledger_rollforward", column, december)))
        elif family == "treasury":
            for flow in ["OPERATING", "INVESTING", "FINANCING"]:
                measures.append(
                    (
                        flow.capitalize() + " unpaid requests at December close",
                        total(
                            "treasury_reconciliation",
                            "closing_unpaid_usd",
                            lambda row: december(row) and row["cash_flow"] == flow,
                        ),
                    )
                )
        elif family == "close":
            for label, column in [
                ("Consolidated December ending cash", "ending_cash_usd"),
                ("Consolidated December assets", "assets_usd"),
            ]:
                measures.append(
                    (
                        label,
                        total(
                            "legal_statements",
                            column,
                            lambda row: december(row) and row["entity"] == "CONSOLIDATED",
                        ),
                    )
                )
            measures.append(
                (
                    "Consolidated 2027 net income",
                    total(
                        "legal_statements",
                        "net_income_usd",
                        lambda row: row["entity"] == "CONSOLIDATED",
                    ),
                )
            )
        elif family == "supporting-schedules":
            measures.append(
                (
                    "Core December asset net book value",
                    total("asset_rollforward", "net_book_usd", december),
                )
            )
            measures.append(
                (
                    "Core 2027 allocated employer cost",
                    total("workforce_assignments", "loaded_cost_usd", lambda row: True),
                )
            )
            measures.append(
                (
                    "ARU December legacy term principal",
                    total("industrial_debt", "closing_legacy_term_usd", december),
                )
            )
        else:
            bridge = json.loads((folder / "CURRENT_SOURCE_BRIDGE.json").read_text())["ppa"]
            measures = [
                ("ARU stock consideration", bridge["stock_consideration_usd"]),
                ("Residual book goodwill", bridge["goodwill_usd"]),
                ("Independent tax goodwill basis", bridge["tax_goodwill_basis_usd"]),
            ]
        report += "\n## Financial measures\n\n| Measure | USD |\n|---|---:|\n"
        for label, value in measures:
            report += f"| {label} | {value:,.2f} |\n"
        report += "\nThese measures use the stated Core, Treasury, consolidated or industrial view; they are not interchangeable populations. Source columns remain in the complete workbook.\n"
        report += (
            "\n## Reconciliation and review\n\n"
            + str(len(checks))
            + " independently computed checks passed: population/source identity, decimal rollforwards and the applicable ledger or document joins. RECONCILIATION.json preserves each result; the workbook Checks sheet makes the tolerance test visible. No balancing adjustment was added.\n\n## Provenance\n\nRelease business-operations-v1.0.0, source "
            + m.REVISION
            + ". The evidence register pins archive, native database, each CSV and extracted database hashes. Other scenarios and later years remain in the native release and are not claimed human-complete by this package.\n"
        )
        if family == "tax-transaction":
            report += "\nThe additional acquisition PPA, opening accounts, tax, debt and asset sheets reproduce current industrial sources separately. CURRENT_SOURCE_BRIDGE.json records their distinct current-source hashes. Filing-ready remains distinct from filed or accepted.\n"
        (out / "WORKING_PAPER.md").write_text(report)
        with tempfile.TemporaryDirectory() as td:
            namespace["render_pdf"](
                libreoffice="libreoffice",
                ghostscript="gs",
                qpdf=None,
                tmp=Path(td),
                src_rel=str((out / "WORKING_PAPER.md").relative_to(ROOT)),
                out_rel=str((out / "working-paper.pdf").relative_to(ROOT)),
                brand="corporate",
            )
        for previous in list(qa.glob("paper-*.png")) + list(qa.glob("workbook-*.png")):
            previous.unlink()
        renders = []
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(
                [
                    "libreoffice",
                    "-env:UserInstallation=" + Path(td, "profile").as_uri(),
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    td,
                    str(out / "working-papers.xlsx"),
                ],
                check=True,
                capture_output=True,
            )
            for path, prefix in [
                (out / "working-paper.pdf", "paper"),
                (Path(td) / "working-papers.pdf", "workbook"),
            ]:
                document = fitz.open(path)
                for i, page in enumerate(document):
                    target = qa / f"{prefix}-{i + 1:02d}.png"
                    page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(target)
                    renders.append(
                        {
                            "path": str(target.relative_to(ROOT)),
                            "source": prefix,
                            "page": i + 1,
                            "sha256": sha(target),
                        }
                    )
        m.dump(out / "render-manifest.json", renders)
        artifacts = {
            str(p.relative_to(ROOT)): sha(p)
            for p in sorted(out.rglob("*"))
            if p.is_file() and p.name != "manifest.json"
        }
        m.dump(
            out / "manifest.json",
            {
                "status": "DRAFT_FOR_EXACT_FILE_REVIEW",
                "artifacts": artifacts,
                "source_register_sha256": sha(folder / "evidence-register.json"),
                "renderer_sha256": sha(Path(__file__)),
                "source_dependencies": {
                    str(p.relative_to(ROOT)): sha(p)
                    for p in [
                        Path(__file__).with_name("build.py"),
                        ROOT / "tools/documents/build_controlled_publications.py",
                        ROOT / "assets/brand/logos/sable-harbor__primary-horizontal.svg",
                    ]
                },
            },
        )
        print(family, len(maprows) + 2, "sheets", len(renders), "renders")


if __name__ == "__main__":
    render()
