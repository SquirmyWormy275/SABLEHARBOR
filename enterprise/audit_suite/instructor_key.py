"""Private-only instructor explanation migration. No learner projection or company-store adapter.

This structural index preserves authored claims; it neither infers causal proof nor grades.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import stat
import zipfile
from collections import Counter
from pathlib import Path

from .corpus import obligations, validate_variant
from .store import DomainError, digest

SEARCH_FIELDS = (
    "title",
    "mechanism",
    "facts",
    "actor_knowledge",
    "artifacts",
    "events",
    "playable_paths",
)
MAX_SEARCH_TERMS = 32
MAX_SEARCH_CHARACTERS = 128
MAX_SEARCH_BYTES = 4 * 1024
MAX_SEARCH_INDEX_BYTES = 8 * 1024 * 1024
MAX_SEARCH_KEY_BYTES = 8 * 1024 * 1024
MAX_COMPLETE_SEARCH_BYTES = 64 * 1024 * 1024
MAX_SEARCH_QUERY_CHARACTERS = 1000
MAX_SEARCH_RESULT_BYTES = 256 * 1024


def semantic_search_query(value: str) -> str:
    if not isinstance(value, str) or len(value) > MAX_SEARCH_QUERY_CHARACTERS:
        raise DomainError("Bounded authored search query required")
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise DomainError("Valid authored search Unicode required") from error
    return value.strip().lower()


def _authored_scalars(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from _authored_scalars(child)
    elif isinstance(value, list):
        for child in value:
            yield from _authored_scalars(child)
    elif value is None or type(value) in (str, int, float, bool):
        yield value if isinstance(value, str) else json.dumps(value, allow_nan=False)


def semantic_search_text(raw: bytes, entry: dict) -> str:
    """Complete literal matching; display truncation never bounds this projection."""
    semantic_search_projection(raw, entry)  # exact held source/Key binding
    key = json.loads(raw)
    review = entry["review"]
    values = [
        entry["id"],
        entry["raw_sha256"],
        entry["canonical_sha256"],
        entry["key_sha256"],
        review["professional"],
        review["causal_validation"],
        review["grading"],
        *review["gaps"],
    ]
    for field in SEARCH_FIELDS:
        values.extend(_authored_scalars(key["explanation"].get(field)))
    return " ".join(values).lower()


def semantic_search_matches(texts: dict[str, str], query: str) -> list[str]:
    query = semantic_search_query(query)
    return [identifier for identifier, text in texts.items() if query in text]


def semantic_search_projection(raw: bytes, entry: dict) -> dict:
    """Literal authored search terms, never inferred person/asset/audit metadata."""
    if (
        not isinstance(entry, dict)
        or not isinstance(entry.get("id"), str)
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", entry["id"]) is None
        or any(
            not isinstance(entry.get(field), str)
            or re.fullmatch(r"[a-f0-9]{64}", entry[field]) is None
            for field in ("key_sha256", "raw_sha256", "canonical_sha256")
        )
    ):
        raise DomainError("Semantic search identity/pins differ", status=503)
    if len(raw) > MAX_SEARCH_KEY_BYTES or hashlib.sha256(raw).hexdigest() != entry["key_sha256"]:
        raise DomainError("Semantic search key bytes differ", status=503)
    key = json.loads(raw)
    if (
        key.get("schema") != "PRIVATE_INSTRUCTOR_KEY_V1"
        or key.get("audience") != "INSTRUCTOR_ONLY"
        or key.get("id") != entry["id"]
        or key.get("source", {}).get("raw_sha256") != entry["raw_sha256"]
        or key.get("source", {}).get("canonical_sha256") != entry["canonical_sha256"]
        or digest(key.get("explanation")) != entry["canonical_sha256"]
    ):
        raise DomainError("Semantic search explanation binding differs", status=503)
    terms, seen, truncated = [], 0, 0
    term_bytes = 0
    included = {field: 0 for field in SEARCH_FIELDS}
    totals = {field: 0 for field in SEARCH_FIELDS}

    def scalars(value, pointer):
        if isinstance(value, dict):
            for name, child in value.items():
                # JSON pointers preserve literal field names; no role classification.
                yield from scalars(
                    child, pointer + "/" + name.replace("~", "~0").replace("/", "~1")
                )
        elif isinstance(value, list):
            for number, child in enumerate(value):
                yield from scalars(child, pointer + "/" + str(number))
        elif value is None or type(value) in (str, int, float, bool):
            yield pointer, value

    # Title is first. Round-robin coverage prevents a large facts array from
    # taking every slot before actor/artifact/event/path terms are considered.
    readers = {
        field: iter(scalars(key["explanation"].get(field), "/" + field)) for field in SEARCH_FIELDS
    }
    while readers:
        for field in list(readers):
            try:
                pointer, value = next(readers[field])
            except StopIteration:
                del readers[field]
                continue
            seen += 1
            totals[field] += 1
            if len(terms) >= MAX_SEARCH_TERMS or len(pointer) > 256:
                continue
            text = value if isinstance(value, str) else json.dumps(value, allow_nan=False)
            term = {"pointer": pointer, "text": text[:MAX_SEARCH_CHARACTERS]}
            if len(text) > MAX_SEARCH_CHARACTERS:
                term.update(truncated=True, full_characters=len(text), value_sha256=digest(value))
            size = len(_json(term))
            if term_bytes + size <= MAX_SEARCH_BYTES - 1536:
                terms.append(term)
                included[field] += 1
                term_bytes += size
                truncated += bool(term.get("truncated"))
    result = {
        "schema": "PRIVATE_AUTHORED_SEMANTIC_SEARCH_V1",
        "basis": "LITERAL_AUTHORED_SCALARS_NOT_VERIFIED_PERSON_ASSET_PERIOD_OR_CAUSALITY",
        "id": entry["id"],
        "source_sha256": entry["raw_sha256"],
        "canonical_sha256": entry["canonical_sha256"],
        "key_sha256": entry["key_sha256"],
        "coverage_fields": list(SEARCH_FIELDS),
        "terms": terms,
        "included_by_field": included,
        "omitted_by_field": {field: totals[field] - included[field] for field in SEARCH_FIELDS},
        "total_scalars": seen,
        "omitted_scalars": seen - len(terms),
        "truncated_values": truncated,
    }
    # Nested JSON indentation can be larger than individually measured terms.
    # Trim display previews only; complete matching retains every scalar.
    while terms and len(_json(result)) > MAX_SEARCH_BYTES:
        removed = terms.pop()
        field = removed["pointer"].split("/")[1]
        result["included_by_field"][field] -= 1
        result["omitted_by_field"][field] += 1
        result["omitted_scalars"] += 1
        result["truncated_values"] -= bool(removed.get("truncated"))
    if len(_json(result)) > MAX_SEARCH_BYTES:
        raise DomainError("Semantic search projection limit", status=503)
    return result


def semantic_search_index(root: Path, index: dict) -> dict:
    """Enrich a verified index without changing any retained source/index/ZIP bytes."""
    return semantic_search_bundle(root, index)[0]


def semantic_search_bundle(root: Path, index: dict) -> tuple[dict, dict[str, str]]:
    """Bounded immutable display and complete matching caches, never evidence outcomes."""
    entries = []
    texts = {}
    complete_bytes = 0
    for entry in index["entries"]:
        path = Path(root) / entry["key"]
        if (
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", entry["id"])
            or entry["key"] != "keys/" + entry["id"] + ".json"
            or path.resolve() != path.absolute()
        ):
            raise DomainError("Semantic search key path differs", status=503)
        before = path.stat()
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size > MAX_SEARCH_KEY_BYTES
        ):
            raise DomainError("Semantic search key input limit", status=503)
        with path.open("rb") as stream:
            raw = stream.read(MAX_SEARCH_KEY_BYTES + 1)
        after = path.stat()
        fields = (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_nlink",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
        )
        if any(getattr(before, field) != getattr(after, field) for field in fields):
            raise DomainError("Semantic search key changed during read", status=503)
        text = semantic_search_text(raw, entry)
        complete_bytes += len(text.encode("utf-8"))
        if entry["id"] in texts or complete_bytes > MAX_COMPLETE_SEARCH_BYTES:
            raise DomainError("Complete authored search cache limit/duplicate identity", status=503)
        texts[entry["id"]] = text
        entries.append({**entry, "semantic_search": semantic_search_projection(raw, entry)})
    result = {**index, "entries": entries}
    result["semantic_matching"] = {
        "schema": "PRIVATE_COMPLETE_AUTHORED_MATCHING_V1",
        "coverage_fields": list(SEARCH_FIELDS),
        "display_previews_only": True,
        "complete_scalar_matching": True,
        "query_max_characters": MAX_SEARCH_QUERY_CHARACTERS,
    }
    if len(_json(result)) > MAX_SEARCH_INDEX_BYTES:
        raise DomainError("Semantic search index limit", status=503)
    return result, texts


def migrate_definition(raw: bytes, *, migration_version: int = 1) -> dict:
    """Return a protected explanation pinned to original bytes and canonical content."""
    if type(migration_version) is not int or migration_version not in (1, 2):
        raise DomainError("Supported exact migration version required")
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
    dual_references = 0
    for index, path in enumerate(source["playable_paths"]):
        for offset, action in enumerate(path["actions"]):
            targets = by_id.get(action, []) if isinstance(action, str) else []
            references = [(targets[0], "EXACT_ACTION_REFERENCE")] if len(targets) == 1 else []
            if migration_version == 2 and isinstance(action, str) and action.startswith("INSPECT:"):
                # The corpus executor defines this exact command grammar. It names
                # an artifact, not an inferred fact, corroboration or completed action.
                artifact_id = action.split(":", 1)[1]
                targets = [
                    n["id"]
                    for n in nodes
                    if n["kind"] == "artifact"
                    and isinstance(n.get("source_id"), str)
                    and n["source_id"] == artifact_id
                ]
                if len(targets) == 1:
                    if references:
                        dual_references += 1
                    references.append((targets[0], "AUTHORED_INSPECTION_TARGET"))
            for target, relation in references:
                edges.append(
                    {
                        "from": f"path:{path['id']}",
                        "to": target,
                        "relation": relation,
                        "source_pointer": f"/playable_paths/{index}/actions/{offset}",
                    }
                )
            if not references:
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
    if dual_references:
        gaps.append("DUAL_LITERAL_AND_INSPECTION_REFERENCES_REQUIRE_REVIEW")
    if source["rubric"]["professional_validation"] != "EXPERT_REVIEWED":
        gaps.append("PROFESSIONAL_RUBRIC_NOT_EXPERT_REVIEWED")
    result = {
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
    if migration_version == 2:
        result["migration_version"] = 2
    return result


def _private_write(path: Path, raw: bytes) -> None:
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _json(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def build_archive(definitions: Path, output: Path, *, migration_version: int = 1) -> dict:
    """Build all required definitions in a NEW protected generated directory.

    Failed partial attempts remain private and lack a completion receipt. Retry in a new
    directory. No company/runtime database connection is made by this module.
    """
    definitions, output = Path(definitions).absolute(), Path(output).absolute()
    if type(migration_version) is not int or migration_version not in (1, 2):
        raise DomainError("Supported exact migration version required")
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
        key = migrate_definition(raw, migration_version=migration_version)
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
    if migration_version == 2:
        index["migration_version"] = 2
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
    if migration_version == 2:
        receipt["migration_version"] = 2
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
