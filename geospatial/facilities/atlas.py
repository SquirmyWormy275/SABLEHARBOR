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

ROOT = Path(__file__).resolve().parents[2]
MAPS = ROOT / "geospatial/maps"
FAC = MAPS / "facilities"
HTML = MAPS / "index.html"
PDF = MAPS / "SABLE_HARBOR_Facility_Atlas_v0.1.0.pdf"
COVERAGE = ROOT / "geospatial/facilities/coverage/COVERAGE_MATRIX.json"


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
    """Base-14 PDF font punctuation equivalents; HTML retains exact Unicode."""
    return str(value).translate(str.maketrans({"—": " - ", "–": "-", "“": '"', "”": '"', "’": "'"}))


def main():
    coverage = load(COVERAGE)
    current, prior = normal_maps()
    allmaps = current + prior
    source_files = sorted((ROOT / "geospatial/facilities/source").glob("*.json"))
    sites = []
    for p in source_files:
        source = load(p)
        for s in source.get("sites", [source] if "site_id" in source else []):
            sites.append((s, p))
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
        return (
            f'<article class="map" id="map-{esc(m["id"])}"><h4>{esc(m["title"])}</h4><p class="meta">{esc(m["id"])} · {esc(m["status"])}</p><p>{links(m)}</p>'
            + (
                f'<a href="{href(m["artifacts"]["png"]["path"])}"><img loading="lazy" src="{href(m["artifacts"]["png"]["path"])}" alt="{esc(m["title"])}"></a>'
                if preview and "png" in m["artifacts"]
                else ""
            )
            + "</article>"
        )

    out = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sable Harbor facility atlas</title><style>',
        "body{margin:0;background:#f1f2f2;color:#20282b;font:16px/1.5 system-ui,sans-serif}header{background:#152329;color:#fff;padding:36px max(24px,calc((100% - 1200px)/2))}main{max-width:1200px;margin:auto;padding:24px}h1,h2,h3,h4{line-height:1.25}a{color:#225d72}header a{color:#cae5ed}.meta{font-size:13px;overflow-wrap:anywhere;color:#59676b}details,article.record{background:white;border:1px solid #cbd2d4;border-radius:4px;padding:16px;margin:14px 0}summary{font-weight:650;cursor:pointer}img{width:100%;height:auto;display:block}.map{padding:12px;background:#f8f9f9;margin:12px 0}.tag{display:inline-block;font-size:12px;background:#e4e9eb;padding:3px 8px;margin:4px}.historical{border-left:5px solid #897565}.external{border-left:5px solid #6277a1}.unresolved,.proposed{border-left:5px solid #a57e37}input,select{font:inherit;padding:10px;border:1px solid #89999e;max-width:100%}.filters{display:flex;gap:12px;flex-wrap:wrap}nav ul{columns:2;padding-left:22px}@media(max-width:700px){nav ul{columns:1}main{padding:12px}}[hidden]{display:none!important}</style></head><body>",
        '<header id="top"><h1>SABLE HARBOR<br>Facility atlas</h1><p>September 2026 · Source-based context and clearly labelled concept plans</p><p><a href="'
        + esc(PDF.name)
        + '">Portable PDF atlas</a> · <a href="facilities/ARTIFACT_INDEX.md">Complete artifact index</a> · <a href="facilities/ATLAS_LINKS.json">Link graph</a></p></header><main>',
        "<p>Follow a location to its site plan, buildings and separately saved floor images. Existing geographic context remains rc4; concept layouts do not establish ownership, construction completion or actual occupancy. Historical, external and unresolved records retain explicit dispositions without invented map pins.</p>",
        f"<p>{len(sites)} modelled site packages · {len(building_lookup)} buildings · {sum(len(b[1]['floors']) for b in building_lookup.values())} floors · {len(coverage['records'])} coverage dispositions</p>",
        "<nav><h2>Locations and sites</h2><ul>",
    ]
    out += [f'<li><a href="#{esc(s["site_id"])}">{esc(s["name"])}</a></li>' for s, p in sites]
    out += [
        '</ul><p><a href="#contexts">Geographic context</a> · <a href="#coverage">All coverage records</a></p></nav>'
    ]
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
        out.extend(card(m) for m in current if m.get("site_id") == sid and not m.get("building_id"))
        if s.get("floor_exemption"):
            out.append(
                "<p><strong>Floor disposition:</strong> " + esc(s["floor_exemption"]) + "</p>"
            )
        for b in s["buildings"]:
            out.append(
                f'<details id="{esc(b["id"])}"><summary>{esc(b["name"])} · {len(b["floors"])} modelled floors</summary><p class="meta">{esc(b["id"])} · {esc(b["status"])}</p>'
            )
            out.extend(
                card(m, False)
                for m in current
                if m.get("building_id") == b["id"] and not m.get("floor_id")
            )
            for f in b["floors"]:
                out.append(
                    f'<section id="{esc(f["id"])}"><h3>{esc(f["name"])}</h3><p class="meta">{esc(f["id"])} · {f["gross_area_m2"]:,.1f} m² gross · {f["planned_peak"]} planned peak · {esc(f["status"])}</p>'
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
        '</section></main><script>const rows=[...document.querySelectorAll(".record")];function filter(){const q=document.querySelector("#query").value.toLowerCase(),c=document.querySelector("#class").value;let n=0;rows.forEach(r=>{r.hidden=!(r.textContent.toLowerCase().includes(q)&&(!c||r.dataset.class===c));if(!r.hidden)n++});document.querySelector("#shown").textContent=n+" records shown"}document.querySelector("#query").addEventListener("input",filter);document.querySelector("#class").addEventListener("change",filter);function reveal(){let e=document.getElementById(decodeURIComponent(location.hash.slice(1)));while(e){if(e.tagName==="DETAILS")e.open=true;e=e.parentElement}}window.addEventListener("hashchange",reveal);filter();reveal();</script></body></html>'
    )
    HTML.write_text("\n".join(out) + "\n")
    # PDF index is linked to imported independently saved maps, never rasterized pages.
    doc = fitz.open()
    toc = []
    index_links = []

    def page(title):
        p = doc.new_page(width=842, height=595)
        p.draw_rect(fitz.Rect(0, 0, 842, 68), color=None, fill=(0.08, 0.14, 0.16))
        p.insert_text((30, 43), pdf_text(title), fontsize=18, color=(1, 1, 1))
        return p

    p = page("SABLE HARBOR | Facility atlas")
    toc.append([1, "Facility atlas", 1])
    p.insert_textbox(
        fitz.Rect(30, 95, 810, 230),
        "September 2026 | Concept layouts and source dispositions\n\nIndividual site, building and floor drawings remain saved independently.\nPlan status is explicit: no construction, ownership or actual occupancy is inferred.\nUse bookmarks or the linked site index. Geographic context rc4 remains preserved.",
        fontsize=13,
    )
    for start in range(0, len(sites), 17):
        p = page("Location / site index")
        toc.append([1, "Site index" + (" continued" if start else ""), p.number + 1])
        for i, (s, _) in enumerate(sites[start : start + 17]):
            y = 95 + i * 27
            label = s["site_id"] + " | " + s["name"]
            p.insert_text((30, y), pdf_text(label[:115]), fontsize=10)
            index_links.append((p.number, fitz.Rect(28, y - 12, 814, y + 5), s["site_id"]))
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
                fitz.Rect(30, 95, 810, 520), s.get("floor_exemption", s["status"]), fontsize=12
            )
        for b in s["buildings"]:
            bm = [m for m in current if m.get("building_id") == b["id"] and not m.get("floor_id")]
            if bm:
                append_map(bm[0], 2, b["name"])
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
            r["id"] + " | " + r["name"] + " | " + r["status"], width=120
        ) + textwrap.wrap(r["reason"], width=140)
        height = 14 + 12 * len(lines)
        if p is None or y + height > 565:
            p = page("Coverage dispositions")
            y = 92
            if not any(t[1] == "Coverage dispositions" for t in toc):
                toc.append([1, "Coverage dispositions", p.number + 1])
        rc = p.insert_textbox(
            fitz.Rect(30, y, 810, y + height),
            pdf_text("\n".join(lines)),
            fontsize=9,
            lineheight=1.2,
        )
        assert rc >= 0, f"PDF coverage overflow {r['id']}"
        y += height + 7
    for pn, rect, sid in index_links:
        doc[pn].insert_link({"kind": fitz.LINK_GOTO, "from": rect, "page": destinations[sid]})
    doc.set_toc(toc)
    doc.set_metadata(
        {
            "title": "Sable Harbor Facility Atlas v0.1.0",
            "author": "Sable Harbor",
            "subject": "September 2026 sourced geography and labelled concept facilities",
            "creator": "geospatial/facilities/atlas.py",
            "producer": "PyMuPDF deterministic build",
        }
    )
    doc.save(PDF, garbage=4, deflate=True, no_new_id=True)
    pdf_pages = len(doc)
    doc.close()
    dependencies = [COVERAGE, FAC / "MANIFEST.json", *source_files, Path(__file__)]
    # Hash only preserved rc4 records so adding this successor to MAP_MANIFEST is not cyclic.
    graph = {
        "schema_version": "1.0.0",
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
        "# Facility atlas artifact index",
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
