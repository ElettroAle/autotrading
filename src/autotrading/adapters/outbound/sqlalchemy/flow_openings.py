from sqlalchemy import Engine, func, select

from autotrading.adapters.outbound.sqlalchemy.tables import orders
from autotrading.domain.flows.closed_position import PositionEnd
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.stop_outcome import PositionOpening
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId

EXECUTED = ("FILLED", "PARTIALLY_FILLED")


class SqlAlchemyFlowOpeningsAdapter:
    """The openings of the flows of one tenant, read from the orders the platform recorded (ADR 0055, ADR 0050).

    A flow opens and closes a position whole (R1.4.4): its last executed opening on an asset is the one still open.
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def last_opening(self, flow_id: FlowId, asset: str) -> PositionOpening | None:
        query = (
            select(orders)
            .where(
                orders.c.flow_id == flow_id.value,
                orders.c.coin == asset,
                orders.c.reduce_only.is_(False),
                orders.c.status.in_(EXECUTED),
            )
            .order_by(orders.c.executed_at.desc())
            .limit(1)
        )
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            row = connection.execute(query).mappings().one_or_none()
        if row is None:
            return None
        margin = row["filled_size"] * row["average_price"] / row["leverage"]
        end = PositionEnd(row["average_price"], row["executed_at"], row["cycle_planned_at"])
        return PositionOpening(TradeSide(row["direction"]), row["leverage"], margin, end, row["fee"])
