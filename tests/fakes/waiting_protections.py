"""Fake of the recording of the protections waiting on the exchange of the positions of a flow (R5.5.3)."""

from decimal import Decimal

from autotrading.application.flows.ports import FlowHeldAssets
from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.protection_repository import ProtectionStore


class FakeWaitingProtectionsAdapter:
    """Records in the store the protections waiting on the exchange of the assets it is asked, as the orders context
    does for a position without protections recorded, and remembers what it was asked.
    """

    def __init__(self, store: ProtectionStore, tenant_id: TenantId) -> None:
        self._store = store
        self._tenant_id = tenant_id
        self.asked: list[FlowHeldAssets] = []
        # The protections waiting on the exchange for each asset, never recorded by the platform.
        self.waiting: dict[str, list[tuple[ProtectionKind, Decimal]]] = {}

    def execute(self, held: FlowHeldAssets) -> None:
        self.asked.append(held)
        for asset in held.assets:
            for kind, price in self.waiting.pop(asset, []):
                protection = PlacedProtection(
                    held.account_id, held.flow_id, asset, kind, price, f"{asset}-{kind.name}", ClientOrderId.new()
                )
                self._store.protections.append((self._tenant_id, protection))
