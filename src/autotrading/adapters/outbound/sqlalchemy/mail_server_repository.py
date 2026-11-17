from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Connection, Engine, RowMapping, delete, func, select
from sqlalchemy.dialects.postgresql import insert

from autotrading.adapters.outbound.sqlalchemy.tables import notification_mail_servers
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.notifications.mail_security import MailSecurity
from autotrading.domain.notifications.mail_server import MailServer
from autotrading.domain.notifications.sealed_mail_password import SealedMailPassword
from autotrading.domain.tenancy.tenant_id import TenantId


class SqlAlchemyMailServerRepositoryAdapter:
    """Bound to the tenant of the request: every transaction declares it, and row level security does the rest."""

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def get(self) -> MailServer | None:
        with self._transaction() as connection:
            row = connection.execute(select(notification_mail_servers)).mappings().one_or_none()
        return None if row is None else _server_of(row)

    def save(self, server: MailServer) -> None:
        if server.tenant_id != self._tenant_id:
            raise CrossTenantAccessError
        values = _row_of(server)
        statement = insert(notification_mail_servers).values(values)
        # One server per tenant: a new one replaces the previous one (R3.5.5).
        statement = statement.on_conflict_do_update(
            index_elements=[notification_mail_servers.c.tenant_id],
            set_={**{name: value for name, value in values.items() if name != "tenant_id"}, "updated_at": func.now()},
        )
        with self._transaction() as connection:
            connection.execute(statement)

    def remove(self) -> None:
        with self._transaction() as connection:
            connection.execute(delete(notification_mail_servers))

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


def _row_of(server: MailServer) -> dict[str, object]:
    return {
        "tenant_id": server.tenant_id.value,
        "host": server.host,
        "port": server.port,
        "security": server.security.value,
        "username": server.username,
        "sender": server.sender.value,
        "sealed_password": server.password.ciphertext,
        "key_version": server.password.key_version,
    }


def _server_of(row: RowMapping) -> MailServer:
    return MailServer(
        TenantId(row["tenant_id"]),
        row["host"],
        row["port"],
        MailSecurity(row["security"]),
        row["username"],
        EmailAddress(row["sender"]),
        SealedMailPassword(row["key_version"], bytes(row["sealed_password"])),
    )
