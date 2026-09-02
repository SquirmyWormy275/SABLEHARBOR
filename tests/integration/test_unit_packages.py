import hashlib
import json
import sqlite3

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import Base
from sable_harbor.exports.safety import scan_generated_artifacts
from sable_harbor.exports.units import package_business_units
from sable_harbor.generation import generate_standard
from sable_harbor.provenance.service import complete_generation_run, record_generation_run


def test_all_current_business_units_get_scoped_reconciled_packages(tmp_path) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run = record_generation_run(
            session, profile="standard", scenario_code="base", seed=20260831, git_commit="test"
        )
        generate_standard(session)
        complete_generation_run(session, run)
        session.commit()
        manifests = package_business_units(
            session, tmp_path / "units", generation_run_id=run.id, generated_at=run.completed_at
        )

    assert len(manifests) == 7
    assert scan_generated_artifacts(tmp_path / "units") == []
    for manifest_path in manifests:
        root = manifest_path.parent
        manifest = json.loads(manifest_path.read_text())
        assert manifest["validation"]["status"] == "PASS"
        assert manifest["row_counts"]["journal_line_evidence"] > 0
        database = root / f"database/{manifest['unit_id']}.sqlite"
        with sqlite3.connect(database) as connection:
            entities = {
                row[0]
                for row in connection.execute(
                    "SELECT DISTINCT entity_code FROM journal_line_evidence"
                )
            }
        assert entities <= set(manifest["filters"]["entities"])
        for line in (root / "SHA256SUMS.txt").read_text().splitlines():
            expected, relative = line.split("  ", 1)
            assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected
