from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Connection, Engine, RowMapping, func, insert, select, update

from autotrading.adapters.outbound.sqlalchemy.tables import telegram_link_codes
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.notifications.pending_link import PendingLink
from autotrading.domain.tenancy.tenant_id import TenantId


class SqlAlchemyLinkCodeRepositoryAdapter:
    """Bound to the tenant of the request: every transaction declares it, and row level security does the rest."""

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def add(self, link: PendingLink) -> None:
        if link.tenant_id != self._tenant_id:
            raise CrossTenantAccessError
        row = {"digest": link.digest, "tenant_id": link.tenant_id.value, "issued_at": link.issued_at}
        with self._transaction() as connection:
            connection.execute(insert(telegram_link_codes).values(row))

    def get(self, digest: bytes) -> PendingLink | None:
        query = select(telegram_link_codes).where(telegram_link_codes.c.digest == digest)
        with self._transaction() as connection:
            row = connection.execute(query).mappings().one_or_none()
        return None if row is None else _link_of(row)

    def use(self, digest: bytes) -> bool:
        # One statement: of two chats sending the same code at once, only one finds it unused.
        statement = (
            update(telegram_link_codes)
            .where(telegram_link_codes.c.digest == digest, telegram_link_codes.c.used_at.is_(None))
            .values(used_at=func.now())
        )
        with self._transaction() as connection:
            return connection.execute(statement).rowcount == 1

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


class SqlAlchemyLinkCodeLookupAdapter:
    """Finds who asked for a code before the tenant is known: the transaction declares the digest, not a tenant,
    and row level security lets it read that row alone (ADR 0035).
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def tenant_of(self, digest: bytes) -> TenantId | None:
        query = select(telegram_link_codes.c.tenant_id).where(telegram_link_codes.c.digest == digest)
        with self._engine.begin() as connection:
            connection.execute(select(func.set_config("app.link_code_digest", digest.hex(), True)))
            tenant = connection.execute(query).scalar_one_or_none()
        return None if tenant is None else TenantId(tenant)


def _link_of(row: RowMapping) -> PendingLink:
    return PendingLink(TenantId(row["tenant_id"]), row["digest"], row["issued_at"], used=row["used_at"] is not None)
