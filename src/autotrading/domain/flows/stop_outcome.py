from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from autotrading.domain.flows.account_reconciliation import OutsideClosing
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.trade_intent import TradeSide


@dataclass(frozen=True, slots=True)
class PositionLeftOpen:
    """A position of the flow the exchange did not close, with the reason it gave (R1.1.5)."""

    asset: str
    reason: str


@dataclass(frozen=True, slots=True)
class ClosingFill:
    """What the exchange executed to close a position of the flow, with the PnL it realized, when it reported it."""

    price: Decimal
    at: datetime
    fee: Decimal
    realized_pnl: Decimal | None = None

    @classmethod
    def reported(
        cls, price: Decimal | None, at: datetime | None, fee: Decimal | None, realized_pnl: Decimal | None
    ) -> ClosingFill | None:
        """The fill of a closing the exchange confirmed in time; none while its price, time or fee is missing."""
        if price is None or at is None or fee is None:
            return None
        return cls(price, at, fee, realized_pnl)


@dataclass(frozen=True, slots=True)
class PositionClosing:
    """What closing one position of the flow gave: the fill the exchange executed, or the reason it refused."""

    asset: str
    fill: ClosingFill | None = None
    refusal: str | None = None

    @classmethod
    def reported(
        cls, asset: str, *, found: bool, fill: ClosingFill | None, refusal: str | None
    ) -> PositionClosing | None:
        """What closing the position gave: nothing without a position, else its fill or, unconfirmed, the reason."""
        if not found:
            return None
        if fill is None:
            return cls(asset, refusal=refusal)
        return cls(asset, fill)


@dataclass(frozen=True, slots=True)
class PositionOpening:
    """The order of the flow that opened its position on an asset, as the platform recorded it (R1.5.5)."""

    side: TradeSide
    leverage: int
    margin: Decimal
    end: PositionEnd
    fee: Decimal

    def closed(
        self, flow: Flow, asset: str, fill: ClosingFill, reason: CloseReason, cycle: datetime | None = None
    ) -> ClosedPosition:
        """The position closed by the fill, with the fees of both ends and the cycle that closed it, if one did."""
        return ClosedPosition(
            tenant_id=flow.tenant_id,
            flow_id=flow.id,
            asset=asset,
            side=self.side,
            leverage=self.leverage,
            margin=self.margin,
            opening=self.end,
            closing=PositionEnd(fill.price, fill.at, cycle),
            fees=self.fee + fill.fee,
            reason=reason,
            realized_pnl=fill.realized_pnl,
        )

    def closed_outside(self, flow: Flow, closing: OutsideClosing) -> ClosedPosition:
        """The position the exchange shows closed without the platform, liquidations included (R1.6.2, R1.7.2).

        The exchange gives the realized PnL, not the price: the closing price is the one that PnL implies on the
        value the margin held with the leverage, so the history shows the result the exchange reported.
        """
        sign = 1 if self.side is TradeSide.LONG else -1
        move = closing.realized_pnl / (self.margin * self.leverage) * sign
        fill = ClosingFill(self.end.price * (1 + move), closing.closed_at, closing.fee, closing.realized_pnl)
        return self.closed(flow, closing.asset, fill, CloseReason.OUTSIDE_PLATFORM)


@dataclass(frozen=True, slots=True)
class StopOutcome:
    """The flow stopped, whatever happened to its positions, and those still open on the exchange (R1.1.5)."""

    flow: Flow
    left_open: tuple[PositionLeftOpen, ...]
