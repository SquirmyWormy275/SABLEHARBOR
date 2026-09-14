"""Private-only instructor explanation migration. No learner projection or company-store adapter.

This structural index preserves authored claims; it neither infers causal proof nor grades.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import stat
import zipfile
from collections import Counter
from pathlib import Path

from .corpus import obligations, validate_variant
from .store import DomainError, digest


def migrate_definition(raw: bytes) -> dict:
    """Return a protected explanation pinned to original bytes and canonical content."""
    try:
        source = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise DomainError("Invalid definition JSON") from exc
    validation = validate_variant(source)
    nodes, edges = [], []
    by_id: dict[str, list[str]] = {}
    for kind, field in (
        ("fact", "facts"),
        ("artifact", "artifacts"),
        ("event", "events"),
        ("path", "playable_paths"),
    ):
        for index, record in enumerate(source[field]):
            node_id = f"{kind}:{record['id']}"
            if any(n["id"] == node_id for n in nodes):
                raise DomainError("Duplicate explanation node")
            nodes.append(
                {
                    "id": node_id,
                    "kind": kind,
                    "source_id": record["id"],
                    "source_pointer": f"/{field}/{index}",
                }
            )
            by_id.setdefault(record["id"], []).append(node_id)
    for index, actor in enumerate(source["actor_knowledge"]):
        actor_id = f"actor:{index}"
        nodes.append(
            {"id": actor_id, "kind": "actor", "source_pointer": f"/actor_knowledge/{index}"}
        )
        for offset, fact_id in enumerate(actor["knows_fact_ids"]):
            edges.append(
                {
                    "from": actor_id,
                    "to": f"fact:{fact_id}",
                    "relation": "AUTHORED_KNOWLEDGE",
                    "source_pointer": f"/actor_knowledge/{index}/knows_fact_ids/{offset}",
                }
            )
    for index, event in enumerate(source["events"]):
        for offset, effect in enumerate(event["effects"]):
            if effect["operation"] == "release_artifact":
                edges.append(
                    {
                        "from": f"event:{event['id']}",
                        "to": f"artifact:{effect['target']}",
                        "relation": "AUTHORED_RELEASE",
                        "source_pointer": f"/events/{index}/effects/{offset}/target",
                    }
                )
    unlinked_actions = 0
    for index, path in enumerate(source["playable_paths"]):
        for offset, action in enumerate(path["actions"]):
            targets = by_id.get(action, []) if isinstance(action, str) else []
            if len(targets) == 1:
                edges.append(
                    {
                        "from": f"path:{path['id']}",
                        "to": targets[0],
                        "relation": "EXACT_ACTION_REFERENCE",
                        "source_pointer": f"/playable_paths/{index}/actions/{offset}",
                    }
                )
            else:
                unlinked_actions += 1
    # Existing source contract does not encode these typed relationships. Narrative text
    # is preserved below but cannot silently supply missing reviewed graph edges.
    gaps = [
        "EXACT_FRAMEWORK_OBLIGATION_LINKS_NOT_TYPED",
        "CONTROL_OBLIGATION_TO_SOURCE_RECORD_LINKS_NOT_TYPED",
        "SHARED_ROOT_ISSUE_IDENTITY_NOT_TYPED",
        "ACTOR_KNOWLEDGE_EFFECTIVE_INTERVALS_NOT_TYPED",
        "ARTIFACT_RETENTION_AND_ACCESS_RULES_NOT_TYPED",
        "ENGAGEMENT_SCOPE_AND_LEARNER_HISTORY_UNBOUND",
        "REMEDIATION_TO_RETEST_RECORD_LINKS_NOT_TYPED",
    ]
    if unlinked_actions:
        gaps.append("NARRATIVE_PATH_ACTIONS_REQUIRE_REFERENCE_REVIEW")
    if source["rubric"]["professional_validation"] != "EXPERT_REVIEWED":
        gaps.append("PROFESSIONAL_RUBRIC_NOT_EXPERT_REVIEWED")
    return {
        "schema": "PRIVATE_INSTRUCTOR_KEY_V1",
        "audience": "INSTRUCTOR_ONLY",
        "company_store_import": "PROHIBITED",
        "id": source["id"],
        "source": {
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "canonical_sha256": digest(source),
            "schema_version": source["schema_version"],
        },
        "explanation": copy.deepcopy(source),
        "graph": {
            "nodes": nodes,
            "edges": edges,
            "edge_semantics": "AUTHORED_REFERENCES_ONLY_NOT_CORROBORATION",
        },
        "review": {
            "structural": validation["structural"],
            "migration": "PRESERVED_WITH_EXPLICIT_GAPS",
            "professional": validation["professional_rubric"],
            "causal_validation": "NOT_RUN",
            "grading": "NOT_RUN",
            "unlinked_path_actions": unlinked_actions,
            "gaps": gaps,
        },
    }


def _private_write(path: Path, raw: bytes) -> None:
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _json(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def build_archive(definitions: Path, output: Path) -> dict:
    """Build all required definitions in a NEW protected generated directory.

    Failed partial attempts remain private and lack a completion receipt. Retry in a new
    directory. No company/runtime database connection is made by this module.
    """
    definitions, output = Path(definitions).absolute(), Path(output).absolute()
    protected = "private-corpus" in output.parts or (
        "enterprise/generated/audit-suite/overnight-company-source-2026-09-13/" in output.as_posix()
    )
    if output.resolve() != output or not protected:
        raise DomainError("Instructor keys require a nonsymlink protected generated destination")
    if output.exists():
        raise DomainError("Output already exists; use a new immutable destination")
    files = sorted(definitions.glob("*.json"))
    expected = set(obligations())
    loaded = []
    seen = set()
    for path in files:
        if path.resolve() != path or not stat.S_ISREG(path.stat().st_mode):
            raise DomainError("Definition must be a regular nonsymlink source")
        raw = path.read_bytes()
        key = migrate_definition(raw)
        if key["id"] in seen or path.stem != key["id"]:
            raise DomainError("Duplicate or mismatched source identity")
        seen.add(key["id"])
        loaded.append((raw, key))
    if seen != expected:
        raise DomainError("Definition inventory differs from the required corpus denominator")
    # Create missing ancestors privately, never silently relax an existing directory.
    missing = []
    parent = output.parent
    while not parent.exists():
        missing.append(parent)
        parent = parent.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
    if output.parent.stat().st_mode & 0o077:
        raise DomainError("Output parent must be private (0700)")
    output.mkdir(mode=0o700)
    (output / "sources").mkdir(mode=0o700)
    (output / "keys").mkdir(mode=0o700)
    entries, gaps, statuses = [], Counter(), Counter()
    for raw, key in loaded:
        name = key["id"] + ".json"
        key_bytes = _json(key)
        _private_write(output / "sources" / name, raw)
        _private_write(output / "keys" / name, key_bytes)
        entries.append(
            {
                "id": key["id"],
                "source": "sources/" + name,
                "key": "keys/" + name,
                **key["source"],
                "key_sha256": hashlib.sha256(key_bytes).hexdigest(),
                "review": key["review"],
            }
        )
        gaps.update(key["review"]["gaps"])
        statuses.update([key["review"]["professional"]])
    index = {
        "schema": "PRIVATE_INSTRUCTOR_KEY_INDEX_V1",
        "audience": "INSTRUCTOR_ONLY",
        "required": len(expected),
        "migrated": len(entries),
        "causally_validated": 0,
        "professionally_reviewed_source_statuses": dict(statuses),
        "gap_counts": dict(gaps),
        "entries": entries,
    }
    _private_write(output / "index.json", _json(index))
    archive = output / "instructor-keys.zip"
    with archive.open("xb") as stream:
        os.chmod(archive, 0o600)
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(output.rglob("*.json")):
                info = zipfile.ZipInfo(path.relative_to(output).as_posix(), (1980, 1, 1, 0, 0, 0))
                info.external_attr = (stat.S_IFREG | 0o600) << 16
                bundle.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
        stream.flush()
        os.fsync(stream.fileno())
    receipt = {
        "status": "MIGRATED_NOT_PROFESSIONALLY_VALIDATED",
        "required": len(expected),
        "migrated": len(entries),
        "gap_counts": dict(gaps),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "index_sha256": hashlib.sha256((output / "index.json").read_bytes()).hexdigest(),
        "company_store_import": "PROHIBITED",
    }
    _private_write(output / "receipt.json", _json(receipt))
    receipt["reread_verification"] = verify_archive(output)
    _private_write(output / "verification.json", _json(receipt["reread_verification"]))
    return receipt


def verify_archive(output: Path) -> dict:
    """Re-read original files AND ZIP members, verifying every byte/canonical pin."""
    output = Path(output)
    index = json.loads((output / "index.json").read_bytes())
    receipt = json.loads((output / "receipt.json").read_bytes())
    archive = output / "instructor-keys.zip"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != receipt["archive_sha256"]:
        raise DomainError("Archive digest mismatch")
    if hashlib.sha256((output / "index.json").read_bytes()).hexdigest() != receipt["index_sha256"]:
        raise DomainError("Index digest mismatch")
    expected_members = {"index.json"}
    with zipfile.ZipFile(archive) as bundle:
        for entry in index["entries"]:
            for field, pin in (("source", "raw_sha256"), ("key", "key_sha256")):
                member = entry[field]
                if member != f"{'sources' if field == 'source' else 'keys'}/{entry['id']}.json":
                    raise DomainError("Invalid archive member identity")
                expected_members.add(member)
                path = output / member
                raw = path.read_bytes()
                if path.resolve() != path.absolute() or path.stat().st_mode & 0o077:
                    raise DomainError("Private file permissions or path changed")
                if hashlib.sha256(raw).hexdigest() != entry[pin] or bundle.read(member) != raw:
                    raise DomainError("Retained original or archive member digest mismatch")
            source = json.loads((output / entry["source"]).read_bytes())
            key = json.loads((output / entry["key"]).read_bytes())
            if digest(source) != entry["canonical_sha256"] or key["explanation"] != source:
                raise DomainError("Canonical explanation identity mismatch")
            if key["source"]["raw_sha256"] != entry["raw_sha256"]:
                raise DomainError("Key original source binding mismatch")
        if set(bundle.namelist()) != expected_members or len(bundle.namelist()) != len(
            expected_members
        ):
            raise DomainError("Unexpected or duplicate archive members")
        if bundle.read("index.json") != (output / "index.json").read_bytes():
            raise DomainError("Archived index differs")
    return {
        "status": "PASS",
        "sources": len(index["entries"]),
        "keys": len(index["entries"]),
        "members": len(expected_members),
    }
