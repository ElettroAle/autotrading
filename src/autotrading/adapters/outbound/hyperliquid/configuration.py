from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from autotrading.adapters.configuration.errors import InvalidConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.domain.accounts.exchange_network import ExchangeNetwork
from autotrading.domain.orders.slippage import Slippage

SLIPPAGE = "ORDER_MAX_SLIPPAGE_PERCENT"


@dataclass(frozen=True, slots=True)
class _HyperliquidSettings:
    network: ExchangeNetwork
    slippage: Slippage


def _settings_of(source: ConfigurationSource) -> _HyperliquidSettings:
    return _HyperliquidSettings(ExchangeNetwork.of_installation(source.environment()), _slippage_of(source))


def _slippage_of(source: ConfigurationSource) -> Slippage:
    """The largest slippage of the market orders: five percent unless the installation declares it."""
    text = source.optional(SLIPPAGE)
    if text is None:
        return Slippage.default()
    try:
        percent = Decimal(text)
    except InvalidOperation as error:
        raise InvalidConfigurationError(SLIPPAGE) from error
    if not percent.is_finite():
        raise InvalidConfigurationError(SLIPPAGE)
    return Slippage.percent(percent)
