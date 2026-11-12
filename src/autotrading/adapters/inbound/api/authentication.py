import json
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import jwt

from autotrading.adapters.inbound.api.errors import (
    IdentityProviderUnavailableError,
    NotAuthenticatedError,
    UserRoleMissingError,
)
from autotrading.domain.errors import AutotradingError
from autotrading.domain.tenancy.user_id import UserId

USER_ROLE = "Utente"
SIGNING_ALGORITHMS = ["RS256"]
REQUIRED_CLAIMS = ["exp", "iss", "aud", "oid"]
DIRECTORY_TIMEOUT_SECONDS = 5

type FetchJson = Callable[[str], Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class AuthenticationSettings:
    """What the platform knows of the identity provider: any OIDC issuer, Entra ID first (architecture §7.1)."""

    issuer: str
    audience: str
    client_id: str
    scope: str

    @property
    def discovery_url(self) -> str:
        return f"{self.issuer.rstrip('/')}/.well-known/openid-configuration"


def fetch_json(url: str) -> Mapping[str, Any]:
    if not url.startswith("https://"):
        raise IdentityProviderUnavailableError
    with urllib.request.urlopen(url, timeout=DIRECTORY_TIMEOUT_SECONDS) as response:  # noqa: S310 - https only
        document: Mapping[str, Any] = json.load(response)
    return document


@dataclass(frozen=True, slots=True)
class LoginEndpoints:
    """Where the OpenAPI page sends the user to log in and to redeem the code (Authorization Code + PKCE)."""

    authorization_url: str
    token_url: str


class OidcLoginEndpoints:
    """The login endpoints of the issuer, read from its discovery document the first time it answers (ADR 0073)."""

    def __init__(self, discovery_url: str, fetch: FetchJson = fetch_json) -> None:
        self._discovery_url = discovery_url
        self._fetch = fetch
        self._endpoints: LoginEndpoints | None = None

    def endpoints(self) -> LoginEndpoints:
        if self._endpoints is None:
            self._endpoints = self._discovered()
        return self._endpoints

    def _discovered(self) -> LoginEndpoints:
        try:
            document = self._fetch(self._discovery_url)
            endpoints = LoginEndpoints(str(document["authorization_endpoint"]), str(document["token_endpoint"]))
        except AutotradingError:
            raise
        except (OSError, KeyError, ValueError) as error:
            raise IdentityProviderUnavailableError from error
        # The browser carries the code and the verifier to these addresses: only HTTPS ones are offered.
        if not all(url.startswith("https://") for url in (endpoints.authorization_url, endpoints.token_url)):
            raise IdentityProviderUnavailableError
        return endpoints


class OidcSigningKeys:
    """The public keys of the issuer, found through its discovery document and refreshed when a key is unknown."""

    def __init__(self, discovery_url: str, fetch: FetchJson = fetch_json) -> None:
        self._discovery_url = discovery_url
        self._fetch = fetch
        self._keys: dict[str, Any] = {}

    def key_for(self, token: str) -> Any:
        key_id = _key_id_of(token)
        if key_id not in self._keys:
            self._keys = self._published_keys()
        if key_id not in self._keys:
            raise NotAuthenticatedError
        return self._keys[key_id]

    def _published_keys(self) -> dict[str, Any]:
        try:
            jwks_uri = str(self._fetch(self._discovery_url)["jwks_uri"])
            key_set = jwt.PyJWKSet.from_dict(dict(self._fetch(jwks_uri)))
        except AutotradingError:
            raise
        except (OSError, KeyError, ValueError, jwt.PyJWTError) as error:
            raise IdentityProviderUnavailableError from error
        return {key.key_id: key.key for key in key_set.keys if key.key_id}


class AccessTokenVerifier:
    """Accepts only a token signed by the issuer, for this audience, carrying the Utente role (R0.1.1)."""

    def __init__(self, settings: AuthenticationSettings, signing_keys: OidcSigningKeys) -> None:
        self._settings = settings
        self._signing_keys = signing_keys

    def verify(self, token: str) -> UserId:
        claims = self._verified_claims(token)
        _require_user_role(claims)
        return _user_of(claims)

    def _verified_claims(self, token: str) -> Mapping[str, Any]:
        key = self._signing_keys.key_for(token)
        try:
            claims: Mapping[str, Any] = jwt.decode(
                token,
                key,
                algorithms=SIGNING_ALGORITHMS,
                audience=self._settings.audience,
                issuer=self._settings.issuer,
                options={"require": REQUIRED_CLAIMS},
            )
        except jwt.PyJWTError as error:
            raise NotAuthenticatedError from error
        return claims


def _key_id_of(token: str) -> str:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as error:
        raise NotAuthenticatedError from error
    key_id = header.get("kid")
    if not isinstance(key_id, str):
        raise NotAuthenticatedError
    return key_id


def _require_user_role(claims: Mapping[str, Any]) -> None:
    roles = claims.get("roles")
    if not isinstance(roles, list) or USER_ROLE not in roles:
        raise UserRoleMissingError


def _user_of(claims: Mapping[str, Any]) -> UserId:
    # The oid is the only identifier of a person; the display name never identifies anyone (R0.1.2).
    object_id = claims["oid"]
    if not isinstance(object_id, str) or not object_id.strip():
        raise NotAuthenticatedError
    return UserId(object_id)
