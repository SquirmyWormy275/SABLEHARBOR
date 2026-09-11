import hashlib
import json

import pytest

from enterprise.ccf.__main__ import build, verify


def test_complete_builds_are_identical_and_verified(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    build(a)
    build(b)
    assert {p.name: p.read_bytes() for p in a.iterdir()} == {
        p.name: p.read_bytes() for p in b.iterdir()
    }
    assert verify(a)["control"] == 166
    with pytest.raises(ValueError, match="never overwritten"):
        build(a)


def test_rehashed_false_conclusion_fails_reperformance(tmp_path):
    output = tmp_path / "package"
    build(output)
    p = output / "exercises.json"
    payload = json.loads(p.read_text())
    payload["cases"][0]["negative"]["outcome"] = "PASS"
    p.write_text(json.dumps(payload))
    manifest = json.loads((output / "MANIFEST.json").read_text())
    manifest["files"][p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    (output / "MANIFEST.json").write_text(json.dumps(manifest))
    (output / "SHA256SUMS.txt").write_text(
        "".join(
            f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
            for p in sorted(output.iterdir())
            if p.name != "SHA256SUMS.txt"
        )
    )
    with pytest.raises(ValueError, match="re-performance"):
        verify(output)
