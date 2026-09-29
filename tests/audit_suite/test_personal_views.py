from copy import deepcopy

import pytest

from enterprise.audit_suite.personal_views import PersonalViews
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_workspace_context import change
from tests.audit_suite.test_workspace_context import workspace as workspace


@pytest.fixture
def views(workspace, tmp_path):
    _, engine, actor, state = workspace
    state = change(engine, actor, state, lambda s: s["artifacts"][0].update(status="AVAILABLE"))
    root = tmp_path / "views"
    root.mkdir(mode=0o700)
    return PersonalViews(root, engine, max_active=2), engine, actor, state


def payload(v, actor, s):
    return {
        "title": "Backup sources",
        "section": "pbc",
        "query": "backup",
        "framework": "all",
        "reference": v.make_reference(actor, s["id"], kind="artifact", record_id="A1", version=2),
        "table": {"id": "artifacts", "query": "job", "sort": "name", "page": 2},
        "scroll_top": 410,
    }


def create(v, actor, s, p=None, command="save"):
    return v.create(
        actor,
        s["id"],
        p or payload(v, actor, s),
        expected_engagement_revision=s["revision"],
        command_id=command,
    )


def test_explicit_reload_restore_retains_filters_position_and_exact_target(views):
    v, e, a, s = views
    before = e.store.get(a, s["id"])
    p = payload(v, a, s)
    saved = create(v, a, s, p)
    assert saved["engagement_id"] == s["id"]
    assert saved["navigation"] is None and saved["restorable"] is True
    assert create(v, a, s, p) == saved
    reloaded = PersonalViews(v.root, e)
    result = reloaded.restore(
        a, s["id"], saved["id"], expected_version=1, expected_engagement_revision=s["revision"]
    )
    assert result["navigation"] == {k: value for k, value in p.items() if k != "title"}
    assert result["engagement_revision"] == s["revision"]
    assert e.store.get(a, s["id"]) == before
    assert v.path.stat().st_mode & 0o777 == 0o600


def test_cas_clear_replay_cannot_resurrect_private_content(views):
    v, _, a, s = views
    p = payload(v, a, s)
    saved = create(v, a, s, p)
    p2 = deepcopy(p)
    p2["table"]["page"] = 3
    saved2 = v.save(
        a,
        s["id"],
        saved["id"],
        p2,
        expected_version=1,
        expected_engagement_revision=s["revision"],
        command_id="update",
    )
    assert saved2["version"] == 2
    with pytest.raises(DomainError):
        v.save(
            a,
            s["id"],
            saved["id"],
            p,
            expected_version=1,
            expected_engagement_revision=s["revision"],
            command_id="stale",
        )
    clear = v.clear(
        a,
        s["id"],
        saved["id"],
        expected_version=2,
        expected_engagement_revision=s["revision"],
        command_id="clear",
    )
    assert clear["status"] == "CLEARED" and "user" not in clear and v.listing(a, s["id"]) == []
    assert create(v, a, s, p) == clear
    with pytest.raises(DomainError):
        v.restore(
            a, s["id"], saved["id"], expected_version=3, expected_engagement_revision=s["revision"]
        )
    with v._db() as db:
        assert db.execute("SELECT count(*) FROM history").fetchone()[0] == 3


@pytest.mark.parametrize(
    "basis", ["scope", "company_source_binding", "evidence_acquisition", "permissions"]
)
def test_basis_change_redacts_title_query_and_navigation(views, basis):
    v, e, a, s = views
    saved = create(v, a, s)

    def mutate(state):
        if basis == "scope":
            state["scope"]["period_end"] = "2027-12-31"
        else:
            state[basis] = {"changed": True} if basis != "permissions" else ["different"]

    latest = change(e, a, s, mutate)
    # Permissions are engine projected; use actual membership change for this case.
    if basis == "permissions":
        with e.store.connect() as db:
            db.execute(
                "UPDATE members SET permission='review' WHERE principal=? AND engagement=?",
                (a, s["id"]),
            )
    result = v.read(a, s["id"], saved["id"])
    assert result["engagement_id"] == s["id"]
    assert result["context_status"] == "CONTEXT_CHANGED" and "user" not in result
    assert result["navigation"] is None and result["restorable"] is False
    with pytest.raises(DomainError):
        v.restore(
            a,
            s["id"],
            saved["id"],
            expected_version=1,
            expected_engagement_revision=latest["revision"],
        )


def test_missing_original_and_historical_workpaper_never_substitute(views):
    v, e, a, s = views
    p = payload(v, a, s)
    saved = create(v, a, s, p)
    current = change(e, a, s, lambda x: x["artifacts"][0].update(status="QUARANTINED"))
    assert v.read(a, s["id"], saved["id"])["restorable"] is False
    with pytest.raises(DomainError):
        v.restore(
            a,
            s["id"],
            saved["id"],
            expected_version=1,
            expected_engagement_revision=current["revision"],
        )
    p.update(
        section="review",
        table={"id": "workpapers", "query": "", "sort": "version", "page": 0},
        reference=v.make_reference(a, s["id"], kind="workpaper", record_id="W1", version=1),
    )
    second = create(v, a, current, p, "paper")
    latest = change(
        e, a, s, lambda x: x["workpapers"][0]["versions"].append({"version": 2, "text": "new"})
    )
    restored = v.restore(
        a,
        s["id"],
        second["id"],
        expected_version=1,
        expected_engagement_revision=latest["revision"],
    )
    assert restored["target_status"] == "HISTORICAL_VERSION_AVAILABLE"
    assert restored["navigation"]["reference"]["version"] == 1


def test_principal_engagement_revocation_and_expiry_isolation(views):
    v, e, a, s = views
    saved = create(v, a, s)
    other = e.store.provision("Other", ["learner"])["id"]
    e.store.grant(s["id"], other, "learn")
    assert v.listing(other, s["id"]) == []
    with pytest.raises(DomainError):
        v.read(other, s["id"], saved["id"])
    another = deepcopy(e.store.get(a, s["id"]))
    another.pop("id")
    another.pop("revision")
    another = e.store.create(a, another, "other-engagement")
    with pytest.raises(DomainError):
        v.read(a, another["id"], saved["id"])
    with e.store.connect() as db:
        db.execute("DELETE FROM members WHERE engagement=? AND principal=?", (s["id"], a))
    with pytest.raises(DomainError):
        v.read(a, s["id"], saved["id"])


@pytest.mark.parametrize(
    "fault", ["section", "table", "sort", "page_bool", "scroll_float", "hidden", "stale_pin"]
)
def test_strict_payload_rejects_hidden_and_unbounded_navigation(views, fault):
    v, _, a, s = views
    p = payload(v, a, s)
    if fault == "section":
        p["section"] = "instructor-key"
    elif fault == "table":
        p["table"]["id"] = "private-key"
    elif fault == "sort":
        p["table"]["sort"] = "credentials"
    elif fault == "page_bool":
        p["table"]["page"] = True
    elif fault == "scroll_float":
        p["scroll_top"] = 1.0
    elif fault == "hidden":
        p["draft"] = "unsubmitted content"
    else:
        p["reference"]["sha256"] = "b" * 64
    with pytest.raises(DomainError):
        create(v, a, s, p)
    assert v.listing(a, s["id"]) == []


def test_authority_race_and_new_revision_save_fail_before_commit(views, monkeypatch):
    v, e, a, s = views
    p = payload(v, a, s)
    original = v._recheck

    def revoke(*args):
        with e.store.connect() as db:
            db.execute("DELETE FROM members WHERE engagement=? AND principal=?", (s["id"], a))
        original(*args)

    monkeypatch.setattr(v, "_recheck", revoke)
    with pytest.raises(DomainError):
        create(v, a, s, p)
    with v._db() as db:
        assert db.execute("SELECT count(*) FROM views").fetchone()[0] == 0


def test_private_alias_and_hardlink_denied(views, tmp_path):
    v, e, _, _ = views
    alias = tmp_path / "alias"
    alias.symlink_to(v.root, target_is_directory=True)
    with pytest.raises(DomainError):
        PersonalViews(alias, e)
    import os

    os.link(v.path, tmp_path / "copy.sqlite3")
    with pytest.raises(DomainError):
        PersonalViews(v.root, e)


def test_expired_principal_and_mutated_current_view_fail_closed(views):
    import json

    from enterprise.audit_suite.store import canonical, digest

    v, e, a, s = views
    saved = create(v, a, s)
    with v._db() as db:
        row = db.execute("SELECT content FROM views WHERE id=?", (saved["id"],)).fetchone()
        content = json.loads(row["content"])
        content["user"]["query"] = "forged"
        db.execute(
            "UPDATE views SET content=?,sha256=? WHERE id=?",
            (canonical(content), digest(content), saved["id"]),
        )
    with pytest.raises(DomainError, match="integrity"):
        v.read(a, s["id"], saved["id"])
    with e.store.connect() as db:
        db.execute("UPDATE principals SET expires=0 WHERE id=?", (a,))
    with pytest.raises(DomainError, match="expired"):
        v.listing(a, s["id"])


def test_quota_and_current_engagement_revision_are_explicit(views):
    v, e, a, s = views
    first = create(v, a, s)
    create(v, a, s, command="second")
    with pytest.raises(DomainError, match="quota"):
        create(v, a, s, command="third")
    current = change(e, a, s, lambda x: x.update(title="New title"))
    with pytest.raises(DomainError, match="Engagement changed"):
        v.save(
            a,
            s["id"],
            first["id"],
            payload(v, a, s),
            expected_version=1,
            expected_engagement_revision=s["revision"],
            command_id="old-revision",
        )
    result = v.read(a, s["id"], first["id"])
    assert result["revision_status"] == "ENGAGEMENT_ADVANCED"
    assert result["current_engagement_revision"] == current["revision"]


def test_scoped_program_filter_roundtrip_and_foreign_program_denial(views):
    v, e, a, s = views
    s = change(e, a, s, lambda x: x["scope"].update(programs=["SOC2"]))
    p = payload(v, a, s)
    p["framework"] = "SOC2"
    saved = create(v, a, s, p)
    assert (
        v.restore(
            a, s["id"], saved["id"], expected_version=1, expected_engagement_revision=s["revision"]
        )["navigation"]["framework"]
        == "SOC2"
    )
    p["framework"] = "FOREIGN"
    with pytest.raises(DomainError, match="Program filter"):
        create(v, a, s, p, command="foreign")


def test_duplicate_target_identity_and_bool_workpaper_version_denied(views):
    v, e, a, s = views
    p = payload(v, a, s)
    s = change(e, a, s, lambda x: x["artifacts"].append(deepcopy(x["artifacts"][0])))
    with pytest.raises(DomainError, match="unavailable"):
        create(v, a, s, p)
    p.update(
        section="review",
        table=None,
        reference={"kind": "workpaper", "id": "W1", "version": True, "sha256": "a" * 64},
    )
    with pytest.raises(DomainError, match="version unavailable"):
        create(v, a, s, p, command="bool")
