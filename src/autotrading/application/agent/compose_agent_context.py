from autotrading.application.agent.ports import AgentQuestionPort, QuestionPositionPort, QuestionStatePort
from autotrading.domain.agent.agent_context import AgentContext, FlowStateView, PositionView, SourceData
from autotrading.domain.agent.decision import TradeDirection


class ComposeAgentContextUseCase:
    """The context the agent receives for the question of a cycle: the flow alone and nothing else (R1.4.3).

    The context checks its own instants, so a question that cannot be composed fails the step that composes it.
    """

    def execute(self, question: AgentQuestionPort) -> AgentContext:
        return AgentContext(
            instructions=question.instructions,
            assets=tuple(question.assets),
            max_leverage=question.max_leverage,
            started_at=question.started_at,
            now=question.now,
            state=_state_of(question.state),
            sources=tuple(
                SourceData(source.source, source.weight, source.asset, source.values) for source in question.sources
            ),
            missing=tuple(question.missing),
        )


def _state_of(state: QuestionStatePort) -> FlowStateView:
    return FlowStateView(
        currency=state.currency,
        allocated_capital=state.allocated_capital,
        funds=state.funds,
        available_liquidity=state.available_liquidity,
        total_value=state.total_value,
        return_percent=state.return_percent,
        positions=tuple(_position_of(position) for position in state.positions),
    )


def _position_of(position: QuestionPositionPort) -> PositionView:
    return PositionView(
        position.asset,
        TradeDirection(position.direction),
        position.size,
        position.leverage,
        position.entry_price,
        position.unrealized_pnl,
        position.liquidation_price,
    )
