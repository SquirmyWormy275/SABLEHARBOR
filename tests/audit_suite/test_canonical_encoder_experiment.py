import random
import sqlite3

import pytest

from enterprise.audit_suite import canonical_state_codec as candidate
from enterprise.audit_suite import canonical_state_codec as reference
from enterprise.audit_suite.store import DomainError, canonical


@pytest.fixture
def db(tmp_path):
    with sqlite3.connect(tmp_path / "owned-encoder.sqlite3") as result:
        result.executescript(reference.SQL)
        yield result


def test_generated_values_and_utf8_chunk_cuts_reconstruct_exactly(db):
    rng = random.Random(90417)
    values = [
        None,
        True,
        False,
        -0.0,
        5e-324,
        1e200,
        {1: "legacy"},
        (),
        "雪😀\x00" * 20000,
        {"long": "x" * 180000},
    ]
    values += [
        {
            "a": rng.getrandbits(150),
            "b": [rng.random(), True, None],
            "c": "".join(rng.choices("é雪😀\nabc", k=300)),
        }
        for _ in range(40)
    ]
    roots = []
    for value in values:
        root, size = candidate.encode(db, value)
        roots.append(root)
        assert reference.decode(db, root) == canonical(value).encode()
        assert size == len(canonical(value).encode())
    reference.verify_nodes(db, roots)
    assert db.execute("SELECT max(bytes) FROM state_nodes WHERE kind='L'").fetchone()[0] <= 65536


def test_original_errors_publish_no_nodes(db):
    circular = []
    circular.append(circular)
    for value in [circular, float("nan"), float("inf"), object(), {1: 2, "mixed": 3}, "\ud800"]:
        try:
            canonical(value).encode()
        except Exception as original:
            with pytest.raises(type(original)):
                candidate.encode(db, value)
        else:
            raise AssertionError("Invalid fixture unexpectedly admitted")
        assert db.execute("SELECT count(*) FROM state_nodes").fetchone()[0] == 0


def test_original_admitted_deep_values_are_not_redecomposed(db):
    value = "deep"
    for _ in range(400):
        value = [value]
    root, _ = candidate.encode(db, value)
    assert reference.decode(db, root) == canonical(value).encode()


@pytest.mark.parametrize(
    "field,replacement", [("kind", "C"), ("payload", b"false"), ("bytes", 5000)]
)
def test_existing_requested_literal_is_freshly_compared_before_return(db, field, replacement):
    value = {"source": "Generated identical field" * 500}
    candidate.encode(db, value)
    db.execute("DROP TRIGGER state_nodes_no_update")
    identifier = db.execute("SELECT id FROM state_nodes WHERE kind='L' LIMIT 1").fetchone()[0]
    db.execute(f"UPDATE state_nodes SET {field}=? WHERE id=?", (replacement, identifier))
    with pytest.raises(DomainError, match="Existing canonical fragment differs"):
        candidate.encode(db, value)


def test_existing_requested_concat_is_freshly_compared(db):
    value = {"data": "".join(random.Random(713).choices("abcdefghi123456", k=150000))}
    candidate.encode(db, value)
    db.execute("DROP TRIGGER state_nodes_no_update")
    identifier = db.execute("SELECT id FROM state_nodes WHERE kind='C' LIMIT 1").fetchone()[0]
    db.execute("UPDATE state_nodes SET payload=? WHERE id=?", (b"[]", identifier))
    with pytest.raises(DomainError, match="Existing canonical fragment differs"):
        candidate.encode(db, value)


def test_binding_limit_is_observed(db):
    db.setlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER, 7)
    value = list(range(10000))
    root, _ = candidate.encode(db, value)
    assert reference.decode(db, root) == canonical(value).encode()


def test_native_boundary_interface_refuses_nonbytes():
    for raw in ["", bytearray(b"[]"), memoryview(b"[]"), True]:
        with pytest.raises(TypeError):
            candidate._fragmenter.boundaries(raw)


def test_optional_helper_absence_preserves_structural_codec(db, monkeypatch):
    monkeypatch.setattr(candidate, "_fragmenter", None)
    value = {"admitted": [True, 1, None, "雪" * 40000]}
    root, size = candidate.encode(db, value)
    assert reference.decode(db, root) == canonical(value).encode()
    assert size == len(canonical(value).encode())
    assert candidate.native_code_files() == {}


def test_helper_origins_are_explicit_and_wrong_abi_refuses(monkeypatch):
    origins = candidate.native_code_files()
    assert len(origins) == 2
    monkeypatch.setattr(candidate._fragmenter, "__file__", "/unreviewed/native.so")
    with pytest.raises(DomainError, match="origin or interpreter ABI differs"):
        candidate.native_code_files()


@pytest.mark.parametrize("offsets", [[True], [0], [1000000], [], [1, 1]])
def test_invalid_native_offset_vectors_publish_no_nodes(db, monkeypatch, offsets):
    monkeypatch.setattr(candidate._fragmenter, "boundaries", lambda raw: offsets)
    with pytest.raises(DomainError):
        candidate.encode(db, {"field": "Generated original"})
    assert db.execute("SELECT count(*) FROM state_nodes").fetchone()[0] == 0


def test_identifier_collision_cannot_substitute_different_literal(db, monkeypatch):
    monkeypatch.setattr(candidate, "node_id", lambda kind, payload, size: "0" * 64)
    with pytest.raises(
        DomainError, match="identifier collision|Existing canonical fragment differs"
    ):
        candidate.encode(db, {"a": "field" * 600, "b": "different field" * 600})
    assert db.execute("SELECT count(*) FROM state_nodes").fetchone()[0] == 0


def test_small_insert_does_not_rewrite_unchanged_patterned_large_strings(db):
    state = {
        "notes": [],
        "papers": [{"id": str(i), "text": (str(i) + " unchanged ") * 10000} for i in range(20)],
    }
    root, _ = candidate.encode(db, state)
    raw = canonical(state).encode()
    initial = db.execute("SELECT sum(length(payload)) FROM state_nodes").fetchone()[0]
    state["notes"].append({"id": "NOTE", "text": "Small generated mechanics note"})
    newest, _ = candidate.encode(db, state)
    growth = db.execute("SELECT sum(length(payload)) FROM state_nodes").fetchone()[0] - initial
    assert growth < 16384
    assert reference.decode(db, root) == raw
    assert reference.decode(db, newest) == canonical(state).encode()
    reference.verify_nodes(db, [root, newest])


def test_one_hundred_genuine_normal_store_notes_use_lossless_tail_codec(tmp_path):
    import hashlib
    import json

    from enterprise.audit_suite.sealed_history_store import SealedHistoryStore, prepare_tail
    from enterprise.audit_suite.store import Store

    rng = random.Random(509174)
    original = Store(tmp_path / "original")
    operator = original.provision("Owned neutral mechanics operator", ["instructor"])
    initial = original.create(
        operator["id"],
        {
            "mode": "CLEAN",
            "simulated_at": "2027-12-31T09:00:00Z",
            "scope": {"engineering_only": True},
            "notes": [],
            "generated": [
                "".join(rng.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=1000))
                for _ in range(1000)
            ],
        },
        "neutral-birth",
    )
    prefix_sha = hashlib.sha256(original.db_path.read_bytes()).hexdigest()
    choice = prepare_tail(
        original, operator["id"], initial["id"], tmp_path / "tail", state_codec=True
    )
    sealed = SealedHistoryStore(original.root, choice["path"], choice["sha256"])
    with sealed.connect() as db:
        initial_payload = db.execute(
            "SELECT sum(length(payload)) FROM main.state_nodes"
        ).fetchone()[0]
    current = initial
    for index in range(1, 101):
        current = sealed.command(
            operator["id"],
            initial["id"],
            {
                "command_id": f"normal-note-{index:03d}",
                "expected_revision": current["revision"],
                "kind": "neutral.note",
                "payload": {"text": f"Owned neutral normal note {index}"},
            },
            lambda state, command, person: state | {"notes": state["notes"] + [command["payload"]]},
            permissions={"instruct"},
        )
    assert current["revision"] == 100 and len(current["notes"]) == 100
    assert hashlib.sha256(original.db_path.read_bytes()).hexdigest() == prefix_sha
    with sealed.connect() as db:
        sealed.verify_projection(db)
        roots = [sealed.state_codec["initial_root"]]
        frames = list(db.execute("SELECT revision,state FROM main.event_frames ORDER BY revision"))
        assert len(frames) == 100 and [x["revision"] for x in frames] == list(range(1, 101))
        for frame in frames:
            descriptor = json.loads(frame["state"])
            roots.append(descriptor["root"])
            raw = reference.decode(db, descriptor["root"])
            value = json.loads(raw)
            assert value["revision"] == frame["revision"]
            assert len(value["notes"]) == frame["revision"]
            assert hashlib.sha256(raw).hexdigest() == descriptor["sha256"]
        reference.verify_nodes(db, roots)
        growth = (
            db.execute("SELECT sum(length(payload)) FROM main.state_nodes").fetchone()[0]
            - initial_payload
        )
        assert growth < len(canonical(initial).encode())
