from collections.abc import Mapping

from sqlalchemy import Engine, func, select

from autotrading.adapters.outbound.sqlalchemy.tables import flows
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_timing import FlowTiming
from autotrading.domain.tenancy.tenant_id import TenantId


class SqlAlchemyFlowTimingAdapter:
    """The anchor of the cycles, the automatic pause reason and the first start of the flows of one tenant.

    R1.7.3, ADR 0042, ADR 0069.
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def timings(self) -> Mapping[FlowId, FlowTiming]:
        query = select(flows.c.id, flows.c.cycle_anchor, flows.c.pause_reason, flows.c.first_started_at)
        with self._engine.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            rows = connection.execute(query).mappings().all()
        return {
            FlowId(row["id"]): FlowTiming(row["cycle_anchor"], row["pause_reason"], row["first_started_at"])
            for row in rows
        }
