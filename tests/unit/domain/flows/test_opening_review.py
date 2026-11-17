from decimal import Decimal

from autotrading.domain.flows.exit_plan import ExitPlanChange
from autotrading.domain.flows.minimum_confidence import MinimumConfidence
from autotrading.domain.flows.opening_review import OpeningReduction, blocked_openings, reduced_openings
from autotrading.domain.flows.risk_outcome import (
    Adjustment,
    AdjustmentKind,
    ApprovedClose,
    ApprovedOpening,
    ApprovedUpdate,
    BlockedDecision,
    HeldPosition,
)
from autotrading.domain.flows.trade_intent import CloseIntent, HoldIntent, OpenIntent, UpdateIntent
from autotrading.domain.flows.trade_side import TradeSide

FUNDS = Decimal(1000)
CAP = Adjustment(AdjustmentKind.MARGIN, Decimal(150), Decimal(100), "esposizione del margine oltre il 10%")


def an_opening(asset: str, fraction: str = "0.15", leverage: int = 3) -> OpenIntent:
    return OpenIntent.of(asset, "long", Decimal(fraction), leverage, 70)


def approved(asset: str, margin: Decimal, leverage: int = 3) -> ApprovedOpening:
    return ApprovedOpening(asset, TradeSide.LONG, margin * leverage, leverage, (CAP,))


def test_an_opening_approved_with_less_margin_than_asked_is_reduced() -> None:
    reductions = reduced_openings((an_opening("BTC"),), (approved("BTC", Decimal(100)),), FUNDS)

    assert reductions == (OpeningReduction("BTC", Decimal(150), Decimal(100)),)


def test_an_opening_approved_with_the_margin_asked_is_not_reduced() -> None:
    assert reduced_openings((an_opening("BTC"),), (approved("BTC", Decimal(150)),), FUNDS) == ()


def test_an_opening_brought_up_to_the_exchange_minimum_is_not_reduced() -> None:
    assert reduced_openings((an_opening("BTC", "0.001"),), (approved("BTC", Decimal(5)),), FUNDS) == ()


def test_an_opening_with_a_lower_leverage_keeps_its_margin_and_is_not_reduced() -> None:
    capped = ApprovedOpening("BTC", TradeSide.LONG, Decimal(750), 5, ())

    assert reduced_openings((an_opening("BTC", leverage=10),), (capped,), FUNDS) == ()


def test_only_the_openings_are_reduced() -> None:
    intents = (CloseIntent("ETH"), HoldIntent("SOL"), an_opening("BTC"))
    outcomes = (ApprovedClose("ETH"), HeldPosition("SOL"), approved("BTC", Decimal(100)))

    assert [reduction.asset for reduction in reduced_openings(intents, outcomes, FUNDS)] == ["BTC"]


def test_the_openings_blocked_are_those_the_risk_check_stopped() -> None:
    blocked = BlockedDecision.below_minimum_confidence("BTC", 40, MinimumConfidence(60))
    intents = (an_opening("BTC"), an_opening("ETH"), CloseIntent("SOL"))
    outcomes = (blocked, approved("ETH", Decimal(150)), BlockedDecision.without_position("SOL"))

    assert blocked_openings(intents, outcomes) == (blocked,)


def test_an_update_blocked_is_not_an_opening_blocked() -> None:
    intents = (UpdateIntent("BTC", ExitPlanChange(stop=Decimal(1))),)
    outcomes = (BlockedDecision.without_position("BTC"),)

    assert blocked_openings(intents, outcomes) == ()
    assert reduced_openings(intents, (ApprovedUpdate("BTC", ExitPlanChange(), ()),), FUNDS) == ()


def test_the_cause_of_a_blocked_opening_is_its_reason_without_the_opening() -> None:
    blocked = BlockedDecision.below_minimum_confidence("BTC", 40, MinimumConfidence(60))

    assert blocked.reason == "apertura BTC non eseguita: confidenza 40 sotto la minima 60"
    assert blocked.cause == "confidenza 40 sotto la minima 60"


def test_the_cause_of_a_decision_blocked_without_naming_the_opening_is_its_reason() -> None:
    assert BlockedDecision("BTC", "posizione già aperta su BTC").cause == "posizione già aperta su BTC"


def test_an_opening_blocked_names_the_opening_before_its_cause() -> None:
    assert BlockedDecision.opening("BTC", "esposizione complessiva esaurita").reason == (
        "apertura BTC non eseguita: esposizione complessiva esaurita"
    )
