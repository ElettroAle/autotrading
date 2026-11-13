from autotrading.adapters.outbound.hyperliquid.activity import HyperliquidAccountActivityAdapter
from autotrading.adapters.outbound.hyperliquid.configuration import _HyperliquidSettings
from autotrading.adapters.outbound.hyperliquid.exchange import HyperliquidExchangeAdapter
from autotrading.adapters.outbound.hyperliquid.executions import HyperliquidAccountExecutionsAdapter
from autotrading.adapters.outbound.hyperliquid.market_data import (
    HyperliquidMarketDataAdapter,
    HyperliquidPriceHistoryAdapter,
)
from autotrading.adapters.outbound.hyperliquid.markets import HyperliquidMarketsAdapter
from autotrading.adapters.outbound.hyperliquid.orders import HyperliquidOrderExchangeAdapter
from autotrading.domain.accounts.exchange_network import ExchangeNetwork

type HyperliquidAdaptersOfInstallation = tuple[
    dict[str, HyperliquidExchangeAdapter],
    dict[str, HyperliquidMarketsAdapter],
    dict[str, HyperliquidOrderExchangeAdapter],
    dict[str, HyperliquidAccountActivityAdapter],
    dict[str, HyperliquidAccountExecutionsAdapter],
    HyperliquidPriceHistoryAdapter,
    HyperliquidMarketDataAdapter,
]


def hyperliquid_adapters(network: ExchangeNetwork) -> HyperliquidAdaptersOfInstallation:
    """The adapters by exchange name, for the use cases that pick the exchange of an account, and the market data."""
    settings = _HyperliquidSettings(network)
    testnet = settings.testnet
    return (
        {settings.name: HyperliquidExchangeAdapter.for_network(testnet=testnet)},
        {settings.name: HyperliquidMarketsAdapter.for_network(testnet=testnet)},
        {settings.name: HyperliquidOrderExchangeAdapter.for_network(testnet=testnet)},
        {settings.name: HyperliquidAccountActivityAdapter.for_network(testnet=testnet)},
        {settings.name: HyperliquidAccountExecutionsAdapter.for_network(testnet=testnet)},
        HyperliquidPriceHistoryAdapter.for_network(testnet=testnet),
        HyperliquidMarketDataAdapter.for_network(testnet=testnet),
    )
