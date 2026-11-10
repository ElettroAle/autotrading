from dataclasses import dataclass
from uuid import UUID

from autotrading.application.orders.outcome import OrderOutcome
from autotrading.application.orders.ports import PositionClosingPort
from autotrading.domain.tenancy.user_id import UserId


@dataclass(frozen=True, slots=True)
class ClosePositionCommand:
    account_id: UUID
    coin: str
    user_id: UserId


class ClosePositionUseCase:
    """A user closes a position of an account of the tenant, whenever they want (R0.3.2).

    The worker holds the credentials and checks, under row level security, that the account belongs to the tenant:
    an account of another tenant is not found before anything is opened (ADR 0023).
    """

    def __init__(self, closing: PositionClosingPort) -> None:
        self._closing = closing

    def execute(self, command: ClosePositionCommand) -> OrderOutcome:
        return self._closing.close(command.account_id, command.coin.strip(), command.user_id)
