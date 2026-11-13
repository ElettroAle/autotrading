"""The question of a cycle as the agent reads it: the flow alone, its sources, its limits (R1.4.3)."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from autotrading.application.agent.compose_agent_context import ComposeAgentContextUseCase
from autotrading.domain.agent.agent_context import AgentContext, FlowStateView, PositionView, SourceData
from autotrading.domain.agent.decision import TradeDirection

NOW = datetime(2026, 11, 12, 10, 30, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class Position:
    asset: str = "BTC"
    direction: str = "short"
    size: Decimal = Decimal("0.1")
    leverage: int = 3
    entry_price: Decimal = Decimal(60000)
    unrealized_pnl: Decimal = Decimal(-2)
    liquidation_price: Decimal | None = None


@dataclass(frozen=True, slots=True)
class State:
    currency: str = "USDC"
    allocated_capital: Decimal = Decimal(500)
    funds: Decimal = Decimal(480)
    available_liquidity: Decimal = Decimal(300)
    total_value: Decimal = Decimal(478)
    return_percent: Decimal = Decimal("-4.40")
    positions: tuple[Position, ...] = (Position(),)


@dataclass(frozen=True, slots=True)
class Source:
    source: str = "indicatori"
    weight: int = 8
    asset: str | None = "BTC"
    values: Mapping[str, str] = field(default_factory=lambda: {"rsi": "71"})


@dataclass(frozen=True, slots=True)
class Question:
    model: str = "openrouter/deepseek-chat"
    settings: Mapping[str, Decimal | str] = field(default_factory=dict)
    instructions: str = "Sei un trader"
    assets: tuple[str, ...] = ("BTC",)
    max_leverage: int = 5
    started_at: datetime = NOW
    now: datetime = NOW
    state: State = State()
    sources: tuple[Source, ...] = (Source(),)
    missing: tuple[str, ...] = ("notizie: timeout",)


def test_the_question_becomes_the_context_of_the_agent() -> None:
    context = ComposeAgentContextUseCase().execute(Question())

    assert context == AgentContext(
        instructions="Sei un trader",
        assets=("BTC",),
        max_leverage=5,
        started_at=NOW,
        now=NOW,
        state=FlowStateView(
            "USDC",
            Decimal(500),
            Decimal(480),
            Decimal(300),
            Decimal(478),
            Decimal("-4.40"),
            (PositionView("BTC", TradeDirection.SHORT, Decimal("0.1"), 3, Decimal(60000), Decimal(-2), None),),
        ),
        sources=(SourceData("indicatori", 8, "BTC", {"rsi": "71"}),),
        missing=("notizie: timeout",),
    )
