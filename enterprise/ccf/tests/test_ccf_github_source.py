import copy
import io
import json

import pytest

from enterprise.ccf.operations import github_source


@pytest.fixture
def source():
    pr = dict(
        number=146,
        merged=True,
        merged_at="2026-09-12T08:00:00Z",
        created_at="2026-09-11T08:00:00Z",
        updated_at="2026-09-12T08:00:00Z",
        base={"repo": {"full_name": "owner/repo"}},
        head={"sha": "a" * 40},
        merge_commit_sha="b" * 40,
        user={"id": 1},
    )
    review = dict(
        id=1,
        state="APPROVED",
        commit_id="a" * 40,
        submitted_at="2026-09-12T07:00:00Z",
        user={"id": 2},
    )
    scope = dict(
        origin="OPERATOR_SUPPLIED",
        boundary_id="corporate",
        period_start="2026-09-11T00:00:00Z",
        period_end="2026-09-13T00:00:00Z",
    )
    return pr, review, scope


def test_exact_native_commit_does_not_fabricate_artifact_or_policy(source):
    pr, review, scope = source
    record = github_source.normalize(pr, [review], scope, "owner", "repo")
    assert record["data"]["decision"] == "APPROVE"
    assert record["data"]["github_review_commit_id"] == pr["head"]["sha"]
    assert "protected_branch" not in record["data"]
    assert "reviewed_revision_sha256" not in record["data"]


@pytest.mark.parametrize(
    "change",
    [
        dict(state="DISMISSED"),
        dict(state="CHANGES_REQUESTED"),
        dict(commit_id="c" * 40),
        dict(submitted_at="2026-09-12T09:00:00Z"),
        dict(user={"id": 1}),
    ],
)
def test_unacceptable_review_does_not_approve(source, change):
    pr, review, scope = source
    review.update(change)
    assert (
        github_source.normalize(pr, [review], scope, "owner", "repo")["data"]["decision"]
        == "NOT_ESTABLISHED"
    )


def test_latest_substantive_and_other_reviewer_veto(source):
    pr, review, scope = source
    later = dict(review, id=2, state="CHANGES_REQUESTED", submitted_at="2026-09-12T07:10:00Z")
    assert (
        github_source.normalize(pr, [review, later], scope, "owner", "repo")["data"]["decision"]
        == "NOT_ESTABLISHED"
    )
    later["state"] = "COMMENTED"
    assert (
        github_source.normalize(pr, [review, later], scope, "owner", "repo")["data"]["decision"]
        == "APPROVE"
    )
    later.update(state="CHANGES_REQUESTED", user={"id": 3})
    assert (
        github_source.normalize(pr, [review, later], scope, "owner", "repo")["data"]["decision"]
        == "NOT_ESTABLISHED"
    )


def test_wrong_scope_repo_and_duplicate_rejected(source):
    pr, review, scope = source
    with pytest.raises(ValueError, match="Duplicate"):
        github_source.normalize(pr, [review, review], scope, "owner", "repo")
    with pytest.raises(ValueError, match="repository"):
        github_source.normalize(pr, [review], scope, "other", "repo")
    scope["period_end"] = "2026-09-12T00:00:00Z"
    with pytest.raises(ValueError, match="period"):
        github_source.normalize(pr, [review], scope, "owner", "repo")


def test_bounded_acquisition_and_original_bytes(source, monkeypatch):
    pr, review, scope = source
    urls = []

    class Opener:
        def open(self, request, timeout):
            urls.append(request.full_url)
            return io.BytesIO(
                json.dumps([review] if "/reviews?" in request.full_url else pr).encode()
            )

    monkeypatch.setattr(github_source.urllib.request, "build_opener", lambda *a: Opener())
    config = dict(owner="owner", repo="repo", pull_numbers=[146], scope=scope)
    result = github_source.acquire(config)
    assert result["test_outcome"] == "NOT_RUN"
    assert len(result["provenance"]["pages"]) == 3
    assert all(u.startswith("https://api.github.com/repos/owner/repo/pulls/146") for u in urls)
    with pytest.raises(ValueError, match="byte limit"):
        github_source.acquire(dict(config, max_bytes=1))


def test_duplicate_selection_and_pagination_limit(source, monkeypatch):
    pr, review, scope = source
    config = dict(owner="owner", repo="repo", pull_numbers=[146, 146], scope=scope)
    with pytest.raises(ValueError, match="distinct"):
        github_source.acquire(config)

    class Opener:
        def open(self, request, timeout):
            return io.BytesIO(
                json.dumps(
                    [dict(review, id=i) for i in range(100)]
                    if "/reviews?" in request.full_url
                    else pr
                ).encode()
            )

    monkeypatch.setattr(github_source.urllib.request, "build_opener", lambda *a: Opener())
    with pytest.raises(ValueError, match="pagination incomplete"):
        github_source.acquire(dict(config, pull_numbers=[146], max_pages_per_pr=1))


def test_unicode_secret_echo_rejected(source, monkeypatch):
    pr, review, scope = source
    monkeypatch.setenv("TEST_GITHUB_TOKEN", "secret-private-token")

    class Opener:
        def open(self, request, timeout):
            value = copy.deepcopy(pr)
            value["body"] = "secret-private-token"
            return io.BytesIO(
                json.dumps(value)
                .encode()
                .replace(b"secret-private-token", b"\\u0073ecret-private-token")
            )

    monkeypatch.setattr(github_source.urllib.request, "build_opener", lambda *a: Opener())
    with pytest.raises(ValueError, match="credential material"):
        github_source.acquire(
            dict(
                owner="owner",
                repo="repo",
                pull_numbers=[146],
                scope=scope,
                credential={"env": "TEST_GITHUB_TOKEN"},
            )
        )


def test_normalized_source_collects_and_enters_operator_case_not_run(source, tmp_path, monkeypatch):
    from enterprise.ccf.operations import collection, connectors, examples, store

    pr, review, scope = source
    scope["period_end"] = "2026-09-12T12:00:00Z"
    record = github_source.normalize(pr, [review], scope, "owner", "repo")
    evidence, census = tmp_path / "source.json", tmp_path / "independent-census.json"
    evidence.write_text(json.dumps([record]))
    # Explicit independent fixture roster, not populated from observed source rows.
    census.write_text('[{"id":"github:owner/repo:pull:146"}]')
    config = collection.config_template(evidence, census, scope)
    assert connectors.collect(config["evidence"])["records"][0]["origin"] == "OPERATOR_SUPPLIED"
    packet = collection.prepare_packets(
        config["evidence"], config["census"], [], "", "2026-09-12T13:00:00Z", "2026-10-01T00:00:00Z"
    )
    assert packet["ready_for_review"]
    plan = dict(
        id="GITHUB-CORPORATE",
        control_id="SH-ENG-002",
        boundary_id="corporate",
        adapter="revision_review",
        criteria={"BASE": "Review exact artifact and branch enforcement"},
    )
    path = tmp_path / "workflow.db"
    tokens = store.initialize(path, {plan["id"]: plan}, examples.principals(["corporate"]))
    monkeypatch.setattr(store, "now", lambda: "2026-09-12T14:00:00Z")
    case_scope = dict(
        scope,
        service="FIXTURE GitHub source contract",
        implementation_version="FIXTURE",
        criteria_authority="Fixture schema integration only, no real appointment",
    )
    packet["population"]["criteria_review"] = "Explicit fixture independent review only"
    db = store.connect(path)
    try:
        store.command(
            db,
            tokens["DEMO-PREPARER"],
            "CASE",
            "create",
            dict(plan_id=plan["id"], scope=case_scope),
            0,
        )
        store.command(db, tokens["DEMO-REVIEWER"], "CASE", "population", packet["population"], 1)
        result = store.command(db, tokens["DEMO-PREPARER"], "CASE", "intake", packet["intake"], 2)
        assert result["submissions"][-1]["result"]["outcome"] == "NOT_RUN"
        assert result["submissions"][-1]["result"]["checks"] == []
    finally:
        db.close()
