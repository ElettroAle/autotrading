"""What the reading tools give back: the same fields and texts the API gives the dashboard."""

from dataclasses import dataclass

from autotrading.adapters.inbound.mcp.formats import (
    amount_text,
    instant_text,
    optional_amount,
    optional_instant,
    optional_percent,
    optional_text,
)
from autotrading.application.accounts.account_summary import AccountSummary
from autotrading.application.flows.list_flow_overviews import FlowOverview
from autotrading.domain.flows.account_activity import AccountPosition
from autotrading.domain.flows.closed_position import ClosedPosition
from autotrading.domain.flows.closed_position_page import ClosedPositionPage
from autotrading.domain.flows.cycle_page import CyclePage
from autotrading.domain.flows.cycle_record import CycleFailure, CycleRecord, FailedAttempt
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow_ranking import FlowRanking
from autotrading.domain.flows.flow_results import FlowResults
from autotrading.domain.flows.flow_return import FlowReturn
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.flow_statistics import FlowStatistics
from autotrading.domain.flows.memory_entry import AssetMemory
from autotrading.domain.flows.openings_suspension import OpeningsSuspension
from autotrading.domain.flows.reopening_block import ReopeningBlock


@dataclass(frozen=True)
class OpeningsSuspensionView:
    """Why the openings are suspended, since when, the cause and whether the user resumes them (R3.2.2, R3.3.1)."""

    reason: str
    suspended_at: str
    cause: str
    resumable: bool

    @classmethod
    def of(cls, suspension: OpeningsSuspension | None) -> OpeningsSuspensionView | None:
        if suspension is None:
            return None
        return cls(
            reason=suspension.reason,
            suspended_at=instant_text(suspension.suspended_at),
            cause=suspension.cause.value,
            resumable=suspension.resumable,
        )


@dataclass(frozen=True)
class ReopeningBlockView:
    """The openings on a side stopped after consecutive losses until an instant, on the asset or on every asset of the
    flow when it is null, with the text of the API (R5.5.2).
    """

    side: str
    asset: str | None
    consecutive_losses: int
    until: str
    text: str

    @classmethod
    def of(cls, block: ReopeningBlock) -> ReopeningBlockView:
        return cls(
            side=block.side.value,
            asset=block.asset,
            consecutive_losses=block.consecutive_losses,
            until=instant_text(block.until),
            text=block.state_text,
        )


@dataclass(frozen=True)
class ResultsView:
    """How a flow is doing in the period asked for (R6.4.2): the gain since the start and in the period."""

    total_gain: str
    total_gain_percent: str | None
    period_gain: str
    period_gain_percent: str | None
    open_positions: int
    failed_cycles: int
    next_cycle_at: str | None

    @classmethod
    def of(cls, results: FlowResults) -> ResultsView:
        return cls(
            total_gain=amount_text(results.total_gain),
            total_gain_percent=optional_text(results.total_gain_percent),
            period_gain=amount_text(results.period_gain),
            period_gain_percent=optional_text(results.period_gain_percent),
            open_positions=results.open_positions,
            failed_cycles=results.failed_cycles,
            next_cycle_at=optional_instant(results.next_cycle_at),
        )


@dataclass(frozen=True)
class LastCycleView:
    planned_at: str
    outcome: str

    @classmethod
    def of(cls, record: CycleRecord) -> LastCycleView:
        return cls(planned_at=instant_text(record.planned_at), outcome=record.outcome.value)


@dataclass(frozen=True)
class FlowOverviewView:
    """A flow in use: status, value, gain since the start, last and next cycle (R1.7.3, R2.2.2, R6.4.2)."""

    id: str
    name: str
    account: str
    environment: str
    status: str
    pause_reason: str | None
    openings_suspension: OpeningsSuspensionView | None
    model: str
    version: int
    assets: list[str]
    last_cycle: LastCycleView | None
    next_cycle_at: str | None
    currency: str | None
    initial_capital: str | None
    current_capital: str | None
    return_percent: str | None
    recent_outcomes: list[LastCycleView]
    summary: ResultsView | None

    @classmethod
    def of(cls, overview: FlowOverview) -> FlowOverviewView:
        summary, capital, last = overview.summary, overview.capital, overview.last_cycle
        return cls(
            id=str(summary.flow_id),
            name=summary.name,
            account=summary.account,
            environment=overview.environment,
            status=summary.status,
            pause_reason=summary.pause_reason,
            openings_suspension=OpeningsSuspensionView.of(overview.openings_suspension),
            model=summary.model,
            version=summary.version,
            assets=list(summary.assets),
            last_cycle=None if last is None else LastCycleView.of(last),
            next_cycle_at=optional_instant(overview.next_cycle_at),
            currency=overview.currency,
            initial_capital=None if capital is None else amount_text(capital.initial_capital),
            current_capital=None if capital is None else amount_text(capital.current_capital),
            return_percent=None if capital is None else optional_text(capital.percent),
            recent_outcomes=[LastCycleView.of(record) for record in overview.recent_cycles],
            summary=None if overview.results is None else ResultsView.of(overview.results),
        )


@dataclass(frozen=True)
class FlowListView:
    flows: list[FlowOverviewView]


@dataclass(frozen=True)
class PositionView:
    """An open position of the flow with its exit plan in force (R1.6.1, R3.1.1) and, when the stop of the flow follows
    the price, the largest profit it reached (R5.5.1)."""

    asset: str
    side: str
    size: str
    leverage: str
    entry_price: str
    mark_price: str
    margin: str
    unrealized_pnl: str
    unrealized_pnl_percent: str | None
    target_price: str | None
    stop_price: str | None
    invalidation: str | None
    max_profit_reached: str | None

    @classmethod
    def of(cls, position: AccountPosition, state: FlowState) -> PositionView:
        plan = state.exit_plan_of(position.asset)
        return cls(
            asset=position.asset,
            side=position.side.value,
            size=amount_text(position.size),
            leverage=str(position.leverage),
            entry_price=amount_text(position.entry_price),
            mark_price=amount_text(position.mark_price),
            margin=amount_text(position.margin),
            unrealized_pnl=amount_text(position.unrealized_pnl),
            unrealized_pnl_percent=optional_amount(position.unrealized_pnl_percent),
            target_price=optional_amount(plan.target),
            stop_price=optional_amount(plan.stop),
            invalidation=plan.invalidation,
            max_profit_reached=optional_amount(state.max_profit_of(position.asset)),
        )


@dataclass(frozen=True)
class FlowStateView:
    """The state of a flow read from the exchange now (R1.6.1), with its open positions and results (R6.4.2) and the
    openings blocked after consecutive losses (R5.5.2)."""

    flow_id: str
    currency: str
    allocated_capital: str
    available_liquidity: str
    margin: str
    unrealized_pnl: str
    realized_pnl: str
    fees: str
    total_value: str
    return_percent: str | None
    positions: list[PositionView]
    summary: ResultsView
    openings_suspension: OpeningsSuspensionView | None
    reopening_blocks: list[ReopeningBlockView]

    @classmethod
    def of(cls, results: FlowResults) -> FlowStateView:
        state = results.state
        return cls(
            flow_id=str(state.flow_id.value),
            currency=state.currency,
            allocated_capital=amount_text(state.allocated_capital),
            available_liquidity=amount_text(state.available_liquidity),
            margin=amount_text(state.margin),
            unrealized_pnl=amount_text(state.unrealized_pnl),
            realized_pnl=amount_text(state.realized_pnl),
            fees=amount_text(state.fees),
            total_value=amount_text(state.total_value),
            return_percent=optional_amount(FlowReturn.of(state).percent),
            positions=[PositionView.of(position, state) for position in state.positions],
            summary=ResultsView.of(results),
            openings_suspension=OpeningsSuspensionView.of(results.openings_suspension),
            reopening_blocks=[ReopeningBlockView.of(block) for block in state.reopening_blocks],
        )


@dataclass(frozen=True)
class ClosedPositionView:
    """A closed position of a flow with its result (R1.7.2)."""

    asset: str
    side: str
    leverage: int
    margin: str
    open_price: str
    close_price: str
    opened_at: str
    closed_at: str
    duration_seconds: int
    pnl: str
    pnl_percent_of_margin: str
    fees: str
    reason: str
    opening_cycle: str | None
    closing_cycle: str | None

    @classmethod
    def of(cls, position: ClosedPosition) -> ClosedPositionView:
        return cls(
            asset=position.asset,
            side=position.side.value,
            leverage=position.leverage,
            margin=amount_text(position.margin),
            open_price=amount_text(position.opening.price),
            close_price=amount_text(position.closing.price),
            opened_at=instant_text(position.opening.at),
            closed_at=instant_text(position.closing.at),
            duration_seconds=int(position.duration.total_seconds()),
            pnl=amount_text(position.pnl),
            pnl_percent_of_margin=amount_text(position.pnl_percent_of_margin),
            fees=amount_text(position.fees),
            reason=position.reason.value,
            opening_cycle=optional_instant(position.opening.cycle),
            closing_cycle=optional_instant(position.closing.cycle),
        )


@dataclass(frozen=True)
class ClosedPositionPageView:
    """A page of the closed positions of a flow, from the most recent close, with how many match in all."""

    page: int
    has_next: bool
    total: int
    positions: list[ClosedPositionView]

    @classmethod
    def of(cls, page: ClosedPositionPage) -> ClosedPositionPageView:
        return cls(
            page=page.number,
            has_next=page.has_next,
            total=page.total,
            positions=[ClosedPositionView.of(position) for position in page.positions],
        )


@dataclass(frozen=True)
class FailureView:
    step: str
    error_type: str
    message: str

    @classmethod
    def of(cls, failure: CycleFailure | None) -> FailureView | None:
        if failure is None:
            return None
        return cls(step=failure.step.value, error_type=failure.error_type, message=failure.message)


@dataclass(frozen=True)
class CycleSummaryView:
    """A cycle in the list: its instants, its outcome, the decisions of the agent and what started it (R1.7.3)."""

    planned_at: str
    started_at: str | None
    outcome: str
    failure: FailureView | None
    decisions: dict[str, object] | None
    trigger: str

    @classmethod
    def of(cls, record: CycleRecord) -> CycleSummaryView:
        decisions = record.document(CycleStep.AGENT_DECISION)
        return cls(
            planned_at=instant_text(record.planned_at),
            started_at=optional_instant(record.started_at),
            outcome=record.outcome.value,
            failure=FailureView.of(record.failure),
            decisions=None if decisions is None else dict(decisions),
            trigger=record.trigger.value,
        )


@dataclass(frozen=True)
class CyclePageView:
    page: int
    has_next: bool
    total: int
    cycles: list[CycleSummaryView]

    @classmethod
    def of(cls, page: CyclePage) -> CyclePageView:
        return cls(
            page=page.number,
            has_next=page.has_next,
            total=page.total,
            cycles=[CycleSummaryView.of(cycle) for cycle in page.cycles],
        )


@dataclass(frozen=True)
class StepDocumentView:
    step: str
    content: dict[str, object]


@dataclass(frozen=True)
class AbsentSourceView:
    source: str
    reason: str
    adapter: str | None


@dataclass(frozen=True)
class FailedAttemptView:
    step: str
    attempt: int
    error_type: str
    message: str

    @classmethod
    def of(cls, attempt: FailedAttempt) -> FailedAttemptView:
        return cls(
            step=attempt.step.value, attempt=attempt.attempt, error_type=attempt.error_type, message=attempt.message
        )


@dataclass(frozen=True)
class CycleDetailView:
    """A cycle with everything recorded about it, the decisions of the agent among its documents (R1.7.1)."""

    planned_at: str
    started_at: str | None
    delay_seconds: int | None
    outcome: str
    failure: FailureView | None
    steps: list[str]
    absent_sources: list[AbsentSourceView]
    documents: list[StepDocumentView]
    model_attempts: int | None
    trigger: str
    failed_attempts: list[FailedAttemptView]
    # The memory as the domain gives it, which the results of the tools write as the API does (R5.3.4).
    memory: tuple[AssetMemory, ...] | None

    @classmethod
    def of(cls, record: CycleRecord) -> CycleDetailView:
        return cls(
            planned_at=instant_text(record.planned_at),
            started_at=optional_instant(record.started_at),
            delay_seconds=record.delay_seconds,
            outcome=record.outcome.value,
            failure=FailureView.of(record.failure),
            steps=[step.value for step in record.steps],
            absent_sources=[
                AbsentSourceView(source=item.source, reason=item.reason, adapter=item.adapter)
                for item in record.absent_sources
            ],
            documents=[
                StepDocumentView(step=document.step.value, content=dict(document.content))
                for document in record.documents
            ],
            model_attempts=record.model_attempts,
            trigger=record.trigger.value,
            failed_attempts=[FailedAttemptView.of(attempt) for attempt in record.failed_attempts],
            memory=record.memory,
        )


@dataclass(frozen=True)
class FlowStatisticsView:
    """The statistics of a flow over a period (R2.2.6)."""

    won: int
    lost: int
    operations: int
    win_rate_percent: str | None
    average_winning_pnl: str | None
    average_losing_pnl: str | None
    total_fees: str
    model_cost_usd: str
    model_calls_without_cost: int
    return_percent: str | None

    @classmethod
    def of(cls, statistics: FlowStatistics) -> FlowStatisticsView:
        return cls(
            won=statistics.won,
            lost=statistics.lost,
            operations=statistics.operations,
            win_rate_percent=optional_percent(statistics.win_rate_percent),
            average_winning_pnl=optional_amount(statistics.average_winning_pnl),
            average_losing_pnl=optional_amount(statistics.average_losing_pnl),
            total_fees=amount_text(statistics.total_fees),
            model_cost_usd=amount_text(statistics.model_cost_usd),
            model_calls_without_cost=statistics.model_calls_without_cost,
            return_percent=optional_percent(statistics.return_percent),
        )


@dataclass(frozen=True)
class FlowRankingView:
    """A row of the ranking of the flows (R2.4.2)."""

    flow_id: str
    flow_name: str
    return_percent: str | None
    max_drawdown_percent: str | None
    pnl: str
    total_fees: str
    win_rate_percent: str | None
    operations: int
    model_cost_usd: str
    model_calls_without_cost: int

    @classmethod
    def of(cls, ranking: FlowRanking) -> FlowRankingView:
        statistics = ranking.statistics
        return cls(
            flow_id=str(ranking.flow_id),
            flow_name=ranking.flow_name,
            return_percent=optional_percent(ranking.return_percent),
            max_drawdown_percent=optional_percent(ranking.max_drawdown_percent),
            pnl=amount_text(statistics.net_pnl),
            total_fees=amount_text(statistics.total_fees),
            win_rate_percent=optional_percent(statistics.win_rate_percent),
            operations=statistics.operations,
            model_cost_usd=amount_text(statistics.model_cost_usd),
            model_calls_without_cost=statistics.model_calls_without_cost,
        )


@dataclass(frozen=True)
class RankingView:
    flows: list[FlowRankingView]


@dataclass(frozen=True)
class AccountView:
    """An account of the tenant: what it is, the capital its flows hold and the largest exposure they may have together
    on one side, never its credentials (R0.2.3, R5.5.5)."""

    id: str
    name: str
    exchange: str
    network: str
    allocated_capital: str
    currency: str
    max_direction_exposure_percent: str | None

    @classmethod
    def of(cls, summary: AccountSummary) -> AccountView:
        return cls(
            id=str(summary.id.value),
            name=summary.name.value,
            exchange=summary.exchange.value,
            network=summary.network.kind.value,
            allocated_capital=amount_text(summary.allocated_capital),
            currency=summary.currency,
            max_direction_exposure_percent=optional_amount(summary.max_direction_exposure_percent),
        )


@dataclass(frozen=True)
class AccountListView:
    accounts: list[AccountView]
