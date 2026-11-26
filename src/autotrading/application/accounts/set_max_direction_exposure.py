from dataclasses import dataclass
from decimal import Decimal

from autotrading.application.accounts.get_account import find_account
from autotrading.application.accounts.ports import AccountRepositoryPort
from autotrading.domain.accounts.account_id import AccountId


@dataclass(frozen=True, slots=True)
class SetMaxDirectionExposureCommand:
    account_id: AccountId
    # None takes the limit away: the flows of the account open on a side whatever the others hold.
    percent: Decimal | None


class SetMaxDirectionExposureUseCase:
    """Sets or takes away the largest exposure the flows of an account may have together on one side, in percent of its
    balance read from the exchange (R5.5.5, ADR esposizione-massima-per-direzione-del-conto).

    The next cycle of every flow of the account checks its openings on the new limit.
    """

    def __init__(self, accounts: AccountRepositoryPort) -> None:
        self._accounts = accounts

    def execute(self, command: SetMaxDirectionExposureCommand) -> None:
        account = find_account(self._accounts, command.account_id)
        self._accounts.replace(account.with_max_direction_exposure(command.percent))
