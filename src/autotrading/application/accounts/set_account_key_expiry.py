from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from autotrading.application.accounts.get_account import find_account
from autotrading.application.accounts.ports import AccountRepositoryPort, ExchangePort
from autotrading.application.accounts.verification import operations, require_expiry_editable, supported_exchange
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.key_expiry import KeyExpiry


@dataclass(frozen=True, slots=True)
class SetAccountKeyExpiryCommand:
    account_id: AccountId
    # None forgets the date: the expiry is unknown again.
    expires_on: date | None


class SetAccountKeyExpiryUseCase:
    """Keeps the day the user says the credentials of an account stop working, or forgets it, when the exchange does
    not read it (R6.2.2, ADR scadenza-delle-chiavi-letta-o-indicata).

    A new date is a new expiry: the notices of the old one do not count for it (R6.2.2).
    """

    def __init__(self, accounts: AccountRepositoryPort, exchanges: Mapping[str, ExchangePort]) -> None:
        self._accounts = accounts
        self._exchanges = exchanges

    def execute(self, command: SetAccountKeyExpiryCommand) -> None:
        account = find_account(self._accounts, command.account_id)
        require_expiry_editable(supported_exchange(self._exchanges, account.exchange))
        expiry = None if command.expires_on is None else KeyExpiry.entered(command.expires_on)
        self._accounts.replace(account.with_expiry(expiry))
        operations.info("scadenza delle credenziali indicata", extra={"account_id": str(account.id.value)})
