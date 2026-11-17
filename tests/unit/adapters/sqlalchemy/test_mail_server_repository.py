import pytest
from sqlalchemy import create_engine

from autotrading.adapters.outbound.sqlalchemy.mail_server_repository import SqlAlchemyMailServerRepositoryAdapter
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.mail_servers import MailServers

# The engine never connects: the test stops before the database.
ENGINE = create_engine("postgresql+psycopg://nobody@unreachable.invalid/none")


def test_the_server_of_another_tenant_is_refused_before_the_database() -> None:
    servers = SqlAlchemyMailServerRepositoryAdapter(ENGINE, TenantId.new())
    other = TenantId.new()

    with pytest.raises(CrossTenantAccessError):
        servers.save(MailServers().configure(other, "bruno@example.com"))
