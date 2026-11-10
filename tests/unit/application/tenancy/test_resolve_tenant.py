import pytest

from autotrading.application.tenancy.errors import TenantAlreadyExistsError
from autotrading.application.tenancy.resolve_tenant import ResolveTenantCommand, ResolveTenantUseCase
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.tenant_repository import InMemoryTenantRepositoryAdapter

ANNA = UserId("oid-anna")


@pytest.fixture
def tenants() -> InMemoryTenantRepositoryAdapter:
    return InMemoryTenantRepositoryAdapter()


def test_founds_a_tenant_at_the_first_access(tenants: InMemoryTenantRepositoryAdapter) -> None:
    tenant_id = ResolveTenantUseCase(tenants).execute(ResolveTenantCommand(ANNA))

    assert tenants.tenants == [Tenant(tenant_id, ANNA)]


def test_returns_the_same_tenant_at_later_accesses(tenants: InMemoryTenantRepositoryAdapter) -> None:
    resolve = ResolveTenantUseCase(tenants)

    first = resolve.execute(ResolveTenantCommand(ANNA))
    second = resolve.execute(ResolveTenantCommand(ANNA))

    assert first == second
    assert len(tenants.tenants) == 1


def test_returns_the_tenant_founded_by_a_concurrent_first_access(tenants: InMemoryTenantRepositoryAdapter) -> None:
    concurrent = Tenant.found_for(ANNA)
    tenants.create_concurrently_on_next_add(concurrent)

    tenant_id = ResolveTenantUseCase(tenants).execute(ResolveTenantCommand(ANNA))

    assert tenant_id == concurrent.id
    assert tenants.tenants == [concurrent]


def test_reports_the_conflict_when_no_tenant_is_found_after_it(tenants: InMemoryTenantRepositoryAdapter) -> None:
    tenants.refuse_next_add_without_storing()

    with pytest.raises(TenantAlreadyExistsError) as raised:
        ResolveTenantUseCase(tenants).execute(ResolveTenantCommand(ANNA))

    assert raised.value.user_id == ANNA


def test_tenant_already_exists_error_names_the_user() -> None:
    error = TenantAlreadyExistsError(ANNA)

    assert error.user_id == ANNA
    assert str(error) == "il tenant dell'utente esiste già"
