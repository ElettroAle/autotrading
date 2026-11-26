"""The question of a cycle as the agent reads it: the flow alone, its sources, its limits (R1.4.3)."""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal

from autotrading.application.agent.compose_agent_context import ComposeAgentContextUseCase
from autotrading.domain.agent.agent_context import AgentContext, FlowStateView, PositionView, SourceData
from autotrading.domain.agent.decision import TradeDirection
from autotrading.domain.agent.exit_plan import ExitPlan

NOW = datetime(2026, 11, 12, 10, 30, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class Plan:
    target: Decimal | None = None
    stop: Decimal | None = None
    invalidation: str | None = None


@dataclass(frozen=True, slots=True)
class Position:
    asset: str = "BTC"
    direction: str = "short"
    size: Decimal = Decimal("0.1")
    leverage: int = 3
    entry_price: Decimal = Decimal(60000)
    mark_price: Decimal = Decimal(59000)
    unrealized_pnl: Decimal = Decimal(-2)
    liquidation_price: Decimal | None = None
    exit_plan: Plan = Plan()
    max_profit: Decimal | None = None


@dataclass(frozen=True, slots=True)
class State:
    currency: str = "USDC"
    allocated_capital: Decimal = Decimal(500)
    funds: Decimal = Decimal(480)
    available_liquidity: Decimal = Decimal(300)
    total_value: Decimal = Decimal(478)
    return_percent: Decimal = Decimal("-4.40")
    positions: tuple[Position, ...] = (Position(),)
    reopening_blocks: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Source:
    source: str = "indicatori"
    adapter: str = "Hyperliquid"
    weight: int = 8
    asset: str | None = "BTC"
    values: Mapping[str, str] = field(default_factory=lambda: {"rsi": "71"})


@dataclass(frozen=True, slots=True)
class Question:
    model: str = "openrouter/deepseek-chat"
    settings: Mapping[str, Decimal | str] = field(default_factory=dict)
    system_prompt: str = "Sei un trader su BTC"
    assets: tuple[str, ...] = ("BTC",)
    started_at: datetime = NOW
    now: datetime = NOW
    state: State = State()
    sources: tuple[Source, ...] = (Source(),)
    missing: tuple[str, ...] = ("notizie: timeout",)


def test_the_question_becomes_the_context_of_the_agent() -> None:
    context = ComposeAgentContextUseCase().execute(Question())

    assert context == AgentContext(
        system_prompt="Sei un trader su BTC",
        assets=("BTC",),
        started_at=NOW,
        now=NOW,
        state=FlowStateView(
            "USDC",
            Decimal(500),
            Decimal(480),
            Decimal(300),
            Decimal(478),
            Decimal("-4.40"),
            (
                PositionView(
                    "BTC", TradeDirection.SHORT, Decimal("0.1"), 3, Decimal(60000), Decimal(59000), Decimal(-2), None
                ),
            ),
        ),
        sources=(SourceData("indicatori", "Hyperliquid", 8, "BTC", {"rsi": "71"}),),
        missing=("notizie: timeout",),
    )


def test_each_position_keeps_the_exit_plan_in_force() -> None:
    planned = Position(exit_plan=Plan(Decimal(57000), Decimal(61000), "chiusura sopra 60500"))
    question = replace(Question(), state=State(positions=(planned,)))

    [position] = ComposeAgentContextUseCase().execute(question).state.positions

    assert position.exit_plan == ExitPlan(Decimal(57000), Decimal(61000), "chiusura sopra 60500")


def test_each_position_keeps_the_largest_profit_it_reached_when_the_flow_hands_it() -> None:
    # R5.5.1, ADR massimo-profitto-raggiunto-nello-stato-della-posizione.
    question = replace(Question(), state=State(positions=(Position(max_profit=Decimal(30)), Position(asset="ETH"))))

    positions = ComposeAgentContextUseCase().execute(question).state.positions

    assert [position.max_profit for position in positions] == [Decimal(30), None]


def test_the_state_keeps_the_openings_blocked_after_consecutive_losses_the_flow_hands() -> None:
    # R5.5.2, ADR controllo-delle-riaperture-dopo-perdite-consecutive.
    block = "riaperture short su NEAR ferme fino alle 15:30: 2 perdite consecutive"
    question = replace(Question(), state=State(reopening_blocks=(block,)))

    state = ComposeAgentContextUseCase().execute(question).state

    assert state.reopening_blocks == (block,)
