"""Bounded normalized exports. Collection establishes provenance, never assurance."""

import base64
import csv
import hashlib
import http.client
import io
import ipaddress
import json
import os
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .testing import instant, nonempty


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Connector redirects are forbidden")


class PublicHTTPSConnection(http.client.HTTPSConnection):
    """Resolve once per connection, reject private addresses and pin the socket."""

    def connect(self):
        if self._tunnel_host:
            raise ValueError("Proxy tunnels forbidden")
        addresses = socket.getaddrinfo(self.host, self.port, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError("Public endpoint required")
        last_error = None
        for family, socktype, proto, _, address in addresses:
            connection = socket.socket(family, socktype, proto)
            connection.settimeout(self.timeout)
            try:
                connection.connect(address)
                self.sock = self._context.wrap_socket(connection, server_hostname=self.host)
                return
            except OSError as error:
                connection.close()
                last_error = error
        raise OSError("Public endpoint connection failed") from last_error


class PublicHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, request):
        return self.do_open(PublicHTTPSConnection, request, context=ssl.create_default_context())


def _credential(ref):
    if set(ref) == {"env"}:
        secret = os.environ.get(nonempty(ref["env"]), "")
    elif set(ref) == {"file"}:
        path = Path(ref["file"])
        if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
            raise ValueError("Credential file must be private and regular")
        secret = path.read_text().strip()
    else:
        raise ValueError("Use exactly one credential env or file reference")
    if not secret or any(c in secret for c in "\r\n"):
        raise ValueError("Credential missing or invalid")
    return secret


def _url(url, endpoint, allow_test_http=False):
    p, base = urllib.parse.urlsplit(url), urllib.parse.urlsplit(endpoint)
    if p.username or p.password or p.fragment:
        raise ValueError("URL credentials and fragments forbidden")
    if (p.scheme, p.hostname, p.port, p.path) != (base.scheme, base.hostname, base.port, base.path):
        raise ValueError("Pagination must stay on the exact configured endpoint")
    if allow_test_http and p.scheme == "http" and p.hostname == "127.0.0.1":
        return
    if p.scheme != "https" or not p.hostname:
        raise ValueError("HTTPS required")
    addresses = socket.getaddrinfo(p.hostname, p.port or 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("Public endpoint required")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate source JSON key")
        result[key] = value
    return result


def _contains_secret(value, secret):
    if isinstance(value, str):
        return secret in value
    if isinstance(value, dict):
        return any(
            _contains_secret(k, secret) or _contains_secret(v, secret) for k, v in value.items()
        )
    if isinstance(value, list):
        return any(_contains_secret(v, secret) for v in value)
    return False


def collect(config, *, allow_test_http=False):
    """Return normalized rows and raw-page hashes; raises on incomplete exports.

    HTTPS envelope: {records: [...], total: integer, next: URL-or-null}.
    CSV data column contains a JSON object. Census rows are {id: string}.
    The test HTTP exception is code-only, never available from configuration/CLI.
    """
    kind = config["type"]
    maximum = config.get("max_bytes", 5_000_000)
    pages = config.get("max_pages", 100)
    timeout = config.get("timeout_seconds", 15)
    if type(maximum) is not int or not 1 <= maximum <= 10_000_000:
        raise ValueError("Invalid byte limit")
    if type(pages) is not int or not 1 <= pages <= 1000 or not 0 < timeout <= 60:
        raise ValueError("Invalid request limits")
    source = nonempty(config["source_system"])
    nonempty(config["query"])
    rows, hashes, raw_pages, consumed = [], [], [], 0
    if kind in {"local_json", "local_csv"}:
        path = Path(config["path"])
        if path.is_symlink() or not path.is_file():
            raise ValueError("Export must be a regular non-symlink file")
        with path.open("rb") as handle:
            raw = handle.read(maximum + 1)
        if len(raw) > maximum:
            raise ValueError("Export exceeds byte limit")
        hashes.append(hashlib.sha256(raw).hexdigest())
        raw_pages.append(base64.b64encode(raw).decode("ascii"))
        if kind == "local_json":
            rows = json.loads(raw)
        else:
            rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
            for row in rows:
                if "data" in row:
                    row["data"] = json.loads(row["data"])
        locator = str(path.resolve())
    elif kind == "https_json":
        endpoint = config["endpoint"]
        # Query strings may contain secrets: all parameters must be passed separately.
        if urllib.parse.urlsplit(endpoint).query:
            raise ValueError("Endpoint query forbidden; use non-secret parameters")
        params = config.get("parameters", {})
        if any(
            any(s in key.lower() for s in ("token", "secret", "password", "key")) for key in params
        ):
            raise ValueError("Credentials cannot be query parameters")
        url = endpoint + ("?" + urllib.parse.urlencode(params) if params else "")
        secret = _credential(config["credential"])
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect(), PublicHTTPSHandler()
        )
        seen, total = set(), None
        while url is not None:
            if url in seen or len(seen) >= pages:
                raise ValueError("Repeated cursor or page limit exceeded")
            _url(url, endpoint, allow_test_http)
            seen.add(url)
            request = urllib.request.Request(
                url, headers={"Authorization": "Bearer " + secret, "Accept": "application/json"}
            )
            try:
                with opener.open(request, timeout=timeout) as response:
                    raw = response.read(maximum - consumed + 1)
                consumed += len(raw)
                if consumed > maximum:
                    raise ValueError("Export exceeds byte limit")
                if secret.encode() in raw:
                    raise ValueError("Source response contains credential material")
                envelope = json.loads(raw, object_pairs_hook=_unique_object)
                if _contains_secret(envelope, secret):
                    raise ValueError("Decoded source response contains credential material")
            except (urllib.error.URLError, TimeoutError, OSError):
                raise ValueError("Source request failed; no collection published") from None
            if not isinstance(envelope, dict) or set(envelope) != {"records", "total", "next"}:
                raise ValueError("Expected explicit records, total and next envelope")
            count = envelope["total"]
            if type(count) is not int or count < 0 or (total is not None and total != count):
                raise ValueError("Population count changed during pagination")
            total = count
            if not isinstance(envelope["records"], list):
                raise ValueError("Records must be an array")
            rows.extend(envelope["records"])
            hashes.append(hashlib.sha256(raw).hexdigest())
            raw_pages.append(base64.b64encode(raw).decode("ascii"))
            nxt = envelope["next"]
            if nxt is not None and (not isinstance(nxt, str) or not nxt):
                raise ValueError("Invalid next cursor")
            url = urllib.parse.urljoin(endpoint, nxt) if nxt else None
        if len(rows) != total:
            raise ValueError("Incomplete export: reported total differs from collected rows")
        locator = endpoint
    else:
        raise ValueError("Unknown connector type")
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        raise ValueError("Export must contain object rows")
    ids = [nonempty(r["id"]) for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate source IDs")
    if config.get("purpose", "evidence") == "evidence":
        scope = config["scope"]
        if scope["origin"] not in {"SYNTHETIC", "OPERATOR_SUPPLIED"}:
            raise ValueError("Workflow-compatible source origin required")
        nonempty(scope["boundary_id"])
        if instant(scope["period_start"]) > instant(scope["period_end"]):
            raise ValueError("Invalid source scope period")
        for row in rows:
            if row["boundary_id"] != scope["boundary_id"] or row["origin"] != scope["origin"]:
                raise ValueError("Source record has wrong boundary or origin")
            if (
                not instant(scope["period_start"])
                <= instant(row["occurred_at"])
                <= instant(scope["period_end"])
            ):
                raise ValueError("Source record falls outside assessment period")
    elif config["purpose"] != "census":
        raise ValueError("Unknown collection purpose")
    return dict(
        records=rows,
        provenance=dict(
            source_system=source,
            locator=locator,
            query=config["query"],
            connector_type=kind,
            raw_page_sha256=hashes,
            raw_pages_base64=raw_pages,
            source_count=len(rows),
            transformation_version="normalized-export-v1",
        ),
    )
