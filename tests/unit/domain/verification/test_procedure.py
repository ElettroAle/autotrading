from decimal import Decimal

import pytest

from autotrading.domain.verification.errors import (
    InsufficientMarginError,
    PositionAlreadyOpenError,
    VerificationNotStartedError,
)
from autotrading.domain.verification.procedure import (
    PROCEDURE_OPENING,
    REQUIRED_MARGIN,
    Opening,
    Step,
    missing_opening,
    remaining_position,
    require_startable,
)
from autotrading.domain.verification.reading import PositionReading
from tests.support.verification import LONG_BTC, SHORT_ETH, a_reading


def test_the_procedure_always_opens_long_btc_with_leverage_2_for_12_usdc() -> None:
    assert Opening(coin="BTC", side="long", leverage=2, value=Decimal(12)) == PROCEDURE_OPENING
    assert Decimal(12) == REQUIRED_MARGIN


def test_the_steps_run_in_their_order() -> None:
    assert [step.value for step in Step] == [
        "apertura long BTC leva 2",
        "lettura dopo apertura",
        "chiusura",
        "lettura dopo chiusura",
    ]


@pytest.mark.parametrize(
    ("step", "short_name"),
    [
        (Step.OPENING, "apertura"),
        (Step.READING_AFTER_OPENING, "lettura dopo apertura"),
        (Step.CLOSING, "chiusura"),
        (Step.READING_AFTER_CLOSING, "lettura dopo chiusura"),
    ],
)
def test_the_outcome_names_each_step_without_its_details(step: Step, short_name: str) -> None:
    assert step.short_name == short_name


@pytest.mark.parametrize("margin", [Decimal(12), Decimal("12.01"), Decimal(1000)])
def test_an_account_without_btc_and_with_enough_margin_starts(margin: Decimal) -> None:
    require_startable(a_reading(SHORT_ETH, margin=margin))


@pytest.mark.parametrize("held", [LONG_BTC, PositionReading("BTC", "short", Decimal("0.1"), 5)])
def test_any_position_on_btc_stops_the_procedure_before_it_starts(held: PositionReading) -> None:
    with pytest.raises(PositionAlreadyOpenError) as raised:
        require_startable(a_reading(held))

    assert str(raised.value) == "posizione già aperta su BTC"
    assert isinstance(raised.value, VerificationNotStartedError)


@pytest.mark.parametrize("margin", [Decimal("11.99"), Decimal(5), Decimal(0)])
def test_less_than_12_usdc_of_margin_stops_the_procedure_before_it_starts(margin: Decimal) -> None:
    with pytest.raises(InsufficientMarginError) as raised:
        require_startable(a_reading(margin=margin))

    assert raised.value.reason == "margine insufficiente: servono almeno 12 USDC"


def test_the_open_position_is_said_before_the_missing_margin() -> None:
    with pytest.raises(PositionAlreadyOpenError):
        require_startable(a_reading(LONG_BTC, margin=Decimal(5)))


def test_the_reading_after_the_opening_holds_long_btc_with_leverage_2() -> None:
    assert missing_opening(a_reading(LONG_BTC, SHORT_ETH)) is None


@pytest.mark.parametrize(
    "positions",
    [
        (),
        (PositionReading("BTC", "short", Decimal("0.00012"), 2),),
        (PositionReading("BTC", "long", Decimal("0.00012"), 3),),
        (SHORT_ETH,),
    ],
    ids=["nothing", "short", "other-leverage", "other-asset"],
)
def test_a_reading_after_the_opening_without_the_opened_position_says_so(
    positions: tuple[PositionReading, ...],
) -> None:
    assert missing_opening(a_reading(*positions)) == "nessuna posizione long su BTC con leva 2 letta"


def test_the_reading_after_the_closing_holds_nothing_on_btc() -> None:
    assert remaining_position(a_reading(SHORT_ETH)) is None


def test_a_reading_after_the_closing_still_holding_btc_says_so() -> None:
    assert remaining_position(a_reading(LONG_BTC)) == "posizione su BTC ancora aperta"
