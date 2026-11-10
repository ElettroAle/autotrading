"""An OIDC identity provider for the tests: it publishes its keys and issues tokens signed with them."""

import json
import time
from collections.abc import Mapping
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from autotrading.adapters.inbound.api.authentication import AuthenticationSettings
from tests.support.directory import Person

ISSUER = "https://login.example.test/tenant-id/v2.0"
AUDIENCE = "api://autotrading-test"
SETTINGS = AuthenticationSettings(issuer=ISSUER, audience=AUDIENCE, client_id="swagger-client", scope="api://x/access")
JWKS_URI = f"{ISSUER}/keys"
LIFETIME_SECONDS = 3600


class IdentityProvider:
    def __init__(self, key_id: str = "key-1") -> None:
        self.key_id = key_id
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.requests: list[str] = []
        self.reachable = True

    def fetch(self, url: str) -> Mapping[str, Any]:
        """Serves the discovery document and the key set, as the issuer does over HTTPS."""
        self.requests.append(url)
        if not self.reachable:
            raise ConnectionRefusedError
        if url == SETTINGS.discovery_url:
            return {"issuer": ISSUER, "jwks_uri": JWKS_URI}
        if url == JWKS_URI:
            return {"keys": [self._public_jwk()]}
        raise FileNotFoundError(url)

    def token_for(self, person: Person, **overrides: object) -> str:
        now = int(time.time())
        claims: dict[str, Any] = {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": now,
            "exp": now + LIFETIME_SECONDS,
            "oid": person.object_id,
            "name": person.display_name,
            "roles": sorted(person.roles),
        }
        claims.update(overrides)
        return jwt.encode(
            {name: value for name, value in claims.items() if value is not None},
            self.private_key,
            algorithm="RS256",
            headers={"kid": self.key_id},
        )

    def _public_jwk(self) -> dict[str, Any]:
        jwk: dict[str, Any] = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.private_key.public_key()))
        jwk.update({"kid": self.key_id, "use": "sig", "alg": "RS256"})
        return jwk
