from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from autotrading.adapters.configuration.errors import InvalidConfigurationError, MissingConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.sqlalchemy.composition import (
    sqlalchemy_adapters,
    sqlalchemy_simulated_exchange_adapters,
    sqlalchemy_simulation_adapters,
)
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.simulation.simulated_account import SimulatedAccount
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.tenancy.tenant_id import TenantId

AT = datetime(2026, 11, 24, 9, 0, tzinfo=UTC)


def _database(tmp_path: Path, **overrides: str) -> ConfigurationSource:
    password = tmp_path / "password"
    password.write_text("s3cret\n", encoding="utf-8")
    values = {
        "DATABASE_HOST": "postgres",
        "DATABASE_NAME": "autotrading",
        "DATABASE_USER": "autotrading_app",
        "DATABASE_PASSWORD_FILE": str(password),
    }
    return ConfigurationSource(values | overrides)


def test_the_engine_reaches_the_declared_database_on_the_default_port(tmp_path: Path) -> None:
    url = sqlalchemy_adapters(_database(tmp_path)).url

    assert (url.host, url.port, url.database, url.username, url.password) == (
        "postgres",
        5432,
        "autotrading",
        "autotrading_app",
        "s3cret",
    )


def test_the_port_can_be_declared(tmp_path: Path) -> None:
    assert sqlalchemy_adapters(_database(tmp_path, DATABASE_PORT=" 6543 ")).url.port == 6543


@pytest.mark.parametrize("port", ["five", "0", "70000"])
def test_a_port_that_is_not_a_port_is_an_invalid_configuration(tmp_path: Path, port: str) -> None:
    with pytest.raises(InvalidConfigurationError) as raised:
        sqlalchemy_adapters(_database(tmp_path, DATABASE_PORT=port))

    assert raised.value.name == "DATABASE_PORT"


@pytest.mark.parametrize("name", ["DATABASE_HOST", "DATABASE_NAME", "DATABASE_USER", "DATABASE_PASSWORD_FILE"])
def test_the_database_must_be_declared(tmp_path: Path, name: str) -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        sqlalchemy_adapters(_database(tmp_path, **{name: ""}))

    assert raised.value.name == name


def _simulated_price(source: ConfigurationSource) -> Decimal:
    """The price a long executes at on a market priced 100000, with the slippage the installation declares."""
    execution = sqlalchemy_simulation_adapters(source)
    order = MarketOrder.opening("BTC", Direction.LONG, Decimal("0.001"), Slippage.percent(Decimal(5)))
    market = Market("BTC", max_leverage=40, size_decimals=5, mid_price=Decimal(100000), min_order_value=Decimal(10))
    return execution.market_order(SimulatedAccount(Decimal(1000), ()), market, order, 1, AT).fill.price


def test_the_simulated_exchange_executes_a_tenth_of_a_percent_away_unless_declared() -> None:
    assert _simulated_price(ConfigurationSource({})) == Decimal(100100)
    assert _simulated_price(ConfigurationSource({"SIMULATED_EXCHANGE_SLIPPAGE_PERCENT": "0.5"})) == Decimal(100500)


@pytest.mark.parametrize("slippage", ["half", "NaN", "Infinity"])
def test_a_slippage_that_is_not_a_number_is_an_invalid_configuration(slippage: str) -> None:
    with pytest.raises(InvalidConfigurationError) as raised:
        sqlalchemy_simulation_adapters(ConfigurationSource({"SIMULATED_EXCHANGE_SLIPPAGE_PERCENT": slippage}))

    assert raised.value.name == "SIMULATED_EXCHANGE_SLIPPAGE_PERCENT"


def test_the_simulated_exchange_is_offered_by_its_name_on_the_accounts_of_the_tenant() -> None:
    simulation = sqlalchemy_simulation_adapters(ConfigurationSource({}))

    simulated = sqlalchemy_simulated_exchange_adapters(create_engine("sqlite://"), simulation, TenantId.new())

    assert list(simulated) == ["simulato"]
    assert simulated["simulato"].network_name() == "simulato"
