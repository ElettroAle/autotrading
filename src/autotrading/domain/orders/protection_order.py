from dataclasses import dataclass, field
from decimal import Decimal

from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.protection_kind import ProtectionKind


@dataclass(frozen=True, slots=True)
class ProtectionOrder:
    """A stop loss or take profit placed on the exchange over the whole position of a flow on an asset (R3.1.2).

    The closing direction is the direction of the position the order closes; the trigger price is already rounded to
    what the exchange admits. The client order id ties its execution to the flow
    (ADR chiusure-per-protezione-nello-storico).
    """

    asset: str
    kind: ProtectionKind
    closing_direction: Direction
    trigger_price: Decimal
    client_order_id: ClientOrderId = field(default_factory=ClientOrderId.new)

    @property
    def is_buy(self) -> bool:
        # Closing a long sells, closing a short buys.
        return self.closing_direction is Direction.SHORT


@dataclass(frozen=True, slots=True)
class ActiveProtection:
    """A protection still waiting on the exchange for its price, with the identifier the exchange gave it."""

    order_id: str
    kind: ProtectionKind
    trigger_price: Decimal
