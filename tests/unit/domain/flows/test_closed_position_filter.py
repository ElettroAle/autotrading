from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.closed_position_filter import ClosedPositionFilter, PositionResult
from autotrading.domain.flows.errors import (
    InvalidClosedPositionFilterError,
    RangeEndingBeforeStartError,
    UnknownPositionResultError,
    UnknownPositionSideError,
)
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId

OPENED = datetime(2026, 11, 12, 9, tzinfo=UTC)


def a_position(
    *,
    asset: str = "BTC",
    side: TradeSide = TradeSide.LONG,
    pnl: Decimal = Decimal(1),
    fees: Decimal = Decimal(0),
    closed_at: datetime = OPENED + timedelta(hours=1),
) -> ClosedPosition:
    return ClosedPosition(
        tenant_id=TenantId.new(),
        flow_id=FlowId.new(),
        asset=asset,
        side=side,
        leverage=1,
        margin=Decimal(100),
        opening=PositionEnd(Decimal(100), OPENED),
        closing=PositionEnd(Decimal(100), closed_at),
        fees=fees,
        reason=CloseReason.AGENT,
        realized_pnl=pnl,
    )


def test_a_filter_without_values_admits_every_position() -> None:
    criteria = ClosedPositionFilter.named()

    assert criteria == ClosedPositionFilter()
    assert criteria.matches(a_position(side=TradeSide.SHORT, pnl=Decimal(-3)))


def test_the_side_admits_only_positions_on_that_side() -> None:
    criteria = ClosedPositionFilter.named(side="short")

    assert criteria.side is TradeSide.SHORT
    assert criteria.matches(a_position(side=TradeSide.SHORT))
    assert not criteria.matches(a_position(side=TradeSide.LONG))


def test_an_unknown_side_is_refused_with_the_choices() -> None:
    with pytest.raises(UnknownPositionSideError) as raised:
        ClosedPositionFilter.named(side="buy")

    assert str(raised.value) == "direzione non valida: scegliere tra long, short"
    assert raised.value.status_code == 400


def test_a_won_position_has_a_positive_result_after_the_fees() -> None:
    criteria = ClosedPositionFilter.named(result="vinta")

    assert criteria.result is PositionResult.WON
    assert criteria.matches(a_position(pnl=Decimal(2), fees=Decimal(1)))
    assert not criteria.matches(a_position(pnl=Decimal(1), fees=Decimal(1)))


def test_a_lost_position_has_a_negative_result_after_the_fees() -> None:
    criteria = ClosedPositionFilter.named(result="persa")

    assert criteria.result is PositionResult.LOST
    assert criteria.matches(a_position(pnl=Decimal("0.5"), fees=Decimal(1)))
    assert not criteria.matches(a_position(pnl=Decimal(1), fees=Decimal(1)))


def test_an_unknown_result_is_refused_with_the_choices() -> None:
    with pytest.raises(UnknownPositionResultError) as raised:
        ClosedPositionFilter.named(result="pari")

    assert str(raised.value) == "risultato non valido: scegliere tra vinta, persa"
    assert isinstance(raised.value, InvalidClosedPositionFilterError)


def test_the_asset_admits_only_positions_on_that_asset() -> None:
    criteria = ClosedPositionFilter.named(asset="ETH")

    assert criteria.matches(a_position(asset="ETH"))
    assert not criteria.matches(a_position(asset="BTC"))


def test_the_days_admit_the_positions_closed_within_them() -> None:
    criteria = ClosedPositionFilter.named(first_day=date(2026, 11, 12), last_day=date(2026, 11, 12))

    assert criteria.window == TimeWindow(datetime(2026, 11, 12, tzinfo=UTC), datetime(2026, 11, 13, tzinfo=UTC))
    assert criteria.matches(a_position(closed_at=datetime(2026, 11, 12, 23, 59, tzinfo=UTC)))
    assert not criteria.matches(a_position(closed_at=datetime(2026, 11, 13, tzinfo=UTC)))


def test_a_last_day_before_the_first_is_refused() -> None:
    with pytest.raises(RangeEndingBeforeStartError):
        ClosedPositionFilter.named(first_day=date(2026, 11, 3), last_day=date(2026, 11, 1))
