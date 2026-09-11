"""Build the existing geographic atlas's linked facility extension from manifests.

Run with .venv/bin/python geospatial/facilities/atlas.py. No web server required.
Individual drawings remain independently saved; the portable PDF imports them.
"""

from __future__ import annotations
import hashlib
import html
import json
import os
from pathlib import Path
import textwrap
import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MAPS = ROOT / "geospatial/maps"
FAC = MAPS / "facilities"
HTML = MAPS / "index.html"
PDF = MAPS / "SABLE_HARBOR_Facility_Atlas_v0.2.0.pdf"
COVERAGE = ROOT / "geospatial/facilities/coverage/COVERAGE_MATRIX.json"
RUNTIME = ROOT / "geospatial/facilities/RUNTIME_BRIDGE.json"
REFERENCES = ROOT / "docs/facilities/references/sacramento-hq/r01-approved"
FONTS = ROOT / "geospatial/facilities/fonts"
FONT_FILES = [FONTS / "DejaVuSans.ttf", FONTS / "DejaVuSans-Bold.ttf"]
PRIOR_PDF = MAPS / "SABLE_HARBOR_Facility_Atlas_v0.1.0.pdf"
PAPER = (247 / 255, 246 / 255, 241 / 255)
INK = (34 / 255, 55 / 255, 64 / 255)
MUTED = (98 / 255, 118 / 255, 126 / 255)


def load(p):
    return json.loads(p.read_text())


def rel(p):
    return str(p.relative_to(ROOT))


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def esc(value):
    return html.escape(str(value if value is not None else "Unknown"), quote=True)


def href(path):
    return esc(os.path.relpath(ROOT / path, MAPS))


def normal_maps():
    current = load(FAC / "MANIFEST.json")["maps"]
    if RUNTIME.is_file():
        current = current + load(RUNTIME)["maps"]
    # The main manifest may include this successor after integration; deduplicate it.
    current_ids = {m["id"] for m in current}
    prior = []
    for m in load(MAPS / "MAP_MANIFEST.json"):
        if m.get("map_id", m.get("id")) in current_ids:
            continue
        if m.get("version") != "0.1.0-rc4":
            continue
        arts = {}
        for fmt, a in m["files"].items():
            p = a["path"]
            p = p if p.startswith("geospatial/") else "geospatial/maps/" + p
            arts[fmt] = {"path": p, "sha256": a["sha256"]}
        prior.append(
            {
                "id": m["map_id"],
                "title": m["title"],
                "kind": "context",
                "status": m["canon_status"],
                "artifacts": arts,
            }
        )
    return current, prior


def context_ids(site_id, prior):
    prefixes = {
        "SH-SITE-0001": ["SH-MAP-SAC-001"],
        "SH-SITE-0002": ["SH-MAP-WIL-001"],
        "SH-SITE-0003": ["SH-MAP-WIL-001"],
        "SH-SITE-0005": ["SH-MAP-CRD-001"],
        "SH-SITE-0006": ["SH-MAP-RWM-001", "SH-MAP-RWM-002"],
        "SH-SITE-0007": ["SH-MAP-BST-002"],
    }
    choices = prefixes.get(site_id, [])
    if site_id.startswith("SH-IND-FAC-"):
        choices = (
            ["SH-MAP-RWM-001", "SH-MAP-RWM-002"]
            if "RW-RECEIVING" in site_id
            else ["SH-MAP-BST-002"]
        )
    return [m["id"] for m in prior if any(m["id"].startswith(p) for p in choices)]


def pdf_text(value):
    """Embedded DejaVu supports the approved typography without ASCII fallback."""
    return str(value)


def main():
    coverage = load(COVERAGE)
    reference_manifest = load(REFERENCES / "MANIFEST.json")
    references = [r for r in reference_manifest["files"] if r["filename"].endswith(".png")]
    assert len(references) == 4, "R01 consists of exactly four original approved PNGs"
    for reference in reference_manifest["files"]:
        assert digest(REFERENCES / reference["filename"]) == reference["sha256"], (
            "R01 original changed"
        )
    for font in FONT_FILES:
        assert font.is_file(), f"Missing approved font asset {font}"
    current, prior = normal_maps()
    allmaps = current + prior
    source_files = sorted((ROOT / "geospatial/facilities/source").glob("*.json"))
    sites = []
    for p in source_files:
        source = load(p)
        for s in source.get("sites", [source] if "site_id" in source else []):
            sites.append((s, p))
    if RUNTIME.is_file():
        sites.extend((s, RUNTIME) for s in load(RUNTIME)["sites"])
    sites.sort(key=lambda pair: (pair[0]["site_id"] != "SH-SITE-0001", pair[0]["site_id"]))
    nodes = {}
    edges = set()
    paths = set()
    artifact_nodes = {}
    map_by_id = {m["id"]: m for m in allmaps}

    def node(id, kind, **kw):
        nodes.setdefault(id, {"id": id, "kind": kind, **kw})
        if kw.get("path"):
            paths.add(kw["path"])

    def edge(a, b):
        edges.add((a, b))

    node("atlas", "enterprise", path=rel(HTML))
    node("portable-atlas", "publication", path=rel(PDF))
    edge("atlas", "portable-atlas")
    node(
        "SH-FAC-REF-SAC-R01",
        "reference_family",
        title="Original approved Sacramento R01",
        status="APPROVED_VISUAL_REFERENCE",
    )
    edge("atlas", "SH-FAC-REF-SAC-R01")
    for reference in reference_manifest["files"]:
        reference_id = "SH-FAC-REF-SAC-R01:" + reference["filename"]
        node(
            reference_id,
            "approved_reference"
            if reference["filename"].endswith(".png")
            else "reference_provenance",
            path=rel(REFERENCES / reference["filename"]),
            sha256=reference["sha256"],
            status=reference["status"],
        )
        edge("SH-FAC-REF-SAC-R01", reference_id)
    node(
        "SH-FAC-REF-SAC-R01:manifest", "reference_manifest", path=rel(REFERENCES / "MANIFEST.json")
    )
    edge("SH-FAC-REF-SAC-R01", "SH-FAC-REF-SAC-R01:manifest")
    if PRIOR_PDF.is_file():
        node(
            "superseded-atlas-v0.1.0",
            "historical_publication",
            path=rel(PRIOR_PDF),
            status="SUPERSEDED_PRE_R01_PROPOSAL_NOT_APPROVED",
        )
        edge("atlas", "superseded-atlas-v0.1.0")
    for font in FONT_FILES:
        node("font:" + font.name, "font_source", path=rel(font), sha256=digest(font))
        edge("atlas", "font:" + font.name)
    for label, path in [
        ("artifact-index", FAC / "ARTIFACT_INDEX.md"),
        ("link-graph", FAC / "ATLAS_LINKS.json"),
        ("coverage-source", COVERAGE),
    ]:
        node(label, "index", path=rel(path))
        edge("atlas", label)
    for m in allmaps:
        node(m["id"], "map", title=m["title"], status=m["status"])
        for fmt, a in m["artifacts"].items():
            p = a["path"]
            assert (ROOT / p).is_file(), f"missing asset {p}"
            assert digest(ROOT / p) == a["sha256"], f"stale asset {p}"
            aid = "artifact:" + p
            node(aid, "artifact", path=p, sha256=a["sha256"])
            edge(m["id"], aid)
            artifact_nodes[p] = aid
    site_lookup = {s["site_id"]: s for s, p in sites}
    building_lookup = {b["id"]: (s, b) for s, p in sites for b in s["buildings"]}
    for s, p in sites:
        sid = s["site_id"]
        node(sid, "site", title=s["name"], status=s["status"], source=rel(p))
        edge("atlas", sid)
        node("source:" + rel(p), "source", path=rel(p))
        edge(sid, "source:" + rel(p))
        for mid in context_ids(sid, prior):
            edge(sid, mid)
        for b in s["buildings"]:
            node(b["id"], "building", title=b["name"], status=b["status"])
            edge(sid, b["id"])
            for f in b["floors"]:
                node(f["id"], "floor", title=f["name"], status=f["status"])
                edge(b["id"], f["id"])
        for m in current:
            if m.get("site_id") == sid:
                parent = m.get("floor_id") or m.get("building_id") or sid
                edge(parent, m["id"])
            if sid in m.get("related_site_ids", []):
                edge(sid, m["id"])
    coverage_links = []
    for r in coverage["records"]:
        cid = "coverage:" + r["id"]
        node(
            cid, "coverage", title=r["name"], status=r["status"], classification=r["classification"]
        )
        edge("atlas", cid)
        targets = []
        for provenance in r.get("provenance", []):
            p = provenance["path"]
            if (ROOT / p).is_file():
                node("source:" + p, "source", path=p)
                edge(cid, "source:" + p)
        if r["id"] in site_lookup or r["id"] in building_lookup:
            targets.append(r["id"])
        if r.get("parent_id") in site_lookup:
            targets.append(r["parent_id"])
        targets += [
            s["site_id"]
            for s, p in sites
            if next(
                (q.get("parent_id") for q in coverage["records"] if q["id"] == s["site_id"]), None
            )
            == r["id"]
        ]
        targets = list(dict.fromkeys(targets))
        for t in targets:
            edge(cid, t)
        contexts = context_ids(r["id"], prior)
        for mid in contexts:
            edge(cid, mid)
        coverage_links.append(
            {
                "coverage_id": r["id"],
                "anchor": "record-" + r["id"],
                "targets": targets,
                "context_map_ids": contexts,
                "disposition": r["reason"],
                "status": r["status"],
                "classification": r["classification"],
                "geometry_precision": r.get("precision"),
            }
        )
    # All original context sheets remain discoverable, even where no exact site match exists.
    for m in prior:
        edge("atlas", m["id"])

    def links(m):
        return " ".join(
            f'<a href="{href(a["path"])}">{esc(fmt.upper())}</a>'
            for fmt, a in m["artifacts"].items()
        )

    def card(m, preview=True):
        size = ""
        if preview and "png" in m["artifacts"]:
            with Image.open(ROOT / m["artifacts"]["png"]["path"]) as im:
                size = f' width="{im.width}" height="{im.height}"'
        return (
            f'<article class="map" id="map-{esc(m["id"])}"><h4>{esc(m["title"])}</h4><p class="meta">{esc(m["id"])} · {esc(m["status"])}</p><p>{links(m)}</p>'
            + (
                f'<a href="{href(m["artifacts"]["png"]["path"])}"><img loading="lazy"{size} src="{href(m["artifacts"]["png"]["path"])}" alt="{esc(m["title"])}"></a>'
                if preview and "png" in m["artifacts"]
                else ""
            )
            + "</article>"
        )

    out = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sable Harbor facility atlas</title><style>',
        "@font-face{font-family:SH;src:url('../facilities/fonts/DejaVuSans.ttf')}@font-face{font-family:SH;src:url('../facilities/fonts/DejaVuSans-Bold.ttf');font-weight:700}body{margin:0;background:#f7f6f1;color:#223740;font:16px/1.6 SH,sans-serif}header,main{max-width:1500px;margin:auto;padding:30px 36px}header{padding-bottom:20px}header .brand{font-size:20px;letter-spacing:.28em;font-weight:700;border-bottom:1px solid #223740;padding-bottom:22px}.brand span{float:right;letter-spacing:.02em;font-size:12px;font-weight:400}h1,h2,h3,h4{line-height:1.25}h1{font-size:42px;text-transform:uppercase;letter-spacing:.035em}h2{text-transform:uppercase;font-size:23px;margin-top:30px}h3{font-size:20px}h4{font-size:18px}a{color:#3d7186;text-underline-offset:3px}.meta{font-size:13px;overflow-wrap:anywhere;color:#62767e}details,article.record{border:0;border-top:1px solid #aab5b5;padding:22px 0;margin:18px 0}details details{margin-left:24px}summary{font-weight:700;cursor:pointer;font-size:20px}img{width:100%;height:auto;display:block}.map{padding:16px 0;margin:18px 0;border-bottom:1px solid #d7ddd9}.reference{padding:16px 0;max-width:1150px}.historical{border-left:3px solid #799487;padding-left:16px!important}.external{border-left:3px solid #49778b;padding-left:16px!important}.unresolved,.proposed{border-left:3px solid #ac9052;padding-left:16px!important}code{font-size:12px;overflow-wrap:anywhere}input,select{font:inherit;padding:10px;border:1px solid #8c9da1;background:#f7f6f1;max-width:100%}.filters{display:flex;gap:12px;flex-wrap:wrap}nav{border-top:1px solid #223740;border-bottom:1px solid #223740;padding:12px 0}nav ul{columns:2;padding-left:22px}@media(max-width:700px){nav ul{columns:1}header,main{padding:20px}.brand span{float:none;display:block;margin-top:14px}h1{font-size:30px}details details{margin-left:12px}}[hidden]{display:none!important}</style></head><body>",
        '<header id="top"><div class="brand">SABLE HARBOR<span>SACRAMENTO / INSTITUTIONAL CAMPUS</span></div><h1>Enterprise facility atlas</h1><p class="meta">COORDINATED DESIGN STUDY · 11 SEPTEMBER 2026 · R02 SUCCESSOR TO THE APPROVED R01 VISUAL BASELINE</p><p><a href="'
        + esc(PDF.name)
        + '">Portable PDF atlas v0.2.0</a> · <a href="facilities/ARTIFACT_INDEX.md">Complete artifact index</a> · <a href="workbench.html">Planning workbench</a> · <a href="spatial.html">3D spatial review</a> · <a href="spatial/README.md">Architectural sheets</a> · <a href="facilities/ATLAS_LINKS.json">Link graph</a> · <a href="#approved-r01">Original approved R01 sheets</a></p></header><main>',
        "<p>Follow a location to its site plan, buildings and separately saved floor images. Existing geographic context remains rc4; concept layouts do not establish ownership, construction completion or actual occupancy. Historical, external and unresolved records retain explicit dispositions without invented map pins.</p>",
        f"<p>{len(sites)} modelled site packages · {len(building_lookup)} buildings · {sum(len(b[1]['floors']) for b in building_lookup.values())} floors · {len(coverage['records'])} coverage dispositions</p>",
        "<nav><h2>Locations and sites</h2><ul>",
    ]
    out += [f'<li><a href="#{esc(s["site_id"])}">{esc(s["name"])}</a></li>' for s, p in sites]
    out += [
        '</ul><p><a href="#contexts">Geographic context</a> · <a href="#coverage">All coverage records</a></p></nav>'
    ]
    out.append(
        '<details id="approved-r01"><summary>Original approved Sacramento R01 references</summary><p>Exactly four owner-approved PNGs, recovered intact. Approval records the visual system and campus composition. These originals are immutable; this R02 HTML/PDF atlas and its generated plans are derivatives, not original approved R01 artifacts.</p>'
    )
    for reference in references:
        path = rel(REFERENCES / reference["filename"])
        out.append(
            f'<article class="reference" id="ref-{esc(reference["filename"])}"><h3>{esc(reference["filename"])}</h3><p><a href="{href(path)}">Open original 3240 × 2304 PNG</a></p><p class="meta">APPROVED VISUAL REFERENCE · 11 SEPTEMBER 2026<br>SHA-256 <code>{reference["sha256"]}</code><br>{esc(reference["approval_source"])}</p><a href="{href(path)}"><img loading="lazy" width="3240" height="2304" src="{href(path)}" alt="Immutable approved R01 reference: {esc(reference["filename"])}"></a></article>'
        )
    out.append(
        '<p><a href="'
        + href(rel(REFERENCES / "SABLE_HARBOR_Sacramento_HQ_Drafts_R01.zip"))
        + '">Original recovered four-image ZIP</a> · <a href="'
        + href(rel(REFERENCES / "MANIFEST.json"))
        + '">Reference manifest and provenance</a> · <a href="'
        + href(rel(REFERENCES / "CODEX_ADDENDUM_APPROVED_SACRAMENTO_VISUAL_BASELINE_R01.md"))
        + '">Controlling approval addendum</a></p></details>'
    )
    if PRIOR_PDF.is_file():
        out.append(
            '<details class="historical" id="superseded-atlas"><summary>Superseded pre-R01 proposal v0.1.0</summary><p>The earlier six-building implementation was superseded when the four original approved references were recovered. It is retained as development history, not the current campus or an approved R01 artifact. Its draft release was withheld and never published.</p><p><a href="'
            + href(rel(PRIOR_PDF))
            + '">Archived pre-R01 proposal PDF</a></p></details>'
        )
    for s, p in sites:
        sid = s["site_id"]
        out.append(
            f'<details id="{esc(sid)}" open><summary>{esc(s["name"])}</summary><p class="meta">{esc(sid)} · {esc(s["status"])} · {esc(s["geometry_status"])}</p><p>{esc(s.get("geometry_basis", ""))}</p><p>Tenure: {esc(s.get("tenure"))}. Occupancy start: {esc(s.get("occupancy_start"))}. <a href="{href(rel(p))}">Editable structured source</a></p>'
        )
        ctx = context_ids(sid, prior)
        if ctx:
            out.append(
                "<p>Context: "
                + " · ".join(
                    f'<a href="#map-{esc(mid)}">{esc(map_by_id[mid]["title"])}</a>' for mid in ctx
                )
                + "</p>"
            )
        related = [
            m for m in current if sid in m.get("related_site_ids", []) and m.get("site_id") != sid
        ]
        if related:
            out.append(
                "<p>Shared runtime context: "
                + " · ".join(
                    f'<a href="#map-{esc(m["id"])}">{esc(m["title"])}</a>' for m in related
                )
                + "</p>"
            )
        out.extend(card(m) for m in current if m.get("site_id") == sid and not m.get("building_id"))
        if s.get("floor_exemption"):
            out.append(
                "<p><strong>Floor disposition:</strong> " + esc(s["floor_exemption"]) + "</p>"
            )
        for b in s["buildings"]:
            out.append(
                f'<details id="{esc(b["id"])}"><summary>{esc(b["name"])} · {len(b["floors"])} modelled floors</summary><p class="meta">{esc(b["id"])} · {esc(b["status"])}</p>'
            )
            out.append(
                f'<p><a href="spatial.html#{esc(b["id"])}">Explore building in 3D, sections, elevations and roof</a></p>'
            )
            out.extend(
                card(m, False)
                for m in current
                if m.get("building_id") == b["id"] and not m.get("floor_id")
            )
            for f in b["floors"]:
                out.append(
                    f'<section id="{esc(f["id"])}"><h3>{esc(f["name"])}</h3><p class="meta">{esc(f["id"])} · {f["gross_area_m2"]:,.1f} m² gross · {esc(f["planned_peak"])} planned peak · {esc(f["status"])}</p>'
                )
                out.extend(card(m) for m in current if m.get("floor_id") == f["id"])
                out.append("</section>")
            out.append("</details>")
        out.append('<p><a href="#top">Back to atlas</a></p></details>')
    out.append(
        '<details id="contexts"><summary>Existing geographic context — preserved rc4 publication</summary>'
    )
    out.extend(card(m) for m in prior)
    out.append("</details>")
    out.append(
        '<section id="coverage"><h2>Complete coverage register</h2><p>These are source records, including aliases and nonphysical functions; they are not a count of buildings. Use search or category to inspect every disposition.</p><div class="filters"><label>Search <input id="query" type="search" placeholder="Name, ID or status"></label><label>Class <select id="class"><option value="">All</option>'
    )
    out.extend(
        f'<option value="{esc(k)}">{esc(k)} · {esc(v)}</option>'
        for k, v in coverage["class_definitions"].items()
    )
    out.append('</select></label></div><p id="shown"></p>')
    for r, c in zip(coverage["records"], coverage_links):
        state = r["status"].lower()
        out.append(
            f'<article class="record {esc(state)}" id="record-{esc(r["id"])}" data-class="{r["class"]}"><h3>{esc(r["name"])}</h3><p class="meta">{esc(r["id"])} · {esc(r["status"])} · {esc(r["classification"])}</p><p>{esc(r["reason"])}</p><p class="meta">Precision: {esc(r.get("precision"))} · Tenure: {esc(r.get("tenure"))} · Occupancy: {esc(r.get("occupancy_start"))} to {esc(r.get("occupancy_end"))}</p>'
        )
        if c["targets"]:
            out.append(
                "<p>Plans: "
                + " · ".join(f'<a href="#{esc(t)}">{esc(t)}</a>' for t in c["targets"])
                + "</p>"
            )
        elif c["context_map_ids"]:
            out.append(
                "<p>Context only: "
                + " · ".join(f'<a href="#map-{esc(t)}">{esc(t)}</a>' for t in c["context_map_ids"])
                + "</p>"
            )
        else:
            out.append(
                '<p class="meta">No dedicated physical layout: disposition above governs; no geometry or occupancy is inferred.</p>'
            )
        out.append(
            '<p class="meta">Sources: '
            + " · ".join(
                f'<a href="{href(v["path"])}">{esc(v["path"])}</a>'
                for v in r.get("provenance", [])
                if (ROOT / v["path"]).is_file()
            )
            + "</p></article>"
        )
    out.append(
        '</section></main><script>const rows=[...document.querySelectorAll(".record")];function filter(){const q=document.querySelector("#query").value.toLowerCase(),c=document.querySelector("#class").value;let n=0;rows.forEach(r=>{r.hidden=!(r.textContent.toLowerCase().includes(q)&&(!c||r.dataset.class===c));if(!r.hidden)n++});document.querySelector("#shown").textContent=n+" records shown"}document.querySelector("#query").addEventListener("input",filter);document.querySelector("#class").addEventListener("change",filter);function reveal(){const target=document.getElementById(decodeURIComponent(location.hash.slice(1)));let e=target;while(e){if(e.tagName==="DETAILS")e.open=true;e=e.parentElement}if(target)requestAnimationFrame(()=>target.scrollIntoView({block:"start"}))}window.addEventListener("hashchange",reveal);filter();reveal();</script></body></html>'
    )
    HTML.write_text("\n".join(out) + "\n")
    # PDF index is linked to imported independently saved maps, never rasterized pages.
    doc = fitz.open()
    toc = []
    index_links = []

    def page(title):
        p = doc.new_page(width=1080, height=768)
        p.draw_rect(p.rect, color=None, fill=PAPER)
        p.insert_font(fontname="SHRegular", fontfile=str(FONT_FILES[0]))
        p.insert_font(fontname="SHBold", fontfile=str(FONT_FILES[1]))
        p.insert_text(
            (36, 35), "S A B L E   H A R B O R", fontsize=13, fontname="SHBold", color=INK
        )
        p.insert_text(
            (751, 34),
            "SACRAMENTO / INSTITUTIONAL CAMPUS",
            fontsize=8,
            fontname="SHRegular",
            color=INK,
        )
        p.draw_line((36, 50), (1044, 50), color=INK, width=0.65)
        rc = p.insert_textbox(
            fitz.Rect(36, 66, 1044, 111),
            pdf_text(title.upper()),
            fontname="SHBold",
            fontsize=23,
            color=INK,
        )
        assert rc >= 0, "PDF title overflow: " + title
        p.draw_line((36, 728), (1044, 728), color=INK, width=0.65)
        p.insert_text(
            (36, 747),
            "COORDINATED DESIGN STUDY · 11 SEPTEMBER 2026",
            fontname="SHRegular",
            fontsize=8,
            color=MUTED,
        )
        p.insert_text((844, 747), "FACILITY ATLAS / R02", fontname="SHBold", fontsize=9, color=INK)
        return p

    p = page("Enterprise facility atlas")
    toc.append([1, "Facility atlas / R02", 1])
    intro = "September 2026 · R02 successor to the approved R01 visual baseline\n\nFollow a location to its site, building and independently saved floor drawings.\n\nFour original approved R01 PNGs are embedded unchanged on their own pages. This portable PDF is a derivative publication; it is not an original approved R01 artifact.\n\nConcept layouts do not establish acquisition, construction completion or actual occupancy. Original rc4 geographic context remains preserved."
    rc = p.insert_textbox(
        fitz.Rect(36, 145, 725, 425),
        intro,
        fontname="SHRegular",
        fontsize=15,
        color=INK,
        lineheight=1.5,
    )
    assert rc >= 0, "PDF introduction overflow"
    p.insert_text(
        (36, 487),
        f"{len(sites)} SITE PACKAGES   /   {len(building_lookup)} BUILDINGS   /   {sum(len(b[1]['floors']) for b in building_lookup.values())} FLOORS",
        fontname="SHBold",
        fontsize=16,
        color=INK,
    )
    p.insert_text(
        (36, 530),
        "Use the PDF bookmarks or the linked site index to drill down.",
        fontname="SHRegular",
        fontsize=12,
        color=MUTED,
    )
    p.insert_text((36, 576), "Original R01 references →", fontname="SHBold", fontsize=12, color=INK)
    for reference in references:
        p = doc.new_page(width=1080, height=768)
        p.draw_rect(p.rect, color=None, fill=PAPER)
        p.insert_font(fontname="SHRegular", fontfile=str(FONT_FILES[0]))
        p.insert_image(
            fitz.Rect(36, 8, 1044, 724),
            stream=(REFERENCES / reference["filename"]).read_bytes(),
            keep_proportion=True,
        )
        caption = (
            "Original approved PNG embedded unchanged · PDF derivative, not original approved R01 · "
            + reference["filename"]
        )
        rc = p.insert_textbox(
            fitz.Rect(36, 735, 1044, 762), caption, fontname="SHRegular", fontsize=8, color=INK
        )
        assert rc >= 0, "R01 original caption overflow"
        toc.append([1, "Approved R01 original | " + reference["filename"], p.number + 1])
    for start in range(0, len(sites), 17):
        p = page("Location / site index")
        toc.append([1, "Site index" + (" continued" if start else ""), p.number + 1])
        for i, (s, _) in enumerate(sites[start : start + 17]):
            y = 142 + i * 30
            label = s["site_id"] + "  /  " + s["name"]
            rc = p.insert_textbox(
                fitz.Rect(36, y - 14, 1044, y + 12),
                pdf_text(label),
                fontname="SHRegular",
                fontsize=11,
                color=INK,
            )
            assert rc >= 0, "Site index label overflow"
            index_links.append((p.number, fitz.Rect(34, y - 14, 1046, y + 12), s["site_id"]))
    destinations = {}

    def append_map(m, level, label=None):
        source = fitz.open(ROOT / m["artifacts"]["pdf"]["path"])
        dest = len(doc)
        doc.insert_pdf(source)
        source.close()
        toc.append([level, (label or m["title"])[:160], dest + 1])
        return dest

    for s, _ in sites:
        sid = s["site_id"]
        ms = [m for m in current if m.get("site_id") == sid and not m.get("building_id")]
        if ms:
            destinations[sid] = append_map(ms[0], 1, s["name"])
            for m in ms[1:]:
                append_map(m, 2)
        else:
            p = page(s["name"])
            destinations[sid] = p.number
            toc.append([1, s["name"], p.number + 1])
            p.insert_textbox(
                fitz.Rect(36, 135, 1044, 690),
                s.get("floor_exemption", s["status"]),
                fontsize=12,
                fontname="SHRegular",
                color=INK,
            )
        for b in s["buildings"]:
            bm = [m for m in current if m.get("building_id") == b["id"] and not m.get("floor_id")]
            if bm:
                append_map(bm[0], 2, b["name"])
                for extra_map in bm[1:]:
                    append_map(extra_map, 3)
            else:
                toc.append([2, b["name"], len(doc) + 1])
            for f in b["floors"]:
                fm = [m for m in current if m.get("floor_id") == f["id"]]
                assert len(fm) == 1, f"floor map missing or duplicate {f['id']}"
                append_map(fm[0], 3, f["name"])
    for m in prior:
        append_map(m, 1, "Geographic context | " + m["title"])
    # Complete portable disposition register, with text wrapping and overflow check.
    p = None
    y = 0
    for r in coverage["records"]:
        lines = textwrap.wrap(
            r["id"] + " | " + r["name"] + " | " + r["status"], width=138
        ) + textwrap.wrap(r["reason"], width=158)
        height = 16 + 14 * len(lines)
        if p is None or y + height > 706:
            p = page("Coverage dispositions")
            y = 126
            if not any(t[1] == "Coverage dispositions" for t in toc):
                toc.append([1, "Coverage dispositions", p.number + 1])
        rc = p.insert_textbox(
            fitz.Rect(36, y, 1044, y + height),
            pdf_text("\n".join(lines)),
            fontsize=10,
            fontname="SHRegular",
            color=INK,
            lineheight=1.2,
        )
        assert rc >= 0, f"PDF coverage overflow {r['id']}"
        y += height + 7
    doc[0].insert_link({"kind": fitz.LINK_GOTO, "from": fitz.Rect(34, 559, 310, 585), "page": 1})
    for pn, rect, sid in index_links:
        doc[pn].insert_link({"kind": fitz.LINK_GOTO, "from": rect, "page": destinations[sid]})
    doc.set_toc(toc)
    doc.set_metadata(
        {
            "title": "Sable Harbor Facility Atlas v0.2.0 / R02",
            "author": "Sable Harbor",
            "subject": "R02 successor to approved R01; September 2026 sourced geography and labelled concept facilities",
            "creator": "geospatial/facilities/atlas.py",
            "producer": "PyMuPDF deterministic build",
        }
    )
    doc.save(PDF, garbage=4, deflate=True, no_new_id=True)
    pdf_pages = len(doc)
    doc.close()
    dependencies = [
        COVERAGE,
        FAC / "MANIFEST.json",
        *source_files,
        Path(__file__),
        REFERENCES / "MANIFEST.json",
        *FONT_FILES,
        *[REFERENCES / r["filename"] for r in reference_manifest["files"]],
    ]
    if RUNTIME.is_file():
        dependencies.append(RUNTIME)
        dependencies.extend(ROOT / path for path in load(RUNTIME)["source_sha256"])
    spatial_manifest = MAPS / "spatial/MANIFEST.json"
    if spatial_manifest.is_file():
        spatial = load(spatial_manifest)
        dependencies.append(spatial_manifest)
        node("spatial-review", "index", path="geospatial/maps/spatial.html")
        edge("atlas", "spatial-review")
        node("spatial-index", "index", path="geospatial/maps/spatial/README.md")
        edge("spatial-review", "spatial-index")
        if spatial.get("portable_pdf"):
            node("spatial-pdf", "publication", **spatial["portable_pdf"])
            edge("spatial-review", "spatial-pdf")
        for m in spatial["maps"]:
            mid = m.get("map_id", m["id"])
            node(mid, "map", title=m["title"], status=m.get("status", "MODELLED"))
            parent = m.get("floor_id") or m.get("building_id") or m["site_id"]
            edge(parent, mid)
            edge("spatial-index", mid)
            for fmt, a in m["artifacts"].items():
                aid = mid + ":" + fmt
                node(aid, "artifact", **a)
                edge(mid, aid)
    # Hash only preserved rc4 records so adding this successor to MAP_MANIFEST is not cyclic.
    graph = {
        "schema_version": "1.0.0",
        "revision": "0.2.0",
        "visual_revision": "R02_DERIVED_FROM_APPROVED_R01",
        "approved_reference_pages": [
            {
                "filename": r["filename"],
                "page": i + 2,
                "sha256": r["sha256"],
                "status": "ORIGINAL_PNG_EMBEDDED_UNCHANGED_PDF_IS_DERIVATIVE",
            }
            for i, r in enumerate(references)
        ],
        "entrypoint": rel(HTML),
        "pdf": rel(PDF),
        "pdf_pages": pdf_pages,
        "source_sha256": {rel(p): digest(p) for p in dependencies},
        "legacy_context_manifest_sha256": hashlib.sha256(
            json.dumps(prior, sort_keys=True).encode()
        ).hexdigest(),
        "nodes": list(nodes.values()),
        "edges": [{"source": a, "target": b} for a, b in sorted(edges)],
        "paths": sorted(paths),
        "coverage": coverage_links,
        "counts": {
            "coverage_records": len(coverage_links),
            "sites": len(sites),
            "buildings": len(building_lookup),
            "floors": sum(len(b["floors"]) for s, p in sites for b in s["buildings"]),
            "facility_maps": len(current),
            "legacy_context_maps": len(prior),
        },
    }
    for e in graph["edges"]:
        assert e["source"] in nodes and e["target"] in nodes, e
    (FAC / "ATLAS_LINKS.json").write_text(json.dumps(graph, indent=2) + "\n")
    md = [
        "# Facility atlas artifact index · R02 / v0.2.0",
        "",
        "[Open HTML atlas](../index.html) · [Portable bookmarked PDF](../"
        + PDF.name
        + ") · [Machine-readable link graph](ATLAS_LINKS.json)",
        "",
        "All links below refer to independently saved assets. Source statuses remain controlling.",
        "",
        "| Map | Title | Status | Assets |",
        "|---|---|---|---|",
    ]
    for m in allmaps:
        links_md = " · ".join(
            f"[{fmt.upper()}]({os.path.relpath(ROOT / a['path'], FAC)})"
            for fmt, a in m["artifacts"].items()
        )
        md.append(f"| {m['id']} | {m['title'].replace('|', '/')} | {m['status']} | {links_md} |")
    md += [
        "",
        "## Original approved Sacramento R01 references",
        "",
        "These four immutable PNGs and the recovered ZIP are approved source artifacts. This R02 PDF, HTML atlas and new plan derivatives are not original approved R01 artifacts.",
        "",
        "| Original | SHA-256 | Approval |",
        "|---|---|---|",
    ]
    for reference in references:
        md.append(
            f"| [{reference['filename']}]({os.path.relpath(REFERENCES / reference['filename'], FAC)}) | `{reference['sha256']}` | 2026-09-11; APPROVED_VISUAL_REFERENCE |"
        )
    md += [
        "",
        "[Original recovered ZIP]("
        + os.path.relpath(REFERENCES / "SABLE_HARBOR_Sacramento_HQ_Drafts_R01.zip", FAC)
        + ") · [Reference manifest/provenance]("
        + os.path.relpath(REFERENCES / "MANIFEST.json", FAC)
        + ")",
        "",
    ]
    if PRIOR_PDF.is_file():
        md += [
            "[Archived pre-R01 proposal v0.1.0](../"
            + PRIOR_PDF.name
            + ") — SUPERSEDED; earlier six-building implementation, not current or approved R01. Its draft release was withheld and never published.",
            "",
        ]
    md += [
        "",
        "Full coverage/exemptions: [coverage matrix](../../facilities/coverage/COVERAGE_MATRIX.md). Population evidence: [bridge](../../facilities/population/BRIDGE.md).",
        "",
    ]
    (FAC / "ARTIFACT_INDEX.md").write_text("\n".join(md))
    print(
        json.dumps(
            {
                "status": "PASS",
                **graph["counts"],
                "pdf_pages": pdf_pages,
                "graph_nodes": len(nodes),
                "graph_edges": len(edges),
            }
        )
    )


if __name__ == "__main__":
    main()
