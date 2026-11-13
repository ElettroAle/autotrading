import pytest

from autotrading.adapters.configuration.errors import MissingConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.oidc.access_token_verifier import OidcAccessTokenVerifierAdapter
from autotrading.adapters.outbound.oidc.composition import oidc_adapters
from autotrading.adapters.outbound.oidc.login_endpoints import OidcLoginEndpointsAdapter

ISSUER = "https://login.example.test/tenant/v2.0"


def test_without_an_issuer_there_is_no_login() -> None:
    assert oidc_adapters(ConfigurationSource({"AUTH_AUDIENCE": "api://autotrading"})) is None


def test_with_an_issuer_the_tokens_are_verified_and_the_login_is_offered() -> None:
    login = oidc_adapters(ConfigurationSource({"AUTH_ISSUER": ISSUER, "AUTH_AUDIENCE": "api://autotrading"}))

    assert login is not None
    verifier, endpoints = login
    assert isinstance(verifier, OidcAccessTokenVerifierAdapter)
    assert isinstance(endpoints, OidcLoginEndpointsAdapter)


def test_an_issuer_without_an_audience_is_a_missing_configuration() -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        oidc_adapters(ConfigurationSource({"AUTH_ISSUER": ISSUER}))

    assert raised.value.name == "AUTH_AUDIENCE"
