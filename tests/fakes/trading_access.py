from uuid import UUID

from autotrading.application.orders.errors import OrderAccountNotFoundError
from autotrading.application.orders.open_trading_access import OpenTradingAccessUseCase
from autotrading.domain.orders.sealed_access import SealedAccess
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.tenancy.tenant_id import TenantId

TENANT = TenantId.new()


class FakeTradingAccessAdapter:
    """The accounts of one tenant and what signs for each of them, sealed and opened as the worker does."""

    def __init__(self) -> None:
        self.accesses: dict[UUID, TradingAccess] = {}

    def sealed_access(self, account_id: UUID) -> SealedAccess:
        access = self.accesses.get(account_id)
        if access is None:
            raise OrderAccountNotFoundError
        return SealedAccess(TENANT, account_id, access.exchange, 1, b"sealed")

    def open_access(self, sealed: SealedAccess) -> TradingAccess:
        return self.accesses[sealed.account_id]

    @property
    def use_case(self) -> OpenTradingAccessUseCase:
        return OpenTradingAccessUseCase(self, self)
