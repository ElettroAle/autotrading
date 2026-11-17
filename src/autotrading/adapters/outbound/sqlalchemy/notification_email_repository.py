from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Connection, Engine, delete, func, select
from sqlalchemy.dialects.postgresql import insert

from autotrading.adapters.outbound.sqlalchemy.tables import notification_emails
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.notifications.notification_email import NotificationEmail
from autotrading.domain.tenancy.tenant_id import TenantId


class SqlAlchemyNotificationEmailRepositoryAdapter:
    """Bound to the tenant of the request: every transaction declares it, and row level security does the rest."""

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def get(self) -> NotificationEmail | None:
        with self._transaction() as connection:
            address = connection.execute(select(notification_emails.c.address)).scalar_one_or_none()
        return None if address is None else NotificationEmail(self._tenant_id, EmailAddress(address))

    def set(self, email: NotificationEmail) -> None:
        if email.tenant_id != self._tenant_id:
            raise CrossTenantAccessError
        statement = insert(notification_emails).values(tenant_id=email.tenant_id.value, address=email.address.value)
        # One address per tenant: a new one replaces the previous one (R3.5.2).
        statement = statement.on_conflict_do_update(
            index_elements=[notification_emails.c.tenant_id],
            set_={"address": statement.excluded.address, "updated_at": func.now()},
        )
        with self._transaction() as connection:
            connection.execute(statement)

    def remove(self) -> None:
        with self._transaction() as connection:
            connection.execute(delete(notification_emails))

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection
