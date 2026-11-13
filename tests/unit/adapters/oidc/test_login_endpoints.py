from collections.abc import Mapping

import pytest

from autotrading.adapters.outbound.oidc.login_endpoints import OidcLoginEndpointsAdapter
from autotrading.application.tenancy.errors import IdentityProviderUnavailableError
from autotrading.application.tenancy.ports import LoginEndpoints
from tests.support.identity_provider import AUTHORIZATION_URL, DISCOVERY_URL, ISSUER, TOKEN_URL, IdentityProvider


@pytest.fixture
def provider() -> IdentityProvider:
    return IdentityProvider()


def test_the_login_endpoints_come_from_the_discovery_of_the_issuer(provider: IdentityProvider) -> None:
    endpoints = provider.login().endpoints()

    assert endpoints == LoginEndpoints(AUTHORIZATION_URL, TOKEN_URL)


def test_the_login_endpoints_are_read_once(provider: IdentityProvider) -> None:
    login = provider.login()

    login.endpoints()
    login.endpoints()

    assert provider.requests == [DISCOVERY_URL]


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
        {"authorization_endpoint": 7, "token_endpoint": "https://idp.test/token"},
        {"authorization_endpoint": "http://idp.test/authorize", "token_endpoint": "https://idp.test/token"},
        {"authorization_endpoint": "https://idp.test/authorize", "token_endpoint": "http://idp.test/token"},
    ],
    ids=["no-token-endpoint", "no-authorization-endpoint", "not-text", "plain-authorization", "plain-token"],
)
def test_a_login_endpoint_missing_or_not_over_https_is_refused(document: Mapping[str, object]) -> None:
    login = OidcLoginEndpointsAdapter(ISSUER, lambda _url: document)

    with pytest.raises(IdentityProviderUnavailableError):
        login.endpoints()
