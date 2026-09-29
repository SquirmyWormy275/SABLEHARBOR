import io
import json
import zipfile

import pytest

from enterprise.audit_suite import review
from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.store import DomainError, digest


def test_review_exact_input_consent_and_inert_locations(tmp_path, monkeypatch):
    engine = Engine(tmp_path / "state")
    manifest = engine.artifacts.retain(
        "ENG-fixture",
        "note.txt",
        b"Observed evidence",
        source={},
        coverage={},
    )
    extracted = review.extract(
        {**manifest, "name": "note.html"}, b"<p>Observed evidence</p><script>steal()</script>"
    )
    assert "steal" not in json.dumps(extracted)
    state = {k: [] for k in COLLECTIONS}
    state.update(
        id="ENG-fixture",
        revision=1,
        scope={"program_versions": {}},
        organization={},
        artifacts=[manifest],
        workpapers=[{"id": "WP-1", "versions": [{"version": 1, "artifact_id": manifest["id"]}]}],
    )
    prepared = review.prepare(state, engine.artifacts, selected_workpapers=["WP-1"])
    calls = []
    monkeypatch.setattr(review, "LocalInference", lambda *args: calls.append(args))
    with pytest.raises(DomainError):
        review.run(state, engine.artifacts, tmp_path / "missing", {"experimental_consent": False})
    with pytest.raises(DomainError):
        review.run(
            state,
            engine.artifacts,
            tmp_path / "missing",
            {"experimental_consent": True, "input_digest": "stale", "workpaper_ids": ["WP-1"]},
        )
    assert not calls
    assert (
        next(s for s in prepared["observable_layer"]["sources"] if "original_sha256" in s)[
            "original_sha256"
        ]
        == manifest["sha256"]
    )
    assert digest(prepared) == digest(
        review.prepare(state, engine.artifacts, selected_workpapers=["WP-1"])
    )


def test_learner_export_projects_every_history_snapshot(tmp_path):
    engine = Engine(tmp_path / "state")
    user = engine.store.provision("Trainer", ["instructor"])
    state = {k: [] for k in COLLECTIONS}
    state.update(
        title="Fixture",
        phase="ACTIVE",
        scope={"program_versions": {}},
        organization={},
        simulated_at="2027-01-01T00:00:00Z",
        custom_drafts=[{"id": "PRIVATE-DRAFT-MARKER"}],
        configuration={"secret": "PRIVATE-CONFIG-MARKER"},
    )
    state = engine.store.create(user["id"], state, "create")
    engine._export(
        state,
        {},
        {"actor": user["id"], "recorded_at": "now", "simulated_at": state["simulated_at"]},
    )
    data = engine.artifacts.read(state["artifacts"][-1])
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in ("engagement.json", "history.json"):
            assert b"PRIVATE-DRAFT-MARKER" not in archive.read(name)
            assert b"PRIVATE-CONFIG-MARKER" not in archive.read(name)
