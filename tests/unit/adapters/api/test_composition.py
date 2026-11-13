from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.configuration.errors import MissingConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.inbound.api.composition import api_adapters, worker_api_adapters
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.adapters.inbound.api.worker import WorkerUseCases
from autotrading.application.tenancy.ports import LoginEndpoints
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.verified_identity import VerifiedIdentity
from tests.fakes.tenant_repository import InMemoryTenantRepositoryAdapter

VERSION = {"APP_VERSION": "1.2.1", "APP_ENVIRONMENT": "prod"}
CLIENT = {"AUTH_CLIENT_ID": "swagger-client", "AUTH_SCOPE": "api://autotrading/access"}


class UnusedVerifier:
    def verify(self, token: str) -> VerifiedIdentity:
        raise AssertionError(token)


class StubLogin:
    def endpoints(self) -> LoginEndpoints:
        return LoginEndpoints("https://login.example.test/authorize", "https://login.example.test/token")


def _no_tenant_use_cases(tenant_id: TenantId) -> TenantUseCases:
    raise AssertionError(tenant_id)


def _no_worker_use_cases(tenant_id: TenantId) -> WorkerUseCases:
    raise AssertionError(tenant_id)


def _api(values: dict[str, str], *, login: bool = False) -> TestClient:
    resolve_tenant = ResolveTenantUseCase(InMemoryTenantRepositoryAdapter())
    adapters = (UnusedVerifier(), StubLogin()) if login else None
    return TestClient(api_adapters(ConfigurationSource(values), resolve_tenant, _no_tenant_use_cases, adapters))


def test_the_api_declares_its_version_and_environment() -> None:
    assert _api(VERSION).get("/health").json() == {"version": "1.2.1", "environment": "prod"}


def test_the_api_needs_its_version() -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        _api({"APP_ENVIRONMENT": "dev"})

    assert raised.value.name == "APP_VERSION"


def test_without_a_login_the_client_of_the_openapi_page_is_not_read() -> None:
    assert _api(VERSION).get("/health").status_code == 200


def test_with_a_login_the_openapi_page_logs_in_with_the_declared_client() -> None:
    assert '"clientId": "swagger-client"' in _api(VERSION | CLIENT, login=True).get("/docs").text


@pytest.mark.parametrize("name", ["AUTH_CLIENT_ID", "AUTH_SCOPE"])
def test_a_login_without_its_client_refuses_to_start(name: str) -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        _api(VERSION | CLIENT | {name: ""}, login=True)

    assert raised.value.name == name


def test_the_worker_api_refuses_a_caller_without_the_token_of_the_machine(tmp_path: Path) -> None:
    token = tmp_path / "worker_token"
    token.write_text("t0k\n", encoding="utf-8")
    source = ConfigurationSource({"WORKER_TOKEN_FILE": str(token)})
    client = TestClient(worker_api_adapters(source, _no_worker_use_cases, None, None, None))

    response = client.get("/bot/start-link", headers={"Authorization": "Bearer wrong"})

    assert response.status_code == 401


def test_the_worker_api_needs_the_token_of_the_machine() -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        worker_api_adapters(ConfigurationSource({}), _no_worker_use_cases, None, None, None)

    assert raised.value.name == "WORKER_TOKEN_FILE"
