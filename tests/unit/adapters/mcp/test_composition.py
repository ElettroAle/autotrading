import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.configuration.errors import InvalidConfigurationError, MissingConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.inbound.mcp.composition import mcp_adapters
from autotrading.adapters.inbound.mcp.server import McpApplication
from autotrading.adapters.inbound.mcp.use_cases import McpUseCases
from autotrading.application.tenancy.ports import LoginEndpoints
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.verified_identity import VerifiedIdentity
from tests.fakes.tenant_repository import InMemoryTenantRepositoryAdapter

SERVER = {
    "APP_VERSION": "1.2.1",
    "MCP_PUBLIC_URL": "https://autotrading.example.ts.net/mcp",
    "AUTH_ISSUER": "https://login.example.test/tenant/v2.0",
    "AUTH_SCOPE": "api://autotrading/access",
}


class UnusedVerifier:
    def verify(self, token: str) -> VerifiedIdentity:
        raise AssertionError(token)


class StubLogin:
    def endpoints(self) -> LoginEndpoints:
        return LoginEndpoints("https://login.example.test/authorize", "https://login.example.test/token")


def _no_use_cases(tenant_id: TenantId) -> McpUseCases:
    raise AssertionError(tenant_id)


def _server(values: dict[str, str], *, login: bool = True) -> McpApplication:
    resolve_tenant = ResolveTenantUseCase(InMemoryTenantRepositoryAdapter())
    adapters = (UnusedVerifier(), StubLogin()) if login else None
    return mcp_adapters(ConfigurationSource(values), resolve_tenant, _no_use_cases, adapters)


def test_the_server_declares_its_version_and_the_resource_of_its_public_address() -> None:
    client = TestClient(_server(SERVER))

    assert client.get("/health").json() == {"name": "AutoTrading", "version": "1.2.1"}
    metadata = client.get("/.well-known/oauth-protected-resource/mcp").json()
    assert (metadata["resource"], metadata["authorization_servers"]) == (
        "https://autotrading.example.ts.net/mcp",
        ["https://login.example.test/tenant/v2.0"],
    )


def test_without_the_directory_the_server_refuses_to_start() -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        _server(SERVER, login=False)

    assert raised.value.name == "AUTH_ISSUER"


@pytest.mark.parametrize("name", ["APP_VERSION", "MCP_PUBLIC_URL", "AUTH_SCOPE"])
def test_the_server_refuses_to_start_without_its_configuration(name: str) -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        _server(SERVER | {name: " "})

    assert raised.value.name == name


def test_a_public_address_not_on_https_refuses_to_start() -> None:
    with pytest.raises(InvalidConfigurationError) as raised:
        _server(SERVER | {"MCP_PUBLIC_URL": "http://autotrading.example.ts.net/mcp"})

    assert raised.value.name == "MCP_PUBLIC_URL"
