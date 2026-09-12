"""Generate source-bound legal dossiers and optional review-only PDF/HTML renders."""

from pathlib import Path
import argparse
import hashlib
import html
import json
import os
import sqlite3

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p, v):
    p.write_text(json.dumps(v, indent=2, ensure_ascii=False) + "\n")


def link(p, target):
    return os.path.relpath(ROOT / target, p.parent).replace(os.sep, "/")


def build(render=False):
    config = json.loads((HERE / "dossier_source.json").read_text())
    dossiers = config["dossiers"]
    all_sources = set()
    for folder in ("commercial", "corporate", "assets-rights"):
        base = ROOT / "docs/legal/evidence" / folder
        selected = [d for d in dossiers if d["folder"] == folder]
        sourcepaths = sorted(
            {s for d in selected for s in d["sources"]}
            | {"docs/reader/transactions/dossier_source.json"}
        )
        all_sources.update(sourcepaths)
        index = [
            "# "
            + {
                "commercial": "Commercial contracts and service obligations",
                "corporate": "Corporate, capital and workforce records",
                "assets-rights": "Acquisitions, assets, hosts and tenure",
            }[folder],
            "",
            "**Source-bound reading package.** The individual dossiers below contain concrete terms from accepted source documents. They are reader summaries with clause-level source links, not replacement agreements, new legal opinions or invented signatures. New PDF designs remain review-only.",
            "",
            "[Structured package identity](evidence-register.json) · [Complete legal inventory](../../../reader/transactions/README.md)",
            "",
            "| Dossier | Source state |",
            "|---|---|",
        ]
        for d in selected:
            p = base / (d["id"] + ".md")
            lines = [
                "# " + d["title"],
                "",
                f"**Reader record:** {d['id']} · **Reviewed:** September 12, 2026",
                "",
                f"**Source state:** {d['status']}",
                "",
                "This is a source-bound reading summary. The linked full instruments retain their own authority, effective dates and limitations. No new party, signature, payment, legal term or filing is established here.",
                "",
            ]
            for c in d["clauses"]:
                lines += [
                    "## " + c["label"],
                    "",
                    c["text"] + " [Source](" + link(p, c["source"]) + ").",
                    "",
                ]
            lines += [
                "## Accounting and record trace",
                "",
                d["accounting"],
                "",
                "**Native identifiers / tables:** "
                + ", ".join("`" + x + "`" for x in d["native_keys"])
                + ".",
                "",
                "## Missing evidence and limits",
                "",
                d["missing"],
                "",
                "## Full source records",
                "",
            ]
            lines += ["- [" + s + "](" + link(p, s) + ")" for s in d["sources"]]
            lines += [
                "",
                "[Package index](README.md) · [Source/section database](../../../reader/transactions/legal-records.sqlite3)",
                "",
                "A draft PDF can be generated with `python docs/reader/transactions/build_readers.py --render`. Its exact bytes require owner review; the source summary does not approve the design.",
            ]
            p.write_text("\n".join(lines) + "\n")
            index.append(f"| [{d['title']}]({d['id']}.md) | {d['status']} |")
        index += [
            "",
            "## How to use this package",
            "",
            "Read the selected dossier, open the cited clause in its full source, then follow the native key into the relevant accounting or facility register. A figure repeated here is not independent corroboration. The complete source section text and missing-record dispositions are queryable in the legal SQLite index.",
            "",
            "Use `SELECT * FROM reading_dossier` and `SELECT * FROM dossier_clause` in `docs/reader/transactions/legal-records.sqlite3`. Financial row-level populations remain in the native finance releases; this database stores document lineage only.",
            "",
            "No draft design is accepted through this Markdown publication. Rendered drafts and exact-file manifests are retained separately on the review branch.",
        ]
        (base / "README.md").write_text("\n".join(index) + "\n")
        dump(
            base / "evidence-register.json",
            {
                "schema_version": 1,
                "package_id": "SH-LEGAL-" + folder.upper() + "-001",
                "title": index[0][2:],
                "status": "SOURCE_BOUND_READER_DERIVATIVES",
                "scope": {
                    "source_revision": json.loads((HERE / "source_scope.json").read_text())[
                        "base_sha"
                    ],
                    "review_date": "2026-09-12",
                },
                "sources": [{"path": s, "sha256": sha(ROOT / s)} for s in sourcepaths],
                "markdown": str((base / "README.md").relative_to(ROOT)),
                "reconciliation": "docs/reader/transactions/RECONCILIATION.md",
                "visual_manifest": None,
                "database": "docs/reader/transactions/legal-records.sqlite3",
                "dossiers": [
                    {
                        "id": d["id"],
                        "title": d["title"],
                        "status": d["status"],
                        "markdown": str((base / (d["id"] + ".md")).relative_to(ROOT)),
                        "native_keys": d["native_keys"],
                        "pdf_disposition": "NEW_DESIGN_AWAITING_EXACT_REVIEW",
                    }
                    for d in selected
                ],
            },
        )
    db = sqlite3.connect(HERE / "legal-records.sqlite3")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript(
        "DROP TABLE IF EXISTS dossier_clause; DROP TABLE IF EXISTS reading_dossier; CREATE TABLE reading_dossier(id TEXT PRIMARY KEY,title TEXT NOT NULL,status TEXT NOT NULL,markdown TEXT NOT NULL,native_keys_json TEXT NOT NULL); CREATE TABLE dossier_clause(dossier_id TEXT NOT NULL REFERENCES reading_dossier(id),ordinal INTEGER NOT NULL,label TEXT NOT NULL,text TEXT NOT NULL,source_path TEXT NOT NULL,source_sha256 TEXT NOT NULL,PRIMARY KEY(dossier_id,ordinal));"
    )
    for d in dossiers:
        db.execute(
            "INSERT INTO reading_dossier VALUES(?,?,?,?,?)",
            (
                d["id"],
                d["title"],
                d["status"],
                f"docs/legal/evidence/{d['folder']}/{d['id']}.md",
                json.dumps(d["native_keys"]),
            ),
        )
        for n, c in enumerate(d["clauses"], 1):
            db.execute(
                "INSERT INTO dossier_clause VALUES(?,?,?,?,?,?)",
                (d["id"], n, c["label"], c["text"], c["source"], sha(ROOT / c["source"])),
            )
    db.commit()
    assert not db.execute("PRAGMA foreign_key_check").fetchall()
    db.execute("VACUUM")
    db.close()
    if render:
        render_drafts(dossiers)
    print(f"{len(dossiers)} source-bound reading dossiers; render={render}")


def render_drafts(dossiers):
    from playwright.sync_api import sync_playwright
    import fitz
    import base64

    logo = ROOT / "assets/brand/logos/sable-harbor__primary-horizontal.png"
    logo_uri = "data:image/png;base64," + base64.b64encode(logo.read_bytes()).decode()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"]
        )
        for folder in ("commercial", "corporate", "assets-rights"):
            base = ROOT / "docs/legal/evidence" / folder
            out = base / "drafts"
            out.mkdir(exist_ok=True)
            manifest = {
                "status": "DRAFT_FOR_EXACT_FILE_REVIEW",
                "approved": False,
                "source_revision": json.loads((HERE / "source_scope.json").read_text())["base_sha"],
                "logo": {"path": str(logo.relative_to(ROOT)), "sha256": sha(logo)},
                "artifacts": [],
            }
            links = []
            for d in [x for x in dossiers if x["folder"] == folder]:
                body = f'<header><img src="{logo_uri}"><span>LEGAL RECORDS / READER EDITION</span></header><p class="draft">DRAFT VISUAL • SOURCE STATUS RETAINED • NOT AN EXECUTED ORIGINAL</p><h1>{html.escape(d["title"])}</h1><p class="meta">{d["id"]} · Reviewed September 12, 2026</p><p class="state">{html.escape(d["status"])}</p>'
                for c in d["clauses"]:
                    body += f"<section><h2>{html.escape(c['label'])}</h2><p>{html.escape(c['text'])}</p></section>"
                body += f'<section><h2>Accounting and record trace</h2><p>{html.escape(d["accounting"])}</p><p class="keys">{html.escape(" · ".join(d["native_keys"]))}</p></section><section><h2>Missing evidence and limits</h2><p>{html.escape(d["missing"])}</p></section><section><h2>Controlling source paths</h2>'
                for s in d["sources"]:
                    body += f'<p class="source">{html.escape(s)}</p>'
                body += "</section>"
                css = """@page{size:Letter;margin:0.6in 0.65in 0.65in}*{box-sizing:border-box}body{font-family:Arial,sans-serif;color:#20262a;font-size:10.5pt;line-height:1.4;margin:0}header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #363d40;padding-bottom:12px;margin-bottom:12px}header img{width:210px;height:auto}header span{font-size:8pt;letter-spacing:.8px;color:#5c6265}h1{font-size:22pt;line-height:1.12;margin:16px 0 8px;font-weight:600}h2{font-size:11pt;margin:13px 0 4px}p{margin:0 0 6px}.draft{font-size:8pt;color:#735c38;letter-spacing:.35px}.meta{font-size:9pt;color:#60686d}.state{font-size:9pt;border-bottom:1px solid #d4d8db;padding-bottom:10px;margin-bottom:12px}section{break-inside:avoid}.keys,.source{font-size:8.5pt;overflow-wrap:anywhere;color:#4a5359}.source{margin:3px 0}@media screen{body{max-width:850px;margin:24px auto;padding:42px;background:white}html{background:#eceff1}}"""
                payload = (
                    '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'
                    + html.escape(d["title"])
                    + "</title><style>"
                    + css
                    + "</style><body>"
                    + body
                    + "</body></html>"
                )
                hp = out / (d["id"] + ".html")
                hp.write_text(payload)
                pp = out / (d["id"] + ".pdf")
                page = browser.new_page()
                page.set_content(payload)
                page.emulate_media(media="print")
                raw = page.pdf(
                    format="Letter",
                    print_background=True,
                    display_header_footer=True,
                    header_template="<span></span>",
                    footer_template='<div style="font-family:Arial;font-size:8px;color:#646b70;width:100%;margin:0 48px;display:flex;justify-content:space-between"><span>'
                    + d["id"]
                    + ' | Draft for exact-file review</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>',
                )
                page.close()
                pdf = fitz.open(stream=raw, filetype="pdf")
                pdf.set_metadata({})
                pdf.save(pp, garbage=4, deflate=True, no_new_id=True)
                count = len(pdf)
                pdf.close()
                manifest["artifacts"].append(
                    {
                        "id": d["id"],
                        "markdown": str((base / (d["id"] + ".md")).relative_to(ROOT)),
                        "source_sha256": sha(base / (d["id"] + ".md")),
                        "pdf": str(pp.relative_to(ROOT)),
                        "pdf_sha256": sha(pp),
                        "html": str(hp.relative_to(ROOT)),
                        "html_sha256": sha(hp),
                        "pages": count,
                    }
                )
                links.append(
                    f'<li><a href="{d["id"]}.pdf">{html.escape(d["title"])} — PDF</a> · <a href="{d["id"]}.html">HTML</a></li>'
                )
            (out / "index.html").write_text(
                '<!doctype html><meta charset="utf-8"><title>Draft legal reader review</title><h1>Draft legal reader review</h1><p>Exact-file acceptance required; no signed instruments or new terms.</p><ul>'
                + "".join(links)
                + "</ul>"
            )
            dump(base / "visual-manifest.json", manifest)
        browser.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true")
    build(ap.parse_args().render)
