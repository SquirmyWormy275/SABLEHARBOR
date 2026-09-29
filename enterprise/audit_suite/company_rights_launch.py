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
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from .company_native_rights import NativeRecordClosure
from .company_rights_producer import (
    CompanyRightsProducer,
    RightsUnavailable,
    VerifiedCaseContext,
    pinned_git_source_reader,
)
from .store import DomainError, Store, canonical

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = "enterprise/ccf/company_closeout/source/information_policy_2026_09_22.json"
POLICY_MODULE = "enterprise/ccf/company_closeout/information_policy.py"
REHEARSAL_PATH = "enterprise/ccf/company_closeout/source/daedalus_rehearsal_2026_09_29.json"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private_data(path: Path, expected_sha256: str):
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
        return json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DomainError("Protected company config is invalid JSON", status=503) from exc


def _private_config(path: Path, expected_sha256: str) -> dict:
    config = _private_data(path, expected_sha256)
    required = {
        "version", "source_commit", "policy_sha256", "policy_module_sha256",
        "rights_root", "checkpoint_root",
    }
    rehearsal = {
        "rehearsal_authority_sha256", "rehearsal_binding_file", "rehearsal_binding_sha256"
    }
    optional = {"native_manifest_file", "native_manifest_sha256"} | rehearsal
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
        or len(rehearsal & set(config)) not in (0, len(rehearsal))
    ):
        raise DomainError("Protected company config schema invalid", status=503)
    if "native_manifest_sha256" in config and (
        not isinstance(config["native_manifest_sha256"], str)
        or not _SHA.fullmatch(config["native_manifest_sha256"])
    ):
        raise DomainError("Native closure hash required", status=503)
    for key in ("rehearsal_authority_sha256", "rehearsal_binding_sha256"):
        if key in config and (
            not isinstance(config[key], str) or not _SHA.fullmatch(config[key])
        ):
            raise DomainError("Exact rehearsal source and binding hashes required", status=503)
    for key in (
        "rights_root", "checkpoint_root", "native_manifest_file", "rehearsal_binding_file"
    ):
        if key in config and (
            not isinstance(config[key], str) or not Path(config[key]).is_absolute()
        ):
            raise DomainError("Absolute protected company paths required", status=503)
    return config


def _rehearsal(config: dict, source) -> tuple[dict, dict]:
    if "rehearsal_authority_sha256" not in config:
        raise DomainError("Reviewed rehearsal authority not configured", status=503)
    raw = source(REHEARSAL_PATH)
    if hashlib.sha256(raw).hexdigest() != config["rehearsal_authority_sha256"]:
        raise DomainError("Accepted rehearsal authority changed", status=503)
    try:
        authority = json.loads(raw)
        binding = _private_data(
            Path(config["rehearsal_binding_file"]), config["rehearsal_binding_sha256"]
        )
        roles = {
            row["role"]: row["person_id"] for row in authority["person_bindings"]
        }
        records = authority["records"]
        clock = authority["case_clock_approval"]
        if (
            authority["document_id"] != "SH-DAE-REHEARSAL-AUTH-20260929"
            or authority["policy_source"]["source_path"] != POLICY_PATH
            or authority["policy_source"]["source_sha256"] != config["policy_sha256"]
            or authority["person_population"]["population_count"] != 702
            or authority["engagement"]["tenant"] != "SH"
            or authority["engagement"]["purpose"] != "inspection"
            or set(roles) != {"auditor", "record_owner"}
            or len(authority["person_bindings"]) != 2
            or clock["approved_by_person_id"] != roles["record_owner"]
            or clock["learner_may_advance"] is not False
            or authority["grant_authorization"]["approved_by_person_id"]
            != roles["record_owner"]
            or authority["grant_authorization"]["reviewed_person_id"] != roles["auditor"]
            or not authority["record_population"]["complete_for_scope"]
            or len(records) != len(authority["record_population"]["expected_record_ids"])
            or {r["record_id"] for r in records}
            != set(authority["record_population"]["expected_record_ids"])
            or type(binding["version"]) is not int
            or binding["version"] != 1
            or set(binding) != {"version", "authority_sha256", "engagement_id", "principals"}
            or binding["authority_sha256"] != config["rehearsal_authority_sha256"]
            or not isinstance(binding["engagement_id"], str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", binding["engagement_id"])
            or not isinstance(binding["principals"], dict)
            or set(binding["principals"]) != set(roles)
            or len(set(binding["principals"].values())) != len(roles)
            or any(
                not isinstance(value, str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value)
                for value in binding["principals"].values()
            )
        ):
            raise ValueError("Rehearsal authority or private binding changed")
        if not isinstance(clock["case_as_of"], str):
            raise ValueError("Approved case clock missing")
        instant = datetime.fromisoformat(clock["case_as_of"].replace("Z", "+00:00"))
        if instant.utcoffset() is None:
            raise ValueError("Approved case clock lacks timezone")
        for pinned in (authority["person_population"], authority["case_source"]):
            if hashlib.sha256(source(pinned["source_path"])).hexdigest() != pinned[
                "source_sha256"
            ]:
                raise ValueError("Rehearsal dependency source changed")
        for row in records:
            if (
                row["tenant"] != "SH"
                or row["purposes"] != ["inspection"]
                or row["owner_id"] != roles["record_owner"]
                or {grant["subject_id"] for grant in row["grants"]} - set(roles.values())
                or hashlib.sha256(source(row["repository_path"])).hexdigest()
                != row["source_sha256"]
            ):
                raise ValueError("Rehearsal record source or grant changed")
    except (AttributeError, KeyError, TypeError, ValueError, RightsUnavailable) as exc:
        raise DomainError("Reviewed rehearsal authority or binding invalid", status=503) from exc
    return authority, binding


def _case_for_context(
    authority: dict, binding: dict, context: VerifiedCaseContext
) -> str:
    roles = {row["role"]: row["person_id"] for row in authority["person_bindings"]}
    if (
        context.engagement_id != binding["engagement_id"]
        or context.tenant != authority["engagement"]["tenant"]
        or context.purpose != authority["engagement"]["purpose"]
        or not any(
            context.principal_id == binding["principals"][role]
            and context.person_id == person
            for role, person in roles.items()
        )
    ):
        raise RightsUnavailable("Approved engagement case identity unavailable")
    return authority["case_clock_approval"]["case_as_of"]


def _exact_staged(producer: CompanyRightsProducer, authority: dict, binding: dict) -> None:
    roles = {row["role"]: row["person_id"] for row in authority["person_bindings"]}
    expected_bindings = sorted(
        (
            principal,
            binding["engagement_id"],
            roles[role],
            authority["engagement"]["tenant"],
            authority["engagement"]["purpose"],
        )
        for role, principal in binding["principals"].items()
    )
    expected_records = sorted(
        (
            row["record_id"], row["repository_path"], row["source_sha256"], canonical(row)
        )
        for row in authority["records"]
    )
    with producer._locked():
        with producer._db(producer.rights_db) as db:
            current_bindings = sorted(
                tuple(row) for row in db.execute(
                    "SELECT principal,engagement,person_id,tenant,purpose FROM bindings"
                )
            )
            current_records = sorted(
                tuple(row) for row in db.execute(
                    "SELECT record_id,repository_path,source_sha256,policy_row FROM records"
                )
            )
            if (
                producer._revision(db) != len(expected_bindings) + len(expected_records)
                or current_bindings != expected_bindings
                or current_records != expected_records
            ):
                raise RightsUnavailable("Exact staged rehearsal rights population unavailable")
    producer.checkpoint()


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


def reviewed_company_factories(
    config_file: Path, config_sha256: str, *, require_staged: bool = True
):
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
    rehearsal = "rehearsal_authority_sha256" in config
    if rehearsal:
        _rehearsal(config, source)

    def rights_factory(engine):
        _checked_source(config)
        producer_ref = None

        def approved_case(context: VerifiedCaseContext) -> str:
            if _private_config(config_file, config_sha256) != config:
                raise RightsUnavailable("Protected launch configuration changed")
            _checked_source(config)
            authority, binding = _rehearsal(config, source)
            if producer_ref is None:
                raise RightsUnavailable("Protected producer unavailable")
            _exact_staged(producer_ref, authority, binding)
            return _case_for_context(authority, binding, context)

        producer = CompanyRightsProducer(
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
            case_as_of=approved_case if rehearsal else None,
        )
        producer_ref = producer
        if rehearsal and require_staged:
            authority, binding = _rehearsal(config, source)
            _exact_staged(producer, authority, binding)
        return producer

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


def stage_reviewed_company_authority(
    config_file: Path, config_sha256: str, private_root: Path
) -> dict:
    """Explicitly stage only the accepted rehearsal rows in a fresh rights store.

    Portal principals and engagement must already exist and have membership.
    A failed partial stage requires fresh private rights/checkpoint roots; it
    never silently continues from an unknown revision.
    """
    config = _private_config(config_file, config_sha256)
    _checked_source(config)
    source = pinned_git_source_reader(ROOT, config["source_commit"])
    authority, binding = _rehearsal(config, source)
    rights_factory, _ = reviewed_company_factories(
        config_file, config_sha256, require_staged=False
    )
    store = Store(private_root)
    producer = rights_factory(SimpleNamespace(store=store))
    roles = {row["role"]: row["person_id"] for row in authority["person_bindings"]}
    for role, principal in binding["principals"].items():
        with store.connect() as db:
            store._authorize(db, principal, binding["engagement_id"])
        if roles[role] not in producer.known_person_ids:
            raise DomainError("Reviewed rehearsal person absent from census", status=503)
    for row in authority["records"]:
        producer.validate_record(row)
    with producer._locked():
        with producer._db(producer.rights_db) as db:
            if (
                producer._revision(db) != 0
                or db.execute("SELECT count(*) FROM bindings").fetchone()[0]
                or db.execute("SELECT count(*) FROM records").fetchone()[0]
            ):
                raise DomainError("Fresh empty rights store required for staging", status=503)
    revision = 0
    try:
        for role in ("auditor", "record_owner"):
            revision = producer.bind_person(
                principal_id=binding["principals"][role],
                engagement_id=binding["engagement_id"],
                person_id=roles[role],
                tenant=authority["engagement"]["tenant"],
                purpose=authority["engagement"]["purpose"],
                expected_revision=revision,
            )
        for row in authority["records"]:
            revision = producer.put_record(row, expected_revision=revision)
    except RightsUnavailable as exc:
        raise DomainError(
            "Rehearsal staging failed; use fresh private rights roots", status=503
        ) from exc
    return {
        "status": "STAGED_SYNTHETIC_REHEARSAL",
        "source_commit": config["source_commit"],
        "authority_sha256": config["rehearsal_authority_sha256"],
        "engagement_id": binding["engagement_id"],
        "bindings": len(roles),
        "records": len(authority["records"]),
        "rights_revision": revision,
        "checkpoint_epoch": producer.checkpoint()["epoch"],
    }
