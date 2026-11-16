from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.ports import FlowAccountNamePort, ReconciliationRepositoryPort
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm


@dataclass(frozen=True, slots=True)
class ListReconciliationAlarmsCommand:
    account_id: UUID


class ListReconciliationAlarmsUseCase:
    """Every alarm of reconciliation of an account, open and confirmed, the most recent first (R3.3.1)."""

    def __init__(self, readings: ReconciliationRepositoryPort, accounts: FlowAccountNamePort) -> None:
        self._readings = readings
        self._accounts = accounts

    def execute(self, command: ListReconciliationAlarmsCommand) -> list[ReconciliationAlarm]:
        # An account of another tenant is not found, as every account route answers (R0.1.3).
        self._accounts.account_name(command.account_id)
        return self._readings.alarms_of(command.account_id)
