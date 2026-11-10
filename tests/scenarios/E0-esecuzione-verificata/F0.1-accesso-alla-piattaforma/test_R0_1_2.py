import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.platform import HYPERLIQUID, Platform, registration
from tests.support.steps import quoted

scenarios("E0-esecuzione-verificata/F0.1-accesso-alla-piattaforma/R0.1.2-tenant-utente-al-primo-accesso.feature")


@pytest.fixture
def platform() -> Platform:
    return Platform()


@pytest.fixture
def accesses() -> dict[str, list[TenantId]]:
    return {}


def access(platform: Platform, name: str, accesses: dict[str, list[TenantId]]) -> None:
    accesses.setdefault(name, []).append(platform.tenant_of(name))


@given(quoted('che "{name}" ha un tenant'))
def has_tenant(platform: Platform, accesses: dict[str, list[TenantId]], name: str) -> None:
    access(platform, name, accesses)


@given(quoted('che "{name}" ha un tenant con il conto "{account}"'))
def has_tenant_with_account(platform: Platform, accesses: dict[str, list[TenantId]], name: str, account: str) -> None:
    platform.directory.person(name).roles.add("Utente")
    access(platform, name, accesses)
    platform.register_account(name, registration(account, HYPERLIQUID, platform.accepted_credentials()))


@given(quoted('che nella directory il nome visualizzato di "{name}" cambia in "{display_name}"'))
def display_name_changes(platform: Platform, name: str, display_name: str) -> None:
    platform.directory.person(name).display_name = display_name


@when(quoted('"{name}" accede di nuovo alla piattaforma'))
def accesses_again(platform: Platform, accesses: dict[str, list[TenantId]], name: str) -> None:
    access(platform, name, accesses)


@then(quoted('"{name}" ritrova lo stesso tenant'))
def same_tenant(accesses: dict[str, list[TenantId]], name: str) -> None:
    first, again = accesses[name]
    assert again == first


@then(quoted('la piattaforma non crea un secondo tenant per "{name}"'))
def no_second_tenant(platform: Platform, accesses: dict[str, list[TenantId]], name: str) -> None:
    owner = UserId(platform.directory.person(name).object_id)
    assert [tenant.owner for tenant in platform.tenants.tenants].count(owner) == 1
    assert len(set(accesses[name])) == 1


@then(quoted('il tenant di "{name}" contiene il conto "{account}"'))
def tenant_holds_account(platform: Platform, accesses: dict[str, list[TenantId]], name: str, account: str) -> None:
    (tenant_id,) = set(accesses[name])
    assert account in [saved.name.value for saved in platform.accounts.of(tenant_id)]
