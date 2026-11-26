"""The context, the decisions of the agent and the risk check of a cycle, on the flow alone (R1.4.3-R1.5.4)."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.application.flows.check_risk import CheckRiskUseCase
from autotrading.application.flows.compose_cycle_context import ComposeCycleContextUseCase
from autotrading.application.flows.decide_cycle import DecideCycleUseCase
from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.application.flows.ports import CycleContext, CycleDecisions, FlowSnapshot, SourceReading
from autotrading.application.flows.remembered_decisions import MemoryReadings
from autotrading.application.flows.review_cycle_risk import ReviewCycleRiskUseCase
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.cycle_account import CycleAccount, CyclePosition
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_question import CycleQuestion
from autotrading.domain.flows.cycle_record import AbsentSource, CycleOutcome, CycleRecord
from autotrading.domain.flows.exit_plan import ExitPlan, ExitPlanChange
from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.memory_entry import AssetMemory, MemoryEntry
from autotrading.domain.flows.minimum_confidence import MinimumConfidence
from autotrading.domain.flows.openings_suspension import OpeningsSuspension
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.risk_outcome import ApprovedClose, ApprovedOpening, ApprovedUpdate, BlockedDecision
from autotrading.domain.flows.selections import ActiveSource
from autotrading.domain.flows.source_data import SourceData
from autotrading.domain.flows.trade_intent import OpenIntent
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.closed_position_repository import ClosedPositionStore, InMemoryClosedPositionRepositoryAdapter
from tests.fakes.cycles import InMemoryCycleRepositoryAdapter
from tests.fakes.exchange_limits import FakeExchangeLimitsAdapter
from tests.fakes.opening_blocked_notices import FakeOpeningBlockedNoticeAdapter
from tests.fakes.opening_reduced_notices import FakeOpeningReducedNoticeAdapter
from tests.fakes.order_repository import InMemoryOrderRepositoryAdapter
from tests.fakes.past_decisions import InMemoryPastDecisionsAdapter
from tests.support.flows import a_configuration, a_flow

READ_AT = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
NOW = READ_AT + timedelta(seconds=3)
TENANT = TenantId.new()
FLOW = a_flow(TENANT, configuration=replace(a_configuration(), assets=("BTC", "ETH")))
STATE = FlowState(FLOW.id, "USDC", Decimal(500), (), Decimal(0), Decimal(0), Decimal(0))
CYCLE_FLOW = CycleFlow(
    TENANT, FLOW, "test-1", "Hyperliquid", READ_AT, CycleAccount("USDC", Decimal(500), (), Decimal(500)), STATE
)
SNAPSHOT = FlowSnapshot((ActiveSource("news", "RSS"),), CYCLE_FLOW)


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
class Plan:
    target: Decimal | None = None
    stop: Decimal | None = None
    invalidation: str | None = None


@dataclass(frozen=True, slots=True)
class Change:
    target: Decimal | None = None
    stop: Decimal | None = None
    invalidation: str | None = None
    remove_target: bool = False


@dataclass(frozen=True, slots=True)
class Decision:
    action: str
    asset: str
    plan: Plan = Plan()
    change: Change = Change()
    confidence: int = 70
    reasoning: str = "ragionamento"
    motive: str | None = "motivo"

    def intent_with[O, C, H, U, R](
        self,
        opening: Callable[[str, str, Decimal, int, Plan, int], O],
        closing: Callable[[str], C],
        holding: Callable[[str], H],
        updating: Callable[[str, Change], U],
        reversing: Callable[[str, Decimal, int, Plan, int], R],
    ) -> O | C | H | U | R:
        if self.action == "open":
            return opening(self.asset, "long", Decimal("0.1"), 2, self.plan, self.confidence)
        if self.action == "reverse":
            return reversing(self.asset, Decimal("0.2"), 3, self.plan, self.confidence)
        if self.action == "close":
            return closing(self.asset)
        if self.action == "update":
            return updating(self.asset, self.change)
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
    attempts: int = 1


class Agent:
    def __init__(self) -> None:
        self.questions: list[CycleQuestion] = []

    def execute(self, question: CycleQuestion) -> Reply:
        self.questions.append(question)
        return Reply(Response((Closing("BTC"),)))


class LossGuard:
    """The guard of the losses of the flow, with the answer the test gives, and the flows it guarded."""

    def __init__(self, *, suspended: bool) -> None:
        self.suspended = suspended
        self.guarded: list[CycleFlow] = []

    def execute(self, flow: CycleFlow) -> OpeningsSuspension | None:
        self.guarded.append(flow)
        return OpeningsSuspension("perdita giornaliera 6% oltre il 5%", flow.started_at) if self.suspended else None


def review_of(
    check: CheckRiskUseCase,
    guard: LossGuard | None = None,
    reduced: FakeOpeningReducedNoticeAdapter | None = None,
    blocked: FakeOpeningBlockedNoticeAdapter | None = None,
) -> ReviewCycleRiskUseCase:
    return ReviewCycleRiskUseCase(
        check,
        guard or LossGuard(suspended=False),
        reduced or FakeOpeningReducedNoticeAdapter(),
        blocked or FakeOpeningBlockedNoticeAdapter(),
    )


class Actions:
    def execute(self) -> tuple[str, ...]:
        return ("apri", "chiudi")


@dataclass(frozen=True, slots=True)
class Aggregated:
    source: str
    adapter: str
    asset: str | None
    values: Mapping[str, str]


class Aggregates:
    """The aggregates of the sources, with the answer the test gives, and the data it received."""

    def __init__(self, *answer: Aggregated) -> None:
        self.answer = answer
        self.received: list[tuple[SourceData, ...]] = []

    def execute(self, data: Sequence[SourceData]) -> tuple[Aggregated, ...]:
        self.received.append(tuple(data))
        return self.answer


def no_past_decisions() -> InMemoryPastDecisionsAdapter:
    return InMemoryPastDecisionsAdapter(
        InMemoryCycleRepositoryAdapter(), InMemoryOrderRepositoryAdapter(), ClosedPositionStore()
    )


def a_closing(asset: str, pnl: Decimal) -> ClosedPosition:
    closed_at = NOW - timedelta(hours=1)
    return ClosedPosition(
        tenant_id=TENANT,
        flow_id=FLOW.id,
        asset=asset,
        side=TradeSide.LONG,
        leverage=2,
        margin=Decimal(50),
        opening=PositionEnd(Decimal(100), closed_at - timedelta(minutes=5)),
        closing=PositionEnd(Decimal(101), closed_at),
        fees=Decimal(0),
        reason=CloseReason.AGENT,
        realized_pnl=pnl,
    )


def a_context(
    aggregates: Aggregates | None = None,
    snapshot: FlowSnapshot[CycleFlow] = SNAPSHOT,
    decisions: InMemoryPastDecisionsAdapter | None = None,
    closed: ClosedPositionStore | None = None,
) -> CycleContext:
    readings = [SourceReading("news", (SourceData("news", "RSS", 2, None, {"titolo": "t"}),))]
    closings = InMemoryClosedPositionRepositoryAdapter(closed or ClosedPositionStore(), TENANT)
    memory = MemoryReadings(decisions or no_past_decisions(), closings)
    compose = ComposeCycleContextUseCase(Composer(), Actions(), aggregates or Aggregates(), Clock(), memory)
    return compose.execute(FLOW.id.value, snapshot, readings, [AbsentSource("pivots", "fonte non disponibile")])


def remembering(memory: FlowMemory, *positions: CyclePosition) -> FlowSnapshot[CycleFlow]:
    flow = replace(FLOW, configuration=replace(FLOW.configuration, memory=memory))
    account = CycleAccount("USDC", Decimal(500), positions, Decimal(500))
    return FlowSnapshot(SNAPSHOT.sources, replace(CYCLE_FLOW, flow=flow, account=account))


def decided(cycles: InMemoryCycleRepositoryAdapter, ago: timedelta, *decisions: RecordedDecision) -> None:
    cycles.record(CycleRecord(FLOW.id.value, NOW - ago, CycleOutcome.COMPLETED, decisions=decisions))


def test_without_the_memory_the_question_has_none_and_nothing_is_read() -> None:
    cycles = InMemoryCycleRepositoryAdapter()
    decided(cycles, timedelta(hours=1), RecordedDecision("BTC", DecisionAction.CLOSE, None, 60, "obiettivo"))
    decisions = InMemoryPastDecisionsAdapter(cycles, InMemoryOrderRepositoryAdapter(), ClosedPositionStore())

    assert a_context(decisions=decisions).question.memory is None


def test_with_the_memory_the_question_holds_the_operative_decisions_before_now_with_the_pnl_held_now() -> None:
    cycles = InMemoryCycleRepositoryAdapter()
    opening = RecordedDecision("BTC", DecisionAction.OPEN, TradeSide.LONG, 80, "rottura")
    decided(cycles, timedelta(hours=1), opening, RecordedDecision("ETH", DecisionAction.HOLD, None, 50, "laterale"))
    decisions = InMemoryPastDecisionsAdapter(cycles, InMemoryOrderRepositoryAdapter(), ClosedPositionStore())
    held = CyclePosition("BTC", TradeSide.LONG, Decimal(1), 2, Decimal(100), Decimal(104), Decimal(4), None)

    snapshot = remembering(FlowMemory(active=True), held)

    question = a_context(snapshot=snapshot, decisions=decisions).question

    memory = (
        AssetMemory(
            "BTC",
            (
                MemoryEntry(
                    NOW - timedelta(hours=1), "BTC", DecisionAction.OPEN, TradeSide.LONG, None, "rottura", None, None
                ),
            ),
        ),
        AssetMemory("ETH", ()),
    )
    assert question.memory == memory
    assert question.system_prompt == snapshot.state.configuration.rendered_system_prompt(("apri", "chiudi"), memory)
    assert "- 2026-" in question.system_prompt


def test_with_the_summary_the_memory_begins_with_the_closings_of_the_flow_in_the_currency_of_its_account() -> None:
    closed = ClosedPositionStore()
    closed.positions.append(a_closing("ETH", Decimal("1.5")))
    snapshot = remembering(FlowMemory(active=True, days=2, summary=True))

    question = a_context(snapshot=snapshot, closed=closed).question

    assert question.memory is not None
    assert question.memory[1].summary == (
        "ETH long — oggi: 1 chiuse, 1 vinte, 0 perse, PnL 1,50 USDC; ultimi 2 giorni: 1 chiuse, 1 vinte, 0 perse,"
        " PnL 1,50 USDC",
    )
    assert f"ETH:\n- {question.memory[1].summary[0]}" in question.system_prompt


def test_the_question_of_the_cycle_carries_the_flow_alone_its_sources_and_the_missing_declared() -> None:
    configuration = FLOW.configuration

    assert a_context().question == CycleQuestion(
        model=configuration.model.name,
        settings=configuration.model.parameters,
        system_prompt=configuration.rendered_system_prompt(("apri", "chiudi")),
        assets=configuration.assets,
        started_at=CYCLE_FLOW.started_at,
        now=NOW,
        state=CYCLE_FLOW.state_view(),
        sources=(SourceData("news", "RSS", 2, None, {"titolo": "t"}),),
        missing=("pivots: fonte non disponibile",),
        memory=None,
    )


def test_the_aggregates_of_the_sources_follow_the_data_they_were_made_of() -> None:
    aggregated = Aggregated("volumi", "aggregato", "BTC", {"volume_24h_usd": "400"})
    aggregates = Aggregates(aggregated)

    question = a_context(aggregates).question

    assert aggregates.received == [(SourceData("news", "RSS", 2, None, {"titolo": "t"}),)]
    assert question.sources == (
        SourceData("news", "RSS", 2, None, {"titolo": "t"}),
        SourceData("volumi", "aggregato", None, "BTC", {"volume_24h_usd": "400"}),
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

    review = review_of(check).execute(FLOW.id.value, SNAPSHOT, decisions)

    assert [order.flow for order in review.orders] == [CYCLE_FLOW]
    outcomes = review.outcomes
    assert isinstance(outcomes, tuple)
    assert [type(outcome) for outcome in outcomes] == [ApprovedOpening, BlockedDecision]
    assert review.orders[0].outcome == outcomes[0]


def test_the_exit_plan_of_the_agent_reaches_the_risk_check() -> None:
    plan = Plan(Decimal(110000), Decimal(105000), "chiusura sotto 98000")
    decisions = CycleDecisions(CYCLE_FLOW, Reply(Response((Decision("open", "BTC", plan),))))
    check = CheckRiskUseCase({"Hyperliquid": FakeExchangeLimitsAdapter(frozenset({"BTC"}))})

    review = review_of(check).execute(FLOW.id.value, SNAPSHOT, decisions)

    [order] = review.orders
    assert isinstance(order.outcome, ApprovedOpening)
    assert order.outcome.exit_plan == ExitPlan(target=Decimal(110000), invalidation="chiusura sotto 98000")
    assert [adjustment.reason for adjustment in order.outcome.adjustments] == [
        "stop 105000 scartato: incoerente con long al prezzo 100000"
    ]


def test_the_minimum_confidence_of_the_flow_blocks_a_weak_opening() -> None:
    configuration = replace(FLOW.configuration, minimum_confidence=MinimumConfidence(60))
    cycle_flow = replace(CYCLE_FLOW, flow=replace(FLOW, configuration=configuration))
    weak, convinced = Decision("open", "BTC", confidence=40), Decision("open", "ETH", confidence=60)
    decisions = CycleDecisions(cycle_flow, Reply(Response((weak, convinced))))
    check = CheckRiskUseCase({"Hyperliquid": FakeExchangeLimitsAdapter(frozenset({"BTC", "ETH"}))})

    review = review_of(check).execute(FLOW.id.value, SNAPSHOT, decisions)

    outcomes = review.outcomes
    assert isinstance(outcomes, tuple)
    assert outcomes[0] == BlockedDecision("BTC", "apertura BTC non eseguita: confidenza 40 sotto la minima 60")
    assert [order.outcome.asset for order in review.orders] == ["ETH"]


def test_the_exchange_of_an_account_without_limits_is_unavailable() -> None:
    decisions = CycleDecisions(replace(CYCLE_FLOW, exchange="Altro"), Reply(Response((Closing("BTC"),))))
    check = CheckRiskUseCase({"Hyperliquid": FakeExchangeLimitsAdapter()})

    with pytest.raises(FlowExchangeUnavailableError):
        review_of(check).execute(FLOW.id.value, SNAPSHOT, decisions)


def test_openings_suspended_by_the_guard_of_the_losses_are_blocked_before_the_exchange() -> None:
    decisions = CycleDecisions(CYCLE_FLOW, Reply(Response((Opening("BTC"),))))
    guard = LossGuard(suspended=True)

    review = review_of(CheckRiskUseCase({"Hyperliquid": FakeExchangeLimitsAdapter()}), guard).execute(
        FLOW.id.value, SNAPSHOT, decisions
    )

    assert guard.guarded == [CYCLE_FLOW]
    assert review.orders == ()
    assert review.outcomes == (
        BlockedDecision("BTC", "apertura BTC non eseguita: aperture sospese per perdita massima"),
    )


def test_the_change_of_the_plan_of_an_open_position_reaches_the_risk_check() -> None:
    held = CyclePosition(
        "BTC", TradeSide.SHORT, Decimal("0.01"), 2, Decimal(102000), Decimal(100000), Decimal(20), None
    )
    cycle_flow = replace(CYCLE_FLOW, account=CycleAccount("USDC", Decimal(500), (held,), Decimal(500)))
    change = Change(Decimal(99000), Decimal(101500), "sopra 103000", remove_target=False)
    decisions = CycleDecisions(cycle_flow, Reply(Response((Decision("update", "BTC", change=change),))))
    check = CheckRiskUseCase({"Hyperliquid": FakeExchangeLimitsAdapter(frozenset({"BTC"}))})

    review = review_of(check).execute(FLOW.id.value, SNAPSHOT, decisions)

    [order] = review.orders
    assert order.outcome == ApprovedUpdate("BTC", ExitPlanChange(Decimal(99000), Decimal(101500), "sopra 103000"), ())


def test_a_removal_of_the_target_reaches_the_risk_check() -> None:
    held = CyclePosition("BTC", TradeSide.LONG, Decimal("0.01"), 2, Decimal(98000), Decimal(100000), Decimal(20), None)
    cycle_flow = replace(CYCLE_FLOW, account=CycleAccount("USDC", Decimal(500), (held,), Decimal(500)))
    decisions = CycleDecisions(
        cycle_flow, Reply(Response((Decision("update", "BTC", change=Change(remove_target=True)),)))
    )
    check = CheckRiskUseCase({"Hyperliquid": FakeExchangeLimitsAdapter(frozenset({"BTC"}))})

    review = review_of(check).execute(FLOW.id.value, SNAPSHOT, decisions)

    [order] = review.orders
    assert order.outcome == ApprovedUpdate("BTC", ExitPlanChange(remove_target=True), ())


def test_an_opening_reduced_by_the_risk_check_is_told_with_the_margin_asked_and_the_one_approved() -> None:
    configuration = replace(FLOW.configuration, risk_limits=RiskLimits(5, Decimal(5)))
    cycle_flow = replace(CYCLE_FLOW, flow=replace(FLOW, configuration=configuration))
    decisions = CycleDecisions(cycle_flow, Reply(Response((Opening("BTC"), Opening("ETH")))))
    check = CheckRiskUseCase({"Hyperliquid": FakeExchangeLimitsAdapter(frozenset({"BTC"}))})
    reduced, blocked = FakeOpeningReducedNoticeAdapter(), FakeOpeningBlockedNoticeAdapter()

    review = review_of(check, reduced=reduced, blocked=blocked).execute(FLOW.id.value, SNAPSHOT, decisions)

    [order] = review.orders
    assert isinstance(order.outcome, ApprovedOpening)
    assert reduced.told == [("alfa", "BTC", Decimal(50), Decimal(25))]
    assert blocked.told == [("alfa", "ETH", "asset non negoziabile sull'exchange: ETH")]


def test_an_opening_blocked_by_the_risk_check_is_told_with_its_cause() -> None:
    configuration = replace(FLOW.configuration, minimum_confidence=MinimumConfidence(60))
    cycle_flow = replace(CYCLE_FLOW, flow=replace(FLOW, configuration=configuration))
    decisions = CycleDecisions(cycle_flow, Reply(Response((Decision("open", "BTC", confidence=40),))))
    check = CheckRiskUseCase({"Hyperliquid": FakeExchangeLimitsAdapter(frozenset({"BTC"}))})
    reduced, blocked = FakeOpeningReducedNoticeAdapter(), FakeOpeningBlockedNoticeAdapter()

    review_of(check, reduced=reduced, blocked=blocked).execute(FLOW.id.value, SNAPSHOT, decisions)

    assert blocked.told == [("alfa", "BTC", "confidenza 40 sotto la minima 60")]
    assert reduced.told == []


def test_a_close_blocked_and_an_opening_approved_as_asked_are_not_told() -> None:
    decisions = CycleDecisions(CYCLE_FLOW, Reply(Response((Closing("ETH"), Opening("BTC")))))
    check = CheckRiskUseCase({"Hyperliquid": FakeExchangeLimitsAdapter(frozenset({"BTC", "ETH"}))})
    reduced, blocked = FakeOpeningReducedNoticeAdapter(), FakeOpeningBlockedNoticeAdapter()

    review = review_of(check, reduced=reduced, blocked=blocked).execute(FLOW.id.value, SNAPSHOT, decisions)

    outcomes = review.outcomes
    assert isinstance(outcomes, tuple)
    assert [type(outcome) for outcome in outcomes] == [BlockedDecision, ApprovedOpening]
    assert (reduced.told, blocked.told) == ([], [])


def short_on_btc() -> CycleFlow:
    position = CyclePosition(
        "BTC", TradeSide.SHORT, Decimal("0.01"), 2, Decimal(100000), Decimal(100000), Decimal(0), None
    )
    return replace(CYCLE_FLOW, account=CycleAccount("USDC", Decimal(500), (position,), Decimal(500)))


def test_a_reversal_closes_the_position_and_leaves_its_opening_waiting_for_the_second_execution() -> None:
    flow = short_on_btc()
    plan = Plan(Decimal(110000), Decimal(90000), None)
    decisions = CycleDecisions(flow, Reply(Response((Decision("reverse", "BTC", plan),))))
    check = CheckRiskUseCase({"Hyperliquid": FakeExchangeLimitsAdapter(frozenset({"BTC"}))})

    review = review_of(check).execute(FLOW.id.value, FlowSnapshot((), flow), decisions)

    [order] = review.orders
    reopening = OpenIntent("BTC", TradeSide.LONG, Decimal("0.2"), 3, 70, ExitPlan(Decimal(110000), Decimal(90000)))
    assert order.outcome == ApprovedClose("BTC", reopening)
    assert review.reversing


def test_a_cycle_without_reversals_has_nothing_waiting() -> None:
    decisions = CycleDecisions(short_on_btc(), Reply(Response((Closing("BTC"),))))
    check = CheckRiskUseCase({"Hyperliquid": FakeExchangeLimitsAdapter(frozenset({"BTC"}))})

    review = review_of(check).execute(FLOW.id.value, SNAPSHOT, decisions)

    assert [order.outcome for order in review.orders] == [ApprovedClose("BTC")]
    assert not review.reversing
