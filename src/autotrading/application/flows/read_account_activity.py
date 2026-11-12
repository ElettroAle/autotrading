from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.ports import AccountActivityPort
from autotrading.domain.flows.account_activity import AccountActivity


@dataclass(frozen=True, slots=True)
class ReadAccountActivityCommand:
    account_id: UUID


class ReadAccountActivityUseCase:
    """In the worker: what the exchange shows of an account, for the state of its flows read by the API (R1.6.1)."""

    def __init__(self, activity: AccountActivityPort) -> None:
        self._activity = activity

    def execute(self, command: ReadAccountActivityCommand) -> AccountActivity:
        return self._activity.activity(command.account_id)
