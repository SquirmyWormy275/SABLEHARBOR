"""Build an isolated local pilot from a verified CCF delivery; never deploy externally."""

import argparse
import ipaddress
import json
import os
import shlex
import ssl
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from . import delivery, store

ROOT = Path(__file__).resolve().parents[3]


def private_write(path, content, executable=False):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(content)
    if executable:
        path.chmod(0o700)


def certificates(output):
    """Private thirty-day localhost CA; never install it into machine trust."""
    output.mkdir(mode=0o700)
    now = datetime.now(timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "CCF LOCAL PILOT ONLY")])
    ca = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(False, False, False, False, False, True, True, False, False),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]))
        .issuer_name(ca_name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
            ),
            critical=False,
        )
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]), critical=False
        )
        .sign(ca_key, hashes.SHA256())
    )
    for name, data in [
        ("ca.pem", ca.public_bytes(serialization.Encoding.PEM)),
        ("server.pem", cert.public_bytes(serialization.Encoding.PEM)),
        (
            "server.key",
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            ),
        ),
    ]:
        private_write(output / name, data.decode())
    # The CA signing key is intentionally not retained: recreate the isolated pilot to renew.


def build(delivery_path, output, keycloak_home=None, java_home=None):
    from . import pilot_identity

    if bool(keycloak_home) != bool(java_home):
        raise ValueError("Supply both Keycloak and Java runtime directories")
    if keycloak_home:
        keycloak_home, java_home = Path(keycloak_home).resolve(), Path(java_home).resolve()
        if not (keycloak_home / "bin/kc.sh").is_file() or not (java_home / "bin/java").is_file():
            raise ValueError("Runtime directories lack Keycloak or Java executables")
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("Pilot requires a new private directory")
    delivery.verify(delivery_path)
    db = store.connect(Path(delivery_path) / "control-exercise/workflow.sqlite3")
    try:
        plans = store.configuration(db)["plans"]
    finally:
        db.close()
    boundaries = sorted({p["boundary_id"] for p in plans.values()})
    now = datetime.now(timezone.utc)
    principals = [
        dict(
            id="PILOT-" + role.upper(),
            permissions=[permission],
            boundaries=boundaries,
            valid_from=(now - timedelta(seconds=1)).isoformat(),
            expires_at=(now + timedelta(days=30)).isoformat(),
        )
        for role, permission in [
            ("preparer", "prepare"),
            ("reviewer", "review"),
            ("operator", "admin"),
        ]
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ccf-pilot-", dir=output.parent) as tmp:
        staged = Path(tmp) / "pilot"
        staged.mkdir(mode=0o700)
        certificates(staged / "tls")
        (staged / "evidence").mkdir(mode=0o700)
        # Random local CLI tokens are deliberately not distributed; use the pinned IdP bindings.
        store.initialize(staged / "workflow.sqlite3", plans, principals)
        identity = pilot_identity.build(
            staged / "identity",
            principals,
            tls={
                "ca_pem": (staged / "tls/ca.pem").read_bytes(),
                "server_pem": (staged / "tls/server.pem").read_bytes(),
                "server_key_pem": (staged / "tls/server.key").read_bytes(),
            },
        )
        identity["output"] = str(output / "identity")
        private_write(staged / "PRINCIPALS.json", json.dumps(principals, indent=2) + "\n")
        settings = dict(
            CCF_DATABASE=str(output / "workflow.sqlite3"),
            CCF_IDENTITY_CONFIG=str(output / "identity/identity.json"),
            CCF_PUBLIC_ORIGIN="https://localhost:8765",
        )
        command = [
            str(ROOT / ".venv/bin/gunicorn"),
            "--config",
            str(ROOT / "enterprise/ccf/operations/deploy/gunicorn.conf.py"),
            "--certfile",
            str(output / "tls/server.pem"),
            "--keyfile",
            str(output / "tls/server.key"),
            "enterprise.ccf.operations.service:from_environment()",
        ]
        private_write(
            staged / "start-api.sh",
            "#!/bin/sh\nset -eu\numask 077\ncd "
            + shlex.quote(str(ROOT))
            + "\n"
            + "\n".join("export " + k + "=" + shlex.quote(v) for k, v in settings.items())
            + "\nexec "
            + shlex.join(command)
            + "\n",
            executable=True,
        )
        runtime_env = (
            (
                "export KEYCLOAK_HOME="
                + shlex.quote(str(keycloak_home))
                + "\nexport JAVA_HOME="
                + shlex.quote(str(java_home))
                + "\n"
            )
            if keycloak_home
            else ': "${KEYCLOAK_HOME:?Set the private Keycloak distribution path}"\n: "${JAVA_HOME:?Set the private Java runtime path}"\n'
        )
        private_write(
            staged / "start-identity.sh",
            "#!/bin/sh\nset -eu\numask 077\n"
            + runtime_env
            + "exec "
            + shlex.join(
                [str(ROOT / ".venv/bin/python"), str(output / "identity/start-keycloak.py")]
            )
            + "\n",
            executable=True,
        )
        python = shlex.quote(str(ROOT / ".venv/bin/python"))
        pilot_root = shlex.quote(str(output))
        identity_root = shlex.quote(str(output / "identity"))
        wrapper = (
            "#!/bin/sh\nset -eu\numask 077\ncd "
            + shlex.quote(str(ROOT))
            + "\n"
            + "case ${1:-help} in\n"
            + "  identity) exec "
            + shlex.quote(str(output / "start-identity.sh"))
            + ";;\n"
            + "  pin|device|poll) exec "
            + python
            + ' -m enterprise.ccf.operations.pilot_identity "$1" --root '
            + identity_root
            + ";;\n"
            + "  api) exec "
            + shlex.quote(str(output / "start-api.sh"))
            + ";;\n"
            + '  report) test "$#" -eq 2; exec '
            + python
            + " -m enterprise.ccf.operations.pilot report --pilot "
            + pilot_root
            + " --token-file "
            + shlex.quote(str(output / "identity/access-token.json"))
            + ' --output "$2";;\n'
            + '  source) test "$#" -eq 2; exec '
            + python
            + " -m enterprise.ccf.operations.github_source "
            + shlex.quote(str(output / "github-source.example.json"))
            + ' --output "$2";;\n'
            + "  *) echo 'Usage: run.sh identity|pin|device|poll|api|report <new-private-json>|source <new-private-directory>';;\nesac\n"
        )
        private_write(staged / "run.sh", wrapper, executable=True)
        result = dict(
            status="LOCAL_PILOT_PREPARED_NOT_DEPLOYED",
            identity_provider="Keycloak",
            issuer="https://localhost:8443/realms/ccf-pilot",
            audience="ccf-api",
            api_origin=settings["CCF_PUBLIC_ORIGIN"],
            plans=len(plans),
            controls=len({p["control_id"] for p in plans.values()}),
            identity_setup=identity,
            source_candidate="GitHub pull-request reviews, read-only; independent census and missing control facts require review",
            actual_appointments=[],
            actual_assurance="NOT_ASSERTED",
        )
        private_write(staged / "PILOT_SYSTEM.json", json.dumps(result, indent=2) + "\n")
        private_write(
            staged / "github-source.example.json",
            json.dumps(
                dict(
                    owner="SquirmyWormy275",
                    repo="SABLEHARBOR",
                    pull_numbers=[146],
                    scope=dict(
                        origin="OPERATOR_SUPPLIED",
                        boundary_id="corporate",
                        period_start="2026-09-12T00:00:00Z",
                        period_end="2026-09-12T19:00:00Z",
                    ),
                    max_pages_per_pr=20,
                    max_bytes=10000000,
                    timeout_seconds=15,
                ),
                indent=2,
            )
            + "\n",
        )
        private_write(
            staged / "START_HERE.md",
            "# Your local CCF pilot\n\nThis is a working-system pilot with three test identities, not an operating assessment or actual owner appointment. Existing synthetic assessment cases are not copied into its empty database.\n\n1. Run `./run.sh identity` in one terminal. If private runtime paths were not supplied at build time, set them as described in `identity/README.md`. This starts Keycloak with the generated realm and explicit localhost TLS on port 8443. Wait until startup completes.\n2. Run this folder's `./run.sh pin` to pin its public signing keys with this pilot's explicit CA; never disable certificate verification or install this CA globally.\n3. Run `./run.sh api` for the CCF API on https://localhost:8765. It uses Gunicorn with direct TLS, bound to loopback.\n4. Run `./run.sh device`, open its returned login URL, and use a test identity from private `identity/pilot-credentials.json`. Then run `./run.sh poll` and `./run.sh report /absolute/path/to/new-report.json`. The helper uses the explicit CA and keeps the access token out of command arguments. Test preparer, reviewer and operator are separate subjects.\n5. Acquire the selected public PR with `./run.sh source /absolute/path/to/new-pr146-evidence`. The dated example is a bounded acquisition selection, not a complete assessment population; retain its raw provenance. An independent person must approve the complete population and supply missing historical control facts. No fetched record silently passes a control.\n\nUse the repository's pilot-system design for the move to a private Linux host, actual identity appointments, monitored backups and eventual Reno/Boise responsibilities. These localhost certificates and grants expire after 30 days. No host, DNS name, cloud service or PHI processing has been activated.\n",
        )
        staged.rename(output)
    return result


def request(pilot, token_file, destination, payload=None):
    """Use a private access-token file without putting a bearer token in process arguments."""
    pilot, token_file, destination = Path(pilot), Path(token_file), Path(destination)
    if token_file.is_symlink() or not token_file.is_file() or token_file.stat().st_mode & 0o077:
        raise ValueError("Access token must be a private regular file")
    if destination.exists() or destination.is_symlink():
        raise ValueError("Response requires a new private file")
    token = json.loads(token_file.read_text())["access_token"]
    if not isinstance(token, str) or not token or any(c.isspace() for c in token):
        raise ValueError("Invalid access-token record")
    context = ssl.create_default_context(cafile=str(pilot / "tls/ca.pem"))

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            raise ValueError("Pilot API redirects are forbidden")

    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect(), urllib.request.HTTPSHandler(context=context)
    )
    req = urllib.request.Request(
        "https://localhost:8765/v1/" + ("command" if payload is not None else "report"),
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
    )
    try:
        with opener.open(req, timeout=15) as response:
            content = response.read(4 * 1024 * 1024 + 1)
        if len(content) > 4 * 1024 * 1024:
            raise ValueError("Pilot response exceeds limit")
        parsed = json.loads(content)
    except urllib.error.HTTPError as exc:
        raise ValueError(f"Pilot API rejected request (HTTP {exc.code})") from None
    private_write(destination, json.dumps(parsed, indent=2) + "\n")
    return {"status": "PRIVATE_RESPONSE_WRITTEN"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    setup = sub.add_parser("build")
    setup.add_argument("--delivery", required=True)
    setup.add_argument("--output", required=True)
    setup.add_argument("--keycloak-home")
    setup.add_argument("--java-home")
    for action in ("report", "command"):
        child = sub.add_parser(action)
        child.add_argument("--pilot", required=True)
        child.add_argument("--token-file", required=True)
        child.add_argument("--output", required=True)
        if action == "command":
            child.add_argument("--request-file", required=True)
    args = parser.parse_args()
    try:
        if args.command == "build":
            result = build(args.delivery, args.output, args.keycloak_home, args.java_home)
            result = {k: result[k] for k in ("status", "issuer", "api_origin", "plans", "controls")}
        else:
            payload = (
                json.loads(Path(args.request_file).read_text())
                if args.command == "command"
                else None
            )
            result = request(args.pilot, args.token_file, args.output, payload)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"Pilot setup error: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
