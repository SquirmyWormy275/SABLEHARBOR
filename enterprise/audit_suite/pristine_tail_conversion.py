"""Derived storage for an externally approved, pristine delegated tail.

The execution tuple is an explicit trusted operator input. The original signed
delegation and consumed receipt are checked as provenance, never re-consumed or
interpreted as a bearer identity. Same IDs alone cannot prove which process
produced a parent tail. Raw prefix bytes, user authority and expiry stay exact.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
import stat
import time
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .canonical_state_codec import SCHEMA as NODE_SCHEMA
from .canonical_state_codec import SQL, encode
from .history_inspection import _stamp
from .sealed_history_authority import LocalAuthority, loaded_backend, read_pin, write_new
from .sealed_history_store import (
    CODEC_SCHEMA,
    TAIL_SQL,
    SealedHistoryStore,
    _file_sha,
    _private,
    _schema_hash,
)
from .sealed_history_store import (
    SCHEMA as PARENT_SCHEMA,
)
from .sealed_history_store import (
    _require as require,
)
from .store import DomainError, _ClosingConnection, canonical, digest

SCHEMA = "SH_PRISTINE_DELEGATED_TAIL_STORAGE_CONVERSION_V1"
DELEGATION_SCHEMA = "SH_ORIGINAL_OPERATOR_PREEXPIRY_SEAL_DELEGATION_V1"
DELEGATION_DOMAIN = (DELEGATION_SCHEMA + "\n").encode()
ACTION = "ONE_FINAL_PREFIX_PREPARATION_ATTEMPT_WITH_SAME_ID_INITIAL_ROTATION"
PARENT_FIELDS = {
    "schema",
    "audit_root",
    "prefix",
    "tail_path",
    "initial_tail_sha256",
    "tail_schema_sha256",
    "operator_authority",
    "session_authority",
    "initial_authority_head",
}
DERIVATION_FIELDS = {
    "schema",
    "parent_manifest",
    "parent_head",
    "parent_tail",
    "delegation",
    "consumed",
}


def _pinned(choice, limit=1024 * 1024):
    require(
        type(choice) is dict and set(choice) == {"path", "sha256"},
        "Exact external file pin required",
    )
    return json.loads(read_pin(choice["path"], choice["sha256"], limit))


def _code_files(origins):
    # These are the preserved producer's literal files, not an assertion that
    # those modules are loaded in this separate storage-conversion process.
    required = {
        "preexpiry_seal_delegation",
        "store",
        "sealed_history_store",
        "sealed_history_authority",
        "history_inspection",
        "recovery",
    }
    require(
        type(origins) is dict and {"enterprise.audit_suite." + x for x in required} <= set(origins),
        "Explicit preserved delegation producer origins required",
    )
    for name, choice in origins.items():
        require(
            type(name) is str
            and name.startswith("enterprise.audit_suite.")
            and type(choice) is dict
            and set(choice) == {"path", "sha256"},
            "Exact preserved producer code pin required",
        )
        path = Path(choice["path"]).absolute()
        before = path.stat()
        require(
            path == path.resolve()
            and not any(x.is_symlink() for x in [path, *path.parents])
            and stat.S_ISREG(before.st_mode)
            and before.st_nlink == 1,
            "Unaliased preserved producer code required",
        )
        require(
            _file_sha(path) == choice["sha256"]
            and all(
                getattr(path.stat(), k) == getattr(before, k)
                for k in (
                    "st_dev",
                    "st_ino",
                    "st_mode",
                    "st_nlink",
                    "st_size",
                    "st_mtime_ns",
                    "st_ctime_ns",
                )
            ),
            "Preserved producer code changed",
        )


def _provenance(derivation, parent):
    choice = derivation["delegation"]
    require(
        type(choice) is dict and set(choice) == {"path", "sha256", "public_key_hex"},
        "Exact previously consumed delegation pin required",
    )
    value = _pinned({k: choice[k] for k in ("path", "sha256")})
    require(type(value) is dict, "Signed original delegation object required")
    fields = {k: v for k, v in value.items() if k != "signature"}
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(choice["public_key_hex"])).verify(
            bytes.fromhex(value["signature"]), DELEGATION_DOMAIN + canonical(fields).encode()
        )
    except (InvalidSignature, ValueError, TypeError, KeyError):
        raise DomainError(
            "Original delegation provenance signature refused", code="INTEGRITY", status=503
        ) from None
    require(
        set(fields)
        == {
            "schema",
            "action",
            "audit_root",
            "prefix_path",
            "engagement",
            "operator",
            "membership",
            "birth",
            "binding",
            "code_origins",
            "signature_backend",
            "issued_at",
            "deadline",
            "nonce",
        }
        and fields["schema"] == DELEGATION_SCHEMA
        and fields["action"] == ACTION
        and fields["audit_root"] == parent["audit_root"]
        and fields["prefix_path"] == parent["prefix"]["path"]
        and fields["engagement"] == parent["prefix"]["engagement"]
        and fields["membership"] == "instruct"
        and all(
            type(fields[k]) in (int, float) and math.isfinite(fields[k])
            for k in ("issued_at", "deadline")
        )
        and 60 <= fields["deadline"] - fields["issued_at"] <= 86400
        and type(fields["operator"]) is dict
        and type(fields["operator"].get("expires")) in (int, float)
        and math.isfinite(fields["operator"]["expires"])
        and fields["issued_at"] < fields["operator"]["expires"]
        and digest(fields["signature_backend"]) == digest(loaded_backend()),
        "Exact consumed delegation authority/provenance required",
    )
    _code_files(fields["code_origins"])
    _pinned(fields["binding"], 65536)
    receipt = _pinned(derivation["consumed"], 65536)
    require(
        type(receipt) is dict
        and set(receipt)
        == {"schema", "delegation_sha256", "operator", "engagement", "consumed_at", "status"}
        and receipt["schema"] == DELEGATION_SCHEMA + "_CONSUMED"
        and receipt["delegation_sha256"] == choice["sha256"]
        and receipt["operator"] == fields["operator"].get("id")
        and receipt["engagement"] == fields["engagement"]
        and type(receipt["consumed_at"]) in (int, float)
        and math.isfinite(receipt["consumed_at"])
        and fields["issued_at"] <= receipt["consumed_at"] < fields["deadline"]
        and receipt["consumed_at"] <= time.time()
        and receipt["status"] == "ONE_ATTEMPT_CONSUMED_BEFORE_PREFIX_PUBLICATION",
        "Exact successful externally approved consumption tuple required",
    )
    return fields


def _parent(derivation, prefix, *, expected_stamp=None):
    require(
        type(derivation) is dict
        and set(derivation) == DERIVATION_FIELDS
        and derivation["schema"] == SCHEMA,
        "Exact pristine storage derivation required",
    )
    parent = _pinned(derivation["parent_manifest"])
    require(
        type(parent) is dict
        and set(parent) == PARENT_FIELDS
        and parent["schema"] == PARENT_SCHEMA
        and digest(parent["prefix"]) == digest(prefix),
        "Exact original ordinary-tail parent required",
    )
    require(
        derivation["parent_head"] == parent["initial_authority_head"]
        and derivation["parent_tail"]
        == {"path": parent["tail_path"], "sha256": parent["initial_tail_sha256"]},
        "Externally approved pristine parent/head tuple differs",
    )
    authority = LocalAuthority(
        parent["operator_authority"],
        derivation["parent_head"],
        directory=Path(derivation["parent_manifest"]["path"]).parent,
        prefix_sha256=prefix["sha256"],
        engagement=prefix["engagement"],
    )
    head = authority.read_head()
    require(
        head["sequence"] == 0 and head["last_hash"] == "", "Parent authority already transitioned"
    )
    _provenance(derivation, parent)
    tail = _private(parent["tail_path"])
    outside = _stamp(tail)
    require(not any(outside[0][1:]), "Pristine parent must close without sidecars")
    if expected_stamp is not None:
        require(outside == expected_stamp, "Immutable pristine parent tail changed")
    else:
        require(
            _file_sha(tail) == parent["initial_tail_sha256"] and _stamp(tail) == outside,
            "Externally pinned pristine parent physical image differs",
        )
        _initial_projection(parent, _provenance(derivation, parent))
    directory = _private(parent["session_authority"]["revocation_directory"], directory=True)
    require(
        directory == tail.parent / "SESSION_REVOCATIONS" and not any(directory.iterdir()),
        "Pristine parent contains logout history",
    )
    return parent, outside


def _initial_projection(parent, fields):
    """Reopen validates the preserved parent intrinsically, beyond repaired pins."""
    path = Path(parent["tail_path"])
    outside = _stamp(path)
    with sqlite3.connect(path.as_uri() + "?mode=rw", uri=True, factory=_ClosingConnection) as db:
        db.row_factory = sqlite3.Row
        db.execute("BEGIN IMMEDIATE")
        db.execute("PRAGMA query_only=ON")
        inside = _stamp(path)
        require(_schema_hash(db) == parent["tail_schema_sha256"], "Parent ordinary schema changed")
        require(
            all(
                db.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] == 0
                for name in ("event_tail", "authority_events", "issued_sessions")
            ),
            "Parent is no longer pristine",
        )
        current = db.execute("SELECT id,revision,state FROM engagements").fetchall()
        prefix = parent["prefix"]
        require(
            len(current) == 1
            and current[0]["id"] == prefix["engagement"]
            and type(current[0]["revision"]) is int
            and current[0]["revision"] == prefix["revision"]
            and hashlib.sha256(current[0]["state"].encode()).hexdigest()
            == prefix["current_state_sha256"],
            "Parent initial current-state projection changed",
        )
        require(
            all(
                digest([dict(r) for r in db.execute(f"SELECT * FROM {name} ORDER BY 1")])
                == expected
                for name, expected in prefix["initial_auth_sha256"].items()
            )
            and set(prefix["initial_auth_sha256"]) == {"principals", "members", "sessions"},
            "Parent initial identities/members/sessions changed",
        )
        operator = db.execute(
            "SELECT * FROM principals WHERE id=?", (fields["operator"]["id"],)
        ).fetchone()
        member = db.execute(
            "SELECT permission FROM members WHERE engagement=? AND principal=?",
            (prefix["engagement"], fields["operator"]["id"]),
        ).fetchone()
        require(
            operator is not None
            and digest(dict(operator)) == digest(fields["operator"])
            and type(operator["revoked"]) is int
            and operator["revoked"] == 0
            and json.loads(operator["roles"]) == ["instructor"]
            and member is not None
            and member[0] == "instruct",
            "Parent original instructor changed",
        )
        require(_stamp(path) == inside, "Parent changed during initial validation")
    require(_stamp(path) == outside, "Parent changed during initial closure")


def verify_derivation(store, *, expected_stamp=None):
    parent, stamp = _parent(
        store.manifest["storage_derivation"], store.prefix, expected_stamp=expected_stamp
    )
    require(
        store.manifest["operator_authority"]["algorithm"]
        == parent["operator_authority"]["algorithm"]
        and store.manifest["operator_authority"]["public_key_hex"]
        == parent["operator_authority"]["public_key_hex"]
        and store.manifest["operator_authority"]["private_signing_key"]["sha256"]
        == parent["operator_authority"]["private_signing_key"]["sha256"]
        and store.manifest["session_authority"]["public_key_hex"]
        == parent["session_authority"]["public_key_hex"]
        and store.manifest["session_authority"]["private_signing_key"]["sha256"]
        == parent["session_authority"]["private_signing_key"]["sha256"]
        and store.manifest["initial_authority_head"]["sha256"]
        == parent["initial_authority_head"]["sha256"],
        "Derived storage changed original signing authority",
    )
    return stamp


def convert_pristine_tail(audit_root, parent_manifest, delegation, consumed, destination):
    """Local storage conversion; no token authentication or second prefix preparation.

    The caller supplies the independently approved producer execution tuple.
    Expired bearer credentials remain expired. Full company/native/typed prefix
    bootstrap under the new exact code vector is still required before activation.
    """
    source = SealedHistoryStore(audit_root, parent_manifest["path"], parent_manifest["sha256"])
    require(source.state_codec is None, "An original ordinary delegated tail is required")
    derivation = {
        "schema": SCHEMA,
        "parent_manifest": parent_manifest,
        "parent_head": source.manifest["initial_authority_head"],
        "parent_tail": {
            "path": str(source.db_path),
            "sha256": source.manifest["initial_tail_sha256"],
        },
        "delegation": delegation,
        "consumed": consumed,
    }
    parent, outside = _parent(derivation, source.prefix)
    fields = _provenance(derivation, parent)
    target = Path(destination).absolute()
    _private(target.parent, directory=True)
    require(
        not any(p.is_symlink() for p in [target, *target.parents]),
        "New unaliased codec directory required",
    )
    # Validate the parent before reserving any new output. Only this target is written.
    with source.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("PRAGMA query_only=ON")
        inside = _stamp(source.db_path)
        source.verify_projection(db)
        require(
            all(
                db.execute(f"SELECT COUNT(*) FROM main.{name}").fetchone()[0] == 0
                for name in ("event_tail", "authority_events", "issued_sessions")
            ),
            "Pristine parent contains lifecycle or fieldwork events",
        )
        operator = db.execute(
            "SELECT * FROM main.principals WHERE id=?", (fields["operator"]["id"],)
        ).fetchone()
        require(
            operator is not None
            and digest(dict(operator)) == digest(fields["operator"])
            and type(operator["revoked"]) is int
            and operator["revoked"] == 0
            and json.loads(operator["roles"]) == ["instructor"]
            and db.execute(
                "SELECT permission FROM members WHERE engagement=? AND principal=?",
                (source.prefix["engagement"], operator["id"]),
            ).fetchone()[0]
            == "instruct",
            "Original delegated instructor authority changed",
        )
        birth = db.execute(
            "SELECT * FROM sealed_prefix.events WHERE revision=0 AND engagement=?",
            (source.prefix["engagement"],),
        ).fetchone()
        require(
            birth is not None
            and digest(fields["birth"])
            == digest(
                {
                    "state_sha256": hashlib.sha256(birth["state"].encode()).hexdigest(),
                    "hash": birth["hash"],
                    "command_id": birth["command_id"],
                    "actor": birth["actor"],
                }
            ),
            "Original delegated birth changed",
        )
        target.mkdir(mode=0o700)
        tail_path = target / "tail.sqlite3"
        fd = os.open(tail_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        with sqlite3.connect(tail_path, factory=_ClosingConnection) as tail:
            tail.row_factory = sqlite3.Row
            tail.executescript(TAIL_SQL.replace("event_tail", "event_frames"))
            tail.executescript(SQL)
            current = db.execute("SELECT state FROM main.engagements").fetchone()[0]
            root, size = encode(tail, json.loads(current))
            for table in ("principals", "engagements", "members", "sessions"):
                for row in db.execute(f"SELECT * FROM main.{table}"):
                    tail.execute(
                        f"INSERT INTO {table} VALUES ({','.join('?' for _ in row)})", tuple(row)
                    )
            tail_schema = _schema_hash(tail)
        require(
            _stamp(source.db_path) == inside and source.check_prefix() == source._prefix_stamp,
            "Pristine parent changed during conversion",
        )
    require(_stamp(source.db_path) == outside, "Pristine parent changed at conversion close")
    # Copy exact existing signing bytes/head; paths change, authority does not.
    operator_descriptor = dict(parent["operator_authority"])
    session_descriptor = dict(parent["session_authority"])
    for descriptor, name in (
        (operator_descriptor, "OPERATOR_SIGNING_SECRET.key"),
        (session_descriptor, "SERVER_SESSION_SIGNING_SECRET.key"),
    ):
        old = descriptor["private_signing_key"]
        descriptor["private_signing_key"] = write_new(
            target / name, read_pin(old["path"], old["sha256"], 64)
        )
    initial_head = write_new(
        target / "AUTHORITY_HEAD_00000000.json",
        read_pin(derivation["parent_head"]["path"], derivation["parent_head"]["sha256"], 65536),
    )
    revocations = target / "SESSION_REVOCATIONS"
    revocations.mkdir(mode=0o700)
    session_descriptor["revocation_directory"] = str(revocations)
    result = {
        "schema": CODEC_SCHEMA,
        "audit_root": str(source.root),
        "prefix": dict(source.prefix),
        "tail_path": str(tail_path),
        "initial_tail_sha256": _file_sha(tail_path),
        "tail_schema_sha256": tail_schema,
        "operator_authority": operator_descriptor,
        "session_authority": session_descriptor,
        "initial_authority_head": initial_head,
        "state_codec": {
            "schema": NODE_SCHEMA,
            "initial_root": root,
            "initial_state_bytes": size,
            "initial_state_sha256": hashlib.sha256(current.encode()).hexdigest(),
        },
        "storage_derivation": derivation,
    }
    _parent(derivation, source.prefix, expected_stamp=outside)
    source.check_prefix()
    return write_new(target / "SEALED_HISTORY.json", (canonical(result) + "\n").encode())
