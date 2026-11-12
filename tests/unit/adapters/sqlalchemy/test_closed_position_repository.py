from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from autotrading.adapters.outbound.sqlalchemy.closed_position_repository import (
    SqlAlchemyClosedPositionRepositoryAdapter,
    position_of,
    row_of,
)
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId

# The engine never connects: these tests stop before the database.
ENGINE = create_engine("postgresql+psycopg://nobody@unreachable.invalid/none")
OPENED = datetime(2026, 11, 12, 10, tzinfo=UTC)
POSITION = ClosedPosition(
    tenant_id=TenantId.new(),
    flow_id=FlowId.new(),
    asset="BTC",
    side=TradeSide.SHORT,
    leverage=2,
    margin=Decimal("50.5"),
    opening=PositionEnd(Decimal(100000), OPENED, OPENED),
    closing=PositionEnd(Decimal(102000), OPENED + timedelta(hours=2), None),
    fees=Decimal("0.08"),
    reason=CloseReason.OUTSIDE_PLATFORM,
)


def test_a_closed_position_is_saved_with_side_and_reason_by_name() -> None:
    assert row_of(POSITION) == {
        "tenant_id": POSITION.tenant_id.value,
        "flow_id": POSITION.flow_id.value,
        "asset": "BTC",
        "side": "short",
        "leverage": 2,
        "margin": Decimal("50.5"),
        "open_price": Decimal(100000),
        "opened_at": OPENED,
        "opening_cycle": OPENED,
        "close_price": Decimal(102000),
        "closed_at": OPENED + timedelta(hours=2),
        "closing_cycle": None,
        "fees": Decimal("0.08"),
        "reason": "outside_platform",
        "realized_pnl": None,
    }


def test_the_pnl_the_exchange_reported_is_saved_and_read_back() -> None:
    position = replace(POSITION, realized_pnl=Decimal("-4.2"))

    assert row_of(position)["realized_pnl"] == Decimal("-4.2")
    assert position_of(row_of(position)) == position


@pytest.mark.parametrize("reason", list(CloseReason))
def test_a_saved_closed_position_reads_back_as_it_was(reason: CloseReason) -> None:
    position = replace(POSITION, reason=reason)

    assert position_of(row_of(position)) == position


def test_a_closed_position_of_another_tenant_is_refused_before_the_database() -> None:
    repository = SqlAlchemyClosedPositionRepositoryAdapter(ENGINE, TenantId.new())

    with pytest.raises(CrossTenantAccessError):
        repository.add(POSITION)
