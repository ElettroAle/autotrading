from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from autotrading.domain.orders.order import Order, OrderStatus
from autotrading.domain.orders.rejection import RejectionReason


@dataclass(frozen=True, slots=True)
class OrderOutcome:
    """What a user reads of an order: its status and what the exchange executed or why it refused (R0.3.2, R0.3.3)."""

    order_id: UUID
    status: OrderStatus
    coin: str
    filled_size: Decimal | None = None
    average_price: Decimal | None = None
    fee: Decimal | None = None
    realized_pnl: Decimal | None = None
    executed_at: datetime | None = None
    reason: RejectionReason | None = None
    exchange_message: str | None = None

    @classmethod
    def of(cls, order: Order) -> OrderOutcome:
        execution, rejection = order.execution, order.rejection
        return cls(
            order.id.value,
            order.status,
            order.request.market_order.coin,
            filled_size=None if execution is None else execution.filled_size,
            average_price=None if execution is None else execution.average_price,
            fee=None if execution is None else execution.fee,
            realized_pnl=None if execution is None else execution.realized_pnl,
            executed_at=None if execution is None else execution.executed_at,
            reason=None if rejection is None else rejection.reason,
            exchange_message=None if rejection is None else rejection.exchange_message,
        )
