from uuid import UUID

from sqlalchemy import Engine, func, select

from autotrading.adapters.outbound.sqlalchemy.tables import orders
from autotrading.domain.flows.account_reconciliation import PlatformOrders
from autotrading.domain.tenancy.tenant_id import TenantId


class SqlAlchemyPlatformOrdersAdapter:
    """The client order ids of the orders the platform recorded on an account, bound to the tenant (ADR 0044).

    The orders of E0 come from the verification procedure and from manual commands: none belongs to a flow. The
    flow that sends an order joins its record with the execution of the decisions (R1.5.5).
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def orders_of_account(self, account_id: UUID) -> PlatformOrders:
        query = select(orders.c.id).where(orders.c.account_id == account_id)
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            return dict.fromkeys(connection.execute(query).scalars())
