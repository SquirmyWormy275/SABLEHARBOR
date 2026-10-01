"""A whole company library stays native, typed, bounded, and isolated from audit answers."""

import copy
import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from enterprise.audit_suite import company_operational_library_projection_v3 as source
from enterprise.audit_suite.company_collection import discover
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from enterprise.audit_suite.store import DomainError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


@pytest.fixture(scope="module")
def sealed_library(tmp_path_factory):
    parent = tmp_path_factory.mktemp("operational-library")
    root = parent / "initialized"
    source.create(root, repository=REPOSITORY, private_repository=PRIVATE)
    return root


@pytest.fixture
def created(tmp_path, sealed_library):
    root = tmp_path / "library"
    root.mkdir(mode=0o700)
    for p in sealed_library.iterdir():
        shutil.copyfile(p, root / p.name)
        (root / p.name).chmod(0o600)
    return root


def _verify(root):
    return source.verify(root, repository=REPOSITORY, private_repository=PRIVATE)


def _reseal(root):
    path = root / "MANIFEST.json"
    value = json.loads(path.read_text())
    value["files"] = {name: source._digest(root / name) for name in value["files"]}
    path.write_text(json.dumps(value))


def _mutate(root, change):
    with closing(sqlite3.connect(root / "company.sqlite3")) as db, db:
        db.row_factory = sqlite3.Row
        trigger = db.execute(
            "SELECT sql FROM sqlite_master WHERE name='no_version_update'"
        ).fetchone()[0]
        db.execute("DROP TRIGGER no_version_update")
        change(db)
        for row in db.execute("SELECT * FROM versions").fetchall():
            fingerprint = sha(
                encoded(
                    [
                        [row[k] for k in ("company", "branch", "system", "record")],
                        row["version"] - 1,
                        row["event_at"],
                        row["available_at"],
                        row["origin"],
                        json.loads(row["provenance"]),
                        row["sha256"],
                    ]
                )
            )
            if fingerprint != row["input_digest"]:
                db.execute(
                    "UPDATE versions SET input_digest=? WHERE command_id=?",
                    (fingerprint, row["command_id"]),
                )
        current = {
            tuple(row[k] for k in ("company", "branch", "system", "record", "version")): dict(row)
            for row in db.execute("SELECT * FROM versions")
        }
        db.execute(trigger)
    receipt_path = root / "RECEIPT.json"
    receipt = json.loads(receipt_path.read_text())
    from enterprise.audit_suite.company_store import CompanyStore

    receipt["records"] = [
        CompanyStore._metadata(
            current[tuple(ref[k] for k in ("company", "branch", "system", "record", "version"))]
        )
        for ref in receipt["records"]
    ]
    receipt_path.write_text(json.dumps(receipt))
    _reseal(root)


def _at(value, pointer):
    for part in pointer.lstrip("/").split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def _original_at(row, pointer):
    prefix = "/@operational_metadata"
    if pointer.startswith(prefix + "/"):
        return _at(json.loads(row["provenance"]), pointer[len(prefix) :])
    return _at(row["body"], pointer)


def _published_at(row, pointer, plan):
    prefix = "/@operational_metadata"
    if pointer.startswith(prefix + "/"):
        value = json.loads(row["provenance"])["operational_metadata"]
        pieces = pointer[len(prefix) + 1 :].split("/")
        pieces[0] = plan.get("metadata_rename_keys", {}).get(pieces[0], pieces[0])
        pieces[-1] = plan["rename_keys"].get(pointer, pieces[-1])
        return _at(value, "/" + "/".join(pieces))
    return _at(json.loads(row["content"]), pointer)


def test_every_original_provenance_leaf_has_exact_declared_custody(sealed_library):
    registry = source._registry(REPOSITORY)
    _, _, originals, _ = source._inputs(registry, PRIVATE)
    inventory = json.loads(
        (
            REPOSITORY
            / "enterprise/generated/audit-suite/company-operational-library-2026-10-01"
            / "V3-PROVENANCE-LEAF-INVENTORY.json"
        ).read_bytes()
    )
    assert sha(encoded(inventory)) == registry["provenance_field_classification_sha256"]
    native = _native(sealed_library)
    by_projection = {}
    for item in inventory:
        by_projection.setdefault(item["projection_id"], []).append(item)
        assert item["raw_value"] == _at(
            json.loads(originals[item["input_id"]]["provenance"]), item["path"]
        )
        assert item["decision"].startswith(("PRESERVE_", "PRIVATE_", "SUPERSEDED_", "OPERATIONAL_"))
    checked = 0
    for plan in registry["records"]:
        original = json.loads(originals[plan["input_id"]]["provenance"])
        expected = []

        def walk(value, pointer, expected=expected):
            if isinstance(value, dict):
                for key, child in value.items():
                    walk(child, pointer + "/" + key.replace("~", "~0").replace("/", "~1"))
            elif isinstance(value, list):
                for i, child in enumerate(value):
                    walk(child, pointer + "/" + str(i))
            else:
                expected.append((pointer, value))

        walk(original, "")
        assert sorted(
            (x["path"], x["raw_value"]) for x in by_projection[plan["projection_id"]]
        ) == sorted(expected)
        row = native[plan["projection_id"][:60]]
        for item in by_projection[plan["projection_id"]]:
            selected = item["path"].split("/")[1] in plan["operational_metadata"]
            assert selected == item["decision"].startswith(("PRESERVE_", "OPERATIONAL_"))
            pointer = "/@operational_metadata" + item["path"]
            if selected and not any(
                pointer == p or pointer.startswith(p + "/") for p in plan["operations"]
            ):
                assert _published_at(row, pointer, plan) == item["raw_value"]
                checked += 1
    assert checked == 24110


def test_original_execution_and_operational_admission_custody_survive(sealed_library):
    registry = source._registry(REPOSITORY)
    _, _, originals, _ = source._inputs(registry, PRIVATE)
    native = _native(sealed_library)
    index = {
        tuple(row[k] for k in ("company", "branch", "system", "record", "version")): row
        for row in native.values()
    }
    periods, admissions, joined, restricted = 0, 0, 0, 0
    for plan in registry["records"]:
        row = native[plan["projection_id"][:60]]
        raw = originals[plan["input_id"]]
        provenance = json.loads(row["provenance"])
        metadata = provenance["operational_metadata"]
        if raw["component"] == "period-history":
            assert row["content"] == raw["content"]
            assert row["sha256"] == raw["sha256"]
            assert "EXACT_ORIGINAL_EXECUTED_CONFIGURATION_BYTES" in provenance["definition_basis"]
            periods += 1
        if "source_admission" not in metadata:
            continue
        admission = metadata["source_admission"]
        original = json.loads(raw["provenance"])["source_admission"]
        assert admission["original_metadata_sha256"] == original["metadata_sha256"]
        assert "ORIGINAL_PROVENANCE" in admission["original_metadata_digest_basis"]
        assert admission["projected_metadata_sha256"] == sha(
            encoded(
                {"original": admission["metadata"], "definition": admission["definition_metadata"]}
            )
        )
        for name in (
            "consumed_at",
            "consumer_runtime_id",
            "consumer_runtime_sha256",
            "dataset_id",
            "source_store_id",
            "source_location_sha256",
            "identity_basis",
            "qualification",
            "execution_source_sha256",
        ):
            assert admission[name] == original[name]
        assert "NOT_PRODUCER_AUTHENTICATION" in admission["identity_basis"]
        for field in ("source_pin", "source_definition_pin", "metadata", "definition_metadata"):
            ref = admission[field]
            if "status" in ref:
                assert ref["status"].startswith("RESTRICTED_") and "sha256" not in ref
                restricted += 1
                continue
            target = index[
                tuple(ref[k] for k in ("company", "branch", "system", "record", "version"))
            ]
            assert set(ref) == {
                "company",
                "branch",
                "system",
                "record",
                "version",
                "event_at",
                "available_at",
                "sha256",
            }
            for name in ref:
                assert target[name] == ref[name]
            assert source._time(ref["available_at"]) <= source._time(admission["consumed_at"])
            if field in {"source_pin", "metadata"}:
                assert target["content"] == row["content"]
                assert target["sha256"] == row["sha256"] == raw["sha256"]
            joined += 1
        admissions += 1
    assert (periods, admissions, joined, restricted) == (2, 4, 8, 8)


def test_fully_resealed_operational_provenance_loss_is_rejected(created):
    def change(db):
        row = db.execute(
            "SELECT * FROM versions WHERE system LIKE '%backup-runtime-history%' "
            "AND system LIKE '%source_dataset%'"
        ).fetchone()
        value = json.loads(row["provenance"])
        value["operational_metadata"]["source_admission"]["consumed_at"] = "2027-02-01T00:00:00Z"
        db.execute(
            "UPDATE versions SET provenance=? WHERE command_id=?",
            (json.dumps(value), row["command_id"]),
        )

    _mutate(created, change)
    with pytest.raises(CompanyStoreError):
        _verify(created)


def test_every_unmodified_business_leaf_and_plain_bytes_survive(sealed_library):
    registry = source._registry(REPOSITORY)
    _, _, raw, _ = source._inputs(registry, PRIVATE)
    receipt = _verify(sealed_library)
    assert receipt["native_versions"] == registry["native_versions"]
    assert registry["v18_physical_component_count"] == 43
    assert registry["historical_v18_reported_component_count"] == 42
    with closing(source._read_db(sealed_library / "company.sqlite3")) as db:
        db.row_factory = sqlite3.Row
        native = {r["command_id"]: dict(r) for r in db.execute("SELECT * FROM versions")}
    checked, text = 0, 0
    for plan in registry["records"]:
        original = raw[plan["input_id"]]
        row = native["MIG-" + plan["projection_id"][:60]]
        assert row["event_at"] == original["event_at"]
        assert row["available_at"] == original["available_at"]
        assert row["version"] == plan["version"]
        assert receipt["initialized_at"] <= row["imported_at"] <= receipt["completed_at"]
        provenance = json.loads(row["provenance"])
        assert not source._leaks(provenance)
        if plan["format"] == "UTF8_TEXT":
            assert row["content"] == original["content"]
            assert row["sha256"] == original["sha256"]
            assert provenance["name"].endswith(".txt")
            assert provenance["content_type"].startswith("text/plain")
            text += 1
            continue
        body = json.loads(row["content"])
        assert not source._leaks(
            body, business_key_exemptions=set(plan.get("diagnostic_business_key_exemptions", []))
        )
        assert provenance["name"].endswith(".json")

        def check(before, after, pointer="", plan=plan):
            nonlocal checked
            if pointer in plan["operations"]:
                return
            if isinstance(before, dict):
                for key, value in before.items():
                    p = pointer + "/" + key.replace("~", "~0").replace("/", "~1")
                    if p in plan["operations"]:
                        continue
                    check(value, after[plan["rename_keys"].get(p, key)], p)
            elif isinstance(before, list):
                assert len(before) == len(after)
                for index, value in enumerate(before):
                    check(value, after[index], pointer + "/" + str(index))
            else:
                assert before == after
                checked += 1

        check(original["body"], body)
    assert checked > 20000
    assert text == 6
    assert receipt["access_granted"] is receipt["engagement_created"] is False


def test_all_references_keep_exact_private_custody_and_restricted_status(sealed_library):
    registry = source._registry(REPOSITORY)
    plans = {p["projection_id"]: p for p in registry["records"]}
    _, _, raw, _ = source._inputs(registry, PRIVATE)
    private = json.loads((sealed_library / "TRANSFORMATION.json").read_text())
    with closing(source._read_db(sealed_library / "company.sqlite3")) as db:
        db.row_factory = sqlite3.Row
        native = {
            (r["company"], r["branch"], r["system"], r["record"], r["version"]): dict(r)
            for r in db.execute("SELECT * FROM versions")
        }
    restricted = {}
    for item in private["reference_custody"]:
        plan = plans[item["projection_id"]]
        op = plan["operations"][item["path"]]
        original = _original_at(raw[item["input_id"]], item["path"])
        assert item["raw_reference"] == original
        assert sha(encoded(original)) == op["raw_reference_sha256"]
        ref = item["projected_reference"]
        if ref.get("status") in {
            "RESTRICTED_CROSS_BRANCH_DEPENDENCY",
            "RESTRICTED_ARCHIVE_MOTIVATION_ONLY",
        }:
            assert set(ref) == {"custody_id", "status", *op["preserved_business_fields"]}
        else:
            assert ref.get("branch", ref.get("branch_id")) == plan["branch"]
        assert not source._leaks(ref)
        if "sha256" in ref:
            aliases = op.get("native_key_aliases", {})
            norm = {aliases.get(k, k): v for k, v in ref.items()}
            key = tuple(norm[k] for k in ("company", "branch", "system", "record", "version"))
            target = native[key]
            assert target["sha256"] == ref["sha256"]
            assert target["event_at"] == ref["event_at"]
            assert target["available_at"] == ref["available_at"]
            if "branch" in original:
                assert original["branch"] == raw[op["target_original_input_id"]]["branch"]
        else:
            assert ref["status"].startswith("RESTRICTED_")
            assert ref["custody_id"].startswith("UPSTREAM-")
            assert "provenance" not in ref and "imported_at" not in ref
            restricted[ref["status"]] = restricted.get(ref["status"], 0) + 1
    assert restricted == {
        "RESTRICTED_CROSS_BRANCH_DEPENDENCY": 54,
        "RESTRICTED_UNREGISTERED_DEPENDENCY": 82,
        "RESTRICTED_ARCHIVE_MOTIVATION_ONLY": 60,
        "RESTRICTED_AMBIGUOUS_DEPENDENCY": 8,
    }


@pytest.mark.parametrize("ledger", ["human", "service", "person"])
def test_normal_engine_collection_reads_exact_typed_text_and_enforces_access(
    created, tmp_path, ledger
):
    engine = Engine(tmp_path / "audit", company_root=created)
    actor = engine.store.provision("Source auditor", ["learner"])["id"]
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="Source type collection check",
        phase="ACTIVE",
        discipline="IT",
        mode="CLEAN",
        simulated_at="2028-02-01T00:00:00Z",
        scope={
            "boundaries": ["corporate"],
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "timezone": "UTC",
        },
        configuration={"selections": []},
    )
    state["requests"] = [{"id": "R1", "status": "ISSUED", "artifact_ids": []}]
    state = engine.store.create(actor, state, "type-check")
    branch = source.BRANCHES[0]
    system = (
        "person-access-history.workspace_object"
        if ledger == "person"
        else "iam005-" + ledger + ".local_object"
    )
    record_id = "CORPORATE-REFERENCE" if ledger == "person" else "LOCAL-IAM005-TRACE-OBJECT"
    with closing(source._read_db(created / "company.sqlite3")) as db:
        original_payload = db.execute(
            "SELECT content FROM versions WHERE branch=? AND system=? AND record=? AND version=1",
            (branch, system, record_id),
        ).fetchone()[0]
    engine.company_bindings[state["id"]] = {"company": source.COMPANY, "branch": branch}
    with pytest.raises(DomainError):
        discover(engine, actor, state["id"], system)
    assert engine.store.get(actor, state["id"])["artifacts"] == []
    engine.company_store.grant(actor, state["id"], source.COMPANY, branch, system)
    discovered = discover(engine, actor, state["id"], system)["records"]
    assert len(discovered) == 1
    command = {
        "command_id": "collect-text",
        "expected_revision": state["revision"],
        "kind": "company.collect",
        "payload": {
            "system_id": system,
            "record_id": record_id,
            "version": 1,
            "request_id": "R1",
        },
    }
    result = engine.command(actor, state["id"], command)
    artifact = result["artifacts"][0]
    assert engine.artifacts.read(artifact) == original_payload
    assert artifact["name"].endswith(".txt")
    assert artifact["source"]["receipt"]["source"]["branch"] == branch
    assert artifact["source"]["receipt"]["source"]["system"] == system
    assert artifact["coverage"]["professional_sufficiency"] == "NOT_ASSERTED"
    engine.company_store.grant(actor, state["id"], source.COMPANY, branch, system, active=False)
    with pytest.raises(DomainError):
        discover(engine, actor, state["id"], system)


@pytest.mark.parametrize("attack", ["ANSWER", "PROVENANCE", "CLOCK", "CONTENT_DISCREPANCY"])
def test_resealed_native_mutation_rejected(created, attack):
    def change(db):
        row = db.execute(
            "SELECT * FROM versions WHERE system='sec003vuln.vulnerability_scan' "
            "AND record='SCAN-OCT-01' AND branch=?",
            (source.BRANCHES[1],),
        ).fetchone()
        if attack == "PROVENANCE":
            p = json.loads(row["provenance"])
            p["scenario"] = "MESSY"
            db.execute(
                "UPDATE versions SET provenance=? WHERE command_id=?",
                (encoded(p).decode(), row["command_id"]),
            )
        elif attack == "CLOCK":
            db.execute(
                "UPDATE versions SET imported_at='2025-01-01T00:00:00.000000+00:00' "
                "WHERE command_id=?",
                (row["command_id"],),
            )
        else:
            body = json.loads(row["content"])
            if attack == "ANSWER":
                body["expected_findings"] = ["FAIL"]
            else:
                body["detail"]["observed_count"] = 4
            data = encoded(body)
            db.execute(
                "UPDATE versions SET content=?,sha256=? WHERE command_id=?",
                (data, sha(data), row["command_id"]),
            )

    _mutate(created, change)
    with pytest.raises(CompanyStoreError, match="native body/provenance/clock custody"):
        _verify(created)


@pytest.mark.parametrize(
    "attack",
    [
        "MISSING_TRIGGER",
        "INERT_TRIGGER",
        "EXTRA_TABLE",
        "UNAUTHORIZED_GRANT",
        "EXTRA_RECEIPT_BRANCH",
        "CUSTODY_REBASE",
    ],
)
def test_resealed_boundary_or_custody_mutation_rejected(created, attack):
    if attack in {"MISSING_TRIGGER", "INERT_TRIGGER", "EXTRA_TABLE", "UNAUTHORIZED_GRANT"}:
        with closing(sqlite3.connect(created / "company.sqlite3")) as db, db:
            if attack == "EXTRA_TABLE":
                db.execute("CREATE TABLE hidden_key(answer TEXT)")
            elif attack == "UNAUTHORIZED_GRANT":
                row = db.execute("SELECT company,branch,system FROM systems LIMIT 1").fetchone()
                db.execute(
                    "INSERT INTO grants VALUES(?,?,?,?,?,?)", ("unapproved", "uncreated", *row, 1)
                )
            else:
                db.execute("DROP TRIGGER no_collection_update")
                if attack == "INERT_TRIGGER":
                    db.execute(
                        "CREATE TRIGGER no_collection_update BEFORE UPDATE ON collections "
                        "BEGIN SELECT 1; END"
                    )
    elif attack == "EXTRA_RECEIPT_BRANCH":
        p = created / "RECEIPT.json"
        value = json.loads(p.read_text())
        value["branches"].append("HIDDEN_BRANCH")
        p.write_text(json.dumps(value))
    else:
        p = created / "TRANSFORMATION.json"
        value = json.loads(p.read_text())
        ref = next(
            r
            for r in value["reference_custody"]
            if r["projected_reference"].get("status") == "RESTRICTED_CROSS_BRANCH_DEPENDENCY"
        )
        ref["projected_reference"]["status"] = "IMPORTED"
        p.write_text(json.dumps(value))
    _reseal(created)
    with pytest.raises(CompanyStoreError):
        _verify(created)


def test_explicit_reference_identity_cannot_choose_opposite_or_byte_equal_object():
    registry = source._registry(REPOSITORY)
    _, _, rows, _ = source._inputs(registry, PRIVATE)
    bad = copy.deepcopy(registry)
    target = next(
        p
        for p in bad["records"]
        if p["identity"][0] == "iam005-human"
        and p["identity"][3] == "local_object"
        and p["branch"] == source.BRANCHES[1]
    )
    selected = next(
        p
        for p in bad["records"]
        if any(
            o.get("target_original_input_id")
            and rows[o["target_original_input_id"]]["component"] == "iam005-human"
            and rows[o["target_original_input_id"]]["system"] == "local_object"
            for o in p["operations"].values()
        )
    )
    op = next(
        o
        for o in selected["operations"].values()
        if o.get("target_original_input_id")
        and rows[o["target_original_input_id"]]["component"] == "iam005-human"
        and rows[o["target_original_input_id"]]["system"] == "local_object"
    )
    op["target_original_input_id"] = target["input_id"]
    op["target_projection_id"] = target["projection_id"]
    with pytest.raises(CompanyStoreError):
        source._project(bad, rows)


def _native(root):
    with closing(source._read_db(root / "company.sqlite3")) as db:
        db.row_factory = sqlite3.Row
        return {r["command_id"][4:]: dict(r) for r in db.execute("SELECT * FROM versions")}


def test_exact_shared_counterparts_keep_original_bytes_dates_and_private_identity(sealed_library):
    registry = source._registry(REPOSITORY)
    _, _, originals, _ = source._inputs(registry, PRIVATE)
    native = _native(sealed_library)
    assert registry["native_versions"] == 5608
    assert registry["raw_source_versions"] == 5600
    assert registry["physical_component_count"] == 69
    assert len(registry["common_upstream_admissions"]) == 8
    assert len(registry["same_branch_business_equivalences"]) == 3
    for contract in registry["common_upstream_admissions"]:
        raw = originals[contract["input_id"]]
        counterparts = contract["counterpart_identities"]
        assert {c[2] for c in counterparts} == set(source.BRANCHES)
        for projection_id, *identity in counterparts:
            row = native[projection_id[:60]]
            assert [
                row[k] for k in ("company", "branch", "system", "record", "version")
            ] == identity
            assert row["content"] == raw["content"]
            assert row["sha256"] == raw["sha256"]
            assert row["event_at"] == raw["event_at"]
            assert row["available_at"] == raw["available_at"]
            provenance = json.loads(row["provenance"])
            assert provenance["common_upstream_copy"] is True
            assert provenance["original_content_version"] == raw["version"]
            assert (
                "NO_NEW_COUNTERPART_EXECUTION_OR_AUTHORITY_ASSERTED" in provenance["runtime_scope"]
            )
    assert sum(p["projection_id"] != p["input_id"] for p in registry["records"]) == 8


def test_every_declared_digest_reperforms_from_native_bytes(sealed_library):
    registry = source._registry(REPOSITORY)
    plans = {p["projection_id"]: p for p in registry["records"]}
    _, _, originals, _ = source._inputs(registry, PRIVATE)
    native = _native(sealed_library)
    private = json.loads((sealed_library / "TRANSFORMATION.json").read_text())
    counts = {}
    for item in private["digest_custody"]:
        counts[item["kind"]] = counts.get(item["kind"], 0) + 1
        owner = native[item["projection_id"][:60]]
        body = json.loads(owner["content"])
        value = _published_at(owner, item["path"], plans[item["projection_id"]])
        assert value == item["projected_digest"]
        if item["kind"] == "HASH_REFERENCE":
            target = native[item["target_projection_id"][:60]]
            assert owner["branch"] == target["branch"]
            assert value == sha(target["content"])
            assert item["raw_digest"] in {r["sha256"] for r in originals.values()}
        elif item["kind"] == "DERIVED_DIGEST":
            assert value == sha(encoded(_at(body, item["basis_pointer"])))
        elif item["kind"] == "DERIVED_OBJECT_DIGEST":
            basis = _at(body, item["basis_pointer"])
            assert value == sha(
                encoded({k: v for k, v in basis.items() if k not in item["excluded_keys"]})
            )
        elif item["kind"] == "DERIVED_TARGET_VECTOR_DIGEST":
            target = native[item["target_projection_id"][:60]]
            assert target["branch"] == owner["branch"]
            assert value == sha(encoded(_at(json.loads(target["content"]), item["basis_pointer"])))
        elif item["kind"] in {"TARGET_VALUE_REFERENCE", "DERIVED_TARGET_HASH_MAP"}:
            vector = {}
            for declaration in item["targets"]:
                target = native[declaration["projection_id"][:60]]
                assert target["branch"] == owner["branch"]
                vector[declaration["key"]] = _at(
                    json.loads(target["content"]), declaration["pointer"]
                )
            assert value == (
                next(iter(vector.values()))
                if item["kind"] == "TARGET_VALUE_REFERENCE"
                else sha(encoded(vector))
            )
        elif item["kind"] in {"ARCHIVED_METADATA_DIGEST", "ARCHIVED_METADATA_BUNDLE_DIGEST"}:
            fields = (
                "company",
                "branch",
                "system",
                "record",
                "version",
                "sha256",
                "event_at",
                "available_at",
                "origin",
                "provenance",
            )
            if item["kind"] == "ARCHIVED_METADATA_BUNDLE_DIGEST":
                basis = {
                    name: {k: originals[i][k] for k in fields}
                    for name, i in item["original_metadata_members"].items()
                }
            else:
                rows = sorted(
                    (originals[i] for i in item["original_input_ids"]),
                    key=lambda r: tuple(r[k] for k in fields[:5]),
                )
                basis = [{k: r[k] for k in fields} for r in rows]
            assert value == item["raw_digest"] == sha(encoded(basis))
        else:
            pytest.fail("Undeclared digest contract")
    assert counts["DERIVED_TARGET_VECTOR_DIGEST"] == 40
    assert counts["DERIVED_OBJECT_DIGEST"] == 12
    assert counts["ARCHIVED_METADATA_DIGEST"] == 78
    assert counts["ARCHIVED_METADATA_BUNDLE_DIGEST"] == 4
    assert counts["DERIVED_DIGEST"] == 18
    assert private["unresolved_digest_limits"] == []
    for check in private["unchanged_byte_digest_checks"]:
        owner = native[check["input_id"][:60]]
        assert _at(json.loads(owner["content"]), check["path"]) == check["raw_digest"]
        for original_id in check["raw_target_input_ids"]:
            assert originals[original_id]["sha256"] == check["raw_digest"]
            copies = [p for p in registry["records"] if p["input_id"] == original_id]
            assert copies
            for plan in copies:
                assert (
                    native[plan["projection_id"][:60]]["content"]
                    == originals[original_id]["content"]
                )
                assert native[plan["projection_id"][:60]]["sha256"] == check["raw_digest"]
    assert len(private["unchanged_byte_digest_checks"]) > 2200


def test_all_eight_legacy_quarters_keep_member_decision_and_hr_population_joins(sealed_library):
    native = _native(sealed_library)
    lookup = {(r["branch"], r["system"], r["record"], r["version"]): r for r in native.values()}
    for branch in source.BRANCHES:
        for quarter in range(1, 5):
            record = f"PRIV-2027-Q{quarter}"
            population = lookup[(branch, "identity-history.review_population", record, 1)]
            members = json.loads(population["content"])["members"]
            assert json.loads(population["content"])["membership_sha256"] == sha(encoded(members))
            for member in members:
                account = lookup[
                    (branch, "identity-history.application", member["record"], member["version"])
                ]
                body = json.loads(account["content"])
                assert account["sha256"] == member["sha256"]
                assert body["person_id"] == member["person_id"]
                assert body["rights"] == member["rights"]
            decisions = json.loads(
                lookup[(branch, "identity-history.review_decisions", record, 1)]["content"]
            )
            reconciliation = json.loads(
                lookup[(branch, "identity-history.review_reconciliation", record, 1)]["content"]
            )
            assert (
                decisions["population_sha256"]
                == reconciliation["population_sha256"]
                == population["sha256"]
            )
            for decision in decisions["decisions"]:
                assert (
                    decision["source_sha256"]
                    == lookup[
                        (
                            branch,
                            "identity-history.application",
                            decision["source_record"],
                            decision["source_version"],
                        )
                    ]["sha256"]
                )
            for hr in reconciliation["hr_sources"]:
                assert (
                    hr["sha256"]
                    == lookup[(branch, "identity-history.hr", hr["record"], hr["version"])][
                        "sha256"
                    ]
                )


def test_projected_logging_payload_chain_and_historical_gap_survive(sealed_library):
    from enterprise.audit_suite.company_security_logging_activity import reconcile

    native = _native(sealed_library)
    checks = 0
    for family in ("logging-history", "baseline-logging"):
        for branch in source.BRANCHES:
            rows = [
                r
                for r in native.values()
                if r["branch"] == branch and r["system"].startswith(family + ".")
            ]
            if not rows:
                continue
            publisher = sorted(
                (
                    json.loads(r["content"])["event"]
                    for r in rows
                    if r["system"] == family + ".publisher_events"
                ),
                key=lambda b: b["sequence"],
            )
            for row in rows:
                if row["system"] != family + ".coverage_reconciliation":
                    continue
                body = json.loads(row["content"])
                candidates = [
                    r
                    for r in rows
                    if r["system"] == family + ".ingestion_journal"
                    and r["available_at"] <= row["available_at"]
                ]
                latest = {}
                for r in candidates:
                    b = json.loads(r["content"])
                    n = b["event"]["sequence"]
                    if n not in latest or r["version"] > latest[n][0]:
                        latest[n] = (r["version"], b)
                observed = reconcile(publisher, [item[1] for item in latest.values()])
                for field, value in observed.items():
                    assert body[field] == value
                checks += 1
    assert checks == 6


@pytest.mark.parametrize(
    "attack",
    [
        "UNDECLARED_FORK",
        "WRONG_BRANCH",
        "RAW_BYTES",
        "ARCHIVE_METADATA",
        "VECTOR_TARGET",
        "COMPACT_CLOCK",
        "BUSINESS_PURPOSE",
    ],
)
def test_exact_fork_archive_and_linked_basis_challenges_reject(attack):
    registry = source._registry(REPOSITORY)
    _, _, originals, _ = source._inputs(registry, PRIVATE)
    bad = copy.deepcopy(registry)
    if attack == "UNDECLARED_FORK":
        bad["common_upstream_admissions"].pop()
    elif attack == "WRONG_BRANCH":
        contract = bad["common_upstream_admissions"][0]
        second = contract["counterpart_identities"][1]
        second[2] = contract["counterpart_identities"][0][2]
    elif attack == "RAW_BYTES":
        original = originals[bad["common_upstream_admissions"][0]["input_id"]]
        original["content"] += b" "
    elif attack == "ARCHIVE_METADATA":
        original = originals[bad["same_branch_business_equivalences"][0]["original_input_id"]]
        original["provenance"] += " "
    else:
        kind = {
            "VECTOR_TARGET": "DERIVED_TARGET_VECTOR_DIGEST",
            "COMPACT_CLOCK": "COMPACT_NATIVE_REFERENCE",
            "BUSINESS_PURPOSE": "NATIVE_REFERENCE",
        }[attack]
        plan = next(
            p
            for p in bad["records"]
            if any(
                o["kind"] == kind
                and (
                    attack != "BUSINESS_PURPOSE"
                    or "purpose" in o.get("preserved_business_fields", {})
                )
                for o in p["operations"].values()
            )
        )
        path, op = next(
            (q, o)
            for q, o in plan["operations"].items()
            if o["kind"] == kind
            and (
                attack != "BUSINESS_PURPOSE" or "purpose" in o.get("preserved_business_fields", {})
            )
        )
        if attack == "VECTOR_TARGET":
            op["basis_pointer"] = "/declared_fake_population"
        elif attack == "COMPACT_CLOCK":
            parent = _at(originals[plan["input_id"]]["body"], path)
            parent["available_at"] = "2029-01-01T00:00:00Z"
            op["raw_reference_sha256"] = sha(encoded(parent))
        else:
            op["preserved_business_fields"]["purpose"] = "NEW_OPERATING_AUTHORITY"
    with pytest.raises((CompanyStoreError, KeyError)):
        source._project(bad, originals)


def test_person_history_actual_read_deny_epochs_and_all_closed_window_denominators(sealed_library):
    from datetime import UTC, datetime

    def clock(value):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    native = _native(sealed_library)
    probes = months = quarters = 0
    for branch in source.BRANCHES:
        selected = [
            r
            for r in native.values()
            if r["branch"] == branch and r["system"].startswith("person-access-history.")
        ]
        rows = []
        for original in selected:
            r = dict(original)
            r["system"] = r["system"].split(".", 1)[1]
            r["body"] = None if r["system"] == "workspace_object" else json.loads(r["content"])
            rows.append(r)
        lookup = {(r["system"], r["record"], r["version"]): r for r in rows}
        affiliations = [r for r in rows if r["system"] == "affiliation_register"]
        statuses = {
            status: sum(r["body"]["source_status"] == status for r in affiliations)
            for status in (
                "current_employee",
                "current_nonemployee_director",
                "former_employee",
                "PROPOSED_OFFICE_OCCUPANT",
            )
        }
        assert statuses == {
            "current_employee": 44,
            "current_nonemployee_director": 7,
            "former_employee": 1,
            "PROPOSED_OFFICE_OCCUPANT": 15,
        }
        assert not next(r["body"] for r in affiliations if r["record"] == "P008")[
            "included_in_service_boundary"
        ]
        assert sum(r["body"]["relationship_kind"] == "SERVICE_DELEGATE" for r in affiliations) == 6
        states = [
            r for r in rows if r["system"].startswith("account_") and "state" in (r["body"] or {})
        ]
        assert min(r["available_at"] for r in states) == "2027-01-01T03:15:00.000000+00:00"
        payload = lookup[("workspace_object", "CORPORATE-REFERENCE", 1)]["content"]
        for row in rows:
            if row["system"] != "permission_activity":
                continue
            body = row["body"]
            prior = [
                s
                for s in states
                if s["body"]["state"]["account_id"] == body["account_id"]
                and clock(s["available_at"]) <= clock(body["decision_at"])
            ]
            current = max(prior, key=lambda s: s["version"])
            state = current["body"]["state"]
            allowed = (
                state["active"]
                and clock(state["starts"]) <= clock(body["decision_at"]) < clock(state["ends"])
                and state["credential_epoch"] == body["credential_epoch"]
                and body["right"] in state["rights"]
            )
            assert body["account_state"]["sha256"] == current["sha256"]
            assert body["decision"] == ("ALLOW" if allowed else "DENY")
            assert body["returned_bytes"] == (len(payload) if allowed else 0)
            assert body["returned_sha256"] == (sha(payload) if allowed else None)
            probes += 1
        subjects = {
            r["record"]: {
                "starts": r["body"]["service_effective_from"],
                "ends": r["body"]["service_effective_to"],
            }
            for r in affiliations
            if r["body"]["included_in_service_boundary"]
        }
        for row in rows:
            if row["system"] in {"contractor_relationship", "nonhuman_inventory"}:
                body = row["body"]
                subjects[body.get("person_id", body.get("identity_id"))] = {
                    "starts": body["starts"],
                    "ends": body["ends"],
                }
        for month in range(1, 13):
            snapshot = lookup[("denominator_snapshot", f"2027-{month:02}", 1)]["body"]
            cutoff = clock(snapshot["cutoff_exclusive"])
            assert cutoff == datetime(
                2028 if month == 12 else 2027, 1 if month == 12 else month + 1, 1, tzinfo=UTC
            )
            latest = {}
            for state in states:
                if clock(state["available_at"]) >= cutoff:
                    continue
                account = state["body"]["state"]["account_id"]
                if account not in latest or state["version"] > latest[account]["version"]:
                    latest[account] = state
            active = {
                account: state
                for account, state in latest.items()
                if state["body"]["state"]["active"]
                and clock(state["body"]["state"]["starts"])
                < cutoff
                <= clock(state["body"]["state"]["ends"])
            }
            expected = sorted(
                subject
                for subject, state in subjects.items()
                if clock(state["starts"]) < cutoff <= clock(state["ends"])
            )
            assert snapshot["registered_subject_ids"] == expected
            declared = {account["state"]["account_id"]: account for account in snapshot["accounts"]}
            assert set(declared) == set(active)
            for account, member in declared.items():
                assert member["state"] == active[account]["body"]["state"]
                assert member["source"]["sha256"] == active[account]["sha256"]
            reconciliation = lookup[("monthly_reconciliation", f"2027-{month:02}", 1)]["body"]
            assert reconciliation["account_population_sha256"] == sha(encoded(snapshot["accounts"]))
            months += 1
            if month % 3:
                continue
            population = lookup[("periodic_review_population", f"2027-Q{month // 3}", 1)]["body"]
            unresolved = {
                s["body"]["state"]["subject_id"]
                for s in active.values()
                if s["body"]["state"]["review_anchor"] is None
            }
            assert {member["subject_id"] for member in population["members"]} == set(
                expected
            ) - unresolved
            digest = sha(encoded(population["members"]))
            assert population["membership_sha256"] == digest
            for system in ("periodic_review_decisions", "review_followup"):
                assert (
                    lookup[(system, f"2027-Q{month // 3}", 1)]["body"]["population_sha256"]
                    == digest
                )
            quarters += 1
    assert (probes, months, quarters) == (1462, 24, 8)


def test_monitor_capture_and_original_provenance_witness_have_distinct_valid_bases(sealed_library):
    native = _native(sealed_library)
    registry = source._registry(REPOSITORY)
    _, _, originals, _ = source._inputs(registry, PRIVATE)
    plans = {p["projection_id"][:60]: p for p in registry["records"]}
    for branch in source.BRANCHES:
        scan = next(
            r
            for r in native.values()
            if r["branch"] == branch and r["system"] == "backup-runtime-history.monitor_scan"
        )
        body = json.loads(scan["content"])
        assert body["capture"]["jobs_sha256"] == sha(encoded(body["capture"]["membership"]))
        for ref in body["capture"]["membership"]["jobs"]:
            target = next(
                r
                for r in native.values()
                if all(r[k] == ref[k] for k in ("company", "branch", "system", "record", "version"))
            )
            assert ref["sha256"] == target["sha256"]
            raw = originals[plans[target["command_id"][4:]]["input_id"]]
            assert ref["original_provenance_sha256"] == sha(raw["provenance"].encode())
            assert ref["original_provenance_sha256"] != sha(target["provenance"].encode())
            assert (
                ref["original_provenance_digest_basis"]
                == "EXACT_PRIVATE_ORIGINAL_PROVENANCE_BYTES_NOT_PROJECTED_METADATA"
            )
            assert "provenance_sha256" not in ref
