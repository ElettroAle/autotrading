"""The closed positions and the clock the state of a flow reads its blocks of the openings with (R5.5.2)."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from autotrading.application.flows.read_flow_state import ClosingReadings
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.closed_position_repository import ClosedPositionStore, InMemoryClosedPositionRepositoryAdapter

NOW = datetime(2026, 11, 26, 14, 0, tzinfo=UTC)
TENANT = TenantId(UUID("00000000-0000-4000-8000-0000000005e2"))
FLOW = FlowId(UUID("00000000-0000-4000-8000-0000000005f2"))


def closing_readings(
    tenant_id: TenantId, store: ClosedPositionStore | None = None, clock: Callable[[], datetime] = lambda: NOW
) -> ClosingReadings:
    """The closings of the tenant, none unless a store is given, read at the instant of the clock."""
    positions = InMemoryClosedPositionRepositoryAdapter(store or ClosedPositionStore(), tenant_id)
    return ClosingReadings(positions, clock)


def a_closing(
    side: TradeSide,
    asset: str,
    closed_at: datetime,
    net_pnl: Decimal,
    *,
    tenant_id: TenantId = TENANT,
    flow_id: FlowId = FLOW,
) -> ClosedPosition:
    """A position of the flow closed at the instant with the net result given: the exchange reported it, no fees."""
    return ClosedPosition(
        tenant_id=tenant_id,
        flow_id=flow_id,
        asset=asset,
        side=side,
        leverage=2,
        margin=Decimal(10),
        opening=PositionEnd(Decimal(2), closed_at - timedelta(minutes=20)),
        closing=PositionEnd(Decimal(2), closed_at),
        fees=Decimal(0),
        reason=CloseReason.STOP_LOSS,
        realized_pnl=net_pnl,
    )
