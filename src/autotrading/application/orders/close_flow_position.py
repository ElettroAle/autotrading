from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from autotrading.application.orders.errors import (
    NoOpenPositionError,
    OrderAccountNotFoundError,
    OrderExchangeUnavailableError,
    OrderWorkerUnavailableError,
)
from autotrading.application.orders.ports import PositionClosingPort
from autotrading.domain.orders.order import OrderStatus
from autotrading.domain.orders.order_outcome import OrderOutcome
from autotrading.domain.tenancy.user_id import UserId


@dataclass(frozen=True, slots=True)
class CloseFlowPositionCommand:
    account_id: UUID
    coin: str
    user_id: UserId


@dataclass(frozen=True, slots=True)
class ClosingReport:
    """What closing a position of a flow gave, as data: a flow stops whatever happens to its positions (R1.1.5)."""

    found: bool
    refusal: str | None = None
    average_price: Decimal | None = None
    executed_at: datetime | None = None
    fee: Decimal | None = None
    realized_pnl: Decimal | None = None


class CloseFlowPositionUseCase:
    """Closes a position of a flow through the worker and reports the outcome instead of raising (ADR 0086)."""

    def __init__(self, closing: PositionClosingPort) -> None:
        self._closing = closing

    def execute(self, command: CloseFlowPositionCommand) -> ClosingReport:
        try:
            outcome = self._closing.close(command.account_id, command.coin, command.user_id)
        except NoOpenPositionError:
            return ClosingReport(found=False)
        except (OrderAccountNotFoundError, OrderExchangeUnavailableError, OrderWorkerUnavailableError) as error:
            return ClosingReport(found=True, refusal=str(error))
        return _report_of(outcome)


def _report_of(outcome: OrderOutcome) -> ClosingReport:
    if outcome.status == OrderStatus.REJECTED:
        return ClosingReport(found=True, refusal=outcome.exchange_message or str(outcome.reason))
    if outcome.average_price is None or outcome.executed_at is None or outcome.fee is None:
        # Not confirmed in time: the position may still be open, so it is reported as such.
        return ClosingReport(found=True, refusal=outcome.status.value)
    return ClosingReport(
        found=True,
        average_price=outcome.average_price,
        executed_at=outcome.executed_at,
        fee=outcome.fee,
        realized_pnl=outcome.realized_pnl,
    )
