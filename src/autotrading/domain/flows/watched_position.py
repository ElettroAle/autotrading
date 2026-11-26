from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal

from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.flows.trailing_stop import TrailingStop

ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class WatchedPosition:
    """An open position of a flow whose stop follows the price, as the platform watches it between the cycles (R5.5.1,
    ADR sorveglianza-del-prezzo-per-lo-stop-che-segue): the opening it belongs to, the best price it reached and the
    largest unrealized profit that gives, in the currency of the account (ADR
    massimo-profitto-raggiunto-nello-stato-della-posizione).

    A move of the stop the exchange refused waits here, as the cycle records it, until the next cycle tells it.
    """

    asset: str
    opened_at: datetime | None
    best_price: Decimal
    max_profit: Decimal
    refusal: str | None = None

    @classmethod
    def seen(  # noqa: PLR0913, PLR0917 - the position as the exchange shows it now
        cls,
        previous: WatchedPosition | None,
        asset: str,
        opened_at: datetime | None,
        side: TradeSide,
        entry_price: Decimal,
        size: Decimal,
        price: Decimal,
    ) -> WatchedPosition:
        """The position after a price: a position watched before keeps its best price; one never watched, or opened
        again since, counts from this price.
        """
        same = previous if previous is not None and previous.opened_at == opened_at else None
        best = TrailingStop.best_price(side, None if same is None else same.best_price, price)
        gained = (best - entry_price) * size if side is TradeSide.LONG else (entry_price - best) * size
        return cls(asset, opened_at, best, max(gained, ZERO), None if same is None else same.refusal)

    def moved(self, refusal: str | None) -> WatchedPosition:
        """After a move of the stop: the refusal of the exchange, or none when it went through."""
        return replace(self, refusal=refusal)

    def told(self) -> WatchedPosition:
        """After the cycle that recorded the refusal."""
        return replace(self, refusal=None)

    def note(self) -> TrailingStopNote | None:
        """The refusal waiting for the next cycle, as that cycle records it; None when no move was refused."""
        return None if self.refusal is None else TrailingStopNote(self.asset, self.refusal)


@dataclass(frozen=True, slots=True)
class TrailingStopNote:
    """A move of the stop that follows the price the exchange refused between the cycles, as the next cycle records it
    beside the notes of the protections (R5.5.1, ADR sorveglianza-del-prezzo-per-lo-stop-che-segue)."""

    asset: str
    text: str
