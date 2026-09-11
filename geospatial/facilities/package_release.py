"""Build a portable, checksummed facility delivery from one committed repository snapshot.

The complete public source context is included deliberately so offline atlas provenance
links resolve. Preserved historical ZIP packages are excluded from redistribution.
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
                if member.name.lower().endswith((".zip", ".tar", ".tar.gz")):
                    excluded.append(member.name)
                    continue
                data = source.extractfile(member).read()
                info = zipfile.ZipInfo(member.name, (2026, 9, 11, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                bundle.writestr(info, data, compresslevel=9)
                records.append(
                    {
                        "path": member.name,
                        "bytes": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(),
                    }
                )
            manifest = {
                "package": "SABLE_HARBOR_Facility_Atlas_v0.1.0",
                "source_commit": revision,
                "canon_base": "786fc9a5311a04dde92ee6dbb08ac3b77a380200",
                "entry_point": "geospatial/maps/index.html",
                "scope": "Facility plans with complete public repository source context for offline provenance and reproduction. Included historical sources retain their original status, not current branding authority.",
                "excluded_historical_archives": excluded,
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
