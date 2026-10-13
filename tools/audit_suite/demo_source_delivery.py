"""Publish and read an allowlisted file edition without company or auditor imports.

The private edition descriptor is an operator input. Only the selected stage and
explicit public fields enter the release. Directories are published by rename
only after every member has been verified; an existing destination is refused.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path, PurePosixPath

SCHEMA = "sableharbor.source-files.v1"
PACKAGE_FIELDS = {
    "edition",
    "company",
    "boundary",
    "period_start",
    "period_end",
    "cutoff",
    "generated_at",
}
ARTIFACT_FIELDS = {
    "artifact_id",
    "version",
    "path",
    "media_type",
    "bytes",
    "sha256",
    "source_locator",
    "source_sha256",
    "event_at",
    "available_at",
    "classification",
    "derives_from",
    "supersedes",
}
FORBIDDEN = (
    "/home/",
    "/tmp/",
    "HARBOR-OPERATIONS-",
    "change-release-",
    "CLEAN",
    "MESSY",
    "expected_result",
    "instructor_key",
    "scenario_seed",
)


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def encode(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def read_json(path: Path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON field")
            result[key] = value
        return result

    return json.loads(path.read_bytes(), object_pairs_hook=unique)


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Explicit timestamp offset required")
    return result


def no_alias(path: Path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Path alias forbidden")


def member(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("Invalid member path")
    parts = PurePosixPath(relative)
    if parts.is_absolute() or any(p in {".", ".."} for p in parts.parts) or str(parts) != relative:
        raise ValueError("Escaping or noncanonical member path")
    path = root / relative
    no_alias(path)
    if not path.is_relative_to(root):
        raise ValueError("Escaping member")
    return path


def safe_text(content: bytes, extra=()):
    text = content.decode("utf-8", errors="ignore")
    if any(token in text for token in (*FORBIDDEN, *extra)):
        raise ValueError("Private routing or forbidden content in release")
    if re.search(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|password\s*[=:]\s*\S+)", text):
        raise ValueError("Potential credential in release")


def validate_manifest(manifest):
    if set(manifest) != {"schema", "package", "artifacts"} or manifest["schema"] != SCHEMA:
        raise ValueError("Unsupported manifest")
    package = manifest["package"]
    if set(package) != PACKAGE_FIELDS or any(
        not isinstance(v, str) or not v for v in package.values()
    ):
        raise ValueError("Invalid package fields")
    cutoff = timestamp(package["cutoff"])
    timestamp(package["generated_at"])
    if datetime.fromisoformat(package["period_start"]) > datetime.fromisoformat(
        package["period_end"]
    ):
        raise ValueError("Invalid period")
    if not isinstance(manifest["artifacts"], list) or not manifest["artifacts"]:
        raise ValueError("Empty edition")
    paths, identities = set(), set()
    for artifact in manifest["artifacts"]:
        if set(artifact) != ARTIFACT_FIELDS:
            raise ValueError("Invalid artifact fields")
        if type(artifact["version"]) is not int or artifact["version"] < 1:
            raise ValueError("Invalid version")
        identity = (artifact["artifact_id"], artifact["version"])
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", identity[0]):
            raise ValueError("Invalid artifact identity")
        if (
            identity in identities
            or artifact["path"] in paths
            or artifact["path"] == "manifest.json"
        ):
            raise ValueError("Duplicate identity/path")
        identities.add(identity)
        paths.add(artifact["path"])
        if type(artifact["bytes"]) is not int or artifact["bytes"] < 1:
            raise ValueError("Invalid size")
        for key in ("sha256", "source_sha256"):
            if not isinstance(artifact[key], str) or not re.fullmatch(
                r"[0-9a-f]{64}", artifact[key]
            ):
                raise ValueError("Invalid digest")
        if not isinstance(artifact["source_locator"], str) or not artifact[
            "source_locator"
        ].startswith("sh-source:"):
            raise ValueError("Opaque source locator required")
        if artifact["classification"] not in {"original", "derivative", "authored-company-record"}:
            raise ValueError("Invalid classification")
        if (
            artifact["classification"] != "derivative"
            and artifact["sha256"] != artifact["source_sha256"]
        ):
            raise ValueError("Original hash mismatch")
        if not isinstance(artifact["media_type"], str) or "/" not in artifact["media_type"]:
            raise ValueError("Invalid media type")
        available = timestamp(artifact["available_at"])
        event = timestamp(artifact["event_at"]) if artifact["event_at"] else None
        if available > cutoff or (event and event > available):
            raise ValueError("Unavailable source or reversed dates")
        for key in ("derives_from", "supersedes"):
            if not isinstance(artifact[key], list):
                raise ValueError("Invalid relationship list")
            for ref in artifact[key]:
                if (
                    set(ref) != {"artifact_id", "version", "sha256"}
                    or type(ref["version"]) is not int
                    or ref["version"] < 1
                ):
                    raise ValueError("Invalid relationship")
                if not re.fullmatch(r"[0-9a-f]{64}", ref["sha256"]):
                    raise ValueError("Invalid relationship hash")
        if artifact["classification"] == "derivative" and not artifact["derives_from"]:
            raise ValueError("Derivative requires source relationship")
    safe_text(encode(manifest))


def verify(root: Path):
    root = root.absolute()
    no_alias(root)
    manifest = read_json(member(root, "manifest.json"))
    validate_manifest(manifest)
    expected = {"manifest.json"}
    for artifact in manifest["artifacts"]:
        path = member(root, artifact["path"])
        if not path.is_file() or path.stat().st_nlink != 1:
            raise ValueError("Regular unaliased member required")
        data = path.read_bytes()
        if len(data) != artifact["bytes"] or digest(data) != artifact["sha256"]:
            raise ValueError("Artifact hash/size mismatch")
        if (
            artifact["media_type"].startswith("text/")
            or artifact["media_type"] == "application/json"
        ):
            safe_text(data)
        expected.add(artifact["path"])
    actual = set()
    for path in root.rglob("*"):
        no_alias(path)
        if not path.is_file() and not path.is_dir():
            raise ValueError("Unexpected member type")
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    if actual != expected:
        raise ValueError("Unexpected or missing package member")
    return manifest


def rename_new(source: Path, destination: Path):
    """Linux atomic no-replacement publication; the reader is platform independent."""
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, "renameat2", None)
    if rename is None:
        raise OSError(errno.ENOSYS, "Atomic no-replacement publication unavailable")
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(-100, os.fsencode(source), -100, os.fsencode(destination), 1):
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))


def publish(descriptor: Path, input_root: Path, stage: str, destination: Path):
    descriptor, input_root, destination = (
        p.absolute() for p in (descriptor, input_root, destination)
    )
    for path in (descriptor, input_root, destination):
        no_alias(path)
    if (
        destination.exists()
        or destination.is_relative_to(input_root)
        or input_root.is_relative_to(destination)
    ):
        raise ValueError("New destination outside input root required")
    config = read_json(descriptor)
    if set(config) != {"schema", "stages", "deny_tokens"} or config["schema"] != SCHEMA:
        raise ValueError("Invalid private descriptor")
    if stage not in config["stages"]:
        raise ValueError("Stage unavailable")
    selected = config["stages"][stage]
    if set(selected) != {"package", "artifacts"}:
        raise ValueError("Invalid stage")
    artifacts = []
    retained = []
    for spec in selected["artifacts"]:
        if set(spec) != ARTIFACT_FIELDS | {"input_path", "allowed"} or spec["allowed"] is not True:
            raise ValueError("Source denied or invalid")
        path = member(input_root, spec["input_path"])
        if not path.is_file() or path.stat().st_nlink != 1:
            raise ValueError("Source missing or aliased")
        data = path.read_bytes()
        if digest(data) != spec["sha256"] or len(data) != spec["bytes"]:
            raise ValueError("Source changed")
        public = {k: spec[k] for k in ARTIFACT_FIELDS}
        member(destination, public["path"])
        if public["media_type"].startswith("text/") or public["media_type"] == "application/json":
            safe_text(data, config["deny_tokens"])
        artifacts.append(public)
        retained.append(data)
    manifest = {"schema": SCHEMA, "package": selected["package"], "artifacts": artifacts}
    validate_manifest(manifest)
    safe_text(encode(manifest), config["deny_tokens"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    pending = Path(tempfile.mkdtemp(prefix=".pending-", dir=destination.parent))
    try:
        for artifact, data in zip(artifacts, retained, strict=True):
            path = member(pending, artifact["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        with (pending / "manifest.json").open("xb") as handle:
            handle.write(encode(manifest))
            handle.flush()
            os.fsync(handle.fileno())
        for directory in [p for p in pending.rglob("*") if p.is_dir()] + [pending]:
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        verify(pending)
        rename_new(pending, destination)
        fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except BaseException:
        shutil.rmtree(pending)
        raise
    return manifest


def flatten_population(population):
    """Keep account, subject and entitlement denominators distinct; reject duplicates."""
    rows, subjects, accounts = [], set(), set()
    for subject in population["members"]:
        sid = subject["subject_id"]
        if sid in subjects:
            raise ValueError("Duplicate review subject")
        subjects.add(sid)
        for account in subject["accounts"]:
            state = account["state"]
            aid = state["account_id"]
            if aid in accounts or state["subject_id"] != sid:
                raise ValueError("Duplicate account or mismatched join")
            accounts.add(aid)
            rights = state["rights"]
            if len(rights) != len(set(rights)):
                raise ValueError("Duplicate entitlement")
            rows.append(
                {"subject_id": sid, "relationship_kind": subject["relationship_kind"], **state}
            )
    return rows


def configuration_differences(baseline, observed):
    return [
        {"field": key, "approved": baseline.get(key), "observed": observed.get(key)}
        for key in sorted(set(baseline) | set(observed))
        if baseline.get(key) != observed.get(key)
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    reader = commands.add_parser("verify")
    reader.add_argument("directory", type=Path)
    writer = commands.add_parser("publish")
    writer.add_argument("--edition", type=Path, required=True)
    writer.add_argument("--input-root", type=Path, required=True)
    writer.add_argument("--stage", required=True)
    writer.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = (
            verify(args.directory)
            if args.command == "verify"
            else publish(args.edition, args.input_root, args.stage, args.destination)
        )
        print(
            json.dumps(
                {
                    "status": "VERIFIED",
                    "edition": result["package"]["edition"],
                    "artifacts": len(result["artifacts"]),
                }
            )
        )
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f"Source delivery failed: {error}\n")


if __name__ == "__main__":
    main()
