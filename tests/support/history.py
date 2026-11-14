"""Rows of the histories of R2.5.1, as the tests of the use cases and of the API build them."""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.history import (
    ClosedPositionHistoryEntry,
    CycleHistoryEntry,
    OrderExecution,
    OrderHistoryEntry,
)
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_history import HistoryRow

ACCOUNT = UUID("00000000-0000-4000-8000-0000000000a1")
FLOW = UUID("00000000-0000-4000-8000-0000000000f1")
TENANT = TenantId(UUID("00000000-0000-4000-8000-0000000000e1"))


def a_cycle_row(
    planned_at: datetime, *, version: int = 1, assets: frozenset[str] = frozenset({"BTC"}), flow_id: UUID = FLOW
) -> HistoryRow[CycleHistoryEntry]:
    entry = CycleHistoryEntry("alfa", version, CycleRecord(flow_id, planned_at, CycleOutcome.COMPLETED, planned_at))
    return HistoryRow(entry, ACCOUNT, flow_id, planned_at, assets, version)


def a_closed_position(closed_at: datetime, asset: str = "ETH") -> ClosedPosition:
    return ClosedPosition(
        tenant_id=TENANT,
        flow_id=FlowId(FLOW),
        asset=asset,
        side=TradeSide.LONG,
        leverage=2,
        margin=Decimal(100),
        opening=PositionEnd(Decimal(3000), closed_at - timedelta(hours=2)),
        closing=PositionEnd(Decimal(3150), closed_at),
        fees=Decimal("0.42"),
        reason=CloseReason.AGENT,
    )


def a_position_row(
    closed_at: datetime, *, asset: str = "ETH", version: int = 1
) -> HistoryRow[ClosedPositionHistoryEntry]:
    entry = ClosedPositionHistoryEntry(uuid4(), "alfa", a_closed_position(closed_at, asset))
    return HistoryRow(entry, ACCOUNT, FLOW, closed_at, frozenset({asset}), version)


def an_order(created_at: datetime, *, asset: str = "BTC", flow_id: UUID | None = FLOW) -> OrderHistoryEntry:
    return OrderHistoryEntry(
        order_id=uuid4(),
        created_at=created_at,
        account_id=ACCOUNT,
        account_name="principale",
        flow_id=flow_id,
        flow_name=None if flow_id is None else "alfa",
        asset=asset,
        direction="long",
        closing=False,
        leverage=3,
        requested_size=Decimal("0.02"),
        status="eseguito",
        origin="flusso",
        executions=(
            OrderExecution(created_at + timedelta(seconds=1), Decimal("91000.5"), Decimal("0.015"), Decimal("0.41")),
            OrderExecution(created_at + timedelta(seconds=2), Decimal("91001"), Decimal("0.005"), Decimal("0.14")),
        ),
    )


def an_order_row(
    created_at: datetime, *, asset: str = "BTC", account_id: UUID = ACCOUNT, version: int = 1
) -> HistoryRow[OrderHistoryEntry]:
    return HistoryRow(an_order(created_at, asset=asset), account_id, FLOW, created_at, frozenset({asset}), version)
