"""The mail server of each tenant in PostgreSQL, under row level security (ADR server-di-posta-per-tenant)."""

from uuid import uuid4

import pytest
from sqlalchemy import Engine, select

from autotrading.adapters.outbound.sqlalchemy.mail_server_repository import SqlAlchemyMailServerRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import notification_mail_servers
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.notifications.mail_security import MailSecurity
from autotrading.domain.notifications.mail_server import MailServer, MailServerAddress
from autotrading.domain.notifications.sealed_mail_password import SealedMailPassword
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId

pytestmark = pytest.mark.integration


def new_tenant(database: Engine) -> TenantId:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    return tenant.id


def server_of(tenant_id: TenantId, port: int = 587, security: MailSecurity = MailSecurity.STARTTLS) -> MailServer:
    address = MailServerAddress("smtp.example.com", port, security, "anna@example.com", "avvisi@example.com")
    return MailServer.of(tenant_id, address, SealedMailPassword(2, b"\x00sealed\xff"))


def test_a_server_reads_back_with_its_sealed_password_and_a_new_one_replaces_it(database: Engine) -> None:
    anna = new_tenant(database)
    servers = SqlAlchemyMailServerRepositoryAdapter(database, anna)

    assert servers.get() is None
    servers.save(server_of(anna))
    servers.save(server_of(anna, 465, MailSecurity.TLS))

    assert servers.get() == server_of(anna, 465, MailSecurity.TLS)


def test_a_removed_server_is_no_more_and_removing_again_is_no_error(database: Engine) -> None:
    anna = new_tenant(database)
    servers = SqlAlchemyMailServerRepositoryAdapter(database, anna)
    servers.save(server_of(anna))

    servers.remove()
    servers.remove()

    assert servers.get() is None


def test_a_tenant_never_sees_nor_changes_the_server_of_another(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    SqlAlchemyMailServerRepositoryAdapter(database, anna).save(server_of(anna))
    bruno_servers = SqlAlchemyMailServerRepositoryAdapter(database, bruno)

    assert bruno_servers.get() is None
    bruno_servers.remove()
    with pytest.raises(CrossTenantAccessError):
        bruno_servers.save(server_of(anna))

    assert SqlAlchemyMailServerRepositoryAdapter(database, anna).get() == server_of(anna)


def test_a_transaction_without_a_tenant_sees_no_server(database: Engine) -> None:
    anna = new_tenant(database)
    SqlAlchemyMailServerRepositoryAdapter(database, anna).save(server_of(anna))

    with database.begin() as connection:
        visible = connection.execute(select(notification_mail_servers.c.tenant_id)).scalars().all()

    assert visible == []
