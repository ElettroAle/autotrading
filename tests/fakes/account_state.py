from collections.abc import Callable

from autotrading.application.accounts.errors import WorkerUnavailableError
from autotrading.application.accounts.read_exchange_state import ReadExchangeStateCommand, ReadExchangeStateUseCase
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
