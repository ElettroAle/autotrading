from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Connection, Engine, delete, func, select
from sqlalchemy.dialects.postgresql import insert

from autotrading.adapters.outbound.sqlalchemy.tables import telegram_chats
from autotrading.application.notifications.errors import ChatNotLinkedError
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.tenancy.tenant_id import TenantId


class SqlAlchemyLinkedChatRepositoryAdapter:
    """Bound to the tenant of the request: every transaction declares it, and row level security does the rest."""

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def get(self) -> LinkedChat | None:
        with self._transaction() as connection:
            chat_id = connection.execute(select(telegram_chats.c.chat_id)).scalar_one_or_none()
        return None if chat_id is None else LinkedChat(self._tenant_id, ChatId(chat_id))

    def link(self, chat: LinkedChat) -> None:
        if chat.tenant_id != self._tenant_id:
            raise CrossTenantAccessError
        statement = insert(telegram_chats).values(tenant_id=chat.tenant_id.value, chat_id=chat.chat_id.value)
        # At most one chat per tenant: a new link replaces the previous one (R1.8.1).
        statement = statement.on_conflict_do_update(
            index_elements=[telegram_chats.c.tenant_id],
            set_={"chat_id": statement.excluded.chat_id, "linked_at": func.now()},
        )
        with self._transaction() as connection:
            connection.execute(statement)

    def unlink(self) -> None:
        with self._transaction() as connection:
            if connection.execute(delete(telegram_chats)).rowcount != 1:
                raise ChatNotLinkedError

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


class SqlAlchemyLinkedChatLookupAdapter:
    """Finds the tenants of a chat before the tenant is known: the transaction declares the chat, not a tenant,
    and row level security lets it read the links of that chat alone (ADR 0081).
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def tenants_of(self, chat_id: ChatId) -> tuple[TenantId, ...]:
        query = select(telegram_chats.c.tenant_id).where(telegram_chats.c.chat_id == chat_id.value)
        with self._engine.begin() as connection:
            connection.execute(select(func.set_config("app.telegram_chat_id", str(chat_id.value), True)))
            tenants = connection.execute(query).scalars().all()
        return tuple(TenantId(tenant) for tenant in tenants)
