from collections.abc import Sequence

from sqlalchemy import Engine, func, select, update

from autotrading.adapters.outbound.sqlalchemy.tables import flows
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.tenancy.tenant_id import TenantId


class SqlAlchemyAutomaticPauseAdapter:
    """Pauses active flows of the tenant with the reason of the automatic pause (R1.2.4, ADR 0042).

    One statement: a flow the user paused or stopped in the meantime keeps the status the user gave it.
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def pause(self, flow_ids: Sequence[FlowId], reason: str) -> None:
        if not flow_ids:
            return
        statement = (
            update(flows)
            .where(flows.c.id.in_([flow_id.value for flow_id in flow_ids]), flows.c.status == "active")
            .values(status="paused", pause_reason=reason)
        )
        with self._engine.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            connection.execute(statement)
