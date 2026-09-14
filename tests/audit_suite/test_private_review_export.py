import io
import json
import zipfile
from types import SimpleNamespace

import pytest

from enterprise.audit_suite.artifacts import Artifacts
from enterprise.audit_suite.generation import private_json, run_directory
from enterprise.audit_suite.private_review_export import build
from enterprise.audit_suite.store import DomainError, Store


def test_private_export_preserves_bytes_and_excludes_unrelated_files(tmp_path):
    store = Store(tmp_path)
    actor = store.provision("Instructor", ["instructor"])
    engine = SimpleNamespace(store=store, artifacts=Artifacts(tmp_path))
    state = store.create(
        actor["id"],
        {
            "title": "<Training>",
            "scope": {},
            "artifacts": [],
        },
        "create",
    )
    original = b"record,value\nR1,12.50\n"
    manifest = engine.artifacts.retain(
        state["id"], "original.csv", original, source={}, coverage={}, generated=True
    )
    state["artifacts"].append(manifest)
    root = run_directory(engine, state["id"])
    private_json(root / "world.json", {"variants": [{"id": "selected-only"}]})
    private_json(root / "credentials.json", {"secret": "MUST_NOT_EXPORT"})
    result = build(engine, state, actor["id"])
    assert result["audience"] == "REVIEWER"
    with zipfile.ZipFile(io.BytesIO(engine.artifacts.read(result))) as archive:
        assert archive.read(f"files/{manifest['id']}/original.csv") == original
        assert json.loads(archive.read("private/world.json"))["variants"]
        assert "private/credentials.json" not in archive.namelist()
        assert "&lt;Training&gt;" in archive.read("index.html").decode()
        assert json.loads(archive.read("reviewer-appendix.json"))["overall_grade"] == "NOT_PROVIDED"
        assert len(json.loads(archive.read("history.json"))) == 1
    learner = store.provision("Learner", ["learner"])
    other = store.create(learner["id"], {"title": "Other", "scope": {}, "artifacts": []}, "new")
    with pytest.raises(DomainError):
        build(engine, other, learner["id"])
    state["artifacts"].append({**manifest, "engagement_id": other["id"]})
    with pytest.raises(DomainError, match="Cross-engagement"):
        build(engine, state, actor["id"])
