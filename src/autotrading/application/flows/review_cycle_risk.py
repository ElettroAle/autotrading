from uuid import UUID

from autotrading.application.flows.check_risk import CheckRiskCommand, CheckRiskUseCase
from autotrading.application.flows.ports import CycleDecisions, FlowSnapshot, RiskReview
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_order import CycleOrder
from autotrading.domain.flows.risk_outcome import approved_of
from autotrading.domain.flows.trade_intent import CloseIntent, HoldIntent, OpenIntent


class ReviewCycleRiskUseCase:
    """The decisions of the agent through the risk check of the flow, on the exchange of its account
    (R1.5.1-R1.5.4).
    """

    def __init__(self, check_risk: CheckRiskUseCase) -> None:
        self._check_risk = check_risk

    def execute(
        self,
        flow_id: UUID,  # noqa: ARG002 - the signature of the port
        snapshot: FlowSnapshot[CycleFlow],  # noqa: ARG002 - the signature of the port
        decisions: CycleDecisions,
    ) -> RiskReview[CycleOrder]:
        cycle_flow = decisions.flow
        command = CheckRiskCommand(
            tuple(
                decision.intent_with(OpenIntent.of, CloseIntent, HoldIntent)
                for decision in decisions.reply.response.decisions
            ),
            cycle_flow.configuration.risk_policy,
            cycle_flow.risk_state(),
            cycle_flow.exchange,
        )
        outcomes = self._check_risk.execute(command)
        orders = tuple(CycleOrder(cycle_flow, outcome) for outcome in approved_of(outcomes))
        return RiskReview(orders, tuple(outcomes))
