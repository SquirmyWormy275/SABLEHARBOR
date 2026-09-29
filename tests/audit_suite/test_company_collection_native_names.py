"""Future raw-byte collection names preserve validation and historical quarantine."""

from copy import deepcopy
from hashlib import sha256

import pytest

from tests.audit_suite import test_company_collection as fixtures


@pytest.fixture
def workspace(tmp_path):
    return fixtures.workspace.__wrapped__(tmp_path)


def collect(workspace, system, record, raw, name=None):
    engine, actor, state = workspace
    store = engine.company_store
    store.register_system("SH", "base", system, "owner")
    provenance = {"source_reference": record}
    if name is not None:
        provenance["name"] = name
    store.append_version(
        "SH",
        "base",
        system,
        record,
        expected_version=0,
        command_id="source-" + record,
        event_at="2027-01-01T00:00:00Z",
        available_at="2027-01-02T00:00:00Z",
        content=raw,
        provenance=provenance,
    )
    store.grant(actor, state["id"], "SH", "base", system)
    command = fixtures.envelope(state)
    command.update(command_id="collect-" + record)
    command["payload"].update(system_id=system, record_id=record)
    result = engine.command(actor, state["id"], command)
    return result, result["artifacts"][-1]


@pytest.mark.parametrize(
    "system,raw,suffix",
    [
        (
            "privileged_object",
            b"Local protected object for explicitly declared session actions.\n",
            ".txt",
        ),
        ("policy_document", b"# Policy\n\n**Status:** APPROVED DESIGN STANDARD\n", ".txt"),
        ("nonhuman_source", b"Exact local dependency bytes\n", ".txt"),
        ("copied_dataset", b"Exact locally copied bytes\n", ".txt"),
        ("unlabelled_envelope", b'{"retained":true}', ".json"),
    ],
)
def test_known_raw_originals_have_accurate_text_intake_and_exact_bytes(
    workspace, system, raw, suffix
):
    out, artifact = collect(workspace, system, "record-" + system, raw)
    assert artifact["name"].endswith(suffix)
    assert artifact["status"] == "AVAILABLE"
    assert workspace[0].artifacts.read(artifact) == raw
    assert artifact["sha256"] == sha256(raw).hexdigest()
    receipt = artifact["source"]["receipt"]["source"]
    assert receipt["system"] == system and receipt["version"] == 1
    assert receipt["sha256"] == artifact["sha256"]
    assert out["requests"][0]["company_collections"][-1]["source_identity"]["system"] == system


@pytest.mark.parametrize(
    "system,name", [("ordinary_envelope", None), ("privileged_object", "explicit.json")]
)
def test_malformed_json_and_explicit_producer_names_stay_quarantined(workspace, system, name):
    _, artifact = collect(workspace, system, "malformed", b'{"truncated":', name)
    assert artifact["name"].endswith(".json")
    assert artifact["status"] == "QUARANTINED"
    if name is not None:
        assert artifact["name"] == name


def test_binary_raw_object_is_not_silently_accepted_as_text(workspace):
    _, artifact = collect(workspace, "privileged_object", "binary", b"\xff\xfe\x00\x01")
    assert artifact["name"].endswith(".txt")
    assert artifact["status"] == "QUARANTINED"


def test_future_collection_does_not_unquarantine_retained_original(workspace):
    state, old = collect(
        workspace, "privileged_object", "old", b"Retained old plain text.\n", "legacy.json"
    )
    before = deepcopy(old)
    assert old["status"] == "QUARANTINED"
    engine, actor, _ = workspace
    out, new = collect((engine, actor, state), "privileged_object", "new", b"New plain text.\n")
    assert new["status"] == "AVAILABLE" and len(out["artifacts"]) == 2
    assert out["artifacts"][0] == before
