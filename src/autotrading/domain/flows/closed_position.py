from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from autotrading.domain.flows.errors import InvalidClosedPositionError
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned

PERCENT = Decimal(100)


class CloseReason(StrEnum):
    """Why a position of a flow was closed in E1 (R1.7.2)."""

    AGENT = "decisione dell'agente"
    MANUAL = "comando manuale"
    FLOW_STOP = "stop del flusso"
    ACCOUNT_REMOVAL = "rimozione del conto"
    # Liquidations included: the platform sees the position gone without having closed it.
    OUTSIDE_PLATFORM = "chiusa fuori dalla piattaforma"


@dataclass(frozen=True, slots=True)
class PositionEnd:
    """One end of a position: price and instant, and the cycle that produced it, when a cycle did."""

    price: Decimal
    at: datetime
    cycle: datetime | None = None


@dataclass(frozen=True, slots=True)
class ClosedPosition(TenantOwned):
    """A position of a flow, closed, with its result (R1.7.2)."""

    tenant_id: TenantId
    flow_id: FlowId
    asset: str
    side: TradeSide
    leverage: int
    margin: Decimal
    opening: PositionEnd
    closing: PositionEnd
    fees: Decimal
    reason: CloseReason

    def __post_init__(self) -> None:
        ends = (self.opening, self.closing)
        if self.leverage < 1 or self.margin <= 0 or self.fees < 0:
            raise InvalidClosedPositionError
        if any(end.price <= 0 or end.at.tzinfo is None for end in ends):
            raise InvalidClosedPositionError
        if self.closing.at < self.opening.at:
            raise InvalidClosedPositionError

    @property
    def duration(self) -> timedelta:
        return self.closing.at - self.opening.at

    @property
    def pnl(self) -> Decimal:
        """The result of the price move on the value the margin held with the leverage, before the fees."""
        move = (self.closing.price - self.opening.price) / self.opening.price
        sign = 1 if self.side is TradeSide.LONG else -1
        return self.margin * self.leverage * move * sign

    @property
    def pnl_percent_of_margin(self) -> Decimal:
        return self.pnl / self.margin * PERCENT
