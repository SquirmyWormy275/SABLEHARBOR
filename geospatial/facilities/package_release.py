"""Build a portable, checksummed facility delivery from one committed repository snapshot.

The complete public source context is included deliberately so offline atlas provenance
links resolve. Historical distribution ZIPs are excluded; the immutable approved R01
source ZIP is included as an explicit source-artifact exception.
"""

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
R01_SOURCE_ARCHIVE = "docs/facilities/references/sacramento-hq/r01-approved/SABLE_HARBOR_Sacramento_HQ_Drafts_R01.zip"
R01_SOURCE_SHA256 = "eb10588f6cc6e214d8541b96b1bd044f52f0df85e384fc53a316b55b5d026fe0"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    revision = subprocess.check_output(
        ["git", "rev-parse", args.revision], cwd=ROOT, text=True
    ).strip()
    archive = subprocess.check_output(["git", "archive", revision], cwd=ROOT)
    records = []
    excluded = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        with zipfile.ZipFile(
            args.output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as bundle:
            for member in sorted(source.getmembers(), key=lambda entry: entry.name):
                if not member.isfile():
                    continue
                if (
                    member.name.lower().endswith((".zip", ".tar", ".tar.gz"))
                    and member.name != R01_SOURCE_ARCHIVE
                ):
                    excluded.append(member.name)
                    continue
                data = source.extractfile(member).read()
                origin = "committed_source"
                if member.name == R01_SOURCE_ARCHIVE:
                    if hashlib.sha256(data).hexdigest() != R01_SOURCE_SHA256:
                        raise ValueError("Approved R01 source archive bytes changed")
                    origin = "immutable_approved_source_archive_exception"
                if member.name == "docs/releases/FACILITY_ATLAS_RELEASES.md":
                    origin = "generated_offline_release_navigation"
                    data = (
                        "# Facility atlas release navigation\n\n"
                        f"Packaged source snapshot: `{revision}`.\n\n"
                        "Use [the embedded manifest](../../FACILITY_PACKAGE_MANIFEST.json) "
                        "for every included file hash. The enclosing archive checksum and accepted "
                        "release record belong with the [versioned release]"
                        "(https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/facility-atlas-v0.2.0).\n\n"
                        "This generated navigation page avoids embedding a circular archive checksum "
                        "or stale draft-release metadata. The committed source record remains retrievable "
                        f"at [its exact revision](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/{revision}/docs/releases/FACILITY_ATLAS_RELEASES.md).\n"
                    ).encode()
                info = zipfile.ZipInfo(member.name, (2026, 9, 11, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                bundle.writestr(info, data, compresslevel=9)
                records.append(
                    {
                        "path": member.name,
                        "origin": origin,
                        "bytes": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(),
                    }
                )
            if not any(r["path"] == R01_SOURCE_ARCHIVE for r in records):
                raise ValueError("R02 delivery requires the immutable approved R01 source archive")
            manifest = {
                "package": "SABLE_HARBOR_Facility_Atlas_v0.2.0",
                "source_commit": revision,
                "canon_base": "b83e4be2182a5e4143808a3dab5f8d929a133caf",
                "initial_facility_base": "786fc9a5311a04dde92ee6dbb08ac3b77a380200",
                "entry_point": "geospatial/maps/index.html",
                "scope": "Facility plans with complete public repository source context for offline provenance and reproduction. Included historical sources retain their original status, not current branding authority.",
                "excluded_historical_archives": excluded,
                "included_source_archive_exception": {
                    "path": R01_SOURCE_ARCHIVE,
                    "sha256": R01_SOURCE_SHA256,
                    "authority": "Corrected owner handover; approved source-artifact exception recorded in docs/facilities/references/sacramento-hq/r01-approved/README.md",
                    "meaning": "Immutable original reference ZIP, not a generated distributable bundle or an R02 derivative",
                },
                "files": records,
            }
            payload = (json.dumps(manifest, indent=2) + "\n").encode()
            info = zipfile.ZipInfo("FACILITY_PACKAGE_MANIFEST.json", (2026, 9, 11, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, payload, compresslevel=9)
    args.output.with_suffix(".manifest.json").write_bytes(payload)
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.output.with_suffix(".sha256").write_text(f"{digest}  {args.output.name}\n")
    with zipfile.ZipFile(args.output) as bundle:
        assert bundle.testzip() is None
        for record in records:
            assert hashlib.sha256(bundle.read(record["path"])).hexdigest() == record["sha256"]
    print(
        json.dumps(
            {
                "source_commit": revision,
                "files": len(records),
                "sha256": digest,
                "bytes": args.output.stat().st_size,
            }
        )
    )


if __name__ == "__main__":
    main()
