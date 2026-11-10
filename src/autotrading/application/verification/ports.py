from typing import Protocol
from uuid import UUID

from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.verification.order_result import OrderResult
from autotrading.domain.verification.procedure import Opening
from autotrading.domain.verification.reading import AccountReading
from autotrading.domain.verification.verification_run import VerificationRun


class AccountReadingPort(Protocol):
    """Reads the account on the exchange; raises VerificationStepError when it cannot."""

    def read(self, account_id: UUID) -> AccountReading: ...


class OrderExecutionPort(Protocol):
    """Sends the orders of the procedure, recorded with its origin and the user who launched it."""

    def open(self, account_id: UUID, opening: Opening, user_id: UserId) -> OrderResult: ...

    def close(self, account_id: UUID, coin: str, user_id: UserId) -> OrderResult: ...


class VerificationRunRepositoryPort(Protocol):
    def add(self, run: VerificationRun) -> None: ...


class VerificationPort(Protocol):
    """The worker, asked by the API to run the procedure on an account of the tenant of the request."""

    def run(self, account_id: UUID, user_id: UserId) -> VerificationRun: ...
