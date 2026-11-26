from dataclasses import dataclass
from uuid import UUID

from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ActiveProtection


@dataclass(frozen=True, slots=True)
class HeldProtections:
    """A position open on the exchange with the protections waiting for its price (R3.1.2, R5.5.3)."""

    position: HeldPosition
    waiting: tuple[ActiveProtection, ...]

    @property
    def has_stop_loss(self) -> bool:
        return any(protection.kind is ProtectionKind.STOP_LOSS for protection in self.waiting)

    def recorded_for(self, account_id: UUID, flow_id: UUID) -> tuple[PlacedProtection, ...]:
        """The protections waiting as the platform records them for the flow, like those it places (R5.5.3).

        The exchange does not give back the client order id a protection was placed with, so each gets a new one: the
        account and the asset find it again at the closing of the position, and its exchange order id cancels it.
        """
        return tuple(
            PlacedProtection(
                account_id,
                flow_id,
                self.position.coin,
                protection.kind,
                protection.trigger_price,
                protection.order_id,
                ClientOrderId.new(),
            )
            for protection in self.waiting
        )
