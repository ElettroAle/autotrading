from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.errors import InvalidClosedPositionError
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId

OPENED = datetime(2026, 11, 12, 10, tzinfo=UTC)
POSITION = ClosedPosition(
    tenant_id=TenantId.new(),
    flow_id=FlowId.new(),
    asset="BTC",
    side=TradeSide.LONG,
    leverage=2,
    margin=Decimal(50),
    opening=PositionEnd(Decimal(100000), OPENED, OPENED),
    closing=PositionEnd(Decimal(102000), OPENED + timedelta(hours=2, minutes=30)),
    fees=Decimal("0.08"),
    reason=CloseReason.AGENT,
)


def test_a_long_position_earns_when_the_price_rises() -> None:
    assert POSITION.pnl == Decimal(2)
    assert POSITION.pnl_percent_of_margin == Decimal(4)


def test_a_short_position_earns_when_the_price_falls() -> None:
    position = replace(POSITION, side=TradeSide.SHORT, closing=PositionEnd(Decimal(98000), OPENED))

    assert position.pnl == Decimal(2)


def test_a_short_position_loses_when_the_price_rises() -> None:
    position = replace(POSITION, side=TradeSide.SHORT)

    assert position.pnl == Decimal(-2)
    assert position.pnl_percent_of_margin == Decimal(-4)


def test_the_leverage_multiplies_the_result_on_the_margin() -> None:
    position = replace(POSITION, leverage=5)

    assert position.pnl == Decimal(5)
    assert position.pnl_percent_of_margin == Decimal(10)


def test_the_duration_runs_from_opening_to_closing() -> None:
    assert POSITION.duration == timedelta(hours=2, minutes=30)


def test_a_position_closed_in_the_instant_it_opened_lasts_nothing() -> None:
    assert replace(POSITION, closing=PositionEnd(Decimal(100000), OPENED)).duration == timedelta(0)


def test_the_ends_keep_the_cycles_that_produced_them() -> None:
    assert (POSITION.opening.cycle, POSITION.closing.cycle) == (OPENED, None)


def test_the_reasons_of_e1_speak_italian() -> None:
    assert [reason.value for reason in CloseReason] == [
        "decisione dell'agente",
        "comando manuale",
        "stop del flusso",
        "rimozione del conto",
        "chiusa fuori dalla piattaforma",
    ]


@pytest.mark.parametrize(
    "position",
    [
        lambda: replace(POSITION, leverage=0),
        lambda: replace(POSITION, margin=Decimal(0)),
        lambda: replace(POSITION, fees=Decimal("-0.01")),
        lambda: replace(POSITION, opening=PositionEnd(Decimal(0), OPENED)),
        lambda: replace(POSITION, closing=PositionEnd(Decimal(0), OPENED)),
        lambda: replace(POSITION, opening=PositionEnd(Decimal(1), OPENED.replace(tzinfo=None))),
        lambda: replace(POSITION, closing=PositionEnd(Decimal(1), OPENED.replace(tzinfo=None))),
        lambda: replace(POSITION, closing=PositionEnd(Decimal(1), OPENED - timedelta(seconds=1))),
    ],
)
def test_a_position_the_exchange_cannot_show_is_a_defect(position: object) -> None:
    assert callable(position)
    with pytest.raises(InvalidClosedPositionError) as raised:
        position()

    assert raised.value.status_code == 500
    assert str(raised.value) == "posizione chiusa non valida"


def test_fees_and_leverage_at_their_limits_are_admitted() -> None:
    position = replace(POSITION, leverage=1, fees=Decimal(0))

    assert (position.leverage, position.fees) == (1, Decimal(0))
