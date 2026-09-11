"""Author the new runtime workbook with available local tooling; preserve prior reviewed bytes.

Artifact Tool was unavailable locally and its registry returned 404. The owner
authorized choosing where to run the work. This distinct successor uses the
repository's installed XlsxWriter, explicit formula caches and independent readback.
It never replaces the operations Artifact Tool publication or its acceptance tests.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import xlsxwriter
from openpyxl import load_workbook
from . import model


def build(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    source = model.load()
    result = model.export(source)
    a = source["capital"]["implementation_assumptions"]
    tables = {
        "Capacity": (
            [
                {
                    k: r[k]
                    for k in [
                        "scenario",
                        "year",
                        "site",
                        "cpu_hosts",
                        "gpu_systems",
                        "storage_shelves",
                        "racks",
                        "peak_kw",
                        "typical_synthetic_kw",
                        "equipment_cost",
                        "durable_tib",
                        "full_network_restore_hours",
                    ]
                }
                for r in result["capacity"]
            ]
        ),
        "Cash requests": [
            {
                k: r[k]
                for k in [
                    "scenario",
                    "year",
                    "facility_cash_request",
                    "hardware_cash_request",
                    "operating_cash_request",
                    "terminal_cash",
                    "gross_cash_request",
                    "net_cash_request",
                    "discounted_net_cash",
                    "funding_gap",
                ]
            }
            for r in result["finance"]["annual"]
        ],
        "Investment": [
            {
                k: r[k]
                for k in [
                    "scenario",
                    "year",
                    "colo_cash",
                    "owned_cash_before_sale",
                    "terminal_sale",
                    "owned_cash_after_sale",
                    "incremental_discounted_cost",
                    "migration_assumption",
                ]
            }
            for r in result["investment_comparison"]
        ],
        "Workforce": [
            {
                k: r[k]
                for k in [
                    "id",
                    "owner",
                    "required_fte",
                    "annual_loaded_cost",
                    "allocated_fraction",
                ]
            }
            for r in a["workforce"]["roles"]
        ],
        "Phases": [
            {
                k: r[k]
                for k in [
                    "id",
                    "start",
                    "end",
                    "cost",
                    "authorization_state",
                    "actual_completion",
                    "paid",
                ]
            }
            for r in a["phases"]
        ],
    }
    enterprise = (
        model.ROOT
        / "enterprise/generated/runtime-v1/enterprise/enterprise_annual_statements.csv"
    )
    if not enterprise.is_file():
        raise ValueError("Build integrated enterprise finance before the workbook")
    with enterprise.open() as f:
        tables["Enterprise"] = [
            {
                k: r[k]
                for k in [
                    "scenario",
                    "year",
                    "assets_usd",
                    "liabilities_usd",
                    "equity_usd",
                    "net_income_usd",
                    "ending_cash_usd",
                ]
            }
            for r in csv.DictReader(f)
            if r["entity"] == "CONSOLIDATED"
        ]
    content = hashlib.sha256(json.dumps(tables, sort_keys=True).encode()).hexdigest()
    path = output / "runtime-design-review-v1.0.0.xlsx"
    w = xlsxwriter.Workbook(path)
    w.set_properties(
        {
            "title": "Runtime estate synthetic design review",
            "author": "Sable Harbor synthetic archive",
            "created": __import__("datetime").datetime(2026, 9, 11),
        }
    )
    title = w.add_format(
        {"font_name": "Arial", "font_size": 18, "bold": True, "font_color": "#173247"}
    )
    header = w.add_format(
        {
            "font_name": "Arial",
            "font_size": 9,
            "bold": True,
            "bg_color": "#173247",
            "font_color": "white",
            "text_wrap": True,
        }
    )
    number = w.add_format({"num_format": "#,##0.00;[Red](#,##0.00)", "font_size": 9})
    text = w.add_format({"font_name": "Arial", "font_size": 9, "text_wrap": True})
    integer = w.add_format({"num_format": "0", "font_size": 9, "align": "center"})
    note = w.add_format(
        {
            "font_name": "Arial",
            "font_size": 9,
            "font_color": "#555555",
            "text_wrap": True,
        }
    )
    checks = []
    summary = w.add_worksheet("Summary")
    summary.set_column("A:A", 36)
    summary.set_column("B:D", 23)
    summary.merge_range("A1:D1", "Runtime estate design review", title)
    summary.merge_range(
        "A2:D3",
        "SYNTHETIC / UNFUNDED / PROCUREMENT PENDING. Construction: land acquired, 0% vertical, 0 kW commissioned.",
        note,
    )
    summary.write("A5", "Scenario", header)
    summary.write("B5", "base")
    summary.data_validation("B5", {"validate": "list", "source": list(a["scenarios"])})
    summary.write("A6", "Year", header)
    summary.write("B6", 2027)
    summary.data_validation(
        "B6",
        {
            "validate": "integer",
            "criteria": "between",
            "minimum": 2026,
            "maximum": 2036,
        },
    )
    summary.write("A8", "Gross cash request", text)
    base = next(
        r
        for r in result["finance"]["annual"]
        if r["scenario"] == "base" and r["year"] == 2027
    )
    summary.write_formula(
        "B8",
        "=SUMIFS('Cash requests'!G6:G49,'Cash requests'!A6:A49,B5,'Cash requests'!B6:B49,B6)",
        number,
        float(base["gross_cash_request"]),
    )
    summary.write("A9", "Land within Phase I", text)
    summary.write_number("B9", 3000000, number)
    summary.write("A10", "Phase I inclusive of land", text)
    summary.write_number("B10", 15500000, number)
    summary.write("A11", "Unspent contingency", text)
    summary.write_number("B11", 500000, number)
    summary.write("A12", "Proposed technical FTE", text)
    summary.write_number(
        "B12", result["workforce"]["colo"]["required_technical_fte"], number
    )
    summary.merge_range(
        "A15:D17",
        "Settlement of the synthetic land acquisition is unresolved. Enterprise forecast payment requests are subject to existing Treasury limits; workbook cash requirements are not proof of financing, contracts, occupied personnel or payments.",
        note,
    )
    summary.merge_range(
        "A19:D21",
        "Workbook tooling: local XlsxWriter successor; existing Artifact Tool operations workbook and source locks preserved. Formulas and caches independently verified. See identity and review manifest.",
        note,
    )
    summary.set_landscape()
    summary.set_paper(9)
    summary.fit_to_pages(1, 1)
    summary.print_area("A1:D22")
    for name, rows in tables.items():
        sheet = w.add_worksheet(name)
        fields = list(rows[0])
        last = len(fields) - 1
        sheet.merge_range(
            0, 0, 0, last, name + " — synthetic design / conditional forecast", title
        )
        sheet.merge_range(
            1,
            0,
            2,
            last,
            "No real operational evidence. Unknown funding/settlement remains explicit. Source identity "
            + content[:20],
            note,
        )
        sheet.set_row(1, 25)
        sheet.set_row(2, 18)
        sheet.set_row(4, 36)
        for col, key in enumerate(fields):
            sheet.write(4, col, key.replace("_", " "), header)
        sheet.write(4, len(fields), "Check", header)
        for n, row in enumerate(rows, 5):
            sheet.set_row(n, 28)
            for col, key in enumerate(fields):
                value = row[key]
                try:
                    numeric = (
                        float(value)
                        if value is not None and not isinstance(value, bool)
                        else None
                    )
                except (TypeError, ValueError):
                    numeric = None
                if numeric is not None:
                    sheet.write_number(
                        n,
                        col,
                        numeric,
                        integer
                        if key
                        in {
                            "year",
                            "cpu_hosts",
                            "gpu_systems",
                            "storage_shelves",
                            "racks",
                            "migration_assumption",
                        }
                        else number,
                    )
                else:
                    sheet.write(n, col, "" if value is None else value, text)
            r = n + 1
            formula = {
                "Cash requests": f"=G{r}-C{r}-D{r}-E{r}",
                "Investment": f"=F{r}-D{r}+E{r}",
                "Enterprise": f"=C{r}-D{r}-E{r}",
                "Workforce": f"=MAX(0,E{r}-1)",
                "Phases": f"=G{r}",
                "Capacity": f"=MAX(0,I{r}-H{r})",
            }[name]
            # Cache the actual formula result, not a blanket success value.
            expected = 0.0
            if name == "Cash requests":
                expected = (
                    float(row["gross_cash_request"])
                    - float(row["facility_cash_request"])
                    - float(row["hardware_cash_request"])
                    - float(row["operating_cash_request"])
                )
            if name == "Enterprise":
                expected = (
                    float(row["assets_usd"])
                    - float(row["liabilities_usd"])
                    - float(row["equity_usd"])
                )
            formula = "=ROUND("+formula[1:]+",2)"
            expected = round(expected, 2)
            sheet.write_formula(n, len(fields), formula, number, expected)
            checks.append((name, n + 1, len(fields) + 1, formula, expected))
        sheet.set_column(0, 0, 23)
        sheet.set_column(1, len(fields), 17)
        if name == "Phases":
            sheet.set_column(4, 4, 34)
        if name == "Workforce":
            sheet.set_column(0, 1, 38)
        sheet.freeze_panes(5, 2)
        sheet.autofilter(4, 0, len(rows) + 4, last)
        sheet.set_landscape()
        sheet.set_paper(8)
        sheet.fit_to_pages(1, 1)
        sheet.repeat_rows(0, 4)
        sheet.print_area(0, 0, len(rows) + 4, len(fields))
        sheet.set_footer("&LSource-controlled synthetic design&RPage &P of &N")
    w.close()
    values = load_workbook(path, data_only=True)
    formulas = load_workbook(path, data_only=False)
    for name, row, col, formula, expected in checks:
        if (
            formulas[name].cell(row, col).value != formula
            or abs(values[name].cell(row, col).value - expected) > 0.0001
        ):
            raise ValueError("Workbook formula/cache mismatch")
    for name, rows in tables.items():
        for n, row in enumerate(rows, 6):
            for col, value in enumerate(row.values(), 1):
                actual = values[name].cell(n, col).value
                if value is None:
                    if actual not in (None, ""):
                        raise ValueError("Unknown workbook value was fabricated")
                else:
                    try:
                        if abs(float(actual) - float(value)) > 0.0001:
                            raise ValueError("Workbook numeric source mismatch")
                    except (TypeError, ValueError):
                        if str(actual) != str(value):
                            raise ValueError("Workbook source cell mismatch")
    manifest = {
        "source_content_id": content,
        "runtime_source_sha256": result["source_sha256"],
        "enterprise_source_sha256": hashlib.sha256(enterprise.read_bytes()).hexdigest(),
        "workbook_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "tooling": "XlsxWriter distinct runtime successor; prior Artifact Tool workbook preserved",
        "formula_checks": len(checks),
        "sheets": values.sheetnames,
        "visual_review_record": "../VISUAL_REVIEW.md",
    }
    (output / "review_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


def verify(output):
    import tempfile

    output = Path(output)
    retained = json.loads((output / "review_manifest.json").read_text())
    with tempfile.TemporaryDirectory() as temp:
        build(temp)
        reproduced = json.loads((Path(temp) / "review_manifest.json").read_text())
    if retained != reproduced:
        raise ValueError(
            "Retained runtime workbook does not reproduce from current source"
        )
    if (
        hashlib.sha256(
            (output / "runtime-design-review-v1.0.0.xlsx").read_bytes()
        ).hexdigest()
        != retained["workbook_sha256"]
    ):
        raise ValueError("Retained runtime workbook hash mismatch")
    print("Retained runtime workbook and source-cell/formula checks reproduce")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    (verify if args.verify else build)(args.output)
