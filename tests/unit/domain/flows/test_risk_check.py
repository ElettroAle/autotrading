from datetime import UTC, datetime
from decimal import Decimal

import pytest

from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.exit_plan import ExitPlan, ExitPlanChange
from autotrading.domain.flows.minimum_confidence import MinimumConfidence
from autotrading.domain.flows.openings_suspension import MAXIMUM_LOSS_BLOCK
from autotrading.domain.flows.reopening_block import ReopeningBlock
from autotrading.domain.flows.risk_check import AssetLimits, RiskCheck, RiskPolicy, RiskState
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.risk_outcome import (
    Adjustment,
    AdjustmentKind,
    ApprovedClose,
    ApprovedOpening,
    ApprovedUpdate,
    BlockedDecision,
    HeldPosition,
)
from autotrading.domain.flows.trade_intent import CloseIntent, HoldIntent, OpenIntent, ReverseIntent, UpdateIntent
from autotrading.domain.flows.trade_side import TradeSide

EXCHANGE = AssetLimits(max_leverage=50, min_order_value=Decimal(10), market_price=Decimal(60000))


def check(
    *,
    max_leverage: int = 50,
    margin: str | None = "100",
    value: str | None = None,
    liquidity: str = "1000",
    funds: str = "1000",
    open_assets: frozenset[str] = frozenset(),
    open_sides: dict[str, TradeSide] | None = None,
    bring_to_minimum: bool = False,
    total_margin: str | None = None,
    total_value: str | None = None,
    open_margin: str = "0",
    open_value: str = "0",
    openings_suspended: str | None = None,
    minimum_confidence: int | None = None,
    reopening_blocks: tuple[ReopeningBlock, ...] = (),
) -> RiskCheck:
    open_sides = open_sides or {}
    limits = RiskLimits(
        max_leverage,
        None if margin is None else Decimal(margin),
        None if value is None else Decimal(value),
        None if total_margin is None else Decimal(total_margin),
        None if total_value is None else Decimal(total_value),
    )
    state = RiskState(
        "USDC",
        Decimal(funds),
        Decimal(liquidity),
        {asset: open_sides.get(asset, TradeSide.LONG) for asset in open_assets | open_sides.keys()},
        Decimal(open_margin),
        Decimal(open_value),
        openings_suspended=openings_suspended,
        reopening_blocks=reopening_blocks,
    )
    return RiskCheck(RiskPolicy(limits, bring_to_minimum, MinimumConfidence.optional(minimum_confidence)), state)


def opening(  # noqa: PLR0917 - one argument per field of the intent
    fraction: str,
    leverage: int,
    asset: str = "BTC",
    side: TradeSide = TradeSide.LONG,
    plan: ExitPlan | None = None,
    confidence: int = 70,
) -> OpenIntent:
    return OpenIntent(asset, side, Decimal(fraction), leverage, confidence, plan or ExitPlan())


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
    outcome = approved(
        check(max_leverage=50).outcome(opening("0.01", 60), AssetLimits(40, Decimal(10), Decimal(60000)))
    )

    assert outcome.leverage == 40
    assert [(item.before, item.after) for item in outcome.adjustments] == [
        (Decimal(60), Decimal(50)),
        (Decimal(50), Decimal(40)),
    ]
    assert outcome.adjustments[1].reason == "leva oltre il massimo dell'exchange per BTC: 40"


def test_a_leverage_equal_to_the_maxima_is_kept() -> None:
    assert (
        approved(
            check(max_leverage=40).outcome(opening("0.01", 40), AssetLimits(40, Decimal(10), Decimal(60000)))
        ).adjustments
        == ()
    )


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
    outcome = approved(
        check(margin=None, value="0.5").outcome(opening("0.006", 2), AssetLimits(50, Decimal(1), Decimal(60000)))
    )

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


# ADR-esposizione-complessiva-nel-controllo-del-rischio: the overall limits come after the limit per operation and
# the openings of one cycle consume the residual in their order.


def test_an_opening_beyond_the_overall_margin_is_reduced_to_the_residual() -> None:
    outcome = approved(check(total_margin="30", open_margin="200").outcome(opening("0.15", 1), EXCHANGE))

    assert (outcome.margin, outcome.value) == (Decimal(100), Decimal(100))
    assert outcome.adjustments == (
        Adjustment(
            AdjustmentKind.TOTAL_MARGIN, Decimal(150), Decimal(100), "esposizione complessiva del margine al 30%"
        ),
    )


def test_the_overall_margin_residual_keeps_the_leverage_of_the_opening() -> None:
    outcome = approved(check(total_margin="30", open_margin="200").outcome(opening("0.15", 3), EXCHANGE))

    assert (outcome.margin, outcome.value, outcome.leverage) == (Decimal(100), Decimal(300), 3)


def test_an_opening_beyond_the_overall_value_is_reduced_to_the_residual() -> None:
    outcome = approved(check(total_value="100", open_value="800").outcome(opening("0.3", 1), EXCHANGE))

    assert outcome.value == Decimal(200)
    assert outcome.adjustments == (
        Adjustment(
            AdjustmentKind.TOTAL_VALUE, Decimal(300), Decimal(200), "esposizione complessiva del valore al 100%"
        ),
    )


def test_with_both_overall_limits_the_smaller_residual_wins() -> None:
    risk = check(total_margin="30", total_value="100", open_margin="200", open_value="400")

    outcome = approved(risk.outcome(opening("0.15", 2), EXCHANGE))

    assert (outcome.margin, outcome.value) == (Decimal(100), Decimal(200))
    assert [item.kind for item in outcome.adjustments] == [AdjustmentKind.TOTAL_MARGIN]


def test_with_both_overall_limits_the_value_can_be_the_smaller_residual() -> None:
    risk = check(total_margin="100", total_value="50", open_margin="100", open_value="400")

    outcome = approved(risk.outcome(opening("0.2", 1), EXCHANGE))

    assert outcome.value == Decimal(100)
    assert [item.kind for item in outcome.adjustments] == [AdjustmentKind.TOTAL_VALUE]


def test_an_exhausted_overall_limit_blocks_the_opening() -> None:
    outcome = check(total_margin="30", open_margin="300").outcome(opening("0.15", 1), EXCHANGE)

    assert outcome == BlockedDecision(
        "BTC", "apertura BTC non eseguita: esposizione complessiva del margine al 30% esaurita"
    )


def test_an_overall_limit_already_exceeded_blocks_the_opening() -> None:
    outcome = check(total_value="0.5", open_value="100").outcome(opening("0.01", 1), EXCHANGE)

    assert outcome == BlockedDecision(
        "BTC", "apertura BTC non eseguita: esposizione complessiva del valore al 0,5% esaurita"
    )


def test_an_opening_within_the_overall_limits_passes_unchanged() -> None:
    outcome = approved(check(total_margin="30", open_margin="100").outcome(opening("0.15", 1), EXCHANGE))

    assert (outcome.margin, outcome.adjustments) == (Decimal(150), ())


def test_without_overall_limits_the_open_positions_do_not_reduce_an_opening() -> None:
    outcome = approved(check(open_margin="900", open_value="900").outcome(opening("0.15", 1), EXCHANGE))

    assert outcome.margin == Decimal(150)


def test_the_overall_limit_applies_after_the_limit_per_operation() -> None:
    outcome = approved(check(margin="20", total_margin="30", open_margin="150").outcome(opening("0.3", 1), EXCHANGE))

    assert [(item.kind, item.before, item.after) for item in outcome.adjustments] == [
        (AdjustmentKind.MARGIN, Decimal(300), Decimal(200)),
        (AdjustmentKind.TOTAL_MARGIN, Decimal(200), Decimal(150)),
    ]


def test_the_openings_of_one_cycle_consume_the_overall_residual_in_their_order() -> None:
    risk = check(total_margin="30", total_value="50")

    first = approved(risk.outcome(opening("0.2", 1, asset="BTC"), EXCHANGE))
    second = approved(risk.outcome(opening("0.2", 1, asset="SOL"), EXCHANGE))
    third = risk.outcome(opening("0.2", 1, asset="ETH"), EXCHANGE)

    assert (first.margin, second.margin) == (Decimal(200), Decimal(100))
    assert third == BlockedDecision(
        "ETH", "apertura ETH non eseguita: esposizione complessiva del margine al 30% esaurita"
    )


def test_a_blocked_opening_consumes_no_overall_residual() -> None:
    risk = check(total_margin="30", open_assets=frozenset({"ETH"}))

    risk.outcome(opening("0.2", 1, asset="ETH"), EXCHANGE)

    assert approved(risk.outcome(opening("0.3", 1), EXCHANGE)).margin == Decimal(300)


def test_a_residual_below_the_exchange_minimum_follows_the_rule_of_the_minimum() -> None:
    outcome = check(total_value="100", open_value="995").outcome(opening("0.01", 1), EXCHANGE)

    assert outcome == BlockedDecision("BTC", "valore sotto il minimo dell'exchange per BTC: 10 USDC")


def test_brought_to_the_minimum_an_opening_still_respects_the_overall_residual() -> None:
    risk = check(total_value="100", open_value="995", bring_to_minimum=True)

    outcome = risk.outcome(opening("0.01", 1), EXCHANGE)

    assert outcome == BlockedDecision("BTC", "minimo dell'exchange oltre il limite di esposizione")


def test_brought_to_the_minimum_within_the_overall_residual_an_opening_passes() -> None:
    risk = check(total_value="100", open_value="985", bring_to_minimum=True)

    outcome = approved(risk.outcome(opening("0.005", 1), EXCHANGE))

    assert outcome.value == Decimal(10)


def test_openings_suspended_for_maximum_loss_block_every_opening() -> None:
    outcome = check(openings_suspended=MAXIMUM_LOSS_BLOCK).outcome(opening("0.01", 2), EXCHANGE)

    assert outcome == BlockedDecision("BTC", "apertura BTC non eseguita: aperture sospese per perdita massima")


def test_openings_suspended_for_maximum_loss_still_let_closings_and_holds_through() -> None:
    suspended = check(openings_suspended=MAXIMUM_LOSS_BLOCK, open_assets=frozenset({"BTC"}))

    assert suspended.outcome(CloseIntent("BTC"), None) == ApprovedClose("BTC")
    assert suspended.outcome(HoldIntent("ETH"), None) == HeldPosition("ETH")


def test_openings_are_not_suspended_unless_the_state_says_so() -> None:
    state = RiskState("USDC", Decimal(1000), Decimal(1000), {}, Decimal(0), Decimal(0))

    assert not state.openings_suspended


def test_an_approved_opening_keeps_an_exit_plan_coherent_with_its_side() -> None:
    plan = ExitPlan(Decimal(63000), Decimal(58500), "chiusura a 4 ore sotto 59000")

    outcome = approved(check().outcome(opening("0.03", 2, plan=plan), EXCHANGE))

    assert (outcome.exit_plan, outcome.adjustments) == (plan, ())


def test_a_level_incoherent_with_the_market_price_of_the_exchange_is_discarded_and_recorded() -> None:
    plan = ExitPlan(Decimal(63000), Decimal(61000), None)

    outcome = approved(check().outcome(opening("0.03", 2, plan=plan), EXCHANGE))

    assert outcome.exit_plan == ExitPlan(target=Decimal(63000))
    assert outcome.adjustments == (
        Adjustment(
            AdjustmentKind.EXIT_PLAN,
            Decimal(61000),
            None,
            "stop 61000 scartato: incoerente con long al prezzo 60000",
        ),
    )


def test_the_exit_plan_is_checked_on_a_short_too() -> None:
    plan = ExitPlan(target=Decimal(61000))

    outcome = approved(check().outcome(opening("0.03", 2, side=TradeSide.SHORT, plan=plan), EXCHANGE))

    assert outcome.exit_plan == ExitPlan()
    assert [item.reason for item in outcome.adjustments] == [
        "obiettivo 61000 scartato: incoerente con short al prezzo 60000"
    ]


def test_an_opening_brought_to_the_minimum_keeps_its_exit_plan_checked() -> None:
    plan = ExitPlan(Decimal(59000), Decimal(58000), None)

    outcome = approved(check(bring_to_minimum=True).outcome(opening("0.003", 2, plan=plan), EXCHANGE))

    assert outcome.exit_plan == ExitPlan(stop=Decimal(58000))
    assert [item.kind for item in outcome.adjustments] == [AdjustmentKind.VALUE, AdjustmentKind.EXIT_PLAN]


def test_an_update_of_an_open_position_is_approved_with_its_change() -> None:
    change = ExitPlanChange(Decimal(68000), Decimal(59000), "chiusura sotto 61000")

    outcome = check(open_assets=frozenset({"BTC"})).outcome(UpdateIntent("BTC", change), EXCHANGE)

    assert outcome == ApprovedUpdate("BTC", change, ())


def test_an_update_without_an_open_position_is_blocked() -> None:
    outcome = check().outcome(UpdateIntent("ETH", ExitPlanChange(stop=Decimal(3000))), None)

    assert outcome == BlockedDecision("ETH", "nessuna posizione aperta su ETH")


def test_an_update_on_an_asset_the_exchange_does_not_trade_is_blocked() -> None:
    outcome = check(open_assets=frozenset({"BTC"})).outcome(UpdateIntent("BTC", ExitPlanChange()), None)

    assert outcome == BlockedDecision("BTC", "asset non negoziabile sull'exchange: BTC")


def test_an_update_discards_the_levels_incoherent_with_the_side_of_the_position() -> None:
    risk = RiskCheck(
        RiskPolicy(RiskLimits(50, Decimal(100))),
        RiskState("USDC", Decimal(1000), Decimal(1000), {"BTC": TradeSide.SHORT}),
    )
    change = ExitPlanChange(Decimal(61000), Decimal(62000))

    outcome = risk.outcome(UpdateIntent("BTC", change), EXCHANGE)

    reason = "obiettivo 61000 scartato: incoerente con short al prezzo 60000"
    assert outcome == ApprovedUpdate(
        "BTC",
        ExitPlanChange(None, Decimal(62000)),
        (Adjustment(AdjustmentKind.EXIT_PLAN, Decimal(61000), None, reason),),
    )


def test_an_update_commits_no_liquidity() -> None:
    risk = check(liquidity="60", open_assets=frozenset({"BTC"}))

    risk.outcome(UpdateIntent("BTC", ExitPlanChange(stop=Decimal(59000))), EXCHANGE)

    assert approved(risk.outcome(opening("0.06", 1, asset="ETH"), EXCHANGE)).margin == Decimal(60)


def test_an_opening_below_the_minimum_confidence_is_blocked_with_the_reason() -> None:
    outcome = check(minimum_confidence=60).outcome(opening("0.01", 2, confidence=40), EXCHANGE)

    assert outcome == BlockedDecision("BTC", "apertura BTC non eseguita: confidenza 40 sotto la minima 60")


@pytest.mark.parametrize("confidence", [60, 95])
def test_an_opening_at_or_above_the_minimum_confidence_passes(confidence: int) -> None:
    outcome = check(minimum_confidence=60).outcome(opening("0.01", 2, confidence=confidence), EXCHANGE)

    assert isinstance(outcome, ApprovedOpening)


def test_without_a_minimum_confidence_any_confidence_opens() -> None:
    assert isinstance(check().outcome(opening("0.01", 2, confidence=0), EXCHANGE), ApprovedOpening)


def test_a_weak_opening_commits_no_liquidity() -> None:
    risk_check = check(minimum_confidence=60, liquidity="20")

    risk_check.outcome(opening("0.01", 2, confidence=10), EXCHANGE)

    assert isinstance(risk_check.outcome(opening("0.02", 1, "ETH"), EXCHANGE), ApprovedOpening)


def test_closes_and_updates_ignore_the_minimum_confidence() -> None:
    risk_check = check(minimum_confidence=100, open_assets=frozenset({"BTC", "ETH"}))
    update = UpdateIntent("ETH", ExitPlanChange(stop=Decimal(59000)))

    assert risk_check.outcome(CloseIntent("BTC"), None) == ApprovedClose("BTC")
    assert isinstance(risk_check.outcome(update, EXCHANGE), ApprovedUpdate)


SUSPENDED = "allarme di riconciliazione sul conto test-1"


def suspended_check(open_assets: frozenset[str] = frozenset()) -> RiskCheck:
    limits = RiskLimits(50, Decimal(100))
    positions = {asset: TradeSide.LONG for asset in open_assets}
    state = RiskState("USDC", Decimal(1000), Decimal(1000), positions, openings_suspended=SUSPENDED)
    return RiskCheck(RiskPolicy(limits), state)


def test_with_the_openings_suspended_an_opening_is_blocked_with_the_reason() -> None:
    assert suspended_check().outcome(opening("0.03", 2, asset="ETH"), EXCHANGE) == BlockedDecision(
        "ETH", f"apertura ETH non eseguita: {SUSPENDED}"
    )


def test_with_the_openings_suspended_a_close_is_still_approved() -> None:
    assert suspended_check(frozenset({"BTC"})).outcome(CloseIntent("BTC"), None) == ApprovedClose("BTC")


def test_with_the_openings_suspended_a_hold_stays_a_hold() -> None:
    assert suspended_check().outcome(HoldIntent("SOL"), None) == HeldPosition("SOL")


def test_the_openings_are_not_suspended_unless_the_state_says_so() -> None:
    assert check().outcome(opening("0.03", 2), EXCHANGE) == ApprovedOpening("BTC", TradeSide.LONG, Decimal(60), 2, ())


def reversal(asset: str = "BTC") -> ReverseIntent:
    return ReverseIntent(asset, Decimal("0.2"), 3, 70, ExitPlan(Decimal(70000), Decimal(50000), None))


def test_a_reversal_closes_the_position_and_waits_to_open_the_opposite_side() -> None:
    outcome = check(open_sides={"BTC": TradeSide.SHORT}).outcome(reversal(), None)

    assert outcome == ApprovedClose(
        "BTC", OpenIntent("BTC", TradeSide.LONG, Decimal("0.2"), 3, 70, ExitPlan(Decimal(70000), Decimal(50000), None))
    )
    assert isinstance(outcome, ApprovedClose)
    assert outcome.reason is CloseReason.REVERSAL


def test_a_reversal_without_a_position_of_the_flow_is_blocked() -> None:
    assert check().outcome(reversal("ETH"), None) == BlockedDecision("ETH", "nessuna posizione da invertire")


def test_the_close_of_a_reversal_goes_while_openings_are_suspended() -> None:
    outcome = check(open_sides={"BTC": TradeSide.LONG}, openings_suspended="perdita").outcome(reversal(), None)

    assert isinstance(outcome, ApprovedClose)
    assert outcome.reopening is not None
    assert outcome.reopening.side is TradeSide.SHORT


def test_the_close_of_a_reversal_frees_no_liquidity_before_it_is_executed() -> None:
    risk = check(open_sides={"BTC": TradeSide.LONG}, liquidity="50", margin="100")
    risk.outcome(reversal(), None)

    assert risk.outcome(opening("0.06", 1, "ETH"), EXCHANGE) == BlockedDecision(
        "ETH", "liquidità del flusso insufficiente: 50 USDC"
    )


def test_a_close_decided_by_the_agent_has_its_reason() -> None:
    assert ApprovedClose("BTC").reason is CloseReason.AGENT


def trailing(side: TradeSide = TradeSide.LONG, stop: int = 61740) -> RiskCheck:
    """A position whose stop follows the price, with the stop the platform computes for it (R5.5.1)."""
    state = RiskState("USDC", Decimal(1000), Decimal(1000), {"BTC": side}, trailing_stops={"BTC": Decimal(stop)})
    return RiskCheck(RiskPolicy(RiskLimits(50, Decimal(100))), state)


def test_a_stop_of_the_agent_farther_than_the_one_that_follows_the_price_goes_back_to_it() -> None:
    # R5.5.1, ADR sorveglianza-del-prezzo-per-lo-stop-che-segue.
    market = AssetLimits(max_leverage=50, min_order_value=Decimal(10), market_price=Decimal(63000))

    outcome = trailing().outcome(UpdateIntent("BTC", ExitPlanChange(stop=Decimal(58000))), market)

    reason = "stop 58000 riportato a 61740: oltre lo stop che segue il prezzo"
    assert outcome == ApprovedUpdate(
        "BTC",
        ExitPlanChange(stop=Decimal(61740)),
        (Adjustment(AdjustmentKind.EXIT_PLAN, Decimal(58000), Decimal(61740), reason),),
    )


def test_a_stop_of_the_agent_closer_than_the_one_that_follows_the_price_stands() -> None:
    market = AssetLimits(max_leverage=50, min_order_value=Decimal(10), market_price=Decimal(63000))
    change = ExitPlanChange(stop=Decimal(62000))

    assert trailing().outcome(UpdateIntent("BTC", change), market) == ApprovedUpdate("BTC", change, ())


def test_the_stop_of_a_short_goes_back_below_when_the_agent_puts_it_higher() -> None:
    market = AssetLimits(max_leverage=50, min_order_value=Decimal(10), market_price=Decimal(57000))

    outcome = trailing(TradeSide.SHORT, 58140).outcome(UpdateIntent("BTC", ExitPlanChange(stop=Decimal(59000))), market)

    assert isinstance(outcome, ApprovedUpdate)
    assert outcome.plan_change.stop == Decimal(58140)


def test_an_update_without_a_stop_is_left_as_it_is_by_the_stop_that_follows_the_price() -> None:
    market = AssetLimits(max_leverage=50, min_order_value=Decimal(10), market_price=Decimal(63000))
    change = ExitPlanChange(target=Decimal(66000))

    assert trailing().outcome(UpdateIntent("BTC", change), market) == ApprovedUpdate("BTC", change, ())


# R5.5.2, ADR controllo-delle-riaperture-dopo-perdite-consecutive.
SHORTS_ON_NEAR = ReopeningBlock(TradeSide.SHORT, "NEAR", 2, datetime(2026, 11, 26, 15, 30, tzinfo=UTC))
SHORTS_IN_THE_FLOW = ReopeningBlock(TradeSide.SHORT, None, 2, datetime(2026, 11, 26, 15, 30, tzinfo=UTC))


def test_an_opening_on_a_side_blocked_after_consecutive_losses_is_blocked_with_the_reason_of_the_block() -> None:
    blocked = check(reopening_blocks=(SHORTS_ON_NEAR,))

    outcome = blocked.outcome(opening("0.01", 2, "NEAR", TradeSide.SHORT), EXCHANGE)

    assert outcome == BlockedDecision("NEAR", SHORTS_ON_NEAR.opening_reason("NEAR"))


def test_a_block_after_consecutive_losses_leaves_the_other_side_and_the_other_assets_alone() -> None:
    blocked = check(reopening_blocks=(SHORTS_ON_NEAR,))

    approved(blocked.outcome(opening("0.01", 2, "NEAR", TradeSide.LONG), EXCHANGE))
    approved(blocked.outcome(opening("0.01", 2, "SUI", TradeSide.SHORT), EXCHANGE))


def test_a_block_of_the_flow_blocks_its_side_on_every_asset() -> None:
    blocked = check(reopening_blocks=(SHORTS_IN_THE_FLOW,))

    outcome = blocked.outcome(opening("0.01", 2, "SUI", TradeSide.SHORT), EXCHANGE)

    assert outcome == BlockedDecision("SUI", SHORTS_IN_THE_FLOW.opening_reason("SUI"))


def test_a_block_after_consecutive_losses_lets_the_close_of_a_reversal_through() -> None:
    blocked = check(reopening_blocks=(SHORTS_ON_NEAR,), open_sides={"NEAR": TradeSide.LONG})

    outcome = blocked.outcome(ReverseIntent("NEAR", Decimal("0.01"), 2, 70, ExitPlan()), EXCHANGE)

    assert isinstance(outcome, ApprovedClose)
    assert outcome.reopening is not None
    assert outcome.reopening.side is TradeSide.SHORT


def test_the_suspension_of_the_openings_comes_before_a_block_after_consecutive_losses() -> None:
    both = check(openings_suspended=MAXIMUM_LOSS_BLOCK, reopening_blocks=(SHORTS_ON_NEAR,))

    outcome = both.outcome(opening("0.01", 2, "NEAR", TradeSide.SHORT), EXCHANGE)

    assert outcome == BlockedDecision.opening("NEAR", MAXIMUM_LOSS_BLOCK)


def test_an_opening_without_the_limits_of_the_exchange_is_held() -> None:
    assert check().outcome(opening("0.01", 2), None) == HeldPosition("BTC")
