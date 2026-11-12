from uuid import UUID

from sqlalchemy import Engine, func, select

from autotrading.domain.flows.flow_id import FlowId


def flow_lock_key(flow_id: UUID) -> int:
    """The advisory lock a cycle of the flow holds: the first 8 bytes of its id, the signed bigint PostgreSQL takes."""
    return int.from_bytes(flow_id.bytes[:8], "big", signed=True)


class SqlAlchemyRunningCycleAdapter:
    """Waits for the cycle of a flow that the worker runs, through the advisory lock it holds (ADR 0052).

    Session and transaction advisory locks share one space: the lock is taken here only to know the cycle is over.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def wait_until_finished(self, flow_id: FlowId) -> None:
        key = flow_lock_key(flow_id.value)
        with self._engine.connect() as connection:
            connection.execute(select(func.pg_advisory_lock(key)))
            connection.execute(select(func.pg_advisory_unlock(key)))
