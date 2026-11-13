from contextlib import AbstractContextManager
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.verification.reading import AccountReading
from autotrading.domain.verification.verification_access import SealedVerificationAccess, VerificationAccess
from autotrading.domain.verification.verification_run import VerificationRun


class AccountReadingPort(Protocol):
    """Reads what the exchange shows of the account: it is ReadAccountForVerificationUseCase."""

    def execute(self, account_id: UUID) -> AccountReading:
        """Raises VerificationAccountNotFoundError, or VerificationStepError when the exchange cannot be read."""
        ...


class VerificationAccountPort(Protocol):
    """Bound to the tenant of the request: the account as the worker opens it for the procedure."""

    def sealed_verification(self, account_id: UUID) -> SealedVerificationAccess:
        """Raises VerificationAccountNotFoundError for an account missing or of another tenant (R0.1.3)."""
        ...


class VerificationOpenerPort(Protocol):
    """In the worker: opens the sealed credentials of the account for the procedure (ADR 0007)."""

    def open_verification(self, sealed: SealedVerificationAccess) -> VerificationAccess:
        """Raises VerificationCredentialsNotOpenedError when the sealed text is of another account or no key opens
        it."""
        ...


class AccountReaderPort(Protocol):
    """An exchange: balance, available margin and positions of the account, proving the credentials still work."""

    def verification_reading(self, access: VerificationAccess) -> AccountReading:
        """Raises VerificationCredentialsRejectedError, or VerificationExchangeUnavailableError."""
        ...


class FlowsOnAccountPort(Protocol):
    """Bound to the tenant of the request: the flows that trade on the account."""

    def flow_on(self, account_id: UUID, asset: str) -> str | None:
        """The name of a flow of the account trading the asset, if any: active or paused, it compares its position
        at the next cycle (ADR 0075)."""
        ...


@dataclass(frozen=True, slots=True)
class ProcedureAsset:
    """The asset of the account the procedure trades on."""

    account_id: UUID
    coin: str


@dataclass(frozen=True, slots=True)
class ProcedureClosing:
    """The position the procedure closes, with the user who launched it."""

    account_id: UUID
    coin: str
    user_id: UserId


@dataclass(frozen=True, slots=True)
class ProcedureOpening:
    """The position the procedure opens, with the user who launched it."""

    account_id: UUID
    coin: str
    user_id: UserId
    side: str
    leverage: int
    value: Decimal


class OrderAnswerPort(Protocol):
    """What the exchange did with an order of the procedure: its fee and PnL when executed, else why not."""

    @property
    def fee(self) -> Decimal | None: ...

    @property
    def realized_pnl(self) -> Decimal | None: ...

    @property
    def exchange_message(self) -> str | None: ...

    @property
    def status(self) -> str: ...


class MinimumValuePort(Protocol):
    """It is ReadMinimumValueUseCase of the orders context, built with the failures of this context."""

    def execute(self, asset: ProcedureAsset) -> Decimal:
        """The smallest value of an order the exchange of the account accepts on the asset, read from it.
        Raises VerificationAccountNotFoundError, or VerificationStepError when the exchange cannot be read."""
        ...


class OpeningOrderPort(Protocol):
    """It is OpenVerificationPositionUseCase of the orders context, built with the failures of this context."""

    def execute(self, opening: ProcedureOpening) -> OrderAnswerPort:
        """Raises VerificationAccountNotFoundError, or VerificationStepError when the order cannot be sent."""
        ...


class ClosingOrderPort(Protocol):
    """It is CloseVerificationPositionUseCase of the orders context, built with the failures of this context."""

    def execute(self, closing: ProcedureClosing) -> OrderAnswerPort:
        """Raises VerificationAccountNotFoundError, or VerificationStepError when the order cannot be sent."""
        ...


@dataclass(frozen=True, slots=True)
class ProcedureOrders:
    """The orders of the procedure, recorded with its origin and the user who launched it, by the rules the exchange
    of the account sets (ADR 0024)."""

    minimum: MinimumValuePort
    opening: OpeningOrderPort
    closing: ClosingOrderPort


class VerificationRunRepositoryPort(Protocol):
    """The runs of the procedure: the ones recorded, and the one in progress on an asset of an account."""

    def add(self, run: VerificationRun) -> None: ...

    def running(self, account_id: UUID, coin: str) -> AbstractContextManager[None]:
        """Marks the procedure in progress on the asset of the account until the context ends, for the worker and
        the API alike (ADR 0079). Raises VerificationInProgressError when one already is."""
        ...


class VerificationPort(Protocol):
    """The worker, asked by the API to run the procedure on an account of the tenant of the request."""

    def run(self, account_id: UUID, user_id: UserId, amount: Decimal | None) -> VerificationRun: ...
