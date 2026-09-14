import json
from dataclasses import replace

import pytest

from enterprise.audit_suite.company_change_activity import generate_pair
from enterprise.audit_suite.company_configuration_activity import (
    ConfigurationRecipe,
    generate,
    read_originals,
)
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from tests.audit_suite.test_company_change_activity import ROOT, rows
from tests.audit_suite.test_company_change_activity import recipe as change_recipe


@pytest.fixture
def inputs(tmp_path):
    tmp_path.chmod(0o700)
    source = tmp_path / "source"
    generate_pair(source, repository=ROOT, recipe=change_recipe())
    originals, pin = read_originals(source)
    r = ConfigurationRecipe(
        "SH",
        "original-change-source",
        pin,
        ("release-a", "release-b"),
        ("2027-02-01T12:30:00Z", "2027-02-01T14:00:00Z"),
        "LOCAL-CONFIG-TARGET",
    )
    return source, r, originals


def test_actual_release_approval_drift_and_corrected_snapshots(tmp_path, inputs):
    source, r, originals = inputs
    receipt = generate(tmp_path / "cfg", repository=ROOT, source_root=source, recipe=r)
    store = CompanyStore(tmp_path / "cfg")
    values = rows(store)
    drift = {}
    for (branch, _), row in values.items():
        assert sha(row["content"]) == row["sha256"]
        body = json.loads(row["content"])
        assert body["owner_id"] == "AS-P007" and body["operating_reviewer_id"] == "AS-P008"
        if row["system"] == "configuration_drift":
            drift[branch, body["observed_at"]] = body
        if row["system"] == "configuration_desired":
            assert body["approval"]["available_at"] <= row["available_at"]
            exact = next(
                x
                for x in originals
                if x["branch"] == branch and x["record"] == body["approval"]["record_id"]
            )
            assert body["approval"]["sha256"] == exact["sha256"]
            assert json.loads(exact["content"])["decision"] == "APPROVED"
    first = "2027-02-01T12:30:00.000000+00:00"
    second = "2027-02-01T14:00:00.000000+00:00"
    assert drift["release-a", first]["matches_approved_desired"]
    assert drift["release-b", first]["field_differences"] == [
        {"field": "timeout_ms", "actual": 50, "desired": 40}
    ]
    assert (
        drift["release-b", first]["actual_local_calculation"]["calculated_total_timeout_ms"] == 150
    )
    assert all(drift[b, second]["matches_approved_desired"] for b in r.branch_ids)
    assert len(values) == 12
    assert read_originals(source) == (originals, r.source_versions_sha256)
    assert receipt["not_exercised"] == ["SH-CFG-003", "SH-CFG-004"]
    with store._db() as db:
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0
    with pytest.raises(CompanyStoreError):
        generate(tmp_path / "cfg", repository=ROOT, source_root=source, recipe=r)
    assert rows(store) == values


@pytest.mark.parametrize(
    "change",
    [
        {"source_versions_sha256": "wrong"},
        {"checkpoints": ("2027-02-01T08:00:00Z",)},
        {"branch_ids": ("unknown",)},
        {"checkpoints": ("2027-02-01T14:00:00Z", "2027-02-01T12:30:00Z")},
    ],
)
def test_missing_future_or_changed_inputs_never_publish(tmp_path, inputs, change):
    source, r, _ = inputs
    with pytest.raises(CompanyStoreError):
        generate(tmp_path / "cfg", repository=ROOT, source_root=source, recipe=replace(r, **change))
    assert not (tmp_path / "cfg").exists()


def test_source_append_invalidates_frozen_input_and_alias_denied(tmp_path, inputs):
    source, r, _ = inputs
    store = CompanyStore(source)
    store.register_system("SH", "release-a", "extra", "P005")
    store.append_version(
        "SH",
        "release-a",
        "extra",
        "new",
        expected_version=0,
        command_id="new",
        event_at="2027-02-01T01:00:00Z",
        available_at="2027-02-01T01:00:00Z",
        content=encoded({"extra": "original"}),
        provenance={"source_reference": "new"},
    )
    with pytest.raises(CompanyStoreError, match="Frozen"):
        generate(tmp_path / "cfg", repository=ROOT, source_root=source, recipe=r)
    alias = tmp_path / "alias"
    alias.symlink_to(source, target_is_directory=True)
    with pytest.raises(CompanyStoreError):
        read_originals(alias)


def test_wal_append_between_size_check_and_read_uses_one_snapshot(inputs, monkeypatch):
    import sqlite3

    from enterprise.audit_suite import company_configuration_activity as module

    source, _, originals = inputs
    native_connect = sqlite3.connect
    writer = native_connect(source / "company.sqlite3")
    writer.execute("PRAGMA journal_mode=WAL")
    limit = sum(len(row["content"]) for row in originals) + 1000
    monkeypatch.setattr(module, "MAX_SOURCE_BYTES", limit)
    appended = False

    class InterleavedConnection(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            nonlocal appended
            result = super().execute(sql, *args, **kwargs)
            if sql.startswith("SELECT COUNT(*)") and not appended:
                assert self.in_transaction
                assert super().execute("PRAGMA query_only").fetchone()[0] == 1
                # Count SELECT has established a WAL snapshot; a second connection can
                # commit new native bytes before the first connection reads originals.
                old = writer.execute("SELECT * FROM versions LIMIT 1").fetchone()
                columns = [x[1] for x in writer.execute("PRAGMA table_info(versions)")]
                new = dict(zip(columns, old, strict=True))
                new.update(
                    record="CONCURRENT",
                    content=b"x" * 2000,
                    sha256=sha(b"x" * 2000),
                    command_id="concurrent",
                    input_digest="new",
                )
                writer.execute(
                    "INSERT INTO versions VALUES (" + ",".join("?" for _ in columns) + ")",
                    tuple(new[c] for c in columns),
                )
                writer.commit()
                appended = True
            return result

    def connect(*args, **kwargs):
        return native_connect(*args, **kwargs, factory=InterleavedConnection)

    monkeypatch.setattr(module.sqlite3, "connect", connect)
    try:
        current, _ = read_originals(source)
        assert appended and current == originals
        with pytest.raises(CompanyStoreError, match="Bounded"):
            read_originals(source)  # New transaction sees the larger committed set.
    finally:
        writer.close()


def test_hardlink_and_nested_destination_are_rejected_without_source_changes(tmp_path, inputs):
    import os

    source, recipe, originals = inputs
    nested = source / "derived"
    with pytest.raises(CompanyStoreError, match="outside original"):
        generate(nested, repository=ROOT, source_root=source, recipe=recipe)
    assert not nested.exists() and read_originals(source)[0] == originals
    alias = tmp_path / "hardlinked-db"
    os.link(source / "company.sqlite3", alias)
    with pytest.raises(CompanyStoreError):
        read_originals(source)
    alias.unlink()
    assert read_originals(source)[0] == originals


def collect_configuration_pair(company_root, audit_root, *, change_root, recipe, program_pack=None):
    """Separate actual Engine collection; all upstream and retained source versions stay pinned."""
    from enterprise.audit_suite.company_collection import discover
    from enterprise.audit_suite.engine import Engine
    from enterprise.audit_suite.store import DomainError, canonical

    original_rows, config_pin = read_originals(company_root)
    upstream_rows, upstream_pin = read_originals(change_root)
    assert upstream_pin == recipe.source_versions_sha256
    original_index = {
        (r["branch"], r["system"], r["record"], r["version"]): r for r in original_rows
    }
    upstream_index = {
        (r["company"], r["branch"], r["system"], r["record"], r["version"]): r
        for r in upstream_rows
    }

    def refs(value):
        if isinstance(value, dict):
            if "source_store_id" in value and "record_id" in value and "sha256" in value:
                yield value
            for v in value.values():
                yield from refs(v)
        elif isinstance(value, list):
            for v in value:
                yield from refs(v)

    source = CompanyStore(company_root)
    engine = Engine(
        audit_root, repository=ROOT, company_root=company_root, program_pack=program_pack
    )
    operator = engine.store.provision("Isolated configuration collection operator", ["instructor"])[
        "id"
    ]
    actor = engine.store.provision("Isolated configuration collection learner", ["learner"])["id"]
    results = []
    for branch in recipe.branch_ids:
        state = engine.create(
            operator,
            {
                "command_id": "cfg-create-" + branch,
                "title": "Local configuration source collection",
                "discipline": "IT",
                "mode": "CLEAN",
                "configuration": {"selections": []},
                "scope": {
                    "programs": ["SOC2"],
                    "report_type": "Type 2",
                    "period_start": "2027-02-01",
                    "period_end": "2027-02-02",
                    "fieldwork_start": "2027-02-01",
                    "timezone": "UTC",
                    "boundaries": ["corporate"],
                    "trust_services_categories": ["Security"],
                    "control_ids": ["SH-CFG-001", "SH-CFG-002"],
                },
            },
        )
        engine.store.grant(state["id"], actor, "learn")
        engine.company_bindings[state["id"]] = {"company": recipe.company_id, "branch": branch}
        available_rows = [r for r in original_rows if r["branch"] == branch]
        systems = sorted({r["system"] for r in available_rows})
        for system in systems:
            source.grant(actor, state["id"], recipe.company_id, branch, system)
        serial = 0

        def command(kind, payload, principal=actor, branch=branch):
            nonlocal state, serial
            serial += 1
            envelope = {
                "command_id": "cfg-" + branch + "-" + str(serial),
                "expected_revision": state["revision"],
                "kind": kind,
                "payload": payload,
            }
            state = engine.command(principal, state["id"], envelope)
            return envelope

        command("company.activate", {}, operator)
        command("kickoff.start", {})
        requests = {}
        for control in state["controls"]:
            command(
                "pbc.create",
                {
                    "title": "Original configuration records " + control["id"],
                    "purpose": (
                        "Inspect local inventory and approved desired-state comparison only."
                    ),
                    "control_id": control["id"],
                    "person_id": control["assignment"]["primary_person_id"],
                    "boundary_id": "corporate",
                },
            )
            request = state["requests"][-1]["id"]
            requests[control["id"]] = request
            command("pbc.issue", {"request_id": request})
        future = max(available_rows, key=lambda r: r["available_at"])
        before = state["revision"]
        with pytest.raises(DomainError):
            engine.command(
                actor,
                state["id"],
                {
                    "command_id": "future",
                    "expected_revision": before,
                    "kind": "company.collect",
                    "payload": {
                        "system_id": future["system"],
                        "record_id": future["record"],
                        "version": future["version"],
                        "request_id": requests["SH-CFG-002"],
                    },
                },
            )
        assert engine.store.get(actor, state["id"])["revision"] == before
        collected = []
        seen = set()
        checkpoints = []
        for checkpoint in recipe.checkpoints:
            command("clock.advance", {"mode": "TARGET_DATE", "target": checkpoint})
            for system in systems:
                for item in discover(engine, actor, state["id"], system, limit=1000)["records"]:
                    key = (branch, system, item["record"], item["version"])
                    if key in seen:
                        continue
                    original = original_index[key]
                    cid = json.loads(original["provenance"])["control_ids"][0]
                    envelope = command(
                        "company.collect",
                        {
                            "system_id": system,
                            "record_id": item["record"],
                            "version": item["version"],
                            "request_id": requests[cid],
                        },
                    )
                    assert canonical(engine.command(actor, state["id"], envelope)) == canonical(
                        state
                    )
                    artifact = state["artifacts"][-1]
                    native = engine.artifacts.read(artifact)
                    assert (
                        native == original["content"] and artifact["sha256"] == original["sha256"]
                    )
                    dependencies = list(refs(json.loads(native)))
                    for ref in dependencies:
                        assert ref["source_store_id"] == recipe.source_store_id
                        upstream = upstream_index[
                            ref["company_id"],
                            ref["branch_id"],
                            ref["system_id"],
                            ref["record_id"],
                            ref["version"],
                        ]
                        assert upstream["sha256"] == ref["sha256"]
                        assert upstream["available_at"] <= original["available_at"]
                    collected.append(
                        {
                            "record_id": item["record"],
                            "artifact_id": artifact["id"],
                            "sha256": artifact["sha256"],
                            "upstream_references": dependencies,
                        }
                    )
                    seen.add(key)
            checkpoints.append({"at": checkpoint, "collected": len(collected)})
        assert len(collected) == len(available_rows) == 6
        assert not (audit_root / "worlds" / state["id"]).exists()
        assert not state["workpapers"] and not state["findings"] and not state["populations"]
        assert all(t["status"] == "NOT_STARTED" for t in state["tasks"])
        for system in systems:
            source.grant(actor, state["id"], recipe.company_id, branch, system, active=False)
        results.append(
            {
                "branch": branch,
                "engagement_id": state["id"],
                "revision": state["revision"],
                "checkpoints": checkpoints,
                "collected": collected,
                "future_denied": True,
                "every_replay_identical": True,
                "no_model_world_or_testing_credit": True,
            }
        )
    assert read_originals(company_root) == (original_rows, config_pin)
    assert read_originals(change_root) == (upstream_rows, upstream_pin)
    return {
        "status": "PASS",
        "branches": results,
        "configuration_versions_sha256": config_pin,
        "change_versions_sha256": upstream_pin,
        "all_versions_unchanged": True,
        "temporary_grants_revoked": True,
    }


def test_actual_paired_configuration_collection(tmp_path, inputs):
    source, r, _ = inputs
    generate(tmp_path / "cfg", repository=ROOT, source_root=source, recipe=r)
    receipt = collect_configuration_pair(
        tmp_path / "cfg", tmp_path / "audit", change_root=source, recipe=r
    )
    assert receipt["status"] == "PASS"
    assert all(
        [c["collected"] for c in branch["checkpoints"]] == [3, 6] for branch in receipt["branches"]
    )
