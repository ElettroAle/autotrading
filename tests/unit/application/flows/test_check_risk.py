from decimal import Decimal

import pytest

from autotrading.application.flows.check_risk import CheckRiskCommand, CheckRiskUseCase
from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.domain.flows.exit_plan import ExitPlanChange
from autotrading.domain.flows.risk_check import RiskPolicy, RiskState
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.risk_outcome import (
    ApprovedClose,
    ApprovedOpening,
    ApprovedUpdate,
    BlockedDecision,
    HeldPosition,
)
from autotrading.domain.flows.trade_intent import CloseIntent, HoldIntent, OpenIntent, ReverseIntent, UpdateIntent
from autotrading.domain.flows.trade_side import TradeSide
from tests.fakes.exchange_limits import FakeExchangeLimitsAdapter

EXCHANGE = "Hyperliquid"
POLICY = RiskPolicy(RiskLimits(5, Decimal(100)))
STATE = RiskState("USDC", Decimal(1000), Decimal(1000), {"ETH": TradeSide.LONG})


def test_every_decision_gets_its_own_outcome_in_order() -> None:
    exchange = FakeExchangeLimitsAdapter()
    exchange.set("BTC", max_leverage=3)
    intents = (
        CloseIntent("ETH"),
        OpenIntent("BTC", TradeSide.LONG, Decimal("0.1"), 5, 70),
        CloseIntent("SOL"),
        HoldIntent("SOL"),
    )

    outcomes = CheckRiskUseCase({EXCHANGE: exchange}).execute(CheckRiskCommand(intents, POLICY, STATE, EXCHANGE))

    assert outcomes[0] == ApprovedClose("ETH")
    assert isinstance(outcomes[1], ApprovedOpening)
    assert (outcomes[1].margin, outcomes[1].leverage) == (Decimal(100), 3)
    assert outcomes[2] == BlockedDecision("SOL", "nessuna posizione aperta su SOL")
    assert outcomes[3] == HeldPosition("SOL")


def test_an_opening_on_an_asset_the_exchange_does_not_trade_is_blocked() -> None:
    intents = (OpenIntent("DOGE", TradeSide.LONG, Decimal("0.1"), 1, 70),)

    outcomes = CheckRiskUseCase({EXCHANGE: FakeExchangeLimitsAdapter()}).execute(
        CheckRiskCommand(intents, POLICY, STATE, EXCHANGE)
    )

    assert outcomes == (BlockedDecision("DOGE", "asset non negoziabile sull'exchange: DOGE"),)


def test_a_close_or_a_hold_needs_no_limits_of_the_exchange() -> None:
    state = RiskState("USDC", Decimal(1000), Decimal(1000), {"MATIC": TradeSide.SHORT})
    intents = (CloseIntent("MATIC"), HoldIntent("DOGE"))

    outcomes = CheckRiskUseCase({EXCHANGE: FakeExchangeLimitsAdapter()}).execute(
        CheckRiskCommand(intents, POLICY, state, EXCHANGE)
    )

    assert outcomes == (ApprovedClose("MATIC"), HeldPosition("DOGE"))


def test_the_limits_are_those_of_the_exchange_of_the_account() -> None:
    intents = (OpenIntent("BTC", TradeSide.LONG, Decimal("0.1"), 1, 70),)

    with pytest.raises(FlowExchangeUnavailableError):
        CheckRiskUseCase({EXCHANGE: FakeExchangeLimitsAdapter()}).execute(
            CheckRiskCommand(intents, POLICY, STATE, "Altro")
        )


def test_an_update_is_checked_on_the_market_price_of_the_exchange() -> None:
    exchange = FakeExchangeLimitsAdapter()
    exchange.set("ETH", market_price=Decimal(3000))
    intents = (UpdateIntent("ETH", ExitPlanChange(Decimal(2900), Decimal(2800))),)

    outcomes = CheckRiskUseCase({EXCHANGE: exchange}).execute(CheckRiskCommand(intents, POLICY, STATE, EXCHANGE))

    [outcome] = outcomes
    assert isinstance(outcome, ApprovedUpdate)
    assert outcome.plan_change == ExitPlanChange(None, Decimal(2800))
    assert [adjustment.reason for adjustment in outcome.adjustments] == [
        "obiettivo 2900 scartato: incoerente con long al prezzo 3000"
    ]


def test_an_update_without_a_position_is_blocked_even_on_an_asset_the_exchange_does_not_trade() -> None:
    intents = (UpdateIntent("DOGE", ExitPlanChange(stop=Decimal(1))),)

    outcomes = CheckRiskUseCase({EXCHANGE: FakeExchangeLimitsAdapter()}).execute(
        CheckRiskCommand(intents, POLICY, STATE, EXCHANGE)
    )

    assert outcomes == (BlockedDecision("DOGE", "nessuna posizione aperta su DOGE"),)


def test_the_close_of_a_reversal_needs_no_limits_of_the_exchange() -> None:
    state = RiskState("USDC", Decimal(1000), Decimal(1000), {"MATIC": TradeSide.SHORT})
    intents = (ReverseIntent("MATIC", Decimal("0.1"), 2, 70),)

    outcomes = CheckRiskUseCase({EXCHANGE: FakeExchangeLimitsAdapter()}).execute(
        CheckRiskCommand(intents, POLICY, state, EXCHANGE)
    )

    assert outcomes == (ApprovedClose("MATIC", OpenIntent("MATIC", TradeSide.LONG, Decimal("0.1"), 2, 70)),)
