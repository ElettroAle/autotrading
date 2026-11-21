"""The platform of a test behind its programmatic interface, mounted as the tests of the routes mount it
(tests/unit/adapters/api): a user reaches it with a token of the identity provider and the role Utente.
"""

from fastapi.testclient import TestClient
from httpx2 import Response

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform

USER_ROLE = "Utente"


class ApiSession:
    def __init__(self, platform: Platform) -> None:
        self._platform = platform
        self._identity_provider = IdentityProvider()
        self._api = create_api(
            HealthReport("1.0.0", "dev"),
            ResolveTenantUseCase(platform.tenants),
            platform.for_tenant,
            self._identity_provider.authentication(),
        )

    def get_as(self, user: str, path: str) -> Response:
        return self._client_of(user).get(path)

    def post_as(self, user: str, path: str, body: object = None) -> Response:
        return self._client_of(user).post(path, json=body)

    def _client_of(self, user: str) -> TestClient:
        person = self._platform.directory.person(user)
        person.roles.add(USER_ROLE)
        token = self._identity_provider.token_for(person)
        return TestClient(self._api, headers={"Authorization": f"Bearer {token}"})
