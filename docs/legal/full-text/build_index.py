"""Index complete legal source editions without altering their source records."""
# ruff: noqa: E501 -- long literals are publication text and HTML templates.

import hashlib
import html
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def relative(path):
    return quote(os.path.relpath(ROOT / path, HERE), safe="/-_.")


def build():
    scope = json.loads((HERE / "SOURCE_MANIFEST.json").read_text())
    rendered = json.loads((HERE / "render-manifest.json").read_text())
    artifacts = {row["id"]: row for row in rendered["artifacts"]}
    if set(artifacts) != {row["id"] for row in scope["records"]}:
        raise ValueError("Full source edition coverage mismatch")
    with tempfile.TemporaryDirectory(prefix=".index-", dir=HERE) as temporary:
        dbpath = Path(temporary) / "full-text.sqlite3"
        db = sqlite3.connect(dbpath)
        db.executescript("""
            PRAGMA foreign_keys=ON;
            CREATE TABLE source_document (
                id TEXT PRIMARY KEY, family TEXT NOT NULL, title TEXT NOT NULL,
                markdown_path TEXT NOT NULL UNIQUE, source_sha256 TEXT NOT NULL,
                source_revision TEXT NOT NULL, status_json TEXT NOT NULL,
                complete_markdown TEXT NOT NULL);
            CREATE TABLE publication (
                source_id TEXT PRIMARY KEY REFERENCES source_document(id),
                status TEXT NOT NULL, pdf_path TEXT NOT NULL, pdf_sha256 TEXT NOT NULL,
                html_path TEXT NOT NULL, html_sha256 TEXT NOT NULL, pages INTEGER NOT NULL);
            CREATE VIRTUAL TABLE source_search USING fts5(id UNINDEXED,title,complete_markdown,
                content='source_document',content_rowid='rowid');
        """)
        lines = [
            "# Full-length legal source editions",
            "",
            "**Draft designs — exact-file review pending.** Every selected source is reproduced in full. These are complete editions of the available records: a source that is itself a summary, term sheet, proposal, policy or index retains that character. Missing agreements and execution evidence remain missing; publication supplies no new terms or approvals.",
            "",
            "Open a PDF below to read the complete record. The HTML contains the same full text and can be opened locally. The Markdown link is the original controlling source, not another summary.",
            "",
            "[Source manifest](SOURCE_MANIFEST.json) · [Artifact hashes](render-manifest.json) · [Source audit](SOURCE_AUDIT.md) · [Missing instruments and source conflicts](../../reader/transactions/RECONCILIATION.md) · [Searchable full-text database](full-text.sqlite3)",
            "",
            f"Source revision: `{scope['source_revision']}`. Prior approved PDFs retain their bytes and remain linked in the [original source inventory](../../reader/transactions/README.md).",
            "",
        ]
        browser_rows = []
        family = None
        total_pages = 0
        for row in scope["records"]:
            item = artifacts[row["id"]]
            source = ROOT / row["source"]
            if digest(source) != row["source_sha256"]:
                raise ValueError("Source changed: " + row["source"])
            for kind in ("pdf", "html"):
                if digest(ROOT / item[kind]) != item[kind + "_sha256"]:
                    raise ValueError("Artifact changed: " + item[kind])
            db.execute(
                "INSERT INTO source_document VALUES(?,?,?,?,?,?,?,?)",
                (
                    row["id"],
                    row["family"],
                    row["title"],
                    row["source"],
                    row["source_sha256"],
                    scope["source_revision"],
                    json.dumps(row["source_status_verbatim"]),
                    source.read_text(),
                ),
            )
            db.execute(
                "INSERT INTO publication VALUES(?,?,?,?,?,?,?)",
                (
                    row["id"],
                    scope["status"],
                    item["pdf"],
                    item["pdf_sha256"],
                    item["html"],
                    item["html_sha256"],
                    item["pages"],
                ),
            )
            if row["family"] != family:
                family = row["family"]
                lines += [
                    "## " + family.replace("-", " ").title(),
                    "",
                    "| Complete source record | PDF | Pages | HTML | Markdown |",
                    "|---|---|---:|---|---|",
                ]
            title = row["title"].replace("|", "\\|")
            lines.append(
                f"| {title} | [Read]({relative(item['pdf'])}) | {item['pages']} | [Open]({relative(item['html'])}) | [Source]({relative(row['source'])}) |"
            )
            browser_rows.append(
                "<tr><td>"
                + html.escape(row["family"])
                + "</td><td>"
                + html.escape(row["title"])
                + '</td><td><a href="'
                + relative(item["pdf"])
                + '">PDF</a></td><td>'
                + str(item["pages"])
                + '</td><td><a href="'
                + relative(item["html"])
                + '">HTML</a></td><td><a href="'
                + relative(row["source"])
                + '">Markdown</a></td></tr>'
            )
            total_pages += item["pages"]
        db.execute("INSERT INTO source_search(source_search) VALUES('rebuild')")
        db.commit()
        db.execute("VACUUM")
        db.close()
        dbpath.replace(HERE / "full-text.sqlite3")
    lines += [
        "",
        "## Verification and review",
        "",
        "[Delivery and correction record](CLOSEOUT.md) · [Exact visual QA manifest](QA_MANIFEST.json)",
        "",
        f"This edition contains **{len(artifacts)} complete source documents / {total_pages} PDF pages**. The database stores the complete original Markdown, its exact hash and revision, and the corresponding PDF/HTML paths and hashes.",
        "",
        "Build with `python docs/legal/full-text/build.py` then `python docs/legal/full-text/build_index.py`. Validate with `python docs/legal/full-text/validate.py`. Completeness validation is separate from visual acceptance.",
        "",
        "The earlier 13 reading summaries are optional navigation aids. They do not fulfill full-document delivery. Their draft files remain preserved in Git history and are not substitutes for the editions above.",
        "",
    ]
    (HERE / "README.md").write_text("\n".join(lines))
    (HERE / "index.html").write_text(
        """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Full-length legal sources — review</title><style>body{font:16px/1.5 Arial,sans-serif;color:#20262a;max-width:1200px;margin:36px auto;padding:0 20px}h1{font-size:30px}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:12px;border-bottom:1px solid #d6dbde}th{background:#172025;color:white}a{color:#16557a}input{font:inherit;padding:10px;width:min(100%,500px);box-sizing:border-box;margin:12px 0}.scroll{overflow-x:auto}tr[hidden]{display:none}@media(max-width:700px){thead{display:none}tbody{display:block}tr{display:grid;grid-template-columns:1fr 1fr;padding:12px 0;border-bottom:1px solid #d6dbde}td{display:block;border:0;padding:5px 10px}td:first-child,td:nth-child(2){grid-column:1/-1}td:first-child{font-size:13px;color:#58646b}td:nth-child(2){font-weight:600}td:nth-child(4)::before{content:"Pages: "}}</style></head><body><h1>Full-length legal source editions</h1><p>Draft designs for exact-file review. Each PDF contains its complete source record. Source status is retained; summaries and proposed instruments do not become executed agreements.</p><p><a href="README.md">Source, audit and verification guide</a></p><label for="search">Find a record</label><br><input id="search" type="search" placeholder="Title or source family"><div class="scroll"><table><thead><tr><th>Family</th><th>Complete record</th><th>PDF</th><th>Pages</th><th>HTML</th><th>Source</th></tr></thead><tbody>"""
        + "".join(browser_rows)
        + """</tbody></table></div><script>document.querySelector('#search').addEventListener('input',e=>{const q=e.target.value.toLowerCase();document.querySelectorAll('tbody tr').forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q));});</script></body></html>"""
    )
    dump(
        HERE / "evidence-register.json",
        dict(
            schema_version=1,
            package_id=scope["package_id"],
            title="Complete legal source editions",
            status=scope["status"],
            scope={
                "source_revision": scope["source_revision"],
                "documents": len(artifacts),
                "pages": total_pages,
            },
            sources=[{"path": r["source"], "sha256": r["source_sha256"]} for r in scope["records"]],
            markdown="docs/legal/full-text/README.md",
            reconciliation="docs/reader/transactions/RECONCILIATION.md",
            visual_manifest="docs/legal/full-text/render-manifest.json",
            database="docs/legal/full-text/full-text.sqlite3",
        ),
    )
    print(f"Indexed {len(artifacts)} complete source documents / {total_pages} pages")


if __name__ == "__main__":
    build()
