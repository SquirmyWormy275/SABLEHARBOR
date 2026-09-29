import io
import os
import zipfile

import pytest

from enterprise.audit_suite import artifacts
from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.store import DomainError


def test_generated_human_review_over_upload_cap_retains_all_originals(tmp_path):
    engine = Engine(tmp_path / "state")
    user = engine.store.provision("Trainer", ["instructor"])
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="Large original package",
        phase="ACTIVE",
        scope={},
        organization={},
        simulated_at="2028-01-01T09:00:00Z",
    )
    state = engine.store.create(user["id"], state, "create")
    originals = []
    for index in range(2):
        # Valid UTF-8 originals under the per-upload cap, jointly incompressible
        # enough that the actual human-review ZIP exceeds 25 MiB.
        data = os.urandom(12 * 1024 * 1024).hex().encode()
        row = engine.artifacts.retain(
            state["id"], f"original-{index}.txt", data, source={}, coverage={}
        )
        assert row["status"] == "AVAILABLE" and row["bytes"] < artifacts.MAX_BYTES
        state["artifacts"].append(row)
        originals.append(row)
    engine._export(state, {}, {"actor": user["id"], "recorded_at": "2028-01-01T09:00:00Z"})
    manifest = state["artifacts"][-1]
    assert artifacts.MAX_BYTES < manifest["bytes"] < artifacts.MAX_EXPANDED
    package = engine.artifacts.read(manifest)
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        assert {"engagement.json", "history.json", "index.html", "manifest.json"} <= set(
            archive.namelist()
        )
        for row in originals:
            assert archive.read(f"files/{row['id']}/{row['name']}") == engine.artifacts.read(row)
    with pytest.raises(DomainError, match="oversized"):
        engine.artifacts.retain(
            state["id"], "caller.zip", package, source={}, coverage={}, generated=True
        )


def test_export_expansion_members_and_total_size_are_bounded(tmp_path, monkeypatch):
    store = artifacts.Artifacts(tmp_path)
    monkeypatch.setattr(artifacts, "MAX_EXPANDED", 4096)

    def package(name, data):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(name, data)
        return buf.getvalue()

    for data in [package("large.txt", b"a" * 5000), package("../escape", b"content"), b"x" * 4097]:
        with pytest.raises(DomainError):
            store.retain_export("ENG-fixture", "review.zip", data, source={}, coverage={})
    assert not list(store.root.iterdir())
