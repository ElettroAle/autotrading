from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.notifications.channel_preferences import ChannelPreferences
from autotrading.domain.tenancy.tenant_id import TenantId

type ChannelPreferencesStore = dict[TenantId, ChannelPreferences]


class InMemoryChannelPreferencesRepositoryAdapter:
    """Bound to a tenant, like the SQLAlchemy adapter under row level security."""

    def __init__(self, store: ChannelPreferencesStore, tenant_id: TenantId) -> None:
        self._store = store
        self._tenant_id = tenant_id

    def get(self) -> ChannelPreferences:
        return self._store.get(self._tenant_id, ChannelPreferences.of(self._tenant_id))

    def save(self, preferences: ChannelPreferences) -> None:
        if preferences.tenant_id != self._tenant_id:
            raise CrossTenantAccessError
        self._store[self._tenant_id] = preferences
