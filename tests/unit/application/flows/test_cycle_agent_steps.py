"""The context, the decisions of the agent and the risk check of a cycle, on the flow alone (R1.4.3-R1.5.4)."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.application.flows.check_risk import CheckRiskUseCase
from autotrading.application.flows.compose_cycle_context import ComposeCycleContextUseCase
from autotrading.application.flows.decide_cycle import DecideCycleUseCase
from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.application.flows.ports import CycleContext, CycleDecisions, FlowSnapshot, SourceReading
from autotrading.application.flows.review_cycle_risk import ReviewCycleRiskUseCase
from autotrading.domain.flows.cycle_account import CycleAccount
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_question import CycleQuestion
from autotrading.domain.flows.cycle_record import AbsentSource
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.risk_outcome import ApprovedOpening, BlockedDecision
from autotrading.domain.flows.source_data import SourceData
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.exchange_limits import FakeExchangeLimitsAdapter
from tests.support.flows import a_configuration, a_flow

READ_AT = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
NOW = READ_AT + timedelta(seconds=3)
TENANT = TenantId.new()
FLOW = a_flow(TENANT, configuration=replace(a_configuration(), assets=("BTC", "ETH")))
STATE = FlowState(FLOW.id, "USDC", Decimal(500), (), Decimal(0), Decimal(0), Decimal(0))
CYCLE_FLOW = CycleFlow(TENANT, FLOW, "test-1", "Hyperliquid", READ_AT, CycleAccount("USDC", Decimal(500), ()), STATE)
SNAPSHOT = FlowSnapshot(("news",), CYCLE_FLOW)


class Clock:
    def now(self) -> datetime:
        return NOW


@dataclass(frozen=True, slots=True)
class Prompt:
    question: CycleQuestion

    def messages(self) -> tuple[()]:
        return ()


class Composer:
    def execute(self, question: CycleQuestion) -> Prompt:
        return Prompt(question)


@dataclass(frozen=True, slots=True)
class Decision:
    action: str
    asset: str

    def intent_with[O, C, H](
        self, opening: Callable[[str, str, Decimal, int], O], closing: Callable[[str], C], holding: Callable[[str], H]
    ) -> O | C | H:
        if self.action == "open":
            return opening(self.asset, "long", Decimal("0.1"), 2)
        if self.action == "close":
            return closing(self.asset)
        return holding(self.asset)


def Opening(asset: str) -> Decision:  # noqa: N802 - reads as the decision it builds
    return Decision("open", asset)


def Closing(asset: str) -> Decision:  # noqa: N802 - reads as the decision it builds
    return Decision("close", asset)


@dataclass(frozen=True, slots=True)
class Response:
    decisions: tuple[Decision, ...]
    raw: str = "{}"
    discarded: tuple[object, ...] = ()
    missing: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Usage:
    input_tokens: int = 1
    output_tokens: int = 1


@dataclass(frozen=True, slots=True)
class Reply:
    response: Response
    usage: Usage = Usage()
    cost_usd: Decimal | None = None


class Agent:
    def __init__(self) -> None:
        self.questions: list[CycleQuestion] = []

    def execute(self, question: CycleQuestion) -> Reply:
        self.questions.append(question)
        return Reply(Response((Closing("BTC"),)))


def a_context() -> CycleContext:
    readings = [SourceReading("news", (SourceData("news", 2, None, {"titolo": "t"}),))]
    return ComposeCycleContextUseCase(Composer(), Clock()).execute(
        FLOW.id.value, SNAPSHOT, readings, [AbsentSource("pivots", "fonte non disponibile")]
    )


def test_the_question_of_the_cycle_carries_the_flow_alone_its_sources_and_the_missing_declared() -> None:
    configuration = FLOW.configuration

    assert a_context().question == CycleQuestion(
        model=configuration.model.name,
        settings=configuration.model.parameters,
        instructions=configuration.instructions,
        assets=configuration.assets,
        max_leverage=configuration.risk_limits.max_leverage,
        started_at=CYCLE_FLOW.started_at,
        now=NOW,
        state=CYCLE_FLOW.state_view(),
        sources=(SourceData("news", 2, None, {"titolo": "t"}),),
        missing=("pivots: fonte non disponibile",),
    )


def test_the_context_keeps_the_flow_and_what_the_composer_made_of_the_question() -> None:
    context = a_context()

    assert context.flow == CYCLE_FLOW
    assert context.prompt == Prompt(context.question)


def test_the_agent_answers_the_question_of_the_cycle_for_the_flow() -> None:
    agent = Agent()
    context = a_context()

    decisions = DecideCycleUseCase(agent).execute(FLOW.id.value, context)

    assert agent.questions == [context.question]
    assert decisions == CycleDecisions(CYCLE_FLOW, Reply(Response((Closing("BTC"),))))


def test_the_risk_check_runs_on_the_limits_of_the_exchange_of_the_account() -> None:
    decisions = CycleDecisions(CYCLE_FLOW, Reply(Response((Opening("BTC"), Opening("ETH")))))
    check = CheckRiskUseCase({"Hyperliquid": FakeExchangeLimitsAdapter(frozenset({"BTC"}))})

    review = ReviewCycleRiskUseCase(check).execute(FLOW.id.value, SNAPSHOT, decisions)

    assert [order.flow for order in review.orders] == [CYCLE_FLOW]
    outcomes = review.outcomes
    assert isinstance(outcomes, tuple)
    assert [type(outcome) for outcome in outcomes] == [ApprovedOpening, BlockedDecision]
    assert review.orders[0].outcome == outcomes[0]


def test_the_exchange_of_an_account_without_limits_is_unavailable() -> None:
    decisions = CycleDecisions(replace(CYCLE_FLOW, exchange="Altro"), Reply(Response((Closing("BTC"),))))
    check = CheckRiskUseCase({"Hyperliquid": FakeExchangeLimitsAdapter()})

    with pytest.raises(FlowExchangeUnavailableError):
        ReviewCycleRiskUseCase(check).execute(FLOW.id.value, SNAPSHOT, decisions)
