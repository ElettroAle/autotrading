from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Connection, Engine, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from autotrading.adapters.outbound.sqlalchemy.tables import flow_exit_plans
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.flows.exit_plan import ExitPlan
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.tenancy.tenant_id import TenantId

KEY = ("flow_id", "asset")


class SqlAlchemyExitPlanRepositoryAdapter:
    """The exit plan in force of each open position of the flows of one tenant, under row level security (R3.1.1)."""

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def current(self, flow_id: FlowId, asset: str) -> ExitPlan | None:
        query = select(flow_exit_plans).where(
            flow_exit_plans.c.flow_id == flow_id.value, flow_exit_plans.c.asset == asset
        )
        with self._transaction() as connection:
            row = connection.execute(query).mappings().one_or_none()
        if row is None:
            return None
        return ExitPlan(row["target_price"], row["stop_price"], row["invalidation"])

    def save(self, flow_id: FlowId, asset: str, plan: ExitPlan) -> None:
        levels = {"target_price": plan.target, "stop_price": plan.stop, "invalidation": plan.invalidation}
        statement = (
            insert(flow_exit_plans)
            .values(flow_id=flow_id.value, asset=asset, tenant_id=self._tenant_id.value, **levels)
            .on_conflict_do_update(index_elements=KEY, set_=levels)
        )
        try:
            with self._transaction() as connection:
                connection.execute(statement)
        except IntegrityError as error:
            # The key (flow_id, tenant_id) of the flow admits only a flow of the tenant of the adapter.
            raise CrossTenantAccessError from error

    def remove(self, flow_id: FlowId, asset: str) -> None:
        statement = delete(flow_exit_plans).where(
            flow_exit_plans.c.flow_id == flow_id.value, flow_exit_plans.c.asset == asset
        )
        with self._transaction() as connection:
            connection.execute(statement)

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection
