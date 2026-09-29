"""Later organization additions cannot rewrite sources pinned by J2 history."""

import json
import shutil
from pathlib import Path

import pytest

from enterprise.operations.historical_pins import PREDECESSORS, verify

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("source_path", sorted(PREDECESSORS))
def test_preserved_bytes_and_unchanged_predecessor_population(tmp_path, source_path):
    expected, preserved_path = PREDECESSORS[source_path]
    for relative in (source_path, preserved_path):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    assert verify(tmp_path, source_path, expected, failure="stale: ") == preserved_path

    current = tmp_path / source_path
    data = json.loads(current.read_text())
    if "chartbook" in source_path:
        data["nodes"][0]["name"] = "Changed earlier person"
    else:
        earlier = json.loads((tmp_path / preserved_path).read_text())
        earlier_id = earlier["people"][0]["person_id"]
        next(row for row in data["people"] if row["person_id"] == earlier_id)["name"] = (
            "Changed earlier person"
        )
    current.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="stale"):
        verify(tmp_path, source_path, expected, failure="stale: ")

    shutil.copyfile(ROOT / source_path, current)
    (tmp_path / preserved_path).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="stale"):
        verify(tmp_path, source_path, expected, failure="stale: ")
