"""Pinned OIDC access-token verification; identity never confers workflow permissions."""

import json
from pathlib import Path
from urllib.parse import urlsplit

import jwt


class AuthenticationError(ValueError):
    pass


def private_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise ValueError("Identity configuration must be a private regular file")
    if path.stat().st_size > 1_048_576:
        raise ValueError("Identity configuration is too large")
    return json.loads(path.read_text())


class Identity:
    """Config and keys are operator controlled, loaded once; rotate by reviewed restart."""

    def __init__(self, config):
        self.issuer = config["issuer"]
        issuer = urlsplit(self.issuer)
        if (
            issuer.scheme != "https"
            or not issuer.hostname
            or issuer.query
            or issuer.fragment
            or issuer.username
        ):
            raise ValueError("An exact HTTPS issuer is required")
        self.audience = config["audience"]
        if not isinstance(self.audience, str) or not self.audience:
            raise ValueError("Dedicated API audience required")
        self.max_lifetime = config.get("max_token_lifetime_seconds", 3600)
        if type(self.max_lifetime) is not int or not 60 <= self.max_lifetime <= 3600:
            raise ValueError("Token lifetime must be between 60 and 3600 seconds")
        # Require an API-specific access-token marker; never accept an ID token merely
        # because its audience happens to match. Provider-specific claim is explicit.
        self.required_claims = config["required_claims"]
        if (
            not isinstance(self.required_claims, dict)
            or not self.required_claims
            or any(
                k in {"iss", "sub", "aud", "exp", "iat", "nbf"} or not isinstance(v, str) or not v
                for k, v in self.required_claims.items()
            )
        ):
            raise ValueError("Explicit provider access-token claims required")
        self.bindings = {}
        for b in config["bindings"]:
            if b["issuer"] != self.issuer or not all(
                isinstance(b[k], str) and b[k] for k in ("subject", "principal")
            ):
                raise ValueError("Exact issuer, subject and local principal required")
            key = (b["issuer"], b["subject"])
            if key in self.bindings:
                raise ValueError("Duplicate identity binding")
            self.bindings[key] = b["principal"]
        if not self.bindings:
            raise ValueError("At least one explicit identity binding required")
        self.keys = {}
        for item in config["jwks"]["keys"]:
            if (
                item.get("kty") != "RSA"
                or item.get("alg") != "RS256"
                or item.get("use") != "sig"
                or any(k in item for k in ("d", "p", "q", "dp", "dq", "qi"))
            ):
                raise ValueError("Only public RS256 signature keys allowed")
            kid = item.get("kid")
            if (
                not isinstance(kid, str)
                or not kid
                or kid in self.keys
                or item.get("key_ops", ["verify"]) != ["verify"]
            ):
                raise ValueError("Unique key ID and verification-only key required")
            key = jwt.PyJWK.from_dict(item, algorithm="RS256").key
            if key.key_size < 2048:
                raise ValueError("RSA keys must be at least 2048 bits")
            self.keys[kid] = key
        if not self.keys:
            raise ValueError("Pinned public keys required")

    def authenticate(self, authorization):
        try:
            if (
                not isinstance(authorization, str)
                or not authorization.startswith("Bearer ")
                or len(authorization) > 16384
            ):
                raise ValueError("Bearer token required")
            token = authorization[7:]
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256" or any(
                k in header for k in ("jku", "jwk", "x5u", "crit")
            ):
                raise ValueError("Unsupported token header")
            key = self.keys[header["kid"]]
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=self.issuer,
                audience=self.audience,
                leeway=0,
                options={"require": ["iss", "sub", "aud", "exp", "iat", "nbf"], "strict_aud": True},
            )
            if (
                any(type(claims[k]) is not int for k in ("iat", "exp", "nbf"))
                or not claims["iat"] <= claims["nbf"] < claims["exp"]
                or claims["exp"] - claims["iat"] > self.max_lifetime
            ):
                raise ValueError("Invalid token lifetime")
            if any(claims.get(k) != v for k, v in self.required_claims.items()):
                raise ValueError("Wrong access-token purpose")
            return self.bindings[(claims["iss"], claims["sub"])]
        except (ValueError, KeyError, TypeError, jwt.PyJWTError) as exc:
            raise AuthenticationError("Invalid access token") from exc
