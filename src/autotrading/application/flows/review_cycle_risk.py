from decimal import Decimal
from uuid import UUID

from autotrading.application.flows.check_risk import CheckRiskCommand, CheckRiskUseCase
from autotrading.application.flows.ports import (
    CycleDecisions,
    DecisionExitPlanPort,
    DecisionPlanChangePort,
    FlowLossGuardPort,
    FlowSnapshot,
    OpeningBlockedNoticePort,
    OpeningReducedNoticePort,
    RiskReview,
)
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_order import CycleOrder
from autotrading.domain.flows.exit_plan import ExitPlan
from autotrading.domain.flows.opening_review import blocked_openings, reduced_openings
from autotrading.domain.flows.risk_outcome import ApprovedClose, RiskOutcome, approved_of
from autotrading.domain.flows.trade_intent import CloseIntent, HoldIntent, OpenIntent, ReverseIntent, UpdateIntent


class ReviewCycleRiskUseCase:
    """The decisions of the agent through the risk check of the flow, on the exchange of its account
    (R1.5.1-R1.5.4), with the minimum confidence of the flow for the openings (R3.1.4).

    The guard of the losses comes first: openings suspended for maximum loss are blocked by the check (R3.2.2). Every
    opening reduced or blocked is told before the orders go (R3.5.1). The opening of a reversal waits for the close of
    its position, which goes with the orders (R1.4.10).
    """

    def __init__(
        self,
        check_risk: CheckRiskUseCase,
        loss_guard: FlowLossGuardPort,
        reduced_notice: OpeningReducedNoticePort,
        blocked_notice: OpeningBlockedNoticePort,
    ) -> None:
        self._check_risk = check_risk
        self._loss_guard = loss_guard
        self._reduced_notice = reduced_notice
        self._blocked_notice = blocked_notice

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
                decision.intent_with(_open_intent, CloseIntent, HoldIntent, _update_intent, _reverse_intent)
                for decision in decisions.reply.response.decisions
            ),
            cycle_flow.configuration.risk_policy,
            cycle_flow.risk_state(loss_suspension=loss_suspension),
            cycle_flow.exchange,
        )
        outcomes = self._check_risk.execute(command)
        self._tell_openings(cycle_flow, command, outcomes)
        orders = tuple(CycleOrder(cycle_flow, outcome) for outcome in approved_of(outcomes))
        return RiskReview(orders, tuple(outcomes), reversing=_reversing(outcomes))

    def _tell_openings(
        self, cycle_flow: CycleFlow, command: CheckRiskCommand, outcomes: tuple[RiskOutcome, ...]
    ) -> None:
        flow_id, flow_name = cycle_flow.flow.id.value, cycle_flow.flow.name.value
        for reduction in reduced_openings(command.intents, outcomes, command.state.funds):
            self._reduced_notice.execute(
                flow_id, flow_name, reduction.asset, reduction.requested_margin, reduction.approved_margin
            )
        for blocked in blocked_openings(command.intents, outcomes):
            self._blocked_notice.execute(flow_id, flow_name, blocked.asset, blocked.cause)


def _open_intent(  # noqa: PLR0913, PLR0917 - the fields of the opening the agent gives
    asset: str, side: str, margin_fraction: Decimal, leverage: int, exit_plan: DecisionExitPlanPort, confidence: int
) -> OpenIntent:
    plan = ExitPlan(exit_plan.target, exit_plan.stop, exit_plan.invalidation)
    return OpenIntent.of(asset, side, margin_fraction, leverage, confidence, plan)


def _update_intent(asset: str, change: DecisionPlanChangePort) -> UpdateIntent:
    return UpdateIntent.of(asset, change.target, change.stop, change.invalidation, remove_target=change.remove_target)


def _reverse_intent(
    asset: str, margin_fraction: Decimal, leverage: int, exit_plan: DecisionExitPlanPort, confidence: int
) -> ReverseIntent:
    plan = ExitPlan(exit_plan.target, exit_plan.stop, exit_plan.invalidation)
    return ReverseIntent(asset, margin_fraction, leverage, confidence, plan)


def _reversing(outcomes: tuple[RiskOutcome, ...]) -> bool:
    return any(isinstance(outcome, ApprovedClose) and outcome.reopening is not None for outcome in outcomes)
