from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from autotrading.adapters.configuration.errors import InvalidConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.domain.accounts.exchange_network import ExchangeNetwork
from autotrading.domain.orders.slippage import Slippage

SLIPPAGE = "ORDER_MAX_SLIPPAGE_PERCENT"


@dataclass(frozen=True, slots=True)
class _HyperliquidSettings:
    """The network chosen by the installation, never deduced from the credentials (ADR 0087).

    The name is the exchange an account declares at registration: the use cases pick the adapter by it.
    """

    network: ExchangeNetwork
    name: str = "Hyperliquid"

    @property
    def testnet(self) -> bool:
        return self.network.is_test


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
