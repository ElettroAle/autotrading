from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import takewhile

from autotrading.domain.flows.closed_position import ClosedPosition
from autotrading.domain.flows.consecutive_loss_limit import ConsecutiveLossLimit
from autotrading.domain.flows.trade_side import TradeSide


@dataclass(frozen=True, slots=True)
class ReopeningBlock:
    """The openings on one side stopped after consecutive losses on it, on one asset or, without an asset, on every
    asset of the flow, until an instant (R5.5.2, ADR controllo-delle-riaperture-dopo-perdite-consecutive).

    Computed from the closings, never saved: it ends on its own and follows every change of the limit.
    """

    side: TradeSide
    asset: str | None
    consecutive_losses: int
    until: datetime

    @classmethod
    def in_force(
        cls, limit: ConsecutiveLossLimit, closed: Iterable[ClosedPosition], at: datetime
    ) -> tuple[ReopeningBlock, ...]:
        """The blocks in force at the instant: on every side, and on every asset with the scope of the asset, the
        closings within the window are counted from the most recent back while their net result is below zero; as many
        losses as the limit block the side for its duration from the most recent of them.
        """
        window = limit.window(at)
        recent = sorted(
            (position for position in closed if window.contains(position.closing.at)),
            key=lambda position: position.closing.at,
            reverse=True,
        )
        counted: dict[tuple[TradeSide, str | None], list[ClosedPosition]] = {}
        for position in recent:
            counted.setdefault((position.side, limit.counted_asset(position.asset)), []).append(position)
        blocks = (cls._after(limit, side, asset, closings) for (side, asset), closings in counted.items())
        in_force = (block for block in blocks if block is not None and block.until > at)
        return tuple(sorted(in_force, key=lambda block: (block.side.value, block.asset or "")))

    @classmethod
    def _after(
        cls, limit: ConsecutiveLossLimit, side: TradeSide, asset: str | None, newest_first: Sequence[ClosedPosition]
    ) -> ReopeningBlock | None:
        # A closing in profit or even breaks the count: only the losses since then are consecutive.
        losses = tuple(takewhile(lambda position: position.net_pnl < 0, newest_first))
        if len(losses) < limit.max_consecutive_losses:
            return None
        return cls(side, asset, len(losses), losses[0].closing.at + limit.block_duration)

    def blocks(self, side: TradeSide, asset: str) -> bool:
        """Whether an opening on the side and the asset is blocked: the other side is never touched."""
        return side is self.side and (self.asset is None or self.asset == asset)

    @property
    def state_text(self) -> str:
        """The block as the state of the flow reports it, to the agent and to the user."""
        return f"{self._stopped_reopenings}: {self._losses_text}"

    def opening_reason(self, asset: str) -> str:
        """Why an opening on the asset is blocked, as the cycle records it."""
        return f"apertura {self.side.value} su {asset} bloccata: {self._losses_text}, {self._stopped_reopenings}"

    @property
    def _stopped_reopenings(self) -> str:
        where = "" if self.asset is None else f" su {self.asset}"
        return f"riaperture {self.side.value}{where} ferme fino alle {self.until.astimezone(UTC):%H:%M}"

    @property
    def _losses_text(self) -> str:
        counted = "perdita consecutiva" if self.consecutive_losses == 1 else "perdite consecutive"
        losses = f"{self.consecutive_losses} {counted}"
        return losses if self.asset is not None else f"{losses} {self.side.value} nel flusso"
