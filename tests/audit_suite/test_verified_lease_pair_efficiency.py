"""Actual candidate classes against two-record temporary NEUTRAL worlds only."""

import ast
from dataclasses import replace
from pathlib import Path
from types import MethodType, SimpleNamespace

import pytest

from enterprise.audit_suite import full_scope_company_pair as pair_module
from enterprise.audit_suite import persistent_company_journey as runtime
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.source_library_audit import AcceptedLibrary, LibraryAudit, file_sha
from tests.audit_suite.test_persistent_company_journey import source
from tests.audit_suite.test_persistent_company_verification_performance import _change_original


@pytest.fixture
def world(tmp_path):
    tmp_path.chmod(0o700)
    return runtime.PersistentCompany.initialize(
        source(tmp_path / "accepted-neutral"),
        tmp_path / "world-neutral",
        operator_id="COMPANY-OPERATOR-NEUTRAL",
        engineering_only=True,
    )


@pytest.fixture
def pair(world, tmp_path, monkeypatch):
    pack = tmp_path / "FICTIONAL_TEST_PROGRAM.json"
    pack.write_text('{"engineering_neutral_fixture":true}\n')
    pack.chmod(0o600)
    monkeypatch.setattr(pair_module, "PROGRAM_SHA", file_sha(pack))
    result = pair_module.FullScopePair.__new__(pair_module.FullScopePair)
    result.world, result.pins = world, dict(world.pins)
    result.program_pack, result.engineering_only = pack, True
    return result


def counted(world, monkeypatch):
    calls = {"accepted_full_scans": 0, "world_full_scans": 0}
    accepted_verify, world_verify = AcceptedLibrary.verify, world.verify

    def accepted(self):
        calls["accepted_full_scans"] += 1
        return accepted_verify(self)

    def verify():
        calls["world_full_scans"] += 1
        return world_verify()

    monkeypatch.setattr(AcceptedLibrary, "verify", accepted)
    monkeypatch.setattr(world, "verify", verify)
    return calls


def read(world, actor="NEUTRAL-AUDITOR"):
    return world.store.read_version(
        actor,
        "NEUTRAL-ENGAGEMENT",
        "NEUTRAL-COMPANY",
        "ALPHA",
        "operations.events",
        "event-one",
        version=1,
        as_of="2027-01-03T00:00:00Z",
    )


def grant(world, active=True):
    world.store.grant(
        "NEUTRAL-AUDITOR",
        "NEUTRAL-ENGAGEMENT",
        "NEUTRAL-COMPANY",
        "ALPHA",
        "operations.events",
        active=active,
    )


def test_twenty_real_pair_checks_and_point_reads_have_only_entry_exit_full_scans(
    world,
    pair,
    monkeypatch,
):
    grant(world)
    calls = counted(world, monkeypatch)
    with world.verified_sources():
        for _ in range(20):
            pair.check()
            assert read(world)["version"] == 1
    assert calls == {"accepted_full_scans": 2, "world_full_scans": 2}
    pair.check()
    assert calls == {"accepted_full_scans": 4, "world_full_scans": 3}
    assert world._local.verified_source_binding is None


def test_each_new_lease_gets_fresh_full_verification(world, pair, monkeypatch):
    calls = counted(world, monkeypatch)
    for _ in range(3):
        with world.verified_sources():
            for _ in range(5):
                pair.check()
    assert calls == {"accepted_full_scans": 6, "world_full_scans": 6}


def test_saved_original_check_vs_candidate_on_identical_fictional_point_reads(
    world,
    pair,
    monkeypatch,
):
    # Compile only the saved parent method literal into repository globals.
    # No external original source file or workstation path is needed.
    # Saved parent check text; original whole-file SHA256:
    # 1327acb4551c0b29d9a720fac0e24ede006c830dba4a866604553ad59f9f61d0
    original_check = (
        "def check(self):\n"
        '    require(self.world.accepted.verify() == self.pins, "Accepted baseline changed")\n'
        '    require(file_sha(self.program_pack) == PROGRAM_SHA, "Retained program pack changed")\n'
        "    self.world.require_runtime()\n"
        "    if not self.engineering_only:\n"
        "        adapter_gate(self.adapter_review.path, self.adapter_review.sha256, self.pins)\n"
        "        require_pair_gate(\n"
        "            self.pair_review,\n"
        "            self.pins,\n"
        "            self.routes_by_mode,\n"
        "            expected_scope=self.expected_scope,\n"
        "        )\n"
    )
    method = ast.parse(original_check).body[0]
    namespace = dict(vars(pair_module))
    exec(
        compile(
            ast.Module(body=[method], type_ignores=[]), "<saved-original-check-source-only>", "exec"
        ),
        namespace,
    )
    grant(world)
    calls = counted(world, monkeypatch)
    candidate_check = pair.check
    pair.check = MethodType(namespace["check"], pair)
    with world.verified_sources():
        for _ in range(20):
            pair.check()
            assert read(world)["version"] == 1
    assert calls == {"accepted_full_scans": 22, "world_full_scans": 2}
    calls.update(accepted_full_scans=0, world_full_scans=0)
    pair.check = candidate_check
    with world.verified_sources():
        for _ in range(20):
            pair.check()
            assert read(world)["version"] == 1
    assert calls == {"accepted_full_scans": 2, "world_full_scans": 2}


def test_pair_outside_lease_refuses_changed_accepted_bytes(world, pair):
    _change_original(world.accepted.database)
    with pytest.raises(ProcedureError, match="Accepted library pin changed"):
        pair.check()


def test_lease_closing_refuses_changed_accepted_bytes_even_after_reused_pair_check(world, pair):
    with pytest.raises(ProcedureError, match="Accepted library pin changed"):
        with world.verified_sources():
            _change_original(world.accepted.database)
            pair.check()
    assert not world._local.verified_sources
    assert world._local.verified_source_binding is None


def test_pair_pin_mismatch_cannot_use_world_lease(world, pair):
    pair.pins = {**pair.pins, "version_count": 999}
    with world.verified_sources():
        with pytest.raises(ProcedureError, match="Accepted baseline changed"):
            pair.check()


def test_equal_but_replaced_accepted_object_is_refused_and_closing_still_verifies(
    world,
    pair,
    monkeypatch,
):
    calls = counted(world, monkeypatch)
    with pytest.raises(ProcedureError, match="Exact locked world"):
        with world.verified_sources():
            world.accepted = replace(world.accepted)
            pair.check()
    assert calls["world_full_scans"] == 2
    assert not world._local.verified_sources and world._local.verified_source_binding is None


def test_base_exception_at_closing_clears_lease_and_preserves_fresh_full_checks(
    world,
    pair,
    monkeypatch,
):
    calls = counted(world, monkeypatch)
    original = world.verify_accepted_pins
    failure = KeyboardInterrupt("fictional cancellation at closing boundary")

    def cancel():
        raise failure

    with pytest.raises(KeyboardInterrupt) as caught:
        with world.verified_sources():
            pair.check()
            token = world._local.verified_source_binding
            assert all(type(value) in (str, int, bool) for value in token[2].values())
            with pytest.raises(TypeError):
                token[2]["version_count"] = 999
            returned = world.verify_accepted_pins()
            returned["version_count"] = 999
            assert world.verify_accepted_pins() == world.pins
            monkeypatch.setattr(world, "verify_accepted_pins", cancel)
    assert caught.value is failure
    assert not world._local.verified_sources
    assert world._local.verified_source_binding is None
    assert calls == {"accepted_full_scans": 2, "world_full_scans": 2}
    monkeypatch.setattr(world, "verify_accepted_pins", original)
    world.require_runtime()
    assert calls == {"accepted_full_scans": 3, "world_full_scans": 3}
    with world.verified_sources():
        pair.check()
    assert calls == {"accepted_full_scans": 5, "world_full_scans": 5}


def test_changed_world_pins_are_refused_inside_lease(world, pair):
    original = world.pins
    with world.verified_sources():
        try:
            world.pins = {**original, "version_count": 999}
            with pytest.raises(ProcedureError, match="Exact locked world"):
                pair.check()
        finally:
            world.pins = original


def test_cross_world_does_not_inherit_lease_and_transplanted_token_is_refused(
    world,
    pair,
    tmp_path,
    monkeypatch,
):
    other = runtime.PersistentCompany.initialize(
        world.accepted,
        tmp_path / "other-neutral-world",
        operator_id="OTHER-COMPANY-OPERATOR-NEUTRAL",
        engineering_only=True,
    )
    calls = counted(world, monkeypatch)
    with world.verified_sources():
        pair.world = other
        before = calls["accepted_full_scans"]
        pair.check()
        assert calls["accepted_full_scans"] == before + 2
        with other.locked():
            other._local.verified_sources = True
            other._local.verified_source_binding = world._local.verified_source_binding
            try:
                with pytest.raises(ProcedureError, match="Exact locked world"):
                    pair.check()
            finally:
                other._local.verified_sources = False
                other._local.verified_source_binding = None
        pair.world = world


def test_private_boolean_alone_does_not_enable_lease_reuse(world, pair):
    with world.locked():
        world._local.verified_sources = True
        try:
            with pytest.raises(ProcedureError, match="Exact locked world"):
                pair.check()
            with pytest.raises(ProcedureError, match="Exact locked world"):
                world.require_runtime()
        finally:
            world._local.verified_sources = False


def test_current_acl_actor_and_clock_checks_stay_fresh_inside_lease(world, pair):
    with world.verified_sources():
        grant(world)
        pair.check()
        assert read(world)["content"]
        with pytest.raises(CompanyStoreError, match="unauthorized"):
            read(world, actor="OTHER-NEUTRAL-AUDITOR")
        with pytest.raises(CompanyStoreError, match="unavailable"):
            world.store.read_version(
                "NEUTRAL-AUDITOR",
                "NEUTRAL-ENGAGEMENT",
                "NEUTRAL-COMPANY",
                "ALPHA",
                "operations.events",
                "event-one",
                version=1,
                as_of="2027-01-01T00:00:00Z",
            )
        grant(world, active=False)
        with pytest.raises(CompanyStoreError, match="unauthorized"):
            read(world)


def test_same_lease_does_not_bypass_original_audit_context_actor_guard(world, pair):
    audit = LibraryAudit.__new__(LibraryAudit)
    audit.engine = SimpleNamespace(company_store=world.store)
    audit.engagement, audit.identities = "NEUTRAL-ENGAGEMENT", {"auditor": "NEUTRAL-AUDITOR"}
    with world.verified_sources():
        pair.check()
        with pytest.raises(ProcedureError, match="Actual bound Engine engagement"):
            audit._context(audit.engine, "OTHER-NEUTRAL-AUDITOR", audit.engagement)


def test_point_record_body_hash_stays_fresh_inside_lease(world, pair):
    import sqlite3
    from contextlib import closing

    with pytest.raises(ProcedureError, match="Accepted company history was changed"):
        with world.verified_sources():
            grant(world)
            with closing(sqlite3.connect(world.database)) as db:
                trigger = db.execute(
                    "SELECT sql FROM sqlite_master WHERE name='no_version_update'"
                ).fetchone()[0]
                db.execute("DROP TRIGGER no_version_update")
                db.execute(
                    "UPDATE versions SET content=? WHERE branch='ALPHA'", (b'{"changed":true}',)
                )
                db.execute(trigger)
                db.commit()
            pair.check()
            with pytest.raises(CompanyStoreError, match="Source integrity failure"):
                read(world)


def test_candidate_import_origins_are_isolated():
    root = Path(__file__).resolve().parents[2]
    assert Path(runtime.__file__).is_relative_to(root)
    assert Path(pair_module.__file__).is_relative_to(root)
