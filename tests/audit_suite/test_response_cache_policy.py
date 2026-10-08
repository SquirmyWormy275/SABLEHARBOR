"""Actual in-process ASGI response contracts; fictional endpoint collaborators.

The exact selected middleware and route bodies are compiled from repository
Source. No service/company constructor, product SQL or live HTTP is invoked.
This tests transport policy and export-byte guards, not company authorization.
"""

import ast
import asyncio
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.testclient import TestClient


class DomainError(ValueError):
    def __init__(self, message: str, *, code: str = "INVALID", status: int = 422):
        super().__init__(message)
        self.code, self.status = code, status


class RightsUnavailable(Exception):
    pass


@pytest.fixture
def transport():
    source = Path(__file__).resolve().parents[2] / "enterprise/audit_suite/service.py"
    tree = ast.parse(source.read_text())
    factory = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "create_app"
    )
    selected = {
        "domain_error",
        "headers_and_origin",
        "debrief_export",
        "rights_session",
        "rights_read",
        "company_rights_record",
        "company_rights_snippet",
        "company_rights_export",
    }
    nodes = [
        node
        for node in factory.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in selected
    ]
    assert {node.name for node in nodes} == selected
    app = FastAPI()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("fictional.txt", b"FICTIONAL NEUTRAL DEBRIEF ONLY\n")
    raw = stream.getvalue()
    calls, rate_calls, source_calls = [], [], []
    result = {
        "bytes": raw,
        "filename": "fictional-debrief.zip",
        "sha256": hashlib.sha256(raw).hexdigest(),
    }

    def export_confirm(principal, engagement, release, payload):
        calls.append((principal, engagement, release, payload))
        return dict(result)

    def release_store(request, *, mutation):
        assert mutation is True
        return {"id": "FICTIONAL-RECIPIENT"}, SimpleNamespace(export_confirm=export_confirm)

    async def json_body(request):
        return json.loads(await request.body())

    def direct(**kwargs):
        assert kwargs["token"] == "fictional-browser-session"
        source_calls.append(kwargs)
        return b"FICTIONAL COMPANY ORIGINAL\n"

    namespace = {
        "app": app,
        "Request": Request,
        "Response": Response,
        "JSONResponse": JSONResponse,
        "DomainError": DomainError,
        "RightsUnavailable": RightsUnavailable,
        "asyncio": asyncio,
        "hashlib": hashlib,
        "re": re,
        "urlsplit": urlsplit,
        "release_store": release_store,
        "json_body": json_body,
        "limits": SimpleNamespace(check=lambda *args: rate_calls.append(args)),
        "company_rights": SimpleNamespace(direct=direct),
        "session_cookie_name": "fictional-session-cookie",
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)

    @app.get("/api/neutral-public")
    async def public(cache: str | None = None):
        return JSONResponse(
            {"fictional": True}, headers={} if cache is None else {"Cache-Control": cache}
        )

    @app.get("/api/neutral-private")
    async def private(cache: str):
        return Response(b"fictional private bytes", headers={"Cache-Control": cache})

    @app.get("/api/engagements/ENG-neutral/company/rights/search")
    @app.get("/api/engagements/ENG-neutral/instructor-key/KEY-neutral/original")
    async def path_private():
        return Response(b"fictional path-private bytes")

    with TestClient(app, base_url="https://testserver") as client:
        client.cookies.set("fictional-session-cookie", "fictional-browser-session")
        yield SimpleNamespace(
            client=client,
            calls=calls,
            rate_calls=rate_calls,
            source_calls=source_calls,
            result=result,
            raw=raw,
        )


EXPORT = "/api/engagements/ENG-neutral/assistance/REL-neutral/export"


def assert_security(response, *, private=False):
    assert response.headers["cache-control"] == ("no-store, private" if private else "no-store")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(self)"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_successful_debrief_export_preserves_exact_private_zip_response(transport):
    response = transport.client.post(EXPORT, json={"fictional_confirmation": True})
    assert response.status_code == 200
    assert response.content == transport.raw
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["content-length"] == str(len(transport.raw))
    assert response.headers["x-content-sha256"] == hashlib.sha256(response.content).hexdigest()
    assert response.headers["content-disposition"] == 'attachment; filename="fictional-debrief.zip"'
    assert response.headers["pragma"] == "no-cache"
    assert len(transport.calls) == 1
    assert transport.calls[0][1:] == (
        "ENG-neutral",
        "REL-neutral",
        {"fictional_confirmation": True},
    )
    assert transport.rate_calls == [("debrief-export", {"id": "FICTIONAL-RECIPIENT"}, 12)]
    assert_security(response, private=True)


@pytest.mark.parametrize("mutation", ["bytes", "filename", "sha256"])
def test_export_byte_contract_still_fails_closed(transport, mutation):
    transport.result[mutation] = {
        "bytes": "not bytes",
        "filename": "../bad.zip",
        "sha256": "0" * 64,
    }[mutation]
    response = transport.client.post(EXPORT, json={"fictional_confirmation": True})
    assert response.status_code == 503
    assert len(transport.calls) == 1
    assert response.json()["error"] == "Debrief export integrity check failed"
    assert_security(response)


@pytest.mark.parametrize(
    "suffix,action", [("", "read"), ("/snippet", "snippet"), ("/export", "export")]
)
def test_exact_direct_company_source_paths_remain_private(transport, suffix, action):
    response = transport.client.get(
        "/api/engagements/ENG-neutral/company/rights/records/REC-neutral" + suffix
    )
    assert response.status_code == 200
    assert transport.source_calls == [
        {
            "token": "fictional-browser-session",
            "engagement_id": "ENG-neutral",
            "record_id": "REC-neutral",
            "action": action,
        }
    ]
    if action == "snippet":
        assert response.json() == {
            "record_id": "REC-neutral",
            "snippet": "FICTIONAL COMPANY ORIGINAL\n",
        }
    else:
        assert response.content == b"FICTIONAL COMPANY ORIGINAL\n"
        assert response.headers["x-content-sha256"] == hashlib.sha256(response.content).hexdigest()
    assert_security(response, private=True)


@pytest.mark.parametrize("cache", ["no-store, private", "PRIVATE, max-age=3600"])
def test_endpoint_private_directive_is_preserved_without_a_path_exception(transport, cache):
    response = transport.client.get("/api/neutral-private", params={"cache": cache})
    assert response.content == b"fictional private bytes"
    assert_security(response, private=True)


@pytest.mark.parametrize("cache", [None, "public, max-age=3600", "max-age=120"])
def test_ordinary_or_public_response_always_gets_no_store(transport, cache):
    response = transport.client.get(
        "/api/neutral-public", params={} if cache is None else {"cache": cache}
    )
    assert response.status_code == 200
    assert_security(response)


@pytest.mark.parametrize(
    "path",
    [
        "/api/engagements/ENG-neutral/company/rights/search",
        "/api/engagements/ENG-neutral/instructor-key/KEY-neutral/original",
    ],
)
def test_existing_private_path_rules_remain_without_endpoint_cache_header(transport, path):
    response = transport.client.get(path)
    assert response.status_code == 200
    assert_security(response, private=True)


@pytest.mark.parametrize("origin", ["https://other.example", "http://testserver"])
def test_real_origin_rejection_prevents_the_export_callback(transport, origin):
    response = transport.client.post(EXPORT, json={}, headers={"Origin": origin})
    assert response.status_code == 403
    assert response.json() == {"error": "Cross-origin mutation rejected"}
    assert transport.calls == [] and transport.rate_calls == []


def test_same_origin_export_executes_once_and_stays_private(transport):
    response = transport.client.post(EXPORT, json={}, headers={"Origin": "https://testserver"})
    assert response.status_code == 200
    assert len(transport.calls) == 1
    assert_security(response, private=True)
