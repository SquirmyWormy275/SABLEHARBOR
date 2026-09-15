"""Independent checks with re-pinned native originals, never stale expected hashes."""

import json
from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from enterprise.audit_suite import company_access_review_continuation as review
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from tests.audit_suite.test_company_access_review_continuation import ROOT, group, rows
from tests.audit_suite.test_company_access_review_continuation import inputs as inputs


def clone(root, destination, change):
    destination.mkdir(mode=0o700)
    target = CompanyStore(destination)
    originals = CompanyStore(root)
    rewritten, native_pins = {}, {}

    def repin(value):
        if isinstance(value, dict):
            return {k: repin(v) for k, v in value.items()}
        if isinstance(value, list):
            return [repin(v) for v in value]
        return rewritten.get(value, value) if isinstance(value, str) else value

    originals_in_order = sorted(
        rows(root),
        key=lambda r: (
            r["event_at"],
            len(json.loads(r["content"]).get("previous_events", [])),
            r["system"],
            r["record"],
            r["version"],
        ),
    )
    for native in originals_in_order:
        with originals._db() as db:
            owner = db.execute(
                "SELECT owner FROM systems WHERE company=? AND branch=? AND system=?",
                (native["company"], native["branch"], native["system"]),
            ).fetchone()[0]
        target.register_system(native["company"], native["branch"], native["system"], owner)
        body = repin(json.loads(native["content"]))
        for link in body.get("previous_events", []):
            key = (native["branch"], link["system"], link["record"], link["version"])
            if key in native_pins:
                link["sha256"] = native_pins[key]
        change(native, body)
        raw = encoded(body)
        target.append_version(
            native["company"],
            native["branch"],
            native["system"],
            native["record"],
            expected_version=native["version"] - 1,
            command_id=native["command_id"],
            event_at=native["event_at"],
            available_at=native["available_at"],
            content=raw,
            provenance=json.loads(native["provenance"]),
        )
        rewritten[native["sha256"]] = sha(raw)
        native_pins[(native["branch"], native["system"], native["record"], native["version"])] = (
            sha(raw)
        )
    return target


def changed_chain(inputs, tmp_path, mutation):
    roots, recipe = inputs
    altered = tmp_path / "repinned"
    clone(roots["remediation_initial"], altered, mutation)
    index = {
        (r["system"], r["record"], r["version"]): r
        for r in rows(altered)
        if r["branch"] == "removal-b"
    }
    selected = (
        recipe.source_groups[0],
        group(
            "remediation_initial", "removal-original", altered, [index[k] for k in review.CHAIN[:6]]
        ),
        group(
            "remediation_final", "removal-original", altered, [index[k] for k in review.CHAIN[6:]]
        ),
    )
    return (
        {**roots, "remediation_initial": altered, "remediation_final": altered},
        replace(recipe, source_groups=selected),
    )


@pytest.mark.parametrize("version", [True, 1.0])
def test_repinned_native_chain_requires_integer_link_versions(inputs, tmp_path, version):
    def mutation(native, body):
        if (
            native["branch"] == "removal-b"
            and native["system"] == "validation_probes"
            and native["version"] == 2
        ):
            body["previous_events"][0]["version"] = version

    roots, recipe = changed_chain(inputs, tmp_path, mutation)
    with pytest.raises(CompanyStoreError):
        review.generate(tmp_path / "rejected", repository=ROOT, source_roots=roots, recipe=recipe)
    assert not (tmp_path / "rejected").exists()


@pytest.mark.parametrize(
    "fault", ["invented_execution", "extra_right", "late_predecessor", "wrong_source_period"]
)
def test_fully_repinned_internal_causal_contradictions_rejected(inputs, tmp_path, fault):
    def mutation(native, body):
        if native["branch"] != "removal-b":
            return
        if (
            fault == "invented_execution"
            and native["system"] == "execution_attempts"
            and native["version"] == 1
        ):
            body["removed_rights"] = ["billing-admin"]
        if (
            fault == "extra_right"
            and native["system"] == "entitlement_state"
            and native["version"] == 3
        ):
            body["rights"].append("unrequested-admin")
        if fault == "wrong_source_period":
            body["period_start"] = "2028-01-01T00:00:00+00:00"
            body["period_end_exclusive"] = "2028-04-01T00:00:00+00:00"
        if fault == "late_predecessor" and native["system"] == "removal_requests":
            native["available_at"] = (
                datetime.fromisoformat(body["period_end_exclusive"]) - timedelta(seconds=2)
            ).isoformat()

    roots, recipe = changed_chain(inputs, tmp_path, mutation)
    with pytest.raises(
        CompanyStoreError,
        match={
            "wrong_source_period": "period|span",
            "invented_execution": "execution must match",
            "extra_right": "resulting rights",
            "late_predecessor": "Predecessor unavailable",
        }[fault],
    ):
        review.generate(tmp_path / "rejected", repository=ROOT, source_roots=roots, recipe=recipe)
    assert not (tmp_path / "rejected").exists()


def test_final_source_recheck_failure_does_not_publish(inputs, tmp_path, monkeypatch):
    roots, recipe = inputs
    read = review.read_inputs
    calls = 0

    def changed(*args):
        nonlocal calls
        calls += 1
        values, pin = read(*args)
        return values, "f" * 64 if calls == 4 else pin

    monkeypatch.setattr(review, "read_inputs", changed)
    with pytest.raises(CompanyStoreError, match="changed before publication"):
        review.generate(tmp_path / "rejected", repository=ROOT, source_roots=roots, recipe=recipe)
    assert calls == 4
    assert not (tmp_path / "rejected").exists()
    assert not list(tmp_path.glob(".review-continuation-*"))


def test_final_code_pin_recheck_failure_does_not_publish(inputs, tmp_path, monkeypatch):
    roots, recipe = inputs
    code = (ROOT / "enterprise/audit_suite/company_access_review_continuation.py").read_bytes()
    digest = review.sha
    calls = 0

    def changed(value):
        nonlocal calls
        if value == code:
            calls += 1
            if calls == 2:
                return "f" * 64
        return digest(value)

    monkeypatch.setattr(review, "sha", changed)
    with pytest.raises(CompanyStoreError, match="pins changed before publication"):
        review.generate(tmp_path / "rejected", repository=ROOT, source_roots=roots, recipe=recipe)
    assert calls == 2
    assert not (tmp_path / "rejected").exists()


@pytest.mark.parametrize("scenario", ["missing_authorized", "unsupported_member"])
def test_source_limits_remain_unresolved_after_real_local_removal(inputs, tmp_path, scenario):
    from enterprise.audit_suite.company_access_remediation_activity import generate_pair
    from tests.audit_suite.test_company_access_remediation_activity import typed

    roots, recipe = inputs
    parent = recipe.source_groups[0]
    branch = parent.source_refs[0].branch

    other = next(
        r
        for r in rows(roots["identity"])
        if r["branch"] == branch
        and r["system"] == "application"
        and json.loads(r["content"]).get("person_id") == "P014"
        and r["version"] == 2
    )

    def missing_grant(native, body):
        if native["branch"] != branch:
            return
        if scenario == "unsupported_member":
            if native["system"] == "review_population":
                body["members"].append(
                    {
                        "person_id": "P014",
                        "record": other["record"],
                        "version": other["version"],
                        "sha256": other["sha256"],
                        "rights": json.loads(other["content"])["rights"],
                    }
                )
                body["membership_sha256"] = sha(encoded(body["members"]))
            if native["system"] == "review_reconciliation":
                body["missing_person_ids"] = []
            return
        if native["system"] == "application" and body.get("person_id") == "P015":
            body["rights"] = ["billing-admin"]
        if native["system"] == "review_population":
            for member in body["members"]:
                if member["person_id"] == "P015":
                    member["rights"] = ["billing-admin"]
            body["membership_sha256"] = sha(encoded(body["members"]))
        if native["system"] == "review_decisions":
            for decision in body["decisions"]:
                if decision["person_id"] == "P015":
                    decision["observed_rights"] = ["billing-admin"]

    altered_parent = tmp_path / "missing-authorized-parent"
    clone(roots["identity"], altered_parent, missing_grant)
    index = {
        (r["company"], r["branch"], r["system"], r["record"], r["version"]): r
        for r in rows(altered_parent)
    }
    selected = [
        index[(ref.company, ref.branch, ref.system, ref.record, ref.version)]
        for ref in parent.source_refs
    ]
    parent_group = group("identity", parent.source_store_id, altered_parent, selected)
    raw = json.loads((roots["remediation_initial"] / "SOURCE_RECEIPT.json").read_bytes())["recipe"]
    raw["source_refs"] = [
        {field: getattr(ref, field) for field in review.FIELDS} for ref in parent_group.source_refs
    ]
    raw["source_versions_sha256"] = parent_group.source_versions_sha256
    removal = tmp_path / "missing-authorized-removal"
    generate_pair(removal, repository=ROOT, source_root=altered_parent, recipe=typed(raw))
    native = {
        (r["system"], r["record"], r["version"]): r
        for r in rows(removal)
        if r["branch"] == "removal-b"
    }
    groups = (
        parent_group,
        group(
            "remediation_initial",
            "removal-original",
            removal,
            [native[k] for k in review.CHAIN[:6]],
        ),
        group(
            "remediation_final", "removal-original", removal, [native[k] for k in review.CHAIN[6:]]
        ),
    )
    output = tmp_path / "missing-authorized-review"
    review.generate(
        output,
        repository=ROOT,
        source_roots={
            "identity": altered_parent,
            "remediation_initial": removal,
            "remediation_final": removal,
        },
        recipe=replace(recipe, source_groups=groups),
    )
    created = {r["system"]: json.loads(r["content"]) for r in rows(output)}
    decision = created["review_decisions"]["decisions"][0]
    if scenario == "missing_authorized":
        assert decision["observed_rights"] == []
        assert decision["decision"] == "UNRESOLVED_MISSING_AUTHORIZED"
        assert decision["missing_authorized_rights"] == ["inventory-admin"]
    else:
        assert decision["decision"] == "RETAIN_AUTHORIZED"
        pop = created["review_population"]
        assert [m["person_id"] for m in pop["members"]] == ["P015"]
        assert pop["unsupported_prior_population_person_ids"] == ["P014"]
        assert pop["unresolved_parent_missing_person_ids"] == []
    assert created["review_reconciliation"]["unresolved_person_ids"] == ["P014"]
    assert created["review_reconciliation"]["whole_review_closed"] is False
    assert created["review_population"]["whole_quarter_operation"] == "NOT_ESTABLISHED"
