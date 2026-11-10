from sqlalchemy import Engine, insert, select
from sqlalchemy.exc import IntegrityError

from autotrading.adapters.outbound.sqlalchemy.tables import memberships, tenants
from autotrading.application.tenancy.errors import TenantAlreadyExistsError
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId


class SqlAlchemyTenantRepositoryAdapter:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def find_by_member(self, user_id: UserId) -> Tenant | None:
        query = select(memberships.c.tenant_id).where(memberships.c.user_id == user_id.value)
        with self._engine.connect() as connection:
            tenant_id = connection.execute(query).scalar_one_or_none()
        if tenant_id is None:
            return None
        return Tenant(TenantId(tenant_id), user_id)

    def add(self, tenant: Tenant) -> None:
        try:
            with self._engine.begin() as connection:
                connection.execute(insert(tenants).values(id=tenant.id.value))
                connection.execute(insert(memberships).values(user_id=tenant.owner.value, tenant_id=tenant.id.value))
        except IntegrityError as error:
            raise TenantAlreadyExistsError(tenant.owner) from error
