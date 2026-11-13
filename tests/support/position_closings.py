"""What closing a position of a flow answers, as the flows context reads it (ADR 0055)."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from autotrading.domain.flows.stop_outcome import ClosingFill


@dataclass(frozen=True, slots=True)
class ClosingAnswer:
    found: bool = True
    refusal: str | None = None
    average_price: Decimal | None = None
    executed_at: datetime | None = None
    fee: Decimal | None = None
    realized_pnl: Decimal | None = None


NOTHING_TO_CLOSE = ClosingAnswer(found=False)


def closed_by(fill: ClosingFill) -> ClosingAnswer:
    return ClosingAnswer(average_price=fill.price, executed_at=fill.at, fee=fill.fee, realized_pnl=fill.realized_pnl)


def refused(reason: str) -> ClosingAnswer:
    return ClosingAnswer(refusal=reason)
