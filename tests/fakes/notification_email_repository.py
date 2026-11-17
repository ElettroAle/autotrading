from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.notifications.notification_email import NotificationEmail
from autotrading.domain.tenancy.tenant_id import TenantId

type NotificationEmailStore = dict[TenantId, NotificationEmail]


class InMemoryNotificationEmailRepositoryAdapter:
    """Bound to a tenant, like the SQLAlchemy adapter under row level security."""

    def __init__(self, store: NotificationEmailStore, tenant_id: TenantId) -> None:
        self._store = store
        self._tenant_id = tenant_id

    def get(self) -> NotificationEmail | None:
        return self._store.get(self._tenant_id)

    def set(self, email: NotificationEmail) -> None:
        if email.tenant_id != self._tenant_id:
            raise CrossTenantAccessError
        self._store[self._tenant_id] = email

    def remove(self) -> None:
        self._store.pop(self._tenant_id, None)
