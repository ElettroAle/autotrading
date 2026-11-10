import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.tenancy.resolve_tenant import ResolveTenantCommand, ResolveTenantUseCase
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.tenant_repository import InMemoryTenantRepositoryAdapter
from tests.support.directory import Directory

scenarios("E0-esecuzione-verificata/F0.1-accesso-alla-piattaforma/R0.1.2-tenant-utente-al-primo-accesso.feature")


@pytest.fixture
def directory() -> Directory:
    return Directory()


@pytest.fixture
def tenants() -> InMemoryTenantRepositoryAdapter:
    return InMemoryTenantRepositoryAdapter()


@pytest.fixture
def accesses() -> dict[str, list[TenantId]]:
    return {}


def access(name: str, directory: Directory, tenants: InMemoryTenantRepositoryAdapter) -> TenantId:
    command = ResolveTenantCommand(UserId(directory.person(name).object_id))
    return ResolveTenantUseCase(tenants).execute(command)


@given(parsers.parse('che "{name}" ha un tenant'))
def has_tenant(
    name: str, directory: Directory, tenants: InMemoryTenantRepositoryAdapter, accesses: dict[str, list[TenantId]]
) -> None:
    accesses.setdefault(name, []).append(access(name, directory, tenants))


@given(parsers.parse('che nella directory il nome visualizzato di "{name}" cambia in "{display_name}"'))
def display_name_changes(name: str, display_name: str, directory: Directory) -> None:
    directory.person(name).display_name = display_name


@when(parsers.parse('"{name}" accede di nuovo alla piattaforma'))
def accesses_again(
    name: str, directory: Directory, tenants: InMemoryTenantRepositoryAdapter, accesses: dict[str, list[TenantId]]
) -> None:
    accesses.setdefault(name, []).append(access(name, directory, tenants))


@then(parsers.parse('"{name}" ritrova lo stesso tenant'))
def same_tenant(name: str, accesses: dict[str, list[TenantId]]) -> None:
    first, again = accesses[name]
    assert again == first
