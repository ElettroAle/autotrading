from dataclasses import dataclass

from autotrading.application.flows.ports import (
    AccountActivityPort,
    ExitPlanRepositoryPort,
    FlowLedgerPort,
    FlowProtectionLevelsPort,
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
    ledger, net of the profits it cashed out, and the changes of its capital that chain its return (R1.6.1, R3.1.1,
    ADR 0063, R3.4.1, R3.4.3).

    The stop and the target in force are the levels of the protections the platform recorded for the position, whatever
    their origin; the invalidation is the one of the agent (R5.5.3, ADR
    stop-e-obiettivo-in-vigore-nello-stato-della-posizione).
    """

    def __init__(
        self,
        flows: FlowRepositoryPort,
        activity: AccountActivityPort,
        ledger: FlowLedgerPort,
        exit_plans: ExitPlanRepositoryPort,
        protection_levels: FlowProtectionLevelsPort,
    ) -> None:
        self._flows = flows
        self._activity = activity
        self._ledger = ledger
        self._exit_plans = exit_plans
        self._protection_levels = protection_levels

    def execute(self, command: ReadFlowStateCommand) -> FlowState:
        flow = self._flows.get(command.flow_id)
        activity = self._activity.execute(flow.assigned_account_id)
        totals = self._ledger.totals_of((flow.id,)).get(flow.id) or FlowTotals(flow.id)
        changes = self._flows.capital_changes_of((flow.id,)).get(flow.id, ())
        return FlowState.attributed(flow, activity, totals, changes, self._exit_plans_of(flow, activity))

    def _exit_plans_of(self, flow: Flow, activity: AccountActivity) -> dict[str, ExitPlan]:
        held = flow.configuration.held(activity.positions, lambda position: position.asset)
        return {position.asset: self._plan_in_force(flow, position.asset) for position in held}

    def _plan_in_force(self, flow: Flow, asset: str) -> ExitPlan:
        plan = self._exit_plans.current(flow.id, asset) or ExitPlan()
        return plan.in_force(self._protection_levels.placed_levels(flow.id, asset))
