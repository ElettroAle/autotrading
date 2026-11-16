from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.italian_text import number_text
from autotrading.domain.orders.direction import Direction

PERCENT = Decimal(100)


@dataclass(frozen=True, slots=True)
class ProtectionLevels:
    """The prices of the protection of a position, and why a level of the agent was changed (R3.1.2)."""

    stop: Decimal
    take_profit: Decimal | None
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProtectionRequest:
    """What protects an opening: the stop and target of the exit plan of the agent, if any, and the defaults of the
    flow in percent of the entry price (R3.1.1, R3.1.2).
    """

    stop: Decimal | None
    target: Decimal | None
    default_stop_percent: Decimal
    default_take_profit_percent: Decimal | None

    def levels_at(self, direction: Direction, entry_price: Decimal) -> ProtectionLevels:
        """The levels on the real entry price: those of the agent where it gave them, the defaults elsewhere.

        A stop of the agent farther from the entry price than the default stop goes back to the default, with a note:
        the agent moves the stop, never beyond the default (decision of the owner).
        """
        default_stop = _away(entry_price, self.default_stop_percent, _loss_sign(direction))
        take_profit = self._take_profit(direction, entry_price)
        if self.stop is None:
            return ProtectionLevels(default_stop, take_profit, ())
        if _farther(self.stop, default_stop, direction):
            note = (
                f"stop {number_text(self.stop)} riportato a {number_text(default_stop)}: "
                f"oltre lo stop predefinito del {number_text(self.default_stop_percent)}%"
            )
            return ProtectionLevels(default_stop, take_profit, (note,))
        return ProtectionLevels(self.stop, take_profit, ())

    def _take_profit(self, direction: Direction, entry_price: Decimal) -> Decimal | None:
        if self.target is not None:
            return self.target
        if self.default_take_profit_percent is None:
            return None
        return _away(entry_price, self.default_take_profit_percent, -_loss_sign(direction))


def _loss_sign(direction: Direction) -> int:
    """Where a loss lies from the entry price: below for a long, above for a short."""
    return -1 if direction is Direction.LONG else 1


def _away(price: Decimal, percent: Decimal, sign: int) -> Decimal:
    return price * (1 + sign * percent / PERCENT)


def _farther(stop: Decimal, default_stop: Decimal, direction: Direction) -> bool:
    return stop < default_stop if direction is Direction.LONG else stop > default_stop
