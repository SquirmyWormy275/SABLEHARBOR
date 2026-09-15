import json

import pytest

from tools.company_closeout.edition import EditionError, encoded, sha
from tools.company_closeout.transport import MAX_BYTES, prepare, verify_original


@pytest.mark.parametrize("content", [b"", b"ordinary", b"0123456789", bytes(range(27))])
def test_existing_store_bounds_preserve_originals(content):
    parts = prepare("public/source.bin", content, limit=10)
    stored = {p["record"]: p["content"] for p in parts}
    assert all(0 < len(value) <= MAX_BYTES for value in stored.values())
    verify_original("public/source.bin", sha(content), len(content), parts, stored.__getitem__)
    if 0 < len(content) <= 10:
        assert len(parts) == 1 and parts[0]["content"] == content
    else:
        assert parts[0]["kind"] == "TRANSPORT_MANIFEST"


@pytest.mark.parametrize("fault", ["missing", "duplicate", "reordered", "bytes", "source"])
def test_transport_rejects_population_and_identity_changes(fault):
    content = bytes(range(27))
    parts = prepare("public/source.bin", content, limit=10)
    stored = {p["record"]: p["content"] for p in parts}
    manifest = json.loads(parts[0]["content"])
    if fault == "missing":
        manifest["parts"].pop()
    elif fault == "duplicate":
        manifest["parts"].append(manifest["parts"][0])
    elif fault == "reordered":
        manifest["parts"].reverse()
    elif fault == "source":
        manifest["source_path"] = "different-source.bin"
    else:
        stored[parts[1]["record"]] = b"corrupted!"
    stored[parts[0]["record"]] = encoded(manifest)
    with pytest.raises(EditionError):
        verify_original("public/source.bin", sha(content), len(content), parts, stored.__getitem__)


def test_adapter_cannot_raise_pinned_store_limit():
    with pytest.raises(EditionError):
        prepare("public/source.bin", b"bytes", limit=MAX_BYTES + 1)
