from dataclasses import dataclass

from autotrading.application.flows.ports import (
    AccountActivityPort,
    ExitPlanRepositoryPort,
    FlowLedgerPort,
    FlowRepositoryPort,
)
from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.exit_plan import ExitPlan
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.ledger import FlowTotals


@dataclass(frozen=True, slots=True)
class ReadFlowStateCommand:
    flow_id: FlowId


class ReadFlowStateUseCase:
    """A flow's positions from what the exchange shows now, each with its exit plan in force, its money from its
    ledger net of the profits it cashed out, and the changes of its capital that chain its return (R1.6.1, R3.1.1,
    ADR 0063, R3.4.1, R3.4.3).
    """

    def __init__(
        self,
        flows: FlowRepositoryPort,
        activity: AccountActivityPort,
        ledger: FlowLedgerPort,
        exit_plans: ExitPlanRepositoryPort,
    ) -> None:
        self._flows = flows
        self._activity = activity
        self._ledger = ledger
        self._exit_plans = exit_plans

    def execute(self, command: ReadFlowStateCommand) -> FlowState:
        flow = self._flows.get(command.flow_id)
        activity = self._activity.execute(flow.assigned_account_id)
        totals = self._ledger.totals_of((flow.id,)).get(flow.id) or FlowTotals(flow.id)
        changes = self._flows.capital_changes_of((flow.id,)).get(flow.id, ())
        return FlowState.attributed(flow, activity, totals, self._exit_plans_of(flow, activity), changes)

    def _exit_plans_of(self, flow: Flow, activity: AccountActivity) -> dict[str, ExitPlan]:
        held = flow.configuration.held(activity.positions, lambda position: position.asset)
        plans = {position.asset: self._exit_plans.current(flow.id, position.asset) for position in held}
        return {asset: plan for asset, plan in plans.items() if plan is not None}
