import time
from collections.abc import Mapping
from typing import Any

import jwt
import pytest

from autotrading.adapters.inbound.api.authentication import (
    AccessTokenVerifier,
    AuthenticationSettings,
    LoginEndpoints,
    OidcLoginEndpoints,
    OidcSigningKeys,
    fetch_json,
)
from autotrading.adapters.inbound.api.errors import (
    IdentityProviderUnavailableError,
    NotAuthenticatedError,
    UserRoleMissingError,
)
from autotrading.domain.tenancy.user_id import UserId
from tests.support.directory import Person
from tests.support.identity_provider import AUTHORIZATION_URL, JWKS_URI, SETTINGS, TOKEN_URL, IdentityProvider

SHARED_SECRET = "a-shared-secret-of-thirty-two-chars"  # noqa: S105 - signs a forged token in the test


@pytest.fixture
def provider() -> IdentityProvider:
    return IdentityProvider()


@pytest.fixture
def anna() -> Person:
    return Person("anna", roles={"Utente"})


def verifier_for(provider: IdentityProvider) -> AccessTokenVerifier:
    return AccessTokenVerifier(SETTINGS, OidcSigningKeys(SETTINGS.discovery_url, provider.fetch))


def test_discovery_url_follows_the_issuer_without_doubling_the_slash() -> None:
    settings = AuthenticationSettings(issuer="https://idp.test/t/v2.0/", audience="a", client_id="c", scope="s")

    assert settings.discovery_url == "https://idp.test/t/v2.0/.well-known/openid-configuration"


def test_accepts_a_token_with_the_user_role_and_returns_the_object_id(provider: IdentityProvider, anna: Person) -> None:
    assert verifier_for(provider).verify(provider.token_for(anna)) == UserId(anna.object_id)


def test_rejects_a_token_without_the_user_role(provider: IdentityProvider, anna: Person) -> None:
    with pytest.raises(UserRoleMissingError) as raised:
        verifier_for(provider).verify(provider.token_for(anna, roles=["Lettore"]))

    assert str(raised.value) == "ruolo Utente assente"


@pytest.mark.parametrize("roles", [None, "Utente", {"Utente": True}], ids=["absent", "string", "object"])
def test_rejects_roles_that_are_not_a_list(provider: IdentityProvider, anna: Person, roles: object) -> None:
    with pytest.raises(UserRoleMissingError):
        verifier_for(provider).verify(provider.token_for(anna, roles=roles))


@pytest.mark.parametrize(
    "overrides",
    [
        {"exp": int(time.time()) - 60},
        {"iss": "https://other-issuer.test/v2.0"},
        {"aud": "api://another-application"},
        {"exp": None},
        {"oid": None},
        {"oid": "   "},
        {"oid": 42},
    ],
    ids=["expired", "issuer", "audience", "no-expiry", "no-oid", "blank-oid", "numeric-oid"],
)
def test_rejects_a_token_that_does_not_prove_the_identity(
    provider: IdentityProvider, anna: Person, overrides: dict[str, Any]
) -> None:
    with pytest.raises(NotAuthenticatedError) as raised:
        verifier_for(provider).verify(provider.token_for(anna, **overrides))

    assert str(raised.value) == "non autenticato"


def test_rejects_a_token_signed_by_another_key_with_the_same_key_id(provider: IdentityProvider, anna: Person) -> None:
    impostor = IdentityProvider(key_id=provider.key_id)

    with pytest.raises(NotAuthenticatedError):
        verifier_for(provider).verify(impostor.token_for(anna))


def test_rejects_a_token_signed_with_a_shared_secret(provider: IdentityProvider, anna: Person) -> None:
    claims = jwt.decode(provider.token_for(anna), options={"verify_signature": False})
    forged = jwt.encode(claims, SHARED_SECRET, algorithm="HS256", headers={"kid": provider.key_id})

    with pytest.raises(NotAuthenticatedError):
        verifier_for(provider).verify(forged)


@pytest.mark.parametrize(
    "token",
    ["not-a-token", jwt.encode({"oid": "x"}, SHARED_SECRET, algorithm="HS256")],
    ids=["garbage", "no-key-id"],
)
def test_rejects_a_token_without_a_readable_key_id(provider: IdentityProvider, token: str) -> None:
    with pytest.raises(NotAuthenticatedError):
        verifier_for(provider).verify(token)


def test_rejects_a_key_id_the_issuer_does_not_publish(provider: IdentityProvider, anna: Person) -> None:
    unknown = IdentityProvider(key_id="key-unknown")

    with pytest.raises(NotAuthenticatedError):
        verifier_for(provider).verify(unknown.token_for(anna))


def test_downloads_the_keys_once_while_the_key_id_is_known(provider: IdentityProvider, anna: Person) -> None:
    verifier = verifier_for(provider)

    verifier.verify(provider.token_for(anna))
    verifier.verify(provider.token_for(anna))

    assert provider.requests == [SETTINGS.discovery_url, JWKS_URI]


def test_downloads_the_keys_again_when_the_issuer_rotates_them(provider: IdentityProvider, anna: Person) -> None:
    verifier = verifier_for(provider)
    verifier.verify(provider.token_for(anna))
    rotated = IdentityProvider(key_id="key-2")
    provider.private_key, provider.key_id = rotated.private_key, rotated.key_id

    assert verifier.verify(provider.token_for(anna)) == UserId(anna.object_id)


def test_an_unreachable_issuer_is_reported_as_unavailable(provider: IdentityProvider, anna: Person) -> None:
    provider.reachable = False

    with pytest.raises(IdentityProviderUnavailableError) as raised:
        verifier_for(provider).verify(provider.token_for(anna))

    assert str(raised.value) == "directory non raggiungibile"


@pytest.mark.parametrize(
    "documents",
    [{}, {SETTINGS.discovery_url: {"jwks_uri": JWKS_URI}, JWKS_URI: {"keys": "none"}}],
    ids=["no-jwks-uri", "malformed-key-set"],
)
def test_a_malformed_discovery_is_reported_as_unavailable(
    provider: IdentityProvider, anna: Person, documents: dict[str, Mapping[str, Any]]
) -> None:
    def serve(url: str) -> Mapping[str, Any]:
        return documents.get(url, {})

    verifier = AccessTokenVerifier(SETTINGS, OidcSigningKeys(SETTINGS.discovery_url, serve))

    with pytest.raises(IdentityProviderUnavailableError):
        verifier.verify(provider.token_for(anna))


def test_the_directory_is_reached_only_over_https() -> None:
    with pytest.raises(IdentityProviderUnavailableError):
        fetch_json("http://login.example.test/.well-known/openid-configuration")


def test_the_login_endpoints_come_from_the_discovery_of_the_issuer(provider: IdentityProvider) -> None:
    endpoints = provider.login().endpoints()

    assert endpoints == LoginEndpoints(AUTHORIZATION_URL, TOKEN_URL)


def test_the_login_endpoints_are_read_once(provider: IdentityProvider) -> None:
    login = provider.login()

    login.endpoints()
    login.endpoints()

    assert provider.requests == [SETTINGS.discovery_url]


def test_an_unreachable_issuer_gives_no_login_endpoints_until_it_answers(provider: IdentityProvider) -> None:
    login = provider.login()
    provider.reachable = False

    with pytest.raises(IdentityProviderUnavailableError):
        login.endpoints()
    provider.reachable = True

    assert login.endpoints().token_url == TOKEN_URL


@pytest.mark.parametrize(
    "document",
    [
        {"authorization_endpoint": "https://idp.test/authorize"},
        {"token_endpoint": "https://idp.test/token"},
        {"authorization_endpoint": "http://idp.test/authorize", "token_endpoint": "https://idp.test/token"},
        {"authorization_endpoint": "https://idp.test/authorize", "token_endpoint": "http://idp.test/token"},
    ],
    ids=["no-token-endpoint", "no-authorization-endpoint", "plain-authorization", "plain-token"],
)
def test_a_login_endpoint_missing_or_not_over_https_is_refused(document: Mapping[str, Any]) -> None:
    login = OidcLoginEndpoints(SETTINGS.discovery_url, lambda _url: document)

    with pytest.raises(IdentityProviderUnavailableError):
        login.endpoints()
