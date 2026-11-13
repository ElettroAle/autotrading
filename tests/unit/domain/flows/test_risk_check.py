from decimal import Decimal

import pytest

from autotrading.domain.flows.risk_check import AssetLimits, RiskCheck, RiskPolicy, RiskState
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.risk_outcome import (
    Adjustment,
    AdjustmentKind,
    ApprovedClose,
    ApprovedOpening,
    BlockedDecision,
    HeldPosition,
)
from autotrading.domain.flows.trade_intent import CloseIntent, HoldIntent, OpenIntent, TradeSide

EXCHANGE = AssetLimits(max_leverage=50, min_order_value=Decimal(10))


def check(
    *,
    max_leverage: int = 50,
    margin: str | None = "100",
    value: str | None = None,
    liquidity: str = "1000",
    funds: str = "1000",
    open_assets: frozenset[str] = frozenset(),
    bring_to_minimum: bool = False,
) -> RiskCheck:
    limits = RiskLimits(
        max_leverage, None if margin is None else Decimal(margin), None if value is None else Decimal(value)
    )
    state = RiskState("USDC", Decimal(funds), Decimal(liquidity), open_assets)
    return RiskCheck(RiskPolicy(limits, bring_to_minimum), state)


def opening(fraction: str, leverage: int, asset: str = "BTC", side: TradeSide = TradeSide.LONG) -> OpenIntent:
    return OpenIntent(asset, side, Decimal(fraction), leverage)


def approved(outcome: object) -> ApprovedOpening:
    assert isinstance(outcome, ApprovedOpening), outcome
    return outcome


def test_an_opening_within_every_limit_passes_unchanged() -> None:
    outcome = approved(check().outcome(opening("0.03", 2, side=TradeSide.SHORT), EXCHANGE))

    assert outcome == ApprovedOpening("BTC", TradeSide.SHORT, Decimal(60), 2, ())
    assert outcome.margin == Decimal(30)


def test_a_leverage_above_the_flow_maximum_is_reduced_keeping_the_margin() -> None:
    outcome = approved(check(max_leverage=5).outcome(opening("0.05", 10), EXCHANGE))

    assert (outcome.margin, outcome.leverage) == (Decimal(50), 5)
    assert outcome.adjustments == (
        Adjustment(AdjustmentKind.LEVERAGE, Decimal(10), Decimal(5), "leva oltre il massimo del flusso: 5"),
    )


def test_the_flow_maximum_applies_before_the_exchange_maximum() -> None:
    outcome = approved(check(max_leverage=50).outcome(opening("0.01", 60), AssetLimits(40, Decimal(10))))

    assert outcome.leverage == 40
    assert [(item.before, item.after) for item in outcome.adjustments] == [
        (Decimal(60), Decimal(50)),
        (Decimal(50), Decimal(40)),
    ]
    assert outcome.adjustments[1].reason == "leva oltre il massimo dell'exchange per BTC: 40"


def test_a_leverage_equal_to_the_maxima_is_kept() -> None:
    assert approved(check(max_leverage=40).outcome(opening("0.01", 40), AssetLimits(40, Decimal(10)))).adjustments == ()


def test_the_margin_limit_reduces_the_margin() -> None:
    outcome = approved(check(margin="5").outcome(opening("0.2", 2), EXCHANGE))

    assert (outcome.margin, outcome.value) == (Decimal(50), Decimal(100))
    assert outcome.adjustments == (
        Adjustment(AdjustmentKind.MARGIN, Decimal(200), Decimal(50), "esposizione del margine oltre il 5%"),
    )


def test_the_value_limit_reduces_the_value() -> None:
    outcome = approved(check(margin=None, value="10").outcome(opening("0.1", 3), EXCHANGE))

    assert outcome.value == Decimal(100)
    assert outcome.adjustments == (
        Adjustment(AdjustmentKind.VALUE, Decimal(300), Decimal(100), "esposizione del valore oltre il 10%"),
    )


@pytest.mark.parametrize(
    ("margin", "value", "fraction", "leverage", "expected", "kind"),
    [
        ("5", "8", "0.05", 4, Decimal(80), AdjustmentKind.VALUE),
        ("5", "80", "0.1", 4, Decimal(200), AdjustmentKind.MARGIN),
    ],
)
def test_with_both_limits_the_smaller_position_wins(
    *, margin: str, value: str, fraction: str, leverage: int, expected: Decimal, kind: AdjustmentKind
) -> None:
    outcome = approved(check(margin=margin, value=value).outcome(opening(fraction, leverage), EXCHANGE))

    assert outcome.value == expected
    assert [item.kind for item in outcome.adjustments] == [kind]


def test_a_value_exactly_at_the_limit_is_not_reduced() -> None:
    assert approved(check(margin=None, value="10").outcome(opening("0.05", 2), EXCHANGE)).adjustments == ()


def test_a_decimal_percent_is_written_with_a_comma() -> None:
    outcome = approved(check(margin=None, value="0.5").outcome(opening("0.006", 2), AssetLimits(50, Decimal(1))))

    assert outcome.adjustments[0].reason == "esposizione del valore oltre il 0,5%"


def test_an_opening_on_an_asset_with_an_open_position_is_blocked() -> None:
    outcome = check(open_assets=frozenset({"BTC"})).outcome(opening("0.01", 1), EXCHANGE)

    assert outcome == BlockedDecision("BTC", "posizione già aperta su BTC")


def test_a_margin_above_the_available_liquidity_is_blocked() -> None:
    outcome = check(liquidity="40").outcome(opening("0.05", 1, "ETH"), EXCHANGE)

    assert outcome == BlockedDecision("ETH", "liquidità del flusso insufficiente: 40 USDC")


def test_a_margin_equal_to_the_liquidity_passes() -> None:
    assert approved(check(liquidity="50").outcome(opening("0.05", 1), EXCHANGE)).margin == Decimal(50)


def test_the_liquidity_is_compared_after_the_reductions() -> None:
    outcome = approved(check(margin="4", liquidity="40").outcome(opening("0.5", 1), EXCHANGE))

    assert outcome.margin == Decimal(40)


def test_a_value_under_the_exchange_minimum_is_blocked_by_default() -> None:
    outcome = check().outcome(opening("0.006", 1), EXCHANGE)

    assert outcome == BlockedDecision("BTC", "valore sotto il minimo dell'exchange per BTC: 10 USDC")


def test_a_value_equal_to_the_minimum_passes() -> None:
    assert approved(check().outcome(opening("0.01", 1), EXCHANGE)).value == Decimal(10)


def test_bring_to_minimum_raises_the_value_to_the_minimum() -> None:
    outcome = approved(check(bring_to_minimum=True).outcome(opening("0.003", 2), EXCHANGE))

    assert (outcome.value, outcome.margin, outcome.leverage) == (Decimal(10), Decimal(5), 2)
    assert outcome.adjustments == (
        Adjustment(AdjustmentKind.VALUE, Decimal(6), Decimal(10), "portata al minimo dell'exchange"),
    )


def test_bring_to_minimum_beyond_the_exposure_limit_is_blocked() -> None:
    outcome = check(margin=None, value="0.5", bring_to_minimum=True).outcome(opening("0.006", 1), EXCHANGE)

    assert outcome == BlockedDecision("BTC", "minimo dell'exchange oltre il limite di esposizione")


def test_bring_to_minimum_at_exactly_the_exposure_limit_passes() -> None:
    outcome = check(margin=None, value="1", bring_to_minimum=True).outcome(opening("0.006", 1), EXCHANGE)

    assert approved(outcome).value == Decimal(10)


def test_bring_to_minimum_beyond_the_liquidity_is_blocked() -> None:
    outcome = check(liquidity="8", bring_to_minimum=True).outcome(opening("0.006", 1), EXCHANGE)

    assert outcome == BlockedDecision("BTC", "liquidità del flusso insufficiente: 8 USDC")


def test_a_close_of_an_open_position_is_approved() -> None:
    assert check(open_assets=frozenset({"ETH"})).outcome(CloseIntent("ETH"), None) == ApprovedClose("ETH")


def test_a_close_without_an_open_position_is_blocked() -> None:
    assert check().outcome(CloseIntent("ETH"), None) == BlockedDecision("ETH", "nessuna posizione aperta su ETH")


def test_a_hold_stays_a_hold() -> None:
    assert check().outcome(HoldIntent("SOL"), None) == HeldPosition("SOL")


def test_an_approved_opening_commits_the_liquidity_for_the_next_decisions() -> None:
    risk = check(liquidity="100")

    first = approved(risk.outcome(opening("0.06", 1, asset="BTC"), EXCHANGE))
    second = risk.outcome(opening("0.06", 1, asset="ETH"), EXCHANGE)

    assert first.margin == Decimal(60)
    assert second == BlockedDecision("ETH", "liquidità del flusso insufficiente: 40 USDC")


def test_the_remaining_liquidity_still_admits_an_opening_that_fits() -> None:
    risk = check(liquidity="100")

    risk.outcome(opening("0.06", 1, asset="BTC"), EXCHANGE)

    assert approved(risk.outcome(opening("0.04", 2, asset="ETH"), EXCHANGE)).margin == Decimal(40)


def test_an_opening_brought_to_the_minimum_commits_its_margin() -> None:
    risk = check(liquidity="15", bring_to_minimum=True)

    approved(risk.outcome(opening("0.006", 1, asset="BTC"), EXCHANGE))

    assert risk.outcome(opening("0.006", 1, asset="ETH"), EXCHANGE) == BlockedDecision(
        "ETH", "liquidità del flusso insufficiente: 5 USDC"
    )


def test_a_blocked_opening_commits_nothing() -> None:
    risk = check(liquidity="50")

    risk.outcome(opening("0.06", 1, asset="BTC"), EXCHANGE)

    assert approved(risk.outcome(opening("0.05", 1, asset="ETH"), EXCHANGE)).margin == Decimal(50)


def test_a_close_in_the_same_cycle_frees_no_liquidity() -> None:
    risk = check(liquidity="40", open_assets=frozenset({"BTC"}))

    risk.outcome(CloseIntent("BTC"), None)

    assert risk.outcome(opening("0.05", 1, asset="ETH"), EXCHANGE) == BlockedDecision(
        "ETH", "liquidità del flusso insufficiente: 40 USDC"
    )


def test_an_opening_with_leverage_commits_its_margin_not_its_value() -> None:
    risk = check(liquidity="100")

    risk.outcome(opening("0.03", 2, asset="BTC"), EXCHANGE)

    assert approved(risk.outcome(opening("0.07", 1, asset="ETH"), EXCHANGE)).margin == Decimal(70)


def test_an_opening_raised_to_the_minimum_is_compared_with_the_liquidity_left() -> None:
    risk = check(liquidity="18", bring_to_minimum=True)

    risk.outcome(opening("0.01", 1, asset="BTC"), EXCHANGE)

    assert risk.outcome(opening("0.006", 1, asset="ETH"), EXCHANGE) == BlockedDecision(
        "ETH", "liquidità del flusso insufficiente: 8 USDC"
    )


def test_the_quota_is_a_fraction_of_the_money_of_the_flow() -> None:
    outcome = approved(check(funds="600", liquidity="400").outcome(opening("0.4", 1), EXCHANGE))

    assert outcome.margin == Decimal(240)


def test_the_margin_exposure_limit_is_a_percent_of_the_money_of_the_flow() -> None:
    outcome = approved(check(margin="50", funds="600", liquidity="400").outcome(opening("0.6", 1), EXCHANGE))

    assert outcome.margin == Decimal(300)
    assert outcome.adjustments == (
        Adjustment(AdjustmentKind.MARGIN, Decimal(360), Decimal(300), "esposizione del margine oltre il 50%"),
    )


def test_the_value_exposure_limit_is_a_percent_of_the_money_of_the_flow() -> None:
    outcome = approved(
        check(margin=None, value="50", funds="1200", liquidity="800").outcome(opening("0.5", 2), EXCHANGE)
    )

    assert outcome.value == Decimal(600)


def test_a_flow_without_money_left_opens_nothing() -> None:
    outcome = check(funds="0", liquidity="0").outcome(opening("0.4", 1), EXCHANGE)

    assert isinstance(outcome, BlockedDecision)
