from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PositionReading:
    """A position as the procedure read it: enough to tell what the exchange holds on the asset."""

    coin: str
    side: str
    size: Decimal
    leverage: int


@dataclass(frozen=True, slots=True)
class AccountReading:
    """Balance, available margin and positions of the account, as the procedure read them from the exchange."""

    balance: Decimal
    available_margin: Decimal
    currency: str
    positions: tuple[PositionReading, ...]

    def positions_on(self, coin: str) -> tuple[PositionReading, ...]:
        return tuple(position for position in self.positions if position.coin == coin)
