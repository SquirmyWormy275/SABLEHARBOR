"""Package clean source and reconciled runtime outputs without replacing old releases."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from . import model


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def verify_archive(path):
    with ZipFile(path) as archive:
        manifest = json.loads(archive.read("MANIFEST.json"))
        expected = manifest["files"]
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(expected) | {
            "MANIFEST.json"
        }:
            raise ValueError("Release inventory mismatch")
        for name, digest in expected.items():
            if sha(archive.read(name)) != digest:
                raise ValueError("Release checksum mismatch: " + name)
        return manifest


def build(output):
    root = model.ROOT
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=root).strip():
        raise ValueError("Release packaging requires clean source")
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    generated = root / "enterprise/generated/runtime-v1"
    identity = json.loads((generated / "identity.json").read_text())
    source_digest = model.export(model.load())["source_sha256"]
    if (
        identity["dirty_development_build"]
        or identity["source_revision"] != head
        or identity["runtime_source_sha256"] != source_digest
    ):
        raise ValueError("Release needs a clean financial build of this commit")
    financial = json.loads((generated / "manifest.json").read_text())
    for relative, digest in financial.items():
        if sha((generated / relative).read_bytes()) != digest:
            raise ValueError("Financial artifact drift: " + relative)
    files = {}
    tracked = (
        subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
        .decode()
        .split("\0")
    )
    for relative in filter(None, tracked):
        files["source/" + relative] = (root / relative).read_bytes()
    for path in sorted(generated.rglob("*")):
        if path.is_file():
            files["runtime-finance/" + str(path.relative_to(generated))] = (
                path.read_bytes()
            )
    from .database import build as build_database
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "runtime.sqlite3"
        build_database(database, model.export(model.load()))
        files["runtime-registers/runtime.sqlite3"] = database.read_bytes()
    manifest = dict(
        version="1.0.0",
        source_revision=head,
        runtime_source_sha256=source_digest,
        classification="SYNTHETIC_DESIGN_NOT_DEPLOYMENT_OR_OPERATING_ASSURANCE",
        files={k: sha(v) for k, v in sorted(files.items())},
    )
    files["MANIFEST.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "sable-harbor-runtime-estate-v1.0.0.zip"
    if archive.exists():
        raise ValueError("Refusing to overwrite an existing release archive")
    with ZipFile(archive, "x", compression=ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, payload in sorted(files.items()):
            info = ZipInfo(name, date_time=(2026, 9, 11, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, payload)
    verify_archive(archive)
    (output / "SHA256SUMS.txt").write_text(
        sha(archive.read_bytes()) + "  " + archive.name + "\n"
    )
    print(archive)
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
