from decimal import Decimal

import pytest

from autotrading.domain.verification.errors import (
    AmountBelowMinimumError,
    AssetOfFlowError,
    InsufficientMarginError,
    PositionAlreadyOpenError,
    VerificationAmountNotPositiveError,
    VerificationNotStartedError,
)
from autotrading.domain.verification.procedure import (
    Opening,
    Step,
    missing_opening,
    procedure_opening,
    remaining_position,
    require_free_of_flows,
    require_startable,
)
from autotrading.domain.verification.reading import AccountReading, PositionReading
from tests.support.verification import LONG_BTC, SHORT_ETH, a_reading

MINIMUM = Decimal(10)


def an_opening(value: Decimal) -> Opening:
    return Opening(coin="BTC", side="long", leverage=2, value=value)


@pytest.mark.parametrize("chosen", [Decimal(10), Decimal("10.01"), Decimal(20)])
def test_the_procedure_opens_long_btc_with_leverage_2_for_the_chosen_amount(chosen: Decimal) -> None:
    assert procedure_opening(chosen, MINIMUM, "USDC") == an_opening(chosen)


@pytest.mark.parametrize("minimum", [Decimal(10), Decimal("1.5")])
def test_without_an_amount_the_procedure_opens_the_minimum_of_the_exchange(minimum: Decimal) -> None:
    assert procedure_opening(None, minimum, "USDC") == an_opening(minimum)


@pytest.mark.parametrize("chosen", [Decimal("9.99"), Decimal(5)])
def test_an_amount_below_the_minimum_of_the_exchange_stops_the_procedure(chosen: Decimal) -> None:
    with pytest.raises(AmountBelowMinimumError) as raised:
        procedure_opening(chosen, Decimal("10.5"), "USDC")

    assert (raised.value.reason, raised.value.minimum) == (
        "importo sotto il minimo dell'exchange: 10,50 USDC",
        Decimal("10.5"),
    )
    assert isinstance(raised.value, VerificationNotStartedError)


@pytest.mark.parametrize("chosen", [Decimal(0), Decimal(-5)])
def test_an_amount_not_above_zero_is_invalid_whatever_the_minimum(chosen: Decimal) -> None:
    with pytest.raises(VerificationAmountNotPositiveError) as raised:
        procedure_opening(chosen, Decimal(0), "USDC")

    assert (str(raised.value), raised.value.status_code) == (
        "l'importo della procedura deve essere maggiore di zero",
        422,
    )


def test_a_minimum_of_zero_without_an_amount_is_invalid() -> None:
    with pytest.raises(VerificationAmountNotPositiveError):
        procedure_opening(None, Decimal(0), "USDC")


def test_the_margin_the_opening_needs_is_its_value_over_its_leverage() -> None:
    assert an_opening(Decimal(25)).required_margin == Decimal("12.5")


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


@pytest.mark.parametrize("margin", [Decimal(10), Decimal("10.01"), Decimal(1000)])
def test_an_account_without_btc_and_with_the_margin_of_the_opening_starts(margin: Decimal) -> None:
    require_startable(a_reading(SHORT_ETH, margin=margin), an_opening(Decimal(20)))


@pytest.mark.parametrize("held", [LONG_BTC, PositionReading("BTC", "short", Decimal("0.1"), 5)])
def test_any_position_on_btc_stops_the_procedure_before_it_starts(held: PositionReading) -> None:
    with pytest.raises(PositionAlreadyOpenError) as raised:
        require_startable(a_reading(held), an_opening(MINIMUM))

    assert str(raised.value) == "posizione già aperta su BTC"
    assert isinstance(raised.value, VerificationNotStartedError)


@pytest.mark.parametrize("margin", [Decimal("9.99"), Decimal(8), Decimal(0)])
def test_less_margin_than_the_opening_needs_stops_the_procedure_before_it_starts(margin: Decimal) -> None:
    with pytest.raises(InsufficientMarginError) as raised:
        require_startable(a_reading(margin=margin), an_opening(Decimal(20)))

    assert (raised.value.reason, raised.value.required) == (
        "margine disponibile insufficiente: servono 10 USDC",
        Decimal(10),
    )


def test_the_margin_needed_is_said_in_the_currency_of_the_account_with_its_cents() -> None:
    reading = AccountReading(Decimal(100), Decimal(1), "USDT", ())

    with pytest.raises(InsufficientMarginError) as raised:
        require_startable(reading, an_opening(Decimal("10.5")))

    assert raised.value.reason == "margine disponibile insufficiente: servono 5,25 USDT"


def test_the_open_position_is_said_before_the_missing_margin() -> None:
    with pytest.raises(PositionAlreadyOpenError):
        require_startable(a_reading(LONG_BTC, margin=Decimal(5)), an_opening(Decimal(20)))


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


def test_an_account_without_a_flow_on_btc_starts() -> None:
    require_free_of_flows(None)


def test_a_flow_on_btc_stops_the_procedure_before_it_starts_with_its_name() -> None:
    with pytest.raises(AssetOfFlowError) as raised:
        require_free_of_flows("alfa")

    assert (str(raised.value), raised.value.coin, raised.value.flow_name) == (
        "BTC è un asset del flusso alfa",
        "BTC",
        "alfa",
    )
