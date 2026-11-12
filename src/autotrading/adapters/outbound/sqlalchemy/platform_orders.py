from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import Engine, func, select

from autotrading.adapters.outbound.sqlalchemy.tables import orders
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import PlatformOrders
from autotrading.domain.tenancy.tenant_id import TenantId


class SqlAlchemyPlatformOrdersAdapter:
    """The client order ids of the orders the platform recorded on an account, with their flow (ADR 0044, ADR 0063).

    The orders of the verification procedure and of the manual commands have no flow (ADR 0050).
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def orders_among(self, account_id: UUID, order_ids: Iterable[UUID]) -> PlatformOrders:
        wanted = list(order_ids)
        if not wanted:
            return {}
        query = select(orders.c.id, orders.c.flow_id).where(orders.c.account_id == account_id, orders.c.id.in_(wanted))
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            rows = connection.execute(query).all()
        return {order_id: None if flow_id is None else FlowId(flow_id) for order_id, flow_id in rows}
