from sqlalchemy import Engine, func, select

from autotrading.adapters.outbound.sqlalchemy.tables import flows
from autotrading.application.notifications.ports import NotifiedFlow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId

ARCHIVED = FlowStatus.ARCHIVED.name.lower()


class SqlAlchemyNotifiedFlowsAdapter:
    """Bound to the tenant of the request: the flows its notifications name, under row level security."""

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def list(self) -> tuple[NotifiedFlow, ...]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            rows = connection.execute(
                select(flows.c.id, flows.c.name).where(flows.c.status != ARCHIVED).order_by(flows.c.name)
            ).all()
        return tuple(NotifiedFlow(flow_id, name) for flow_id, name in rows)
