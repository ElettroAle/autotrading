import pytest
from sqlalchemy import create_engine

from autotrading.adapters.outbound.sqlalchemy.notification_email_repository import (
    SqlAlchemyNotificationEmailRepositoryAdapter,
)
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.notifications.notification_email import NotificationEmail
from autotrading.domain.tenancy.tenant_id import TenantId

# The engine never connects: the test stops before the database.
ENGINE = create_engine("postgresql+psycopg://nobody@unreachable.invalid/none")


def test_the_address_of_another_tenant_is_refused_before_the_database() -> None:
    emails = SqlAlchemyNotificationEmailRepositoryAdapter(ENGINE, TenantId.new())

    with pytest.raises(CrossTenantAccessError):
        emails.set(NotificationEmail(TenantId.new(), EmailAddress.parse("anna@example.com")))
