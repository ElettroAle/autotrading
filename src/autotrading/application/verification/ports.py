from typing import Protocol
from uuid import UUID

from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.verification.order_result import OrderResult
from autotrading.domain.verification.procedure import Opening
from autotrading.domain.verification.reading import AccountReading
from autotrading.domain.verification.verification_run import VerificationRun


class AccountReadingPort(Protocol):
    """Reads the account: what the exchange shows of it and the flows that trade on it."""

    def read(self, account_id: UUID) -> AccountReading:
        """Raises VerificationStepError when the exchange cannot be read."""
        ...

    def flow_on(self, account_id: UUID, asset: str) -> str | None:
        """The name of a flow of the account trading the asset, if any: active or paused, it compares its position
        at the next cycle (ADR 0075)."""
        ...


class OrderExecutionPort(Protocol):
    """Sends the orders of the procedure, recorded with its origin and the user who launched it."""

    def open(self, account_id: UUID, opening: Opening, user_id: UserId) -> OrderResult: ...

    def close(self, account_id: UUID, coin: str, user_id: UserId) -> OrderResult: ...


class VerificationRunRepositoryPort(Protocol):
    def add(self, run: VerificationRun) -> None: ...


class VerificationPort(Protocol):
    """The worker, asked by the API to run the procedure on an account of the tenant of the request."""

    def run(self, account_id: UUID, user_id: UserId) -> VerificationRun: ...
