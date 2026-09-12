"""Build a source-bound legal reading index; never creates execution or accounting facts."""

from pathlib import Path
import hashlib
import json
import re
import sqlite3

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def source_identity(path):
    text = (ROOT / path).read_text()
    match = re.search(r"\*\*(?:Document ID|Record ID|Record):\*\*\s*`?([A-Z][A-Z0-9-]+)", text)
    return (
        match.group(1)
        if match
        else "LEGAL-SOURCE-" + hashlib.sha256(path.encode()).hexdigest()[:12].upper()
    )


def sections(text):
    matches = list(re.finditer(r"^#{1,3} (.+)$", text, re.M))
    return [
        {
            "heading": m.group(1),
            "line": text[: m.start()].count("\n") + 1,
            "text": text[
                m.end() : matches[i + 1].start() if i + 1 < len(matches) else len(text)
            ].strip(),
        }
        for i, m in enumerate(matches)
    ]


def build():
    config = json.loads((HERE / "source_scope.json").read_text())
    publication = {
        a["source"]: a
        for a in json.loads((ROOT / "docs/governance/publication_manifest.json").read_text())[
            "artifacts"
        ]
    }
    instruments = []
    for family, paths in config["groups"].items():
        for path in paths:
            p = ROOT / path
            body = p.read_text()
            state = [
                s
                for s in body.splitlines()[:20]
                if re.search(
                    r"\*\*(?:State|Status|Record state|Decision state|Record origin|Evidence state)",
                    s,
                )
            ]
            pub = publication.get(path)
            human = {
                "markdown": path,
                "pdf": None,
                "pdf_disposition": "NO_VERIFIED_CONTROLLED_PAIR",
                "xlsx_disposition": "NOT_REQUIRED_FOR_NARRATIVE_SOURCE",
            }
            if pub:
                good = (
                    pub["source_sha256"] == sha(p)
                    and (ROOT / pub["publication"]).exists()
                    and pub["sha256"] == sha(ROOT / pub["publication"])
                )
                human.update(
                    pdf=pub["publication"],
                    pdf_sha256=pub["sha256"],
                    pdf_disposition="VERIFIED_CONTROLLED_PAIR"
                    if good
                    else "STALE_PAIR_REQUIRES_REBUILD",
                )
            sid = source_identity(path)
            instruments.append(
                {
                    "id": sid,
                    "family": family,
                    "title": body.splitlines()[0].lstrip("# "),
                    "source": {"path": path, "sha256": sha(p)},
                    "source_status_verbatim": state,
                    "disposition": "SOURCE_RECORD_AVAILABLE_EXECUTION_STATUS_RETAINED",
                    "execution_boundary": "The source may be a synthetic instrument, planning record, policy or readiness index. Inclusion never certifies an executed original.",
                    "formats": human,
                    "native_references": config["structured_references"][family],
                    "sections": [
                        {"id": f"{sid}:S{i + 1:03}", **section}
                        for i, section in enumerate(sections(body))
                    ],
                }
            )
    ids = [i["id"] for i in instruments]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate source document ID; disambiguate versions explicitly")
    gaps = json.loads((HERE / "gaps.json").read_text())
    record = {
        "schema_version": 1,
        "package_id": "SH-LEGAL-INVENTORY-001",
        "title": "Transaction and legal instrument reading register",
        "status": "SOURCE_BOUND_READING_INDEX",
        "scope": {
            "source_revision": config["base_sha"],
            "review_date": config["date"],
            "description": config["scope"],
        },
        "sources": [i["source"] for i in instruments],
        "markdown": "docs/reader/transactions/README.md",
        "reconciliation": "docs/reader/transactions/RECONCILIATION.md",
        "visual_manifest": None,
        "database": "docs/reader/transactions/legal-records.sqlite3",
        "instruments": instruments,
        "gaps": gaps,
        "counts": {
            "source_documents": len(instruments),
            "source_sections": sum(len(i["sections"]) for i in instruments),
            "verified_controlled_pdfs": sum(
                i["formats"]["pdf_disposition"] == "VERIFIED_CONTROLLED_PAIR" for i in instruments
            ),
            "explicit_gaps": len(gaps),
        },
    }
    dump(HERE / "evidence-register.json", record)
    dbpath = HERE / "legal-records.sqlite3"
    dbpath.unlink(missing_ok=True)
    db = sqlite3.connect(dbpath)
    db.executescript("""PRAGMA foreign_keys=ON;
      CREATE TABLE source_document(id TEXT PRIMARY KEY, family TEXT NOT NULL, title TEXT NOT NULL, path TEXT UNIQUE NOT NULL, sha256 TEXT NOT NULL, status_json TEXT NOT NULL, pdf TEXT);
      CREATE TABLE source_section(id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES source_document(id), heading TEXT NOT NULL, line INTEGER NOT NULL, text TEXT NOT NULL);
      CREATE TABLE missing_record(id TEXT PRIMARY KEY, category TEXT NOT NULL, status TEXT NOT NULL, detail_json TEXT NOT NULL);
      CREATE TABLE native_reference(document_id TEXT NOT NULL REFERENCES source_document(id), path TEXT NOT NULL, PRIMARY KEY(document_id,path));
    """)
    for i in instruments:
        db.execute(
            "INSERT INTO source_document VALUES(?,?,?,?,?,?,?)",
            (
                i["id"],
                i["family"],
                i["title"],
                i["source"]["path"],
                i["source"]["sha256"],
                json.dumps(i["source_status_verbatim"]),
                i["formats"]["pdf"],
            ),
        )
        db.executemany(
            "INSERT INTO source_section VALUES(?,?,?,?,?)",
            [(s["id"], i["id"], s["heading"], s["line"], s["text"]) for s in i["sections"]],
        )
        db.executemany(
            "INSERT INTO native_reference VALUES(?,?)",
            [(i["id"], p) for p in i["native_references"]],
        )
    db.executemany(
        "INSERT INTO missing_record VALUES(?,?,?,?)",
        [(g["id"], g["category"], g["status"], json.dumps(g, sort_keys=True)) for g in gaps],
    )
    db.commit()
    assert not db.execute("PRAGMA foreign_key_check").fetchall()
    db.execute("VACUUM")
    db.close()
    rows = [
        "# Transaction and legal records",
        "",
        "**Scope:** source-bound reader edition; no new legal terms, signatures, filings or accounting postings. Reviewed September 12, 2026 against base `8898d2d`.",
        "",
        "Start with the specific record below. Each source retains its synthetic, provisional or historical status. The structured register indexes every section of the selected sources and records verified existing PDF pairs. It is a document index, not an accounting subledger.",
        "",
        "[Instrument register](evidence-register.json) · [Missing records and conflicts](RECONCILIATION.md) · [SQLite document/section index](legal-records.sqlite3)",
        "",
        "## Reading packages",
        "",
        "- [Commercial agreements, orders and service obligations](../../legal/evidence/commercial/README.md)",
        "- [Corporate approvals, capital and workforce terms](../../legal/evidence/corporate/README.md)",
        "- [Acquisitions, assets, host rights and tenure](../../legal/evidence/assets-rights/README.md)",
        "- [Unresolved legal and billing fields](../../legal/evidence/proposals/README.md)",
        "",
        "## Complete scoped source inventory",
        "",
        "| Family | Source record | Existing PDF |",
        "|---|---|---|",
    ]
    for i in instruments:
        p = "../../../" + i["source"]["path"]
        pub = i["formats"]["pdf"]
        pdf = f"[PDF](../../../{pub})" if pub else "No verified pair"
        rows.append(
            f"| {i['family']} | [{i['id']}]({p}) — {i['title'].replace('|', '/')} | {pdf} |"
        )
    rows += [
        "",
        "## Query without losing source identity",
        "",
        "The database tables are `source_document`, `source_section`, `native_reference` and `missing_record`. Section IDs identify a source heading and starting line, not a separately signed instrument. For example:",
        "",
        "```sql",
        "SELECT d.id, s.heading, s.line, d.path FROM source_document d JOIN source_section s ON s.document_id=d.id WHERE d.family='acquisition';",
        "```",
        "",
        "Build and verify with `python docs/reader/transactions/build.py` and `python docs/reader/transactions/validate.py`. The package dossiers cite native legal/financial/geographic keys. Only the relevant native accounting source can establish a posting or balance.",
    ]
    (HERE / "README.md").write_text("\n".join(rows) + "\n")
    report = [
        "# Legal record reconciliation",
        "",
        "This report records source differences and missing independent support; it does not supply a legal opinion or resolve canon by inference.",
        "",
    ]
    for g in gaps:
        report += [
            f"## {g['id']} — {g['category']}",
            "",
            f"**Disposition:** {g['status']}",
            "",
            g["detail"],
            "",
            f"**Next action:** {g['next_action']}",
            "",
        ]
        report += [
            "**Sources:** " + ", ".join(f"[{Path(p).name}](../../../{p})" for p in g["sources"]),
            "",
        ]
    (HERE / "RECONCILIATION.md").write_text("\n".join(report) + "\n")
    print(record["counts"])


if __name__ == "__main__":
    build()
