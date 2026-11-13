from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from uuid import UUID

import psycopg
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row
from sqlalchemy import Engine

from autotrading.domain.tenancy.tenant_id import TenantId


class SqlAlchemyCycleCheckpointsAdapter:
    """The checkpoints of the cycles of a tenant, kept in PostgreSQL by the checkpointer of LangGraph (ADR 0104).

    The checkpointer talks to PostgreSQL through its own connection, opened for one cycle on the database of the
    engine and closed after it: the tenant set on that connection never reaches the pool of the other adapters.
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def thread(self, flow_id: UUID, planned_at: datetime) -> str:
        # The tenant leads the thread: row level security reads it from there.
        return f"{self._tenant_id.value}/{flow_id}/{planned_at.isoformat()}"

    @contextmanager
    def opened(self) -> Iterator[BaseCheckpointSaver[str]]:
        # The checkpointer runs in autocommit, one transaction per statement: the tenant is set for the session.
        with psycopg.connect(
            self._conninfo(), autocommit=True, prepare_threshold=0, row_factory=dict_row
        ) as connection:
            connection.execute("SELECT set_config('app.tenant_id', %s, false)", (str(self._tenant_id.value),))
            yield PostgresSaver(connection)

    def _conninfo(self) -> str:
        return self._engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
