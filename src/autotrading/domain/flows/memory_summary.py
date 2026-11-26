from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from autotrading.domain.flows.closed_position import ClosedPosition
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.italian_text import money_text


@dataclass(frozen=True, slots=True)
class ResultCount:
    """How many positions closed, how many of them were won and lost and their result, all after the fees: a position
    even counts only among the closed (R5.3.7).
    """

    closed: int
    won: int
    lost: int
    pnl: Decimal

    @classmethod
    def of(cls, positions: Iterable[ClosedPosition]) -> ResultCount:
        results = [position.net_pnl for position in positions]
        return cls(
            closed=len(results),
            won=sum(1 for result in results if result > 0),
            lost=sum(1 for result in results if result < 0),
            pnl=sum(results, Decimal(0)),
        )

    def text(self, currency: str) -> str:
        # The amount in Italian with its cents, as the requirement writes the line (R5.3.7).
        return f"{self.closed} chiuse, {self.won} vinte, {self.lost} perse, PnL {money_text(self.pnl)} {currency}"


@dataclass(frozen=True, slots=True)
class MemorySummary:
    """The results of the positions of the flow closed within the days of the memory, by asset and side: today, the
    current UTC day of the cycle, and the days of the memory (R5.3.7, ADR
    memoria-del-flusso-con-riepilogo-e-altri-asset).

    The positions are those closed within the days of the memory, which the memory chooses; they count whatever the
    number of decisions the memory holds.
    """

    closed: Sequence[ClosedPosition]
    at: datetime
    days: int
    currency: str

    def lines_of(self, asset: str) -> tuple[str, ...]:
        """A line for every side with positions closed on the asset, long first; none for a side without."""
        on_asset = [position for position in self.closed if position.asset == asset]
        by_side = ((side, [position for position in on_asset if position.side is side]) for side in TradeSide)
        return tuple(self._line(asset, side, closed) for side, closed in by_side if closed)

    @property
    def _today(self) -> date:
        return self.at.astimezone(UTC).date()

    def _line(self, asset: str, side: TradeSide, closed: Sequence[ClosedPosition]) -> str:
        today = ResultCount.of(
            position for position in closed if position.closing.at.astimezone(UTC).date() == self._today
        )
        within = ResultCount.of(closed)
        return (
            f"{asset} {side.value} — oggi: {today.text(self.currency)};"
            f" ultimi {self.days} giorni: {within.text(self.currency)}"
        )
