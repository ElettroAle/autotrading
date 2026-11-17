from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from autotrading.application.flows.ports import (
    FlowAccountNamePort,
    FlowRepositoryPort,
    OpeningsSuspensionPort,
    ReconciliationRepositoryPort,
)
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.openings_suspension import OpeningsSuspension


@dataclass(frozen=True, slots=True)
class ReadOpeningsSuspensionCommand:
    flow_id: FlowId


class ReadOpeningsSuspensionUseCase:
    """The suspension of the openings of a flow of the tenant in force now, or None: for maximum loss (R3.2.2) or for
    the alarm of reconciliation open on its account (R3.3.1, R3.3.2), the same one a cycle blocks the openings with.

    A suspension the next day reads lifted from its midnight, before any cycle writes it.
    """

    def __init__(
        self,
        flows: FlowRepositoryPort,
        openings: OpeningsSuspensionPort,
        readings: ReconciliationRepositoryPort,
        accounts: FlowAccountNamePort,
        clock: Callable[[], datetime],
    ) -> None:
        self._flows = flows
        self._openings = openings
        self._readings = readings
        self._accounts = accounts
        self._clock = clock

    def execute(self, command: ReadOpeningsSuspensionCommand) -> OpeningsSuspension | None:
        flow = self._flows.get(command.flow_id)
        loss = self._openings.status(flow.id.value).at(self._clock(), flow.configuration.openings_resume).suspension
        return OpeningsSuspension.first_of(loss, self._alarm_suspension(flow.assigned_account_id))

    def _alarm_suspension(self, account_id: UUID) -> OpeningsSuspension | None:
        alarm = self._readings.open_alarm(account_id)
        if alarm is None:
            return None
        return alarm.suspension(self._accounts.account_name(account_id))
