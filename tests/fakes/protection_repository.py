"""Fake of the protections the platform placed: those of every tenant, bound to one per request."""

from uuid import UUID

from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.tenancy.tenant_id import TenantId


class ProtectionStore:
    """The protections in force, and every protection ever placed: a removed one stays recorded, as in the database."""

    def __init__(self) -> None:
        self.protections: list[tuple[TenantId, PlacedProtection]] = []
        self.placed: list[tuple[TenantId, PlacedProtection]] = []


class InMemoryProtectionRepositoryAdapter:
    """Bound to one tenant, like the real adapter under row level security."""

    def __init__(self, store: ProtectionStore, tenant_id: TenantId) -> None:
        self._store = store
        self._tenant_id = tenant_id

    def add(self, protection: PlacedProtection) -> None:
        self._store.protections.append((self._tenant_id, protection))
        self._store.placed.append((self._tenant_id, protection))

    def placed(self, account_id: UUID, asset: str) -> tuple[PlacedProtection, ...]:
        return tuple(
            protection
            for tenant_id, protection in self._store.protections
            if tenant_id == self._tenant_id and (protection.account_id, protection.asset) == (account_id, asset)
        )

    def remove(self, account_id: UUID, asset: str, kind: ProtectionKind | None = None) -> None:
        kept = [
            (tenant_id, protection)
            for tenant_id, protection in self._store.protections
            if not (
                tenant_id == self._tenant_id
                and (protection.account_id, protection.asset) == (account_id, asset)
                and kind in {None, protection.kind}
            )
        ]
        self._store.protections[:] = kept
