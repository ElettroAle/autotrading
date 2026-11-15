from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from autotrading.adapters.configuration.errors import InvalidConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.hyperliquid.exchange import MAINNET, TESTNET
from autotrading.domain.accounts.exchange_network import ExchangeNetwork
from autotrading.domain.orders.slippage import Slippage

SLIPPAGE = "ORDER_MAX_SLIPPAGE_PERCENT"
NETWORK = "HYPERLIQUID_NETWORK"
# The names Hyperliquid gives its networks: the installation declares one, nothing deduces it (Bug 277).
NETWORKS = {TESTNET: ExchangeNetwork.TEST, MAINNET: ExchangeNetwork.REAL}


@dataclass(frozen=True, slots=True)
class _HyperliquidSettings:
    """The network the installation declares, never deduced from its name or from the credentials (Bug 277).

    The name is the exchange an account declares at registration: the use cases pick the adapter by it.
    """

    network: ExchangeNetwork
    name: str = "Hyperliquid"

    @property
    def testnet(self) -> bool:
        return self.network.is_test


def _settings_of(source: ConfigurationSource) -> _HyperliquidSettings:
    network = NETWORKS.get(source.value(NETWORK).lower())
    if network is None:
        raise InvalidConfigurationError(NETWORK)
    return _HyperliquidSettings(network)


@dataclass(frozen=True, slots=True)
class _HyperliquidOrderSettings:
    """How far from the current price a market order sent to the exchange may be filled."""

    slippage: Slippage


def _order_settings_of(source: ConfigurationSource) -> _HyperliquidOrderSettings:
    """Five percent unless the installation declares it; the range is a rule of the domain (Slippage)."""
    text = source.optional(SLIPPAGE)
    if text is None:
        return _HyperliquidOrderSettings(Slippage.default())
    try:
        percent = Decimal(text)
    except InvalidOperation as error:
        raise InvalidConfigurationError(SLIPPAGE) from error
    if not percent.is_finite():
        raise InvalidConfigurationError(SLIPPAGE)
    return _HyperliquidOrderSettings(Slippage.percent(percent))
