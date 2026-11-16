from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from autotrading.application.flows.errors import ReconciliationAlarmNotOpenError
from autotrading.application.flows.ports import FlowAccountNamePort, ReconciliationRepositoryPort


@dataclass(frozen=True, slots=True)
class ConfirmReconciliationCommand:
    account_id: UUID


class ConfirmReconciliationUseCase:
    """The user checked the account: its alarm closes at this moment, the balance last read becomes the reference of
    the next comparison, and the openings of its flows resume (R3.3.1).
    """

    def __init__(
        self,
        readings: ReconciliationRepositoryPort,
        accounts: FlowAccountNamePort,
        clock: Callable[[], datetime],
    ) -> None:
        self._readings = readings
        self._accounts = accounts
        self._clock = clock

    def execute(self, command: ConfirmReconciliationCommand) -> None:
        account_name = self._accounts.account_name(command.account_id)
        if not self._readings.confirm(command.account_id, self._clock()):
            raise ReconciliationAlarmNotOpenError(account_name)
        self._take_balance_read_as_reference(command.account_id)

    def _take_balance_read_as_reference(self, account_id: UUID) -> None:
        reading = self._readings.last_reading(account_id)
        if reading is None:
            return
        self._readings.save_reading(reading.confirmed())
