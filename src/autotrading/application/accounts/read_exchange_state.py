from collections.abc import Mapping
from dataclasses import dataclass

from autotrading.application.accounts.get_account import find_account
from autotrading.application.accounts.ports import AccountRepositoryPort, CredentialOpenerPort, ExchangePort
from autotrading.application.accounts.verification import read_state_proving, supported_exchange
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_state import AccountState


@dataclass(frozen=True, slots=True)
class ReadExchangeStateCommand:
    account_id: AccountId


class ReadExchangeStateUseCase:
    """In the worker: opens the stored credentials of an account and reads its state on the exchange (ADR 0021)."""

    def __init__(
        self,
        accounts: AccountRepositoryPort,
        opener: CredentialOpenerPort,
        exchanges: Mapping[str, ExchangePort],
    ) -> None:
        self._accounts = accounts
        self._opener = opener
        self._exchanges = exchanges

    def execute(self, command: ReadExchangeStateCommand) -> AccountState:
        account = find_account(self._accounts, command.account_id)
        exchange = supported_exchange(self._exchanges, account.exchange)
        credentials = self._opener.open(account)
        return read_state_proving(exchange, credentials)
