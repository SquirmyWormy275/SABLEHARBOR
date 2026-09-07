#!/usr/bin/env python3
"""Render restrained map sheets directly from the released GeoPackage.

No basemap screenshots, generated imagery, or independent cartographic geography.
"""

from __future__ import annotations
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import textwrap

import fiona
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon as Patch, Rectangle
from pyproj import Transformer
from shapely.geometry import shape, box
from shapely.ops import transform

BASE = Path(__file__).resolve().parents[1]
GPKG = BASE / "master/sable_harbor_master_v0.1.gpkg"
OUT = BASE / "maps"
INK = "#172e40"
MUTED = "#637078"
RED = "#922d35"
TEAL = "#24716d"
BLUE = "#6194af"
PAPER = "#faf9f5"
GRID = "#dce0e0"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "text.color": INK,
        "axes.labelcolor": MUTED,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.edgecolor": "#aab3b5",
        "svg.fonttype": "none",
        "svg.hashsalt": "sable-harbor-geospatial-rc1",
        "pdf.fonttype": 42,
        "hatch.linewidth": 0.45,
    }
)
CAT = json.loads((BASE / "sources/catalog.json").read_text())
LAYERS = {}
MANIFEST = []


def data(name):
    if name not in LAYERS:
        with fiona.open(GPKG, layer=name) as layer:
            LAYERS[name] = [(shape(f["geometry"]), dict(f["properties"])) for f in layer]
    return LAYERS[name]


def draw_geom(ax, g, face="none", edge=GRID, width=0.55, alpha=1, z=1, hatch=None, style="-"):
    if g.is_empty:
        return
    if g.geom_type == "Polygon":
        ax.add_patch(
            Patch(
                list(g.exterior.coords),
                facecolor=face,
                edgecolor=edge,
                linewidth=width,
                alpha=alpha,
                zorder=z,
                hatch=hatch,
                linestyle=style,
            )
        )
        for ring in g.interiors:
            ax.add_patch(
                Patch(list(ring.coords), facecolor=PAPER, edgecolor=edge, linewidth=width, zorder=z)
            )
    elif hasattr(g, "geoms"):
        for p in g.geoms:
            draw_geom(ax, p, face, edge, width, alpha, z, hatch, style)
    elif g.geom_type == "LineString":
        x, y = g.xy
        ax.plot(x, y, color=edge, linewidth=width, alpha=alpha, zorder=z, linestyle=style)
    elif g.geom_type == "Point":
        ax.plot(g.x, g.y, "o", color=edge, markersize=4, zorder=z)


def base_map(ax, area, bounds, crs, study_ids=None, small=False):
    tx = Transformer.from_crs(4326, crs, always_xy=True).transform
    window = box(*bounds)
    projected = transform(tx, window)
    xmin, ymin, xmax, ymax = projected.bounds
    ax.set_facecolor(PAPER)
    if area == "wamsutter":
        for g, p in data("ref_wyoming_counties"):
            if not g.intersects(window):
                continue
            draw_geom(
                ax,
                transform(tx, g.intersection(window)),
                face="#f0f0e9",
                edge="#bfc5c2",
                width=0.85,
            )
            if p["canonical_name"] in ["Sweetwater County", "Carbon County"]:
                q = transform(tx, g.intersection(window)).representative_point()
                ax.text(
                    q.x,
                    q.y,
                    p["canonical_name"].upper(),
                    color="#9ca49d",
                    fontsize=8 if small else 10,
                    ha="center",
                    va="center",
                    zorder=2,
                )
    for suffix, color, width in [
        ("hydro", BLUE, 0.40),
        ("local_roads", "#d0d0c9", 0.45),
        ("connecting_roads", "#b9b9b3", 0.6),
        ("secondary_roads", "#c0b8a4", 0.7),
        ("highways", "#ae9d7b", 1.0),
        ("rail", MUTED, 1.0),
    ]:
        name = "ref_" + area + "_" + suffix
        if name not in fiona.listlayers(GPKG):
            continue
        for g, p in data(name):
            if g.intersects(window):
                draw_geom(ax, transform(tx, g.intersection(window)), edge=color, width=width, z=3)
    for g, p in data("search_areas"):
        if study_ids and p["feature_id"] not in study_ids:
            continue
        if g.intersects(window):
            color = RED if p["canon_status"] == "CONFLICTING" else TEAL
            draw_geom(
                ax,
                transform(tx, g),
                face="none",
                edge=color,
                width=1.55,
                hatch="///",
                z=5,
                style="--",
            )
    for g, p in data("reference_place_labels"):
        if window.contains(g):
            q = transform(tx, g)
            ax.plot(
                q.x, q.y, "o", markerfacecolor=PAPER, markeredgecolor=INK, markersize=4, zorder=7
            )
            name = p["canonical_name"].replace(" city", "").replace(" town", "")
            ax.annotate(
                name,
                (q.x, q.y),
                xytext=(6, 5),
                textcoords="offset points",
                fontsize=8 if small else 9,
                zorder=8,
                bbox=dict(fc=PAPER, ec="none", alpha=0.9, pad=1),
            )
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal", adjustable="box")
    ax.tick_params(labelsize=7 if small else 8, length=2)
    ax.xaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(
            lambda x, pos: f"{x / 1000:.1f}" if xmax - xmin < 7000 else f"{x / 1000:.0f}"
        )
    )
    ax.yaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(
            lambda y, pos: f"{y / 1000:.1f}" if ymax - ymin < 7000 else f"{y / 1000:.0f}"
        )
    )
    ax.set_xlabel("Easting / km", fontsize=7 if small else 8, labelpad=3)
    ax.set_ylabel("Northing / km", fontsize=7 if small else 8, labelpad=3)
    ax.grid(color=GRID, linewidth=0.35, alpha=0.6, zorder=0)
    ax.annotate(
        "Grid N",
        xy=(0.08, 0.96),
        xytext=(0.08, 0.84),
        xycoords="axes fraction",
        textcoords="axes fraction",
        ha="center",
        fontsize=7,
        arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.8),
        bbox=dict(fc=PAPER, ec="none", alpha=0.8, pad=1),
        zorder=10,
    )
    scale(ax)
    return tx


def scale(ax):
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    width = xmax - xmin
    height = ymax - ymin
    target = width * 0.22
    vals = [100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000, 500000]
    length = max((v for v in vals if v <= target), default=100)
    x = xmin + width * 0.04
    y = ymin + height * 0.06
    ax.add_patch(
        Rectangle(
            (x - width * 0.012, y - height * 0.02),
            length + width * 0.10,
            height * 0.078,
            facecolor=PAPER,
            edgecolor="none",
            alpha=0.9,
            zorder=10,
        )
    )
    ax.plot([x, x + length], [y, y], color=INK, lw=2, zorder=11)
    for v in [x, x + length]:
        ax.plot([v, v], [y - height * 0.008, y + height * 0.008], color=INK, lw=0.8, zorder=11)
    ax.text(x, y + height * 0.022, "0", fontsize=7, zorder=11)
    ax.text(
        x + length, y + height * 0.022, f"{length / 1000:g} km", fontsize=7, ha="center", zorder=11
    )


def page(title, subtitle, mapid, status):
    fig = plt.figure(figsize=(15, 10), facecolor=PAPER)
    fig.text(0.04, 0.955, "SABLE HARBOR", fontsize=11, fontweight="bold", color=INK)
    fig.text(0.96, 0.955, mapid, fontsize=9, color=MUTED, ha="right", family="DejaVu Sans Mono")
    fig.text(0.04, 0.908, title, fontsize=25, fontweight="bold")
    fig.text(0.04, 0.878, subtitle, fontsize=10, color=MUTED)
    fig.add_artist(
        Line2D([0.04, 0.96], [0.858, 0.858], transform=fig.transFigure, color=INK, lw=1.0)
    )
    fig.text(0.04, 0.830, status, fontsize=9, fontweight="bold", color=RED)
    return fig


def footer(fig, crs, notes):
    fig.add_artist(
        Line2D([0.04, 0.96], [0.090, 0.090], transform=fig.transFigure, color=INK, lw=0.6)
    )
    fig.text(
        0.04, 0.070, "WORLD STATE 07 SEP 2026  |  v0.1.0-rc4  |  " + crs, fontsize=8, color=MUTED
    )
    fig.text(
        0.04,
        0.050,
        "Sources: Sable Harbor canon + owner handover; U.S. Census Bureau / USGS / FRA extracts, 06-07 Sep 2026.",
        fontsize=8,
        color=MUTED,
    )
    fig.text(0.04, 0.030, notes, fontsize=8, color=MUTED)
    fig.text(
        0.96,
        0.070,
        "CANON BASE " + CAT["source_commit"][:12],
        fontsize=8,
        color=MUTED,
        ha="right",
        family="DejaVu Sans Mono",
    )


def side(fig, blocks, x=0.73, top=0.76, width=39):
    y = top
    for title, body in blocks:
        fig.text(x, y, title.upper(), fontsize=10, fontweight="bold", color=INK)
        y -= 0.022
        lines = textwrap.wrap(body, width=width, break_long_words=False, break_on_hyphens=False)
        fig.text(x, y, "\n".join(lines), fontsize=9.5, color=MUTED, va="top", linespacing=1.45)
        y -= len(lines) * 0.0205 + 0.035


def legend(fig, x=0.735, y=0.15):
    fig.legend(
        handles=[
            Line2D([0], [0], color=TEAL, lw=1.4, ls="--", label="Analyst search envelope"),
            Line2D([0], [0], color=RED, lw=1.4, ls="--", label="Disputed source geography"),
            Line2D([0], [0], color=MUTED, lw=1, label="Real railroad reference"),
            Line2D([0], [0], color="#ae9d7b", lw=1, label="Highway / road reference"),
            Line2D([0], [0], color=BLUE, lw=1, label="Hydrography reference"),
        ],
        loc="lower left",
        bbox_to_anchor=(x, y),
        frameon=False,
        fontsize=8,
        handlelength=2.6,
    )


def save(fig, mapid, title, crs, layers_used, status):
    stamp = datetime.fromisoformat(CAT["recorded_at"])
    for ext in ["pdf", "svg", "png"]:
        kw = {"dpi": 180}
        if ext == "pdf":
            kw["metadata"] = {
                "Title": title,
                "Author": "Sable Harbor geospatial build",
                "Subject": status,
                "CreationDate": stamp,
                "ModDate": stamp,
            }
        if ext == "svg":
            kw["metadata"] = {"Date": CAT["recorded_at"], "Title": title, "Description": status}
        buffer = io.BytesIO()
        fig.savefig(buffer, format=ext, facecolor=fig.get_facecolor(), **kw)
        path = OUT / (mapid + "." + ext)
        temp = path.with_suffix(path.suffix + ".tmp")
        raw = buffer.getvalue()
        if ext == "svg":
            raw = b"\n".join(line.rstrip() for line in raw.splitlines()) + b"\n"
        temp.write_bytes(raw)
        temp.replace(path)
    m = dict(
        map_id=mapid,
        title=title,
        version="0.1.0-rc4",
        effective_date="2026-01-06"
        if mapid == "SH-MAP-BST-001_bst-pre-acquisition-system"
        else CAT["world_state_date"],
        world_state="CANON_RECONCILED_2026-09-07",
        canon_status=status,
        source_package_version=CAT["package_version"],
        source_commit=CAT["source_commit"],
        source_geopackage_sha256=hashlib.sha256(GPKG.read_bytes()).hexdigest(),
        projection=crs,
        build_timestamp=CAT["recorded_at"],
        builder="geospatial/scripts/render_maps.py",
        review_status="RENDERED_PENDING_VISUAL_QA",
        layers=layers_used,
        files={
            e: dict(
                path=mapid + "." + e,
                sha256=hashlib.sha256((OUT / (mapid + "." + e)).read_bytes()).hexdigest(),
            )
            for e in ["pdf", "svg", "png"]
        },
    )
    (OUT / (mapid + ".json")).write_text(json.dumps(m, indent=2) + "\n")
    MANIFEST.append(m)
    plt.close(fig)


def framework():
    id = "SH-MAP-ENT-001_locked-geographic-framework"
    fig = page(
        "Geographic framework",
        "Named constraints are recorded. Search-envelope vertices remain implementation proposals.",
        id,
        "GOVERNED FRAMEWORK / SITE ENGINEERING IN PROGRESS",
    )
    panels = [
        (
            "SACRAMENTO",
            "sacramento",
            [-121.515, 38.578, -121.47, 38.612],
            26910,
            ["SH-GEO-0001"],
            "HQ: Railyards / River District seam",
        ),
        (
            "PITTSBURGH",
            "hazelwood",
            [-79.975, 40.398, -79.935, 40.433],
            26917,
            ["SH-GEO-0002"],
            "The Fort / Klein lineage: GEO-C002",
        ),
        (
            "FAIRMONT AREA",
            "fairmont",
            [-80.24, 39.38, -80.04, 39.57],
            26917,
            ["SH-GEO-BEDFORD-001"],
            "Bedford: Cradle development / upgrading center",
        ),
        (
            "WYOMING",
            "wamsutter",
            [-108.45, 41.54, -106.73, 42.41],
            26913,
            ["SH-GEO-0004", "SH-GEO-0005", "SH-GEO-0006"],
            "Red Wash / Taylor / Wamsutter: approved addendum",
        ),
    ]
    for i, (title, area, bbox, crs, ids, note) in enumerate(panels):
        col = i % 2
        row = i // 2
        left = 0.08 + col * 0.47
        bottom = 0.505 - row * 0.35
        ax = fig.add_axes([left, bottom, 0.38, 0.265])
        tx = base_map(ax, area, bbox, crs, ids, small=True)
        if area == "wamsutter":
            g, p = data("red_wash_anchor")[0]
            q = tx(g.x, g.y)
            ax.plot(*q, marker="*", color=TEAL, markersize=8, zorder=12)
        fig.text(left, bottom + 0.284, title, fontsize=10, fontweight="bold")
        fig.text(left, bottom - 0.044, note + f" | EPSG:{crs}", fontsize=8, color=MUTED)
    footer(
        fig,
        "Regional NAD83 / UTM zones 10N, 17N, 13N",
        "Hatching = study envelopes, never property. Star = approved fictional Red Wash control anchor. Current addendum governs Wyoming.",
    )
    save(
        fig,
        id,
        "Locked geographic framework",
        "EPSG:26910;26917;26913",
        ["search_areas", "red_wash_anchor", "federal reference layers"],
        "CONFLICT_REVIEW",
    )


def regional(mapid, title, subtitle, area, bounds, crs, ids, blocks):
    fig = page(
        title, subtitle, mapid, "STUDY GEOGRAPHY / EXACT SITE AND PROPERTY INTEREST UNRESOLVED"
    )
    ax = fig.add_axes([0.07, 0.17, 0.62, 0.61])
    base_map(ax, area, bounds, crs, ids)
    side(fig, blocks)
    legend(fig)
    footer(
        fig,
        f"EPSG:{crs}",
        "Fictional study envelope over real reference geography. Not a cadastral boundary, site approval, or construction design.",
    )
    save(
        fig,
        mapid,
        title,
        f"EPSG:{crs}",
        ["search_areas", "ref_" + area + "_*"],
        "PROPOSED_SEARCH_AREA",
    )


def redwash():
    id = "SH-MAP-RWM-001_red-wash-context"
    fig = page(
        "Red Wash / Sweetwater County",
        "Approved fictional mine anchor: 42.22 N / 108.18 W. Full site and access geometry are separate work.",
        id,
        "CURRENT GOVERNING ADDENDUM / CARBON COUNTY PIN SUPERSEDED",
    )
    ax = fig.add_axes([0.07, 0.18, 0.62, 0.60])
    tx = base_map(
        ax,
        "wamsutter",
        [-108.40, 41.59, -107.79, 42.32],
        26913,
        ["SH-GEO-0004", "SH-GEO-0005", "SH-GEO-0006"],
    )
    for g, p in data("red_wash_anchor"):
        q = tx(g.x, g.y)
        ax.plot(*q, marker="*", markersize=12, color=TEAL, zorder=15)
        ax.annotate(
            "Red Wash\n42.22 N / 108.18 W",
            q,
            xytext=(10, 12),
            textcoords="offset points",
            fontsize=9,
            color=TEAL,
            bbox=dict(fc=PAPER, ec="none", alpha=0.95, pad=3),
            zorder=16,
        )
    side(
        fig,
        [
            (
                "Controlling decision",
                "The approved addendum locates this fictional underground uranium mine in the Great Divide Basin / Red Desert, Sweetwater County, north of Wamsutter.",
            ),
            (
                "Anchor precision",
                "The coordinate is a fictional mapping control. It is not a real mine identity, surveyed portal or property boundary.",
            ),
            (
                "Taylor and BS&T",
                "Taylor replaces the former town name and serves as the fictional railway operating hub. Approved service uses Taylor transload and truck last mile. No mine spur is included.",
            ),
            (
                "Preserved history",
                "The original Carbon County artwork and earlier derivatives are retained as superseded evidence. They no longer control current geography.",
            ),
        ],
        width=38,
    )
    footer(
        fig,
        "EPSG:26913",
        "Star = user-approved fictional anchor. Hatching = analyst study windows. See GEO-D009 through GEO-D013 and the supersession record.",
    )
    save(
        fig,
        id,
        "Red Wash current Sweetwater context",
        "EPSG:26913",
        ["search_areas", "red_wash_anchor", "ref_wyoming_counties", "ref_wamsutter_*"],
        "CANON_ANCHOR_WITH_PROPOSED_SITE_GEOMETRY",
    )


def corporate():
    id = "SH-MAP-ENT-002_corporate-geographic-census"
    fig = page(
        "Corporate geographic census",
        "Operating geography, study areas and historical context are distinct records.",
        id,
        "CITY / REGION SCALE / NOT AN OWNED-PROPERTY INVENTORY",
    )
    ax = fig.add_axes([0.055, 0.275, 0.89, 0.5])
    tx = Transformer.from_crs(4326, 5070, always_xy=True).transform
    for g, p in data("ref_us_states"):
        draw_geom(ax, transform(tx, g), face="#eeefe8", edge="#c1c8c4", width=0.55)
    labels = [
        ("Sacramento", "Headquarters", (-25, -24), TEAL),
        ("Pittsburgh", "Willow / Hazelwood study", (-20, 32), RED),
        ("Charleston", "Emberline history", (45, -40), MUTED),
        ("Fairmont", "Bedford / Cradle", (65, 8), TEAL),
    ]
    for start, caption, offset, color in labels:
        g, p = next(
            (g, p)
            for g, p in data("reference_place_labels")
            if p["canonical_name"].startswith(start)
        )
        q = tx(g.x, g.y)
        ax.plot(*q, "o", mfc=PAPER, mec=color, ms=6, zorder=8)
        ax.annotate(
            start + "\n" + caption,
            q,
            xytext=offset,
            textcoords="offset points",
            ha="right" if offset[0] < 0 else "left",
            fontsize=9,
            color=color,
            arrowprops=dict(arrowstyle="-", color=color, lw=0.6),
            bbox=dict(fc=PAPER, ec="none", alpha=0.95, pad=3),
            zorder=9,
        )
    for g, p in data("search_areas"):
        if p["feature_id"] == "SH-GEO-0004":
            gp = transform(tx, g)
            draw_geom(ax, gp, edge=RED, width=1.2, hatch="///", z=8)
            q = gp.centroid
            ax.annotate(
                "Red Wash / Taylor / BS&T\nSweetwater / approved mine anchor",
                (q.x, q.y),
                xytext=(24, 30),
                textcoords="offset points",
                fontsize=9,
                color=RED,
                arrowprops=dict(arrowstyle="-", color=RED, lw=0.6),
                bbox=dict(fc=PAPER, ec="none", alpha=0.9, pad=3),
                zorder=9,
            )
    nv = next(g for g, p in data("ref_us_states") if p["canonical_name"] == "Nevada")
    draw_geom(ax, transform(tx, nv), face="none", edge=MUTED, width=0.7, hatch="..", z=5)
    q = transform(tx, nv).representative_point()
    ax.text(
        q.x,
        q.y,
        "NEVADA\nBlackridge / 2015\nCopper client / 2016",
        ha="center",
        va="center",
        fontsize=8,
        color=MUTED,
        zorder=8,
        bbox=dict(fc=PAPER, ec="none", alpha=0.8, pad=2),
    )
    ax.set_xlim(-2550000, 2350000)
    ax.set_ylim(200000, 3200000)
    ax.set_aspect("equal")
    ax.set_axis_off()
    scale(ax)
    fig.text(0.06, 0.220, "REGISTERED, UNLOCATED", fontsize=10, fontweight="bold")
    fig.text(
        0.06,
        0.183,
        "J2 Education campus • J2 accommodation • Alexandria hosting • early railway alignments\nCradle host parcels • historical offices • provisional Reno / Elko / Tucson offices",
        fontsize=10,
        color=MUTED,
        linespacing=1.5,
    )
    fig.text(0.62, 0.220, "INTERNATIONAL HISTORY", fontsize=10, fontweight="bold")
    fig.text(
        0.62,
        0.183,
        "2022: Sar-e-Sang / Badakhshan, Afghanistan\n2024: South Australia; Mole Creek / Deloraine, Tasmania",
        fontsize=10,
        color=MUTED,
        linespacing=1.5,
    )
    footer(
        fig,
        "EPSG:5070",
        "Open circles locate municipalities, not facilities. Nevada shading is regional historical context. Real venues are not company property.",
    )
    save(
        fig,
        id,
        "Corporate geographic census",
        "EPSG:5070",
        ["ref_us_states", "reference_place_labels", "search_areas", "object_registry"],
        "CONSTRAINED_CENSUS",
    )


def questions():
    id = "SH-MAP-ENT-003_open-geographic-questions"
    fig = page(
        "Open geographic questions",
        "Source conflicts and unknown physical locations remain visible, without invented pins.",
        id,
        "DECISION REVIEW / INITIAL PROGRAM INCOMPLETE",
    )
    ax = fig.add_axes([0.065, 0.405, 0.42, 0.365])
    tx = base_map(
        ax,
        "wamsutter",
        [-108.5, 41.52, -106.65, 42.52],
        26913,
        ["SH-GEO-0004", "SH-GEO-0005", "SH-GEO-0006"],
        small=True,
    )
    g, p = data("red_wash_anchor")[0]
    q = tx(g.x, g.y)
    ax.plot(*q, marker="*", color=TEAL, markersize=9, zorder=12)
    ax.annotate(
        "Approved Red Wash anchor",
        q,
        xytext=(10, 10),
        textcoords="offset points",
        ha="left",
        fontsize=8,
        color=TEAL,
        bbox=dict(fc=PAPER, ec="none", alpha=0.9, pad=2),
        zorder=12,
    )
    ax = fig.add_axes([0.565, 0.405, 0.36, 0.365])
    base_map(
        ax, "hazelwood", [-79.978, 40.396, -79.930, 40.435], 26917, ["SH-GEO-0002"], small=True
    )
    fig.text(0.065, 0.790, "GEO-C003 / ENGINEERING GATES — WYOMING", fontsize=10, fontweight="bold")
    fig.text(0.565, 0.790, "GEO-C002 — PITTSBURGH", fontsize=10, fontweight="bold")
    side(
        fig,
        [
            (
                "Red Wash and BS&T",
                "The mine anchor and Taylor name are approved. ARU closes on 07 Jan 2026. Taylor hub and truck last mile are approved; no mine spur. Current industrial sources supply 40 rail miles, two branches and nine-mile truck access. Final survey and early historical alignments remain separate.",
            )
        ],
        x=0.065,
        top=0.335,
        width=66,
    )
    side(
        fig,
        [
            (
                "Klein and Willow",
                "The Fort and its shed functions are locked. The historical outside-Pittsburgh Klein shop remains unlocated. Same-site continuity or relocation to Hazelwood is not established.",
            )
        ],
        x=0.565,
        top=0.335,
        width=54,
    )
    fig.text(0.065, 0.142, "UNLOCATED REGISTER", fontsize=9, fontweight="bold")
    fig.text(
        0.23,
        0.142,
        "J2 campus / historical offices / early railway / Cradle host parcels / exact Blackridge site",
        fontsize=9,
        color=MUTED,
    )
    footer(
        fig,
        "EPSG:26913 / 26917",
        "Hatching = study geography; red = conflict. Star = approved fictional anchor. Full questions and implications are in the decision register.",
    )
    save(
        fig,
        id,
        "Open geographic questions",
        "EPSG:26913;26917",
        [
            "search_areas",
            "red_wash_anchor",
            "federal reference layers",
            "conflicts",
            "object_registry",
        ],
        "CONFLICT_REVIEW",
    )


def rail_sheet(engineering=False):
    ops = json.loads((BASE.parent / "industrial/source/operations.json").read_text())
    mapid = (
        "SH-MAP-BST-002_bst-engineering-alignment"
        if engineering
        else "SH-MAP-BST-001_bst-pre-acquisition-system"
    )
    title = "BS&T / accepted case geography" if engineering else "BS&T / pre-acquisition case"
    fig = page(
        title,
        "Candidate A / two external-customer branches / Taylor transload / truck-only Red Wash access",
        mapid,
        "ACCEPTED SYNTHETIC CASE / NO SURVEY OR REAL LAND-RIGHTS CLAIM",
    )
    ax = fig.add_axes([0.065, 0.18, 0.60, 0.60])
    tx = base_map(ax, "wamsutter", [-108.38, 41.62, -107.82, 42.30], 26913, ["NONE"])
    for g, p in data("rail_segments"):
        draw_geom(
            ax, transform(tx, g), edge=INK if p["route_id"] == "BST-MAIN" else TEAL, width=1.7, z=10
        )
    if engineering:
        for g, p in data("roads"):
            draw_geom(ax, transform(tx, g), edge=RED, width=1.4, style="--", z=10)
        for g, p in data("rail_bridges") + data("rail_crossings"):
            q = transform(tx, g)
            ax.plot(q.x, q.y, ".", color=MUTED, ms=3, zorder=10)
    labels = [
        ("Wamsutter", ops["geography"]["wamsutter_junction_lon_lat"]),
        ("Taylor", ops["geography"]["taylor_lon_lat"]),
        ("Red Wash", ops["geography"]["red_wash_lon_lat"]),
    ]
    for name, xy in labels:
        q = tx(*xy)
        ax.plot(*q, marker="*" if name == "Red Wash" else "o", color=TEAL, ms=8, zorder=12)
        ax.annotate(
            name,
            q,
            xytext=(7, 8),
            textcoords="offset points",
            fontsize=9,
            bbox=dict(fc=PAPER, ec="none", alpha=0.9, pad=2),
            zorder=13,
        )
    if engineering:
        blocks = [
            (
                "Measured system",
                "33.3485 mainline miles + 4.0000 East Materials + 2.6515 Mineral Transfer = 40.0000 route-miles. Yard tracks excluded.",
            ),
            (
                "Mine interface",
                "Nine-mile modeled truck-only road. No mine rail spur. Uranium custody remains OPEN_GATED; inbound logistics does not approve outbound uranium transport.",
            ),
            (
                "Imported estate",
                "12 facilities, 31 track-register segments, 26 structures. Geometry and roles derive from the accepted industrial source, including the Rawlins truck-served estate.",
            ),
            (
                "Engineering limits",
                "Screening geometry, synthetic structures and source dates do not certify survey, load rating, land title or a real UP operating agreement.",
            ),
        ]
    else:
        blocks = [
            (
                "Temporal cut",
                "06 Jan 2026, before SHIH acquired ARU on 07 Jan. Current track is the accepted case reconstruction, with explicit synthetic opening dates.",
            ),
            (
                "History retained",
                "1898 coal origin; 1954 rescue; 1968 Taylor mainline; 1972 East Materials; 1986 Mineral Transfer; ARU parent from 1991.",
            ),
            (
                "No backfill",
                "1898 alignment and the surviving 14-16 miles in 1954 remain unlocated. Modern 40-mile geometry is not a measured early railway.",
            ),
            (
                "Mine separation",
                "Red Wash is outside ARU. All 2025 mine movements remain external-carrier. The 2026 inbound interface and receiving facility are not shown as pre-acquisition operation.",
            ),
        ]
    side(fig, blocks, x=0.71, width=41)
    footer(
        fig,
        "EPSG:26913 (retained regional comparison CRS)",
        "Navy/teal = synthetic rail case. Red dashed = truck-only case road. Current source: industrial/source/operations.json.",
    )
    save(
        fig,
        mapid,
        title,
        "EPSG:26913",
        ["rail_segments", "roads", "rail_nodes", "rail_bridges", "rail_crossings"],
        "LOCKED_DERIVED_IMPLEMENTATION" if engineering else "PRE_ACQUISITION_CASE_2026_01_06",
    )


def mine_site():
    mapid = "SH-MAP-RWM-002_red-wash-site-study"
    fig = page(
        "Red Wash / surface site study",
        "Functional planning zones around the approved fictional control anchor; no surveyed portal or property boundary.",
        mapid,
        "PROPOSED SITE GEOMETRY / GOVERNING ANCHOR LOCKED",
    )
    ax = fig.add_axes([0.065, 0.18, 0.61, 0.60])
    tx = base_map(ax, "wamsutter", [-108.194, 42.210, -108.166, 42.230], 26913, ["NONE"])
    for label in list(ax.texts):
        if "COUNTY" in label.get_text():
            label.remove()
    for g, p in data("spatial_assets"):
        if p["feature_id"].startswith("SITE-RW"):
            draw_geom(ax, transform(tx, g), face="none", edge=TEAL, width=1.5, hatch="///", z=6)
    for g, p in data("facilities"):
        draw_geom(ax, transform(tx, g), face="#e6eee5", edge=TEAL, width=1, z=7)
        center = transform(tx, g).representative_point()
        label = (
            p["canonical_name"]
            .replace(" planning zone", "")
            .replace(" study zone", "")
            .replace(" siting study zone", "")
        )
        ax.text(
            center.x,
            center.y,
            "\n".join(textwrap.wrap(label, 20)),
            ha="center",
            va="center",
            fontsize=7,
            zorder=9,
        )
    for g, p in data("red_wash_anchor"):
        q = tx(g.x, g.y)
        ax.plot(*q, marker="*", ms=11, color=TEAL, zorder=12)
        ax.annotate(
            "Approved map control",
            q,
            xytext=(8, 7),
            textcoords="offset points",
            fontsize=8,
            zorder=13,
            bbox=dict(fc=PAPER, ec="none", alpha=0.9, pad=2),
        )
    side(
        fig,
        [
            (
                "Geographic correction",
                "Sweetwater County / Great Divide Basin / Red Desert; anchor 42.22 N, 108.18 W. The prior Carbon County image geography is superseded.",
            ),
            (
                "Surface envelope",
                "A 1,000 by 800 m phase-one planning window, about 198 acres. It is not the old scenario's property or disturbance acreage and is not a lease boundary.",
            ),
            (
                "Zone purpose",
                "Processing, administration/workshops, water management and portal siting zones organize further study. Their dimensions are analyst proposals, not recovered image coordinates.",
            ),
            (
                "Engineering remaining",
                "Geology at the new anchor, decline/portal position, process design, waste facilities, setbacks, access, truck access from Taylor, utilities and legal land interests remain open.",
            ),
        ],
        x=0.72,
        width=39,
    )
    footer(
        fig,
        "EPSG:26913",
        "Hatching = proposed surface-study envelope. Green polygons = functional study zones. Star = approved anchor. No property title or construction approval.",
    )
    save(
        fig,
        mapid,
        "Red Wash surface site study",
        "EPSG:26913",
        ["spatial_assets", "facilities", "red_wash_anchor", "ref_wamsutter_*"],
        "PROPOSED_SITE_GEOMETRY",
    )


def main():
    OUT.mkdir(exist_ok=True)
    framework()
    corporate()
    redwash()
    regional(
        "SH-MAP-SAC-001_headquarters-context",
        "Sacramento headquarters",
        "Railyards / River District seam; fictional campus envelope still to be selected.",
        "sacramento",
        [-121.516, 38.578, -121.466, 38.614],
        26910,
        ["SH-GEO-0001"],
        [
            (
                "Locked direction",
                "Sacramento headquarters with an advanced research and industrial institutional character.",
            ),
            (
                "Working scale",
                "8-15 acres. The hatched area is a district search window, not that campus footprint.",
            ),
            (
                "Real constraints",
                "Rail corridors, local streets, river setting and an active redevelopment district. Public data does not convey real parcel title.",
            ),
            (
                "Site work remaining",
                "Screen current parcels, occupied facilities, planned projects, levee/flood context and access before selecting a footprint.",
            ),
        ],
    )
    regional(
        "SH-MAP-WIL-001_fort-hazelwood-context",
        "The Fort / Willow",
        "Pittsburgh industrial compound; Klein's earlier shop history is separately preserved.",
        "hazelwood",
        [-79.978, 40.396, -79.930, 40.435],
        26917,
        ["SH-GEO-0002"],
        [
            (
                "Locked site concept",
                "10-20 acres. Big Shed: research and laboratory. Small Shed: administration and temporary lodging.",
            ),
            (
                "Operational grounds",
                "White Shed: controlled intake, storage and quarantine. The Museum: working yards and retained industrial artifacts.",
            ),
            (
                "Historical precision",
                "Klein's earlier shop was outside Pittsburgh. Exact Fort parcel and occupancy continuity are not established; GEO-C002 remains narrow.",
            ),
            (
                "Real-site boundary",
                "Hazelwood is retained as a study district. No real tenant, parcel, lease, or development is claimed.",
            ),
        ],
    )
    regional(
        "SH-MAP-CRD-001_bedford-fairmont-context",
        "Bedford / Cradle",
        "Fairmont-area development, integration and upgrading center; separate from field deployments.",
        "fairmont",
        [-80.24, 39.38, -80.04, 39.57],
        26917,
        ["SH-GEO-BEDFORD-001"],
        [
            (
                "Locked direction",
                "Bedford: a fictional 15-20 acre redeveloped industrial brownfield near Fairmont in north-central West Virginia.",
            ),
            (
                "Distinct field hosts",
                "Demotte: north-central WV AMD treatment host. Kelly Gang Mining: Tasmanian Stream 17 host. Neither is the Bedford center.",
            ),
            (
                "Supersession",
                "Belle / Kanawha was an earlier site proposal. It is preserved as editorial history, not current Cradle geography or a relocation event.",
            ),
            (
                "Implementation remaining",
                "Exact parcel, industrial access, utilities and brownfield constraints. Dedicated rail or barge access is not selected.",
            ),
        ],
    )
    regional(
        "SH-MAP-BST-001_wamsutter-interchange-study",
        "Wamsutter interchange study",
        "Real railroad context for a accepted fictional interface; real UP geometry remains reference only.",
        "wamsutter",
        [-108.14, 41.62, -107.86, 41.74],
        26913,
        ["SH-GEO-0006"],
        [
            (
                "Real host corridor",
                "FRA rail records around Wamsutter identify UP ownership. The reference geometry remains Union Pacific infrastructure.",
            ),
            (
                "Fictional scope",
                "Accepted case: Wamsutter connection, 18-acre envelope and synthetic interchange agreement; no actual UP rights.",
            ),
            (
                "Historical boundary",
                "All 2025 mine movements remain external-carrier. The later mine interface is truck-only.",
            ),
            (
                "Next engineering gate",
                "Candidate A and January 7 acquisition are settled. Survey and real land/operating rights are not certified.",
            ),
        ],
    )
    questions()
    mine_site()
    rail_sheet()
    rail_sheet(engineering=True)
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()
    for m in MANIFEST:
        writer.append(PdfReader(OUT / (m["map_id"] + ".pdf")))
    writer.add_metadata(
        {
            "/Title": "Sable Harbor geographic framework atlas v0.1.0-rc4",
            "/Author": "Sable Harbor geospatial build",
        }
    )
    with (OUT / "SABLE_HARBOR_Geographic_Framework_Atlas_v0.1.0-rc4.pdf").open("wb") as f:
        writer.write(f)
    (OUT / "MAP_MANIFEST.json").write_text(json.dumps(MANIFEST, indent=2) + "\n")
    print(f"Rendered {len(MANIFEST)} map sheets in PDF/SVG/PNG plus the atlas.")


if __name__ == "__main__":
    main()
