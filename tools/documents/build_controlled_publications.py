#!/usr/bin/env python3
"""Render controlled Markdown publications to reproducible, branded PDFs."""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = [
 ("docs/governance/BOARD_AND_CAPITAL_GOVERNANCE.md","docs/governance/publications/SH-GOV-BOARD-001_v1.0.0.pdf","corporate"),
 ("docs/governance/BOARD_EVOLUTION_2016_2026.md","docs/governance/publications/SH-GOV-BOARD-HIST-001_v1.0.0.pdf","corporate"),
 ("docs/governance/GOVERNANCE_CONSTITUTION.md","docs/governance/publications/SH-GOV-CONST-001_v1.0.0.pdf","corporate"),
 ("docs/governance/ASSUMPTION_OF_RISK_FORM.md","docs/governance/publications/SH-GOV-RISK-001_v1.0.0.pdf","corporate"),
 ("docs/governance/ASSUMPTION_OF_RISK_DOCTRINE.md","docs/governance/publications/SH-GOV-RISK-DOCTRINE-001_v1.0.0.pdf","corporate"),
 ("docs/governance/RESERVED_MATTERS_AND_SUBSIDIARY_AUTONOMY.md","docs/governance/publications/SH-GOV-AUTH-001_v1.0.0.pdf","corporate"),
 ("docs/governance/CONTROL_DISSENT_AND_RAPID_ADJUDICATION.md","docs/governance/publications/SH-GOV-DISSENT-001_v1.0.0.pdf","corporate"),
 ("docs/governance/ABSTENTION_AND_INFORMATION_DEFICIENCY.md","docs/governance/publications/SH-GOV-ABSTAIN-001_v1.0.0.pdf","corporate"),
 ("docs/governance/DECISION_QUALITY_AND_AFTER_ACTION_LEARNING.md","docs/governance/publications/SH-GOV-LEARN-001_v1.0.0.pdf","corporate"),
 ("docs/governance/CONFLICT_INTEGRITY_AND_FOUNDER_AUTHORITY.md","docs/governance/publications/SH-GOV-CONFLICT-001_v1.0.0.pdf","corporate"),
 ("docs/governance/committees/AUDIT_AND_COMPLIANCE_COMMITTEE_CHARTER.md","docs/governance/publications/SH-GOV-COM-AUDIT-001_v1.0.0.pdf","corporate"),
 ("docs/governance/committees/FINANCE_AND_INVESTMENT_COMMITTEE_CHARTER.md","docs/governance/publications/SH-GOV-COM-FIN-001_v1.0.0.pdf","corporate"),
 ("docs/governance/committees/TECHNOLOGY_AND_OPERATIONS_COMMITTEE_CHARTER.md","docs/governance/publications/SH-GOV-COM-TECHOPS-001_v1.0.0.pdf","corporate"),
 ("docs/governance/committees/COMPENSATION_AND_HUMAN_CAPITAL_COMMITTEE_CHARTER.md","docs/governance/publications/SH-GOV-COM-COMP-001_v1.0.0.pdf","corporate"),
 ("docs/governance/committees/GOVERNANCE_AND_NOMINATING_COMMITTEE_CHARTER.md","docs/governance/publications/SH-GOV-COM-GOVNOM-001_v1.0.0.pdf","corporate"),
 ("docs/j2/J2_CHARTER.md","docs/j2/publications/SH-J2-CHARTER-001_v1.0.0.pdf","j2"),
 ("docs/j2/J2_HEADQUARTERS.md","docs/j2/publications/SH-J2-HQ-001_v1.0.0.pdf","j2"),
 ("docs/j2/CONTACT_COLLECTION_MANAGEMENT.md","docs/j2/publications/SH-J2-COLLECT-001_v1.0.0.pdf","j2"),
 ("docs/j2/JUDGMENT_OFFICER_PROFESSION.md","docs/j2/publications/SH-J2-JO-001_v1.0.0.pdf","j2"),
 ("docs/j2/ORIENTATION_OFFICER_PROFESSION.md","docs/j2/publications/SH-J2-OO-001_v1.0.0.pdf","j2"),
 ("docs/j2/J2_OPERATING_MODEL.md","docs/j2/publications/SH-J2-OPS-001_v1.0.0.pdf","j2"),
 ("docs/j2/CONTACT.md","docs/j2/publications/SH-J2-CONTACT-001_v1.0.0.pdf","j2"),
 ("docs/j2/JUDGMENT.md","docs/j2/publications/SH-J2-JUDGMENT-001_v1.0.0.pdf","j2"),
 ("docs/j2/ORIENTATION.md","docs/j2/publications/SH-J2-ORIENT-001_v1.0.0.pdf","j2"),
 ("docs/j2/JUNCTION_ADVISORY_GROUP.md","docs/j2/publications/SH-J2-JAG-001_v1.0.0.pdf","j2"),
 ("docs/j2/EDUCATION.md","docs/j2/publications/SH-J2-EDU-001_v1.0.0.pdf","j2"),
 ("docs/j2/EIB_AND_ENTERPRISE_QUESTIONS.md","docs/j2/publications/SH-J2-EIB-001_v1.0.0.pdf","j2"),
 ("docs/j2/INFORMATION_ACCESS_DOCTRINE.md","docs/j2/publications/SH-J2-ACCESS-001_v1.0.0.pdf","j2"),
 ("docs/j2/alexandria/ALEXANDRIA_CHARTER.md","docs/j2/publications/SH-J2-ALX-001_v1.0.0.pdf","j2"),
 ("docs/j2/alexandria/INSTITUTIONAL_MEMORY_AND_CONNECTION.md","docs/j2/publications/SH-J2-ALX-MEMORY-001_v1.0.0.pdf","j2"),
 ("docs/j2/alexandria/SEARCH_AND_HISTORICAL_RECONSTRUCTION.md","docs/j2/publications/SH-J2-ALX-SEARCH-001_v1.0.0.pdf","j2"),
 ("docs/j2/alexandria/VISUALIZATION_AND_BRANCHING_HISTORY.md","docs/j2/publications/SH-J2-ALX-VIS-001_v1.0.0.pdf","j2"),
 ("docs/j2/alexandria/TEMPORAL_INTEGRITY.md","docs/j2/publications/SH-J2-ALX-TIME-001_v1.0.0.pdf","j2"),
 ("docs/j2/alexandria/PROVENANCE_AND_LINEAGE.md","docs/j2/publications/SH-J2-ALX-PROV-001_v1.0.0.pdf","j2"),
 ("docs/j2/alexandria/INFORMATION_ACCESS_AND_DISCLOSURE.md","docs/j2/publications/SH-J2-ALX-DISCLOSE-001_v1.0.0.pdf","j2"),
 ("docs/j2/alexandria/AI_AUTHORITY_AND_HUMAN_AUTHORSHIP.md","docs/j2/publications/SH-J2-ALX-AI-001_v1.0.0.pdf","j2"),
 ("docs/j2/alexandria/DAEDALUS_PERSONAL_INSTANCE_AND_WORKSPACE.md","docs/j2/publications/SH-J2-DAEDALUS-PERSONAL-001_v1.0.0.pdf","j2"),
 ("docs/j2/alexandria/PINAKES_PORTAL_AND_UX.md","docs/j2/publications/SH-J2-PINAKES-001_v1.0.0.pdf","j2"),
 ("docs/j2/alexandria/SEMAPHORE_TRAFFIC_SYSTEM.md","docs/j2/publications/SH-J2-SEMAPHORE-001_v1.0.0.pdf","j2"),
 ("docs/j2/alexandria/CANON_INSTITUTIONAL_KNOWLEDGE.md","docs/j2/publications/SH-J2-CANON-001_v1.0.0.pdf","j2"),
 ("docs/j2/alexandria/DAEDALUS_OPERATING_DOCTRINE.md","docs/j2/publications/SH-J2-DAEDALUS-001_v1.0.0.pdf","j2"),
 ("docs/canon/RED_WASH_TRANSACTION_OPERATING_RECORD_2026-09-05.md","docs/governance/publications/SH-PS-RW-TOR-001_v1.0.0.pdf","pale_sun"),
 ("red_wash/logistics/ARU_BST_INTERFACE_AND_DEPENDENCY_RECORD.md","docs/governance/publications/SH-PS-RW-LOG-001_v1.0.0.pdf","red_wash"),
 ("docs/internal/COVERAGE_AUDIT_PHASE2.md","docs/internal/COVERAGE_AUDIT_PHASE2.pdf","corporate"),
 ("docs/internal/INSTITUTIONAL_CATALOG_QUERY_GUIDE.md","docs/internal/INSTITUTIONAL_CATALOG_QUERY_GUIDE.pdf","corporate")]

BRANDS = {
    "corporate": {
        "logo": "assets/brand/logos/sable-harbor__primary-horizontal.svg",
        "color": "#C45124",
        "logo_class": "wide-logo",
        "logo_width": 220,
        "logo_height": 52,
    },
    "j2": {
        "logo": "assets/brand/logos/j2__primary-horizontal.svg",
        "color": "#BE0E0C",
        "logo_class": "wide-logo",
        "logo_width": 220,
        "logo_height": 52,
    },
    "pale_sun": {
        "logo": "assets/brand/logos/pale_sun__canonical.png",
        "color": "#B99A53",
        "logo_class": "source-logo",
        "logo_width": 150,
        "logo_height": 100,
    },
    "red_wash": {
        "logo": "assets/brand/logos/red_wash__canonical.png",
        "color": "#A93628",
        "logo_class": "source-logo",
        "logo_width": 200,
        "logo_height": 100,
    },
}

GENERATED_FOR_VERSION = "2026-09-05"

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inline(s: str) -> str:
    s=html.escape(s)
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s)
    return s

def body(md: str) -> str:
    out=[]; in_code=False; rows=[]
    def flush():
        nonlocal rows
        if rows:
            cells=[[inline(c.strip()) for c in r.strip('|').split('|')] for r in rows if not re.match(r'^\|?\s*:?-+',r)]
            if cells:
                out.append('<table>'+''.join('<tr>'+''.join(f'<{("th" if i==0 else "td")}>{c}</{("th" if i==0 else "td")}>' for c in row)+'</tr>' for i,row in enumerate(cells))+'</table>')
            rows=[]
    for line in md.splitlines():
        if line.startswith('```'): flush(); in_code=not in_code; continue
        if in_code: continue
        if line.startswith('|'): rows.append(line); continue
        flush()
        if not line.strip(): continue
        if line.startswith('#'): n=len(line)-len(line.lstrip('#')); out.append(f'<h{min(n,4)}>{inline(line[n:].strip())}</h{min(n,4)}>')
        elif line.startswith(('- ','* ')): out.append(f'<p class="bullet">• {inline(line[2:])}</p>')
        elif re.match(r'^\d+\. ',line): out.append(f'<p class="bullet">{inline(line)}</p>')
        elif line.startswith('> '): out.append(f'<blockquote>{inline(line[2:])}</blockquote>')
        else: out.append(f'<p>{inline(line)}</p>')
    flush(); return '\n'.join(out)

def require_tool(name: str) -> str:
    executable = shutil.which(name)
    if not executable:
        raise SystemExit(f"{name} is required")
    return executable


def render_pdf(
    *,
    libreoffice: str,
    ghostscript: str,
    qpdf: str,
    tmp: Path,
    src_rel: str,
    out_rel: str,
    brand: str,
) -> None:
    if brand not in BRANDS:
        raise SystemExit(f"unknown publication brand: {brand}")

    src = ROOT / src_rel
    out = ROOT / out_rel
    profile = BRANDS[brand]
    logo = ROOT / profile["logo"]
    for required in (src, logo):
        if not required.is_file():
            raise SystemExit(f"controlled-publication input missing: {required.relative_to(ROOT)}")

    out.parent.mkdir(parents=True, exist_ok=True)
    color = profile["color"]
    logo_class = profile["logo_class"]
    logo_width = profile["logo_width"]
    logo_height = profile["logo_height"]
    page = f'''<!doctype html><html><head><meta charset="utf-8"><style>@page{{size:Letter;margin:.62in .7in .58in}}body{{font:10pt Arial;color:#101214;line-height:1.28}}header{{border-bottom:3px solid {color};padding-bottom:8px;margin-bottom:18px;min-height:52px}}header img{{display:block}}header img.source-logo{{background:#000}}h1{{font-size:21pt;margin:12px 0;color:#101214;display:block;clear:both}}h2{{font-size:14pt;color:{color};margin-top:16px;margin-bottom:6px;border-bottom:1px solid #bbb;display:block;clear:both;page-break-after:avoid}}h3{{font-size:11.5pt;display:block;clear:both;page-break-after:avoid}}p{{margin:6px 0;display:block;clear:both}}.bullet{{margin-left:16px}}table{{border-collapse:collapse;width:100%;font-size:8pt;margin:8px 0}}th,td{{border:1px solid #aaa;padding:3px;vertical-align:top}}th{{background:#eee}}blockquote{{border-left:3px solid {color};padding-left:10px;color:#555}}footer{{margin-top:18px;border-top:1px solid #777;padding-top:6px;font-size:7.5pt;color:#666}}code{{font-family:monospace}}</style></head><body><header><img class="{logo_class}" width="{logo_width}" height="{logo_height}" style="width:{logo_width}px;height:{logo_height}px" src="{logo.as_uri()}"></header>{body(src.read_text(encoding="utf-8"))}<footer>Controlled publication • Generated from {src_rel} • Do not alter PDF manually</footer></body></html>'''

    work = tmp / out.stem
    work.mkdir()
    html_path = work / f"{out.stem}.html"
    html_path.write_text(page, encoding="utf-8", newline="\n")
    environment = os.environ.copy()
    environment.update({"LC_ALL": "C.UTF-8", "TZ": "UTC"})
    user_installation = (work / "libreoffice-profile").as_uri()
    subprocess.run(
        [
            libreoffice,
            f"-env:UserInstallation={user_installation}",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(work),
            str(html_path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    )

    libreoffice_pdf = work / f"{out.stem}.pdf"
    ghostscript_pdf = work / f"{out.stem}.letter.pdf"
    normalized_pdf = work / f"{out.stem}.normalized.pdf"
    subprocess.run(
        [
            ghostscript,
            "-q",
            "-dSAFER",
            "-dNOPAUSE",
            "-dBATCH",
            "-dPDFSTOPONERROR",
            "-sDEVICE=pdfwrite",
            "-sPAPERSIZE=letter",
            "-dFIXEDMEDIA",
            "-dPDFFitPage",
            "-dOmitInfoDate=true",
            f"-sOutputFile={ghostscript_pdf}",
            str(libreoffice_pdf),
        ],
        check=True,
        env=environment,
    )
    # Reconstruct from pages so the source PDF's random document ID is not
    # retained. Removing mutable metadata and deriving the new ID from page
    # content makes repeated builds byte-for-byte stable in the same toolchain.
    subprocess.run(
        [
            qpdf,
            "--empty",
            "--pages",
            str(ghostscript_pdf),
            "1-z",
            "--",
            str(normalized_pdf),
            "--remove-info",
            "--remove-metadata",
            "--deterministic-id",
        ],
        check=True,
        env=environment,
    )
    # The system temporary directory may live on another filesystem than the
    # repository, so stage locally before the atomic replacement.
    local_staging = out.with_name(f".{out.name}.tmp")
    shutil.copyfile(normalized_pdf, local_staging)
    local_staging.replace(out)


def main() -> None:
    libreoffice = require_tool("libreoffice")
    ghostscript = require_tool("gs")
    qpdf = require_tool("qpdf")
    manifest = []
    with tempfile.TemporaryDirectory(prefix="sh-docs-") as temp_dir:
        tmp = Path(temp_dir)
        for src_rel, out_rel, brand in DOCS:
            render_pdf(
                libreoffice=libreoffice,
                ghostscript=ghostscript,
                qpdf=qpdf,
                tmp=tmp,
                src_rel=src_rel,
                out_rel=out_rel,
                brand=brand,
            )
            src = ROOT / src_rel
            out = ROOT / out_rel
            manifest.append(
                {
                    "source": src_rel,
                    "publication": out_rel,
                    "sha256": sha256(out),
                    "source_sha256": sha256(src),
                    "brand": brand,
                }
            )
    payload = {
        "standard": "SH-GOV-DOC-001",
        "generated_for_version": GENERATED_FOR_VERSION,
        "reproducibility": {
            "mutable_pdf_metadata": "removed",
            "document_id": "derived from page content",
            "page_size": "US Letter",
        },
        "artifacts": manifest,
    }
    (ROOT / "docs/governance/publication_manifest.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

if __name__=='__main__': main()
