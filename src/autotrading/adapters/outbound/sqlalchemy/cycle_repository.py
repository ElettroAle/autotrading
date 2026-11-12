import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Connection, Engine, RowMapping, func, select
from sqlalchemy.dialects.postgresql import insert

from autotrading.adapters.outbound.sqlalchemy.tables import cycles
from autotrading.application.cycles.errors import UnrecordableDocumentError
from autotrading.domain.cycles.call_cost import CallCost
from autotrading.domain.cycles.cycle_record import (
    AbsentSource,
    CycleFailure,
    CycleOutcome,
    CycleRecord,
    StepDocument,
)
from autotrading.domain.cycles.cycle_step import CycleStep
from autotrading.domain.cycles.flow_cost import CycleCost
from autotrading.domain.tenancy.tenant_id import TenantId

KEY = ["flow_id", "planned_at"]
RECORDED = cycles.c.outcome.is_not(None)


class SqlAlchemyCycleRepositoryAdapter:
    """The cycles of the flows of one tenant: taken, recorded and read back under row level security (ADR 0046)."""

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def claim(self, flow_id: UUID, planned_at: datetime) -> bool:
        statement = (
            insert(cycles)
            .values(flow_id=flow_id, planned_at=planned_at, tenant_id=self._tenant_id.value)
            .on_conflict_do_nothing(index_elements=KEY)
            # The row comes back only when this insert took it: the row count is not reliable with every driver.
            .returning(cycles.c.flow_id)
        )
        with self._transaction() as connection:
            return connection.execute(statement).first() is not None

    def record(self, record: CycleRecord) -> None:
        row = row_of(record, self._tenant_id)
        statement = insert(cycles).values(row).on_conflict_do_update(index_elements=KEY, set_=row)
        with self._transaction() as connection:
            connection.execute(statement)

    def newest(self, flow_id: UUID, offset: int, limit: int) -> list[CycleRecord]:
        query = (
            select(cycles)
            .where(cycles.c.flow_id == flow_id, RECORDED)
            .order_by(cycles.c.planned_at.desc())
            .offset(offset)
            .limit(limit)
        )
        with self._transaction() as connection:
            return [record_of(row) for row in connection.execute(query).mappings()]

    def at(self, flow_id: UUID, planned_at: datetime) -> CycleRecord | None:
        query = select(cycles).where(cycles.c.flow_id == flow_id, cycles.c.planned_at == planned_at, RECORDED)
        with self._transaction() as connection:
            row = connection.execute(query).mappings().first()
        return None if row is None else record_of(row)

    def costs(self, flow_id: UUID) -> list[CycleCost]:
        query = (
            select(cycles.c.planned_at, cycles.c.input_tokens, cycles.c.output_tokens, cycles.c.cost_usd)
            .where(cycles.c.flow_id == flow_id, cycles.c.input_tokens.is_not(None))
            .order_by(cycles.c.planned_at)
        )
        with self._transaction() as connection:
            return [
                CycleCost(row["planned_at"], CallCost(row["input_tokens"], row["output_tokens"], row["cost_usd"]))
                for row in connection.execute(query).mappings()
            ]

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


def row_of(record: CycleRecord, tenant_id: TenantId) -> dict[str, object]:
    cost = record.cost
    return {
        "flow_id": record.flow_id,
        "planned_at": record.planned_at,
        "tenant_id": tenant_id.value,
        "outcome": record.outcome.name.lower(),
        "started_at": record.started_at,
        "delay_seconds": record.delay_seconds,
        "steps": [step.name.lower() for step in record.steps],
        "absent_sources": [{"source": item.source, "reason": item.reason} for item in record.absent_sources],
        "failure": _failure_row(record.failure),
        "documents": [
            {"step": document.step.name.lower(), "content": plain(document.content)} for document in record.documents
        ],
        "input_tokens": None if cost is None else cost.input_tokens,
        "output_tokens": None if cost is None else cost.output_tokens,
        "cost_usd": None if cost is None else cost.cost_usd,
    }


def record_of(row: RowMapping | Mapping[str, Any]) -> CycleRecord:
    return CycleRecord(
        flow_id=row["flow_id"],
        planned_at=row["planned_at"],
        outcome=CycleOutcome[row["outcome"].upper()],
        started_at=row["started_at"],
        delay_seconds=row["delay_seconds"],
        steps=tuple(_step(name) for name in row["steps"] or ()),
        absent_sources=tuple(AbsentSource(item["source"], item["reason"]) for item in row["absent_sources"] or ()),
        failure=_failure_of(row["failure"]),
        documents=tuple(
            StepDocument(_step(document["step"]), document["content"]) for document in row["documents"] or ()
        ),
        cost=_cost_of(row),
    )


def plain(content: Mapping[str, object]) -> Any:
    """The document as plain JSON: amounts as text, so no number is rounded, and instants in ISO 8601."""
    return json.loads(json.dumps(content, default=_plain_value))


def _plain_value(value: object) -> str:
    if isinstance(value, Decimal | UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    # A type the journal should never put in a document: failing here keeps it out of the record.
    raise UnrecordableDocumentError(type(value).__name__)


def _failure_row(failure: CycleFailure | None) -> dict[str, str] | None:
    if failure is None:
        return None
    return {"step": failure.step.name.lower(), "error_type": failure.error_type, "message": failure.message}


def _failure_of(failure: Mapping[str, str] | None) -> CycleFailure | None:
    if failure is None:
        return None
    return CycleFailure(_step(failure["step"]), failure["error_type"], failure["message"])


def _cost_of(row: RowMapping | Mapping[str, Any]) -> CallCost | None:
    if row["input_tokens"] is None:
        return None
    return CallCost(row["input_tokens"], row["output_tokens"], row["cost_usd"])


def _step(name: str) -> CycleStep:
    return CycleStep[name.upper()]
