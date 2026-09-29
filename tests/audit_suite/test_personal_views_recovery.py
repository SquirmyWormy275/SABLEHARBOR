import json
from copy import deepcopy

import pytest

from enterprise.audit_suite.companion_recovery import backup, restore
from enterprise.audit_suite.personal_views import PersonalViews
from enterprise.audit_suite.personal_views_recovery import TABLES, validate
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_personal_views import create, payload
from tests.audit_suite.test_personal_views import views as views
from tests.audit_suite.test_workspace_context import change
from tests.audit_suite.test_workspace_context import workspace as workspace


def rows(v):
    with v._db() as db:
        return {name: [dict(r) for r in db.execute(f"SELECT * FROM {name}")] for name in TABLES}


def test_exact_histories_owner_mapping_current_permissions_and_second_restore(views, tmp_path):
    v, e, old, s = views
    saved = create(v, old, s)
    before = rows(v)
    bundle = tmp_path / "backup"
    manifest = backup(bundle, personal_views=v)
    assert set(manifest["component_captured_at"]) == {"personal_views"}
    new = e.store.provision("Replacement", ["learner"])["id"]
    e.store.grant(s["id"], new, "learn")
    e.store.revoke(old)
    destination = tmp_path / "restored"
    receipt = restore(bundle, destination, engine=e, principal_map={old: new})
    recovered = PersonalViews(destination / "personal-views", e)
    assert recovered.read(new, s["id"], saved["id"])["user"] == saved["user"]
    assert rows(recovered)["history"] == before["history"]
    assert receipt["credentials_or_grants_restored"] is False
    with pytest.raises(DomainError):
        recovered.read(old, s["id"], saved["id"])
    p = deepcopy(saved["user"])
    p["table"]["page"] = 1
    recovered.save(
        new,
        s["id"],
        saved["id"],
        p,
        expected_version=1,
        expected_engagement_revision=s["revision"],
        command_id="after-restore",
    )
    second = tmp_path / "backup2"
    backup(second, personal_views=recovered)
    newest = e.store.provision("Next replacement", ["learner"])["id"]
    e.store.grant(s["id"], newest, "learn")
    final = tmp_path / "restored2"
    restore(second, final, engine=e, principal_map={new: newest})
    again = PersonalViews(final / "personal-views", e)
    assert (
        again.restore(
            newest,
            s["id"],
            saved["id"],
            expected_version=2,
            expected_engagement_revision=s["revision"],
        )["navigation"]["table"]["page"]
        == 1
    )
    assert rows(again)["history"] == rows(recovered)["history"]
    assert len(rows(again)["ownership_history"]) == 2


def test_changed_basis_remains_redacted_and_unauthorized_map_never_publishes(views, tmp_path):
    v, e, old, s = views
    saved = create(v, old, s)
    bundle = tmp_path / "backup"
    backup(bundle, personal_views=v)
    new = e.store.provision("New", ["learner"])["id"]
    with pytest.raises(DomainError):
        restore(bundle, tmp_path / "denied", engine=e, principal_map={old: new})
    assert not (tmp_path / "denied").exists()
    e.store.grant(s["id"], new, "learn")
    latest = change(e, old, s, lambda x: x["scope"].update(period_end="2027-12-31"))
    restore(bundle, tmp_path / "restored", engine=e, principal_map={old: new})
    recovered = PersonalViews(tmp_path / "restored/personal-views", e)
    view = recovered.read(new, s["id"], saved["id"])
    assert "user" not in view and view["context_status"] == "CONTEXT_CHANGED"
    with pytest.raises(DomainError):
        recovered.restore(
            new,
            s["id"],
            saved["id"],
            expected_version=1,
            expected_engagement_revision=latest["revision"],
        )


@pytest.mark.parametrize(
    "fault",
    [
        "orphan",
        "owner",
        "bool_version",
        "command_owner",
        "missing_command",
        "missing_history",
        "extra_table",
        "untyped_title",
    ],
)
def test_typed_snapshot_corruption_rejected(views, fault):
    v, _, a, s = views
    create(v, a, s)
    data = rows(v)
    if fault == "orphan":
        data["history"][0]["view_id"] = "foreign"
    elif fault == "owner":
        data["views"][0]["actor"] = "foreign"
    elif fault == "bool_version":
        data["history"][0]["version"] = True
    elif fault == "command_owner":
        data["commands"][0]["actor"] = "foreign"
    elif fault == "missing_command":
        data["commands"] = []
    elif fault == "missing_history":
        data["history"] = []
    elif fault == "extra_table":
        data["credentials"] = []
    else:
        from enterprise.audit_suite.store import canonical, digest

        content = json.loads(data["history"][0]["content"])
        content["user"]["title"] = 42
        for row in [data["history"][0], data["views"][0]]:
            row.update(content=canonical(content), sha256=digest(content))
    with pytest.raises(DomainError):
        validate(data)


def test_clear_remains_available_at_edit_quota_and_snapshot_is_valid(views):
    v, _, a, s = views
    p = payload(v, a, s)
    saved = create(v, a, s, p)
    for version in range(1, 200):
        saved = v.save(
            a,
            s["id"],
            saved["id"],
            p,
            expected_version=version,
            expected_engagement_revision=s["revision"],
            command_id=f"edit-{version}",
        )
    with pytest.raises(DomainError, match="quota"):
        v.save(
            a,
            s["id"],
            saved["id"],
            p,
            expected_version=200,
            expected_engagement_revision=s["revision"],
            command_id="overflow",
        )
    cleared = v.clear(
        a,
        s["id"],
        saved["id"],
        expected_version=200,
        expected_engagement_revision=s["revision"],
        command_id="clear",
    )
    assert cleared["version"] == 201 and cleared["status"] == "CLEARED"
    validate(rows(v))


def test_changed_companion_and_revoked_restore_authority_do_not_publish(
    views, tmp_path, monkeypatch
):
    from enterprise.audit_suite import companion_recovery as recovery

    v, e, old, s = views
    create(v, old, s)
    bundle = tmp_path / "backup"
    backup(bundle, personal_views=v)
    new = e.store.provision("Replacement", ["learner"])["id"]
    e.store.grant(s["id"], new, "learn")
    original_read = recovery._read
    counts = {}

    def changed(path):
        raw = original_read(path)
        counts[path.name] = counts.get(path.name, 0) + 1
        return raw + b"\n" if path.name == "personal_views.json" and counts[path.name] > 1 else raw

    monkeypatch.setattr(recovery, "_read", changed)
    with pytest.raises(DomainError, match="source changed"):
        restore(bundle, tmp_path / "changed", engine=e, principal_map={old: new})
    assert not (tmp_path / "changed").exists()
    monkeypatch.setattr(recovery, "_read", original_read)
    original_restore = recovery.restore_views

    def revoked(*args):
        result = original_restore(*args)
        e.store.revoke(new)
        return result

    monkeypatch.setattr(recovery, "restore_views", revoked)
    with pytest.raises(DomainError, match="revoked"):
        restore(bundle, tmp_path / "revoked", engine=e, principal_map={old: new})
    assert not (tmp_path / "revoked").exists()


def test_rehashed_orphan_snapshot_rejected_by_actual_restore(views, tmp_path):
    import hashlib

    v, e, a, s = views
    create(v, a, s)
    bundle = tmp_path / "backup"
    backup(bundle, personal_views=v)
    member = bundle / "personal_views.json"
    body = json.loads(member.read_text())
    body["tables"]["commands"][0]["actor"] = "foreign-owner"
    raw = json.dumps(body).encode()
    member.write_bytes(raw)
    manifest = bundle / "MANIFEST.json"
    value = json.loads(manifest.read_text())
    value["members"][member.name] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    manifest.write_text(json.dumps(value))
    with pytest.raises(DomainError, match="Invalid personal-view snapshot"):
        restore(bundle, tmp_path / "denied", engine=e, principal_map={a: a})
    assert not (tmp_path / "denied").exists()
