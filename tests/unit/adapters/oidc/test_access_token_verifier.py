import time
from collections.abc import Mapping

import jwt
import pytest

from autotrading.adapters.outbound.oidc.access_token_verifier import OidcAccessTokenVerifierAdapter
from autotrading.application.tenancy.errors import IdentityProviderUnavailableError, NotAuthenticatedError
from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.tenancy.verified_identity import VerifiedIdentity
from tests.support.directory import Person
from tests.support.identity_provider import AUDIENCE, DISCOVERY_URL, ISSUER, JWKS_URI, IdentityProvider

SHARED_SECRET = "a-shared-secret-of-thirty-two-chars"  # noqa: S105 - signs a forged token in the test


@pytest.fixture
def provider() -> IdentityProvider:
    return IdentityProvider()


@pytest.fixture
def anna() -> Person:
    return Person("anna", roles={"Utente"})


def test_a_valid_token_names_the_object_id_and_the_roles(provider: IdentityProvider, anna: Person) -> None:
    identity = provider.verifier().verify(provider.token_for(anna, roles=["Utente", "Lettore"]))

    assert identity == VerifiedIdentity(UserId(anna.object_id), frozenset({"Utente", "Lettore"}))


def test_the_keys_are_found_from_the_issuer_without_doubling_the_slash(
    provider: IdentityProvider, anna: Person
) -> None:
    verifier = OidcAccessTokenVerifierAdapter(f"{ISSUER}/", AUDIENCE, provider.fetch)

    with pytest.raises(NotAuthenticatedError):
        verifier.verify(provider.token_for(anna))

    assert provider.requests[0] == DISCOVERY_URL


@pytest.mark.parametrize(
    ("roles", "expected"),
    [
        (None, frozenset()),
        ("Utente", frozenset()),
        ({"Utente": True}, frozenset()),
        (["Utente", 7], frozenset({"Utente"})),
    ],
    ids=["absent", "string", "object", "non-text-entries"],
)
def test_only_textual_roles_in_a_list_are_read(
    provider: IdentityProvider, anna: Person, roles: object, expected: frozenset[str]
) -> None:
    identity = provider.verifier().verify(provider.token_for(anna, roles=roles))

    assert identity.roles == expected


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
    provider: IdentityProvider, anna: Person, overrides: dict[str, object]
) -> None:
    with pytest.raises(NotAuthenticatedError) as raised:
        provider.verifier().verify(provider.token_for(anna, **overrides))

    assert str(raised.value) == "non autenticato"


def test_rejects_a_token_signed_by_another_key_with_the_same_key_id(provider: IdentityProvider, anna: Person) -> None:
    impostor = IdentityProvider(key_id=provider.key_id)

    with pytest.raises(NotAuthenticatedError):
        provider.verifier().verify(impostor.token_for(anna))


def test_rejects_a_token_signed_with_a_shared_secret(provider: IdentityProvider, anna: Person) -> None:
    claims = jwt.decode(provider.token_for(anna), options={"verify_signature": False})
    forged = jwt.encode(claims, SHARED_SECRET, algorithm="HS256", headers={"kid": provider.key_id})

    with pytest.raises(NotAuthenticatedError):
        provider.verifier().verify(forged)


@pytest.mark.parametrize(
    "token",
    ["not-a-token", jwt.encode({"oid": "x"}, SHARED_SECRET, algorithm="HS256")],
    ids=["garbage", "no-key-id"],
)
def test_rejects_a_token_without_a_readable_key_id(provider: IdentityProvider, token: str) -> None:
    with pytest.raises(NotAuthenticatedError):
        provider.verifier().verify(token)


def test_rejects_a_key_id_the_issuer_does_not_publish(provider: IdentityProvider, anna: Person) -> None:
    unknown = IdentityProvider(key_id="key-unknown")

    with pytest.raises(NotAuthenticatedError):
        provider.verifier().verify(unknown.token_for(anna))


def test_downloads_the_keys_once_while_the_key_id_is_known(provider: IdentityProvider, anna: Person) -> None:
    verifier = provider.verifier()

    verifier.verify(provider.token_for(anna))
    verifier.verify(provider.token_for(anna))

    assert provider.requests == [DISCOVERY_URL, JWKS_URI]


def test_downloads_the_keys_again_when_the_issuer_rotates_them(provider: IdentityProvider, anna: Person) -> None:
    verifier = provider.verifier()
    verifier.verify(provider.token_for(anna))
    rotated = IdentityProvider(key_id="key-2")
    provider.private_key, provider.key_id = rotated.private_key, rotated.key_id

    assert verifier.verify(provider.token_for(anna)).user_id == UserId(anna.object_id)


def test_an_unreachable_issuer_is_reported_as_unavailable(provider: IdentityProvider, anna: Person) -> None:
    provider.reachable = False

    with pytest.raises(IdentityProviderUnavailableError) as raised:
        provider.verifier().verify(provider.token_for(anna))

    assert str(raised.value) == "directory non raggiungibile"


@pytest.mark.parametrize(
    "documents",
    [
        {},
        {DISCOVERY_URL: {"jwks_uri": 7}},
        {DISCOVERY_URL: {"jwks_uri": JWKS_URI}, JWKS_URI: {"keys": "none"}},
    ],
    ids=["no-jwks-uri", "jwks-uri-not-text", "malformed-key-set"],
)
def test_a_malformed_discovery_is_reported_as_unavailable(
    provider: IdentityProvider, anna: Person, documents: dict[str, Mapping[str, object]]
) -> None:
    def serve(url: str) -> Mapping[str, object]:
        return documents.get(url, {})

    verifier = OidcAccessTokenVerifierAdapter(ISSUER, AUDIENCE, serve)

    with pytest.raises(IdentityProviderUnavailableError):
        verifier.verify(provider.token_for(anna))
