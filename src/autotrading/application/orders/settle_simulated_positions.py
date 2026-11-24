import logging
from collections.abc import Callable
from dataclasses import dataclass

from autotrading.application.orders.errors import ExchangeRejectedOrderError
from autotrading.application.orders.ports import MarketReaderPort, SimulatedSettlementPort, SimulatedTenantsPort
from autotrading.domain.orders.market import Market
from autotrading.domain.tenancy.tenant_id import TenantId

operations = logging.getLogger("autotrading.orders")


@dataclass(frozen=True, slots=True)
class SettleSimulatedPositionsCommand:
    """A round of the worker: the simulated positions of every tenant on the prices of now."""


class SettleSimulatedPositionsUseCase:
    """Closes the simulated positions whose stop loss, take profit or liquidation the real prices reached, tenant by
    tenant, and shows the others at those prices (R6.3.2, ADR exchange-simulato-con-porte-di-lettura-e-scrittura).

    The market of each asset is read once per round, from the reading of the real market; an asset the real market no
    longer trades is left as it is.
    """

    def __init__(
        self,
        market: MarketReaderPort,
        tenants: SimulatedTenantsPort,
        settlement_of: Callable[[TenantId], SimulatedSettlementPort],
    ) -> None:
        self._market = market
        self._tenants = tenants
        self._settlement_of = settlement_of

    def execute(self, command: SettleSimulatedPositionsCommand) -> int:  # noqa: ARG002 - a round carries no data
        markets: dict[str, Market | None] = {}
        settled = sum(
            self._settled(self._settlement_of(tenant_id), markets) for tenant_id in self._tenants.tenant_ids()
        )
        if settled:
            operations.info("posizioni simulate chiuse sui prezzi reali", extra={"positions": settled})
        return settled

    def _settled(self, settlement: SimulatedSettlementPort, markets: dict[str, Market | None]) -> int:
        coins = settlement.open_coins()
        if not coins:
            return 0
        read = {coin: self._market_of(coin, markets) for coin in sorted(coins)}
        return settlement.settle({coin: market for coin, market in read.items() if market is not None})

    def _market_of(self, coin: str, markets: dict[str, Market | None]) -> Market | None:
        if coin not in markets:
            markets[coin] = self._read(coin)
        return markets[coin]

    def _read(self, coin: str) -> Market | None:
        try:
            return self._market.market(coin)
        except ExchangeRejectedOrderError:
            return None
