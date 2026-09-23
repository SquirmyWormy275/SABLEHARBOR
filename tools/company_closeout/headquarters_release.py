"""Build and verify the versioned Sacramento HQ image publication package."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import fitz

from tools.company_closeout.headquarters_publication import (
    ARTWORK,
    PUBLICATION,
    ROOT,
    SOURCE,
    STRUCTURED,
    checked_artwork,
    verify_embedded_image,
)

VERSION = "1.0.0"
PACKAGE = f"sable-harbor-hq-image-v{VERSION}.zip"
FILES = {
    "sacramento-hq-exterior.png": ARTWORK,
    "SH-CORP-HQ-IMAGE-20260922_v1.0.0.pdf": PUBLICATION,
    "HEADQUARTERS_IMAGE_SUCCESSOR_2026-09-22.md": SOURCE,
    "corporate_headquarters_image_successor_2026-09-22.json": STRUCTURED,
    "SOURCE_REVIEW.json": "assets/headquarters/exterior/2026-09-22/SOURCE_REVIEW.json",
    "ARTIFACT.json": "assets/headquarters/exterior/2026-09-22/ARTIFACT.json",
    "PROMPT.txt": "assets/headquarters/exterior/2026-09-22/PROMPT.txt",
}


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def checksum_lines(directory: Path, names: list[str]) -> bytes:
    return "".join(f"{sha256(directory / name)}  {name}\n" for name in names).encode()


def build(destination: Path, accepted: bool) -> dict:
    if destination.exists():
        raise ValueError("HQ release output must be a new directory")
    art, digest = checked_artwork()
    verify_embedded_image(ROOT / PUBLICATION, art)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if accepted and subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT):
        raise ValueError("accepted HQ release requires a clean source checkout")
    destination.mkdir(parents=True)
    for name, source in FILES.items():
        shutil.copyfile(ROOT / source, destination / name)
    manifest = {
        "release_id": "SH-CORP-HQ-IMAGE-20260922",
        "version": VERSION,
        "source_commit": revision,
        "acceptance": "ACCEPTED_SOURCE" if accepted else "PREPARATION_ONLY",
        "decision_source": SOURCE,
        "current_artwork_path": ARTWORK,
        "current_artwork_sha256": digest,
        "prior_approved_hash": "2bf5a1209b9c3ece435271f2fbf5a3c827bbbccf242ea4ee60535749ccee9d92",
        "prior_binary_recovered": False,
        "scope": "Current Sacramento headquarters exterior visual and its controlled publication",
        "members": {
            name: {
                "repository_path": source,
                "sha256": sha256(destination / name),
                "bytes": (destination / name).stat().st_size,
            }
            for name, source in FILES.items()
        },
    }
    (destination / "MANIFEST.json").write_bytes(encoded(manifest))
    internal_names = sorted([*FILES, "MANIFEST.json"])
    (destination / "PACKAGE_SHA256SUMS.txt").write_bytes(
        checksum_lines(destination, internal_names)
    )
    with zipfile.ZipFile(
        destination / PACKAGE, "w", zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name in [*internal_names, "PACKAGE_SHA256SUMS.txt"]:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(
                info, (destination / name).read_bytes(), compress_type=zipfile.ZIP_DEFLATED
            )
    (destination / "SHA256SUMS.txt").write_bytes(
        checksum_lines(
            destination, sorted([*FILES, "MANIFEST.json", "PACKAGE_SHA256SUMS.txt", PACKAGE])
        )
    )
    return manifest


def verify(destination: Path) -> dict:
    inventory = (destination / "SHA256SUMS.txt").read_text().splitlines()
    names = []
    for line in inventory:
        expected, name = line.split("  ", 1)
        if name in names or sha256(destination / name) != expected:
            raise ValueError("HQ release checksum mismatch or duplicate member")
        names.append(name)
    if set(names) != set([*FILES, "MANIFEST.json", "PACKAGE_SHA256SUMS.txt", PACKAGE]):
        raise ValueError("HQ release asset population differs from declared scope")
    manifest = json.loads((destination / "MANIFEST.json").read_text())
    if manifest["current_artwork_sha256"] != sha256(destination / "sacramento-hq-exterior.png"):
        raise ValueError("current HQ artwork differs from release manifest")
    with zipfile.ZipFile(destination / PACKAGE) as archive:
        if set(archive.namelist()) != set([*FILES, "MANIFEST.json", "PACKAGE_SHA256SUMS.txt"]):
            raise ValueError("HQ release ZIP member population differs")
        for name in archive.namelist():
            if archive.read(name) != (destination / name).read_bytes():
                raise ValueError("HQ release ZIP content differs from standalone asset")
    pdf = fitz.open(destination / "SH-CORP-HQ-IMAGE-20260922_v1.0.0.pdf")
    images = [image for page in pdf for image in page.get_images(full=True)]
    if len(images) != 1:
        raise ValueError("HQ PDF does not contain exactly one image")
    source = fitz.Pixmap(str(destination / "sacramento-hq-exterior.png"))
    published = fitz.Pixmap(pdf, images[0][0])
    if (source.width, source.height, source.n, source.samples) != (
        published.width,
        published.height,
        published.n,
        published.samples,
    ):
        raise ValueError("HQ PDF pixels differ from release PNG")
    return {
        "result": "PASS",
        "source_commit": manifest["source_commit"],
        "source_png_sha256": manifest["current_artwork_sha256"],
        "package_sha256": sha256(destination / PACKAGE),
        "assets": len(names),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "verify"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--accepted", action="store_true")
    args = parser.parse_args()
    result = build(args.output, args.accepted) if args.action == "build" else verify(args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
