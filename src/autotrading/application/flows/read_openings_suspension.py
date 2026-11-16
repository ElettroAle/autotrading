from dataclasses import dataclass

from autotrading.application.flows.ports import (
    FlowAccountNamePort,
    FlowRepositoryPort,
    ReconciliationRepositoryPort,
)
from autotrading.domain.flows.flow_id import FlowId


@dataclass(frozen=True, slots=True)
class ReadOpeningsSuspensionCommand:
    flow_id: FlowId


class ReadOpeningsSuspensionUseCase:
    """Why the openings of a flow are suspended, if they are: the alarm of reconciliation open on its account, with the
    same reason a cycle gives an opening it does not execute (R3.3.1, R3.3.2).
    """

    def __init__(
        self, flows: FlowRepositoryPort, readings: ReconciliationRepositoryPort, accounts: FlowAccountNamePort
    ) -> None:
        self._flows = flows
        self._readings = readings
        self._accounts = accounts

    def execute(self, command: ReadOpeningsSuspensionCommand) -> str | None:
        account_id = self._flows.get(command.flow_id).assigned_account_id
        alarm = self._readings.open_alarm(account_id)
        if alarm is None:
            return None
        return alarm.suspension_reason(self._accounts.account_name(account_id))
