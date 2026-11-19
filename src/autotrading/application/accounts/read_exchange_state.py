from collections.abc import Mapping
from dataclasses import dataclass

from autotrading.application.accounts.get_account import find_account
from autotrading.application.accounts.ports import AccountRepositoryPort, CredentialOpenerPort, ExchangePort
from autotrading.application.accounts.verification import read_expiry_proving, read_state_proving, supported_exchange
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.credentials import Credentials


@dataclass(frozen=True, slots=True)
class ReadExchangeStateCommand:
    account_id: AccountId


class ReadExchangeStateUseCase:
    """In the worker: opens the stored credentials of an account and reads its state on the exchange (ADR 0021).

    Every reading checks the credentials: an exchange that tells their expiry has it read again, and kept when it
    changed (R6.2.2, ADR scadenza-delle-chiavi-letta-o-indicata).
    """

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
        state = read_state_proving(exchange, credentials)
        self._refresh_expiry(account, exchange, credentials)
        return state

    def _refresh_expiry(self, account: Account, exchange: ExchangePort, credentials: Credentials) -> None:
        if not exchange.reads_credential_expiry():
            return
        expiry = read_expiry_proving(exchange, credentials)
        if expiry != account.expiry:
            self._accounts.replace(account.with_expiry(expiry))
