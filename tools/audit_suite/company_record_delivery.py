"""Export and verify a complete, source-only synthetic company history."""

import argparse
import hashlib
import json
import re
import sqlite3
import stat
from collections import Counter
from pathlib import Path, PurePosixPath
from urllib.parse import quote

SCHEMA = "sable-harbor-company-record-delivery-v1"
IDENTITY = ("company", "branch", "system", "record", "version")
LINEAGE = (*IDENTITY, "event_at", "available_at", "imported_at", "origin")
PRIVATE_MARKERS = re.compile(
    rb"/home/|/run/media/|\b(?:CLEAN|MESSY|PRIVATE_TRAINING_TRUTH)\b"
    rb"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    # Character classes avoid matching this detector in the repository's literal scanner.
    rb"|\b(?:[g]hp_|[g]ithub_pat_|[s]k-proj-)[A-Za-z0-9_\-]{16,}"
)
EXTENSIONS = {
    "application/json": ".json",
    "application/octet-stream": ".bin",
    "text/plain; charset=utf-8": ".txt",
}
REDACTION_KEYS = {"source_root", "runtime_root"}


def sha(content):
    return hashlib.sha256(content).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()


def decoded(content):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, "Duplicate JSON key")
            value[key] = item
        return value

    return json.loads(content, object_pairs_hook=unique)


def require(value, message):
    if not value:
        raise ValueError(message)


def safe_public_bytes(content):
    require(not PRIVATE_MARKERS.search(content), "Private marker in public delivery")


def member_path(row, history_id, media_type):
    require(media_type in EXTENSIONS, "Unrecognized source content type")
    return (
        f"{history_id}/{quote(row['system'], safe='')}/"
        f"{quote(row['record'], safe='')}-v{row['version']:04d}{EXTENSIONS[media_type]}"
    )


def transform(content):
    """Change only workstation source-root values; preserve all other source facts."""
    if b"/home/" not in content:
        safe_public_bytes(content)
        return content, []
    body = decoded(content)
    redactions = []

    def visit(value, pointer=""):
        if isinstance(value, dict):
            for key, item in value.items():
                child = pointer + "/" + key.replace("~", "~0").replace("/", "~1")
                if isinstance(item, str) and "/home/" in item:
                    require(
                        key in REDACTION_KEYS and item.startswith("/home/"),
                        "Unreviewed local path requires explicit export policy",
                    )
                    replacement = "local-source:" + sha(item.encode())
                    value[key] = replacement
                    redactions.append({"pointer": child, "replacement": replacement})
                else:
                    visit(item, child)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, pointer + "/" + str(index))

    visit(body)
    require(redactions, "Local path was not replaced")
    result = encoded(body)
    safe_public_bytes(result)
    return result, redactions


def build(database, destination):
    database = Path(database).absolute()
    destination = Path(destination).absolute()
    require(database.is_file() and not database.is_symlink(), "Regular source database required")
    require(not destination.exists(), "Fresh delivery destination required")
    before = sha(database.read_bytes())
    connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("BEGIN")
        require(
            connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
            "Source database integrity check failed",
        )
        for table in ("grants", "access_events", "collections"):
            require(
                connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0,
                "Source-only database required",
            )
        rows = connection.execute(
            "SELECT * FROM versions ORDER BY company,branch,system,record,version"
        ).fetchall()
        systems = [
            dict(row)
            for row in connection.execute(
                "SELECT company,branch,system,owner FROM systems ORDER BY company,branch,system"
            )
        ]
        branches = sorted({row["branch"] for row in rows})
        histories = {branch: f"history-{index:02d}" for index, branch in enumerate(branches, 1)}
        records = []
        pending = []
        provenance_rows = {history: [] for history in histories.values()}
        for row in rows:
            original = bytes(row["content"])
            require(sha(original) == row["sha256"], "Original source content hash mismatch")
            provenance = decoded(row["provenance"])
            require(
                row["provenance"]
                == json.dumps(provenance, sort_keys=True, separators=(",", ":"), allow_nan=False),
                "Noncanonical source provenance requires explicit byte preservation",
            )
            metadata = {key: row[key] for key in IDENTITY}
            metadata.update(
                {
                    "command_id": row["command_id"],
                    "input_digest": row["input_digest"],
                    "provenance": provenance,
                }
            )
            provenance_rows[histories[row["branch"]]].append(metadata)
            media_type = provenance["content_type"]
            content, redactions = transform(original)
            relative = member_path(row, histories[row["branch"]], media_type)
            item = {key: row[key] for key in LINEAGE}
            item.update(
                {
                    "path": relative,
                    "history_id": histories[row["branch"]],
                    "media_type": media_type,
                    "relationship": "derivative" if redactions else "original",
                    "bytes": len(content),
                    "sha256": sha(content),
                    "source_bytes": len(original),
                    "source_sha256": row["sha256"],
                    "source_provenance_sha256": sha(row["provenance"].encode()),
                    "redactions": redactions,
                }
            )
            safe_public_bytes(encoded(item))
            records.append(item)
            pending.append((relative, content))
        provenance_files = []
        for history, metadata_rows in provenance_rows.items():
            relative = f"{history}/provenance.jsonl"
            metadata_bytes = b"".join(
                (
                    json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
                ).encode()
                for row in metadata_rows
            )
            safe_public_bytes(metadata_bytes)
            pending.append((relative, metadata_bytes))
            provenance_files.append(
                {
                    "path": relative,
                    "history_id": history,
                    "bytes": len(metadata_bytes),
                    "sha256": sha(metadata_bytes),
                    "version_count": len(metadata_rows),
                }
            )
        manifest = {
            "schema": SCHEMA,
            "snapshot": {
                "source_database_sha256": before,
                "source_database_bytes": database.stat().st_size,
                "source_version_count": len(rows),
                "source_system_count": len(systems),
                "source_only_tables": ["systems", "versions"],
                "omitted_metadata": [],
                "provenance_digest_basis": (
                    "SHA-256 of the exact UTF-8 provenance JSON stored in the source database"
                ),
                "redaction_policy": (
                    "Only absolute workstation source_root/runtime_root values are replaced "
                    "with consistent local-source:SHA256(value) locators. All source facts, "
                    "identities, versions and clocks are retained."
                ),
            },
            "histories": [
                {
                    "id": histories[branch],
                    "source_branch": branch,
                    "version_count": sum(row["branch"] == branch for row in rows),
                }
                for branch in branches
            ],
            "systems": systems,
            "provenance_files": provenance_files,
            "records": records,
        }
        safe_public_bytes(encoded(manifest))
        require(sha(database.read_bytes()) == before, "Source database changed during export")
        destination.mkdir(parents=True)
        for relative, content in pending:
            path = destination / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        (destination / "manifest.json").write_bytes(encoded(manifest))
    finally:
        connection.close()
    return verify(destination)


def verify(root):
    root = Path(root).absolute()
    require(root.is_dir() and not root.is_symlink(), "Regular delivery directory required")
    manifest_path = root / "manifest.json"
    require(
        manifest_path.is_file()
        and not manifest_path.is_symlink()
        and manifest_path.stat().st_nlink == 1,
        "Regular unaliased manifest required",
    )
    manifest_bytes = manifest_path.read_bytes()
    safe_public_bytes(manifest_bytes)
    manifest = decoded(manifest_bytes)
    require(manifest.get("schema") == SCHEMA, "Unsupported delivery schema")
    require(
        set(manifest)
        == {"schema", "snapshot", "histories", "systems", "records", "provenance_files"},
        "Unexpected manifest fields",
    )
    records = manifest["records"]
    snapshot = manifest["snapshot"]
    require(isinstance(records, list) and records, "Nonempty record population required")
    require(len(records) == snapshot["source_version_count"], "Source version count differs")
    require(
        len(manifest["systems"]) == snapshot["source_system_count"], "Source system count differs"
    )
    histories = {row["source_branch"]: row["id"] for row in manifest["histories"]}
    require(len(histories) == len(manifest["histories"]), "Duplicate history")
    require(len(set(histories.values())) == len(histories), "Duplicate history identifier")
    require(
        set(histories.values()) == {f"history-{i:02d}" for i in range(1, len(histories) + 1)},
        "Unexpected history identifiers",
    )
    system_keys = {(row["company"], row["branch"], row["system"]) for row in manifest["systems"]}
    require(len(system_keys) == len(manifest["systems"]), "Duplicate source system")
    expected = {"manifest.json"}
    source_metadata = {}
    commands = set()
    require(len(manifest["provenance_files"]) == len(histories), "Provenance file count differs")
    for item in manifest["provenance_files"]:
        relative = item["path"]
        require(
            item["history_id"] in histories.values()
            and relative == item["history_id"] + "/provenance.jsonl",
            "Unexpected provenance path",
        )
        require(relative not in expected, "Duplicate provenance member")
        expected.add(relative)
        path = root / relative
        require(
            path.is_file() and not path.is_symlink() and path.stat().st_nlink == 1,
            "Regular unaliased provenance required",
        )
        content = path.read_bytes()
        safe_public_bytes(content)
        require(
            len(content) == item["bytes"] and sha(content) == item["sha256"],
            "Provenance file hash or bytes differ",
        )
        metadata_rows = [decoded(line) for line in content.splitlines()]
        require(len(metadata_rows) == item["version_count"], "Provenance population differs")
        for metadata in metadata_rows:
            require(
                set(metadata) == set(IDENTITY) | {"command_id", "input_digest", "provenance"},
                "Unexpected source metadata fields",
            )
            identity = tuple(metadata[key] for key in IDENTITY)
            require(identity not in source_metadata, "Duplicate provenance identity")
            require(
                histories.get(metadata["branch"]) == item["history_id"],
                "Provenance history differs",
            )
            require(isinstance(metadata["provenance"], dict), "Object provenance required")
            require(metadata["command_id"] not in commands, "Duplicate source command")
            commands.add(metadata["command_id"])
            require(
                re.fullmatch(r"[a-f0-9]{64}", metadata["input_digest"]),
                "Invalid source input digest",
            )
            source_metadata[identity] = metadata
    identities = set()
    counts = Counter()
    branches = Counter()
    for row in records:
        identity = tuple(row[key] for key in IDENTITY)
        require(identity not in identities, "Duplicate source version")
        identities.add(identity)
        require(identity in source_metadata, "Missing source provenance")
        provenance = source_metadata[identity]["provenance"]
        canonical = json.dumps(
            provenance, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
        require(
            sha(canonical) == row["source_provenance_sha256"], "Source provenance digest differs"
        )
        require(provenance.get("content_type") == row["media_type"], "Source media type differs")
        require(identity[:3] in system_keys, "Unregistered source system")
        require(type(row["version"]) is int and row["version"] > 0, "Positive version required")
        require(
            row["branch"] in histories and row["history_id"] == histories[row["branch"]],
            "Source history differs",
        )
        relative = row["path"]
        require(
            relative == member_path(row, row["history_id"], row["media_type"]),
            "Noncanonical member path",
        )
        parts = PurePosixPath(relative).parts
        require(
            not PurePosixPath(relative).is_absolute()
            and ".." not in parts
            and "\\" not in relative,
            "Unsafe member path",
        )
        require(relative not in expected, "Duplicate member path")
        expected.add(relative)
        path = root / relative
        require(
            all(not p.is_symlink() for p in [path, *path.parents] if p.is_relative_to(root)),
            "Member aliases forbidden",
        )
        require(path.is_file() and path.stat().st_nlink == 1, "Missing or aliased source member")
        content = path.read_bytes()
        safe_public_bytes(content)
        require(
            type(row["bytes"]) is int
            and len(content) == row["bytes"]
            and sha(content) == row["sha256"],
            "Member hash or byte count differs",
        )
        for key in ("sha256", "source_sha256", "source_provenance_sha256"):
            require(
                isinstance(row[key], str) and re.fullmatch(r"[a-f0-9]{64}", row[key]),
                "Invalid digest",
            )
        relationship = row["relationship"]
        require(relationship in {"original", "derivative"}, "Unsupported relationship")
        if relationship == "original":
            require(
                not row["redactions"]
                and row["bytes"] == row["source_bytes"]
                and row["sha256"] == row["source_sha256"],
                "Original relationship differs",
            )
        else:
            require(
                row["redactions"] and row["sha256"] != row["source_sha256"],
                "Derivative relationship differs",
            )
            body = decoded(content)
            for redaction in row["redactions"]:
                require(set(redaction) == {"pointer", "replacement"}, "Unexpected redaction fields")
                keys = redaction["pointer"].lstrip("/").split("/")
                require(keys[-1] in REDACTION_KEYS, "Unapproved redaction key")
                value = body
                for key in keys:
                    key = key.replace("~1", "/").replace("~0", "~")
                    value = value[int(key)] if isinstance(value, list) else value[key]
                require(
                    re.fullmatch(r"local-source:[a-f0-9]{64}", redaction["replacement"])
                    and value == redaction["replacement"],
                    "Redaction placeholder differs",
                )
        counts[relationship] += 1
        branches[row["branch"]] += 1
    require(set(source_metadata) == identities, "Source provenance identity population differs")
    for history in manifest["histories"]:
        require(
            branches[history["source_branch"]] == history["version_count"], "History count differs"
        )
    actual = set()
    for path in root.rglob("*"):
        require(not path.is_symlink(), "Delivery aliases forbidden")
        require(
            stat.S_ISREG(path.stat().st_mode) or path.is_dir(), "Special delivery member forbidden"
        )
        if path.is_file():
            require(path.stat().st_nlink == 1, "Hardlinked delivery member forbidden")
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    # The human guide is deliberately separate from the immutable source manifest.
    require(actual - {"README.md"} == expected, "Delivery membership differs")
    return {
        "verified_source_versions": len(records),
        "verified_source_systems": len(system_keys),
        "histories": len(histories),
        "originals": counts["original"],
        "derivatives": counts["derivative"],
        "source_content_bytes": sum(row["source_bytes"] for row in records),
        "published_content_bytes": sum(row["bytes"] for row in records),
        "manifest_sha256": sha(manifest_bytes),
        "source_database_sha256": snapshot["source_database_sha256"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    export = subparsers.add_parser("build")
    export.add_argument("--database", type=Path, required=True)
    export.add_argument("--destination", type=Path, required=True)
    check = subparsers.add_parser("verify")
    check.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    result = (
        build(args.database, args.destination) if args.command == "build" else verify(args.root)
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
