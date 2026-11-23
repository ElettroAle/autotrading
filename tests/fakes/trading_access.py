from uuid import UUID

from autotrading.application.orders.errors import OrderAccountNotFoundError
from autotrading.application.orders.open_trading_access import OpenTradingAccessUseCase
from autotrading.domain.errors import AutotradingError
from autotrading.domain.orders.sealed_access import SealedAccess
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.tenancy.tenant_id import TenantId

TENANT = TenantId.new()


class AccountsUnavailableError(AutotradingError):
    """The accounts of the tenant cannot be read for a moment: a temporary error of the access to the account."""

    status_code = 503

    def __init__(self) -> None:
        super().__init__("conti non raggiungibili")


class FakeTradingAccessAdapter:
    """The accounts of one tenant and what signs for each of them, sealed and opened as the worker does."""

    def __init__(self) -> None:
        self.accesses: dict[UUID, TradingAccess] = {}
        # The next openings of the access that fail with a temporary error.
        self.unreached_openings = 0

    def sealed_access(self, account_id: UUID) -> SealedAccess:
        if self.unreached_openings > 0:
            self.unreached_openings -= 1
            raise AccountsUnavailableError
        access = self.accesses.get(account_id)
        if access is None:
            raise OrderAccountNotFoundError
        return SealedAccess(TENANT, account_id, access.exchange, 1, b"sealed")

    def open_access(self, sealed: SealedAccess) -> TradingAccess:
        return self.accesses[sealed.account_id]

    @property
    def use_case(self) -> OpenTradingAccessUseCase:
        return OpenTradingAccessUseCase(self, self)
