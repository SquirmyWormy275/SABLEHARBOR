import copy
import sqlite3

import pytest
from jsonschema import ValidationError

from enterprise.ccf import database
from enterprise.ccf.registry import ROOT, compile_registry, expand, validate


@pytest.fixture(scope="module")
def compiled():
    return compile_registry()


@pytest.fixture
def registry(compiled):
    return copy.deepcopy(compiled)


def item(registry, kind, identifier=None):
    return next(
        r
        for r in registry["records"]
        if r["kind"] == kind and (identifier is None or r["id"] == identifier)
    )


def test_native_population_and_known_gaps_preserved(compiled):
    counts = validate(compiled, ROOT)
    assert counts["control"] == 166 and counts["objective"] == 124 and counts["risk"] == 27
    assert counts["implementation"] == 50 and counts["service"] == 57 and counts["component"] == 49
    assert counts["applicability"] == 1660
    assert {
        r["id"] for r in compiled["records"] if r["kind"] == "control" and not r["data"]["risk_ids"]
    } == {
        "SH-ADV-001",
        "SH-ADV-002",
        "SH-ADV-003",
        "SH-ADV-004",
        "SH-CRD-001",
        "SH-CRD-002",
        "SH-CRD-003",
        "SH-CRD-004",
        "SH-ETH-001",
        "SH-ETH-002",
        "SH-ETH-003",
        "SH-ETH-004",
        "SH-PRD-002",
        "SH-PRD-004",
        "SH-SEC-006",
    }
    assert item(compiled, "provider", "CP-SWITCH")["data"]["contract_state"] == "DRAFT"
    assert item(compiled, "dependency", "DEP-colo-primary")["data"]["provider_id"] == "CP-SWITCH"
    assert len(item(compiled, "implementation", "LC-WORKFORCE")["data"]["boundary_ids"]) == 8


def test_abbreviations_and_ranges_are_lossless():
    assert expand("SH-GOV-001–003, SH-GOV-005/007") == [
        "SH-GOV-001",
        "SH-GOV-002",
        "SH-GOV-003",
        "SH-GOV-005",
        "SH-GOV-007",
    ]
    assert expand("GOV-001/003", "SH-OBJ-") == ["SH-OBJ-GOV-001", "SH-OBJ-GOV-003"]
    for value in ("SH-GOV-003–001", "SH-GOV-001 trailing", "GOV-001", "SH-GOV-001/xyz"):
        with pytest.raises(ValueError):
            expand(value)


@pytest.mark.parametrize(
    "kind,field,value",
    [
        ("control", "objective_ids", ["SH-OBJ-GOV-999"]),
        ("control", "risk_ids", ["SH-RISK-GOV-999"]),
        ("control", "owner_role_id", "ROLE-MISSING"),
        ("implementation", "boundary_ids", ["unknown"]),
        ("service", "component_ids", ["unknown"]),
        ("dependency", "provider_id", "unknown"),
        ("implementation", "operating_assessment", "EFFECTIVE"),
        ("implementation", "evidence_origin", "ACTUAL"),
        ("applicability", "decision_state", "APPROVED"),
        ("implementation", "next_review_due", "bad-date"),
    ],
)
def test_invalid_references_and_promotions_fail(registry, kind, field, value):
    item(registry, kind)["data"][field] = value
    with pytest.raises((ValueError, ValidationError)):
        validate(registry)


def test_unknown_fields_duplicates_missing_fields_fail(registry):
    record = item(registry, "control")
    record["data"]["surprise"] = "unreviewed"
    with pytest.raises(ValidationError):
        validate(registry)
    del record["data"]["surprise"]
    registry["records"].append(copy.deepcopy(record))
    with pytest.raises(ValueError, match="Duplicate record"):
        validate(registry)
    registry["records"].pop()
    del record["data"]["performer_role_id"]
    with pytest.raises(ValidationError):
        validate(registry)


def test_risk_edges_must_agree_both_directions(registry):
    risk = item(registry, "risk")
    risk["data"]["control_ids"].pop()
    with pytest.raises(ValueError, match="traceability"):
        validate(registry)


def test_cycles_review_dates_and_empty_promotions_fail(registry):
    local = item(registry, "implementation")
    local["data"]["inherits_from_id"] = local["id"]
    local["unresolved_fields"].remove("inherits_from_id")
    with pytest.raises(ValueError, match="cycle"):
        validate(registry)
    local["data"]["inherits_from_id"] = None
    local["unresolved_fields"].append("inherits_from_id")
    local["data"]["last_owner_review"] = "2026-12-12"
    local["data"]["next_review_due"] = "2026-12-11"
    local["unresolved_fields"] = [
        f for f in local["unresolved_fields"] if f not in {"last_owner_review", "next_review_due"}
    ]
    with pytest.raises(ValueError, match="chronology"):
        validate(registry)
    local["data"]["next_review_due"] = "2026-12-13"
    item(registry, "control")["status"] = "effective"
    with pytest.raises(ValueError, match="effective"):
        validate(registry)


def test_source_drift_is_rejected(registry):
    registry["source_manifest"]["docs/controls/COMMON_CONTROL_CATALOG_v0.1.md"] = "0" * 64
    with pytest.raises(ValueError, match="Source drift"):
        validate(registry, ROOT)


def test_history_is_immutable_versioned_and_point_in_time(tmp_path, registry):
    with database.connect(tmp_path / "history.sqlite3") as conn:
        first = database.append(conn, registry)
        assert database.append(conn, registry) == first
        assert database.historical(conn, "2026-09-11", "2026-09-10") == []
        selected = item(registry, "control", "SH-GOV-001")
        original = copy.deepcopy(selected)
        selected["version"] = "0.2.0"
        selected["effective_from"] = "2026-10-01"
        selected["recorded_on"] = "2026-09-12"
        selected["data"]["title"] = "Prospective revised title"
        database.append(conn, registry)

        def title(asof, known):
            return next(
                r
                for r in database.historical(conn, asof, known)
                if r["kind"] == "control" and r["id"] == selected["id"]
            )["data"]["title"]

        assert title("2026-09-15", "2026-09-12") == original["data"]["title"]
        assert title("2026-10-02", "2026-09-11") == original["data"]["title"]
        assert title("2026-10-02", "2026-09-12") == "Prospective revised title"
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM record_version")
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()


def test_version_reuse_and_record_disappearance_rollback(tmp_path, registry):
    with database.connect(tmp_path / "history.sqlite3") as conn:
        database.append(conn, registry)
        changed = item(registry, "control", "SH-GOV-001")
        changed["recorded_on"] = "2026-09-12"
        changed["data"]["title"] = "Changed without version"
        with pytest.raises(ValueError, match="new version"):
            database.append(conn, registry)
        assert conn.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0] == 1
        changed["version"] = "0.2.0"
        # An unused role still cannot silently disappear from history.
        registry["records"].append(
            dict(
                kind="role",
                id="ROLE-EXTRA",
                version="0.1.0",
                recorded_on="2026-09-12",
                effective_from="2026-09-12",
                effective_to=None,
                status="draft",
                origin="DERIVED_PREPARATION",
                source_refs=changed["source_refs"],
                unresolved_fields=["appointment_ids"],
                data=dict(
                    title="Synthetic extra role",
                    appointment_ids=[],
                    authority_state="SOURCE_ROLE_LABEL_ONLY",
                ),
            )
        )
        database.append(conn, registry)
        registry["records"].pop()
        changed["version"] = "0.3.0"
        changed["recorded_on"] = "2026-09-13"
        with pytest.raises(ValueError, match="disappear"):
            database.append(conn, registry)


def test_migration_refuses_unowned_database(tmp_path):
    with database.connect(tmp_path / "foreign.sqlite3") as conn:
        conn.execute("CREATE TABLE important_data (id INTEGER)")
        with pytest.raises(ValueError, match="nonempty"):
            database.migrate(conn)


def test_upstream_control_cycles_fail(registry):
    first = item(registry, "control", "SH-GOV-001")
    second = item(registry, "control", "SH-GOV-002")
    first["data"]["upstream_control_ids"] = [second["id"]]
    second["data"]["upstream_control_ids"] = [first["id"]]
    with pytest.raises(ValueError, match="dependency cycle"):
        validate(registry)


def test_incomplete_fields_cannot_be_hidden_from_report(registry):
    row = item(registry, "control", "SH-GOV-001")
    row["unresolved_fields"].remove("performer_role_id")
    with pytest.raises(ValueError, match="Unreported unresolved"):
        validate(registry)
