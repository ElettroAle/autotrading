from collections.abc import Callable
from decimal import Decimal
from uuid import UUID

from autotrading.application.verification.errors import VerificationWorkerUnavailableError
from autotrading.application.verification.run_exchange_verification import (
    RunExchangeVerificationCommand,
    RunExchangeVerificationUseCase,
)
from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.verification.verification_run import VerificationRun


class FakeVerificationAdapter:
    """The worker reached in process instead of over HTTP: the same use case the worker runs, for the same tenant."""

    def __init__(self, worker: Callable[[], RunExchangeVerificationUseCase]) -> None:
        self._worker = worker
        self.reachable = True

    def run(self, account_id: UUID, user_id: UserId, amount: Decimal | None) -> VerificationRun:
        if not self.reachable:
            raise VerificationWorkerUnavailableError
        return self._worker().execute(RunExchangeVerificationCommand(account_id, user_id, amount))
