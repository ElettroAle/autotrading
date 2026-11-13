"""An OIDC identity provider for the tests: it publishes its keys and issues tokens signed with them."""

import json
import time
from collections.abc import Mapping
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from autotrading.adapters.inbound.api.app import Authentication
from autotrading.adapters.outbound.oidc.access_token_verifier import OidcAccessTokenVerifierAdapter
from autotrading.adapters.outbound.oidc.login_endpoints import OidcLoginEndpointsAdapter
from tests.support.directory import Person

ISSUER = "https://login.example.test/tenant-id/v2.0"
AUDIENCE = "api://autotrading-test"
CLIENT_ID = "swagger-client"
SCOPE = "api://x/access"
DISCOVERY_URL = f"{ISSUER}/.well-known/openid-configuration"
JWKS_URI = f"{ISSUER}/keys"
AUTHORIZATION_URL = f"{ISSUER}/authorize"
TOKEN_URL = f"{ISSUER}/token"
LIFETIME_SECONDS = 3600


class IdentityProvider:
    def __init__(self, key_id: str = "key-1") -> None:
        self.key_id = key_id
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.requests: list[str] = []
        self.reachable = True

    def fetch(self, url: str) -> Mapping[str, object]:
        """Serves the discovery document and the key set, as the issuer does over HTTPS."""
        self.requests.append(url)
        if not self.reachable:
            raise ConnectionRefusedError
        if url == DISCOVERY_URL:
            return {
                "issuer": ISSUER,
                "jwks_uri": JWKS_URI,
                "authorization_endpoint": AUTHORIZATION_URL,
                "token_endpoint": TOKEN_URL,
            }
        if url == JWKS_URI:
            return {"keys": [self._public_jwk()]}
        raise FileNotFoundError(url)

    def verifier(self) -> OidcAccessTokenVerifierAdapter:
        """The verifier of the platform, trusting this provider."""
        return OidcAccessTokenVerifierAdapter(ISSUER, AUDIENCE, self.fetch)

    def login(self) -> OidcLoginEndpointsAdapter:
        """Where the OpenAPI page of a test sends the user to log in at this provider."""
        return OidcLoginEndpointsAdapter(ISSUER, self.fetch)

    def authentication(self) -> Authentication:
        """The authentication of an API under test, wired to this provider."""
        return Authentication(CLIENT_ID, SCOPE, self.verifier(), self.login())

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
