"""Private instructor packet with a complete, streamed single-engagement journal.

This local filesystem contract is separate from bounded in-app ZIP exports.
It copies no identity/session tables, other engagements or instructor Key files.
It neither adds an audit event nor imports a packet as company evidence.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sqlite3
import stat
import uuid
from contextlib import closing
from pathlib import Path

from .history_inspection import _update_object
from .persistent_company_journey import write
from .private_publication import publish
from .source_library_audit import private_file
from .store import DomainError, canonical, digest

SCHEMA = "SH_PRIVATE_COMPLETE_AUDIT_REVIEW_PACKET_V1"
EVENT_COLUMNS = (
    "revision",
    "actor",
    "recorded_at",
    "previous_hash",
    "state",
    "command",
    "command_id",
    "hash",
    "request_hash",
)
HISTORY_SQL = (
    "CREATE TABLE history_events (revision INTEGER PRIMARY KEY, actor TEXT NOT NULL, "
    "recorded_at INTEGER NOT NULL, previous_hash TEXT NOT NULL, state TEXT NOT NULL, "
    "command TEXT NOT NULL, command_id TEXT NOT NULL, hash TEXT NOT NULL, "
    "request_hash TEXT NOT NULL)"
)
STATE_SQL = "CREATE TABLE selected_state (id TEXT PRIMARY KEY, state TEXT NOT NULL)"
SCHEMA_OBJECTS = {
    ("table", "history_events", "history_events", HISTORY_SQL),
    ("table", "selected_state", "selected_state", STATE_SQL),
    ("index", "sqlite_autoindex_selected_state_1", "selected_state", None),
}


def file_digest(path):
    private_file(path)
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def _parent(output, source_root):
    path = Path(output).absolute()
    if (
        any(p.is_symlink() for p in [path, *path.parents])
        or not path.parent.is_dir()
        or stat.S_IMODE(path.parent.stat().st_mode) != 0o700
        or path.exists()
        or path.is_relative_to(Path(source_root).absolute())
    ):
        raise DomainError("New private packet outside the audit root required")
    return path


def _record(row):
    return {
        "actor": row["actor"],
        "recorded_at": row["recorded_at"],
        "previous_hash": row["previous_hash"],
        "state": json.loads(row["state"]),
        "command": json.loads(row["command"]),
        "command_id": row["command_id"],
    }


def _artifacts(state, engagement_id):
    included, withheld = [], []
    seen = set()
    for item in state["artifacts"]:
        if (
            item.get("engagement_id") != engagement_id
            or not isinstance(item.get("id"), str)
            or not item["id"]
            or item["id"] in seen
        ):
            raise DomainError("Unique selected-engagement artifact identity required")
        seen.add(item["id"])
        reason = (
            "Unavailable or quarantined original"
            if item.get("status") != "AVAILABLE"
            else "Prior export is indexed without recursive embedding"
            if item.get("source", {}).get("kind")
            in {"PRIVATE_REVIEW_EXPORT", "HUMAN_REVIEW_EXPORT", "INSTRUCTOR_DEBRIEF_EXPORT"}
            else None
        )
        if reason:
            withheld.append({"artifact_id": item["id"], "reason": reason})
            continue
        if (
            not isinstance(item.get("sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
            or type(item.get("bytes")) is not int
            or item["bytes"] < 0
            or not isinstance(item.get("name"), str)
            or not item["name"]
        ):
            raise DomainError("Exact retained artifact digest, byte length and name required")
        included.append({key: item[key] for key in ("id", "name", "sha256", "bytes")})
    return included, withheld


def _index(state, included, withheld):
    tasks = "".join(
        "<tr><td>"
        + html.escape(str(t["id"]))
        + "</td><td>"
        + html.escape(str(t.get("status", "")))
        + "</td><td>"
        + html.escape(str(t.get("conclusion", "")))
        + "</td></tr>"
        for t in state.get("tasks", [])
    )
    files = "".join(
        "<li><a href='files/"
        + item["sha256"]
        + "'>"
        + html.escape(item["name"])
        + "</a> · "
        + html.escape(item["id"])
        + "</li>"
        for item in included
    )
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta http-equiv='Content-Security-Policy' "
        "content=\"default-src 'none'; base-uri 'none'; form-action 'none'\">"
        "<title>Private audit review packet</title></head><body>"
        "<h1>" + html.escape(state["title"]) + "</h1>"
        "<p>Private instructor review · engagement "
        + html.escape(state["id"])
        + " · revision "
        + str(state["revision"])
        + ".</p>"
        "<p>Selected fictional training work; no overall grade, issued opinion or "
        "professional acceptance. Later work is outside this snapshot.</p>"
        "<p><a href='manifest.json'>Exact file manifest</a> · "
        "<a href='engagement.json'>Complete selected state</a> · "
        "<a href='history.sqlite3'>Complete immutable event journal</a></p>"
        "<p>The journal contains every event through this revision. It is a "
        "SQLite database, not an abbreviated history.json. Identity/session tables, "
        "other engagements and instructor Key files are excluded. Retained originals "
        "remain distinct from recorded auditor conclusions.</p>"
        "<h2>Recorded task dispositions</h2><table><thead><tr><th>Task</th>"
        "<th>Status</th><th>Conclusion</th></tr></thead><tbody>"
        + tasks
        + "</tbody></table><h2>Retained originals</h2><ul>"
        + files
        + "</ul><p>Unavailable or recursive export artifacts: "
        + str(len(withheld))
        + ". Exact omissions are indexed in manifest.json.</p></body></html>"
    ).encode()


def export_packet(engine, actor, engagement_id, output):
    """Publish a new private directory only after exact history and source verification."""
    if engine.store.membership(actor, engagement_id) != "instruct":
        raise DomainError("Instructor membership required for complete private history", status=403)
    output = _parent(output, engine.store.root)
    stage = output.parent / ("." + output.name + "-staging-" + uuid.uuid4().hex)
    stage.mkdir(mode=0o700)
    (stage / "files").mkdir(mode=0o700)
    journal = stage / "history.sqlite3"
    fd = os.open(journal, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    rolling, previous, count, last = hashlib.sha256(b"["), "", 0, None
    # One consistent source transaction. Only explicit event fields are copied;
    # the live Store database is never backed up into a distributable packet.
    with closing(engine.store.connect()) as source, closing(sqlite3.connect(journal)) as target:
        source.execute("BEGIN")
        engine.store._authorize(source, actor, engagement_id, {"instruct"})
        current = source.execute(
            "SELECT revision,state FROM engagements WHERE id=?", (engagement_id,)
        ).fetchone()
        state = json.loads(current["state"])
        target.execute(HISTORY_SQL)
        target.execute(STATE_SQL)
        for row in source.execute(
            "SELECT * FROM events WHERE engagement=? ORDER BY revision", (engagement_id,)
        ):
            record = _record(row)
            fields = {name: canonical(value).encode() for name, value in record.items()}
            event_hash = hashlib.sha256()
            _update_object(event_hash, fields)
            if (
                row["revision"] != count
                or previous != row["previous_hash"]
                or event_hash.hexdigest() != row["hash"]
                or hashlib.sha256(fields["command"]).hexdigest() != row["request_hash"]
            ):
                raise DomainError("History integrity failure", code="INTEGRITY", status=500)
            if count:
                rolling.update(b",")
            _update_object(
                rolling,
                {
                    **fields,
                    "hash": canonical(row["hash"]).encode(),
                    "revision": canonical(count).encode(),
                },
            )
            target.execute(
                "INSERT INTO history_events VALUES (?,?,?,?,?,?,?,?,?)",
                tuple(row[column] for column in EVENT_COLUMNS),
            )
            previous, last = row["hash"], record["state"]
            count += 1
        if (
            count != current["revision"] + 1
            or last != state
            or state["id"] != engagement_id
            or state["revision"] != current["revision"]
        ):
            raise DomainError(
                "Complete history/current state mismatch", code="INTEGRITY", status=500
            )
        target.execute("INSERT INTO selected_state VALUES (?,?)", (engagement_id, current["state"]))
        target.commit()
    rolling.update(b"]")
    private_file(journal)
    if any(Path(str(journal) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
        raise DomainError("Complete packet journal is not quiescent")
    write(stage / "engagement.json", canonical(state).encode())
    included, withheld = _artifacts(state, engagement_id)
    copied = set()
    originals = {item["id"]: item for item in state["artifacts"]}
    for entry in included:
        item = originals[entry["id"]]
        pin = item["sha256"]
        # Read through the normal hash/size-verified immutable artifact API.
        raw = engine.artifacts.read(item)
        if pin not in copied:
            write(stage / "files" / pin, raw)
            copied.add(pin)
    write(stage / "index.html", _index(state, included, withheld))
    files = {"history.sqlite3": file_digest(journal)}
    files.update({name: file_digest(stage / name) for name in ("engagement.json", "index.html")})
    files.update({"files/" + pin: file_digest(stage / "files" / pin) for pin in sorted(copied)})
    manifest = {
        "schema": SCHEMA,
        "audience": "INSTRUCTOR_ONLY",
        "engagement_id": engagement_id,
        "revision": state["revision"],
        "state_sha256": digest(state),
        "history_events": count,
        "history_sha256": rolling.hexdigest(),
        "history_terminal_event_sha256": previous,
        "history_format": "COMPLETE_SQLITE_JOURNAL_V1",
        "files": files,
        "included_artifacts": included,
        "omitted_artifacts": withheld,
        "identity_session_tables_copied": False,
        "instructor_key_files_copied": False,
        "source_company_write": False,
        "audit_event_write": False,
        "professional_acceptance": "NOT_ASSERTED",
        "overall_grade": "NOT_PROVIDED",
    }
    # Recheck current authority and selected revision after every potentially
    # expensive read. Failed staging remains private and has no final manifest.
    with closing(engine.store.connect()) as source:
        source.execute("BEGIN IMMEDIATE")
        engine.store._authorize(source, actor, engagement_id, {"instruct"})
        fresh = source.execute(
            "SELECT revision,state FROM engagements WHERE id=?", (engagement_id,)
        ).fetchone()
        if fresh["revision"] != current["revision"] or fresh["state"] != current["state"]:
            raise DomainError("Audit changed during export; retry a new packet", status=409)
        write(stage / "manifest.json", manifest)
        manifest_pin = file_digest(stage / "manifest.json")
        if output.exists() or any(p.is_symlink() for p in [output, *output.parents]):
            raise DomainError("Packet destination changed during export")
        # Exclusive reservation preserves even a destination created after the
        # initial check. Publication durably syncs all files and directories.
        publish(stage, output)
    return {"path": str(output), "manifest_sha256": manifest_pin, **manifest}


def verify_packet(path, expected_manifest_sha256):
    """Read a closed private packet using a separately retained manifest digest.

    Replaying complete states proves journal integrity, not operating sufficiency
    or the truth of an auditor's recorded conclusions. No Store is opened.
    """
    root = Path(path).absolute()
    if (
        any(p.is_symlink() for p in [root, *root.parents])
        or not root.is_dir()
        or stat.S_IMODE(root.stat().st_mode) != 0o700
        or not re.fullmatch(r"[0-9a-f]{64}", expected_manifest_sha256)
        or file_digest(root / "manifest.json") != expected_manifest_sha256
    ):
        raise DomainError("Pinned private packet manifest required")
    manifest = json.loads((root / "manifest.json").read_bytes())
    expected_keys = {
        "schema",
        "audience",
        "engagement_id",
        "revision",
        "state_sha256",
        "history_events",
        "history_sha256",
        "history_terminal_event_sha256",
        "history_format",
        "files",
        "included_artifacts",
        "omitted_artifacts",
        "identity_session_tables_copied",
        "instructor_key_files_copied",
        "source_company_write",
        "audit_event_write",
        "professional_acceptance",
        "overall_grade",
    }
    if (
        set(manifest) != expected_keys
        or manifest["schema"] != SCHEMA
        or manifest["audience"] != "INSTRUCTOR_ONLY"
        or type(manifest["revision"]) is not int
        or manifest["revision"] < 0
        or type(manifest["history_events"]) is not int
        or manifest["history_events"] != manifest["revision"] + 1
        or manifest["history_format"] != "COMPLETE_SQLITE_JOURNAL_V1"
        or any(
            manifest[key] is not False
            for key in (
                "identity_session_tables_copied",
                "instructor_key_files_copied",
                "source_company_write",
                "audit_event_write",
            )
        )
        or manifest["professional_acceptance"] != "NOT_ASSERTED"
        or manifest["overall_grade"] != "NOT_PROVIDED"
    ):
        raise DomainError("Exact complete-packet manifest schema required")
    if not isinstance(manifest["files"], dict) or any(
        not isinstance(name, str)
        or not (
            name in {"engagement.json", "history.sqlite3", "index.html"}
            or re.fullmatch(r"files/[0-9a-f]{64}", name)
        )
        or not isinstance(pin, str)
        or not re.fullmatch(r"[0-9a-f]{64}", pin)
        for name, pin in manifest["files"].items()
    ):
        raise DomainError("Exact packet member names and digests required")
    for name, pin in manifest["files"].items():
        if file_digest(root / name) != pin:
            raise DomainError("Packet file digest disagreement")
    state = json.loads((root / "engagement.json").read_bytes())
    included, withheld = _artifacts(state, manifest["engagement_id"])
    names = {"engagement.json", "history.sqlite3", "index.html"}
    names.update("files/" + item["sha256"] for item in included)
    if (
        set(manifest["files"]) != names
        or included != manifest["included_artifacts"]
        or withheld != manifest["omitted_artifacts"]
        or state["id"] != manifest["engagement_id"]
        or state["revision"] != manifest["revision"]
        or digest(state) != manifest["state_sha256"]
        or (root / "index.html").read_bytes() != _index(state, included, withheld)
    ):
        raise DomainError("Complete state, artifact and offline index membership required")
    members = set()
    for folder, directories, files in os.walk(root, followlinks=False):
        directory = Path(folder)
        if stat.S_IMODE(directory.stat().st_mode) != 0o700:
            raise DomainError("Private packet directory required")
        for name in directories:
            if (directory / name).is_symlink() or (directory / name) != root / "files":
                raise DomainError("Unmanifested packet directory rejected")
        for name in files:
            p = directory / name
            private_file(p)
            members.add(p.relative_to(root).as_posix())
    if members != names | {"manifest.json"}:
        raise DomainError("Exact packet file membership required")
    for name in names:
        if file_digest(root / name) != manifest["files"][name]:
            raise DomainError("Packet file digest disagreement")
    for item in included:
        if (root / "files" / item["sha256"]).stat().st_size != item["bytes"]:
            raise DomainError("Retained original byte length disagreement")
    rolling, previous, count, latest = hashlib.sha256(b"["), "", 0, None
    uri = (root / "history.sqlite3").as_uri() + "?mode=ro&immutable=1"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        db.row_factory = sqlite3.Row
        objects = list(db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master"))
        if (
            {tuple(r) for r in objects} != SCHEMA_OBJECTS
            or tuple(r["name"] for r in db.execute("PRAGMA table_info(history_events)"))
            != EVENT_COLUMNS
            or tuple(r["name"] for r in db.execute("PRAGMA table_info(selected_state)"))
            != ("id", "state")
            or db.execute("PRAGMA quick_check").fetchone()[0] != "ok"
            or db.execute("PRAGMA freelist_count").fetchone()[0] != 0
            or db.execute("PRAGMA application_id").fetchone()[0] != 0
            or db.execute("PRAGMA user_version").fetchone()[0] != 0
            or (root / "history.sqlite3").stat().st_size
            != db.execute("PRAGMA page_count").fetchone()[0]
            * db.execute("PRAGMA page_size").fetchone()[0]
        ):
            raise DomainError("Exclusive complete packet journal schema required")
        selected = list(db.execute("SELECT id,state FROM selected_state"))
        if (
            len(selected) != 1
            or selected[0]["id"] != state["id"]
            or json.loads(selected[0]["state"]) != state
        ):
            raise DomainError("Exact selected packet state required")
        for row in db.execute("SELECT * FROM history_events ORDER BY revision"):
            record = _record(row)
            fields = {name: canonical(value).encode() for name, value in record.items()}
            event_hash = hashlib.sha256()
            _update_object(event_hash, fields)
            if (
                type(row["revision"]) is not int
                or row["revision"] != count
                or row["previous_hash"] != previous
                or event_hash.hexdigest() != row["hash"]
                or hashlib.sha256(fields["command"]).hexdigest() != row["request_hash"]
                or record["state"].get("id") != state["id"]
                or record["state"].get("revision") != count
            ):
                raise DomainError("Complete packet history integrity failure")
            if count:
                rolling.update(b",")
            _update_object(
                rolling,
                {
                    **fields,
                    "hash": canonical(row["hash"]).encode(),
                    "revision": canonical(count).encode(),
                },
            )
            count, previous, latest = count + 1, row["hash"], record["state"]
    rolling.update(b"]")
    if (
        count != manifest["history_events"]
        or latest != state
        or previous != manifest["history_terminal_event_sha256"]
        or rolling.hexdigest() != manifest["history_sha256"]
    ):
        raise DomainError("Complete packet history boundary disagreement")
    if file_digest(root / "manifest.json") != expected_manifest_sha256:
        raise DomainError("Packet manifest changed during verification")
    for name, pin in manifest["files"].items():
        if file_digest(root / name) != pin:
            raise DomainError("Packet member changed during verification")
    return {
        "verified": True,
        "engagement_id": state["id"],
        "revision": state["revision"],
        "history_events": count,
        "manifest_sha256": expected_manifest_sha256,
        "source_company_write": False,
        "audit_event_write": False,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Verify a complete private audit review packet")
    parser.add_argument("packet", type=Path)
    parser.add_argument("manifest_sha256", help="Digest retained separately when exporting")
    arguments = parser.parse_args()
    print(canonical(verify_packet(arguments.packet, arguments.manifest_sha256)))
