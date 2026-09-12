"""Private, loopback-only Keycloak pilot: fictional accounts, PKCE/device login, pinned TLS."""

import argparse
import base64
import hashlib
import ipaddress
import json
import os
import secrets
import ssl
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from .identity import Identity, private_json

CLIENT = "ccf-pilot-cli"
AUDIENCE = "ccf-api"
REALM = "ccf-pilot"


def write(path, value):
    raw = value if isinstance(value, bytes) else (json.dumps(value, indent=2) + "\n").encode()
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)


def local_issuer(issuer):
    parsed = urlsplit(issuer)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"localhost", "127.0.0.1"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path != "/realms/" + REALM
    ):
        raise ValueError("Pilot requires an exact HTTPS loopback ccf-pilot issuer")
    if parsed.port is None or parsed.port < 1024:
        raise ValueError("Explicit unprivileged local TLS port required")
    return parsed


def certificates(output):
    now = datetime.now(timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "CCF FICTIONAL PILOT LOCAL CA")])
    ca = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]))
        .issuer_name(ca_name)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
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
    write(output / "ca.pem", ca.public_bytes(serialization.Encoding.PEM))
    write(output / "server.pem", server.public_bytes(serialization.Encoding.PEM))
    write(
        output / "server-key.pem",
        server_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
    )
    # CA signing key is intentionally not retained; restart/rebuild a new pilot to renew.


def build(output, principals, issuer="https://localhost:8443/realms/ccf-pilot", *, tls=None):
    parsed = local_issuer(issuer)
    if not principals or len({p["id"] for p in principals}) != len(principals):
        raise ValueError("Unique local workflow principals required")
    output = Path(output)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    users, credentials, bindings = [], [], []
    for i, principal in enumerate(principals):
        pid = principal["id"]
        if not isinstance(pid, str) or not pid:
            raise ValueError("Nonempty local principal ID required")
        subject, username, password = (
            str(uuid.uuid4()),
            f"pilot-user-{i + 1}",
            secrets.token_urlsafe(24),
        )
        users.append(
            dict(
                id=subject,
                username=username,
                enabled=True,
                emailVerified=True,
                email=username + "@example.invalid",
                firstName="Fictional",
                lastName=f"Pilot {i + 1}",
                credentials=[dict(type="password", value=password, temporary=False)],
            )
        )
        credentials.append(
            dict(
                origin="SYNTHETIC",
                username=username,
                password=password,
                subject=subject,
                principal=pid,
            )
        )
        bindings.append(dict(issuer=issuer, subject=subject, principal=pid))
    client = dict(
        clientId=CLIENT,
        name="Fictional CCF pilot",
        protocol="openid-connect",
        publicClient=True,
        standardFlowEnabled=True,
        directAccessGrantsEnabled=False,
        serviceAccountsEnabled=False,
        implicitFlowEnabled=False,
        fullScopeAllowed=False,
        redirectUris=["http://127.0.0.1:8766/callback"],
        webOrigins=[],
        defaultClientScopes=["basic"],
        optionalClientScopes=[],
        attributes={
            "pkce.code.challenge.method": "S256",
            "oauth2.device.authorization.grant.enabled": "true",
            "access.token.lifespan": "300",
        },
        protocolMappers=[
            dict(
                name="ccf-api-audience",
                protocol="openid-connect",
                protocolMapper="oidc-audience-mapper",
                config={
                    "included.custom.audience": AUDIENCE,
                    "access.token.claim": "true",
                    "id.token.claim": "false",
                    "introspection.token.claim": "true",
                },
            ),
            dict(
                name="ccf-access-purpose",
                protocol="openid-connect",
                protocolMapper="oidc-hardcoded-claim-mapper",
                config={
                    "claim.name": "token_use",
                    "claim.value": "access",
                    "jsonType.label": "String",
                    "access.token.claim": "true",
                    "id.token.claim": "false",
                    "userinfo.token.claim": "false",
                },
            ),
        ],
    )
    realm = dict(
        realm=REALM,
        enabled=True,
        displayName="FICTIONAL CCF LOCAL PILOT",
        sslRequired="all",
        registrationAllowed=False,
        resetPasswordAllowed=False,
        rememberMe=False,
        loginWithEmailAllowed=False,
        duplicateEmailsAllowed=False,
        bruteForceProtected=True,
        accessTokenLifespan=300,
        ssoSessionIdleTimeout=900,
        ssoSessionMaxLifespan=3600,
        defaultSignatureAlgorithm="RS256",
        clients=[client],
        users=users,
    )
    write(output / "ccf-pilot-realm.json", realm)
    write(
        output / "pilot-credentials.json",
        dict(
            origin="SYNTHETIC",
            users=credentials,
            bootstrap_admin=dict(
                username="pilot-bootstrap-admin", password=secrets.token_urlsafe(24)
            ),
        ),
    )
    write(
        output / "identity.pending.json",
        dict(
            issuer=issuer,
            audience=AUDIENCE,
            max_token_lifetime_seconds=300,
            required_claims={"token_use": "access"},
            bindings=bindings,
        ),
    )
    if tls is None:
        certificates(output)
    else:
        for filename, field in (
            ("ca.pem", "ca_pem"),
            ("server.pem", "server_pem"),
            ("server-key.pem", "server_key_pem"),
        ):
            if not isinstance(tls[field], bytes):
                raise ValueError("TLS material must be PEM bytes")
            write(output / filename, tls[field])
    write(
        output / "pilot-config.json",
        dict(
            origin="SYNTHETIC",
            issuer=issuer,
            client_id=CLIENT,
            keycloak_version="26.7.3",
            port=parsed.port,
            browser_redirect_uri="http://127.0.0.1:8766/callback",
            production_ready=False,
        ),
    )
    write(output / "README.md", PILOT_README.encode())
    write(output / "start-keycloak.py", LAUNCHER.encode())
    return dict(
        output=output.name,
        issuer=issuer,
        users=len(users),
        origin="SYNTHETIC",
        production_ready=False,
    )


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Pilot identity endpoint redirects are forbidden")


def fetch(root, path, data=None):
    config = private_json(Path(root) / "pilot-config.json")
    issuer = config["issuer"]
    local_issuer(issuer)
    if path not in {
        "/.well-known/openid-configuration",
        "/protocol/openid-connect/certs",
        "/protocol/openid-connect/auth/device",
        "/protocol/openid-connect/token",
    }:
        raise ValueError("Unsupported pinned identity endpoint")
    context = ssl.create_default_context(cafile=str(Path(root) / "ca.pem"))
    opener = build_opener(ProxyHandler({}), HTTPSHandler(context=context), NoRedirects())
    request = Request(
        issuer + path,
        data=urlencode(data).encode() if data is not None else None,
        headers={"Accept": "application/json"},
    )
    try:
        with opener.open(request, timeout=15) as response:
            raw = response.read(1_048_577)
            if len(raw) > 1_048_576:
                raise ValueError("Identity response too large")
            return json.loads(raw)
    except HTTPError as error:
        if error.code == 400 and path == "/protocol/openid-connect/token":
            payload = json.loads(error.read(16384))
            if payload.get("error") in {
                "authorization_pending",
                "slow_down",
                "expired_token",
                "access_denied",
            }:
                return {"error": payload["error"]}
        raise ValueError("Identity endpoint request failed") from None


def pin(root):
    root = Path(root)
    config = private_json(root / "identity.pending.json")
    discovery = fetch(root, "/.well-known/openid-configuration")
    if (
        discovery.get("issuer") != config["issuer"]
        or discovery.get("jwks_uri") != config["issuer"] + "/protocol/openid-connect/certs"
    ):
        raise ValueError("Discovery does not match exact local issuer and keys endpoint")
    keys = fetch(root, "/protocol/openid-connect/certs")["keys"]
    config["jwks"] = {
        "keys": [key for key in keys if key.get("alg") == "RS256" and key.get("use") == "sig"]
    }
    Identity(config)
    write(root / "identity.json", config)
    return dict(
        issuer=config["issuer"],
        public_key_count=len(config["jwks"]["keys"]),
        configuration="identity.json",
    )


def start_device(root):
    root = Path(root)
    verifier = secrets.token_urlsafe(48)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    )
    result = fetch(
        root,
        "/protocol/openid-connect/auth/device",
        dict(
            client_id=CLIENT, scope="openid", code_challenge=challenge, code_challenge_method="S256"
        ),
    )
    result["code_verifier"] = verifier
    issuer = private_json(root / "pilot-config.json")["issuer"]
    for field in ("verification_uri", "verification_uri_complete"):
        if not result[field].startswith(issuer + "/"):
            raise ValueError("Unexpected device verification destination")
    write(root / "device-session.json", result)
    return {
        k: result[k]
        for k in (
            "user_code",
            "verification_uri",
            "verification_uri_complete",
            "expires_in",
            "interval",
        )
    }


def poll_device(root):
    root = Path(root)
    state = private_json(root / "device-session.json")
    result = fetch(
        root,
        "/protocol/openid-connect/token",
        dict(
            client_id=CLIENT,
            grant_type="urn:ietf:params:oauth:grant-type:device_code",
            device_code=state["device_code"],
            code_verifier=state["code_verifier"],
        ),
    )
    if "error" in result:
        return result
    identity = Identity(private_json(root / "identity.json"))
    actor = identity.authenticate("Bearer " + result["access_token"])
    write(
        root / "access-token.json",
        dict(
            access_token=result["access_token"], expires_in=result["expires_in"], origin="SYNTHETIC"
        ),
    )
    return dict(
        principal=actor,
        token_path="access-token.json",
        expires_in=result["expires_in"],
        origin="SYNTHETIC",
    )


PILOT_README = """# Fictional local Keycloak pilot

These accounts and realm represent an isolated demonstration, not workforce identities or corporate appointments. Credentials are random and stored only in private `pilot-credentials.json`. Do not share this directory or commit it. The CA expires after 30 days and is never added to system trust.

Use a private, extracted official Keycloak 26.7.3 distribution and Java 21 runtime. Set `KEYCLOAK_HOME` to that private distribution and `JAVA_HOME` to the Java runtime. From the repository root run `uv run --extra ccf-service python <pilot>/identity/start-keycloak.py`. The launcher imports the explicit realm file into its own `identity/keycloak-data` database, locks the shared runtime against concurrent launches, loads bootstrap credentials into its child environment, binds HTTPS to 127.0.0.1 on the configured port, disables HTTP, and runs a local Keycloak pilot with the development-file database. Each pilot directory has its own local development database, so separate pilots can reuse a runtime sequentially without sharing subjects. Never point KEYCLOAK_HOME at a shared or production instance.

Once Keycloak is ready, pin the exact local TLS-protected public keys:

```sh
uv run --extra ccf-service python -m enterprise.ccf.operations.pilot_identity pin --root <pilot>/identity
uv run --extra ccf-service python -m enterprise.ccf.operations.pilot_identity device --root <pilot>/identity
```

Open the printed verification URL in a browser and sign in using the chosen fictional user's private credentials. The displayed issuer must match `pilot-config.json`; validate the supplied CA/certificate explicitly in a dedicated test browser profile, never disable TLS verification globally. The CLI's discovery, keys and token calls use only this CA, reject redirects and bypass environment proxies. Login uses the device authorization grant; the client also supports authorization code with S256 PKCE at the fixed loopback callback. Password and implicit grants are disabled.

After browser authorization, wait the printed interval and run:

```sh
uv run --extra ccf-service python -m enterprise.ccf.operations.pilot_identity poll --root <pilot>/identity
```

Polling writes the verified access token to private `access-token.json` and prints only its relative path, verified local principal and expiry. Respect `authorization_pending` and `slow_down`; a token lasts at most five minutes. The helper makes one request per invocation and never loops aggressively. Device sessions and token files use exclusive creation; remove only your expired private session/token file when deliberately beginning another login. JWT public-key pinning also uses exclusive creation: review key rotation before replacing `identity.json`.

Stop Keycloak with Ctrl-C when finished. Its development database retains these fictional users between restarts; realm import skips an existing realm. Rebuild a fresh private pilot directory/database to change imported subjects rather than assuming an import overwrites an existing realm. Do not use this development database, bootstrap account or CA for production.

Sources: https://www.keycloak.org/getting-started/getting-started-docker ; https://www.keycloak.org/server/enabletls ; https://www.keycloak.org/securing-apps/oidc-layers ; https://www.keycloak.org/2026/08/keycloak-2673-released
"""

LAUNCHER = r'''"""Start only the private fictional Keycloak development database."""
import fcntl
import json
import os
import pathlib
import subprocess

os.umask(0o077)
root = pathlib.Path(__file__).resolve().parent
runtime = pathlib.Path(os.environ["KEYCLOAK_HOME"]).resolve()
config = json.loads((root / "pilot-config.json").read_text())
admin = json.loads((root / "pilot-credentials.json").read_text())["bootstrap_admin"]
# One shared distribution can serve successive pilots, never concurrent mutations.
with (runtime / ".ccf-pilot.lock").open("a") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    data = root / "keycloak-data"
    data.mkdir(mode=0o700, exist_ok=True)
    db_url = "jdbc:h2:file:" + str(data / "keycloak") + ";NON_KEYWORDS=VALUE;DB_CLOSE_ON_EXIT=FALSE"
    env = {**os.environ, "KC_BOOTSTRAP_ADMIN_USERNAME": admin["username"], "KC_BOOTSTRAP_ADMIN_PASSWORD": admin["password"]}
    command = str(runtime / "bin" / "kc.sh")
    # Explicit file/database avoids the shared distribution's data/import directory.
    subprocess.run([command, "import", "--db=dev-file", "--db-url=" + db_url, "--file=" + str(root / "ccf-pilot-realm.json"), "--override=false"], env=env, check=True)
    subprocess.run([command, "start", "--db=dev-file", "--db-url=" + db_url, "--cache=local", "--http-enabled=false", "--http-host=127.0.0.1", "--https-port=" + str(config["port"]), "--hostname=" + config["issuer"].split("/realms/")[0], "--https-certificate-file=" + str(root / "server.pem"), "--https-certificate-key-file=" + str(root / "server-key.pem")], env=env, check=True)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["pin", "device", "poll"])
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    result = {"pin": pin, "device": start_device, "poll": poll_device}[args.action](args.root)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
