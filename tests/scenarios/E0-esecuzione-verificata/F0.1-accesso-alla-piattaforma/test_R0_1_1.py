from collections.abc import Callable

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.tenant_repository import InMemoryTenantRepositoryAdapter
from tests.support.directory import Directory
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

scenarios("E0-esecuzione-verificata/F0.1-accesso-alla-piattaforma/R0.1.1-accesso-riservato-al-ruolo-utente.feature")

# Operational routes that answer without an identity: the deploy health check reads /health (ADR 0016).
PUBLIC_PATHS = frozenset({"/health"})


@pytest.fixture
def directory() -> Directory:
    return Directory()


@pytest.fixture
def identity_provider() -> IdentityProvider:
    return IdentityProvider()


@pytest.fixture
def tenants() -> InMemoryTenantRepositoryAdapter:
    return InMemoryTenantRepositoryAdapter()


@pytest.fixture
def api(identity_provider: IdentityProvider, tenants: InMemoryTenantRepositoryAdapter) -> FastAPI:
    return create_api(
        HealthReport(version="1.0.0", environment="dev"),
        ResolveTenantUseCase(tenants),
        Platform().for_tenant,
        identity_provider.authentication(),
    )


@pytest.fixture
def accesses() -> dict[str, httpx.Response]:
    return {}


@pytest.fixture
def access(directory: Directory, identity_provider: IdentityProvider, api: FastAPI) -> Callable[[str], httpx.Response]:
    def access_as(name: str) -> httpx.Response:
        # Every access presents a token freshly issued by the directory, with the roles the person has now.
        token = identity_provider.token_for(directory.person(name))
        response: httpx.Response = TestClient(api).get("/me", headers={"Authorization": f"Bearer {token}"})
        return response

    return access_as


@given(parsers.parse('che la persona "{name}" esiste nella directory con il ruolo "{role}"'))
def person_with_role(name: str, role: str, directory: Directory) -> None:
    directory.person(name).roles.add(role)


@given(parsers.parse('che la persona "{name}" esiste nella directory senza il ruolo "{role}"'))
def person_without_role(name: str, role: str, directory: Directory) -> None:
    directory.person(name).roles.discard(role)


@given(parsers.parse('che la persona "{name}" ha avuto accesso con il ruolo "{role}"'))
def person_had_access(
    name: str,
    role: str,
    directory: Directory,
    access: Callable[[str], httpx.Response],
    accesses: dict[str, httpx.Response],
) -> None:
    directory.person(name).roles.add(role)
    accesses[name] = access(name)
    assert accesses[name].status_code == 200


@given(parsers.parse('che nella directory a "{name}" viene tolto il ruolo "{role}"'))
def role_revoked(name: str, role: str, directory: Directory) -> None:
    directory.person(name).roles.discard(role)


@when(parsers.parse('"{name}" accede alla piattaforma'))
@when(parsers.parse('"{name}" accede di nuovo alla piattaforma con una nuova identità emessa dalla directory'))
def person_accesses(name: str, access: Callable[[str], httpx.Response], accesses: dict[str, httpx.Response]) -> None:
    accesses[name] = access(name)


@when(
    "una richiesta senza identità raggiunge una qualunque funzione della piattaforma",
    target_fixture="anonymous_responses",
)
def anonymous_request_to_every_function(api: FastAPI) -> dict[str, int]:
    client = TestClient(api)
    # The OpenAPI document lists every function the platform publishes.
    functions = {path: operations for path, operations in api.openapi()["paths"].items() if path not in PUBLIC_PATHS}
    assert functions, "the platform exposes no function to protect"
    return {
        f"{method.upper()} {path}": client.request(method, path).status_code
        for path, operations in functions.items()
        for method in operations
    }


@then(parsers.parse('l\'accesso di "{name}" è consentito'))
def access_allowed(name: str, accesses: dict[str, httpx.Response]) -> None:
    assert accesses[name].status_code == 200


@then(parsers.parse('la piattaforma identifica "{name}" con l\'identificativo che la directory le assegna'))
def identified_by_directory(name: str, directory: Directory, accesses: dict[str, httpx.Response]) -> None:
    assert accesses[name].json()["user_id"] == directory.person(name).object_id


@then(parsers.parse('l\'accesso di "{name}" è negato con il motivo "{reason}"'))
def access_denied(name: str, reason: str, accesses: dict[str, httpx.Response]) -> None:
    assert (accesses[name].status_code, reason_of(accesses[name])) == (403, {"detail": reason})


@then(parsers.parse('la piattaforma non crea alcun tenant per "{name}"'))
def no_tenant(name: str, directory: Directory, tenants: InMemoryTenantRepositoryAdapter) -> None:
    assert tenants.find_by_member(UserId(directory.person(name).object_id)) is None


@then("la richiesta senza identità è respinta come non autenticata")
def rejected_as_unauthenticated(anonymous_responses: dict[str, int]) -> None:
    assert anonymous_responses == dict.fromkeys(anonymous_responses, 401)
