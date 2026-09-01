import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import Base
from sable_harbor.exports.release import package_public_demo, sha256
from sable_harbor.generation import generate_standard


def test_public_release_manifest_inventory_and_checksums(tmp_path: Path) -> None:
    database = tmp_path / "source.sqlite"
    engine = create_engine(f"sqlite:///{database}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        generate_standard(session)
        session.commit()
        manifest_path = package_public_demo(session, tmp_path / "release", git_commit="test")
    manifest = json.loads(manifest_path.read_text())
    assert manifest["validation_status"] == "PASS"
    assert manifest["classification"] == "PUBLIC_SAFE_SYNTHETIC"
    assert manifest["row_counts"]["journal_entry"] > 0
    for artifact in manifest["artifacts"]:
        path = manifest_path.parent / artifact["path"]
        assert path.exists()
        assert sha256(path) == artifact["sha256"]
    assert (manifest_path.parent / "sable_harbor_public_demo.sqlite").stat().st_size > 0
