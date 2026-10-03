"""Exact journal serialization and changed-field growth, not source generation."""

import random
import sqlite3

import pytest

from enterprise.audit_suite.canonical_state_codec import SQL, decode, encode, verify_nodes
from enterprise.audit_suite.store import DomainError, canonical


@pytest.fixture
def db(tmp_path):
    with sqlite3.connect(tmp_path / "owned-author-codec.sqlite3") as result:
        result.executescript(SQL)
        yield result


def test_exact_canonical_bytes_and_all_reused_node_membership(db):
    rng = random.Random(77191)
    values = [
        None,
        True,
        False,
        0,
        -0.0,
        1e30,
        5e-324,
        "雪😀\x00\n",
        {},
        [],
        {"same": "Repeated actual bytes", "nested": [1, None, False]},
        {1: "Original numeric key contract"},
        tuple(range(1000)),
    ]
    for _ in range(500):
        values.append(
            {
                "z": "é雪😀" * rng.randrange(1, 100),
                "a": rng.randrange(10**80),
                "array": [rng.random(), bool(rng.randrange(2)), None],
            }
        )
    roots = []
    for value in values:
        root, size = encode(db, value)
        roots.append(root)
        assert size == len(canonical(value).encode())
        assert decode(db, root) == canonical(value).encode()
    proof = verify_nodes(db, roots)
    assert all("payload" not in x for x in proof.values())
    for root, value in zip(roots, values, strict=True):
        assert decode(db, root, proof=proof) == canonical(value).encode()


def test_one_hundred_notes_reuse_genuine_large_unchanged_state_fragments(db):
    # Each distinct text is a literal authoritative state field, no cached result.
    state = {
        "id": "OWNED-ENGINEERING-JOURNAL",
        "revision": 0,
        "notes": [],
        "workpapers": [{"id": str(i), "text": (str(i) + " unchanged ") * 10000} for i in range(20)],
    }
    initial, _ = encode(db, state)
    original = canonical(state).encode()
    roots = [initial]
    initial_payload = db.execute("SELECT SUM(length(payload)) FROM state_nodes").fetchone()[0]
    for revision in range(1, 101):
        state["revision"] = revision
        state["notes"].append({"id": "ordinary-" + str(revision), "text": "A real new note"})
        root, _ = encode(db, state)
        roots.append(root)
        assert decode(db, root) == canonical(state).encode()
    payload = db.execute("SELECT SUM(length(payload)) FROM state_nodes").fetchone()[0]
    assert payload - initial_payload < len(original)
    assert decode(db, initial) == original
    verify_nodes(db, roots)


def test_fresh_fragment_hash_and_missing_or_unregistered_members_refuse(db):
    root, _ = encode(db, {"state": "Actual retained state", "revision": 1})
    verify_nodes(db, [root])
    db.execute("DROP TRIGGER state_nodes_no_update")
    row = db.execute("SELECT id,payload FROM state_nodes WHERE kind='L' LIMIT 1").fetchone()
    db.execute("UPDATE state_nodes SET payload=? WHERE id=?", (row[1] + b" ", row[0]))
    with pytest.raises(DomainError, match="hash differs"):
        verify_nodes(db, [root])


def test_extra_valid_but_unregistered_fragment_has_no_journal_authority(db):
    root, _ = encode(db, {"scope": ["Security"]})
    encode(db, {"extra": "Has no event root"})
    with pytest.raises(DomainError, match="Unregistered"):
        verify_nodes(db, [root])


def test_original_serialization_errors_are_not_substituted_with_fake_state(db):
    for value in ({"bad": object()}, {1: True, "mixed": False}):
        with pytest.raises(TypeError):
            encode(db, value)
    for value in (float("nan"), float("inf")):
        with pytest.raises(ValueError):
            encode(db, {"float": value})
    circular = []
    circular.append(circular)
    with pytest.raises(ValueError, match="Circular"):
        encode(db, circular)


@pytest.mark.parametrize("depth", [1200, 4097])
def test_resealed_deep_concat_graph_has_bounded_iterative_validation(db, depth):
    from enterprise.audit_suite.canonical_state_codec import Encoder

    encoder = Encoder(db)
    root, _ = encoder.put("L", b"0", 1)
    for _ in range(depth):
        root, _ = encoder.put("C", canonical([root]).encode(), 1)
    if depth == 1200:
        contents = {}
        proof = verify_nodes(db, [root], contents=contents)
        assert decode(db, root, proof=proof, contents=contents) == b"0"
        assert decode(db, root) == b"0"
    else:
        with pytest.raises(DomainError, match="depth exceeds"):
            verify_nodes(db, [root])
        with pytest.raises(DomainError, match="depth exceeds"):
            decode(db, root)


def test_existing_admitted_deep_json_remains_exact_without_python_decomposition_failure(db):
    value = "Actual retained deep value"
    for _ in range(400):
        value = [value]
    reference = canonical(value).encode()
    root, size = encode(db, value)
    assert size == len(reference)
    assert decode(db, root, proof=verify_nodes(db, [root])) == reference
