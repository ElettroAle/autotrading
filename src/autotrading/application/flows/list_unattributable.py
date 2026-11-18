from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.ports import FlowAccountNamePort, ReconciliationRepositoryPort
from autotrading.domain.flows.unattributable_page import UnattributableCursor, UnattributableFilter, UnattributablePage


@dataclass(frozen=True, slots=True)
class ListUnattributableCommand:
    account_id: UUID
    criteria: UnattributableFilter
    after: UnattributableCursor | None = None


class ListUnattributableUseCase:
    """The record of what no flow explains on an account of the tenant, newest first, by pages, with the net of the
    changes of the balance of the filter (R1.6.2, ADR movimenti-non-spiegati-nel-riquadro-del-conto).
    """

    def __init__(self, readings: ReconciliationRepositoryPort, accounts: FlowAccountNamePort) -> None:
        self._readings = readings
        self._accounts = accounts

    def execute(self, command: ListUnattributableCommand) -> UnattributablePage:
        # An account of another tenant is not found, as every account route answers (R0.1.3).
        self._accounts.account_name(command.account_id)
        return self._readings.unattributable_of(command.account_id, command.criteria, command.after)
