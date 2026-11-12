import threading
import time
from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, select

from autotrading.adapters.outbound.sqlalchemy.running_cycle import SqlAlchemyRunningCycleAdapter
from autotrading.adapters.outbound.sqlalchemy.scheduling import lock_key
from autotrading.domain.flows.flow_id import FlowId

pytestmark = pytest.mark.integration

HELD_SECONDS = 0.5


def test_without_a_cycle_running_the_wait_returns_at_once(database: Engine) -> None:
    started = time.monotonic()

    SqlAlchemyRunningCycleAdapter(database).wait_until_finished(FlowId(uuid4()))

    assert time.monotonic() - started < HELD_SECONDS


def test_the_wait_lasts_until_the_cycle_releases_the_lock_of_its_flow(database: Engine) -> None:
    flow_id = FlowId(uuid4())
    key = lock_key(flow_id.value)
    held = threading.Event()

    def cycle() -> None:
        with database.connect() as connection:
            connection.execute(select(func.pg_advisory_lock(key)))
            held.set()
            time.sleep(HELD_SECONDS)
            connection.execute(select(func.pg_advisory_unlock(key)))

    worker = threading.Thread(target=cycle)
    worker.start()
    held.wait()
    started = time.monotonic()

    SqlAlchemyRunningCycleAdapter(database).wait_until_finished(flow_id)

    worker.join()
    assert time.monotonic() - started >= HELD_SECONDS * 0.8


def test_the_wait_leaves_the_lock_free_for_the_next_cycle(database: Engine) -> None:
    flow_id = FlowId(uuid4())

    SqlAlchemyRunningCycleAdapter(database).wait_until_finished(flow_id)

    with database.connect() as connection:
        assert connection.execute(select(func.pg_try_advisory_lock(lock_key(flow_id.value)))).scalar_one()
        connection.execute(select(func.pg_advisory_unlock(lock_key(flow_id.value))))
