import logging
from collections.abc import Sequence
from contextlib import ExitStack
from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.ports import (
    AccountReconciliationIntervalPort,
    ClockPort,
    FlowLockPort,
    FlowRepositoryPort,
    ReconciliationRepositoryPort,
)
from autotrading.application.flows.reconcile_account_for_cycle import (
    ReconcileAccountForCycleCommand,
    ReconcileAccountForCycleUseCase,
)
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.flow import Flow

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class ReconcileOpenAccountsCommand:
    """A check of the worker: the accounts of the tenant whose flows held open positions at their last reading."""


@dataclass(frozen=True, slots=True)
class OpenAccountReadings:
    """What tells whether an account is due, without asking the exchange: its last reading, its interval and the
    clock."""

    readings: ReconciliationRepositoryPort
    intervals: AccountReconciliationIntervalPort
    clock: ClockPort


class ReconcileOpenAccountsUseCase:
    """Reconciles, between the cycles, every account of the flows in use whose flows held open positions at the last
    reading, once the interval of the account has passed since (Bug 778, ADR
    riconciliazione-periodica-dei-conti-con-posizioni-aperte): a stop loss, a take profit, a liquidation or a closing
    outside the platform enters the history without waiting for the next cycle.

    The flows of the account are held as their cycles hold them, without waiting: an account with a cycle running is
    left to it, which reconciles it itself. An exchange that does not answer leaves the account for the next check, and
    an error on one account leaves the others going: no flow is paused from here.
    """

    def __init__(
        self,
        flows: FlowRepositoryPort,
        due: OpenAccountReadings,
        lock: FlowLockPort,
        reconcile: ReconcileAccountForCycleUseCase,
    ) -> None:
        self._flows = flows
        self._due = due
        self._lock = lock
        self._reconcile = reconcile

    def execute(self, command: ReconcileOpenAccountsCommand) -> None:  # noqa: ARG002 - a check carries no data
        for account_id, flows in self._flows_by_account().items():
            self._reconcile_apart(account_id, flows)

    def _flows_by_account(self) -> dict[UUID, list[Flow]]:
        by_account: dict[UUID, list[Flow]] = {}
        for flow in self._flows.list():
            if flow.status.holds_account:
                by_account.setdefault(flow.assigned_account_id, []).append(flow)
        return by_account

    def _reconcile_apart(self, account_id: UUID, flows: Sequence[Flow]) -> None:
        try:
            if self._is_due(account_id):
                self._reconcile_unless_cycling(flows)
        except AutotradingError as error:
            operations.warning(
                "riconciliazione periodica del conto interrotta",
                extra={"account_id": str(account_id), "error": str(error)},
            )

    def _is_due(self, account_id: UUID) -> bool:
        reading = self._due.readings.last_reading(account_id)
        if reading is None:
            return False
        interval = self._due.intervals.reconciliation_interval(account_id)
        return reading.due_for_reconciliation(self._due.clock.now(), interval)

    def _reconcile_unless_cycling(self, flows: Sequence[Flow]) -> None:
        with ExitStack() as held:
            if not all(held.enter_context(self._lock.hold(flow.id.value)) for flow in flows):
                return
            self._reconcile.execute(ReconcileAccountForCycleCommand(flows[0].id))
