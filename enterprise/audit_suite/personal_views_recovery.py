"""Typed application-owned personal-view snapshots and explicit ownership receipts."""

import re
from datetime import UTC, datetime

from .inference import _json as strict_json
from .personal_views import (
    FIELDS,
    REFERENCE_SECTIONS,
    SECTIONS,
    PersonalViews,
    _integer,
    _text,
    require,
)
from .personal_views import TABLES as VIEW_TABLES
from .store import canonical, digest

TABLES = {
    "views": ("id", "actor", "engagement", "version", "status", "content", "sha256"),
    "history": ("view_id", "version", "content", "sha256"),
    "commands": ("actor", "engagement", "command_id", "digest", "view_id", "version"),
    "ownership_history": ("view_id", "version", "content", "sha256"),
}
CONTENT = {
    "id",
    "actor_id",
    "engagement_id",
    "version",
    "status",
    "user",
    "saved_at",
    "engagement_revision",
    "context_basis_sha256",
}
MAPPING = {
    "view_id",
    "engagement_id",
    "from_actor",
    "to_actor",
    "version",
    "previous_sha256",
    "source_manifest_sha256",
    "restored_at",
    "history_version",
}


def hash_value(value):
    require(
        isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value),
        "Exact recovery hash required",
    )


def user_shape(user):
    require(
        isinstance(user, dict) and set(user) == FIELDS, "Exact saved navigation schema required"
    )
    _text(user["title"], 120, nonempty=True)
    _text(user["query"], 1000)
    _text(user["framework"], 256, nonempty=True)
    require(
        isinstance(user["section"], str) and user["section"] in SECTIONS, "Invalid saved section"
    )
    _integer(user["scroll_top"], 1000000)
    table = user["table"]
    if table is not None:
        require(
            isinstance(table, dict) and set(table) == {"id", "query", "sort", "page"},
            "Invalid saved table",
        )
        require(
            isinstance(table["id"], str)
            and table["id"] in VIEW_TABLES
            and VIEW_TABLES[table["id"]][0] == user["section"],
            "Saved table scope differs",
        )
        _text(table["query"], 1000)
        _integer(table["page"], 10000)
        require(
            isinstance(table["sort"], str)
            and table["sort"] in ["", *VIEW_TABLES[table["id"]][1].split()],
            "Invalid saved sort",
        )
    ref = user["reference"]
    if ref is not None:
        require(
            isinstance(ref, dict) and set(ref) == {"kind", "id", "version", "sha256"},
            "Exact saved reference required",
        )
        require(
            isinstance(ref["kind"], str)
            and ref["kind"] in REFERENCE_SECTIONS
            and REFERENCE_SECTIONS[ref["kind"]] == user["section"],
            "Invalid saved reference kind",
        )
        _text(ref["id"], 256, nonempty=True)
        hash_value(ref["sha256"])
        require(
            ref["version"] is None or type(ref["version"]) is int and ref["version"] > 0,
            "Exact saved reference version required",
        )
        if ref["kind"] == "workpaper":
            require(
                type(ref["version"]) is int and ref["version"] > 0,
                "Exact workpaper version required",
            )


def owner_chain(rows, view_id, original_actor, engagement):
    previous = ""
    boundary = 0
    actor = original_actor
    for index, row in enumerate(sorted(rows, key=lambda r: r["version"]), 1):
        require(
            type(row["version"]) is int and row["version"] == index and row["view_id"] == view_id,
            "Ownership receipt order differs",
        )
        body = strict_json(row["content"])
        require(
            isinstance(body, dict) and set(body) == MAPPING and digest(body) == row["sha256"],
            "Ownership receipt integrity failure",
        )
        require(
            body["view_id"] == view_id
            and body["engagement_id"] == engagement
            and body["from_actor"] == actor
            and body["previous_sha256"] == previous
            and type(body["version"]) is int
            and body["version"] == index,
            "Ownership chain differs",
        )
        require(
            type(body["history_version"]) is int and body["history_version"] >= 1,
            "Exact ownership history boundary required",
        )
        require(body["history_version"] >= boundary, "Ownership history boundary moved backwards")
        boundary = body["history_version"]
        _text(body["to_actor"], 256, nonempty=True)
        hash_value(body["source_manifest_sha256"])
        require(
            datetime.fromisoformat(body["restored_at"]).tzinfo is not None,
            "Dated ownership receipt required",
        )
        actor = body["to_actor"]
        previous = row["sha256"]
    return actor


def validate(tables):
    require(
        isinstance(tables, dict) and set(tables) == set(TABLES),
        "Exact saved-view recovery tables required",
    )
    for name, columns in TABLES.items():
        require(
            isinstance(tables[name], list)
            and len(tables[name]) <= 200000
            and all(isinstance(r, dict) and set(r) == set(columns) for r in tables[name]),
            "Typed saved-view table required",
        )
    for rows in tables.values():
        for row in rows:
            for key, value in row.items():
                if key != "version":
                    _text(value, 16384 if key == "content" else 256, nonempty=True)
    require(
        sum(len(row["content"].encode("utf-8")) for row in tables["history"]) <= 64 * 1024 * 1024,
        "Saved-view history byte quota exceeded",
    )
    history = {}
    for row in tables["history"]:
        _text(row["view_id"], 256, nonempty=True)
        require(
            type(row["version"]) is int and 1 <= row["version"] <= 201,
            "Exact history version required",
        )
        _text(row["content"], 16384, nonempty=True)
        require(
            len(row["content"].encode("utf-8")) <= 16384, "Saved-view version byte quota exceeded"
        )
        hash_value(row["sha256"])
        body = strict_json(row["content"])
        key = (row["view_id"], row["version"])
        require(
            isinstance(body, dict)
            and set(body) == CONTENT
            and key not in history
            and digest(body) == row["sha256"]
            and body["id"] == key[0]
            and type(body["version"]) is int
            and body["version"] == key[1],
            "Saved-view history integrity failure",
        )
        for k in ("actor_id", "engagement_id"):
            _text(body[k], 256, nonempty=True)
        _integer(body["engagement_revision"], 1000000000)
        hash_value(body["context_basis_sha256"])
        require(
            datetime.fromisoformat(body["saved_at"]).tzinfo is not None, "Dated saved view required"
        )
        require(body["status"] in ("ACTIVE", "CLEARED"), "Invalid saved-view status")
        if body["status"] == "ACTIVE":
            require(row["version"] <= 200, "Active view edit quota exceeded")
            user_shape(body["user"])
        else:
            require(body["user"] is None, "Cleared view contains personal text")
        history[key] = (row, body)
    heads = {}
    mappings = {}
    for row in tables["ownership_history"]:
        require(
            type(row["version"]) is int and row["version"] > 0, "Exact ownership version required"
        )
        mappings.setdefault(row["view_id"], []).append(row)
    for row in tables["views"]:
        require(
            type(row["version"]) is int and 1 <= row["version"] <= 201 and row["id"] not in heads,
            "Invalid saved-view head",
        )
        entry = history.get((row["id"], row["version"]))
        require(
            entry is not None
            and entry[0]["content"] == row["content"]
            and entry[0]["sha256"] == row["sha256"]
            and entry[1]["status"] == row["status"],
            "Saved-view head integrity failure",
        )
        versions = sorted(v for i, v in history if i == row["id"])
        require(
            versions == list(range(1, row["version"] + 1)),
            "Orphan or incomplete saved-view history",
        )
        first = history[row["id"], 1][1]
        owner = owner_chain(
            mappings.get(row["id"], []), row["id"], first["actor_id"], first["engagement_id"]
        )
        require(
            row["actor"] == owner and row["engagement"] == first["engagement_id"],
            "Saved-view owner mismatch",
        )
        previous_cleared = False
        for v in versions:
            b = history[row["id"], v][1]
            expected_actor = first["actor_id"]
            for mapping in sorted(mappings.get(row["id"], []), key=lambda m: m["version"]):
                body = strict_json(mapping["content"])
                require(
                    body["history_version"] <= row["version"], "Ownership boundary exceeds history"
                )
                if v > body["history_version"]:
                    expected_actor = body["to_actor"]
            require(
                b["actor_id"] == expected_actor
                and b["engagement_id"] == row["engagement"]
                and not previous_cleared,
                "Saved-view historical owner/status mismatch",
            )
            previous_cleared = b["status"] == "CLEARED"
        heads[row["id"]] = row
    require(
        all(i in heads for i, _ in history) and set(mappings) <= set(heads),
        "Orphan saved-view history or ownership",
    )
    seen = set()
    versions = set()
    for row in tables["commands"]:
        require(
            type(row["version"]) is int and row["version"] > 0, "Exact command version required"
        )
        _text(row["command_id"], 128, nonempty=True)
        hash_value(row["digest"])
        key = (row["actor"], row["engagement"], row["command_id"])
        version = (row["view_id"], row["version"])
        head = heads.get(row["view_id"])
        require(
            key not in seen
            and version not in versions
            and version in history
            and head is not None
            and (row["actor"], row["engagement"]) == (head["actor"], head["engagement"]),
            "Orphan or foreign saved-view command",
        )
        seen.add(key)
        versions.add(version)
    require(versions == set(history), "Saved-view history lacks exact command receipts")


def restore_tables(destination, engine, tables, principal_map, manifest_sha256):
    validate(tables)
    restored = PersonalViews(destination, engine)
    authority = []
    for row in tables["views"]:
        actor = principal_map[row["actor"]]
        state, basis = restored._state(actor, row["engagement"])
        authority.append((actor, row["engagement"], basis))
    with restored._db() as db:
        for name, columns in TABLES.items():
            for original in tables[name]:
                row = dict(original)
                if "actor" in row:
                    row["actor"] = principal_map[row["actor"]]
                db.execute(
                    f"INSERT INTO {name} VALUES({','.join('?' for _ in columns)})",
                    tuple(row[k] for k in columns),
                )
        for row in tables["views"]:
            prior = [r for r in tables["ownership_history"] if r["view_id"] == row["id"]]
            previous = max(prior, key=lambda r: r["version"]) if prior else None
            version = 1 + (previous["version"] if previous else 0)
            receipt = {
                "view_id": row["id"],
                "engagement_id": row["engagement"],
                "from_actor": row["actor"],
                "to_actor": principal_map[row["actor"]],
                "version": version,
                "previous_sha256": previous["sha256"] if previous else "",
                "source_manifest_sha256": manifest_sha256,
                "restored_at": datetime.now(UTC).isoformat(),
                "history_version": row["version"],
            }
            db.execute(
                "INSERT INTO ownership_history VALUES(?,?,?,?)",
                (row["id"], version, canonical(receipt), digest(receipt)),
            )
        snapshot = {name: [dict(r) for r in db.execute(f"SELECT * FROM {name}")] for name in TABLES}
        validate(snapshot)
    return restored, authority
