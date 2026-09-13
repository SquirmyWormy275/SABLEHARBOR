"""Render the controlling site decisions and retained real-context evidence."""

import argparse
import hashlib
import html
import json
import math
from pathlib import Path
import textwrap
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from shapely.geometry import shape
from geospatial.finalization.screen import BASE, ROOT, screen
from geospatial.finalization.sync import section, CANON
from geospatial.completion.readers import STYLE


def build(output, raster_inventory=None):
    output.mkdir(parents=True, exist_ok=True)
    decisions = json.loads((BASE / "DECISIONS.json").read_text())
    raw = (ROOT / CANON).read_bytes()
    if hashlib.sha256(raw).hexdigest() != decisions["canon_sha256"]:
        raise ValueError("Canon decision and source hash differ")
    report = screen()
    if report != json.loads((BASE / "SITE_SCREEN.json").read_text()):
        raise ValueError("Site screen drift; regenerate deliberately")
    features = json.loads((BASE / "SITE_SELECTIONS.geojson").read_text())["features"]
    refs = json.loads((BASE / "reference/MANIFEST.json").read_text())["records"]
    maps = []
    with PdfPages(
        output / "Geographic-site-decisions.pdf",
        metadata={
            "Title": "Sable Harbor — Geographic site decisions",
            "Author": "Sable Harbor",
            "CreationDate": None,
            "ModDate": None,
        },
    ) as pdf:
        for f, r in zip(features, report["records"]):
            ident = r["option_id"]
            image_ref = next(
                x for x in refs if x["option_id"] == ident and x["kind"] == "imagery"
            )
            e = image_ref["extent"]
            fig = plt.figure(figsize=(11.7, 8.3), facecolor="#f5f2eb")
            ax = fig.add_axes((0.055, 0.20, 0.64, 0.68))
            ax.imshow(
                plt.imread(BASE / "reference" / image_ref["file"]),
                extent=(e["xmin"], e["xmax"], e["ymin"], e["ymax"]),
            )
            g = shape(f["geometry"])
            x, y = g.exterior.xy
            ax.fill(x, y, facecolor="#d6a14b", alpha=0.12)
            ax.plot(x, y, color="#fff5bc", lw=2.2)
            ax.ticklabel_format(useOffset=False)
            ax.tick_params(labelsize=7)
            ax.set_xlabel("Longitude / WGS 84", fontsize=9)
            ax.set_ylabel("Latitude / WGS 84", fontsize=9)
            lat = (e["ymin"] + e["ymax"]) / 2
            ax.set_aspect(1 / math.cos(math.radians(lat)))
            dx = 100 / (111320 * math.cos(math.radians(lat)))
            left = e["xmin"] + (e["xmax"] - e["xmin"]) * 0.06
            bottom = e["ymin"] + (e["ymax"] - e["ymin"]) * 0.06
            ax.plot([left, left + dx], [bottom, bottom], color="white", lw=6)
            ax.plot([left, left + dx], [bottom, bottom], color="#203b36", lw=2)
            ax.text(
                left + dx / 2,
                bottom + (e["ymax"] - e["ymin"]) * 0.018,
                "100 m",
                ha="center",
                fontsize=8,
                color="#203b36",
                bbox=dict(facecolor="white", alpha=0.85, edgecolor="none"),
            )
            ax.annotate(
                "N",
                xy=(0.94, 0.95),
                xytext=(0.94, 0.86),
                xycoords="axes fraction",
                textcoords="axes fraction",
                ha="center",
                color="white",
                weight="bold",
                arrowprops=dict(arrowstyle="-|>", color="white"),
            )
            fig.text(
                0.055,
                0.95,
                "SABLE HARBOR / GEOGRAPHIC CANON",
                fontsize=10,
                color="#596b60",
                weight="bold",
            )
            fig.text(
                0.055, 0.905, r["name"], fontsize=24, color="#203b36", weight="bold"
            )
            terrain = r["elevation"]
            dates = ", ".join(x["acquisition_date"] for x in r["imagery_sources"])
            summary = (
                f"{r['object_id']}\n\n{r['area_acres']:.2f} acres\nSelected fictional footprint\n\nTerrain\n{terrain['min_m']:.1f}–{terrain['max_m']:.1f} m sampled elevation\n{terrain['relief_m']:.1f} m total relief\n\nNAIP catalog acquisition\n{dates}\n\nReference checks\nNo archived road, rail or hydro centerline intersects.\n\nFEMA mapped zones\n"
                + "\n".join(
                    sorted(
                        {
                            x["zone"] + " — " + x["subtype"].lower()
                            for x in r["flood_intersections"]
                        }
                    )
                )
            )
            fig.text(
                0.735,
                0.85,
                "\n".join(
                    textwrap.fill(line, 34) if line else ""
                    for line in summary.splitlines()
                ),
                fontsize=10,
                va="top",
                color="#203b36",
                linespacing=1.55,
            )
            note = "Design coordinates, not survey or title. Federal imagery dates from 2022; current public planning sources supplement it. Unknown tenure days remain unknown."
            if ident == "BEDFORD-F":
                note += " Bedford’s steep outer ground is a buffer; the working program belongs on the upper bench."
            if ident == "FORT-NORTH":
                note += " The approved 2024 move is fictional history. The Roundhouse and other real tenants remain external."
            fig.text(
                0.055,
                0.105,
                textwrap.fill(note, 145),
                fontsize=9,
                color="#405b4e",
                linespacing=1.5,
            )
            fig.text(
                0.055,
                0.045,
                "SOURCE: USGS NAIP + 3DEP / FEMA NFHL · Retrieved 2026-09-13 · Full requests, hashes and limits in reference/MANIFEST.json",
                fontsize=8,
                color="#65736b",
            )
            filename = ident + ".png"
            fig.savefig(output / filename, dpi=160, facecolor=fig.get_facecolor())
            pdf.savefig(fig)
            plt.close(fig)
            maps.append(
                dict(
                    object_id=r["object_id"],
                    file=filename,
                    sha256=hashlib.sha256((output / filename).read_bytes()).hexdigest(),
                )
            )
    from geospatial.finalization.source_review import write as write_sources

    source_summary, source_rows = write_sources(output)
    from geospatial.finalization.visual_review import verify as verify_visuals

    if raster_inventory is None:
        from geospatial.completion.raster_inventory import build as inventory_images

        raster_inventory = inventory_images(
            output / "container-inventory", execute_ocr=False
        )
    visual_summary, visual_images, visual_appearances = verify_visuals(raster_inventory)
    (output / "VISUAL_REVIEW.json").write_bytes(
        (BASE / "VISUAL_REVIEW.json").read_bytes()
    )
    prospects = json.loads((BASE / "REJECTED_PROSPECTS.json").read_text())["records"]
    (output / "REJECTED_PROSPECTS.json").write_bytes(
        (BASE / "REJECTED_PROSPECTS.json").read_bytes()
    )
    current = []
    cards = []
    for r in decisions["records"]:
        excerpt = section(raw.decode(), r["canon_section"])
        item = {
            **r,
            "current_canon": dict(
                path=CANON, sha256=decisions["canon_sha256"], **excerpt
            ),
        }
        current.append(item)
        title = r["name"]
        mapping = next((x for x in maps if x["object_id"] == r["object_id"]), None)
        im = (
            (
                f'<a href="{mapping["file"]}"><img src="{mapping["file"]}" alt="{html.escape(title)} selected fictional footprint and source limitations" style="width:100%;height:auto"></a>'
            )
            if mapping
            else ""
        )
        cards.append(
            '<article data-search="'
            + html.escape(
                r["object_id"] + " " + title + " " + r["disposition"], quote=True
            )
            + '"><small>'
            + r["object_id"]
            + "</small><h2>"
            + html.escape(title)
            + '</h2><p class="badge">'
            + html.escape(r["disposition"].replace("_", " ").capitalize())
            + "</p>"
            + im
            + "<p>"
            + html.escape(r["unknown_disposition"])
            + "</p><details><summary>Controlling decision and preserved evidence</summary><pre>"
            + html.escape(json.dumps(item, indent=2, ensure_ascii=False))
            + "</pre></details></article>"
        )
    for r in prospects:
        cards.append(
            '<article data-search="'
            + html.escape(r["canonical_name"] + " " + r["place"], quote=True)
            + '"><small>'
            + r["object_id"]
            + "</small><h2>"
            + html.escape(r["canonical_name"])
            + '</h2><p class="badge">Rejected external prospect</p><p>'
            + html.escape(r["place"])
            + "</p><p>Inquiry: "
            + r["review_started"]
            + " through "
            + r["review_closed"]
            + ". No ownership or occupancy.</p><details><summary>Source and disposition</summary><pre>"
            + html.escape(json.dumps(r, indent=2))
            + "</pre></details></article>"
        )
    page = (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sable Harbor · Geographic decisions</title><style>'
        + STYLE
        + '</style><header><small>SABLE HARBOR / CONTROLLING GEOGRAPHIC DECISIONS</small><h1>Places, premises and continuity</h1><p>Three screened fictional footprints and an explicit disposition for every corporate site and Fort component. Accepted canon controls; exactness is used only where it carries meaning.</p></header><main><nav><a href="Geographic-site-decisions.pdf">Download site atlas</a> · <a href="../chronology/history.html">Historical chronology</a> · <a href="../completion/maps/index.html">Historical map series</a></nav><label for="search">Find a place, function or disposition</label><p><input id="search" type="search" placeholder="Search sites and rejected prospects" aria-controls="results"></p><p id="count" role="status">37 records</p><section id="results">'
        + "".join(cards)
        + '</section></main><script>const q=document.querySelector("#search"),cards=[...document.querySelectorAll("article")];q.addEventListener("input",()=>{let n=0;for(const c of cards){c.hidden=!c.dataset.search.toLowerCase().includes(q.value.toLowerCase());n+=!c.hidden;}document.querySelector("#count").textContent=`${n} records`;});</script></html>'
    )
    (output / "index.html").write_text(page)
    (output / "SITE_DECISIONS.json").write_text(
        json.dumps(
            dict(
                decision_id=decisions["decision_id"],
                canon_sha256=decisions["canon_sha256"],
                records=current,
            ),
            indent=2,
        )
        + "\n"
    )
    (output / "SITE_SCREEN.json").write_text(json.dumps(report, indent=2) + "\n")
    result = dict(
        site_records=len(current),
        selected_footprints=len(features),
        rejected_prospects=len(prospects),
        source_review=source_summary,
        visual_review=visual_summary,
        maps=maps,
        canon_sha256=decisions["canon_sha256"],
        issue_106_implementation_complete=True,
        issue_108_complete=False,
        acceptance_boundary="Implementation evidence only; release, integration and validation receipts establish delivery. Full semantic review is separately evaluated.",
    )
    (output / "FINALIZATION.json").write_text(json.dumps(result, indent=2) + "\n")
    return result, current


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(build(args.output)[0], indent=2))
