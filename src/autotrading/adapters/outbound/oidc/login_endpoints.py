from autotrading.adapters.outbound.oidc.discovery import FetchJson, discovery_url_of, fetch_json, text_of
from autotrading.application.tenancy.errors import IdentityProviderUnavailableError
from autotrading.application.tenancy.ports import LoginEndpoints


class OidcLoginEndpointsAdapter:
    """The login endpoints of the issuer, read from its discovery document the first time it answers (ADR 0073)."""

    def __init__(self, issuer: str, fetch: FetchJson = fetch_json) -> None:
        self._discovery_url = discovery_url_of(issuer)
        self._fetch = fetch
        self._endpoints: LoginEndpoints | None = None

    def endpoints(self) -> LoginEndpoints:
        if self._endpoints is None:
            self._endpoints = self._discovered()
        return self._endpoints

    def _discovered(self) -> LoginEndpoints:
        try:
            document = self._fetch(self._discovery_url)
        except OSError as error:
            raise IdentityProviderUnavailableError from error
        endpoints = LoginEndpoints(text_of(document, "authorization_endpoint"), text_of(document, "token_endpoint"))
        # The browser carries the code and the verifier to these addresses: only HTTPS ones are offered.
        if not all(url.startswith("https://") for url in (endpoints.authorization_url, endpoints.token_url)):
            raise IdentityProviderUnavailableError
        return endpoints
