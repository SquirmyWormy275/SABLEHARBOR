"""Private operator-signed identity transitions for a retained ordinary tail.

Verification uses the externally pinned public key. The signing secret is used
only by trusted local operator methods and is excluded from transferable proofs
and review packets. Heads are new immutable files; reopen needs the exact
latest head pin, never a head inferred from the mutable database.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import stat
import sysconfig
import time
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .store import DomainError, canonical

HEAD_SCHEMA = "SH_RETAINED_LOCAL_AUTHORITY_HEAD_V1"
DOMAIN = b"SH_RETAINED_LOCAL_AUTHORITY_V1\n"
SESSION_DOMAIN = b"SH_RETAINED_SESSION_ISSUANCE_V1\n"
BACKEND_MODULES = (
    "cryptography",
    "cryptography.__about__",
    "cryptography.exceptions",
    "cryptography.utils",
    "cryptography.hazmat",
    "cryptography.hazmat.bindings",
    "cryptography.hazmat.bindings._rust",
    "cryptography.hazmat.primitives",
    "cryptography.hazmat.primitives.asymmetric",
    "cryptography.hazmat.primitives.hashes",
    "cryptography.hazmat.primitives._serialization",
    "cryptography.hazmat.primitives.asymmetric.ed25519",
)


def loaded_backend():
    """Explicit directly loaded signature implementation, not process attestation."""
    import cryptography

    origins = {}
    for name in BACKEND_MODULES:
        module = importlib.import_module(name)
        path = Path(module.__file__).absolute()
        require(
            path == path.resolve()
            and not any(p.is_symlink() for p in [path, *path.parents])
            and Path(module.__spec__.origin) == path
            and path.is_file(),
            "Unaliased loaded operator-signature origin required",
        )
        with path.open("rb") as stream:
            sha = hashlib.file_digest(stream, "sha256").hexdigest()
        origins[name] = {"path": str(path), "sha256": sha}
    return {
        "algorithm": "ED25519",
        "package": "cryptography",
        "version": cryptography.__version__,
        "python_abi": sysconfig.get_config_var("SOABI"),
        "origins": origins,
    }


def require(condition, message):
    if not condition:
        raise DomainError(message, code="INTEGRITY", status=503)


def private(path):
    path = Path(path).absolute()
    require(
        path == path.resolve() and not any(p.is_symlink() for p in [path, *path.parents]),
        "Unaliased private authority file required",
    )
    info = path.lstat()
    require(
        stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and not info.st_mode & 0o077,
        "Private ordinary authority file required",
    )
    return path


def read_pin(path, expected, limit):
    path = private(path)
    before = path.stat()
    require(before.st_size <= limit, "Bounded authority member required")
    raw = path.read_bytes()
    require(
        (
            lambda now: all(
                getattr(now, name) == getattr(before, name)
                for name in (
                    "st_dev",
                    "st_ino",
                    "st_mode",
                    "st_nlink",
                    "st_size",
                    "st_mtime_ns",
                    "st_ctime_ns",
                )
            )
        )(path.stat())
        and hashlib.sha256(raw).hexdigest() == expected,
        "Authority file differs from external pin",
    )
    return raw


def write_new(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}


def initialize(directory, prefix_sha256, engagement):
    """Create a local signing authority; no user identity or role is created."""
    directory = Path(directory)
    key = Ed25519PrivateKey.generate()
    secret = write_new(directory / "OPERATOR_SIGNING_SECRET.key", key.private_bytes_raw())
    descriptor = {
        "algorithm": "ED25519",
        "public_key_hex": key.public_key().public_bytes_raw().hex(),
        "private_signing_key": secret,
    }
    fields = {
        "schema": HEAD_SCHEMA,
        "prefix_sha256": prefix_sha256,
        "engagement": engagement,
        "sequence": 0,
        "last_hash": "",
    }
    signature = key.sign(DOMAIN + canonical(fields).encode()).hex()
    head = write_new(
        directory / "AUTHORITY_HEAD_00000000.json",
        (canonical(fields | {"signature": signature}) + "\n").encode(),
    )
    return descriptor, head


class LocalAuthority:
    def __init__(self, descriptor, head, *, directory, prefix_sha256, engagement):
        require(
            isinstance(descriptor, dict)
            and set(descriptor) == {"algorithm", "public_key_hex", "private_signing_key"}
            and descriptor["algorithm"] == "ED25519",
            "Exact operator authority required",
        )
        try:
            self.public = Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(descriptor["public_key_hex"])
            )
        except (TypeError, ValueError):
            raise DomainError(
                "Invalid operator verification key", code="INTEGRITY", status=503
            ) from None
        self.descriptor = descriptor
        self.head_choice = dict(head)
        self.directory = Path(directory)
        self.prefix_sha256 = prefix_sha256
        self.engagement = engagement
        self.read_head()

    def _verify(self, fields, signature):
        try:
            self.public.verify(bytes.fromhex(signature), DOMAIN + canonical(fields).encode())
        except (InvalidSignature, TypeError, ValueError):
            raise DomainError(
                "Operator authority signature refused", code="INTEGRITY", status=503
            ) from None

    def read_head(self):
        require(
            set(self.head_choice) == {"path", "sha256"},
            "Exact external authority-head pin required",
        )
        path = Path(self.head_choice["path"])
        require(
            path.parent == self.directory,
            "Authority head must be in its original private directory",
        )
        value = json.loads(read_pin(path, self.head_choice["sha256"], 65536))
        require(
            set(value)
            == {"schema", "prefix_sha256", "engagement", "sequence", "last_hash", "signature"}
            and value["schema"] == HEAD_SCHEMA
            and value["prefix_sha256"] == self.prefix_sha256
            and value["engagement"] == self.engagement
            and type(value["sequence"]) is int
            and value["sequence"] >= 0,
            "Exact original-identity authority head required",
        )
        self._verify({k: v for k, v in value.items() if k != "signature"}, value["signature"])
        return value

    def records(self, db):
        head = self.read_head()
        previous, sequence = "", 1
        for row in db.execute(
            "SELECT seq,body,sha256,signature FROM authority_events ORDER BY seq"
        ):
            body = row["body"]
            value = json.loads(body)
            require(
                type(row["seq"]) is int
                and row["seq"] == sequence
                and set(value)
                == {
                    "sequence",
                    "kind",
                    "principal",
                    "recorded_at",
                    "payload",
                    "previous_hash",
                    "prefix_sha256",
                    "engagement",
                }
                and type(value["sequence"]) is int
                and value["sequence"] == sequence
                and value["previous_hash"] == previous
                and value["prefix_sha256"] == self.prefix_sha256
                and value["engagement"] == self.engagement
                and canonical(value) == body
                and hashlib.sha256(body.encode()).hexdigest() == row["sha256"],
                "Signed operator transition sequence/body differs",
            )
            self._verify(value, row["signature"])
            yield value
            previous, sequence = row["sha256"], sequence + 1
        require(
            sequence - 1 == head["sequence"] and previous == head["last_hash"],
            "Operator transition history differs from exact externally pinned head",
        )
        require(self.read_head() == head, "Authority head changed during transition verification")

    def append(self, db, *, kind, principal, recorded_at, payload):
        """Trusted local signing operation; never called by an HTTP route."""
        head = self.read_head()
        # Verify the entire existing signed chain before extending it.
        for _ in self.records(db):
            pass
        fields = {
            "sequence": head["sequence"] + 1,
            "kind": kind,
            "principal": principal,
            "recorded_at": recorded_at,
            "payload": payload,
            "previous_hash": head["last_hash"],
            "prefix_sha256": self.prefix_sha256,
            "engagement": self.engagement,
        }
        secret = self.descriptor["private_signing_key"]
        require(
            set(secret) == {"path", "sha256"}, "Exact private operator signing-key pin required"
        )
        raw_key = read_pin(secret["path"], secret["sha256"], 32)
        key = Ed25519PrivateKey.from_private_bytes(raw_key)
        require(
            key.public_key().public_bytes_raw().hex() == self.descriptor["public_key_hex"],
            "Private signing key differs from externally pinned public authority",
        )
        body = canonical(fields)
        signature = key.sign(DOMAIN + body.encode()).hex()
        event_hash = hashlib.sha256(body.encode()).hexdigest()
        db.execute(
            "INSERT INTO authority_events VALUES (?,?,?,?)",
            (fields["sequence"], body, event_hash, signature),
        )
        head_fields = {
            "schema": HEAD_SCHEMA,
            "prefix_sha256": self.prefix_sha256,
            "engagement": self.engagement,
            "sequence": fields["sequence"],
            "last_hash": event_hash,
        }
        signed = head_fields | {
            "signature": key.sign(DOMAIN + canonical(head_fields).encode()).hex()
        }
        return write_new(
            self.directory / f"AUTHORITY_HEAD_{fields['sequence']:08d}.json",
            (canonical(signed) + "\n").encode(),
        )


def initialize_sessions(directory):
    """Separate server issuance key; never gives operator rotation authority."""
    key = Ed25519PrivateKey.generate()
    secret = write_new(
        Path(directory) / "SERVER_SESSION_SIGNING_SECRET.key", key.private_bytes_raw()
    )
    revocations = Path(directory) / "SESSION_REVOCATIONS"
    revocations.mkdir(mode=0o700)
    return {
        "algorithm": "ED25519",
        "public_key_hex": key.public_key().public_bytes_raw().hex(),
        "private_signing_key": secret,
        "revocation_directory": str(revocations),
    }


class SessionAuthority:
    """Public verification of actual successful login, not editable timestamps."""

    def __init__(self, descriptor, *, revocation_pins=None):
        require(
            type(descriptor) is dict
            and set(descriptor)
            == {"algorithm", "public_key_hex", "private_signing_key", "revocation_directory"}
            and descriptor["algorithm"] == "ED25519",
            "Exact server session authority required",
        )
        self.descriptor = descriptor
        self.revocations = Path(descriptor["revocation_directory"])
        require(
            revocation_pins is None or type(revocation_pins) is dict,
            "Session-revocation pins must be an exact mapping",
        )
        self.known_revocations = {} if revocation_pins is None else dict(revocation_pins)
        require(
            all(
                type(name) is str
                and re.fullmatch(r"[a-f0-9]{64}\.json", name)
                and type(sha) is str
                and re.fullmatch(r"[a-f0-9]{64}", sha)
                for name, sha in self.known_revocations.items()
            ),
            "Exact externally supplied session-revocation inventory required",
        )
        try:
            self.public = Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(descriptor["public_key_hex"])
            )
        except (TypeError, ValueError):
            raise DomainError(
                "Invalid server session verification key", code="INTEGRITY", status=503
            ) from None

    def issue(self, value):
        item = self.descriptor["private_signing_key"]
        require(
            type(item) is dict and set(item) == {"path", "sha256"},
            "Exact private session signing choice required",
        )
        raw = read_pin(Path(item["path"]), item["sha256"], 32)
        require(len(raw) == 32, "Exact private server session key required")
        key = Ed25519PrivateKey.from_private_bytes(raw)
        require(
            key.public_key().public_bytes_raw().hex() == self.descriptor["public_key_hex"],
            "Server issuance key differs from pinned public authority",
        )
        body = canonical(value)
        return body, key.sign(SESSION_DOMAIN + body.encode()).hex()

    def verify(self, body, signature):
        value = json.loads(body)
        require(canonical(value) == body, "Canonical signed session issuance required")
        try:
            self.public.verify(bytes.fromhex(signature), SESSION_DOMAIN + body.encode())
        except (InvalidSignature, TypeError, ValueError):
            raise DomainError(
                "Server session issuance signature differs", code="INTEGRITY", status=503
            ) from None
        return value

    def check_revocations(self, prefix_sha256, engagement):
        path = self.revocations
        require(
            path == path.resolve()
            and not any(p.is_symlink() for p in [path, *path.parents])
            and path.is_dir()
            and stat.S_IMODE(path.stat().st_mode) == 0o700,
            "Private ordinary session revocation directory required",
        )
        entries = {p.name: p for p in path.iterdir()}
        require(
            set(self.known_revocations) == set(entries),
            "Historical session revocation removed or unknown inventory added",
        )
        result = {}
        for name, member in entries.items():
            require(
                re.fullmatch(r"[a-f0-9]{64}\.json", name) is not None,
                "Exact server revocation locator required",
            )
            private(member)
            with member.open("rb") as stream:
                sha = hashlib.file_digest(stream, "sha256").hexdigest()
            if name in self.known_revocations:
                require(
                    sha == self.known_revocations[name], "Historical session revocation changed"
                )
            record = json.loads(read_pin(member, sha, 65536))
            require(
                type(record) is dict and set(record) == {"body", "signature"},
                "Exact signed server revocation required",
            )
            value = self.verify(record["body"], record["signature"])
            require(
                set(value)
                == {"kind", "token_hash", "principal", "prefix_sha256", "engagement", "recorded_at"}
                and value["kind"] == "SESSION_LOGOUT"
                and value["token_hash"] == name.removesuffix(".json")
                and value["prefix_sha256"] == prefix_sha256
                and value["engagement"] == engagement
                and type(value["principal"]) is str
                and type(value["recorded_at"]) in (int, float)
                and 0 < value["recorded_at"] <= time.time(),
                "Signed logout identity/clock differs",
            )
            result[name] = sha
        self.known_revocations = result  # Integrity hashes only, never sessions or outcomes.
        return {name.removesuffix(".json") for name in result}

    def logout(self, token_hash, principal, prefix_sha256, engagement):
        revoked = self.check_revocations(prefix_sha256, engagement)
        if token_hash in revoked:
            return
        value = {
            "kind": "SESSION_LOGOUT",
            "token_hash": token_hash,
            "principal": principal,
            "prefix_sha256": prefix_sha256,
            "engagement": engagement,
            "recorded_at": time.time(),
        }
        body, signature = self.issue(value)
        pin = write_new(
            self.revocations / (token_hash + ".json"),
            (canonical({"body": body, "signature": signature}) + "\n").encode(),
        )
        fd = os.open(self.revocations, os.O_RDONLY | os.O_DIRECTORY)
        os.fsync(fd)
        os.close(fd)
        self.known_revocations[token_hash + ".json"] = pin["sha256"]
        self.check_revocations(prefix_sha256, engagement)
