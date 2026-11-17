from uuid import uuid4

import pytest
from sqlalchemy import Engine, select

from autotrading.adapters.outbound.sqlalchemy.notification_email_repository import (
    SqlAlchemyNotificationEmailRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.tables import notification_emails
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.notifications.notification_email import NotificationEmail
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId

pytestmark = pytest.mark.integration


def new_tenant(database: Engine) -> TenantId:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    return tenant.id


def email_of(tenant_id: TenantId, address: str) -> NotificationEmail:
    return NotificationEmail(tenant_id, EmailAddress.parse(address))


def test_an_address_reads_back_and_a_new_one_replaces_it(database: Engine) -> None:
    anna = new_tenant(database)
    emails = SqlAlchemyNotificationEmailRepositoryAdapter(database, anna)

    assert emails.get() is None
    emails.set(email_of(anna, "anna@example.com"))
    emails.set(email_of(anna, "anna2@example.com"))

    assert emails.get() == email_of(anna, "anna2@example.com")


def test_a_removed_address_is_no_more_and_removing_again_is_no_error(database: Engine) -> None:
    anna = new_tenant(database)
    emails = SqlAlchemyNotificationEmailRepositoryAdapter(database, anna)
    emails.set(email_of(anna, "anna@example.com"))

    emails.remove()
    emails.remove()

    assert emails.get() is None


def test_a_tenant_never_sees_nor_changes_the_address_of_another(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    SqlAlchemyNotificationEmailRepositoryAdapter(database, anna).set(email_of(anna, "anna@example.com"))
    bruno_emails = SqlAlchemyNotificationEmailRepositoryAdapter(database, bruno)

    assert bruno_emails.get() is None
    bruno_emails.remove()
    with pytest.raises(CrossTenantAccessError):
        bruno_emails.set(email_of(anna, "bruno@example.com"))

    assert SqlAlchemyNotificationEmailRepositoryAdapter(database, anna).get() == email_of(anna, "anna@example.com")


def test_a_transaction_without_a_tenant_sees_no_address(database: Engine) -> None:
    anna = new_tenant(database)
    SqlAlchemyNotificationEmailRepositoryAdapter(database, anna).set(email_of(anna, "anna@example.com"))

    with database.begin() as connection:
        visible = connection.execute(select(notification_emails.c.tenant_id)).scalars().all()

    assert visible == []
