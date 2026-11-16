from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.hyperliquid.activity import HyperliquidAccountActivityAdapter
from autotrading.adapters.outbound.hyperliquid.configuration import _order_settings_of
from autotrading.adapters.outbound.hyperliquid.exchange import (
    EXCHANGE_NAME,
    TESTNET_EXCHANGE_NAME,
    HyperliquidExchangeAdapter,
    HyperliquidTestnetExchangeAdapter,
)
from autotrading.adapters.outbound.hyperliquid.executions import HyperliquidAccountExecutionsAdapter
from autotrading.adapters.outbound.hyperliquid.market_data import (
    HyperliquidMarketDataAdapter,
    HyperliquidPriceHistoryAdapter,
)
from autotrading.adapters.outbound.hyperliquid.markets import HyperliquidMarketsAdapter
from autotrading.adapters.outbound.hyperliquid.orders import HyperliquidOrderExchangeAdapter
from autotrading.domain.orders.slippage import Slippage

type HyperliquidAdaptersOfInstallation = tuple[
    dict[str, HyperliquidExchangeAdapter],
    dict[str, HyperliquidMarketsAdapter],
    dict[str, HyperliquidOrderExchangeAdapter],
    dict[str, HyperliquidAccountActivityAdapter],
    dict[str, HyperliquidAccountExecutionsAdapter],
    HyperliquidPriceHistoryAdapter,
    HyperliquidMarketDataAdapter,
]


def hyperliquid_adapters() -> HyperliquidAdaptersOfInstallation:
    """The adapters by exchange name, Hyperliquid and Hyperliquid Testnet in every installation, for the use cases that
    pick the exchange of an account; the market sources read the real market (R2.3.11)."""
    return (
        {EXCHANGE_NAME: HyperliquidExchangeAdapter(), TESTNET_EXCHANGE_NAME: HyperliquidTestnetExchangeAdapter()},
        {
            EXCHANGE_NAME: HyperliquidMarketsAdapter.for_network(testnet=False),
            TESTNET_EXCHANGE_NAME: HyperliquidMarketsAdapter.for_network(testnet=True),
        },
        {
            EXCHANGE_NAME: HyperliquidOrderExchangeAdapter.for_network(testnet=False),
            TESTNET_EXCHANGE_NAME: HyperliquidOrderExchangeAdapter.for_network(testnet=True),
        },
        {
            EXCHANGE_NAME: HyperliquidAccountActivityAdapter.for_network(testnet=False),
            TESTNET_EXCHANGE_NAME: HyperliquidAccountActivityAdapter.for_network(testnet=True),
        },
        {
            EXCHANGE_NAME: HyperliquidAccountExecutionsAdapter.for_network(testnet=False),
            TESTNET_EXCHANGE_NAME: HyperliquidAccountExecutionsAdapter.for_network(testnet=True),
        },
        HyperliquidPriceHistoryAdapter.for_network(testnet=False),
        HyperliquidMarketDataAdapter.for_network(testnet=False),
    )


def hyperliquid_slippage_adapters(source: ConfigurationSource) -> Slippage:
    """The largest slippage of the market orders the order use cases send to the exchange."""
    return _order_settings_of(source).slippage
