from dataclasses import replace

from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.notifications.pending_link import PendingLink
from autotrading.domain.tenancy.tenant_id import TenantId

type LinkCodeStore = dict[bytes, PendingLink]


class InMemoryLinkCodeRepositoryAdapter:
    """Bound to a tenant, like the SQLAlchemy adapter under row level security."""

    def __init__(self, store: LinkCodeStore, tenant_id: TenantId) -> None:
        self._store = store
        self._tenant_id = tenant_id

    def add(self, link: PendingLink) -> None:
        if link.tenant_id != self._tenant_id:
            raise CrossTenantAccessError
        self._store[link.digest] = link

    def get(self, digest: bytes) -> PendingLink | None:
        link = self._store.get(digest)
        return link if link is not None and link.tenant_id == self._tenant_id else None

    def use(self, digest: bytes) -> bool:
        link = self.get(digest)
        if link is None or link.used:
            return False
        self._store[digest] = replace(link, used=True)
        return True


class InMemoryLinkCodeLookupAdapter:
    def __init__(self, store: LinkCodeStore) -> None:
        self._store = store

    def tenant_of(self, digest: bytes) -> TenantId | None:
        link = self._store.get(digest)
        return None if link is None else link.tenant_id


class RacedLinkCodeRepositoryAdapter(InMemoryLinkCodeRepositoryAdapter):
    """Another chat redeems the code between the read and the use: the read still shows it unused."""

    def use(self, digest: bytes) -> bool:
        super().use(digest)
        return False
