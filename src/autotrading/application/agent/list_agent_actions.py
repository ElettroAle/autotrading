from autotrading.domain.agent.decision import TradeAction


class ListAgentActionsUseCase:
    """The actions the agent may take on an asset, in the words of its answer: the system prompt of a flow names them
    (R1.4.3, R1.4.8).
    """

    def execute(self) -> tuple[str, ...]:
        return tuple(action.value for action in TradeAction)
