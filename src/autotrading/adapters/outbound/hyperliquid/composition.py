from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.hyperliquid.activity import HyperliquidAccountActivityAdapter
from autotrading.adapters.outbound.hyperliquid.configuration import _HyperliquidMetadataSettings, _order_settings_of
from autotrading.adapters.outbound.hyperliquid.exchange import (
    EXCHANGE_NAME,
    TESTNET_EXCHANGE_NAME,
    HyperliquidExchangeAdapter,
    HyperliquidSdkAdapter,
    HyperliquidTestnetExchangeAdapter,
)
from autotrading.adapters.outbound.hyperliquid.executions import HyperliquidAccountExecutionsAdapter
from autotrading.adapters.outbound.hyperliquid.market_data import (
    HyperliquidMarketDataAdapter,
    HyperliquidPriceHistoryAdapter,
)
from autotrading.adapters.outbound.hyperliquid.market_metadata import _CachedMarketMetadata, _MarketMetadata
from autotrading.adapters.outbound.hyperliquid.markets import HyperliquidMarketsAdapter
from autotrading.adapters.outbound.hyperliquid.orders import HyperliquidOrderExchangeAdapter
from autotrading.adapters.outbound.hyperliquid.protections import HyperliquidProtectionExchangeAdapter
from autotrading.application.orders.ports import ExchangeConnection
from autotrading.domain.orders.slippage import Slippage

type HyperliquidRealMarket = tuple[HyperliquidOrderExchangeAdapter, HyperliquidMarketsAdapter]
type HyperliquidAdaptersOfInstallation = tuple[
    dict[str, HyperliquidExchangeAdapter],
    dict[str, HyperliquidMarketsAdapter],
    dict[str, ExchangeConnection],
    dict[str, HyperliquidAccountActivityAdapter],
    dict[str, HyperliquidAccountExecutionsAdapter],
    HyperliquidRealMarket,
    HyperliquidPriceHistoryAdapter,
    HyperliquidMarketDataAdapter,
]


def hyperliquid_adapters() -> HyperliquidAdaptersOfInstallation:
    """The adapters by exchange name, Hyperliquid and Hyperliquid Testnet in every installation, for the use cases that
    pick the exchange of an account; the market sources read the real market (R2.3.11), and so do the readers of the
    real market without credentials, for an exchange that trades on it (ADR
    exchange-simulato-con-porte-di-lettura-e-scrittura).

    All of them share one client of the SDK, whose market metadata stay valid for an hour (Bug 635, ADR
    metadati-di-mercato-hyperliquid-riusati-dal-client-unico).
    """
    metadata = _CachedMarketMetadata(_MarketMetadata(), _HyperliquidMetadataSettings().validity_seconds)
    sdk = HyperliquidSdkAdapter(metadata)
    orders = HyperliquidOrderExchangeAdapter.for_network(testnet=False, sdk=sdk)
    testnet_orders = HyperliquidOrderExchangeAdapter.for_network(testnet=True, sdk=sdk)
    markets = HyperliquidMarketsAdapter.for_network(testnet=False, sdk=sdk)
    return (
        {
            EXCHANGE_NAME: HyperliquidExchangeAdapter(sdk=sdk),
            TESTNET_EXCHANGE_NAME: HyperliquidTestnetExchangeAdapter(sdk),
        },
        {
            EXCHANGE_NAME: markets,
            TESTNET_EXCHANGE_NAME: HyperliquidMarketsAdapter.for_network(testnet=True, sdk=sdk),
        },
        {
            EXCHANGE_NAME: ExchangeConnection(
                orders, orders, HyperliquidProtectionExchangeAdapter.for_network(testnet=False, sdk=sdk)
            ),
            TESTNET_EXCHANGE_NAME: ExchangeConnection(
                testnet_orders, testnet_orders, HyperliquidProtectionExchangeAdapter.for_network(testnet=True, sdk=sdk)
            ),
        },
        {
            EXCHANGE_NAME: HyperliquidAccountActivityAdapter.for_network(testnet=False, sdk=sdk),
            TESTNET_EXCHANGE_NAME: HyperliquidAccountActivityAdapter.for_network(testnet=True, sdk=sdk),
        },
        {
            EXCHANGE_NAME: HyperliquidAccountExecutionsAdapter.for_network(testnet=False, sdk=sdk),
            TESTNET_EXCHANGE_NAME: HyperliquidAccountExecutionsAdapter.for_network(testnet=True, sdk=sdk),
        },
        (orders, markets),
        HyperliquidPriceHistoryAdapter.for_network(testnet=False, sdk=sdk),
        HyperliquidMarketDataAdapter.for_network(testnet=False, sdk=sdk),
    )


def hyperliquid_slippage_adapters(source: ConfigurationSource) -> Slippage:
    """The largest slippage of the market orders the order use cases send to the exchange."""
    return _order_settings_of(source).slippage
