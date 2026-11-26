from collections.abc import Collection, Iterator
from contextlib import contextmanager

from sqlalchemy import Connection, Engine, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from autotrading.adapters.outbound.sqlalchemy.tables import flow_watched_positions
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.watched_position import WatchedPosition
from autotrading.domain.tenancy.tenant_id import TenantId

KEY = ("flow_id", "asset")
watched = flow_watched_positions.c


class SqlAlchemyWatchedPositionsAdapter:
    """The open positions of the flows of one tenant whose stop follows the price, as the platform watches them, under
    row level security (R5.5.1, ADR sorveglianza-del-prezzo-per-lo-stop-che-segue)."""

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def watched_of(self, flow_id: FlowId) -> tuple[WatchedPosition, ...]:
        query = select(flow_watched_positions).where(watched.flow_id == flow_id.value).order_by(watched.asset)
        with self._transaction() as connection:
            rows = connection.execute(query).mappings().all()
        return tuple(
            WatchedPosition(row["asset"], row["opened_at"], row["best_price"], row["max_profit"], row["refusal"])
            for row in rows
        )

    def save(self, flow_id: FlowId, position: WatchedPosition) -> None:
        values = {
            "opened_at": position.opened_at,
            "best_price": position.best_price,
            "max_profit": position.max_profit,
            "refusal": position.refusal,
        }
        statement = (
            insert(flow_watched_positions)
            .values(flow_id=flow_id.value, asset=position.asset, tenant_id=self._tenant_id.value, **values)
            .on_conflict_do_update(index_elements=KEY, set_=values)
        )
        try:
            with self._transaction() as connection:
                connection.execute(statement)
        except IntegrityError as error:
            # The key (flow_id, tenant_id) of the flow admits only a flow of the tenant of the adapter.
            raise CrossTenantAccessError from error

    def forget(self, flow_id: FlowId, asset: str) -> None:
        statement = delete(flow_watched_positions).where(watched.flow_id == flow_id.value, watched.asset == asset)
        with self._transaction() as connection:
            connection.execute(statement)

    def keep_only(self, flow_ids: Collection[FlowId]) -> None:
        kept = [flow_id.value for flow_id in flow_ids]
        statement = delete(flow_watched_positions).where(watched.flow_id.not_in(kept))
        with self._transaction() as connection:
            connection.execute(statement)

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection
