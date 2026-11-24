from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition

ONE = Decimal(1)


@dataclass(frozen=True, slots=True)
class SimulatedPosition:
    """A position the simulated exchange holds, with isolated margin like every position of the platform (ADR 0095).

    The maintenance rate is the share of the value the margin must keep: below it the position is liquidated (R6.3.2).
    """

    coin: str
    direction: Direction
    size: Decimal
    leverage: int
    entry_price: Decimal
    margin: Decimal
    maintenance_rate: Decimal
    # The last price the simulation read for the asset: what the account shows the position at.
    mark_price: Decimal | None = None

    @property
    def mark(self) -> Decimal:
        return self.entry_price if self.mark_price is None else self.mark_price

    @property
    def signed_size(self) -> Decimal:
        return self.size if self.direction is Direction.LONG else -self.size

    @property
    def liquidation_price(self) -> Decimal:
        """Where the margin plus the unrealized PnL equals the maintenance margin at that price."""
        if self.direction is Direction.LONG:
            return (self.entry_price - self.margin / self.size) / (ONE - self.maintenance_rate)
        return (self.entry_price + self.margin / self.size) / (ONE + self.maintenance_rate)

    @property
    def held(self) -> HeldPosition:
        return HeldPosition(self.coin, self.direction, self.size, self.leverage, self.entry_price)

    def unrealized_pnl(self, price: Decimal) -> Decimal:
        return (price - self.entry_price) * self.signed_size

    def liquidated_at(self, price: Decimal) -> bool:
        if self.direction is Direction.LONG:
            return price <= self.liquidation_price
        return price >= self.liquidation_price
