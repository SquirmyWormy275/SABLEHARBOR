"""Publish five concise case briefs using the existing corporate letterhead."""

import argparse
import base64
import hashlib
import html
import json
import os
import sqlite3
from pathlib import Path

import fitz
from markdown_it import MarkdownIt
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "docs/legal/gap-instruments/case-briefs"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    source = json.loads((HERE / "source.json").read_text())
    logo = ROOT / "assets/brand/logos/sable-harbor__primary-horizontal.svg"
    css = (ROOT / "tools/legal_gaps/style.css").read_text()
    css += "\nh1 {font-size:22pt} h2 {font-size:12pt;margin:15px 0 6px} p,li {font-size:10.5pt} .edition-note {margin-bottom:16px}\n"  # noqa: E501 -- publication text or SQL schema
    uri = "data:image/svg+xml;base64," + base64.b64encode(logo.read_bytes()).decode()
    db = HERE / "case-briefs.sqlite3"
    db.unlink(missing_ok=True)
    connection = sqlite3.connect(db)
    connection.execute(
        "CREATE TABLE cases (id TEXT PRIMARY KEY, title TEXT, period TEXT, situation TEXT, question TEXT, deliverable TEXT, limits TEXT, status TEXT)"  # noqa: E501 -- publication text or SQL schema
    )
    connection.execute(
        "CREATE TABLE files (case_id TEXT, sequence INTEGER, path TEXT, instruction TEXT, PRIMARY KEY(case_id,sequence))"  # noqa: E501 -- publication text or SQL schema
    )
    artifacts = []
    pins = {
        str(p.relative_to(ROOT)): sha(p)
        for p in [HERE / "source.json", Path(__file__), logo, ROOT / "tools/legal_gaps/style.css"]
    }
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        for case in source["cases"]:
            links = []
            for i, file in enumerate(case["files"], 1):
                target = (HERE / file["path"]).resolve()
                if not target.is_relative_to(ROOT) or not target.is_file():
                    raise ValueError(f"Missing or escaped case target: {target}")
                pins[str(target.relative_to(ROOT))] = sha(target)
                links.append(f"{i}. [{file['label']}]({file['path']}) — {file['instruction']}")
                connection.execute(
                    "INSERT INTO files VALUES (?,?,?,?)",
                    (case["id"], i, file["path"], file["instruction"]),
                )
            md = (
                f"# {case['title']}\n\n**{case['id']} · {case['period']}**\n\nPublic learning material. New brief design is draft for exact-file review.\n\n## Situation\n\n{case['situation']}\n\n## Question\n\n{case['question']}\n\n## Open these files\n\n"  # noqa: E501 -- publication text or SQL schema
                + "\n".join(links)
                + f"\n\n## Submit\n\n{case['deliverable']}\n\n## Scope limit\n\n{case['limits']}\n"
            )
            mp = HERE / (case["id"] + ".md")
            mp.write_text(md)
            body = MarkdownIt().render(md)
            hp = mp.with_suffix(".html")
            hp.write_text(
                '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'  # noqa: E501 -- publication text or SQL schema
                + html.escape(case["title"])
                + "</title><style>"
                + css
                + '</style></head><body><header class="edition-header"><img src="'
                + uri
                + '" alt="Sable Harbor"><span>ACCOUNTING CASE BRIEF<br>13 SEPTEMBER 2026</span></header><main>'  # noqa: E501 -- publication text or SQL schema
                + body
                + "</main></body></html>"
            )
            page = browser.new_page(viewport={"width": 1100, "height": 1000})
            page.goto(hp.as_uri(), wait_until="networkidle")
            raw = page.pdf(format="Letter", print_background=True)
            pdf = fitz.open(stream=raw, filetype="pdf")
            if len(pdf) != 1:
                raise ValueError(f"Brief overflow: {case['id']} has {len(pdf)} pages")
            for link in pdf[0].get_links():
                if link.get("file"):
                    link["file"] = os.path.relpath(link["file"], HERE)
                    pdf[0].update_link(link)
            pdf.set_metadata({})
            pp = mp.with_suffix(".pdf")
            pdf.save(pp, garbage=4, deflate=True, no_new_id=True)
            pdf.close()
            page.close()
            for artifact in (mp, hp, pp):
                artifacts.append({"path": artifact.name, "sha256": sha(artifact)})
            connection.execute(
                "INSERT INTO cases VALUES (?,?,?,?,?,?,?,?)",
                tuple(
                    case[k]
                    for k in (
                        "id",
                        "title",
                        "period",
                        "situation",
                        "question",
                        "deliverable",
                        "limits",
                        "status",
                    )
                ),
            )
        browser.close()
    connection.commit()
    connection.close()
    artifacts.append({"path": db.name, "sha256": sha(db)})
    readme = "# Choose a case and start working\n\nEach brief is one printed page: situation, question, exact files and deliverable. These are public learning materials; new designs remain draft for exact-file review.\n\n"  # noqa: E501 -- publication text or SQL schema
    for case in source["cases"]:
        readme += f"- **{case['title']}** — [brief]({case['id']}.md) · [letterhead PDF]({case['id']}.pdf) · [browser view]({case['id']}.html)\n"  # noqa: E501 -- publication text or SQL schema
    readme += "\nAfter completing a case, use [evidence tracking](../evidence-tracking/README.md) to record incomplete or disputed support. [Source-impact reporting](../source-impact/README.md) identifies dependent work requiring recheck when sources change. [The release index](../REVIEW_RELEASES.md) provides the portable review package.\n\nThe [structured source](source.json) and [SQLite index](case-briefs.sqlite3) preserve every brief and file instruction. Reproduce with `python tools/legal_gaps/case_briefs.py build`; validate with `python tools/legal_gaps/case_briefs.py validate`. Existing letterhead and logo are reused unchanged.\n"  # noqa: E501 -- publication text or SQL schema
    (HERE / "README.md").write_text(readme)
    artifacts.append({"path": "README.md", "sha256": sha(HERE / "README.md")})
    (HERE / "manifest.json").write_text(
        json.dumps(
            {
                "revision": source["revision"],
                "status": "DRAFT_FOR_EXACT_FILE_REVIEW",
                "inputs": pins,
                "files": artifacts,
                "pdf_pages": 5,
            },
            indent=2,
        )
        + "\n"
    )
    print("Built five case briefs, five one-page PDFs and the SQLite index")


def validate():
    manifest = json.loads((HERE / "manifest.json").read_text())
    for relative, digest in manifest["inputs"].items():
        assert sha(ROOT / relative) == digest, ("Stale brief input", relative)
    for record in manifest["files"]:
        assert sha(HERE / record["path"]) == record["sha256"], ("Stale brief", record["path"])
    source = json.loads((HERE / "source.json").read_text())
    assert len(source["cases"]) == len({c["id"] for c in source["cases"]}) == 5
    for case in source["cases"]:
        with fitz.open(HERE / (case["id"] + ".pdf")) as pdf:
            assert len(pdf) == 1 and case["id"] in pdf[0].get_text()
            for link in pdf[0].get_links():
                target = link.get("file")
                assert target and not Path(target).is_absolute(), ("Nonportable PDF link", link)
                assert (HERE / target).is_file(), ("Broken PDF link", target)
            for word in ("Situation", "Question", "Submit", "Scope limit"):
                assert word in pdf[0].get_text()
    print("PASS: five one-page briefs, all source pins and artifact hashes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "validate"])
    args = parser.parse_args()
    build() if args.command == "build" else validate()
