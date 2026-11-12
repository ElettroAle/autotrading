from autotrading.application.notifications.errors import ChatNotLinkedError
from autotrading.application.tenancy.errors import CrossTenantAccessError
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
