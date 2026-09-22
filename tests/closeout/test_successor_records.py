"""Finite successor-export identities, routing, source and known-on boundaries."""

import csv
import json
import sqlite3
from copy import deepcopy

import pytest

from enterprise.closeout import successor_records as sr
from enterprise.operations import exports

CONTEXT = dict(
    repository_source_commit="fixture-head",
    repository_source_available_at="2026-09-22T23:00:00Z",
    publication_state="COMMITTED_SOURCE_REVIEWABLE_NOT_RELEASE_ACCEPTANCE",
    publishable_source_snapshot=True,
)


@pytest.fixture(scope="module")
def tables():
    return sr.collect(CONTEXT)


def test_exact_populations_no_cash_and_unchanged_predecessor_contract(tables):
    receipt = sr.validate_tables(tables, CONTEXT)
    assert sum(receipt["counts"].values()) == 260
    assert receipt["counts"]["successor_host_orders"] == 0
    assert receipt["counts"]["successor_asset_screen"] == 149
    assert receipt["counts"]["successor_debt_collateral"] == 64
    assert receipt["additional_cash_usd"] == "0.00"
    schema, scope = sr.contracts()
    old_schema, old_scope = (
        json.loads(exports.SCHEMA.read_text()),
        json.loads(exports.SCOPE.read_text()),
    )
    assert all(schema[name] == fields for name, fields in old_schema.items())
    assert all(scope[name] == rule for name, rule in old_scope.items())
    assert set(schema) - set(old_schema) == set(tables)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda t: t["successor_j2_administration"].pop(),
        lambda t: t["successor_debt_collateral"].append(
            deepcopy(t["successor_debt_collateral"][0])
        ),
        lambda t: t["successor_capital_assents"].clear(),
        lambda t: t.pop("successor_host_orders"),
        lambda t: t["successor_host_instruments"][0].update(entity="ARU"),
        lambda t: t["successor_debt_payoff"][0].update(entity="BST"),
        lambda t: t["successor_asset_screen"][0].update(entity="UNRESOLVED"),
        lambda t: t["successor_capital_rights"][0].update(available_at="2026-09-22T00:00:00Z"),
        lambda t: t["successor_capital_rights"][0].update(payload_json="{}"),
        lambda t: t["successor_debt_collateral"][0].update(source_sha256="0" * 64),
        lambda t: t["successor_debt_payoff"][0].update(additional_cash_usd="13500000.00"),
    ],
)
def test_corruption_rejected(tables, mutation):
    changed = deepcopy(tables)
    mutation(changed)
    with pytest.raises(ValueError):
        sr.validate_tables(changed, CONTEXT)


def test_known_on_and_effective_period_are_separate(tables):
    earlier = sr.visible(tables, effective_on="2026-10-02", known_on="2026-09-22T22:59:59Z")
    assert all(not rows for rows in earlier.values())
    current = sr.visible(tables, effective_on="2026-09-22", known_on="2026-09-22T23:00:00Z")
    assert len(current["successor_capital_rights"]) == 2
    assert current["successor_host_instruments"] == []
    later = sr.visible(tables, effective_on="2026-10-01", known_on="2026-09-22T23:00:00Z")
    assert len(later["successor_host_instruments"]) == 2
    expired = sr.visible(tables, effective_on="2027-02-02", known_on="2027-02-02T23:00:00Z")
    assert len(expired["successor_orientation_commissions"]) == 15
    preview = sr.collect(
        CONTEXT | {"publication_state": "DIRTY_WORKING_COPY_PREVIEW_NOT_PUBLISHABLE"}
    )
    assert all(
        not rows
        for rows in sr.visible(
            preview, effective_on="2026-10-01", known_on="2026-09-23T00:00:00Z"
        ).values()
    )


def test_real_shared_writer_csv_and_sqlite_preserve_complete_payloads(tmp_path, tables):
    schema, _ = sr.contracts()
    subset = {name: schema[name] for name in tables}
    database = tmp_path / "enterprise.sqlite3"
    exports.database(database, tables, subset)
    exports.verify_database(database, tables, subset)
    with sqlite3.connect(database) as connection:
        for name, rows in tables.items():
            exports.csv_table(tmp_path / (name + ".csv"), rows, subset[name])
            with (tmp_path / (name + ".csv")).open(newline="") as stream:
                emitted = list(csv.DictReader(stream))
            assert emitted == rows
            assert connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] == len(rows)
    assets = tables["successor_asset_screen"]
    assert any(row["entity"] == "UNRESOLVED" for row in assets)
    assert any(row["entity"] == "EXTERNAL" for row in assets)
