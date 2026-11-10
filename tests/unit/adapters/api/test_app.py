import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import ENVIRONMENT_HEADER, Authentication, HealthReport, create_api
from autotrading.adapters.inbound.api.authentication import AccessTokenVerifier, OidcSigningKeys
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.tenant_repository import InMemoryTenantRepositoryAdapter
from tests.support.directory import Person
from tests.support.identity_provider import SETTINGS, IdentityProvider
from tests.support.platform import Platform


@pytest.fixture
def provider() -> IdentityProvider:
    return IdentityProvider()


@pytest.fixture
def tenants() -> InMemoryTenantRepositoryAdapter:
    return InMemoryTenantRepositoryAdapter()


def client_for(
    environment: str = "dev",
    tenants: InMemoryTenantRepositoryAdapter | None = None,
    provider: IdentityProvider | None = None,
) -> TestClient:
    authentication = None
    if provider is not None:
        verifier = AccessTokenVerifier(SETTINGS, OidcSigningKeys(SETTINGS.discovery_url, provider.fetch))
        authentication = Authentication(SETTINGS, verifier)
    resolve_tenant = ResolveTenantUseCase(tenants or InMemoryTenantRepositoryAdapter())
    health = HealthReport("1.2.1-dev.57", environment)
    return TestClient(create_api(health, resolve_tenant, Platform().for_tenant, authentication))


def test_health_reports_version_and_environment_without_an_identity() -> None:
    response = client_for("dev").get("/health")

    assert response.status_code == 200
    assert response.json() == {"version": "1.2.1-dev.57", "environment": "dev"}


def test_every_response_declares_the_environment() -> None:
    client = client_for("prod")

    responses = [client.get("/health"), client.get("/does-not-exist"), client.post("/health"), client.get("/me")]

    assert [response.status_code for response in responses] == [200, 404, 405, 401]
    assert [response.headers[ENVIRONMENT_HEADER] for response in responses] == ["prod"] * 4


def test_identity_reports_the_user_and_the_tenant_founded_for_it(
    provider: IdentityProvider, tenants: InMemoryTenantRepositoryAdapter
) -> None:
    anna = Person("anna", roles={"Utente"})

    response = client_for(tenants=tenants, provider=provider).get(
        "/me", headers={"Authorization": f"Bearer {provider.token_for(anna)}"}
    )

    tenant = tenants.find_by_member(UserId(anna.object_id))
    assert tenant is not None
    assert response.json() == {"user_id": anna.object_id, "tenant_id": str(tenant.id.value)}


@pytest.mark.parametrize(
    "authorization",
    [None, "Basic YW5uYTpzZWNyZXQ=", "Bearer", "Bearer    ", "bearer not-a-token"],
    ids=["absent", "basic", "no-token", "blank-token", "garbage-token"],
)
def test_rejects_a_request_without_a_usable_bearer_token(provider: IdentityProvider, authorization: str | None) -> None:
    headers = {"Authorization": authorization} if authorization is not None else {}

    response = client_for(provider=provider).get("/me", headers=headers)

    assert (response.status_code, response.json()) == (401, {"detail": "non autenticato"})


def test_accepts_the_scheme_name_in_any_case(provider: IdentityProvider) -> None:
    anna = Person("anna", roles={"Utente"})

    response = client_for(provider=provider).get("/me", headers={"Authorization": f"BEARER {provider.token_for(anna)}"})

    assert response.status_code == 200


def test_without_an_identity_provider_a_token_is_refused_as_not_configured(provider: IdentityProvider) -> None:
    token = provider.token_for(Person("anna", roles={"Utente"}))

    response = client_for().get("/me", headers={"Authorization": f"Bearer {token}"})

    assert (response.status_code, response.json()) == (503, {"detail": "autenticazione non configurata"})


def test_openapi_page_logs_in_with_the_issuer_through_pkce(provider: IdentityProvider) -> None:
    client = client_for(provider=provider)

    schemes = client.get("/openapi.json").json()["components"]["securitySchemes"]
    page = client.get("/docs").text

    assert schemes == {"OpenIdConnect": {"type": "openIdConnect", "openIdConnectUrl": SETTINGS.discovery_url}}
    assert '"usePkceWithAuthorizationCodeGrant": true' in page
    assert f'"clientId": "{SETTINGS.client_id}"' in page


def test_openapi_page_without_an_identity_provider_offers_a_plain_bearer_token() -> None:
    schemes = client_for().get("/openapi.json").json()["components"]["securitySchemes"]

    assert schemes == {"HTTPBearer": {"type": "http", "scheme": "bearer"}}
