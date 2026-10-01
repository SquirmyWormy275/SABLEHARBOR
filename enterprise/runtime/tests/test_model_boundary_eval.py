import copy

import pytest

from enterprise.runtime import model_boundary_eval as m

PRINCIPAL = {"id": "A", "tenant": "T", "purpose": "review"}
NOW = "2026-09-28T00:00:00"
PROBE = {
    "id": "OPEN_REGRESSION",
    "question": "What is the example date?",
    "resources": [
        {
            "id": "P1",
            "tenant": "T",
            "purposes": ["review"],
            "rights": "INTERNAL_REUSE",
            "classification": "OPEN",
            "payload": "The example date is 2026-09-28.",
        },
        {
            "id": "P2",
            "tenant": "T",
            "purposes": ["review"],
            "rights": "INTERNAL_REUSE",
            "classification": "OPEN",
            "payload": "Other user's private note",
            "memory_owner": "B",
        },
    ],
    "required": ["2026-09-28"],
    "forbidden": [],
}


def test_denied_source_and_personal_memory_never_enter_model_context():
    context = m.prepare(PROBE, PRINCIPAL, NOW)
    assert {source["id"] for source in context["authorized_sources"]} == {"P1"}


def test_malformed_identity_denies_every_probe_source():
    for invalid in (None, "", " ", [], 0):
        assert m.prepare(PROBE, dict(PRINCIPAL, tenant=invalid), NOW)["authorized_sources"] == []


def test_probe_does_not_promote_deleted_or_revoked_copy():
    probe = copy.deepcopy(PROBE)
    probe["resources"][0]["restore_suppressed"] = True
    assert m.prepare(probe, PRINCIPAL, NOW)["authorized_sources"] == []


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:9000",
        "http://example.com:9000",
        "http://127.0.0.1:9000/path",
        "http://user:pass@127.0.0.1:9000",
    ],
)
def test_model_endpoint_is_local_origin_only(url):
    with pytest.raises(ValueError):
        m.endpoint(url)


def test_model_endpoint_accepts_loopback():
    assert m.endpoint("http://127.0.0.1:18834") == "http://127.0.0.1:18834/v1/chat/completions"
