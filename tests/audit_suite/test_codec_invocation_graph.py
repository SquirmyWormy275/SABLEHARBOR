"""Fresh connection-scoped graph proofs, never an examination result cache."""

import hashlib
import sqlite3

import pytest

from enterprise.audit_suite.canonical_state_codec import (
    MAX_INVOCATION_BLOCK_BYTES,
    SQL,
    VerifiedInvocationGraph,
    decode,
    encode,
    node_id,
    verify_nodes,
)
from enterprise.audit_suite.store import DomainError, canonical


def test_exact_fresh_graph_parity_bounded_blocks_and_close():
    with sqlite3.connect(":memory:") as db:
        db.executescript(SQL)
        states = [
            {"text": ("雪😀" + str(i)) * 12000, "scalar": [False, 0, -0.0], "revision": i}
            for i in range(4)
        ]
        roots = [encode(db, x)[0] for x in states]
        graph = VerifiedInvocationGraph(db, roots)
        for root, state in zip(roots, states, strict=True):
            raw = decode(db, root, invocation=graph)
            assert raw == canonical(state).encode()
            assert hashlib.sha256(raw).digest() == hashlib.sha256(decode(db, root)).digest()
        assert graph._block_bytes <= MAX_INVOCATION_BLOCK_BYTES
        graph.close()
        assert not graph._nodes and not graph._proof and not graph._blocks
        with pytest.raises(DomainError, match="closed"):
            decode(db, roots[0], invocation=graph)


def test_fresh_snapshot_required_and_other_connection_refuses():
    with sqlite3.connect(":memory:") as db, sqlite3.connect(":memory:") as other:
        db.executescript(SQL)
        other.executescript(SQL)
        root, _ = encode(db, {"id": "genuine"})
        db.commit()
        with pytest.raises(DomainError, match="transaction"):
            VerifiedInvocationGraph(db, [root])
        db.execute("BEGIN")
        other.execute("BEGIN")
        graph = VerifiedInvocationGraph(db, [root])
        with pytest.raises(DomainError, match="another transaction"):
            decode(other, root, invocation=graph)
        db.rollback()
        with pytest.raises(DomainError, match="closed, changed"):
            decode(db, root, invocation=graph)


def test_same_connection_write_cannot_use_stale_proof():
    with sqlite3.connect(":memory:") as db:
        db.executescript(SQL)
        root, _ = encode(db, {"id": "old", "revision": 0})
        graph = VerifiedInvocationGraph(db, [root])
        new, _ = encode(db, {"id": "new", "revision": 1})
        with pytest.raises(DomainError, match="closed, changed"):
            decode(db, root, invocation=graph)
        with pytest.raises(DomainError, match="closed, changed"):
            decode(db, new, invocation=graph)
        fresh = VerifiedInvocationGraph(db, [root, new])
        assert decode(db, new, invocation=fresh) == canonical({"id": "new", "revision": 1}).encode()


@pytest.mark.parametrize("payload", [b"[", b"{}", b"[true]", b"[]"])
def test_hash_resealed_malformed_concat_is_bounded_domain_refusal(payload):
    with sqlite3.connect(":memory:") as db:
        db.executescript(SQL)
        identifier = node_id("C", payload, 1)
        db.execute("INSERT INTO state_nodes VALUES (?,?,?,?)", (identifier, "C", payload, 1))
        for method in (
            lambda: verify_nodes(db, [identifier]),
            lambda: decode(db, identifier),
            lambda: VerifiedInvocationGraph(db, [identifier]),
        ):
            with pytest.raises(DomainError):
                method()


def test_every_node_fresh_and_unregistered_original_refuses():
    with sqlite3.connect(":memory:") as db:
        db.executescript(SQL)
        root, _ = encode(db, {"text": "exact retained bytes"})
        first = VerifiedInvocationGraph(db, [root])
        assert decode(db, root, invocation=first)
        db.execute("DROP TRIGGER state_nodes_no_update")
        row = db.execute("SELECT id,payload FROM state_nodes WHERE kind='L' LIMIT 1").fetchone()
        db.execute("UPDATE state_nodes SET payload=? WHERE id=?", (row[1] + b" ", row[0]))
        with pytest.raises(DomainError):
            VerifiedInvocationGraph(db, [root])
    with sqlite3.connect(":memory:") as db:
        db.executescript(SQL)
        root, _ = encode(db, {"id": "exact"})
        encode(db, {"unused": "not an authorized root"})
        with pytest.raises(DomainError, match="Unregistered"):
            VerifiedInvocationGraph(db, [root])
