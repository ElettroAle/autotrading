from decimal import Decimal
from uuid import UUID

from autotrading.application.flows.check_risk import CheckRiskCommand, CheckRiskUseCase
from autotrading.application.flows.ports import (
    CycleDecisions,
    DecisionExitPlanPort,
    DecisionPlanChangePort,
    FlowLossGuardPort,
    FlowSnapshot,
    RiskReview,
)
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_order import CycleOrder
from autotrading.domain.flows.exit_plan import ExitPlan
from autotrading.domain.flows.risk_outcome import approved_of
from autotrading.domain.flows.trade_intent import CloseIntent, HoldIntent, OpenIntent, UpdateIntent


class ReviewCycleRiskUseCase:
    """The decisions of the agent through the risk check of the flow, on the exchange of its account
    (R1.5.1-R1.5.4), with the minimum confidence of the flow for the openings (R3.1.4).

    The guard of the losses comes first: openings suspended for maximum loss are blocked by the check (R3.2.2).
    """

    def __init__(self, check_risk: CheckRiskUseCase, loss_guard: FlowLossGuardPort) -> None:
        self._check_risk = check_risk
        self._loss_guard = loss_guard

    def execute(
        self,
        flow_id: UUID,  # noqa: ARG002 - the signature of the port
        snapshot: FlowSnapshot[CycleFlow],  # noqa: ARG002 - the signature of the port
        decisions: CycleDecisions,
    ) -> RiskReview[CycleOrder]:
        cycle_flow = decisions.flow
        loss_suspension = self._loss_guard.execute(cycle_flow)
        command = CheckRiskCommand(
            tuple(
                decision.intent_with(_open_intent, CloseIntent, HoldIntent, _update_intent)
                for decision in decisions.reply.response.decisions
            ),
            cycle_flow.configuration.risk_policy,
            cycle_flow.risk_state(loss_suspension=loss_suspension),
            cycle_flow.exchange,
        )
        outcomes = self._check_risk.execute(command)
        orders = tuple(CycleOrder(cycle_flow, outcome) for outcome in approved_of(outcomes))
        return RiskReview(orders, tuple(outcomes))


def _open_intent(  # noqa: PLR0913, PLR0917 - the fields of the opening the agent gives
    asset: str, side: str, margin_fraction: Decimal, leverage: int, exit_plan: DecisionExitPlanPort, confidence: int
) -> OpenIntent:
    plan = ExitPlan(exit_plan.target, exit_plan.stop, exit_plan.invalidation)
    return OpenIntent.of(asset, side, margin_fraction, leverage, confidence, plan)


def _update_intent(asset: str, change: DecisionPlanChangePort) -> UpdateIntent:
    return UpdateIntent.of(asset, change.target, change.stop, change.invalidation, remove_target=change.remove_target)
