from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from autotrading.application.flows.ports import (
    AccountActivityPort,
    ClosedPositionRepositoryPort,
    FlowLedgerPort,
    FlowRepositoryPort,
    OpenPositionRecords,
)
from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.exit_plan import ExitPlan
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.ledger import FlowTotals
from autotrading.domain.flows.reopening_block import ReopeningBlock
from autotrading.domain.flows.watched_position import WatchedPosition


@dataclass(frozen=True, slots=True)
class ReadFlowStateCommand:
    flow_id: FlowId


@dataclass(frozen=True, slots=True)
class ClosingReadings:
    """The closed positions of the flows and the clock the blocks of the openings after consecutive losses are read
    with (R5.5.2).
    """

    positions: ClosedPositionRepositoryPort
    clock: Callable[[], datetime]


class ReadFlowStateUseCase:
    """A flow's positions from what the exchange shows now, each with its exit plan in force, its money from its
    ledger, net of the profits it cashed out, and the changes of its capital that chain its return (R1.6.1, R3.1.1,
    ADR 0063, R3.4.1, R3.4.3).

    The stop and the target in force are the levels of the protections the platform recorded for the position, whatever
    their origin; the invalidation is the one of the agent (R5.5.3, ADR
    stop-e-obiettivo-in-vigore-nello-stato-della-posizione). The largest profit a position reached comes only for a flow
    whose stop follows the price, the only one the platform watches (R5.5.1, ADR
    massimo-profitto-raggiunto-nello-stato-della-posizione). The blocks of the openings after consecutive losses in
    force now come only for a flow with the limit, the only one whose closings are read (R5.5.2, ADR
    controllo-delle-riaperture-dopo-perdite-consecutive).
    """

    def __init__(
        self,
        flows: FlowRepositoryPort,
        activity: AccountActivityPort,
        ledger: FlowLedgerPort,
        records: OpenPositionRecords,
        closings: ClosingReadings,
    ) -> None:
        self._flows = flows
        self._activity = activity
        self._ledger = ledger
        self._records = records
        self._closings = closings

    def execute(self, command: ReadFlowStateCommand) -> FlowState:
        flow = self._flows.get(command.flow_id)
        activity = self._activity.execute(flow.assigned_account_id)
        totals = self._ledger.totals_of((flow.id,)).get(flow.id) or FlowTotals(flow.id)
        changes = self._flows.capital_changes_of((flow.id,)).get(flow.id, ())
        plans = self._exit_plans_of(flow, activity)
        state = FlowState.attributed(flow, activity, totals, changes, plans)
        return state.watching(self._watched_of(flow)).blocking(self._reopening_blocks_of(flow))

    def _exit_plans_of(self, flow: Flow, activity: AccountActivity) -> dict[str, ExitPlan]:
        held = flow.configuration.held(activity.positions, lambda position: position.asset)
        return {position.asset: self._plan_in_force(flow, position.asset) for position in held}

    def _plan_in_force(self, flow: Flow, asset: str) -> ExitPlan:
        plan = self._records.exit_plans.current(flow.id, asset) or ExitPlan()
        return plan.in_force(self._records.protection_levels.placed_levels(flow.id, asset))

    def _watched_of(self, flow: Flow) -> dict[str, WatchedPosition]:
        if not flow.configuration.trailing_stop.active:
            return {}
        return {position.asset: position for position in self._records.watched.watched_of(flow.id)}

    def _reopening_blocks_of(self, flow: Flow) -> tuple[ReopeningBlock, ...]:
        limit = flow.configuration.consecutive_loss_limit
        if limit is None:
            return ()
        now = self._closings.clock()
        closed = self._closings.positions.closed_within(flow.id, limit.window(now))
        return ReopeningBlock.in_force(limit, closed, now)
