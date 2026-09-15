"""Publish complete, unabridged source Markdown as review-only legal editions."""

# ruff: noqa: E501 -- Embedded HTML templates retain literal readable attributes.

import argparse
import base64
import hashlib
import html
import json
import posixpath
from pathlib import Path
from urllib.parse import urlsplit

import fitz
from markdown_it import MarkdownIt
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def markdown_parser(source, revision):
    parser = MarkdownIt("commonmark", {"html": True}).enable("table").enable("strikethrough")
    default_link = parser.renderer.rules.get("link_open")

    def link_open(tokens, idx, options, env):
        token = tokens[idx]
        href = token.attrGet("href")
        if href and not urlsplit(href).scheme and not href.startswith("#"):
            target = posixpath.normpath(posixpath.join(posixpath.dirname(source), href))
            token.attrSet(
                "href", f"https://github.com/SquirmyWormy275/SABLEHARBOR/blob/{revision}/{target}"
            )
        if default_link:
            return default_link(tokens, idx, options, env)
        return parser.renderer.renderToken(tokens, idx, options, env)

    parser.renderer.rules["link_open"] = link_open
    return parser


def source_path(record):
    value = record["source"]
    return value["path"] if isinstance(value, dict) else value


def render_html(record, revision, css):
    source = source_path(record)
    path = ROOT / source
    assert sha(path) == record["source_sha256"], f"Source changed: {source}"
    brand = record.get("brand", "sable-harbor")
    if isinstance(brand, dict):
        brand = brand.get("logo", brand.get("path", "sable-harbor"))
    brand_paths = {
        "corporate": "assets/brand/logos/sable-harbor__primary-horizontal.svg",
        "aru": "assets/brand/industrial_sources/aru/aru_primary_centered_chat_asset.png",
        "bst": "assets/brand/industrial_sources/bst/bst_railway_primary_chat_asset.png",
        "pale_sun": "assets/brand/logos/pale_sun__canonical.png",
        "j2": "assets/brand/logos/j2__primary-horizontal.svg",
    }
    logo = ROOT / brand_paths.get(
        brand, brand if "/" in brand else f"assets/brand/logos/{brand}__primary-horizontal.png"
    )
    assert logo.exists(), logo
    mime = "image/svg+xml" if logo.suffix == ".svg" else "image/png"
    logo_uri = f"data:{mime};base64," + base64.b64encode(logo.read_bytes()).decode()
    body = markdown_parser(source, revision).render(path.read_text())
    payload = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(record["title"])} — full source edition</title><style>{css}</style></head>
<body><header class="edition-header"><img src="{logo_uri}" alt="{html.escape(str(brand))}"><span>LEGAL RECORDS<br>FULL SOURCE EDITION</span></header>
<aside class="edition-note"><p><strong>Draft publication design · exact-file review required</strong></p><p>Complete source text follows. The source’s own status and limitations remain in force; this edition does not establish execution, filing or approval.</p></aside>
<article id="source-content" data-document-id="{html.escape(record["id"])}">{body}</article>
<aside class="source-identity"><strong>Edition provenance</strong><br>{html.escape(record["id"])}<br>Source: <a href="https://github.com/SquirmyWormy275/SABLEHARBOR/blob/{revision}/{source}">{html.escape(source)}</a><br>Source revision: {revision}<br>Source SHA-256: {record["source_sha256"]}</aside>
</body></html>
'''
    return payload, {"path": str(logo.relative_to(ROOT)), "sha256": sha(logo)}


def build(only=None):
    config = json.loads((HERE / "SOURCE_MANIFEST.json").read_text())
    records = config["records"]
    revision = config["source_revision"]
    out = HERE / "editions"
    out.mkdir(exist_ok=True)
    css = (HERE / "style.css").read_text()
    result = []
    old_path = HERE / "render-manifest.json"
    old = json.loads(old_path.read_text()) if old_path.exists() else {}
    old_records = {x["id"]: x for x in old.get("artifacts", [])}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        for record in records:
            if only and record["id"] not in only:
                result.append(old_records[record["id"]])
                continue
            payload, logo = render_html(record, revision, css)
            hp = out / (record["id"] + ".html")
            pp = hp.with_suffix(".pdf")
            hp.write_text(payload)
            page = browser.new_page()
            page.set_content(payload, wait_until="networkidle")
            page.emulate_media(media="print")
            raw = page.pdf(
                format="Letter",
                print_background=True,
                display_header_footer=True,
                header_template='<div style="font-family:Arial;font-size:8px;color:#67747a;width:100%;margin:0 64px;text-align:right">LEGAL RECORDS · FULL SOURCE EDITION</div>',
                footer_template='<div style="font-family:Arial;font-size:8px;color:#67747a;width:100%;margin:0 64px;display:flex;justify-content:space-between"><span>'
                + html.escape(record["id"])
                + ' · DRAFT FOR REVIEW</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>',
            )
            page.close()
            pdf = fitz.open(stream=raw, filetype="pdf")
            pdf.set_metadata({})
            pdf.save(pp, garbage=4, deflate=True, no_new_id=True)
            pages = len(pdf)
            pdf.close()
            result.append(
                {
                    "id": record["id"],
                    "source": source_path(record),
                    "source_sha256": record["source_sha256"],
                    "html": str(hp.relative_to(ROOT)),
                    "html_sha256": sha(hp),
                    "pdf": str(pp.relative_to(ROOT)),
                    "pdf_sha256": sha(pp),
                    "pages": pages,
                    "logo": logo,
                }
            )
            print(f"{record['id']}: {pages} complete pages", flush=True)
        browser.close()
    manifest = {
        "schema_version": 1,
        "status": "DRAFT_FOR_EXACT_FILE_REVIEW",
        "approved": False,
        "source_revision": revision,
        "source_manifest_sha256": sha(HERE / "SOURCE_MANIFEST.json"),
        "generator_sha256": sha(Path(__file__)),
        "style_sha256": sha(HERE / "style.css"),
        "artifacts": result,
        "counts": {
            "sources": len(result),
            "pdfs": len(result),
            "html": len(result),
            "pages": sum(x["pages"] for x in result),
        },
    }
    old_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="+")
    build(ap.parse_args().only)
