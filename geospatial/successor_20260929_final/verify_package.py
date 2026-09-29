"""Independent hash, population and offline-import check for geographic 1.5."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

EXPECTED_BASE_SHA256 = "f106e164a7578d64c32ba1bcc9444b3a96d89881d7c7b92b51bb97cf2bef6df4"
BASE_MEMBER = "base/sable-harbor-geographic-evidence-v1.4.0.zip"


def digest(stream) -> str:
    h = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        h.update(block)
    return h.hexdigest()


def safe(name: str) -> bool:
    parts = PurePosixPath(name).parts
    return bool(parts) and not name.startswith("/") and ".." not in parts and "\\" not in name


def verify(archive_path: Path, output: Path | None = None) -> dict:
    with zipfile.ZipFile(archive_path) as outer:
        manifest = json.loads(outer.read("MANIFEST.json"))
        files = manifest["files"]
        if (
            manifest["version"] != "1.5.0"
            or manifest["base_version"] != "1.4.0"
            or manifest["base_sha256"] != EXPECTED_BASE_SHA256
            or BASE_MEMBER not in files
            or set(outer.namelist()) != set(files) | {"MANIFEST.json", "CHECKSUMS.sha256"}
        ):
            raise ValueError("Incomplete or mismatched 1.5 package manifest")
        if not all(safe(name) for name in outer.namelist()):
            raise ValueError("Unsafe archive member path")
        listed = {}
        for line in outer.read("CHECKSUMS.sha256").decode().splitlines():
            checksum, name = line.split("  ", 1)
            if name in listed:
                raise ValueError("Duplicate checksum entry")
            listed[name] = checksum
        if listed != {name: meta["sha256"] for name, meta in files.items()}:
            raise ValueError("Checksum list differs from manifest")
        with tempfile.TemporaryDirectory(prefix="sh-geo-import-") as temporary:
            base_path = Path(temporary) / "base.zip"
            with outer.open(BASE_MEMBER) as member, base_path.open("wb") as target:
                shutil.copyfileobj(member, target)
            with base_path.open("rb") as stream:
                if digest(stream) != EXPECTED_BASE_SHA256:
                    raise ValueError("Predecessor archive bytes differ")
            for name, meta in files.items():
                with outer.open(name) as member:
                    actual = digest(member)
                if actual != meta["sha256"] or outer.getinfo(name).file_size != meta["bytes"]:
                    raise ValueError("Changed or truncated member: " + name)
            with zipfile.ZipFile(base_path) as base:
                base_manifest = json.loads(base.read("PACKAGE_MANIFEST.json"))
                if (
                    base_manifest["version"] != "1.4.0"
                    or base_manifest["source_revision"] != manifest["base_source_revision"]
                    or len(base_manifest["files"]) != 1907
                    or set(base.namelist())
                    != set(base_manifest["files"]) | {"PACKAGE_MANIFEST.json"}
                ):
                    raise ValueError("Predecessor manifest or population changed")
                for name, expected in base_manifest["files"].items():
                    if not safe(name):
                        raise ValueError("Unsafe predecessor member")
                    with base.open(name) as member:
                        if digest(member) != expected:
                            raise ValueError("Predecessor member mismatch: " + name)
                for required in (
                    "finalization/index.html",
                    "completion/maps/index.html",
                    "geospatial/master/sable_harbor_master_v0.1.gpkg",
                    "NATIVE_QGIS.json",
                ):
                    if required not in base_manifest["files"]:
                        raise ValueError("Missing offline reader or GIS asset")
                if output is not None:
                    output.mkdir(parents=True, exist_ok=True)
                    for name in base_manifest["files"]:
                        destination = output / "base" / name
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        with base.open(name) as source, destination.open("wb") as target:
                            shutil.copyfileobj(source, target)
                    for name in files:
                        if name == BASE_MEMBER:
                            continue
                        destination = output / name
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        with outer.open(name) as source, destination.open("wb") as target:
                            shutil.copyfileobj(source, target)
                    # SQLite integrity is distinct from source-generator equality.
                    gpkg = output / "base/geospatial/master/sable_harbor_master_v0.1.gpkg"
                    with sqlite3.connect(f"file:{gpkg}?mode=ro", uri=True) as database:
                        if database.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                            raise ValueError("Imported GeoPackage integrity failure")
    if output is not None:
        interface = json.loads(
            (
                output
                / "supplement/geospatial/engineering_review/interface_successor_20260929/register.json"
            ).read_text()
        )
        history = json.loads(
            (
                output / "supplement/geospatial/successors/rail_history_2026_09_29/report.json"
            ).read_text()
        )
        finance = json.loads(
            (
                output / "supplement/industrial/successors/rail_2026_09_29/reperform-result.json"
            ).read_text()
        )
        if (
            interface["corrected_route_miles"]["total"] != 40
            or interface["population"]["facilities"] != 12
            or interface["population"]["track_register"] != 31
            or interface["population"]["structures"] != 26
            or interface["population"]["proposed_turnout_interfaces"] != 8
            or interface["population"]["real_trackage_rights_geometries"] != 0
            or history["accepted_history_preserved"]["1898_extent_miles"] is not None
            or history["accepted_history_preserved"]["1954_recovered_geometry"] is not None
            or history["real_property_instrument_count_added"] != 0
            or finance["planning_months"] != 180
            or len(finance["forecast_datasets"]) != 13
            or finance["modeled_journal_cash_tax_delta_usd"] != 0
        ):
            raise ValueError("Imported source populations or limits differ")
        for link in (
            "base/finalization/index.html",
            "base/completion/maps/index.html",
            "supplement/geospatial/successors/rail_history_2026_09_29/case.svg",
        ):
            if not (output / link).is_file():
                raise ValueError("Offline reader target absent: " + link)
    return {
        "version": manifest["version"],
        "status": manifest["status"],
        "source_revision": manifest["source_revision"],
        "outer_members": len(files) + 2,
        "base_members": 1908,
        "supplement_members": len(files) - 2,
        "import_root": str(output) if output else None,
        "integrity": "PASS",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--import-to", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.archive, args.import_to), indent=2))


if __name__ == "__main__":
    main()
