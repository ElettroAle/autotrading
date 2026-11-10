from uuid import UUID

from autotrading.application.orders.errors import OrderAccountNotFoundError
from autotrading.domain.orders.trading_access import TradingAccess


class FakeTradingAccessAdapter:
    """The accounts of one tenant and what signs for each of them."""

    def __init__(self) -> None:
        self.accesses: dict[UUID, TradingAccess] = {}

    def access(self, account_id: UUID) -> TradingAccess:
        access = self.accesses.get(account_id)
        if access is None:
            raise OrderAccountNotFoundError
        return access
