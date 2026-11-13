from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.hyperliquid.configuration import _settings_of
from autotrading.adapters.outbound.hyperliquid.orders import HyperliquidOrderExchangeAdapter
from autotrading.domain.accounts.exchange_network import ExchangeNetwork
from autotrading.domain.orders.slippage import Slippage

EXCHANGE_NAME = "Hyperliquid"


def hyperliquid_order_adapters(
    source: ConfigurationSource,
) -> tuple[dict[str, HyperliquidOrderExchangeAdapter], Slippage]:
    """Where the orders go, on the network of the installation, and how far from the price they may be filled."""
    settings = _settings_of(source)
    return order_exchanges_for(settings.network), settings.slippage


def order_exchanges_for(network: ExchangeNetwork) -> dict[str, HyperliquidOrderExchangeAdapter]:
    return {EXCHANGE_NAME: HyperliquidOrderExchangeAdapter.for_network(testnet=network.is_test)}
