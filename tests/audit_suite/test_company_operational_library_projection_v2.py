"""A whole company library stays native, typed, bounded, and isolated from audit answers."""

import copy
import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from enterprise.audit_suite import company_operational_library_projection_v2 as source
from enterprise.audit_suite.company_collection import discover
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from enterprise.audit_suite.store import DomainError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


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
        db.execute(trigger)
    _reseal(root)


def _at(value, pointer):
    for part in pointer.lstrip("/").split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


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
        row = native["MIG-" + plan["input_id"][:60]]
        assert row["event_at"] == original["event_at"]
        assert row["available_at"] == original["available_at"]
        assert row["version"] == original["version"]
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
        assert not source._leaks(body)
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
    assert text == 4
    assert receipt["access_granted"] is receipt["engagement_created"] is False


def test_all_references_keep_exact_private_custody_and_restricted_status(sealed_library):
    registry = source._registry(REPOSITORY)
    plans = {p["input_id"]: p for p in registry["records"]}
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
        plan = plans[item["input_id"]]
        op = plan["operations"][item["path"]]
        original = _at(raw[item["input_id"]]["body"], item["path"])
        assert item["raw_reference"] == original
        assert sha(encoded(original)) == op["raw_reference_sha256"]
        ref = item["projected_reference"]
        if ref.get("status") == "RESTRICTED_CROSS_BRANCH_DEPENDENCY":
            assert set(ref) == {"custody_id", "status"}
        else:
            assert ref["branch"] == plan["branch"]
        assert not source._leaks(ref)
        if "sha256" in ref:
            key = tuple(ref[k] for k in ("company", "branch", "system", "record", "version"))
            target = native[key]
            assert target["sha256"] == ref["sha256"]
            assert target["event_at"] == ref["event_at"]
            assert target["available_at"] == ref["available_at"]
            if "branch" in original:
                assert original["branch"] == raw[op["target_input_id"]]["branch"]
        else:
            assert ref["status"].startswith("RESTRICTED_")
            assert ref["custody_id"].startswith("UPSTREAM-")
            assert "provenance" not in ref and "imported_at" not in ref
            restricted[ref["status"]] = restricted.get(ref["status"], 0) + 1
    assert restricted == {
        "RESTRICTED_CROSS_BRANCH_DEPENDENCY": 45,
        "RESTRICTED_UNREGISTERED_DEPENDENCY": 12,
    }


@pytest.mark.parametrize("ledger", ["human", "service"])
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
    system = "iam005-" + ledger + ".local_object"
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
            "record_id": "LOCAL-IAM005-TRACE-OBJECT",
            "version": 1,
            "request_id": "R1",
        },
    }
    result = engine.command(actor, state["id"], command)
    artifact = result["artifacts"][0]
    assert (
        engine.artifacts.read(artifact)
        == b"Nonpersonal local IAM005 fixture: read-only example bytes.\n"
    )
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
            o.get("target_input_id")
            and rows[o["target_input_id"]]["component"] == "iam005-human"
            and rows[o["target_input_id"]]["system"] == "local_object"
            for o in p["operations"].values()
        )
    )
    op = next(
        o
        for o in selected["operations"].values()
        if o.get("target_input_id")
        and rows[o["target_input_id"]]["component"] == "iam005-human"
        and rows[o["target_input_id"]]["system"] == "local_object"
    )
    op["target_input_id"] = target["input_id"]
    with pytest.raises(CompanyStoreError):
        source._project(bad, rows)


def test_all_scalar_dependencies_and_executed_byte_digests(sealed_library):
    registry = source._registry(REPOSITORY)
    _, _, raw, _ = source._inputs(registry, PRIVATE)
    transformation = json.loads((sealed_library / "TRANSFORMATION.json").read_text())
    with closing(source._read_db(sealed_library / "company.sqlite3")) as db:
        db.row_factory = sqlite3.Row
        native = {r["command_id"]: dict(r) for r in db.execute("SELECT * FROM versions")}
    assert len(transformation["digest_custody"]) == 1043
    assert transformation["unresolved_digest_limits"] == []
    changed = 0
    for item in transformation["digest_custody"]:
        owner = native["MIG-" + item["input_id"][:60]]
        target = native["MIG-" + item["target_input_id"][:60]]
        assert _at(json.loads(owner["content"]), item["path"]) == target["sha256"]
        assert item["raw_digest"] == raw[item["target_input_id"]]["sha256"]
        assert item["projected_digest"] == target["sha256"]
        assert owner["branch"] == target["branch"]
        changed += item["raw_digest"] != item["projected_digest"]
    assert changed > 900
    assert len(transformation["unchanged_byte_digest_checks"]) == 49
    runtime_checks = 0
    for item in transformation["unchanged_byte_digest_checks"]:
        owner = native["MIG-" + item["input_id"][:60]]
        assert _at(json.loads(owner["content"]), item["path"]) == item["raw_digest"]
        for target_id in item["raw_target_input_ids"]:
            target = native["MIG-" + target_id[:60]]
            assert target["content"] == raw[target_id]["content"]
            assert target["sha256"] == item["raw_digest"]
            if raw[target_id]["system"] == "quality_definition":
                assert json.loads(target["content"])["plan"]["branch"].startswith(
                    "local-data-quality-"
                )
                runtime_checks += 1
    assert runtime_checks == 6


@pytest.mark.parametrize("attack", ["SCALAR_TARGET", "SCALAR_BASIS", "EXECUTED_BYTES"])
def test_exact_digest_contracts_reject_identity_and_executed_file_mutations(attack):
    registry = source._registry(REPOSITORY)
    _, _, rows, _ = source._inputs(registry, PRIVATE)
    bad = copy.deepcopy(registry)
    if attack in {"SCALAR_TARGET", "SCALAR_BASIS"}:
        op = next(
            o
            for p in bad["records"]
            for o in p["operations"].values()
            if o["kind"] == "HASH_REFERENCE"
        )
        if attack == "SCALAR_BASIS":
            op["target_identity"][4] += "-other"
        else:
            op["target_input_id"] = next(
                p["input_id"] for p in bad["records"] if p["input_id"] != op["target_input_id"]
            )
    else:
        plan = next(
            p
            for p in bad["records"]
            if p["identity"][0] == "rec003" and p["identity"][3] == "quality_definition"
        )
        plan["operations"]["/qualification"] = {
            "kind": "DROP_AUTHORING",
            "reason": "ADVERSARIAL_UNEXECUTED_RUNTIME",
        }
    with pytest.raises(CompanyStoreError, match="digest|bytes"):
        source._project(bad, rows)


IDENTITY_FIXTURE = (
    "enterprise/generated/audit-suite/company-identity-period-2026-09-14/"
    "full-year-v1/company/company.sqlite3"
)
IDENTITY_FIXTURE_SHA = "8183a47f82d0e76c0a785d12a0b0d8113f65d666c0ad5284c9a6e2dc92290357"
NONHUMAN_FIXTURE = (
    "enterprise/generated/audit-suite/company-nonhuman-identity-2026-09-14/v1/company.sqlite3"
)
NONHUMAN_FIXTURE_SHA = "b1c03493f83e2e6e90ec0152b0d966cc200ad64d6c15d920fe76fc59caac2c81"


def _original_fixture(relative, expected_hash, component):
    path = PRIVATE / relative
    assert source._digest(path) == expected_hash
    source._private(path)
    assert not any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-shm", "-journal"))
    with closing(source._read_db(path)) as db:
        db.row_factory = sqlite3.Row
        rows = {}
        for row in db.execute("SELECT * FROM versions"):
            value = dict(row)
            value.update(
                component=component,
                cohort=component,
                format="JSON",
                body=json.loads(row["content"]),
            )
            rows[source._input_id(relative, value)] = value
    return rows


def _identity_quarter_fixture():
    """Exercise absent source families in memory only; never admit them to V2."""
    rows = _original_fixture(IDENTITY_FIXTURE, IDENTITY_FIXTURE_SHA, "quarter-fixture")
    identities = {
        (r["branch"], r["system"], r["record"], r["version"]): input_id
        for input_id, r in rows.items()
    }
    plans = []
    for input_id, raw in rows.items():
        operations = {}
        if raw["system"] == "application":
            # An explicit fixture-only authoring-envelope removal forces a real
            # changed body/hash; entitlement and person facts stay exact.
            operations["/origin"] = {
                "kind": "DROP_AUTHORING",
                "reason": "FIXTURE_ONLY_ORIGIN_ENVELOPE",
            }

        def scalar(pointer, system, record, version, raw=raw, operations=operations):
            target_id = identities[(raw["branch"], system, record, version)]
            target = rows[target_id]
            assert source._pointer(raw["body"], pointer) == target["sha256"]
            operations[pointer] = {
                "kind": "HASH_REFERENCE",
                "target_input_id": target_id,
                "target_identity": [
                    target[k]
                    for k in ("component", "company", "branch", "system", "record", "version")
                ],
                "basis": {
                    "fixture": IDENTITY_FIXTURE,
                    "fixture_sha256": IDENTITY_FIXTURE_SHA,
                    "query_system": system,
                },
            }

        if raw["system"] == "review_population":
            for index, member in enumerate(raw["body"]["members"]):
                target = rows[
                    identities[(raw["branch"], "application", member["record"], member["version"])]
                ]
                assert target["body"]["person_id"] == member["person_id"]
                assert target["body"]["rights"] == member["rights"]
                scalar(
                    f"/members/{index}/sha256", "application", member["record"], member["version"]
                )
            operations["/membership_sha256"] = {
                "kind": "DERIVED_DIGEST",
                "algorithm": "CANONICAL_JSON_SHA256",
                "basis_pointer": "/members",
                "from": raw["body"]["membership_sha256"],
            }
        if raw["system"] in {"review_decisions", "review_reconciliation"}:
            scalar("/population_sha256", "review_population", raw["record"], 1)
        if raw["system"] == "review_decisions":
            for index, member in enumerate(raw["body"]["decisions"]):
                scalar(
                    f"/decisions/{index}/source_sha256",
                    "application",
                    member["source_record"],
                    member["source_version"],
                )
        plans.append(
            {
                "input_id": input_id,
                "input_sha256": raw["sha256"],
                "identity": [
                    raw[k]
                    for k in ("component", "company", "branch", "system", "record", "version")
                ],
                "cohort": raw["cohort"],
                "format": "JSON",
                "branch": source.BRANCHES[0 if raw["branch"] == "year-clean" else 1],
                "system": "quarter-fixture." + raw["system"],
                "record": raw["record"],
                "operations": operations,
                "rename_keys": {},
            }
        )
    return {
        "records": plans,
        "expected_transformation_sha256": (
            "f4248e3fa158ee10e55955b18d016159415fe49f64251ab85187db1d58b1bd72"
        ),
    }, rows


def test_all_original_quarters_have_exact_changed_member_vector_and_population_joins():
    registry, rows = _identity_quarter_fixture()
    ordered, transformation = source._project(registry, rows)
    native = {(r["branch"], r["system"], r["record"], r["version"]): r for r in ordered}
    for branch in source.BRANCHES:
        for quarter in range(1, 5):
            record = f"PRIV-2027-Q{quarter}"
            pop = native[(branch, "quarter-fixture.review_population", record, 1)]
            decisions = native[(branch, "quarter-fixture.review_decisions", record, 1)]
            reconciliation = native[(branch, "quarter-fixture.review_reconciliation", record, 1)]
            assert sha(encoded(pop["body"]["members"])) == pop["body"]["membership_sha256"]
            assert (
                decisions["body"]["population_sha256"]
                == reconciliation["body"]["population_sha256"]
                == pop["sha256"]
            )
            for member in pop["body"]["members"]:
                app = native[
                    (branch, "quarter-fixture.application", member["record"], member["version"])
                ]
                assert member["sha256"] == app["sha256"] != app["input_sha256"]
                assert member["person_id"] == app["body"]["person_id"]
                assert member["rights"] == app["body"]["rights"]
            # The original missing-person history and decisions are not corrected.
            raw = rows[pop["input_id"]]["body"]
            assert pop["body"]["query"] == raw["query"]
            assert len(pop["body"]["members"]) == len(raw["members"])
    assert len([r for r in transformation["digest_custody"] if r["kind"] == "DERIVED_DIGEST"]) == 8
    assert all(p["cohort"] != "quarter-fixture" for p in source._registry(REPOSITORY)["records"])


@pytest.mark.parametrize("attack", ["VECTOR_BASIS", "ALGORITHM", "SCALAR_IDENTITY", "WRONG_BRANCH"])
def test_original_quarter_digest_contract_rejects_invalid_basis_and_peer_branch(attack):
    registry, rows = _identity_quarter_fixture()
    pop = next(
        p
        for p in registry["records"]
        if p["identity"][3] == "review_population"
        and p["identity"][4] == "PRIV-2027-Q2"
        and p["branch"] == source.BRANCHES[0]
    )
    if attack == "VECTOR_BASIS":
        pop["operations"]["/membership_sha256"]["from"] = "0" * 64
    elif attack == "ALGORITHM":
        pop["operations"]["/membership_sha256"]["algorithm"] = "GUESS"
    else:
        op = pop["operations"]["/members/0/sha256"]
        if attack == "SCALAR_IDENTITY":
            op["target_identity"][4] += "-wrong"
        else:
            target = next(
                p
                for p in registry["records"]
                if p["identity"][3:6] == op["target_identity"][3:6]
                and p["branch"] == source.BRANCHES[1]
            )
            op["target_input_id"] = target["input_id"]
            op["target_identity"] = target["identity"]
    with pytest.raises(CompanyStoreError):
        source._project(registry, rows)


def test_original_nonhuman_copied_dataset_bytes_and_input_output_digest_contract():
    rows = _original_fixture(NONHUMAN_FIXTURE, NONHUMAN_FIXTURE_SHA, "copy-fixture")
    copies = {input_id: r for input_id, r in rows.items() if r["system"] == "copied_dataset"}
    plans = [
        {
            "input_id": input_id,
            "input_sha256": raw["sha256"],
            "identity": [
                raw[k] for k in ("component", "company", "branch", "system", "record", "version")
            ],
            "cohort": "copy-fixture",
            "format": "JSON",
            "branch": source.BRANCHES[0 if raw["branch"] == "service-a" else 1],
            "system": "copy-fixture.copied_dataset",
            "record": raw["record"],
            "operations": {},
            "rename_keys": {},
        }
        for input_id, raw in copies.items()
    ]
    ordered, _ = source._project(
        {
            "records": plans,
            "expected_transformation_sha256": (
                "c1fcd72c601d0b2a2d3038b1995dc42ccf09b6d9509a58793b548ae61c6ee5ee"
            ),
        },
        copies,
    )
    projected = {(r["branch"], r["record"], r["version"]): r for r in ordered}
    count = 0
    for raw in rows.values():
        body = raw["body"]
        if raw["system"] != "copy_attempts" or body.get("status") != "COPIED":
            continue
        ref = body["output_ref"]
        branch = source.BRANCHES[0 if raw["branch"] == "service-a" else 1]
        out = projected[(branch, ref["record"], ref["version"])]
        assert out["content"] == copies[out["input_id"]]["content"]
        assert out["sha256"] == ref["sha256"] == body["output_sha256"] == body["input_sha256"]
        assert len(out["content"]) == body["copied_bytes"]
        count += 1
    assert count == 5
    assert all(p["cohort"] != "copy-fixture" for p in source._registry(REPOSITORY)["records"])
