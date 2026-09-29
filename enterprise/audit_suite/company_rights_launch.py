"""Opt-in, source-pinned launch configuration for a protected portal instance.

This loader creates no person binding, record grant, case clock or source row.
Those require separately reviewed operator staging. A protected service with an
empty rights store starts but denies all company disclosures.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path

from .company_native_rights import NativeRecordClosure
from .company_rights_producer import CompanyRightsProducer, pinned_git_source_reader
from .store import DomainError

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = "enterprise/ccf/company_closeout/source/information_policy_2026_09_22.json"
POLICY_MODULE = "enterprise/ccf/company_closeout/information_policy.py"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private_config(path: Path, expected_sha256: str) -> dict:
    if not isinstance(expected_sha256, str) or not _SHA.fullmatch(expected_sha256):
        raise DomainError("Exact protected company config hash required", status=503)
    path = Path(path).absolute()
    if (
        any(part.is_symlink() for part in (path, *path.parents))
        or not path.parent.is_dir()
        or path.parent.stat().st_mode & 0o077
    ):
        raise DomainError("Protected company config requires private directory", status=503)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_size > 65536:
                raise DomainError("Protected company config must be bounded mode 0600", status=503)
            content = stream.read(65537)
    except OSError as exc:
        raise DomainError("Protected company config unavailable", status=503) from exc
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        raise DomainError("Protected company config changed", status=503)
    try:
        config = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DomainError("Protected company config is invalid JSON", status=503) from exc
    required = {
        "version", "source_commit", "policy_sha256", "policy_module_sha256",
        "rights_root", "checkpoint_root",
    }
    optional = {"native_manifest_file", "native_manifest_sha256"}
    if (
        not isinstance(config, dict)
        or set(config) - optional != required
        or type(config["version"]) is not int
        or config["version"] != 1
        or not isinstance(config["source_commit"], str)
        or not _COMMIT.fullmatch(config["source_commit"])
        or any(
            not isinstance(config[key], str) or not _SHA.fullmatch(config[key])
            for key in ("policy_sha256", "policy_module_sha256")
        )
        or ("native_manifest_file" in config) != ("native_manifest_sha256" in config)
    ):
        raise DomainError("Protected company config schema invalid", status=503)
    if "native_manifest_sha256" in config and (
        not isinstance(config["native_manifest_sha256"], str)
        or not _SHA.fullmatch(config["native_manifest_sha256"])
    ):
        raise DomainError("Native closure hash required", status=503)
    for key in ("rights_root", "checkpoint_root", "native_manifest_file"):
        if key in config and (
            not isinstance(config[key], str) or not Path(config[key]).is_absolute()
        ):
            raise DomainError("Absolute protected company paths required", status=503)
    return config


def _checked_source(config: dict) -> None:
    try:
        current = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True, check=True, timeout=10, text=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain"],
            capture_output=True, check=True, timeout=10, text=True,
        ).stdout
        if current != config["source_commit"] or dirty:
            raise ValueError("Source checkout is not the exact clean configured commit")
        for path, field in (
            (POLICY_PATH, "policy_sha256"),
            (POLICY_MODULE, "policy_module_sha256"),
        ):
            working = ROOT / path
            if working.is_symlink() or _file_sha(working) != config[field]:
                raise ValueError("Accepted policy bytes changed")
            pinned = subprocess.run(
                ["git", "-C", str(ROOT), "show", f"{current}:{path}"],
                capture_output=True, check=True, timeout=10,
            ).stdout
            if hashlib.sha256(pinned).hexdigest() != config[field]:
                raise ValueError("Accepted policy commit pin changed")
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError) as exc:
        raise DomainError("Exact clean company source and policy required", status=503) from exc


def reviewed_company_factories(config_file: Path, config_sha256: str):
    """Return trusted factories for `service.create_app` at a clean source commit.

    The accepted 702-person census is verified through its existing generator.
    It supplies possible person IDs only, never a portal binding or entitlement.
    """
    config = _private_config(config_file, config_sha256)
    _checked_source(config)
    try:
        from enterprise.ccf.company_closeout import information_policy
        from enterprise.closeout import final_records

        if (
            Path(information_policy.__file__).resolve() != (ROOT / POLICY_MODULE).resolve()
            or Path(final_records.__file__).resolve()
            != (ROOT / "enterprise/closeout/final_records.py").resolve()
        ):
            raise ValueError("Accepted policy or census module path changed")

        rows = final_records.collect()["final_information_policy_subjects"]
        people = [json.loads(row["payload_json"])["person_id"] for row in rows]
        if len(people) != 702 or len(set(people)) != 702:
            raise ValueError("Complete accepted company person census required")
    except (ImportError, KeyError, TypeError, ValueError) as exc:
        raise DomainError("Accepted company person/policy source unavailable", status=503) from exc
    source = pinned_git_source_reader(ROOT, config["source_commit"])

    def rights_factory(engine):
        _checked_source(config)
        return CompanyRightsProducer(
            store=engine.store,
            rights_root=Path(config["rights_root"]),
            checkpoint_root=Path(config["checkpoint_root"]),
            policy_file=ROOT / POLICY_PATH,
            policy_sha256=config["policy_sha256"],
            source_commit=config["source_commit"],
            source_bytes=source,
            validate_record=information_policy.validate_record,
            decide=information_policy.decide,
            known_person_ids=frozenset(people),
        )

    native_factory = None
    if "native_manifest_file" in config:

        def native_factory(engine, producer):
            _checked_source(config)
            return NativeRecordClosure(
                producer=producer,
                manifest_file=Path(config["native_manifest_file"]),
                manifest_sha256=config["native_manifest_sha256"],
            )

    return rights_factory, native_factory
