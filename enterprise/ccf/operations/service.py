"""Bounded WSGI API: verified OIDC principal enters the store's trusted boundary."""

import argparse
import json
import os
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit
from wsgiref.simple_server import WSGIRequestHandler, make_server

from . import store
from .identity import AuthenticationError, Identity, private_json

LIMIT = 2_097_152


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


class Application:
    def __init__(self, database, identity, public_origin, *, allow_loopback_http=False):
        parsed = urlsplit(public_origin)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Exact HTTPS public origin required")
        self.allow_loopback_http = allow_loopback_http
        self.database = Path(database)
        self.identity = identity
        self.origin = public_origin
        self.host = parsed.netloc
        db = store.connect(self.database)
        try:
            store.configuration(db)
        finally:
            db.close()

    def __call__(self, env, start_response):
        status, result = "500 Internal Server Error", {"error": "Service unavailable"}
        try:
            if env.get("REMOTE_ADDR", "") not in {"", "127.0.0.1", "::1"}:
                raise ValueError("Local transport required")
            if env.get("wsgi.url_scheme") != "https" and not self.allow_loopback_http:
                raise ValueError("TLS proxy required")
            if (
                env.get("HTTP_HOST") != self.host
                or env.get("HTTP_ORIGIN", self.origin) != self.origin
                or env.get("QUERY_STRING")
            ):
                raise ValueError("Invalid request destination")
            if env.get("HTTP_TRANSFER_ENCODING"):
                raise ValueError("Transfer encoding is not supported")
            actor = self.identity.authenticate(env.get("HTTP_AUTHORIZATION"))
            method, path = env.get("REQUEST_METHOD"), env.get("PATH_INFO")
            if (method, path) not in {
                ("GET", "/v1/report"),
                ("POST", "/v1/command"),
                ("POST", "/v1/revoke"),
            }:
                status, result = "404 Not Found", {"error": "Unknown endpoint"}
            else:
                body = {}
                if method == "POST":
                    if env.get("CONTENT_TYPE") != "application/json":
                        raise ValueError("JSON content type required")
                    raw_length = env.get("CONTENT_LENGTH", "")
                    if not raw_length.isascii() or not raw_length.isdecimal():
                        raise ValueError("Content length required")
                    length = int(raw_length)
                    if not 1 <= length <= LIMIT:
                        raise ValueError("Invalid request size")
                    raw = env["wsgi.input"].read(length)
                    if len(raw) != length:
                        raise ValueError("Incomplete request")
                    body = json.loads(
                        raw,
                        object_pairs_hook=object_pairs,
                        parse_constant=lambda _: (_ for _ in ()).throw(
                            ValueError("Invalid JSON number")
                        ),
                    )
                    if not isinstance(body, dict):
                        raise ValueError("JSON object required")
                db = store.connect(self.database)
                try:
                    if path == "/v1/report":
                        result = store.report_as(db, actor)
                    elif path == "/v1/revoke":
                        if set(body) != {"subject"} or not isinstance(body["subject"], str):
                            raise ValueError("Invalid revocation")
                        store.revoke_as(db, actor, body["subject"])
                        result = {"revoked": True}
                    else:
                        if (
                            set(body) != {"case_id", "action", "payload", "expected_revision"}
                            or not isinstance(body["payload"], dict)
                            or not isinstance(body["case_id"], str)
                            or not isinstance(body["action"], str)
                        ):
                            raise ValueError("Invalid command")
                        if {"actor", "at", "clock", "result"} & set(body["payload"]):
                            raise ValueError("Reserved command fields")
                        result = store.command_as(db, actor, **body)
                    status = "200 OK"
                finally:
                    db.close()
        except AuthenticationError:
            status, result = "401 Unauthorized", {"error": "Invalid access token"}
        except (ValueError, KeyError, TypeError, UnicodeError, OverflowError, RecursionError):
            # Do not echo database details, submitted records, tokens or identity claims.
            status, result = (
                "400 Bad Request",
                {"error": "Request rejected; check scope, permissions, payload and revision"},
            )
        except (sqlite3.Error, OSError):
            pass
        encoded = json.dumps(result, allow_nan=False, separators=(",", ":")).encode()
        headers = [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(encoded))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
        ]
        if status.startswith("401"):
            headers.append(("WWW-Authenticate", "Bearer"))
        start_response(status, headers)
        return [encoded]


def from_environment(*, allow_loopback_http=False):
    return Application(
        os.environ["CCF_DATABASE"],
        Identity(private_json(os.environ["CCF_IDENTITY_CONFIG"])),
        os.environ["CCF_PUBLIC_ORIGIN"],
        allow_loopback_http=allow_loopback_http,
    )


class QuietHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Loopback CCF development API; TLS proxy required for external access"
    )
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    with make_server(
        "127.0.0.1",
        args.port,
        from_environment(allow_loopback_http=True),
        handler_class=QuietHandler,
    ) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
