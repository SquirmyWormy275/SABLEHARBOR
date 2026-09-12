"""Fail on stale source sections, missing scoped records, links, identities or draft bytes."""

from pathlib import Path
import argparse
import hashlib
import json
import re
import sqlite3
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def require(test, message):
    if not test:
        raise ValueError(message)


def validate(drafts=False):
    source = json.loads((HERE / "source_scope.json").read_text())
    register = json.loads((HERE / "evidence-register.json").read_text())
    expected = {p for paths in source["groups"].values() for p in paths}
    actual = {i["source"]["path"] for i in register["instruments"]}
    require(expected == actual, "Instrument coverage differs from explicit source scope")
    ids = [i["id"] for i in register["instruments"]]
    require(len(ids) == len(set(ids)), "Duplicate instrument IDs")
    count = 0
    for i in register["instruments"]:
        p = ROOT / i["source"]["path"]
        require(sha(p) == i["source"]["sha256"], "Stale source " + str(p))
        body = p.read_text()
        matches = list(re.finditer(r"^#{1,3} (.+)$", body, re.M))
        require(len(matches) == len(i["sections"]), "Missing source sections")
        for n, s in enumerate(i["sections"]):
            m = matches[n]
            text = body[
                m.end() : matches[n + 1].start() if n + 1 < len(matches) else len(body)
            ].strip()
            require(
                s["text"] == text
                and s["heading"] == m.group(1)
                and s["line"] == body[: m.start()].count("\n") + 1,
                "Source section content drift " + s["id"],
            )
            count += 1
        for p in i["native_references"]:
            require((ROOT / p).is_file(), "Missing native reference " + p)
        f = i["formats"]
        if f["pdf_disposition"] == "VERIFIED_CONTROLLED_PAIR":
            require(sha(ROOT / f["pdf"]) == f["pdf_sha256"], "Controlled PDF drift")
    db = sqlite3.connect(HERE / "legal-records.sqlite3")
    db.row_factory = sqlite3.Row
    require(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SQLite integrity")
    require(not db.execute("PRAGMA foreign_key_check").fetchall(), "SQLite foreign keys")
    require(
        db.execute("SELECT count(*) FROM source_document").fetchone()[0] == len(ids),
        "SQLite document coverage",
    )
    require(
        db.execute("SELECT count(*) FROM source_section").fetchone()[0] == count,
        "SQLite section coverage",
    )
    for row in db.execute("SELECT * FROM source_document"):
        require(row["sha256"] == sha(ROOT / row["path"]), "SQLite source drift")
    for row in db.execute("SELECT * FROM source_section"):
        parent = next(i for i in register["instruments"] if i["id"] == row["document_id"])
        item = next(s for s in parent["sections"] if s["id"] == row["id"])
        require(
            row["heading"] == item["heading"]
            and row["line"] == item["line"]
            and row["text"] == item["text"],
            "SQLite section content drift",
        )
    dossiers = json.loads((HERE / "dossier_source.json").read_text())["dossiers"]
    require(
        db.execute("SELECT count(*) FROM reading_dossier").fetchone()[0] == len(dossiers),
        "SQLite dossier population",
    )
    for d in dossiers:
        row = db.execute("SELECT * FROM reading_dossier WHERE id=?", (d["id"],)).fetchone()
        require(
            row is not None and row["title"] == d["title"] and row["status"] == d["status"],
            "Dossier identity drift",
        )
        require((ROOT / row["markdown"]).is_file(), "Missing dossier Markdown")
        clauses = list(
            db.execute(
                "SELECT * FROM dossier_clause WHERE dossier_id=? ORDER BY ordinal", (d["id"],)
            )
        )
        require(len(clauses) == len(d["clauses"]), "Missing dossier clause")
        for a, b in zip(clauses, d["clauses"]):
            require(
                a["label"] == b["label"]
                and a["text"] == b["text"]
                and a["source_path"] == b["source"]
                and a["source_sha256"] == sha(ROOT / b["source"]),
                "Dossier clause/source drift",
            )
    db.close()
    paths = [
        HERE,
        *[
            ROOT / "docs/legal/evidence" / x
            for x in ("commercial", "corporate", "assets-rights", "proposals")
        ],
    ]
    links = 0
    for base in paths:
        for p in base.rglob("*.md"):
            for target in re.findall(r"\]\(([^\s)]+)\)", p.read_text()):
                u = urlsplit(target)
                if u.scheme or not u.path:
                    continue
                q = (p.parent / unquote(u.path)).resolve()
                require(q.is_relative_to(ROOT) and q.exists(), f"Broken link {p}: {target}")
                links += 1
        for p in base.glob("evidence-register.json"):
            package = json.loads(p.read_text())
            require(
                len(package["scope"]["source_revision"]) == 40, "Source revision must be full SHA"
            )
            for ref in package["sources"]:
                require(
                    sha(ROOT / ref["path"]) == ref["sha256"], "Package source drift " + ref["path"]
                )
    proposal = json.loads(
        (ROOT / "docs/legal/evidence/proposals/decision-register.json").read_text()
    )
    require(
        all(
            r["proposed_value"] is None and r["acceptance_state"] == "NO_NEW_VALUE_ADOPTED"
            for r in proposal["fields"]
        ),
        "Unexpected proposal adoption",
    )
    require(
        proposal["billing_proposal_reference"]["status"] == "UNACCEPTED_REFERENCE_ONLY",
        "Billing reference promoted",
    )
    pages = 0
    if drafts:
        import fitz

        for folder in ("commercial", "corporate", "assets-rights"):
            base = ROOT / "docs/legal/evidence" / folder
            m = json.loads((base / "visual-manifest.json").read_text())
            require(
                m["approved"] is False and m["status"] == "DRAFT_FOR_EXACT_FILE_REVIEW",
                "Draft approval missing",
            )
            for a in m["artifacts"]:
                for key in ("pdf", "html"):
                    require(sha(ROOT / a[key]) == a[key + "_sha256"], "Draft bytes changed")
                require(sha(ROOT / a["markdown"]) == a["source_sha256"], "Draft source stale")
                pdf = fitz.open(ROOT / a["pdf"])
                require(len(pdf) == a["pages"], "PDF page count")
                text = "".join(p.get_text() for p in pdf)
                require(a["id"] in text and "DRAFT VISUAL" in text, "Missing draft identity")
                for page in pdf:
                    require(len(page.get_text().strip()) > 80, "Empty/near-empty page")
                    for block in page.get_text("dict")["blocks"]:
                        if block["type"] != 0:
                            continue
                        x0, y0, x1, y1 = block["bbox"]
                        require(
                            x0 >= 0
                            and y0 >= 0
                            and x1 <= page.rect.width + 1
                            and y1 <= page.rect.height + 1,
                            "Text outside page",
                        )
                pages += len(pdf)
                pdf.close()
    print(
        f"PASS: {len(ids)} documents, {count} exact sections, {len(dossiers)} dossiers, {links} local links, {len(register['gaps'])} explicit gaps; {pages} draft PDF pages"
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--drafts", action="store_true")
    validate(ap.parse_args().drafts)
