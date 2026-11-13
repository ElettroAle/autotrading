from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.oidc.access_token_verifier import OidcAccessTokenVerifierAdapter
from autotrading.adapters.outbound.oidc.configuration import _settings_of
from autotrading.adapters.outbound.oidc.login_endpoints import OidcLoginEndpointsAdapter


def oidc_adapters(
    source: ConfigurationSource,
) -> tuple[OidcAccessTokenVerifierAdapter, OidcLoginEndpointsAdapter] | None:
    """Who verifies the tokens and where the login happens, if the installation declares an issuer (ADR 0016)."""
    settings = _settings_of(source)
    if settings is None:
        return None
    return OidcAccessTokenVerifierAdapter(settings.issuer, settings.audience), OidcLoginEndpointsAdapter(
        settings.issuer
    )
