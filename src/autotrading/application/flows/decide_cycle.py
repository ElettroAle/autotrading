from uuid import UUID

from autotrading.application.flows.ports import CycleContext, CycleDecisions, FlowAgentPort


class DecideCycleUseCase:
    """The decisions of the agent for the cycle: the model of the flow with the key of its tenant (R1.4.4)."""

    def __init__(self, agent: FlowAgentPort) -> None:
        self._agent = agent

    def execute(self, flow_id: UUID, context: CycleContext) -> CycleDecisions:  # noqa: ARG002 - the signature of the port
        return CycleDecisions(context.flow, self._agent.execute(context.question))
