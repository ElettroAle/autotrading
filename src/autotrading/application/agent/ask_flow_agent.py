from autotrading.application.agent.ask_agent import AgentAnswer, AskAgentCommand, AskAgentUseCase
from autotrading.application.agent.compose_agent_context import ComposeAgentContextUseCase
from autotrading.application.agent.ports import AgentQuestionPort


class AskFlowAgentUseCase:
    """Asks the model of the flow the question of its cycle, with the context composed from it (R1.4.3-R1.4.6)."""

    def __init__(self, compose: ComposeAgentContextUseCase, ask: AskAgentUseCase) -> None:
        self._compose = compose
        self._ask = ask

    def execute(self, question: AgentQuestionPort) -> AgentAnswer:
        context = self._compose.execute(question)
        return self._ask.execute(AskAgentCommand(question.model, question.settings, context))
