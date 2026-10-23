#!/usr/bin/env python3
"""Verify committed proposal originals and the historical ZIP download."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAPPING = {
    "README.md": "SOURCE_README.md",
    "manifest.json": "SOURCE_MANIFEST.json",
    "Sable-Harbor-Advisory-Logo.png": "Sable-Harbor-Advisory-Logo.png",
    "Sable-Harbor-Advisory-Letterhead.docx": "Sable-Harbor-Advisory-Letterhead.docx",
    "Sable-Harbor-Advisory-Letterhead-Print.pdf":
        "Sable-Harbor-Advisory-Letterhead-Print-Packaged.pdf",
}


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def verify(package_zip):
    recovery = json.loads((HERE / "RECOVERY_MANIFEST.json").read_text())
    if package_zip.stat().st_size != recovery["package_bytes"] or sha(package_zip.read_bytes()) != recovery["package_sha256"]:
        raise ValueError("Original package size/hash differs")
    for row in recovery["source_assets"]:
        path = HERE / row["repo_path"]
        if path.stat().st_size != row["bytes"] or sha(path.read_bytes()) != row["sha256"]:
            raise ValueError(f"Committed original differs: {path.name}")
    with zipfile.ZipFile(package_zip) as archive:
        if archive.testzip() is not None:
            raise ValueError("Package ZIP CRC failure")
        names = {x.filename for x in archive.infolist() if not x.is_dir()}
        expected = {"Sable-Harbor-Advisory/" + name for name in MAPPING}
        if names != expected:
            raise ValueError("Package member set differs")
        source_manifest = json.loads(archive.read("Sable-Harbor-Advisory/manifest.json"))
        for source_name, local_name in MAPPING.items():
            data = archive.read("Sable-Harbor-Advisory/" + source_name)
            if data != (HERE / local_name).read_bytes():
                raise ValueError(f"Packaged member differs: {source_name}")
            if source_name in source_manifest:
                row = source_manifest[source_name]
                if len(data) != row["bytes"] or sha(data) != row["sha256"]:
                    raise ValueError(f"Package source manifest differs: {source_name}")
    return {"package_sha256": recovery["package_sha256"],
            "package_members_verified": len(MAPPING),
            "committed_originals_verified": len(recovery["source_assets"]),
            "zip_crc_pass": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_zip", type=Path)
    print(json.dumps(verify(parser.parse_args().package_zip), indent=2))
