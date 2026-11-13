from dataclasses import dataclass
from uuid import UUID

from autotrading.application.orders.ports import ManualClosingRecorderPort, PositionClosingPort
from autotrading.domain.orders.order_outcome import OrderOutcome
from autotrading.domain.tenancy.user_id import UserId


@dataclass(frozen=True, slots=True)
class ClosePositionCommand:
    account_id: UUID
    coin: str
    user_id: UserId


class ClosePositionUseCase:
    """A user closes a position of an account of the tenant, whenever they want (R0.3.2).

    The worker holds the credentials and checks, under row level security, that the account belongs to the tenant:
    an account of another tenant is not found before anything is opened (ADR 0023). What the exchange executed then
    enters the history of the flow that trades the asset (ADR 0061).
    """

    def __init__(self, closing: PositionClosingPort, history: ManualClosingRecorderPort) -> None:
        self._closing = closing
        self._history = history

    def execute(self, command: ClosePositionCommand) -> OrderOutcome:
        coin = command.coin.strip()
        outcome = self._closing.close(command.account_id, coin, command.user_id)
        self._history.execute(command.account_id, coin, outcome)
        return outcome
