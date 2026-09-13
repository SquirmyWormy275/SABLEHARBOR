"""Source-bound geographic chronology; event dates never become property tenure."""

from __future__ import annotations
import argparse
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from functools import lru_cache
import subprocess
from geospatial.closeout.sites import ROOT, bind_source, review as site_review

BASELINE = "9cc0d2a5c31700dcd166ef9acf1dd284bddb6e8d"
OPS = "industrial/source/operations.json"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@lru_cache(maxsize=64)
def archived(path, revision=BASELINE):
    return subprocess.check_output(["git", "show", revision + ":" + path], cwd=ROOT)


def pointer(value, locator):
    for token in locator.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def source(path, locator, revision=BASELINE):
    raw = archived(path, revision)
    text = raw.decode()
    if locator.startswith("/"):
        evidence = pointer(json.loads(text), locator)
    else:
        first, last = map(int, locator.removeprefix("lines:").split("-"))
        evidence = "\n".join(text.splitlines()[first - 1 : last])
    return dict(path=path, revision=revision, locator=locator, sha256=sha(raw), evidence=evidence)


def period(value):
    """Bounds describe when an event happened, never continuous occupancy."""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        date.fromisoformat(value)
        return dict(date_text=value, precision="DAY", earliest=value, latest=value)
    if re.fullmatch(r"\d{4}", value):
        year = int(value)
        return dict(
            date_text=value, precision="YEAR", earliest=f"{year}-01-01", latest=f"{year}-12-31"
        )
    match = re.fullmatch(r"(\d{4})[–-](\d{4})", value)
    if match and int(match[1]) <= int(match[2]):
        return dict(
            date_text=value,
            precision="YEAR_RANGE",
            earliest=match[1] + "-01-01",
            latest=match[2] + "-12-31",
        )
    raise ValueError("Unsupported temporal wording: " + value)


def event(ident, title, kind, when, evidence, object_ids=(), notes="", place="Unlocated"):
    return dict(
        event_id=ident,
        title=title,
        kind=kind,
        **period(when),
        object_ids=list(object_ids),
        place=place,
        evidence=evidence,
        source_revision=evidence["revision"],
        occupancy_interval_established=False,
        notes=notes,
    )


def build():
    catalog = json.loads(archived("geospatial/sources/catalog.json"))
    objects = {r["object_id"]: r for r in catalog["objects"]}
    operations = json.loads(archived(OPS))
    events = []
    links = {
        "SH-EVT-0001": ["SH-SITE-0006"],
        "SH-EVT-0004": ["SH-SITE-0002"],
        "SH-EVT-0005": ["SH-SITE-0002", "SH-SITE-0003"],
        "SH-EVT-0006": ["SH-SITE-0004"],
        "SH-EVT-0007": ["SH-SITE-0010"],
        "SH-EVT-0008": ["SH-SITE-0020"],
    }
    for obj in objects.values():
        if obj["object_type"] != "EVENT":
            continue
        if obj["object_id"] == "SH-EVT-0008":
            evidence = source("industrial/source/entities.json", "/entities/4")
            assert evidence["evidence"]["ownership_effective_on"] == obj["relevant_date"]
        else:
            evidence, _ = bind_source(obj)
        # Catalog dates are separately bound, including year metadata absent from a short primary quote.
        evidence["date_register"] = dict(
            path="geospatial/sources/catalog.json",
            revision=BASELINE,
            sha256=sha(archived("geospatial/sources/catalog.json")),
            object_id=obj["object_id"],
            relevant_date=obj["relevant_date"],
        )
        display_titles = {
            "SH-IND-HIST-1898": "Bloodstone & Southern Railway organized",
            "SH-IND-HIST-1907": "Coal-train runaway remembered in oral history",
            "SH-IND-HIST-1909": "Coal-era labor organization",
            "SH-IND-HIST-1916": "Bloodstone No. 2 mine disaster — source-conflicted account",
            "SH-IND-HIST-1953": "Bloodstone Coal & Coke parent fails",
            "SH-IND-HIST-1954": "BS&T rescue and reorganization",
            "SH-IND-HIST-1968": "Taylor mainline extension and industrial hub completed",
            "SH-IND-HIST-1972": "East Materials branch and Taylor transload open",
            "SH-IND-HIST-1986": "Mineral Transfer branch opens",
            "SH-IND-HIST-1991": "ARU formalization and railway ownership",
        }
        events.append(
            event(
                obj["object_id"],
                display_titles.get(obj["object_id"], obj["canonical_name"]),
                "CORPORATE_EVENT" if obj["object_id"].startswith("SH-EVT") else "RAILWAY_HISTORY",
                obj["relevant_date"],
                evidence,
                links.get(obj["object_id"], [obj["object_id"]]),
                obj["notes"],
                obj["place"],
            )
        )
    for i, facility in enumerate(operations["facilities"]):
        oid = "SH-IND-" + facility["id"]
        assert oid in objects
        events.append(
            event(
                "OPEN-" + facility["id"],
                facility["name"] + " opens",
                "FACILITY_OPENING",
                facility["opened"],
                source(OPS, f"/facilities/{i}"),
                [oid],
                "Accepted synthetic opening date. Current footprint is a separate reference; opening does not prove unchanged historical boundaries or owner tenure.",
            )
        )
    for i, item in enumerate(operations["structures"]):
        oid = "SH-IND-" + item["id"]
        assert oid in objects
        events.append(
            event(
                "BUILD-" + item["id"],
                item["id"] + " construction",
                "STRUCTURE_CONSTRUCTION",
                str(item["constructed"]),
                source(OPS, f"/structures/{i}"),
                [oid],
                "Year-only synthetic construction claim. Does not backdate the current route alignment or assert a surveyed historical position.",
            )
        )
    for i, item in enumerate(operations["safety_events"]):
        events.append(
            event(
                item["id"],
                item["description"],
                "SAFETY_EVENT",
                item["date"],
                source(OPS, f"/safety_events/{i}"),
                [],
                "Source does not establish an exact event site; no automatic join to a yard or rail segment.",
            )
        )
    lore = "docs/canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.3.1.md"
    text = archived(lore).decode().splitlines()
    heading = text.index("## 7.4 The Klein shop — 2021") + 1
    sentence = next(
        i + 1
        for i, t in enumerate(text)
        if t.startswith("Klein leases a light-industrial building")
    )
    evidence = source(lore, f"lines:{heading}-{sentence}")
    assert "2021" in evidence["evidence"] and "Klein leases" in evidence["evidence"]
    events.append(
        event(
            "OBS-KLEIN-LEASE-2021",
            "Klein shop lease documented in the 2021 narrative",
            "LEASE_OBSERVATION",
            "2021",
            evidence,
            ["SH-SITE-0002"],
            "Positive year-bounded lease evidence recovered from the section heading and sentence. Exact commencement, expiration and parcel remain unknown. Later approved continuity is recorded separately.",
            "Pittsburgh area",
        )
    )
    closeout = "docs/canon/WILLOW_KLEIN_CLOSEOUT_2026-09-06.md"
    lines = archived(closeout).decode().splitlines()
    start = lines.index("## The Fort — Willow's Pittsburgh compound") + 1
    end = lines.index("## Klein visual identity")
    events.append(
        event(
            "OBS-FORT-DESCRIBED-2026",
            "Fort compound and four named components documented",
            "SITE_DESCRIPTION_SNAPSHOT",
            "2026-09-06",
            source(closeout, f"lines:{start}-{end}"),
            [
                "SH-SITE-0003",
                "SH-FAC-FORT-BIG",
                "SH-FAC-FORT-SMALL",
                "SH-FAC-FORT-WHITE",
                "SH-FAC-FORT-MUSEUM",
            ],
            "Dated canon description; not the opening date of any component.",
            "Pittsburgh area",
        )
    )
    from geospatial.chronology.continuity import evidence as continuity_evidence

    approved = continuity_evidence()
    events.append(
        event(
            "MOVE-KLEIN-FORT-2024",
            "Willow transfers from the Klein shop to separate Fort premises",
            "SITE_RELOCATION",
            "2024",
            approved,
            ["SH-SITE-0002", "SH-SITE-0003"],
            "Owner-approved staged relocation and old-shop vacancy during 2024. Exact days, parcel boundaries and component commissioning dates remain unknown.",
            "Pittsburgh area",
        )
    )
    sites, _ = site_review()
    from geospatial.finalization.prospects import recover as recover_prospects

    for prospect in recover_prospects():
        src = prospect["source"]
        raw = archived(src["path"], src["revision"])
        evidence = dict(path=src["path"], revision=src["revision"],
                        locator="Complete dated rejected-prospect record",
                        sha256=sha(raw), evidence=raw.decode(),
                        source_recorded_at=prospect["source_recorded_at"],
                        available_to_case_company=prospect["source_available_as_of"])
        for suffix, field, title in [
            ("START", "review_started", "Inquiry begins"),
            ("CLOSE", "review_closed", "Acquisition opportunity rejected"),
        ]:
            events.append(event(
                prospect["object_id"] + "-" + suffix,
                prospect["canonical_name"] + " — " + title,
                "REJECTED_PROSPECT_HISTORY", prospect[field], evidence,
                [prospect["object_id"]], prospect["meaning"], prospect["place"],
            ))
    histories = []
    for site in sites["rows"]:
        observations = [e["event_id"] for e in events if site["object_id"] in e["object_ids"]]
        histories.append(
            dict(
                object_id=site["object_id"],
                name=site["canonical_name"],
                events=observations,
                dated_lease_observation="OBS-KLEIN-LEASE-2021"
                if site["object_id"] == "SH-SITE-0002"
                else None,
                occupancy_interval=site["occupancy_bounds"],
                continuity_evidence=site["continuity_evidence"],
                geometry_disposition=site["geometry_disposition"],
                access_disposition=site["access_disposition"],
                period_meaning=site["period_meaning"],
                source_period=site["source_period"],
                conflicts=site["conflict_ids"],
                source=site["source"],
                operational_states=site["retained_operational_states"],
                disposition="OWNER_APPROVED_YEAR_BOUNDED_OCCUPANCY"
                if site["occupancy_bounds"]
                else "SOURCE_BOUND_HISTORY_WITH_EXPLICIT_GAPS",
            )
        )
    # Route snapshots use only accepted dated route records; facilities are current-shape context.
    network = json.loads(archived("geospatial/geojson/rail_network.geojson"))["features"]
    maps = []
    for route in catalog["rail_routes"]:
        for feature in network:
            if feature["properties"]["feature_id"] in route["segment_ids"]:
                maps.append(
                    dict(
                        feature=feature,
                        valid_from=route["valid_from"],
                        valid_to=route["valid_to"],
                        temporal_basis="ACCEPTED_SYNTHETIC_ROUTE_INTERVAL",
                        source=source(
                            "geospatial/sources/catalog.json",
                            "/rail_routes/" + str(catalog["rail_routes"].index(route)),
                        ),
                    )
                )
    return dict(
        version="1.2.0",
        build_revision=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        source_revision=BASELINE,
        events=sorted(events, key=lambda r: (r["earliest"], r["event_id"])),
        sites=histories,
        route_features=maps,
        route_epochs=operations["geography"]["historical_route_epochs"],
        limits=[
            "Event bounds are not occupancy intervals.",
            "No pre-1968 alignment is inferred from modern track.",
            "Current facility footprints do not prove historical footprints.",
            "Owner-approved staged 2024 relocation uses uncertain year bounds, not an invented exact move day.",
        ],
        issues_closed=[],
    )


def write(output):
    output.mkdir(parents=True, exist_ok=True)
    data = build()
    (output / "HISTORY.json").write_text(json.dumps(data, indent=2) + "\n")
    fields = [
        "event_id",
        "title",
        "kind",
        "date_text",
        "precision",
        "earliest",
        "latest",
        "object_ids",
        "place",
        "notes",
    ]
    with (output / "EVENTS.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fields)
        writer.writeheader()
        writer.writerows(
            {k: json.dumps(e[k]) if isinstance(e[k], list) else e[k] for k in fields}
            for e in data["events"]
        )
    template = (Path(__file__).parent / "viewer.html").read_text()
    payload = json.dumps(data).replace("<", "\\u003c").replace("&", "\\u0026")
    (output / "history.html").write_text(template.replace("__HISTORY_DATA__", payload))
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = write(args.output)
    print(
        json.dumps(
            {
                "events": len(result["events"]),
                "sites": len(result["sites"]),
                "route_features": len(result["route_features"]),
            }
        )
    )
