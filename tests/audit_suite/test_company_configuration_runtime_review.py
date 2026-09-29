"""Independent real-source malformed links and persistent input/publication boundaries."""

from copy import deepcopy

import pytest

from enterprise.audit_suite import company_configuration_runtime as runtime
from enterprise.audit_suite.company_backup_runtime import database, pin
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded
from tests.audit_suite.test_company_configuration_runtime import command, ready, snapshot


@pytest.fixture
def current(tmp_path):
    return ready.__wrapped__(tmp_path)


def clone_sources(current, destination, mutation):
    _, _, source, refs = current
    destination.mkdir(mode=0o700)
    store = CompanyStore(destination)
    with database(source) as db:
        originals = {slot: runtime.native(db, ref) for slot, ref in refs.items()}
        owners = {
            (r["company"], r["branch"], r["system"]): r["owner"]
            for r in db.execute("SELECT * FROM systems")
        }
    mapped = {}

    def relink(value):
        if isinstance(value, list):
            return [relink(v) for v in value]
        if not isinstance(value, dict):
            return value
        if set(value) == {"system_id", "record_id", "version", "sha256", "available_at"}:
            key = (value["system_id"], value["record_id"])
            return deepcopy(mapped.get(key, value))
        return {k: relink(v) for k, v in value.items()}

    new_refs = {}
    for slot in ("baseline", "configuration", "build", "tests", "review", "gate", "rollback_plan"):
        row = originals[slot]
        key = (row["company"], row["branch"], row["system"])
        store.register_system(*key, owners[key])
        body = relink(runtime.decode(row["content"]))
        mutation(slot, body)
        new = store.append_version(
            *key,
            row["record"],
            expected_version=0,
            command_id="COPY-" + slot,
            event_at=row["event_at"],
            available_at=row["available_at"],
            content=encoded(body),
            provenance=runtime.decode(row["provenance"]),
            origin=row["origin"],
        )
        new_refs[slot] = pin(new)
        mapped[(row["system"], row["record"])] = {
            "system_id": new["system"],
            "record_id": new["record"],
            "version": new["version"],
            "sha256": new["sha256"],
            "available_at": new["available_at"],
        }
    return new_refs


@pytest.mark.parametrize("bad_version", [True, 1.0])
def test_fully_repinned_native_link_requires_exact_integer(current, tmp_path, bad_version):
    clone = tmp_path / "clone"

    def mutate(slot, body):
        if slot == "build":
            body["source"]["version"] = bad_version

    refs = clone_sources(current, clone, mutate)
    with pytest.raises(CompanyStoreError):
        runtime.initialize(
            tmp_path / "rejected",
            source_root=clone,
            source_pins=refs,
            as_of="2027-02-03T00:00:00Z",
            target_id="NEW",
        )
    assert not (tmp_path / "rejected").exists()


def test_drift_caller_mutation_cannot_change_fingerprinted_operation(current, monkeypatch):
    root, initial, *_ = current
    configuration = {"timeout_ms": 50, "attempts": 3, "max_total_ms": 120}
    args = command(current, "DRIFT", "race", configuration=configuration)
    before = snapshot(root)
    real = runtime._current

    def mutate(*a, **k):
        result = real(*a, **k)
        configuration["timeout_ms"] = 51
        return result

    monkeypatch.setattr(runtime, "_current", mutate)
    try:
        runtime.execute(root, **args)
    except CompanyStoreError:
        assert snapshot(root) == before
    else:
        result = runtime.inspect(root, expected_runtime_sha256=initial["runtime_sha256"])
        assert result["configuration"]["timeout_ms"] == 50


def test_prior_file_changed_after_target_write_rejects_without_new_current(current, monkeypatch):
    root, *_ = current
    args = command(current, "APPLY", "prior-race")
    before = snapshot(root)
    real = runtime._write

    def mutate(parent, name, raw):
        real(parent, name, raw)
        (root / "objects/initial.json").write_bytes(
            encoded({"timeout_ms": 31, "attempts": 3, "max_total_ms": 120})
        )

    monkeypatch.setattr(runtime, "_write", mutate)
    with pytest.raises(CompanyStoreError, match="Prior file"):
        runtime.execute(root, **args)
    assert snapshot(root) == before


def test_old_operation_replay_after_drift_preserves_current_file(current):
    root, initial, *_ = current
    args = command(current, "APPLY", "apply")
    original = runtime.execute(root, **args)
    runtime.execute(
        root,
        **command(
            current,
            "DRIFT",
            "later",
            configuration={"timeout_ms": 50, "attempts": 3, "max_total_ms": 120},
        ),
    )
    before = snapshot(root)
    assert runtime.execute(root, **args) == original
    assert snapshot(root) == before
    assert (
        runtime.inspect(root, expected_runtime_sha256=initial["runtime_sha256"])["configuration"][
            "timeout_ms"
        ]
        == 50
    )


def test_fully_repinned_missing_change_cycle_is_not_one_valid_cycle(current, tmp_path):
    clone = tmp_path / "missing-cycle-source"
    refs = clone_sources(current, clone, lambda slot, body: body.pop("cycle_id", None))
    with pytest.raises(CompanyStoreError):
        runtime.initialize(
            tmp_path / "missing-cycle-target",
            source_root=clone,
            source_pins=refs,
            as_of="2027-02-03T00:00:00Z",
            target_id="MISSING-CYCLE",
        )
    assert not (tmp_path / "missing-cycle-target").exists()


def test_initialization_module_pin_change_before_publication_rejects(
    current, tmp_path, monkeypatch
):
    from pathlib import Path

    root, _, source, refs = current
    target = tmp_path / "changed-code"
    module = Path(runtime.__file__)
    real_read = Path.read_bytes
    real_write = runtime._write
    changed = False

    def fake_read(path):
        data = real_read(path)
        return data + b"\n# changed source bytes\n" if path == module and changed else data

    def trigger(*args, **kwargs):
        nonlocal changed
        result = real_write(*args, **kwargs)
        changed = True
        return result

    monkeypatch.setattr(Path, "read_bytes", fake_read)
    monkeypatch.setattr(runtime, "_write", trigger)
    with pytest.raises(CompanyStoreError):
        runtime.initialize(
            target,
            source_root=source,
            source_pins=refs,
            as_of="2027-02-03T00:00:00Z",
            target_id="CODE-RACE",
        )
    assert not target.exists()
