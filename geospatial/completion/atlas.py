"""Publish dated map plates and site comparisons from explicit source geometry."""

import html
import json
import textwrap
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
from pypdf import PdfReader, PdfWriter
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform
from geospatial.chronology.build import ROOT, sha
from geospatial.completion.site_options import SPECS

INK = "#203b36"
ACCENT = "#a2602d"
PAPER = "#f5f2eb"
MUTED = "#596a64"


def frames(history):
    years = sorted({e["earliest"][:4] for e in history["events"]} | {"2015", "2017"})
    output = []
    for year in years:
        day = year + "-12-31" if year < "2026" else "2026-09-13"
        events = [
            e for e in history["events"] if e["earliest"] <= day and e["latest"] >= year + "-01-01"
        ]
        routes = [
            r
            for r in history["route_features"]
            if r["valid_from"] <= day and (not r["valid_to"] or day < r["valid_to"])
        ]
        output.append(
            dict(
                frame_id="HIST-" + year,
                as_of=day,
                year=year,
                event_ids=[e["event_id"] for e in events],
                route_feature_ids=[r["feature"]["id"] for r in routes],
                event_date_meaning="Events whose uncertain date bounds overlap this year; route view is as-of the labelled day.",
                geometry_basis="Accepted synthetic route intervals only; earliest alignments remain unlocated. Current ownership fields are not projected backwards.",
            )
        )
    return output


def canvas(title, subtitle):
    fig = plt.figure(figsize=(14, 9.5), facecolor=PAPER)
    fig.text(
        0.05, 0.948, "SABLE HARBOR  /  GEOGRAPHIC RESEARCH", fontsize=10, color=INK, weight="bold"
    )
    fig.text(0.05, 0.892, title, fontsize=25, color=INK, weight="bold")
    fig.text(0.05, 0.854, subtitle, fontsize=10, color=MUTED)
    fig.add_artist(plt.Line2D([0.05, 0.95], [0.832, 0.832], color=ACCENT, lw=2))
    fig.text(
        0.05,
        0.047,
        "Source-bound study • Synthetic enterprise • No survey, title or access approval",
        fontsize=8,
        color=MUTED,
    )
    return fig


def save(fig, folder, ident, title, kind, metadata):
    artifacts = {}
    for ext in ["pdf", "svg", "png"]:
        p = folder / (ident + "." + ext)
        kwargs = dict(facecolor=fig.get_facecolor())
        if ext == "pdf":
            kwargs["metadata"] = {"CreationDate": None, "ModDate": None, "Title": title}
        if ext == "svg":
            kwargs["metadata"] = {"Date": None}
        if ext == "png":
            kwargs["dpi"] = 130
        fig.savefig(p, **kwargs)
        artifacts[ext] = dict(path=p.name, sha256=sha(p.read_bytes()))
    plt.close(fig)
    return dict(map_id=ident, title=title, kind=kind, artifacts=artifacts, **metadata)


def draw_geom(ax, geom, **kwargs):
    if geom.is_empty:
        return
    if hasattr(geom, "geoms"):
        for part in geom.geoms:
            draw_geom(ax, part, **kwargs)
    elif geom.geom_type == "Polygon":
        x, y = geom.exterior.xy
        ax.fill(x, y, **kwargs)
    elif hasattr(geom, "xy"):
        x, y = geom.xy
        ax.plot(x, y, **kwargs)


def map_extent(ax, x0, x1, y0, y1):
    # Expand the geographic extent to the panel rather than crushing the panel
    # into a thin strip when the route/candidate population runs north-south.
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    width = max(x1 - x0, (y1 - y0) * 1.22)
    height = width / 1.22
    ax.set_xlim(cx - width / 2, cx + width / 2)
    ax.set_ylim(cy - height / 2, cy + height / 2)
    ax.set_aspect("equal")
    ax.ticklabel_format(style="plain", useOffset=False)
    ax.text(0.97, 0.94, "N ↑", transform=ax.transAxes, ha="right", fontsize=11, color=INK)


def build(output, history, options, access, screens):
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {"font.family": "DejaVu Sans", "svg.hashsalt": "sable-geography-requirements-v1"}
    )
    manifest = []
    temporal = frames(history)
    project = Transformer.from_crs(4326, 26913, always_xy=True).transform
    route_geoms = {
        r["feature"]["id"]: transform(project, shape(r["feature"]["geometry"]))
        for r in history["route_features"]
    }
    for frame in temporal:
        fig = canvas(
            "Geographic history / " + frame["year"],
            "Retrospective route view as of "
            + frame["as_of"]
            + " • Event dates retain source precision",
        )
        ax = fig.add_axes([0.07, 0.15, 0.51, 0.62], facecolor="#fffef9")
        for ident in frame["route_feature_ids"]:
            draw_geom(ax, route_geoms[ident], color=INK, lw=2.7)
        bounds = [g.bounds for g in route_geoms.values()]
        map_extent(
            ax,
            min(b[0] for b in bounds) - 3500,
            max(b[2] for b in bounds) + 3500,
            min(b[1] for b in bounds) - 3500,
            max(b[3] for b in bounds) + 3500,
        )
        ax.set_title("BS&T route geometry", fontsize=11, color=INK, pad=12)
        ax.set_aspect("equal")
        ax.grid(alpha=0.15)
        ax.ticklabel_format(style="plain", useOffset=False)
        ax.tick_params(labelsize=8)
        ax.set_xlabel("Easting / m · EPSG:26913", fontsize=9)
        ax.set_ylabel("Northing / m", fontsize=9)
        if not frame["route_feature_ids"]:
            ax.axis("off")
            ax.text(
                0.5,
                0.52,
                "Historical alignment\nnot established",
                ha="center",
                va="center",
                transform=ax.transAxes,
                fontsize=18,
                color=MUTED,
            )
            ax.text(
                0.5,
                0.36,
                "No current route is drawn before\nits accepted effective interval.",
                ha="center",
                transform=ax.transAxes,
                fontsize=10,
                color=MUTED,
            )
        fig.text(0.63, 0.766, "EVENTS AND OBSERVATIONS", fontsize=11, color=INK, weight="bold")
        events = [e for e in history["events"] if e["event_id"] in frame["event_ids"]]
        y = 0.718
        shown = 0
        for e in events:
            label = e["date_text"] + "  /  " + e["title"]
            lines = textwrap.wrap(label, 48)
            if y - 0.025 * len(lines) - 0.020 < 0.33:
                break
            shown += 1
            fig.text(0.63, y, "\n".join(lines), fontsize=10, color=INK, va="top")
            y -= 0.025 * len(lines) + 0.020
        if len(events) > shown:
            fig.text(
                0.63,
                y,
                f"+ {len(events) - shown} further events in FRAME_EVENTS.csv",
                fontsize=10,
                color=ACCENT,
            )
        if not events:
            fig.text(
                0.63,
                y,
                "No dated event recovered for this year.\nAbsence of a record is not proof of inactivity.",
                fontsize=10,
                color=MUTED,
            )
        fig.text(
            0.63,
            0.225,
            f"{len(frame['route_feature_ids'])} dated route segments\n{len(events)} source events / observations",
            fontsize=12,
            color=INK,
            weight="bold",
        )
        fig.text(
            0.63,
            0.135,
            "\n".join(
                textwrap.wrap(
                    "An institutional, construction or transaction date does not establish property occupancy. Early routes and unlocated events remain explicit.",
                    53,
                )
            ),
            fontsize=9,
            color=MUTED,
        )
        fig.text(
            0.05,
            0.077,
            "Source: chronology/HISTORY.json • " + history["build_revision"],
            fontsize=8,
            color=MUTED,
        )
        manifest.append(
            save(
                fig,
                output,
                frame["frame_id"],
                "History " + frame["year"],
                "HISTORICAL_SNAPSHOT",
                frame,
            )
        )
    for spec in SPECS:
        rows = [r for r in options["features"] if r["properties"]["object_id"] == spec["object_id"]]
        forward = Transformer.from_crs(4326, spec["epsg"], always_xy=True).transform
        geoms = [transform(forward, shape(r["geometry"])) for r in rows]
        fig = canvas(
            spec["name"] + " / site alternatives",
            "Three dimensioned options • Unselected fictional designs • Road/hydro/rail linework screen only",
        )
        ax = fig.add_axes([0.07, 0.16, 0.52, 0.62], facecolor="#fffef9")
        bounds = [g.bounds for g in geoms]
        x0 = min(b[0] for b in bounds) - 400
        x1 = max(b[2] for b in bounds) + 400
        y0 = min(b[1] for b in bounds) - 400
        y1 = max(b[3] for b in bounds) + 400
        for path in (ROOT / "geospatial/reference").glob(spec["prefix"] + "_*.geojson"):
            if not any(k in path.stem for k in ["roads", "rail", "hydro"]):
                continue
            for f in json.loads(path.read_text())["features"]:
                g = transform(forward, shape(f["geometry"]))
                if g.bounds[2] < x0 or g.bounds[0] > x1 or g.bounds[3] < y0 or g.bounds[1] > y1:
                    continue
                draw_geom(ax, g, color="#779fba" if "hydro" in path.stem else "#c2c6bf", lw=0.65)
        for i, (r, g) in enumerate(zip(rows, geoms), 1):
            draw_geom(ax, g, color=ACCENT, alpha=0.55)
            ax.text(
                g.centroid.x,
                g.centroid.y,
                str(i),
                color=INK,
                ha="center",
                va="center",
                weight="bold",
                fontsize=12,
            )
            line = next(a for a in access["features"] if a["properties"]["option_id"] == r["id"])
            draw_geom(ax, transform(forward, shape(line["geometry"])), color=INK, lw=1.8, ls="--")
        map_extent(ax, x0, x1, y0, y1)
        ax.ticklabel_format(style="plain", useOffset=False)
        ax.tick_params(labelsize=8)
        ax.set_xlabel(f"Easting / m · EPSG:{spec['epsg']}", fontsize=9)
        ax.set_ylabel("Northing / m", fontsize=9)
        ax.grid(alpha=0.15)
        fig.text(0.63, 0.76, "DESIGN COMPARISON", fontsize=11, color=INK, weight="bold")
        y = 0.71
        for i, r in enumerate(rows, 1):
            p = r["properties"]
            fig.text(
                0.63,
                y,
                f"Option {i}  /  {p['area_acres']:.2f} acres\n{p['width_m']:.1f} × {p['depth_m']:.1f} m\nRoad-line gap: {p['reference_access_gap_m']:.1f} m",
                fontsize=11,
                color=INK,
                va="top",
            )
            y -= 0.12
        fig.text(
            0.63,
            0.31,
            "\n".join(textwrap.wrap(spec["note"], 52)),
            fontsize=9,
            color=MUTED,
            va="top",
        )
        fig.text(
            0.63,
            0.17,
            "Selection open. Terrain, actual waterbody extent,\nproperty/occupancy, zoning, utilities and access\npermission have not been established.",
            fontsize=9,
            color=ACCENT,
        )
        manifest.append(
            save(
                fig,
                output,
                spec["object_id"] + "-OPTIONS",
                spec["name"] + " alternatives",
                "UNSELECTED_SITE_COMPARISON",
                dict(object_id=spec["object_id"], option_ids=[r["id"] for r in rows]),
            )
        )
    for row in options["features"]:
        p = row["properties"]
        spec = next(s for s in SPECS if s["object_id"] == p["object_id"])
        forward = Transformer.from_crs(4326, spec["epsg"], always_xy=True).transform
        geom = transform(forward, shape(row["geometry"]))
        cx, cy = geom.centroid.x, geom.centroid.y
        fig = canvas(
            p["name"] + " / option " + row["id"].rsplit("-", 1)[-1],
            "Dimensioned site study • Unselected alternative • " + row["id"],
        )
        ax = fig.add_axes([0.07, 0.16, 0.52, 0.62], facecolor="#fffef9")
        for path in (ROOT / "geospatial/reference").glob(spec["prefix"] + "_*.geojson"):
            if not any(k in path.stem for k in ["roads", "rail", "hydro"]):
                continue
            for f in json.loads(path.read_text())["features"]:
                g = transform(forward, shape(f["geometry"]))
                if (
                    g.bounds[2] < cx - 500
                    or g.bounds[0] > cx + 500
                    or g.bounds[3] < cy - 500
                    or g.bounds[1] > cy + 500
                ):
                    continue
                draw_geom(ax, g, color="#779fba" if "hydro" in path.stem else "#b7beb6", lw=1)
        draw_geom(ax, geom, color=ACCENT, alpha=0.5)
        connector = next(a for a in access["features"] if a["properties"]["option_id"] == row["id"])
        draw_geom(ax, transform(forward, shape(connector["geometry"])), color=INK, lw=2, ls="--")
        map_extent(ax, cx - 450, cx + 450, cy - 360, cy + 360)
        ax.tick_params(labelsize=8)
        ax.grid(alpha=0.15)
        ax.set_xlabel(f"Easting / m · EPSG:{spec['epsg']}", fontsize=9)
        ax.set_ylabel("Northing / m", fontsize=9)
        fig.text(0.63, 0.75, "EXPLICIT DESIGN GEOMETRY", fontsize=11, color=INK, weight="bold")
        fig.text(
            0.63,
            0.67,
            f"{p['width_m']:.3f} × {p['depth_m']:.3f} m\n{p['area_acres']:.2f} acres\n{p['reference_access_gap_m']:.1f} m road-line gap",
            fontsize=15,
            color=INK,
            linespacing=1.7,
            va="top",
        )
        fig.text(
            0.63,
            0.43,
            "Brown: unselected site alternative\nDashed: straight-line access test\nGray: archived transport reference\nBlue: archived hydro linework",
            fontsize=10,
            color=MUTED,
            linespacing=1.6,
        )
        fig.text(
            0.63,
            0.26,
            "No parcel is appropriated or declared owned.\nNo occupancy or public access is established.\nScreening does not establish constructability,\nflood safety, zoning or utility availability.",
            fontsize=10,
            color=ACCENT,
            linespacing=1.5,
        )
        manifest.append(
            save(
                fig,
                output,
                row["id"],
                p["name"] + " option " + row["id"].rsplit("-", 1)[-1],
                "UNSELECTED_SITE_DETAIL",
                dict(object_id=p["object_id"], option_id=row["id"]),
            )
        )
    for oid, title, stream in [
        ("SH-SITE-0023", "Kelly Gang Mining / Stream 17", "Existing separation → Stream 17"),
        ("SH-SITE-0027", "Demotte / Gen 1 recovery", "Mine water → controlled slipstream"),
    ]:
        fig = canvas(
            title,
            "Host interface schematic • Not geographically placed • Equipment authority remains distinct from host property",
        )
        ax = fig.add_axes([0.06, 0.29, 0.88, 0.48])
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 45)
        ax.axis("off")
        boxes = [
            (2, 26, 27, 12, "HOST PROCESS\n" + stream),
            (39, 26, 24, 12, "NORMAL HOST\nTREATMENT / PROCESS"),
            (73, 26, 24, 12, "HOST OUTBOUND\nPROCESS / DISCHARGE"),
            (39, 3, 24, 12, "CRADLE RECOVERY\nDefined equipment / stream"),
            (73, 3, 24, 12, "SEGREGATED PRODUCT\nGenealogy / onward delivery"),
        ]
        for x, y, w, h, label in boxes:
            ax.add_patch(Rectangle((x, y), w, h, facecolor="#e3e9df", edgecolor=INK, lw=1.5))
            ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=10, color=INK)
        for a, b in [
            ((29, 32), (39, 32)),
            ((63, 32), (73, 32)),
            ((23, 26), (39, 10)),
            ((63, 9), (73, 9)),
        ]:
            ax.add_patch(
                FancyArrowPatch(a, b, arrowstyle="->", mutation_scale=15, color=ACCENT, lw=2)
            )
        ax.text(33, 22, "Host may bypass / stop recovery", fontsize=10, color=INK)
        fig.text(
            0.08,
            0.21,
            "Host retains plant authority and ordinary process obligations.\nCradle owns the bounded recovery intervention; no host land or mine is transferred.",
            fontsize=12,
            color=INK,
        )
        fig.text(
            0.08,
            0.12,
            "Region: "
            + ("Tasmania, Australia" if oid.endswith("23") else "North-central West Virginia")
            + " • Exact host location, service access and installation date remain unresolved.",
            fontsize=10,
            color=MUTED,
        )
        manifest.append(
            save(
                fig,
                output,
                oid + "-INTERFACE",
                title,
                "UNLOCATED_HOST_INTERFACE",
                dict(object_id=oid, authority="docs/canon/CRADLE_CLOSEOUT_2026-09-06.md"),
            )
        )
    writer = PdfWriter()
    for row in manifest:
        start = len(writer.pages)
        writer.append(PdfReader(output / row["artifacts"]["pdf"]["path"]))
        writer.add_outline_item(row["title"], start)
    writer.add_metadata(
        {
            "/Title": "Sable Harbor — Historical Geography and Site Alternatives",
            "/Author": "Sable Harbor geographic source review",
        }
    )
    with (output / "HISTORICAL_AND_SITE_ATLAS.pdf").open("wb") as f:
        writer.write(f)
    (output / "MAP_SERIES.json").write_text(json.dumps(manifest, indent=2) + "\n")
    import csv

    with (output / "FRAME_EVENTS.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["frame_id", "as_of", "event_id"])
        w.writeheader()
        w.writerows(
            dict(frame_id=r["frame_id"], as_of=r["as_of"], event_id=e)
            for r in temporal
            for e in r["event_ids"]
        )
    cards = "".join(
        f'<article data-title="{html.escape(r["title"], quote=True)}"><a href="{r["artifacts"]["pdf"]["path"]}"><img loading="lazy" alt="{html.escape(r["title"], quote=True)}" src="{r["artifacts"]["png"]["path"]}"></a><h2>{html.escape(r["title"])}</h2><p>{html.escape(r["kind"].replace("_", " ").lower())}</p><a href="{r["artifacts"]["pdf"]["path"]}">PDF</a> · <a href="{r["artifacts"]["svg"]["path"]}">SVG</a></article>'
        for r in manifest
    )
    (output / "index.html").write_text(
        """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sable Harbor · Historical geography and site alternatives</title><style>body{margin:0;background:#f5f2eb;color:#203b36;font:17px/1.6 system-ui}header{background:#203b36;color:#f5f2eb;padding:38px max(24px,calc((100vw - 1200px)/2));border-bottom:5px solid #a2602d}h1{font-size:clamp(30px,4vw,48px);line-height:1.15}main{max-width:1200px;margin:auto;padding:28px}a{color:inherit}input{font:inherit;padding:12px;max-width:90%;width:420px;border:1px solid #8d9b92}section{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:24px;margin-top:24px}article{background:#fffef9;padding:15px;border:1px solid #d7dbd1}article img{width:100%}h2{font-size:20px}article p{font-size:14px}article[hidden]{display:none}</style><header><small>SABLE HARBOR / GEOGRAPHIC RESEARCH</small><h1>History, places & possibilities</h1><p>Dated source evidence and dimensioned site alternatives. Unlocated history stays visible; proposed locations remain explicit.</p></header><main><p><a href="HISTORICAL_AND_SITE_ATLAS.pdf">Download the bookmarked atlas</a> · <a href="../site-docket.html">Site evidence docket</a> · <a href="../SITE_OPTIONS.geojson">Site polygons</a> · <a href="../ACCESS_TESTS.geojson">Access tests</a> · <a href="../../chronology/history.html">Interactive chronology</a></p><label for="filter">Find a year, site or host</label><br><input id="filter" type="search" placeholder="2024, Bedford, Demotte…"><p id="count" aria-live="polite"></p><section>"""
        + cards
        + """</section></main><script>const q=document.querySelector('#filter'),cards=[...document.querySelectorAll('article')];function show(){let n=0;for(const c of cards){c.hidden=!c.dataset.title.toLowerCase().includes(q.value.toLowerCase());if(!c.hidden)n++}document.querySelector('#count').textContent=n+' map plates';}q.addEventListener('input',show);show();</script></html>"""
    )
    return manifest
