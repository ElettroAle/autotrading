from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from autotrading.application.flows.ports import AccountDeviationThresholdPort, ReconciliationRepositoryPort
from autotrading.domain.flows.balance_comparison import BalanceComparison
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm


@dataclass(frozen=True, slots=True)
class ReadAccountReconciliationCommand:
    account_id: UUID


@dataclass(frozen=True, slots=True)
class AccountReconciliationStatus:
    """Whether the balance of an account is the expected one: the threshold of the account, the last comparison of its
    balance, if any, and the alarm still open, if any (R3.3.1).
    """

    threshold_percent: Decimal
    last_comparison: BalanceComparison | None
    open_alarm: ReconciliationAlarm | None

    @property
    def aligned(self) -> bool:
        return self.open_alarm is None


class ReadAccountReconciliationUseCase:
    """The reconciliation of the balance of an account as its owner consults it (R3.3.1)."""

    def __init__(self, readings: ReconciliationRepositoryPort, thresholds: AccountDeviationThresholdPort) -> None:
        self._readings = readings
        self._thresholds = thresholds

    def execute(self, command: ReadAccountReconciliationCommand) -> AccountReconciliationStatus:
        threshold = self._thresholds.deviation_threshold(command.account_id)
        reading = self._readings.last_reading(command.account_id)
        return AccountReconciliationStatus(
            threshold,
            None if reading is None else reading.comparison,
            self._readings.open_alarm(command.account_id),
        )
