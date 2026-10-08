"""Private declared relations between an unbound archive and a bound current Key.

This is reference navigation, never native evidence, rubric validation or grading.
Only existing literal canonical controls, episode/version declarations or scope
declarations can support stronger links. A name or missing binding supports none.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from copy import deepcopy
from datetime import UTC, date, datetime, time
from pathlib import Path

from .company_store import _time
from .corpus import obligations
from .source_library_audit import private_file
from .store import DomainError, canonical, digest

SCHEMA = "SH_PRIVATE_INSTRUCTOR_REFERENCE_CROSSWALK_V1"
STATUSES = {"EXACT", "SHARED_CONTROL_ONLY", "OUT_OF_SCOPE", "UNRESOLVED"}
MAX_BYTES = 4 * 1024 * 1024


def outside_period(left, right):
    """Only explicit complete, valid nonoverlapping periods prove exclusion.

    Different scope strings or a partial date declaration do not prove that an
    event is outside current scope. Cross-model boundary meanings stay unknown.
    """
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    try:
        values = [obj[key] for obj in (left, right) for key in ("period_start", "period_end")]
        if not all(isinstance(value, str) and value.strip() for value in values):
            return False
        points = []
        for i, value in enumerate(values):
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                points.append(
                    datetime.combine(
                        date.fromisoformat(value), time.max if i % 2 else time.min, tzinfo=UTC
                    )
                )
            else:
                points.append(datetime.fromisoformat(_time(value)))
        start, end, current_start, current_end = points
        return (
            start <= end
            and current_start <= current_end
            and (end < current_start or start > current_end)
        )
    except (KeyError, ValueError, TypeError, DomainError):
        return False


def require(condition, message):
    if not condition:
        raise DomainError(message, status=503)


def stamp(path):
    private_file(path)
    info = Path(path).stat()
    return tuple(
        getattr(info, n)
        for n in (
            "st_dev",
            "st_ino",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
            "st_mode",
            "st_nlink",
        )
    )


def read_pin(path, sha256, *, limit=MAX_BYTES):
    """Hash the consumed bytes, with ordinary name/FD identities on both sides."""
    path = Path(path)
    require(
        path.is_absolute() and isinstance(sha256, str) and re.fullmatch(r"[a-f0-9]{64}", sha256),
        "Exact reference pin required",
    )
    before = stamp(path)
    require(before[2] <= limit, "Reference object exceeds declared byte bound")
    with path.open("rb") as stream:
        require(os.fstat(stream.fileno()) == path.stat(), "Reference descriptor differs")
        raw = stream.read(limit + 1)
        # atime may change on read; use only the seven authoritative fields.
        fd = os.fstat(stream.fileno())
        require(
            tuple(
                getattr(fd, n)
                for n in (
                    "st_dev",
                    "st_ino",
                    "st_size",
                    "st_mtime_ns",
                    "st_ctime_ns",
                    "st_mode",
                    "st_nlink",
                )
            )
            == before,
            "Reference changed while reading",
        )
    require(
        stamp(path) == before and hashlib.sha256(raw).hexdigest() == sha256,
        "Reference byte pin or identity changed",
    )
    try:

        def unique_pairs(pairs):
            require(
                len({key for key, _ in pairs}) == len(pairs), "Ambiguous duplicate reference key"
            )
            return dict(pairs)

        value = json.loads(raw, object_pairs_hook=unique_pairs)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise DomainError("Invalid reference JSON", status=503) from error
    require(isinstance(value, dict), "Reference object required")
    return value


def cards(snapshot):
    expectations = snapshot["authored"]["expectations"]
    return [
        {
            "id": issue["id"],
            "sha256": digest(issue),
            "control_ids": list(issue["control_ids"]),
            "task_ids": sorted(
                {
                    task
                    for item in expectations
                    if issue["id"] in item["issue_ids"]
                    for task in item.get("task_ids", [])
                }
            ),
        }
        for issue in snapshot["authored"]["issues"]
    ]


def current_identity(snapshot):
    return {
        "engagement_id": snapshot["engagement"]["id"],
        "snapshot_sha256": digest(snapshot),
        "company_binding": deepcopy(snapshot["company_binding"]),
        "scope": deepcopy(snapshot["engagement"]["scope"]),
        "cards": cards(snapshot),
    }


def build_crosswalk(index, snapshot, archive, declarations=(), *, engineering_neutral_only=False):
    """Build a complete declared inventory. Strong declarations are validated on load.

    No source is read or relation guessed here. Publication is not acceptance.
    Production always requires 1,110 original variants and 76 current cards.
    """
    require(type(engineering_neutral_only) is bool, "Strict engineering boundary required")
    require(
        not engineering_neutral_only
        or snapshot["company_binding"]["company"].startswith("NEUTRAL-"),
        "Owned neutral company required",
    )
    entries, current = index["entries"], current_identity(snapshot)
    require(
        type(index["required"]) is int
        and type(index["migrated"]) is int
        and index["required"] == index["migrated"] == len(entries),
        "Exact archive denominator required",
    )
    require(
        index.get("schema") == "PRIVATE_INSTRUCTOR_KEY_INDEX_V1"
        and index.get("audience") == "INSTRUCTOR_ONLY",
        "Protected archive index required",
    )
    require(
        engineering_neutral_only or {e["id"] for e in entries} == set(obligations()),
        "Every exact canonical legacy variant/version required",
    )
    require(
        len({e["id"] for e in entries}) == len(entries)
        and len({c["id"] for c in current["cards"]}) == len(current["cards"]),
        "Distinct complete identities required",
    )
    require(
        engineering_neutral_only or (len(entries) == 1110 and len(current["cards"]) == 76),
        "Complete 1110-version and 76-card inventories required",
    )
    supplied = {}
    for declaration in declarations:
        require(
            isinstance(declaration, dict)
            and set(declaration) == {"legacy_id", "relations"}
            and declaration["legacy_id"] not in supplied,
            "Distinct exact declarations required",
        )
        supplied[declaration["legacy_id"]] = declaration["relations"]
    require(set(supplied) <= {e["id"] for e in entries}, "Foreign legacy declaration")
    rows = [
        {
            "legacy_id": e["id"],
            **{k: e[k] for k in ("raw_sha256", "canonical_sha256", "key_sha256")},
            "relations": supplied.get(
                e["id"],
                [
                    {
                        "current_id": None,
                        "status": "UNRESOLVED",
                        "reason": (
                            "No explicit current episode/version or scope relation is recorded."
                        ),
                        "proof": None,
                    }
                ],
            ),
        }
        for e in entries
    ]
    inverse = [
        {
            "current_id": c["id"],
            "legacy_ids": sorted(
                {
                    r["legacy_id"]
                    for r in rows
                    for relation in r["relations"]
                    if relation.get("current_id") == c["id"]
                }
            ),
            "unmapped_reason": "No declared legacy relation."
            if not any(x.get("current_id") == c["id"] for r in rows for x in r["relations"])
            else None,
        }
        for c in current["cards"]
    ]
    return {
        "schema": SCHEMA,
        "audience": "INSTRUCTOR_ONLY",
        "archive": archive,
        "current": current,
        "rows": rows,
        "inverse": inverse,
        "engineering_neutral_only": engineering_neutral_only,
        "professional_acceptance": "NOT_ASSERTED",
        "native_evidence_import": "PROHIBITED",
    }


def write_crosswalk(path, value):
    """New private file only. Caller externally preserves its pin after review."""
    path = Path(path)
    require(
        path.is_absolute()
        and not any(p.is_symlink() for p in [path.parent, *path.parents])
        and stat.S_IMODE(path.parent.stat().st_mode) == 0o700,
        "Private ordinary parent required",
    )
    raw = canonical(value).encode("utf-8")
    require(len(raw) <= MAX_BYTES, "Crosswalk byte bound exceeded")
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}


def build_reference_crosswalk(selection, snapshot, output, *, engineering_neutral_only=False):
    """Derive shared controls solely from the existing literal binding contract.

    An absent legacy scope never becomes OUT_OF_SCOPE; no names or prose are
    interpreted. Current five-field cards contain no episode/version declaration,
    so this builder cannot infer EXACT. All originals remain separately indexed.
    """
    root = Path(selection["root"])
    index = read_pin(root / "index.json", selection["index_sha256"])
    declarations = []
    for entry in index["entries"]:
        require(
            entry["source"] == f"sources/{entry['id']}.json", "Exact bounded source path required"
        )
        original = read_pin(root / entry["source"], entry["raw_sha256"])
        require(
            digest(original) == entry["canonical_sha256"], "Original canonical source pin differs"
        )
        contract = original.get("binding_contract", {})
        require(isinstance(contract, dict), "Typed literal binding contract required")
        controls = contract.get("applicable_control_ids", [])
        require(
            isinstance(controls, list) and all(isinstance(c, str) for c in controls),
            "Typed canonical controls required",
        )
        declared_scope, current_scope = contract.get("scope"), snapshot["engagement"]["scope"]
        relations = []
        if outside_period(declared_scope, current_scope):
            relations = [
                {
                    "current_id": None,
                    "status": "OUT_OF_SCOPE",
                    "reason": (
                        "The original complete declared period does not "
                        "overlap the current captured period."
                    ),
                    "proof": {
                        "legacy_pointer": "/binding_contract/scope",
                        "current_pointer": "/engagement/scope",
                    },
                }
            ]
        else:
            for i, card in enumerate(cards(snapshot)):
                shared = sorted(set(controls) & set(card["control_ids"]))
                if shared:
                    relations.append(
                        {
                            "current_id": card["id"],
                            "status": "SHARED_CONTROL_ONLY",
                            "reason": "Explicit canonical controls shared: "
                            + ", ".join(shared)
                            + ". Cause, source, branch, time and procedural "
                            "equivalence are not established.",
                            "proof": {
                                "legacy_pointer": "/binding_contract/applicable_control_ids",
                                "current_pointer": f"/authored/issues/{i}/control_ids",
                            },
                        }
                    )
        if relations:
            declarations.append({"legacy_id": entry["id"], "relations": relations})
    value = build_crosswalk(
        index, snapshot, selection, declarations, engineering_neutral_only=engineering_neutral_only
    )
    pin = write_crosswalk(Path(output), value)
    ReferenceLibrary(selection, pin, snapshot)
    return pin


def pointer(value, path):
    require(
        isinstance(path, str) and path.startswith("/") and len(path) <= 512,
        "Literal JSON pointer required",
    )
    try:
        for part in path[1:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            value = value[int(part)] if isinstance(value, list) and part.isdigit() else value[part]
        return value
    except (KeyError, TypeError, IndexError, ValueError) as error:
        raise DomainError("Declared relation pointer does not exist", status=503) from error


class ReferenceLibrary:
    def __init__(self, selection, crosswalk, snapshot):
        require(
            isinstance(selection, dict)
            and set(selection) == {"root", "index_sha256", "receipt_sha256", "archive_sha256"},
            "Exact archive selection required",
        )
        require(
            isinstance(crosswalk, dict) and set(crosswalk) == {"path", "sha256"},
            "Exact crosswalk selection required",
        )
        self.selection, self.crosswalk, self.snapshot = selection, crosswalk, snapshot
        self.root = Path(selection["root"])
        require(self.root.is_absolute(), "Absolute reference root required")
        self.index = read_pin(self.root / "index.json", selection["index_sha256"])
        receipt = read_pin(self.root / "receipt.json", selection["receipt_sha256"])
        require(
            receipt["index_sha256"] == selection["index_sha256"]
            and receipt["archive_sha256"] == selection["archive_sha256"]
            and receipt["company_store_import"] == "PROHIBITED",
            "Archive receipt differs",
        )
        self.files = {}
        self._members()
        self.check(snapshot)

    def _members(self):
        require(
            not any(p.is_symlink() for p in [self.root, *self.root.parents])
            and self.root.is_dir()
            and stat.S_IMODE(self.root.stat().st_mode) == 0o700,
            "Private ordinary reference directory required",
        )
        expected = {"index.json", "receipt.json", "instructor-keys.zip"}
        for entry in self.index["entries"]:
            require(
                re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", entry["id"]),
                "Exact legacy ID required",
            )
            require(
                entry["source"] == f"sources/{entry['id']}.json"
                and entry["key"] == f"keys/{entry['id']}.json",
                "Exact bounded legacy member paths required",
            )
            expected.update((entry["source"], entry["key"]))
        # A prior archive's independent verification receipt is preserved too.
        if (self.root / "verification.json").exists():
            expected.add("verification.json")
        actual, fingerprints, identities = set(), {}, {}
        for path in self.root.rglob("*"):
            require(not path.is_symlink(), "Reference aliases forbidden")
            if path.is_dir():
                require(
                    stat.S_IMODE(path.stat().st_mode) == 0o700,
                    "Private reference directory required",
                )
                continue
            name = path.relative_to(self.root).as_posix()
            actual.add(name)
            opening = stamp(path)
            with path.open("rb") as stream:
                sha = hashlib.file_digest(stream, "sha256").hexdigest()
            require(stamp(path) == opening, "Reference member changed during hash")
            fingerprints[name] = sha
            identities[name] = opening
        require(actual == expected, "Complete exact archive membership required")
        require(
            fingerprints["index.json"] == self.selection["index_sha256"]
            and fingerprints["receipt.json"] == self.selection["receipt_sha256"]
            and fingerprints["instructor-keys.zip"] == self.selection["archive_sha256"],
            "Archive external pins changed",
        )
        for entry in self.index["entries"]:
            require(
                fingerprints[entry["source"]] == entry["raw_sha256"]
                and fingerprints[entry["key"]] == entry["key_sha256"],
                "Original legacy member bytes differ",
            )
        require(not self.files or self.files == fingerprints, "Reference member inventory changed")
        self.files = fingerprints
        self.identities = identities

    def _close_members(self, crosswalk_identity):
        names = set()
        for path in self.root.rglob("*"):
            require(not path.is_symlink(), "Reference closing alias forbidden")
            if path.is_dir():
                require(
                    stat.S_IMODE(path.stat().st_mode) == 0o700,
                    "Reference closing directory differs",
                )
            else:
                name = path.relative_to(self.root).as_posix()
                names.add(name)
                require(
                    name in self.identities and stamp(path) == self.identities[name],
                    "Reference member changed after validation",
                )
        require(names == set(self.identities), "Reference closing membership differs")
        require(
            stamp(Path(self.crosswalk["path"])) == crosswalk_identity,
            "Crosswalk closing identity differs",
        )

    def check(self, snapshot=None):
        snapshot = self.snapshot if snapshot is None else snapshot
        self._members()
        crosswalk_identity = stamp(Path(self.crosswalk["path"]))
        value = read_pin(Path(self.crosswalk["path"]), self.crosswalk["sha256"])
        require(
            set(value)
            == {
                "schema",
                "audience",
                "archive",
                "current",
                "rows",
                "inverse",
                "engineering_neutral_only",
                "professional_acceptance",
                "native_evidence_import",
            }
            and value["schema"] == SCHEMA
            and value["audience"] == "INSTRUCTOR_ONLY"
            and value["professional_acceptance"] == "NOT_ASSERTED"
            and value["native_evidence_import"] == "PROHIBITED",
            "Exact unvalidated reference schema required",
        )
        require(
            value["archive"] == self.selection
            and digest(value["current"]) == digest(current_identity(snapshot)),
            "Crosswalk current snapshot, branch, scope or archive differs",
        )
        rows = value["rows"]
        rebuilt = build_crosswalk(
            self.index,
            snapshot,
            self.selection,
            [{"legacy_id": r["legacy_id"], "relations": r["relations"]} for r in rows],
            engineering_neutral_only=value["engineering_neutral_only"],
        )
        require(
            digest(rebuilt) == digest(value),
            "Crosswalk complete original and inverse inventories differ",
        )
        by_card = {c["id"]: c for c in cards(snapshot)}
        total = 0
        for row in rows:
            entry = next(e for e in self.index["entries"] if e["id"] == row["legacy_id"])
            require(
                isinstance(row["relations"], list) and row["relations"],
                "Explicit relation or unresolved reason required",
            )
            seen = set()
            for relation in row["relations"]:
                require(
                    isinstance(relation, dict)
                    and set(relation) == {"current_id", "status", "reason", "proof"}
                    and relation["status"] in STATUSES
                    and isinstance(relation["reason"], str)
                    and 0 < len(relation["reason"].strip()) <= 1000,
                    "Exact relation, status and bounded reason required",
                )
                card_id, status = relation["current_id"], relation["status"]
                require(
                    card_id not in seen and (card_id is None or card_id in by_card),
                    "Distinct existing current card required",
                )
                seen.add(card_id)
                total += 1
                if status == "UNRESOLVED":
                    require(relation["proof"] is None, "Unknown relation cannot claim proof")
                    continue
                proof = relation["proof"]
                require(
                    isinstance(proof, dict) and set(proof) == {"legacy_pointer", "current_pointer"},
                    "Literal two-sided proof required",
                )
                legacy = read_pin(self.root / entry["source"], entry["raw_sha256"])
                require(
                    digest(legacy) == entry["canonical_sha256"],
                    "Original canonical relation source differs",
                )
                left, right = (
                    pointer(legacy, proof["legacy_pointer"]),
                    pointer(snapshot, proof["current_pointer"]),
                )
                if status == "SHARED_CONTROL_ONLY":
                    require(
                        card_id is not None
                        and proof["legacy_pointer"] == "/binding_contract/applicable_control_ids"
                        and proof["current_pointer"]
                        == f"/authored/issues/{list(by_card).index(card_id)}/control_ids"
                        and isinstance(left, list)
                        and all(isinstance(c, str) for c in left)
                        and set(left) & set(right),
                        "Explicit shared canonical control required",
                    )
                elif status == "EXACT":
                    require(
                        card_id is not None
                        and proof["current_pointer"].startswith(
                            f"/authored/issues/{list(by_card).index(card_id)}/"
                        )
                        and isinstance(left, dict)
                        and set(left) == {"episode_id", "episode_version"}
                        and isinstance(left["episode_id"], str)
                        and left["episode_id"].strip()
                        and type(left["episode_version"]) is int
                        and left["episode_version"] > 0
                        and digest(left) == digest(right),
                        "Exact existing episode/version declaration required",
                    )
                else:
                    require(
                        card_id is None
                        and proof["legacy_pointer"] == "/binding_contract/scope"
                        and proof["current_pointer"] == "/engagement/scope"
                        and outside_period(left, right),
                        "Explicit nonoverlapping period required; unknown scope is unresolved",
                    )
        require(total <= 8000, "Declared crosswalk relation bound exceeded")
        require(
            digest(read_pin(Path(self.crosswalk["path"]), self.crosswalk["sha256"]))
            == digest(value),
            "Crosswalk changed after relation validation",
        )
        self._close_members(crosswalk_identity)
        return {
            "schema": SCHEMA,
            "projection": "DECLARED_NAVIGATION_ONLY",
            "sha256": self.crosswalk["sha256"],
            "engagement_id": snapshot["engagement"]["id"],
            "archive_sha256": self.selection["archive_sha256"],
            "current_cards": value["current"]["cards"],
            "rows": [
                {
                    "legacy_id": r["legacy_id"],
                    **{k: r[k] for k in ("raw_sha256", "canonical_sha256", "key_sha256")},
                    "relations": r["relations"],
                }
                for r in rows
            ],
            "inverse": value["inverse"],
            "professional_acceptance": "NOT_ASSERTED",
        }
