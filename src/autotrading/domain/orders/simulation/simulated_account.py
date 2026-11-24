from dataclasses import dataclass, replace
from decimal import Decimal

from autotrading.domain.orders.simulation.simulated_position import SimulatedPosition

ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class SimulatedAccount:
    """The virtual balance of an account on the simulated exchange and its open positions (R6.3.2).

    The balance is what the account holds without the unrealized PnL: the fees, the realized PnL and the movements move
    it. The value of the account adds the unrealized PnL at the last price read, as an exchange shows it; the margin of
    the open positions is part of that value and not available to new ones.
    """

    balance: Decimal
    positions: tuple[SimulatedPosition, ...] = ()

    @property
    def unrealized_pnl(self) -> Decimal:
        return sum((position.unrealized_pnl(position.mark) for position in self.positions), ZERO)

    @property
    def value(self) -> Decimal:
        return self.balance + self.unrealized_pnl

    @property
    def available_margin(self) -> Decimal:
        return self.value - sum((position.margin for position in self.positions), ZERO)

    def position_of(self, coin: str) -> SimulatedPosition | None:
        return next((position for position in self.positions if position.coin == coin), None)

    def with_position(self, coin: str, position: SimulatedPosition | None) -> SimulatedAccount:
        """The account with the position of the coin replaced, or gone when there is none."""
        others = tuple(held for held in self.positions if held.coin != coin)
        return replace(self, positions=others if position is None else (*others, position))

    def moved(self, amount: Decimal) -> SimulatedAccount:
        return replace(self, balance=self.balance + amount)
