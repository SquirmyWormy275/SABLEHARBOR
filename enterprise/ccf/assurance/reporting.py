"""Deterministic internal workbooks, scoped reports and a local read-only explorer."""

import csv
import html
import io
import json
from datetime import datetime

import xlsxwriter


def cell(value):
    value = str(value)
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


def flat_rows(report):
    for r in report["rows"]:
        for a in r["attributes"]:
            yield [
                r["framework_id"],
                r["requirement_id"],
                r["boundary_id"],
                r["category"],
                "BASELINE" if r["baseline"] else "EXTENSION",
                r["status"],
                a["id"],
                a["disposition"],
                a["objective"],
                "; ".join(a["control_ids"]),
                "; ".join(a["owner_role_ids"]),
                a["evidence_expectation"],
                "; ".join(r["blockers"] + a["issues"]),
                "; ".join(a["test_ids"]),
                r["source_id"],
                r["locator"],
                a["specification"],
            ]


HEADERS = [
    "Framework",
    "Requirement",
    "Boundary",
    "Category",
    "Selection",
    "Status",
    "Attribute",
    "Action",
    "Objective",
    "Native controls",
    "Owner roles",
    "Evidence needed",
    "Unresolved / findings",
    "Tests",
    "Source",
    "Locator",
    "Specification",
]


def csv_report(report):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(HEADERS)
    writer.writerows([cell(v) for v in row] for row in flat_rows(report))
    return stream.getvalue()


def markdown(report):
    counts = ", ".join(f"{k}: {v}" for k, v in report["summary"].items())
    return "\n".join(
        [
            "# Scoped CCF delta",
            "",
            f"**Origin:** {report['origin']}. **Audience:** internal assessment team.",
            "",
            f"Native snapshot: `{report['native_snapshot_id']}`",
            f"Catalog: `{report['catalog_digest']}`",
            "",
            "## Requirement dispositions",
            "",
            counts,
            "",
            "## Interpretation",
            "",
            "Baseline rows remain in the report: selecting an extension does not hide unfinished baseline work.",
            "Candidate reuse is a mapping hint. Only scoped, reviewed implementations and tests can support an attribute.",
            "An incomplete source inventory leaves the framework delta unresolved even if individual tests pass.",
            "Excluded rows retain their rationale and blockers; they are not reported as covered.",
            "",
            "The workbook and explorer contain internal information. Customer statements require a separate approved export.",
            "",
            *[f"- {x}" for x in report["limitations"]],
            "",
        ]
    )


def explorer(report):
    # Only text is interpolated, escaped before insertion. No input enters script or attributes.
    body = []
    visible = [0, 1, 2, 4, 5, 7]
    for values in flat_rows(report):
        cells = "".join(f"<td>{html.escape(str(values[i]))}</td>" for i in visible)
        details = "".join(
            f"<dt>{HEADERS[i]}</dt><dd>{html.escape(str(v))}</dd>"
            for i, v in enumerate(values)
            if i not in visible
        )
        body.append(
            "<tr>"
            + cells
            + "<td><details><summary>View workpaper</summary><dl>"
            + details
            + "</dl></details></td></tr>"
        )
    return (
        """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CCF assessment workbench</title><style>
body{font:16px system-ui;margin:2rem;color:#17283b;background:#f7f9fc}h1{margin-bottom:.4rem}
input,select{font:inherit;padding:.5rem;max-width:95%;margin:.5rem}table{border-collapse:collapse;background:white}
th,td{text-align:left;vertical-align:top;border:1px solid #c8d3df;padding:.6rem;min-width:8rem}
td{max-width:18rem;overflow-wrap:anywhere}details{min-width:12rem}summary{cursor:pointer}dt{font-weight:bold;margin-top:.6rem}dd{margin:.2rem 0}
th{background:#173954;color:white;position:sticky;top:0}.scroll{overflow:auto;max-height:72vh}
</style><h1>CCF assessment workbench</h1>
<p>Internal planning view. Framework mapping does not establish conformity. Synthetic results are examples.</p>
<label>Search controls, requirements or findings <input id="search" type="search"></label>
<label>Selection <select id="selection"><option value="">All</option><option>BASELINE</option><option>EXTENSION</option></select></label>
<label>Framework <select id="framework"><option value="">All</option></select></label>
<p id="count" aria-live="polite"></p><div class="scroll"><table><thead><tr>"""
        + "".join(f"<th scope='col'>{HEADERS[i]}</th>" for i in visible)
        + "<th scope='col'>Details</th>"
        + "</tr></thead><tbody>"
        + "".join(body)
        + """</tbody></table></div>
<script>
const rows=Array.from(document.querySelectorAll('tbody tr'));
const search=document.getElementById('search'), selection=document.getElementById('selection'), framework=document.getElementById('framework');
Array.from(new Set(rows.map(r=>r.cells[0].textContent))).sort().forEach(f=>{const o=document.createElement('option');o.textContent=f;framework.append(o)});
function filter(){let shown=0;rows.forEach(r=>{r.hidden=!(r.textContent.toLowerCase().includes(search.value.toLowerCase())&&(!selection.value||r.cells[3].textContent===selection.value)&&(!framework.value||r.cells[0].textContent===framework.value));if(!r.hidden)shown++});document.getElementById('count').textContent=shown+' attribute rows shown'}
search.addEventListener('input',filter);selection.addEventListener('change',filter);framework.addEventListener('change',filter);filter();
</script></html>"""
    )


def workbook(path, report, catalog, assessment, native):
    with xlsxwriter.Workbook(
        path, {"strings_to_formulas": False, "strings_to_urls": False}
    ) as book:
        book.set_properties(
            {"title": "Internal CCF assessment and delta", "created": datetime(2026, 9, 11)}
        )
        heading = book.add_format(
            {"bold": True, "bg_color": "#173954", "font_color": "white", "text_wrap": True}
        )
        wrapped = book.add_format({"text_wrap": True, "valign": "top"})

        def sheet(name, headers, rows):
            ws = book.add_worksheet(name)
            ws.freeze_panes(1, 1)
            ws.write_row(0, 0, headers, heading)
            count = 0
            for count, row in enumerate(rows, 1):
                for column, value in enumerate(row):
                    ws.write_string(count, column, str(value), wrapped)
            ws.autofilter(0, 0, count, len(headers) - 1)
            ws.set_column(0, len(headers) - 1, 28)
            ws.set_row(0, 32)

        sheet(
            "Read me",
            ["Item", "Value"],
            [
                ["Audience", "INTERNAL; not a customer assurance report"],
                ["Origin", report["origin"]],
                ["Scope", json.dumps(report["scope"], sort_keys=True)],
                ["Native snapshot", report["native_snapshot_id"]],
                ["Catalog digest", report["catalog_digest"]],
                *[["Limitation", x] for x in report["limitations"]],
            ],
        )
        sheet("Delta", HEADERS, flat_rows(report))
        sheet(
            "Native controls",
            ["Control", "Version", "Definition"],
            (
                [r["id"], r["version"], json.dumps(r["data"], sort_keys=True)]
                for r in native["records"]
                if r["kind"] == "control"
            ),
        )
        sheet(
            "Sources",
            ["Source", "Publisher", "Edition", "URL", "Access", "Content hash", "Rights"],
            (
                [
                    s.id,
                    s.publisher,
                    s.edition,
                    s.url,
                    s.access,
                    s.content_sha256 or "UNAVAILABLE",
                    s.rights_note,
                ]
                for s in catalog.sources
            ),
        )
        sheet(
            "Mappings",
            ["Mapping", "Requirement", "Control", "Attributes", "Rationale", "Uncovered", "Review"],
            (
                [
                    m.id,
                    m.requirement_id,
                    m.control_id,
                    "; ".join(m.attribute_ids),
                    m.rationale,
                    m.uncovered,
                    str(m.review.reviewed_on) if m.review else "PENDING",
                ]
                for m in catalog.mappings
            ),
        )
        sheet(
            "Evidence requests",
            ["Request", "Requirement", "Attribute", "Evidence expectation"],
            (
                [f"ER-{r.id}-{a.id}", r.id, a.id, a.evidence_expectation]
                for r in catalog.requirements
                for a in r.attributes
            ),
        )
        sheet(
            "Evidence index",
            [
                "Evidence",
                "Hash",
                "Boundary",
                "Period start",
                "Period end",
                "Expires",
                "Origin",
                "Classification",
            ],
            (
                [
                    e.id,
                    e.sha256,
                    e.boundary_id,
                    e.period_start,
                    e.period_end,
                    e.expires_on,
                    e.origin,
                    e.classification,
                ]
                for e in assessment.evidence
            ),
        )
        sheet(
            "Tests",
            [
                "Test",
                "Requirement",
                "Implementation",
                "Mode",
                "Result",
                "Evidence",
                "Method",
                "Selection rationale",
                "Findings",
            ],
            (
                [
                    t.id,
                    t.requirement_id,
                    t.implementation_id,
                    t.mode,
                    t.result,
                    "; ".join(t.evidence_ids),
                    t.procedure,
                    t.selection_rationale,
                    "; ".join(t.findings),
                ]
                for t in assessment.tests
            ),
        )
