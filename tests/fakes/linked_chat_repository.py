from autotrading.application.notifications.errors import ChatNotLinkedError
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.tenancy.tenant_id import TenantId

type LinkedChatStore = dict[TenantId, LinkedChat]


class InMemoryLinkedChatRepositoryAdapter:
    """Bound to a tenant, like the SQLAlchemy adapter under row level security."""

    def __init__(self, store: LinkedChatStore, tenant_id: TenantId) -> None:
        self._store = store
        self._tenant_id = tenant_id

    def get(self) -> LinkedChat | None:
        return self._store.get(self._tenant_id)

    def link(self, chat: LinkedChat) -> None:
        if chat.tenant_id != self._tenant_id:
            raise CrossTenantAccessError
        self._store[self._tenant_id] = chat

    def unlink(self) -> None:
        if self._store.pop(self._tenant_id, None) is None:
            raise ChatNotLinkedError


class InMemoryLinkedChatLookupAdapter:
    def __init__(self, store: LinkedChatStore) -> None:
        self._store = store

    def tenants_of(self, chat_id: ChatId) -> tuple[TenantId, ...]:
        return tuple(tenant_id for tenant_id, chat in self._store.items() if chat.chat_id == chat_id)
