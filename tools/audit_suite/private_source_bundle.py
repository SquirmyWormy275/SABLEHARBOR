"""Local-only deterministic private corpus delivery; never publishes sources."""

import argparse
import hashlib
import json
import os
import re
import zipfile
from pathlib import Path, PurePosixPath

BASE = "enterprise/generated/audit-suite/"
CORPUS = BASE + "private-corpus/"
MAX_BYTES = 300 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name or str(path) != name:
        raise ValueError("Unsafe member path")
    return path


def read_source(root, relative):
    path = root.joinpath(*safe_name(relative).parts)
    if path.resolve() != path.absolute() or not path.is_file():
        raise ValueError("Source must be a regular file without symlink aliases: " + relative)
    return path.read_bytes()


def inventory(root):
    result = {}
    groups = {
        "definitions": ("*.json", 1110),
        "clean": ("SH-*.json", 166),
        "authority-editions/REAL_SOURCE": ("*.json", 5),
    }
    for group, (pattern, count) in groups.items():
        paths = sorted((root / CORPUS / group).glob(pattern))
        if len(paths) != count:
            raise ValueError(f"{group}: expected {count} canonical files, found {len(paths)}")
        for path in paths:
            relative = path.relative_to(root).as_posix()
            result[relative] = read_source(root, relative)
    for relative in (CORPUS + "parent-support/source.json", BASE + "build/program-pack.json"):
        result[relative] = read_source(root, relative)
    for relative, data in list(result.items()):
        if "/authority-editions/" not in relative:
            continue
        for pin in json.loads(data).get("authority_source_pins", []):
            path = pin["path"]
            if not path.startswith(BASE + "source-documents/"):
                raise ValueError("Authority pin escapes retained source-documents directory")
            source = read_source(root, path)
            if sha(source) != pin["sha256"]:
                raise ValueError("Authority source digest mismatch")
            result[path] = source
    authority_manifest = CORPUS + "qa/MM13_ADDITIONAL_SOURCE_MANIFEST.json"
    result[authority_manifest] = read_source(root, authority_manifest)
    for path in sorted((root / BASE / "source-documents").iterdir()):
        relative = path.relative_to(root).as_posix()
        data = read_source(root, relative)
        if re.fullmatch(r"[a-f0-9]{64}", path.stem):
            if sha(data) != path.stem:
                raise ValueError("Retained document filename hash differs")
        elif path.name not in {
            "C5_2026_EN_SOURCE_MANIFEST.json",
            "C5_2026_SOURCE_MANIFEST.json",
            "ISM_SOURCE_MANIFEST.json",
        }:
            raise ValueError("Unapproved source-documents member: " + path.name)
        result[relative] = data
    result["tools/audit_suite/private_source_bundle.py"] = read_source(
        root, "tools/audit_suite/private_source_bundle.py"
    )
    return result


README = b"""PRIVATE OPERATOR SOURCE DELIVERY - DO NOT PUBLISH

This contains private scenario mechanisms, facts and rubrics. Keep it outside
public source control, learner workspaces and public file-serving directories.
No QA engagement databases, sessions, credentials, private auth configuration,
model weights, or runtime binaries are included.

Contents: 1110 canonical definitions, 166 native clean source plans, five
REAL_SOURCE authority editions, parent-support source, the compiled program
pack, and retained publisher documents/source manifests for authority editions, C5 and ISM.
Every payload member including this README has its exact SHA256 in MANIFEST.json.
The manifest is not a publisher signature. Preserve the archive SHA receipt via
a trusted local channel if transferring this private package.

Reproduce locally from an authorized matching SABLEHARBOR checkout:
  uv run python tools/audit_suite/private_source_bundle.py build \\
    --repository /absolute/SABLEHARBOR --output /private/new-delivery.zip
Verify without extracting:
  uv run python tools/audit_suite/private_source_bundle.py verify --source /private/new-delivery.zip
Restore into a NEW directory under an existing private0700 parent:
  uv run python tools/audit_suite/private_source_bundle.py restore \\
    --source /private/new-delivery.zip --destination /private/restored-sources

Restore preserves repository-relative paths. Configure corpus_root to
<destination>/enterprise/generated/audit-suite/private-corpus and program_pack to
<destination>/enterprise/generated/audit-suite/build/program-pack.json. Authority
pins are repository-relative: place source-documents at the identical relative
location in the matching authorized runtime checkout, using a new empty private
folder and verifying hashes; do not overwrite an existing corpus/world silently.
For a complete checkout, copy only into previously absent ignored generated
folders. Use the reproducible tool's verify command before and after transport.

The public engine/code checkout, Python/JS dependencies and any local inference,
ASR/TTS runtime/models are installed separately. Create fresh operator credentials
and sessions using the local CLI; this bundle cannot restore authentication or
existing engagement histories. Native organization/CCF registry must match the
program pack's native digest. Source documents retain publisher copyright and
conditions; inclusion grants no redistribution license. Licensed AICPA/ISO
standards and any framework inputs absent here require independently authorized
local copies and source acquisition procedures. This is a private training
source snapshot, not a professional audit acceptance, standards license, or
production deployment bundle. Restore does not start any service.
"""


def build(root, destination):
    root = root.absolute()
    if root.resolve() != root:
        raise ValueError("Repository path cannot use aliases")
    payload = inventory(root)
    payload["README.txt"] = README
    manifest = {
        "schema_version": 1,
        "classification": "PRIVATE_TRAINING_TRUTH",
        "counts": {"definitions": 1110, "clean": 166, "authority_editions": 5},
        "members": {
            name: {"sha256": sha(data), "bytes": len(data)}
            for name, data in sorted(payload.items())
        },
    }
    # Detect changes during intake rather than silently bundling mixed snapshots.
    if inventory(root) != {k: v for k, v in payload.items() if k != "README.txt"}:
        raise ValueError("Source snapshot changed during bundle intake")
    payload["MANIFEST.json"] = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    if sum(map(len, payload.values())) > MAX_BYTES:
        raise ValueError("Bundle exceeds bounded delivery size")
    if destination.parent.resolve() != destination.parent.absolute():
        raise ValueError("Destination parent cannot use aliases")
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream, zipfile.ZipFile(stream, "w") as archive:
            for name, data in sorted(payload.items()):
                info = zipfile.ZipInfo(name, date_time=(2026, 9, 13, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100600 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        verify(destination)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return {
        "file": str(destination),
        "sha256": sha(destination.read_bytes()),
        "bytes": destination.stat().st_size,
        "payload_members": len(manifest["members"]),
    }


def verify(source):
    if source.resolve() != source.absolute() or not source.is_file():
        raise ValueError("Archive must be a regular file without aliases")
    with zipfile.ZipFile(source) as archive:
        entries = archive.infolist()
        if len(entries) > 2000 or sum(i.file_size for i in entries) > MAX_BYTES:
            raise ValueError("Archive exceeds bounded delivery limits")
        if len({i.filename for i in entries}) != len(entries):
            raise ValueError("Duplicate archive members")
        for entry in entries:
            safe_name(entry.filename)
            if entry.external_attr >> 16 != 0o100600:
                raise ValueError("Nonregular or unexpected archive permissions")
        manifest = json.loads(archive.read("MANIFEST.json"))
        if set(archive.namelist()) != set(manifest["members"]) | {"MANIFEST.json"}:
            raise ValueError("Manifest member set differs")
        for name, expected in manifest["members"].items():
            data = archive.read(name)
            if len(data) != expected["bytes"] or sha(data) != expected["sha256"]:
                raise ValueError("Member digest differs: " + name)
        return manifest


def restore(source, destination):
    manifest = verify(source)
    parent = destination.parent
    if (
        parent.resolve() != parent.absolute()
        or not parent.is_dir()
        or parent.stat().st_mode & 0o077
    ):
        raise ValueError("Restore requires an existing private0700 parent without aliases")
    destination.mkdir(mode=0o700)  # Existing destinations are never overwritten.
    with zipfile.ZipFile(source) as archive:
        for name in sorted(set(manifest["members"]) | {"MANIFEST.json"}):
            path = destination.joinpath(*safe_name(name).parts)
            current = destination
            for component in path.relative_to(destination).parts[:-1]:
                current /= component
                current.mkdir(mode=0o700, exist_ok=True)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(archive.read(name))
    return {"destination": str(destination), "payload_members": len(manifest["members"])}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify", "restore"))
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        result = build(args.repository, args.output)
    elif args.command == "restore":
        result = restore(args.source, args.destination)
    else:
        verified = verify(args.source)
        result = {"verified_payload_members": len(verified["members"])}
    print(json.dumps(result, sort_keys=True))
