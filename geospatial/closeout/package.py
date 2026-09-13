"""Build and seal a portable geographic evidence package without altering accepted layers."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sqlite3
import subprocess
import zipfile
from pathlib import Path

from geospatial.closeout.sites import ROOT, review
from geospatial.chronology.build import write as write_history
from geospatial.chronology.operations_review import review as review_operations
from geospatial.scripts.build_geopackage import build as build_geopackage
from tools.evidence.closeout import residual_geography, verify as verify_evidence
from tools.evidence.inventory import inventory

PREDECESSOR_SHA256 = "70723d888c6e9eccf9cc9fac87da4fd37e241468a2aefdf0fc097d7325c379d5"
GPKG = "geospatial/master/sable_harbor_master_v0.1.gpkg"
VERSION = "1.1.0"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def csv_file(path, rows):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def attribute_table(db, name, rows, key):
    columns = list(rows[0])

    def quoted(value):
        return '"' + value.replace('"', '""') + '"'

    declarations = [quoted(c) + (" TEXT PRIMARY KEY" if c == key else " TEXT") for c in columns]
    db.execute("CREATE TABLE " + quoted(name) + " (" + ",".join(declarations) + ")")
    for row in rows:
        values = [
            json.dumps(row[c], sort_keys=True) if isinstance(row[c], (dict, list)) else row[c]
            for c in columns
        ]
        db.execute(
            "INSERT INTO " + quoted(name) + " VALUES (" + ",".join("?" for _ in columns) + ")",
            values,
        )
    db.execute(
        "INSERT INTO gpkg_contents(table_name,data_type,identifier,description,last_change) VALUES (?,?,?,?,?)",
        (
            name,
            "attributes",
            name,
            "Source-bound review evidence; no survey, occupancy or issue closure inferred.",
            "2026-09-13T00:00:00.000Z",
        ),
    )


def prepare(output, predecessor, allow_dirty=False):
    output = output.resolve()
    if output.exists():
        raise ValueError("Use a new output directory")
    if output.is_relative_to(ROOT) and not output.is_relative_to(ROOT / "var"):
        raise ValueError("Build under ignored var/ or outside the checkout")
    if sha(predecessor) != PREDECESSOR_SHA256:
        raise ValueError("Evidence archive differs from accepted release 1.1.0")
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT))
    if dirty and not allow_dirty:
        raise ValueError("Publication requires clean source")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    output.mkdir(parents=True)
    paths = (
        subprocess.check_output(["git", "ls-files", "-z", "geospatial"], cwd=ROOT)
        .decode()
        .split("\0")
    )
    for name in paths:
        if not name:
            continue
        dest = output / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    with zipfile.ZipFile(predecessor) as archive:
        archive.extractall(output / "review")
    verify_evidence(output / "review")
    sites, sources = review()
    history = write_history(output / "chronology")
    operations_raw, operations_summary, operations_rows = review_operations()
    (output / "chronology/OPERATIONS_REVIEW.csv.gz").write_bytes(operations_raw)
    dump(output / "chronology/OPERATIONS_REVIEW.json", operations_summary)
    residual, reconciliation = residual_geography()
    source_inventory = inventory(ROOT, revision, residual)
    dump(output / "SITE_EVIDENCE.json", sites)
    dump(output / "SOURCE_COVERAGE.json", source_inventory)
    packaged_sources = []
    for digest, (source, raw) in sources.items():
        path = output / "archived-sources" / (digest + Path(source["path"]).suffix)
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(raw)
        packaged_sources.append({**source, "packaged_source": str(path.relative_to(output))})
    dump(output / "ARCHIVED_SOURCES.json", packaged_sources)
    flat = [
        {
            "object_id": r["object_id"],
            "name": r["canonical_name"],
            "geometry_disposition": r["geometry_disposition"],
            "geometry_features": len(r["geometry_features"]),
            "access_disposition": r["access_disposition"],
            "occupancy_disposition": r["occupancy_disposition"],
            "source_period": r["source_period"],
            "source_period_precision": r["source_period_precision"],
            "period_meaning": r["period_meaning"],
            "source_path": r["source"]["path"],
            "source_revision": r["source"]["revision"],
            "source_sha256": r["source"]["sha256"],
        }
        for r in sites["rows"]
    ]
    csv_file(output / "SITE_EVIDENCE.csv", flat)
    gpkg = output / GPKG
    original = sqlite3.connect(ROOT / GPKG)
    old_counts = {
        r[0]: original.execute('SELECT COUNT(*) FROM "' + r[0] + '"').fetchone()[0]
        for r in original.execute("SELECT table_name FROM gpkg_contents WHERE data_type='features'")
    }
    old_rows = {
        name: list(original.execute('SELECT * FROM "' + name + '" ORDER BY feature_id'))
        for name in old_counts
    }
    original.close()
    gpkg.unlink()
    build_geopackage(gpkg)
    ocr = json.loads((output / "review/ocr-results.json").read_text())
    with sqlite3.connect(gpkg) as db:
        attribute_table(db, "review_site_evidence", sites["rows"], "object_id")
        attribute_table(db, "review_history_events", history["events"], "event_id")
        history_links = [
            {"link_id": e["event_id"] + "::" + oid, "event_id": e["event_id"], "object_id": oid}
            for e in history["events"]
            for oid in e["object_ids"]
        ]
        attribute_table(db, "review_history_links", history_links, "link_id")
        if db.execute(
            "SELECT object_id FROM review_history_links EXCEPT SELECT object_id FROM object_registry"
        ).fetchall():
            raise ValueError("History references an unknown object")
        attribute_table(db, "review_site_history", history["sites"], "object_id")
        attribute_table(db, "review_operations", operations_rows, "occurrence_id")
        attribute_table(db, "review_occurrences", residual, "occurrence_id")
        attribute_table(
            db, "review_source_coverage", source_inventory["baseline_sources"], "source_path"
        )
        attribute_table(
            db, "review_source_changes", source_inventory["subsequent_changes"], "source_path"
        )
        attribute_table(db, "review_raster_candidates", ocr["images"], "source_path")
        for name, count in old_counts.items():
            if (
                list(db.execute('SELECT * FROM "' + name + '" ORDER BY feature_id'))
                != old_rows[name]
            ):
                raise ValueError("Accepted feature population changed: " + name)
        unknown = db.execute(
            "SELECT object_id FROM review_site_evidence EXCEPT SELECT object_id FROM object_registry"
        ).fetchall()
        if (
            unknown
            or db.execute("PRAGMA foreign_key_check").fetchall()
            or db.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
        ):
            raise ValueError("GeoPackage integrity or site crosswalk failed")
        db.commit()
        db.execute("VACUUM")
    # Native QGIS reads this project at the preserved relative path. The QA step
    # enriches it with registered attribute tables and checks a relocated copy.
    dump(
        output / "BUILD.json",
        {
            "version": VERSION,
            "source_revision": revision,
            "dirty_review": dirty,
            "predecessor_sha256": PREDECESSOR_SHA256,
            "spatial_feature_counts": old_counts,
            "site_records": len(sites["rows"]),
            "history_events": len(history["events"]),
            "operations_review": operations_summary,
            "remaining_occurrences": len(residual),
            "source_reconciliation": reconciliation,
            "issue_106_complete": False,
            "issue_108_complete": False,
        },
    )
    (output / "README.md").write_text(f"""# Sable Harbor geographic evidence package

Source: `{revision}`. {"DEVELOPMENT PREVIEW" if dirty else "Clean source build"}.

Open **chronology/history.html** for the new interactive timeline, site histories and dated route views. Open **geospatial/qgis/sable_harbor_master.qgz** in QGIS. Its relative paths work after moving the complete folder. The GeoPackage is **{GPKG}**; it can also be opened directly by GIS or SQLite tools. Open **geospatial/maps/index.html** for the existing facility atlas, or **review/review.html** for the preserved offline review edition.

History edition 1.1.0 adds 72 source-bound events/observations and an additional 295 industrial occurrence dispositions, leaving 8,666 carriers outside four reviewed batches. The original three-batch residual table remains preserved. The proposed Klein/Fort relocation is kept separate in geospatial/chronology/CONTINUITY_PROPOSAL.md and is excluded from accepted history.

The package contains {len(old_counts)} accepted feature layers, 34 site/component source bindings, 8,961 residual occurrences, 919 baseline source records and the 97-image OCR candidate population from evidence release 1.1.0. New review tables are registered as GeoPackage attributes and joined by stable IDs; they are not invented geographic features. SITE_EVIDENCE.csv is the compact review sheet. SITE_EVIDENCE.json preserves all full records, source excerpts, operational-state evidence and map-feature hashes. ARCHIVED_SOURCES.json identifies the exact historical source bytes included under archived-sources/.

Planning envelopes, synthetic engineering and superseded claims keep their original classifications. Programme, incident, provider-selection and acquisition dates are separated from unknown occupancy intervals. The Klein-shop/Fort continuity conflict remains explicit. No survey, real title, new tenancy, custody approval or issue closure is asserted.

The predecessor offline review remains pinned to its own accepted source; SOURCE_COVERAGE.json and the GeoPackage source-change table describe this package's source revision. OCR candidates are unreviewed machine text, with their original engine/model provenance and logs. Historical QA files elsewhere in the copied geographic tree describe earlier releases; **NATIVE_QGIS.json**, **VALIDATION.json** and the top-level manifest describe this delivery.

Reproduce from the recorded Git revision with full history and the pinned evidence archive: follow geospatial/closeout/README.md. No source image or accepted geometry is replaced by this package.
""")
    return output


def validate(output):
    import fiona

    build = json.loads((output / "BUILD.json").read_text())
    gpkg = output / GPKG
    checks = []
    for name, expected in build["spatial_feature_counts"].items():
        with fiona.open(gpkg, layer=name) as layer:
            checks.append(
                {
                    "layer": name,
                    "count": len(layer),
                    "expected": expected,
                    "epsg": layer.crs.to_epsg(),
                }
            )
    if any(r["count"] != r["expected"] or r["epsg"] != 4326 for r in checks):
        raise ValueError("Independent GIS read differs from accepted layers")
    with sqlite3.connect(gpkg) as db:
        attributes = {
            r[0]: db.execute('SELECT COUNT(*) FROM "' + r[0] + '"').fetchone()[0]
            for r in db.execute(
                "SELECT table_name FROM gpkg_contents WHERE table_name LIKE 'review_%'"
            )
        }
        if (
            attributes["review_site_evidence"] != 34
            or attributes["review_occurrences"] != 8961
            or attributes["review_source_coverage"] != 919
            or attributes["review_raster_candidates"] != 97
            or attributes["review_history_events"] != 72
            or attributes["review_site_history"] != 34
            or attributes["review_operations"] != 295
        ):
            raise ValueError("Review populations differ")
    report = {
        "passed": True,
        "spatial_layers": checks,
        "review_tables": attributes,
        "gpkg_sha256": sha(gpkg),
        "geometry_promotion": False,
        "accepted_spatial_rows_preserved": True,
        "issues_closed": [],
    }
    dump(output / "VALIDATION.json", report)
    return report


def seal(output):
    build = json.loads((output / "BUILD.json").read_text())
    if build["dirty_review"]:
        raise ValueError("Development previews cannot be published")
    browser = json.loads((output / "chronology/BROWSER_RESULTS.json").read_text())
    if not browser["passed"] or browser["html_sha256"] != sha(output / "chronology/history.html"):
        raise ValueError("History browser qualification is absent or stale")
    native = json.loads((output / "NATIVE_QGIS.json").read_text())
    if (
        not native["passed"]
        or native["gpkg_sha256"] != sha(output / GPKG)
        or native["project_sha256"] != sha(output / "geospatial/qgis/sable_harbor_master.qgz")
    ):
        raise ValueError("Native QGIS qualification is absent or stale")
    validate(output)
    files = {
        str(p.relative_to(output)): sha(p)
        for p in sorted(output.rglob("*"))
        if p.is_file() and p != output / "PACKAGE_MANIFEST.json"
    }
    dump(
        output / "PACKAGE_MANIFEST.json",
        {
            "version": VERSION,
            "source_revision": build["source_revision"],
            "files": files,
            "issues_closed": [],
        },
    )
    archive = Path(str(output) + ".zip")
    if archive.exists():
        raise ValueError("Refusing to replace an existing archive")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(output.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(output))
    print(
        json.dumps({"archive": str(archive), "sha256": sha(archive), "files": len(files)}, indent=2)
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence-archive", type=Path)
    parser.add_argument("--allow-dirty-review", action="store_true")
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    if args.seal:
        seal(args.output.resolve())
    else:
        if args.evidence_archive is None:
            parser.error("--evidence-archive is required when preparing a package")
        prepare(args.output, args.evidence_archive, args.allow_dirty_review)
        print(json.dumps(validate(args.output.resolve()), indent=2))
