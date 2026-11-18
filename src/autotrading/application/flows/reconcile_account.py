from dataclasses import dataclass

from autotrading.application.flows.ports import (
    AccountActivityPort,
    AlertResolutionPort,
    FlowRepositoryPort,
    OutsideClosingRecorderPort,
    ProtectionClosingRecorderPort,
    ReconciliationAlarmPorts,
    ReconciliationRepositoryPort,
)
from autotrading.application.flows.record_account_executions import (
    RecordAccountExecutionsCommand,
    RecordAccountExecutionsUseCase,
)
from autotrading.domain.flows.account_reconciliation import AccountReconciliation, OutsideClosing
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from autotrading.domain.flows.unattributable import UnattributableItem


@dataclass(frozen=True, slots=True)
class ReconcileAccountCommand:
    flow_id: FlowId


@dataclass(frozen=True, slots=True)
class ReconciliationOutcome:
    """What this reconciliation found for the first time, for the notifications of the cycle (R1.8.2)."""

    new_items: tuple[UnattributableItem, ...]
    closed_outside: tuple[OutsideClosing, ...]


class ReconcileAccountUseCase:
    """At every cycle of a flow, what the account of the flow shows that no flow explains (R1.6.2), and whether its
    balance is the one expected (R3.3.1).

    The new executions of the account enter the ledger first (ADR 0063). Every case is recorded once; a position
    of a flow closed outside the platform, or by its stop loss or take profit (R3.1.2), enters the history of the flow.
    A balance beyond the threshold of the account opens an alarm, told to the user once while it stays open. A position
    no flow explains that is no longer open resolves, with its alert (R6.2.3).
    Nothing on the exchange is touched but the protections such a closing leaves, and the cycles keep running.
    """

    def __init__(  # noqa: PLR0913, PLR0917 - the readings it compares and where each outcome goes
        self,
        flows: FlowRepositoryPort,
        activity: AccountActivityPort,
        readings: ReconciliationRepositoryPort,
        closed_positions: OutsideClosingRecorderPort,
        record_executions: RecordAccountExecutionsUseCase,
        protection_closings: ProtectionClosingRecorderPort,
        alarms: ReconciliationAlarmPorts,
        alerts: AlertResolutionPort,
    ) -> None:
        self._flows = flows
        self._activity = activity
        self._readings = readings
        self._closed_positions = closed_positions
        self._record_executions = record_executions
        self._protection_closings = protection_closings
        self._alarms = alarms
        self._alerts = alerts

    def execute(self, command: ReconcileAccountCommand) -> ReconciliationOutcome:
        account_id = self._flows.get(command.flow_id).assigned_account_id
        threshold = self._alarms.thresholds.deviation_threshold(account_id)
        recorded = self._record_executions.execute(RecordAccountExecutionsCommand(account_id))
        reconciliation = AccountReconciliation.of(
            account_id,
            (flow for flow in self._flows.list() if flow.belongs_to(account_id)),
            self._activity.execute(account_id),
            self._readings.last_reading(account_id),
            recorded,
            threshold,
        )
        new_items = tuple(item for item in reconciliation.items if self._readings.record(item))
        self._readings.resolve_positions(account_id, reconciliation.open_assets)
        self._alerts.resolve_positions_gone(account_id, reconciliation.open_assets)
        for closing in reconciliation.closed_outside:
            self._closed_positions.execute(closing)
        for protection_closing in reconciliation.closed_by_protection:
            self._protection_closings.execute(protection_closing)
        self._raise(reconciliation.alarm)
        self._readings.save_reading(reconciliation.reading)
        return ReconciliationOutcome(new_items, reconciliation.closed_outside)

    def _raise(self, alarm: ReconciliationAlarm | None) -> None:
        if alarm is None or not self._readings.open(alarm):
            return
        account_name = self._alarms.accounts.account_name(alarm.account_id)
        self._alarms.notice.execute(alarm.account_id, account_name, alarm.read_balance, alarm.expected_balance)
