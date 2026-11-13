from collections.abc import Mapping

import jwt

from autotrading.adapters.outbound.oidc.discovery import FetchJson, discovery_url_of, fetch_json, text_of
from autotrading.application.tenancy.errors import IdentityProviderUnavailableError, NotAuthenticatedError
from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.tenancy.verified_identity import VerifiedIdentity

SIGNING_ALGORITHMS = ["RS256"]
REQUIRED_CLAIMS = ["exp", "iss", "aud", "oid"]


class OidcAccessTokenVerifierAdapter:
    """Accepts only a token signed by the issuer for this audience, and names who it belongs to (R0.1.1)."""

    def __init__(self, issuer: str, audience: str, fetch: FetchJson = fetch_json) -> None:
        self._issuer = issuer
        self._audience = audience
        self._signing_keys = _SigningKeys(discovery_url_of(issuer), fetch)

    def verify(self, token: str) -> VerifiedIdentity:
        claims = self._verified_claims(token)
        return VerifiedIdentity(_user_of(claims), _roles_of(claims))

    def _verified_claims(self, token: str) -> Mapping[str, object]:
        key = self._signing_keys.key_for(token)
        try:
            claims: Mapping[str, object] = jwt.decode(
                token,
                key,
                algorithms=SIGNING_ALGORITHMS,
                audience=self._audience,
                issuer=self._issuer,
                options={"require": REQUIRED_CLAIMS},
            )
        except jwt.PyJWTError as error:
            raise NotAuthenticatedError from error
        return claims


class _SigningKeys:
    """The public keys of the issuer, found through its discovery document and refreshed when a key is unknown."""

    def __init__(self, discovery_url: str, fetch: FetchJson) -> None:
        self._discovery_url = discovery_url
        self._fetch = fetch
        self._keys: dict[str, jwt.PyJWK] = {}

    def key_for(self, token: str) -> jwt.PyJWK:
        key_id = _key_id_of(token)
        if key_id not in self._keys:
            self._keys = self._published_keys()
        if key_id not in self._keys:
            raise NotAuthenticatedError
        return self._keys[key_id]

    def _published_keys(self) -> dict[str, jwt.PyJWK]:
        try:
            jwks_uri = text_of(self._fetch(self._discovery_url), "jwks_uri")
            key_set = jwt.PyJWKSet.from_dict(dict(self._fetch(jwks_uri)))
        except (OSError, jwt.PyJWTError) as error:
            raise IdentityProviderUnavailableError from error
        return {key.key_id: key for key in key_set.keys if key.key_id}


def _key_id_of(token: str) -> str:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as error:
        raise NotAuthenticatedError from error
    key_id = header.get("kid")
    if not isinstance(key_id, str):
        raise NotAuthenticatedError
    return key_id


def _roles_of(claims: Mapping[str, object]) -> frozenset[str]:
    roles = claims.get("roles")
    if not isinstance(roles, list):
        return frozenset()
    return frozenset(role for role in roles if isinstance(role, str))


def _user_of(claims: Mapping[str, object]) -> UserId:
    # The oid is the only identifier of a person; the display name never identifies anyone (R0.1.2).
    object_id = claims.get("oid")
    if not isinstance(object_id, str) or not object_id.strip():
        raise NotAuthenticatedError
    return UserId(object_id)
