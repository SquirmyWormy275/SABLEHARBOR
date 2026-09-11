"""Reproducible workbench companion with public source context and offline atlas."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[3]
APPROVED = "docs/facilities/references/sacramento-hq/r01-approved/SABLE_HARBOR_Sacramento_HQ_Drafts_R01.zip"
APPROVED_HASH = "eb10588f6cc6e214d8541b96b1bd044f52f0df85e384fc53a316b55b5d026fe0"


def package(revision, output):
    revision = subprocess.check_output(["git", "rev-parse", revision], cwd=ROOT, text=True).strip()
    source = subprocess.check_output(["git", "archive", revision], cwd=ROOT)
    files = []
    excluded = []
    output.parent.mkdir(parents=True, exist_ok=True)

    def write(bundle, name, content):
        info = zipfile.ZipInfo(name, (2026, 9, 11, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        bundle.writestr(info, content, compresslevel=9)

    with (
        tarfile.open(fileobj=io.BytesIO(source)) as archive,
        zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as bundle,
    ):
        for item in sorted(archive.getmembers(), key=lambda p: p.name):
            if not item.isfile():
                continue
            if item.name.lower().endswith((".zip", ".tar", ".tar.gz")) and item.name != APPROVED:
                excluded.append(item.name)
                continue
            content = archive.extractfile(item).read()
            origin = "committed_source"
            if item.name == APPROVED:
                assert hashlib.sha256(content).hexdigest() == APPROVED_HASH
                origin = "immutable_approved_source_archive"
            if item.name == "docs/releases/FACILITY_WORKBENCH_RELEASES.md":
                content = (
                    f"# Workbench delivery\n\nSource `{revision}`. Open [the workbench](../../geospatial/maps/workbench.html).\n\nSee [embedded hashes](../../WORKBENCH_PACKAGE_MANIFEST.json) and [published acceptance and checksums](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/facility-workbench-v1.0.0). This navigation avoids circular package checksums.\n"
                ).encode()
                origin = "generated_offline_navigation"
            write(bundle, item.name, content)
            files.append(
                {
                    "path": item.name,
                    "origin": origin,
                    "bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                }
            )
        assert any(f["path"] == APPROVED for f in files)
        manifest = {
            "package": "SABLE_HARBOR_Facility_Workbench_v1.0.0",
            "source_commit": revision,
            "accepted_facility_base": "7bc9879fb94dbf999066b8072cc66ec8e05fda0a",
            "entrypoint": "geospatial/maps/workbench.html",
            "authority": "Tools and experiments do not promote source facts; existing publications retain original statuses.",
            "excluded_historical_archives": excluded,
            "files": files,
        }
        content = (json.dumps(manifest, indent=2) + "\n").encode()
        write(bundle, "WORKBENCH_PACKAGE_MANIFEST.json", content)
    output.with_suffix(".manifest.json").write_bytes(content)
    sha = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".sha256").write_text(f"{sha}  {output.name}\n")
    with zipfile.ZipFile(output) as bundle:
        assert bundle.testzip() is None
        for f in files:
            assert hashlib.sha256(bundle.read(f["path"])).hexdigest() == f["sha256"]
    print(
        json.dumps(
            {
                "source_commit": revision,
                "files": len(files),
                "bytes": output.stat().st_size,
                "sha256": sha,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package(args.revision, args.output)
