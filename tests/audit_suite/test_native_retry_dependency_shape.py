"""Original native pointer formats, fresh local execution, and no append on refusal."""

import pytest

from enterprise.audit_suite import company_operating_depth_runtime as depth
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError, _time
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from enterprise.audit_suite.source_library_audit import typed_content
from tests.audit_suite.test_company_operating_depth_runtime import original, setup_declaration

EARLY = _time("2027-01-01T00:00:00Z")
AT = _time("2027-04-06T00:00:00Z")


def fixture(tmp_path, *, full=True, fault=None):
    root = tmp_path / "native-business"
    root.mkdir(mode=0o700)
    store = CompanyStore(root)
    values = dict(timeout_ms=40, attempts=3, max_total_ms=120)
    config = original(
        store,
        "change-history.configurations",
        "CONFIG-CORRECTED",
        dict(configuration=values, configuration_sha256=sha(encoded(values))),
        owner="P005",
    )

    def reference(pin, target):
        row = dict(
            system_id=pin["system"],
            record_id=pin["record"],
            version=pin["version"],
            sha256=pin["sha256"],
            available_at=EARLY,
        )
        if full:
            row.update(company_id=pin["company"], branch_id=pin["branch"], event_at=EARLY)
        if fault and fault[0] == target:
            field, value = fault[1:]
            if field == "DELETE":
                del row[value]
            else:
                row[field] = value
        return row

    package = dict(format="LOCAL_CONFIG_PACKAGE_V1", configuration=values)
    build = original(
        store,
        "change-history.builds",
        "BUILD-CORRECTED",
        dict(
            package=package, package_sha256=sha(encoded(package)), source=reference(config, "build")
        ),
        owner="P005",
    )
    test = original(
        store,
        "change-history.tests",
        "TEST-CORRECTED",
        dict(artifact=reference(build, "test")),
        owner="P005",
    )
    declaration, _ = setup_declaration(store, "RETRY")
    args = dict(
        declaration_pin=declaration,
        slot_id="LOCAL:0",
        configuration_pin=config,
        build_pin=build,
        test_pin=test,
        actor_id="P005",
        command_id="OWN-RETRY",
        event_at=AT,
    )
    return store, args, (config, build, test)


@pytest.mark.parametrize("full", [False, True])
def test_literal_five_and_eight_field_originals_execute_collect_and_replay(tmp_path, full):
    store, args, pins = fixture(tmp_path, full=full)
    with store._db() as db:
        old = [dict(depth.selected(db, p, AT)[0]) for p in pins]
    result = depth.retry_probe(store, **args)
    before = store.path.read_bytes()
    assert depth.retry_probe(store, **args) == result
    assert store.path.read_bytes() == before
    with store._db() as db:
        assert [dict(depth.selected(db, p, AT)[0]) for p in pins] == old
    observation = depth.inspect(store, declaration_pin=args["declaration_pin"], as_of=AT)["slots"][
        0
    ]["history"][0]["observation"]
    assert observation["calculation"]["calculated_total_timeout_ms"] == 120
    assert observation["status"] == "PASS_LOCAL_RETRY_CRITERION"
    assert observation["security_privacy_pipeline_tests"] == "NOT_EXECUTED_BY_THIS_MODEL"
    # Business execution occurs before any source access is granted to the new local audit.
    store.grant("OWN-AUDITOR", "OWN-AUDIT-AFTER-RETRY", "SH", "depth-owned", depth.SYSTEM)
    row = store.read_version(
        "OWN-AUDITOR",
        "OWN-AUDIT-AFTER-RETRY",
        "SH",
        "depth-owned",
        depth.SYSTEM,
        result["record"],
        version=1,
        as_of=AT,
    )
    receipt = store.collect(
        "OWN-AUDITOR",
        "OWN-AUDIT-AFTER-RETRY",
        "SH",
        "depth-owned",
        depth.SYSTEM,
        result["record"],
        version=1,
        as_of=AT,
        command_id="OWN-COLLECT-RETRY",
    )
    data, mime = typed_content(row)
    assert mime == "application/json" and data["observation"] == observation
    assert sha(row["content"]) == result["sha256"] == receipt["source"]["sha256"]


@pytest.mark.parametrize(
    "fault",
    [
        ("build", "company_id", "FOREIGN"),
        ("test", "company_id", "FOREIGN"),
        ("build", "branch_id", "OTHER"),
        ("test", "branch_id", "OTHER"),
        ("build", "event_at", "2027-01-02T00:00:00Z"),
        ("test", "event_at", "2027-01-02T00:00:00Z"),
        ("build", "event_at", True),
        ("test", "DELETE", "branch_id"),
        ("build", "unknown", "not admitted"),
        ("test", "version", True),
        ("build", "system_id", "configurations"),
        ("test", "sha256", "0" * 64),
        ("build", "available_at", "2027-01-02T00:00:00Z"),
        ("test", "record_id", "OTHER-BUILD"),
    ],
)
def test_native_scope_clock_shape_and_exact_pointer_refuse_without_append(tmp_path, fault):
    store, args, _ = fixture(tmp_path, fault=fault)
    before = store.path.read_bytes()
    with pytest.raises(CompanyStoreError, match="Exact original dependency differs"):
        depth.retry_probe(store, **args)
    assert store.path.read_bytes() == before
    with store._db() as db:
        assert (
            db.execute("SELECT COUNT(*) FROM versions WHERE system=?", (depth.SYSTEM,)).fetchone()[
                0
            ]
            == 0
        )


def test_partial_native_fields_do_not_broaden_legacy_schema(tmp_path):
    store, args, _ = fixture(tmp_path, full=False, fault=("build", "company_id", "SH"))
    before = store.path.read_bytes()
    with pytest.raises(CompanyStoreError, match="Exact original dependency differs"):
        depth.retry_probe(store, **args)
    assert store.path.read_bytes() == before
