from decimal import Decimal

import pytest
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL

from autotrading.adapters.configuration.errors import InvalidConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.hyperliquid.composition import hyperliquid_order_adapters
from autotrading.domain.orders.errors import InvalidSlippageError
from autotrading.domain.orders.slippage import Slippage

SLIPPAGE = "ORDER_MAX_SLIPPAGE_PERCENT"


def _source(**values: str) -> ConfigurationSource:
    return ConfigurationSource({"APP_ENVIRONMENT": "dev"} | values)


@pytest.mark.parametrize(("environment", "url"), [("dev", TESTNET_API_URL), ("prod", MAINNET_API_URL)])
def test_the_orders_go_to_the_network_of_the_installation(environment: str, url: str) -> None:
    exchanges, _ = hyperliquid_order_adapters(_source(APP_ENVIRONMENT=environment))

    assert {name: exchange.base_url for name, exchange in exchanges.items()} == {"Hyperliquid": url}


@pytest.mark.parametrize(
    ("configured", "percent"),
    [({}, Decimal(5)), ({SLIPPAGE: "  "}, Decimal(5)), ({SLIPPAGE: " 1.5 "}, Decimal("1.5"))],
    ids=["absent", "blank", "declared"],
)
def test_the_slippage_is_five_percent_unless_the_installation_declares_it(
    configured: dict[str, str], percent: Decimal
) -> None:
    _, slippage = hyperliquid_order_adapters(_source(**configured))

    assert slippage == Slippage.percent(percent)


@pytest.mark.parametrize("text", ["five", "NaN", "Infinity"])
def test_a_slippage_that_is_not_a_number_is_an_invalid_configuration(text: str) -> None:
    with pytest.raises(InvalidConfigurationError) as raised:
        hyperliquid_order_adapters(_source(**{SLIPPAGE: text}))

    assert raised.value.name == SLIPPAGE


@pytest.mark.parametrize("text", ["0", "-1", "100", "250"])
def test_a_slippage_outside_its_range_is_refused(text: str) -> None:
    with pytest.raises(InvalidSlippageError):
        hyperliquid_order_adapters(_source(**{SLIPPAGE: text}))
