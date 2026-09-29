import json

import pytest

from enterprise.audit_suite.generation import read_world
from enterprise.audit_suite.store import DomainError, digest


def test_world_hash_and_retained_generation_anchor_detect_changed_truth(tmp_path):
    world = {"world_integrity_version": 1, "variants": [{"fact": "Original"}]}
    world["world_sha256"] = digest(world)
    original_digest = digest(world)
    path = tmp_path / "world.json"
    path.write_text(json.dumps(world))
    assert read_world(path, original_digest) == world
    world["variants"][0]["fact"] = "Changed"
    path.write_text(json.dumps(world))
    with pytest.raises(DomainError, match="integrity"):
        read_world(path, original_digest)
    world["world_sha256"] = digest({k: v for k, v in world.items() if k != "world_sha256"})
    path.write_text(json.dumps(world))
    with pytest.raises(DomainError, match="retained generation"):
        read_world(path, original_digest)
