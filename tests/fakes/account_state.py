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
        balance = self._state_for_flows(account_id).balance
        return FlowBalance(balance.amount, balance.currency)

    def open_positions_of(self, account_id: UUID) -> tuple[str, ...]:
        return tuple(position.coin for position in self._state_for_flows(account_id).positions)

    def _state_for_flows(self, account_id: UUID) -> AccountState:
        try:
            return self.read_state(AccountId(account_id))
        except AccountNotFoundError as error:
            raise FlowAccountNotFoundError from error
        except (ExchangeUnavailableError, WorkerUnavailableError) as error:
            raise FlowExchangeUnavailableError from error
