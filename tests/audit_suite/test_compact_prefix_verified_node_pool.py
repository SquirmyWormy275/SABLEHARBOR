"""Neutral exact-prefix fixtures; no production world or accepted evidence."""

import gc
import hashlib
import json
import os
import sqlite3
import sys
import weakref
from pathlib import Path

import pytest

from enterprise.audit_suite import canonical_state_codec as codec
from enterprise.audit_suite import compact_prefix_storage as compact
from enterprise.audit_suite.sealed_history_store import _SealedConnection
from enterprise.audit_suite.store import DomainError, Store, _ClosingConnection, canonical


def fixture_prefix(root, states, module=compact):
    root.mkdir(mode=0o700)
    store = Store(root / "original")
    actor = store.provision("Fictional Instructor", ["instructor"])["id"]
    current = store.create(actor, {"fixture": states[0]}, "fictional-create")
    engagement = current["id"]
    for number, value in enumerate(states[1:], 1):
        with store.connect() as db:
            previous = db.execute(
                "SELECT hash FROM events ORDER BY revision DESC LIMIT 1"
            ).fetchone()[0]
            current = dict(current, fixture=value, revision=number)
            store._append(
                db,
                actor,
                current,
                f"fictional-step-{number}",
                {"kind": "fictional.fixture", "step": number},
                previous,
            )
            db.execute(
                "UPDATE engagements SET revision=?,state=? WHERE id=?",
                (number, canonical(current), engagement),
            )
    with store.connect() as db:
        current_row = db.execute("SELECT revision,state FROM engagements").fetchone()
        tip = db.execute("SELECT hash FROM events ORDER BY revision DESC LIMIT 1").fetchone()[0]
        projection = module._projection(db)
    pin = {
        "path": str(store.db_path),
        "bytes": store.db_path.stat().st_size,
        "sha256": module._file_sha(store.db_path),
        "engagement": engagement,
        "revision": current_row[0],
        "last_hash": tip,
        "current_state_sha256": hashlib.sha256(current_row[1].encode()).hexdigest(),
        "initial_auth_sha256": {
            name: projection[name]["sha256"] for name in ("principals", "members", "sessions")
        },
    }
    receipt = root / "FICTIONAL_RECOVERY.json"
    receipt.write_text('{"qualification":"ENGINEERING_NEUTRAL_ONLY"}\n')
    receipt.chmod(0o600)
    mapping = module.convert_prefix(
        pin,
        root / "derivative",
        recovery_receipts=[{"path": str(receipt), "sha256": module._file_sha(receipt)}],
        min_free_bytes=0,
        engineering_neutral_only=True,
    )
    return pin, mapping


@pytest.fixture
def prefix(tmp_path):
    pin, mapping = fixture_prefix(tmp_path / "prefix", ["F" * 200000, "F" * 200000 + "changed"])
    return compact.CompactPrefix(mapping, pin)


def descriptors(db, schema="main"):
    return [
        tuple(row)
        for row in db.execute(
            "SELECT state_root,state_bytes,state_sha256 "
            f"FROM {schema}.prefix_frames ORDER BY revision"
        )
    ]


def node_reads(db):
    reads = []
    db.set_trace_callback(
        lambda statement: (
            reads.append(statement)
            if statement.startswith("SELECT kind,payload,bytes FROM")
            else None
        )
    )
    return reads


def retained_bytes(pool):
    total = sys.getsizeof(pool) + sys.getsizeof(pool.__dict__) + sys.getsizeof(pool.buckets)
    count = 0
    for entry in pool.buckets:
        while entry is not None:
            total += sys.getsizeof(entry) + sys.getsizeof(entry[0]) + sys.getsizeof(entry[1])
            total += sum(sys.getsizeof(value) for value in entry[1])
            count += 1
            entry = entry[2]
    return total, count


def test_repeated_decode_uses_verified_tuples_and_same_bytes(prefix, monkeypatch):
    with prefix.connection() as db:
        descriptor = descriptors(db)[0]
        reads = node_reads(db)
        calls = []
        original = codec.node_id
        monkeypatch.setattr(
            codec, "node_id", lambda *args: (calls.append(args[0]), original(*args))[1]
        )
        first = prefix.decode(db, *descriptor)
        first_reads, first_hashes = len(reads), len(calls)
        assert first_reads > 0 and first_hashes == first_reads
        assert prefix.decode(db, *descriptor) == first
        assert len(reads) == first_reads and len(calls) == first_hashes
        assert db._compact_prefix_nodes.count > 0


def test_unbound_connection_is_uncached(prefix):
    with sqlite3.connect(
        prefix.database.as_uri() + "?immutable=1", uri=True, factory=_ClosingConnection
    ) as db:
        descriptor = descriptors(db)[0]
        reads = node_reads(db)
        compact.CompactPrefix.decode(db, *descriptor)
        count = len(reads)
        compact.CompactPrefix.decode(db, *descriptor)
        assert len(reads) == 2 * count and not hasattr(db, "_compact_prefix_nodes")


def test_connections_do_not_share_pool(prefix):
    with prefix.connection() as first, prefix.connection() as second:
        compact.CompactPrefix.decode(first, *descriptors(first)[0])
        assert first._compact_prefix_nodes.count > 0 and second._compact_prefix_nodes.count == 0
        assert first._compact_prefix_nodes is not second._compact_prefix_nodes


@pytest.mark.parametrize("wrong", ["sha", "size", "root", "schema"])
def test_locator_refusals_clear_pool(prefix, wrong):
    with prefix.connection() as db:
        root, size, sha = descriptors(db)[0]
        prefix.decode(db, root, size, sha)
        values = dict(root=root, size=size, sha=sha, schema="main")
        values[wrong] = {"sha": "0" * 64, "size": size - 1, "root": "0" * 64, "schema": "bad"}[
            wrong
        ]
        with pytest.raises(DomainError):
            prefix.decode(db, **values)
        assert db._compact_prefix_nodes.count == 0 and db._compact_prefix_nodes.disabled


def test_baseexception_miss_disables_pool(prefix, monkeypatch):
    with prefix.connection() as db:
        monkeypatch.setattr(
            codec, "node_id", lambda *args: (_ for _ in ()).throw(KeyboardInterrupt())
        )
        with pytest.raises(KeyboardInterrupt):
            prefix.decode(db, *descriptors(db)[0])
        assert db._compact_prefix_nodes.count == 0 and db._compact_prefix_nodes.disabled


def test_close_clears_pool_with_outstanding_cursor(prefix):
    db = prefix.connection()
    descriptor = descriptors(db)[0]
    prefix.decode(db, *descriptor)
    cursor = db.execute("SELECT state FROM events")
    pool = db._compact_prefix_nodes
    assert pool.count > 0
    db.close()
    assert pool.count == 0 and pool.disabled
    with pytest.raises(sqlite3.ProgrammingError):
        cursor.fetchone()


def test_close_baseexception_still_clears_pool(prefix):
    class InterruptedClose(_ClosingConnection):
        def close(self):
            try:
                super().close()
            finally:
                raise KeyboardInterrupt()

    db = sqlite3.connect(
        prefix.database.as_uri() + "?immutable=1", uri=True, factory=InterruptedClose
    )
    prefix.install(db)
    prefix.decode(db, *descriptors(db)[0])
    with pytest.raises(KeyboardInterrupt):
        db.close()
    assert db._compact_prefix_nodes.count == 0 and db._compact_prefix_nodes.disabled


def test_connection_finalization_clears_pool(prefix):
    db = prefix.connection()
    prefix.decode(db, *descriptors(db)[0])
    pool, reference = db._compact_prefix_nodes, weakref.ref(db)
    del db
    gc.collect()
    assert reference() is None and pool.count == 0 and pool.disabled


def test_install_sql_error_clears_pool(prefix):
    with sqlite3.connect(
        prefix.database.as_uri() + "?immutable=1", uri=True, factory=_ClosingConnection
    ) as db:
        db.execute("CREATE TEMP VIEW events AS SELECT 1")
        with pytest.raises(sqlite3.OperationalError):
            prefix.install(db)
        assert db._compact_prefix_nodes.count == 0 and db._compact_prefix_nodes.disabled


def test_existing_sealed_close_hook_is_preserved(prefix):
    db = sqlite3.connect(":memory:", uri=True, factory=_SealedConnection)
    db.execute("ATTACH DATABASE ? AS sealed_prefix", (prefix.database.as_uri() + "?immutable=1",))
    prefix.install(db, schema="sealed_prefix", view="prefix_events")
    compact.CompactPrefix.decode(db, *descriptors(db, "sealed_prefix")[0], schema="sealed_prefix")

    class Invocation:
        closed = False

        def close(self):
            self.closed = True

    invocation = Invocation()

    class PrefixOwner:
        checks = 0

        def check_prefix(self):
            prefix.check()
            self.checks += 1

    owner = PrefixOwner()
    db._sealed_owner = owner
    db._codec_invocation = invocation
    db._codec_contents = {"fictional": 1}
    db.close()
    assert invocation.closed and db._codec_contents is None and owner.checks == 1
    assert db._compact_prefix_nodes.count == 0


def test_owner_namespace_rebinding_refused(prefix, tmp_path):
    pin, mapping = fixture_prefix(tmp_path / "other", ["Other fictional bytes"])
    other = compact.CompactPrefix(mapping, pin)
    with prefix.connection() as db:
        with pytest.raises(DomainError):
            other.install(db)
    with sqlite3.connect(":memory:", uri=True, factory=_ClosingConnection) as db:
        db.execute(
            "ATTACH DATABASE ? AS sealed_prefix", (other.database.as_uri() + "?immutable=1",)
        )
        with pytest.raises(DomainError):
            prefix.install(db, schema="sealed_prefix", view="prefix_events")


def test_storage_change_after_cache_fill_refused(prefix):
    with prefix.connection() as db:
        descriptor = descriptors(db)[0]
        prefix.decode(db, *descriptor)
        old = prefix.database.stat()
        os.utime(prefix.database, ns=(old.st_atime_ns, old.st_mtime_ns + 1))
        with pytest.raises(DomainError):
            prefix.decode(db, *descriptor)
        assert db._compact_prefix_nodes.count == 0
        with pytest.raises(DomainError):
            prefix.check()


def test_bound_owner_cannot_be_retargeted_or_readmitted(prefix, tmp_path):
    pin, mapping = fixture_prefix(tmp_path / "retarget", ["Other fictional bytes"])
    with prefix.connection() as db:
        descriptor = descriptors(db)[0]
        prefix.decode(db, *descriptor)
        prefix.__init__(mapping, pin)
        with pytest.raises(DomainError):
            prefix.decode(db, *descriptor)
        assert db._compact_prefix_nodes.count == 0


def test_full_cold_graph_and_byte_checks_remain_uncached(tmp_path, monkeypatch):
    pin, mapping = fixture_prefix(tmp_path / "opening", ["fictional" * 10000])
    graph, hashes, flags = [], [], []
    old_graph, old_hash, old_install = (
        compact.verify_graph,
        compact._file_sha,
        compact.CompactPrefix.install,
    )

    def verify(*args, **kwargs):
        graph.append(True)
        return old_graph(*args, **kwargs)

    def file_hash(path):
        hashes.append(str(path))
        return old_hash(path)

    def install(owner, db, **kwargs):
        flags.append(getattr(owner, "_nodes_verified", False))
        return old_install(owner, db, **kwargs)

    monkeypatch.setattr(compact, "verify_graph", verify)
    monkeypatch.setattr(compact, "_file_sha", file_hash)
    monkeypatch.setattr(compact.CompactPrefix, "install", install)
    owner = compact.CompactPrefix(mapping, pin)
    assert graph == [True] and flags == [False]
    assert hashes.count(str(owner.database)) == 2 and owner._nodes_verified


def test_rehashed_corrupt_node_refused_at_full_cold_validation(tmp_path):
    pin, mapping = fixture_prefix(tmp_path / "corrupt", ["fictional" * 10000])
    path = Path(mapping["path"])
    document = json.loads(path.read_text())
    storage = Path(document["storage"]["path"])
    with sqlite3.connect(storage, factory=_ClosingConnection) as db:
        db.execute("DROP TRIGGER state_nodes_no_update")
        db.execute(
            "UPDATE state_nodes SET payload=? WHERE rowid=(SELECT min(rowid) FROM state_nodes)",
            (b"corrupt",),
        )
    document["storage"]["sha256"] = compact._file_sha(storage)
    path.write_text(canonical(document))
    mapping["sha256"] = compact._file_sha(path)
    with pytest.raises(DomainError):
        compact.CompactPrefix(mapping, pin)


def test_closing_full_byte_failure_never_admits_pool(tmp_path, monkeypatch):
    pin, mapping = fixture_prefix(tmp_path / "closing", ["fictional" * 10000])
    storage = json.loads(Path(mapping["path"]).read_text())["storage"]["path"]
    original, calls = compact._file_sha, []

    def closing_failure(path):
        if str(path) == storage:
            calls.append(True)
            if len(calls) == 2:
                return "0" * 64
        return original(path)

    monkeypatch.setattr(compact, "_file_sha", closing_failure)
    with pytest.raises(DomainError):
        compact.CompactPrefix(mapping, pin)
    assert len(calls) == 2


def test_cache_budget_is_accounted_and_earliest_entries_retained(prefix):
    with prefix.connection() as db:
        pool = db._compact_prefix_nodes
        for number in range(2000):
            payload = (f"fictional-node-{number:08}-".encode() * 4000)[: codec.CHUNK]
            node = ("L", payload, len(payload))
            pool.put(codec.node_id(*node), node)
            assert pool.bytes <= compact.VERIFIED_NODE_CACHE_BYTES
        actual, count = retained_bytes(pool)
        assert actual <= pool.bytes <= 16 * 1024**2 and count == pool.count
        assert count < 2000
        payload = (b"fictional-node-00000000-" * 4000)[: codec.CHUNK]
        assert pool.get(codec.node_id("L", payload, len(payload))) is not None
        pool.clear()
        assert retained_bytes(pool)[1] == 0 and pool.bytes == pool.base_bytes
