"""Bounded transport over fresh neutral fixtures; no actual company or Key inputs."""

from copy import deepcopy

import pytest

import enterprise.audit_suite.instructor_assessments as module
from enterprise.audit_suite.store import DomainError, canonical, digest
from tests.audit_suite.test_instructor_assessments import (
    assessment as assessment_fixture,
)
from tests.audit_suite.test_instructor_assessments import (
    payload,
)
from tests.audit_suite.test_instructor_comparison import advance
from tests.audit_suite.test_instructor_debrief_routes import (
    debrief_http as debrief_http_fixture,
)

assessment = assessment_fixture
debrief_http = debrief_http_fixture


def synthetic_refs(count):
    rows = []
    for n in range(count):
        base = {
            "kind": "request",
            "record_id": "REQUEST-" + str(n).zfill(8) + "-" + "x" * 100,
            "version": None,
            "inventory_sha256": digest({"n": n}),
            "content_sha256": None,
            "relation": "CONTROL_ASSOCIATION_ONLY",
        }
        rows.append({"id": "REF-" + digest(base), **base, "expectation_ids": ["E1"]})
    return rows


def view(core, args):
    return core.options_view(args["instructor_id"], args["engagement_id"], 0, catalogue=True)


def page(core, args, choices, **kwargs):
    c = choices["reference_catalogue"]
    return core.reference_page(
        args["instructor_id"],
        args["engagement_id"],
        0,
        context_sha256=c["context_sha256"],
        catalogue_sha256=c["sha256"],
        **kwargs,
    )


def test_all_pages_cover_exact_ordered_catalogue_without_duplicates(assessment, monkeypatch):
    core, _, args = assessment
    refs = synthetic_refs(83)
    monkeypatch.setattr(module, "references", lambda _: deepcopy(refs))
    choices = view(core, args)
    assert choices["references"] == []
    assert choices["reference_catalogue"]["count"] == 83
    assert choices["reference_catalogue"]["sha256"] == digest(refs)
    rows, offset = [], 0
    while offset is not None:
        result = page(core, args, choices, offset=offset)
        assert len(result["references"]) <= 40
        assert len(canonical(result).encode()) <= 8 * 1024 * 1024
        rows.extend(result["references"])
        offset = result["next_offset"]
    assert rows == refs
    assert len({r["id"] for r in rows}) == 83


def test_large_catalogue_full_http_refuses_but_rubric_page_save_read_work(assessment, monkeypatch):
    core, _, args = assessment
    refs = synthetic_refs(23000)
    monkeypatch.setattr(module, "references", lambda _: deepcopy(refs))
    complete = core.options(args["instructor_id"], args["engagement_id"], 0)
    assert len(canonical(complete).encode()) > 8 * 1024 * 1024
    with pytest.raises(DomainError, match="options byte limit"):
        core.options_view(args["instructor_id"], args["engagement_id"], 0)
    choices = view(core, args)
    assert choices["inventory_sha256"] == complete["inventory_sha256"]
    last = page(core, args, choices, offset=22999)
    assert last["references"] == refs[-1:]
    assert last["next_offset"] is None
    body = payload(core, args)
    body["dimensions"][0]["reference_ids"] = [refs[-1]["id"]]
    saved = core.save(args["instructor_id"], args["engagement_id"], body)
    assert saved["document"]["references"] == refs[-1:]
    assert (
        core.read(args["instructor_id"], args["engagement_id"], saved["id"])["document"]
        == saved["document"]
    )
    correction = {
        **body,
        "command_id": "correction",
        "predecessor": {"id": saved["id"], "sha256": saved["sha256"]},
    }
    assert core.save(args["instructor_id"], args["engagement_id"], correction)["version"] == 2


@pytest.mark.parametrize(
    "patch",
    [
        {"context_sha256": "0" * 64},
        {"catalogue_sha256": "0" * 64},
        {"offset": -1},
        {"offset": 84},
        {"offset": True},
        {"query": "x" * 201},
        {"expectation_ids": ["MISSING"]},
        {"reference_ids": ["FOREIGN"]},
        {"reference_ids": ["SAME", "SAME"]},
        {"reference_ids": [str(n) for n in range(33)]},
    ],
)
def test_rejects_tampered_context_selector_and_foreign_ids(assessment, monkeypatch, patch):
    core, _, args = assessment
    refs = synthetic_refs(83)
    monkeypatch.setattr(module, "references", lambda _: deepcopy(refs))
    choices = view(core, args)
    c = choices["reference_catalogue"]
    kw = {"context_sha256": c["context_sha256"], "catalogue_sha256": c["sha256"], **patch}
    with pytest.raises(DomainError):
        core.reference_page(args["instructor_id"], args["engagement_id"], 0, **kw)


def test_search_and_selected_reference_filter_are_presentational(assessment, monkeypatch):
    core, _, args = assessment
    refs = synthetic_refs(83)
    monkeypatch.setattr(module, "references", lambda _: deepcopy(refs))
    choices = view(core, args)
    selected = [refs[0]["id"], refs[-1]["id"]]
    result = page(core, args, choices, reference_ids=selected)
    assert result["references"] == [refs[0], refs[-1]]
    search = page(core, args, choices, query="REQUEST-00000082", expectation_ids=["E1"])
    assert search["references"] == refs[-1:]
    assert search["reference_catalogue"] == choices["reference_catalogue"]
    assert core.options(args["instructor_id"], args["engagement_id"], 0)["references"] == refs


def test_state_and_membership_changes_refuse_pages(assessment, monkeypatch):
    core, engine, args = assessment
    monkeypatch.setattr(module, "references", lambda _: synthetic_refs(1))
    choices = view(core, args)
    advance(engine, args, lambda state: {**state, "evidence_acquisition": "changed"})
    with pytest.raises(DomainError, match="catalogue context changed"):
        page(core, args, choices)
    monkeypatch.setattr(engine.store, "membership", lambda *_: "learn")
    with pytest.raises(DomainError) as error:
        page(core, args, choices)
    assert error.value.status == 403


def test_page_final_context_revalidation_after_projection(assessment, monkeypatch):
    core, _, args = assessment
    monkeypatch.setattr(module, "references", lambda _: synthetic_refs(1))
    choices = view(core, args)
    original = core._finish
    calls = []

    def finish(*args):
        calls.append(1)
        if len(calls) == 2:
            raise DomainError("Instructor access changed", status=403)
        return original(*args)

    monkeypatch.setattr(core, "_finish", finish)
    with pytest.raises(DomainError) as error:
        page(core, args, choices)
    assert error.value.status == 403 and len(calls) == 2


def test_selected_32_bound_remains_on_save(assessment, monkeypatch):
    core, _, args = assessment
    refs = synthetic_refs(33)
    monkeypatch.setattr(module, "references", lambda _: deepcopy(refs))
    body = payload(core, args)
    body["dimensions"][0]["reference_ids"] = [r["id"] for r in refs[:32]]
    assert (
        len(core.save(args["instructor_id"], args["engagement_id"], body)["document"]["references"])
        == 32
    )
    body["command_id"] = "too-many"
    body["dimensions"][1]["reference_ids"] = [refs[-1]["id"]]
    with pytest.raises(DomainError, match="Selected evidence reference limit"):
        core.save(args["instructor_id"], args["engagement_id"], body)


def test_rubric_and_indivisible_reference_transport_limits(assessment, monkeypatch):
    core, _, args = assessment
    refs = synthetic_refs(1)
    monkeypatch.setattr(module, "references", lambda _: deepcopy(refs))
    view(core, args)
    refs[0]["record_id"] = "x" * (8 * 1024 * 1024)
    with pytest.raises(DomainError) as error:
        page(core, args, view(core, args))
    assert error.value.status == 413
    data, context = core._options(args["instructor_id"], args["engagement_id"], 0)
    data["issues"][0]["claim"] = "x" * (8 * 1024 * 1024)
    monkeypatch.setattr(core, "_options", lambda *_: (data, context))
    with pytest.raises(DomainError, match="options byte limit"):
        view(core, args)


def test_catalogue_route_exact_query_role_and_default_compatibility(debrief_http, monkeypatch):
    app, client, state, teacher, student, _, headers, _ = debrief_http
    app.state.engine.company_bindings[state["id"]] = {"company": "C", "branch": "B"}
    monkeypatch.setattr(module, "references", lambda _: synthetic_refs(83))
    path = f"/api/engagements/{state['id']}/instructor-assessments"
    full = client.get(path + "/options?revision=1", headers=headers(teacher))
    assert full.status_code == 200 and len(full.json()["references"]) == 83
    response = client.get(path + "/options?revision=1&view=catalogue-v1", headers=headers(teacher))
    assert response.status_code == 200, response.text
    catalogue = response.json()["reference_catalogue"]
    params = {
        "revision": 1,
        "offset": 0,
        "context_sha256": catalogue["context_sha256"],
        "catalogue_sha256": catalogue["sha256"],
        "query": "",
        "expectation_ids": "[]",
        "reference_ids": "[]",
    }
    result = client.get(path + "/references", params=params, headers=headers(teacher))
    assert result.status_code == 200 and len(result.json()["references"]) == 40
    assert (
        client.get(path + "/references", params=params, headers=headers(student)).status_code == 403
    )
    assert (
        client.get(
            path + "/references", params={**params, "extra": "bad"}, headers=headers(teacher)
        ).status_code
        == 422
    )
    assert (
        client.get(
            path + "/references",
            params={**params, "expectation_ids": "{"},
            headers=headers(teacher),
        ).status_code
        == 422
    )
    assert (
        client.get(path + "/options?revision=1&view=wrong", headers=headers(teacher)).status_code
        == 422
    )


def test_adaptive_byte_pages_never_omit_or_repeat_rows(assessment, monkeypatch):
    core, _, args = assessment
    data, context = core._options(args["instructor_id"], args["engagement_id"], 0)
    # Generated valid-size identifiers model the existing 2000-expectation ceiling.
    eids = ["E1"] + ["EXPECT-" + str(n).zfill(4) + "-" + "x" * 110 for n in range(1999)]
    refs = synthetic_refs(40)
    for ref in refs:
        ref["expectation_ids"] = eids
    data["references"] = refs
    data["expectations"] = [
        {"id": e, "issue_ids": ["I1"], "procedure": "Authored", "acceptable_alternatives": []}
        for e in eids
    ]
    monkeypatch.setattr(core, "_options", lambda *_: (deepcopy(data), context))
    choices = view(core, args)
    first = page(core, args, choices)
    assert 0 < len(first["references"]) < 40
    assert len(canonical(first).encode()) <= 8 * 1024 * 1024
    second = page(core, args, choices, offset=first["next_offset"])
    assert first["references"] + second["references"] == refs
    assert second["next_offset"] is None
