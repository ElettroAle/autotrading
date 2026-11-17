from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.notifications.mail_server import MailServer
from autotrading.domain.tenancy.tenant_id import TenantId

type MailServerStore = dict[TenantId, MailServer]


class InMemoryMailServerRepositoryAdapter:
    """Bound to a tenant, like the SQLAlchemy adapter under row level security."""

    def __init__(self, store: MailServerStore, tenant_id: TenantId) -> None:
        self._store = store
        self._tenant_id = tenant_id

    def get(self) -> MailServer | None:
        return self._store.get(self._tenant_id)

    def save(self, server: MailServer) -> None:
        if server.tenant_id != self._tenant_id:
            raise CrossTenantAccessError
        self._store[self._tenant_id] = server

    def remove(self) -> None:
        self._store.pop(self._tenant_id, None)
