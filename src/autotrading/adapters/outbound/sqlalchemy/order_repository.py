from sqlalchemy import Engine, func, insert, select

from autotrading.adapters.outbound.sqlalchemy.tables import orders
from autotrading.domain.orders.order import Order
from autotrading.domain.tenancy.tenant_id import TenantId


class SqlAlchemyOrderRepositoryAdapter:
    """Bound to the tenant of the request: every transaction declares it, and row level security does the rest."""

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def add(self, order: Order) -> None:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            connection.execute(insert(orders).values(_row_of(order, self._tenant_id)))


def _row_of(order: Order, tenant_id: TenantId) -> dict[str, object]:
    request, market_order = order.request, order.request.market_order
    execution, rejection, link = order.execution, order.rejection, order.request.source.flow
    return {
        "id": order.id.value,
        "tenant_id": tenant_id.value,
        "account_id": request.account_id,
        "origin": request.source.origin.name,
        "user_id": request.source.user_id,
        "coin": market_order.coin,
        "direction": market_order.direction.value,
        "reduce_only": market_order.reduce_only,
        "leverage": request.leverage,
        "requested_size": market_order.size,
        "slippage": market_order.slippage.fraction,
        "status": order.status.name,
        "filled_size": None if execution is None else execution.filled_size,
        "average_price": None if execution is None else execution.average_price,
        "fee": None if execution is None else execution.fee,
        "realized_pnl": None if execution is None else execution.realized_pnl,
        "executed_at": None if execution is None else execution.executed_at,
        "rejection_reason": None if rejection is None else rejection.reason.name,
        "exchange_message": None if rejection is None else rejection.exchange_message,
        "flow_id": None if link is None else link.flow_id,
        "cycle_planned_at": None if link is None else link.cycle_planned_at,
        "decision_asset": None if link is None else link.decision_asset,
    }
