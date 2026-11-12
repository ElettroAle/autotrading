from sqlalchemy import Engine, func, select

from autotrading.adapters.outbound.sqlalchemy.scheduling import lock_key
from autotrading.domain.flows.flow_id import FlowId


class SqlAlchemyRunningCycleAdapter:
    """Waits for the cycle of a flow that the worker runs, through the advisory lock it holds (ADR 0052).

    The key is the one the worker holds for the whole cycle (`SqlAlchemyFlowLockAdapter`, ADR 0042): the lock is
    taken here only to know the cycle is over.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def wait_until_finished(self, flow_id: FlowId) -> None:
        key = lock_key(flow_id.value)
        with self._engine.connect() as connection:
            connection.execute(select(func.pg_advisory_lock(key)))
            connection.execute(select(func.pg_advisory_unlock(key)))
