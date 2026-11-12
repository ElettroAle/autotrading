from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

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
    """What the exchange executed to close a position of the flow."""

    price: Decimal
    at: datetime
    fee: Decimal


@dataclass(frozen=True, slots=True)
class PositionClosing:
    """What closing one position of the flow gave: the fill the exchange executed, or the reason it refused."""

    asset: str
    fill: ClosingFill | None = None
    refusal: str | None = None


@dataclass(frozen=True, slots=True)
class PositionOpening:
    """The order of the flow that opened its position on an asset, as the platform recorded it (R1.5.5)."""

    side: TradeSide
    leverage: int
    margin: Decimal
    end: PositionEnd
    fee: Decimal

    def closed(self, flow: Flow, asset: str, fill: ClosingFill, reason: CloseReason) -> ClosedPosition:
        """The position closed by the fill, with the fees of both ends (R1.7.2)."""
        return ClosedPosition(
            tenant_id=flow.tenant_id,
            flow_id=flow.id,
            asset=asset,
            side=self.side,
            leverage=self.leverage,
            margin=self.margin,
            opening=self.end,
            closing=PositionEnd(fill.price, fill.at),
            fees=self.fee + fill.fee,
            reason=reason,
        )


@dataclass(frozen=True, slots=True)
class StopOutcome:
    """The flow stopped, whatever happened to its positions, and those still open on the exchange (R1.1.5)."""

    flow: Flow
    left_open: tuple[PositionLeftOpen, ...]
