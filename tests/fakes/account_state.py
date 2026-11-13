from collections.abc import Callable
from uuid import UUID

from autotrading.application.accounts.errors import (
    AccountNotFoundError,
    ExchangeUnavailableError,
    WorkerUnavailableError,
)
from autotrading.application.accounts.read_exchange_state import ReadExchangeStateCommand, ReadExchangeStateUseCase
from autotrading.application.flows.errors import FlowAccountNotFoundError, FlowExchangeUnavailableError
from autotrading.application.flows.ports import FlowBalance
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_state import AccountState


class FakeAccountStateAdapter:
    """The worker reached in process instead of over HTTP: the same use case the worker runs, for the same tenant."""

    def __init__(self, worker: Callable[[], ReadExchangeStateUseCase]) -> None:
        self._worker = worker
        self.reachable = True

    def read_state(self, account_id: AccountId) -> AccountState:
        if not self.reachable:
            raise WorkerUnavailableError
        return self._worker().execute(ReadExchangeStateCommand(account_id))

    def balance_of(self, account_id: UUID) -> FlowBalance:
        try:
            balance = self.read_state(AccountId(account_id)).balance
        except AccountNotFoundError as error:
            raise FlowAccountNotFoundError from error
        except (ExchangeUnavailableError, WorkerUnavailableError) as error:
            raise FlowExchangeUnavailableError from error
        return FlowBalance(balance.amount, balance.currency)
