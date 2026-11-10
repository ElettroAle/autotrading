import pytest
from sqlalchemy import Engine, func, select

from autotrading.adapters.outbound.sqlalchemy.tables import tenants
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.tenancy.errors import TenantAlreadyExistsError
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.user_id import UserId

pytestmark = pytest.mark.integration


def test_finds_no_tenant_for_a_user_who_never_entered(database: Engine) -> None:
    assert SqlAlchemyTenantRepositoryAdapter(database).find_by_member(UserId("oid-never-entered")) is None


def test_finds_the_tenant_added_for_its_owner(database: Engine) -> None:
    repository = SqlAlchemyTenantRepositoryAdapter(database)
    tenant = Tenant.found_for(UserId("oid-anna"))

    repository.add(tenant)

    assert repository.find_by_member(UserId("oid-anna")) == tenant


def test_refuses_a_second_tenant_for_the_same_user(database: Engine) -> None:
    repository = SqlAlchemyTenantRepositoryAdapter(database)
    repository.add(Tenant.found_for(UserId("oid-bruno")))
    second = Tenant.found_for(UserId("oid-bruno"))

    with pytest.raises(TenantAlreadyExistsError) as raised:
        repository.add(second)

    assert raised.value.user_id == UserId("oid-bruno")


def count_tenants(database: Engine) -> int:
    with database.connect() as connection:
        return connection.execute(select(func.count()).select_from(tenants)).scalar_one()


def test_a_refused_tenant_leaves_no_orphan_row(database: Engine) -> None:
    repository = SqlAlchemyTenantRepositoryAdapter(database)
    first = Tenant.found_for(UserId("oid-carla"))
    repository.add(first)
    before = count_tenants(database)

    with pytest.raises(TenantAlreadyExistsError):
        repository.add(Tenant.found_for(UserId("oid-carla")))

    assert count_tenants(database) == before
    assert repository.find_by_member(UserId("oid-carla")) == first
