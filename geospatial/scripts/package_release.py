#!/usr/bin/env python3
"""Build a deterministic, self-contained Geo review bundle into ignored dist/.

Publish as a new GitHub Release; never replace an earlier package or add ZIPs to Git.
"""

import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent


def build():
    cat = json.loads((BASE / "sources/catalog.json").read_text())
    out = BASE / "dist"
    out.mkdir(exist_ok=True)
    paths = {
        p
        for p in BASE.rglob("*")
        if p.is_file()
        and not any(
            part in {"dist", "__pycache__", ".pytest_cache", ".ruff_cache"}
            for part in p.relative_to(BASE).parts
        )
        and not p.name.endswith((".pyc", ".tmp", "-journal"))
        and ".building." not in p.name
    }
    for s in cat["sources"]:
        p = ROOT / s["url_or_repo_path"]
        if p.is_file():
            paths.add(p)
    paths.add(ROOT / "industrial/tools/build_operations.py")
    paths.add(ROOT / "industrial/source/geography/network.geojson")
    paths.add(ROOT / "industrial/source/geography/candidate_comparison.json")
    for s in cat["sources"]:
        if s["source_id"].startswith("SRC-CURRENT-"):
            p = ROOT / s["url_or_repo_path"]
            if hashlib.sha256(p.read_bytes()).hexdigest() != s["file_sha256"]:
                raise ValueError("Current source drift: " + str(p))
    files = [
        dict(
            path=p.relative_to(ROOT).as_posix(),
            bytes=p.stat().st_size,
            sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        )
        for p in sorted(paths)
    ]
    manifest = dict(
        version=cat["package_version"],
        status="CANON_RECONCILED_FRAMEWORK_FULL_PROGRAM_INCOMPLETE",
        canon_commit=cat["source_commit"],
        source_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        files=files,
        limits="Synthetic case geometry is not survey/title/qualification. Remaining tasks: geospatial/docs/PROGRAM_CLOSEOUT_MATRIX.md.",
    )
    raw = (json.dumps(manifest, indent=2) + "\n").encode()
    mp = out / "MANIFEST.json"
    mp.write_bytes(raw)
    archive = out / ("sable-harbor-geospatial-v" + cat["package_version"] + ".zip")

    def member(z, name, data):
        info = zipfile.ZipInfo(name, (2026, 9, 7, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        z.writestr(info, data)

    with zipfile.ZipFile(archive, "w") as z:
        for f in files:
            member(z, f["path"], (ROOT / f["path"]).read_bytes())
        member(z, "MANIFEST.json", raw)
        member(
            z, "CHECKSUMS.sha256", "".join(f"{f['sha256']}  {f['path']}\n" for f in files).encode()
        )
    with zipfile.ZipFile(archive) as z:
        if z.testzip():
            raise ValueError("Archive CRC failure")
        for f in files:
            if hashlib.sha256(z.read(f["path"])).hexdigest() != f["sha256"]:
                raise ValueError("Archive hash mismatch")
    hashes = "".join(
        hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n" for p in [archive, mp]
    )
    (out / "SHA256SUMS.txt").write_text(hashes)
    print(hashes, end="")
    return archive


if __name__ == "__main__":
    build()
