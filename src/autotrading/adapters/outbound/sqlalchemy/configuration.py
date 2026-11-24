from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from autotrading.adapters.configuration.errors import InvalidConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.domain.orders.slippage import Slippage

DEFAULT_PORT = 5432
HIGHEST_PORT = 65535
PORT = "DATABASE_PORT"
SIMULATION_SLIPPAGE = "SIMULATED_EXCHANGE_SLIPPAGE_PERCENT"
# A tenth of a percent unless the installation declares it: about what a market order of the size of a flow moves the
# price of a liquid asset.
DEFAULT_SIMULATION_SLIPPAGE_PERCENT = Decimal("0.1")


@dataclass(frozen=True, slots=True)
class _SqlAlchemySettings:
    host: str
    port: int
    name: str
    user: str
    password: str = field(repr=False)


def _settings_of(source: ConfigurationSource) -> _SqlAlchemySettings:
    return _SqlAlchemySettings(
        host=source.value("DATABASE_HOST"),
        port=_port_of(source.optional(PORT)),
        name=source.value("DATABASE_NAME"),
        user=source.value("DATABASE_USER"),
        password=source.secret("DATABASE_PASSWORD"),
    )


def _port_of(text: str | None) -> int:
    if text is None:
        return DEFAULT_PORT
    if not text.isdigit() or not 0 < int(text) <= HIGHEST_PORT:
        raise InvalidConfigurationError(PORT)
    return int(text)


@dataclass(frozen=True, slots=True)
class _SqlAlchemySimulationSettings:
    """How far from the current price the simulated exchange executes a market order (R6.3.2)."""

    slippage: Slippage


def _simulation_settings_of(source: ConfigurationSource) -> _SqlAlchemySimulationSettings:
    """The range is a rule of the domain (Slippage)."""
    text = source.optional(SIMULATION_SLIPPAGE)
    if text is None:
        return _SqlAlchemySimulationSettings(Slippage.percent(DEFAULT_SIMULATION_SLIPPAGE_PERCENT))
    try:
        percent = Decimal(text)
    except InvalidOperation as error:
        raise InvalidConfigurationError(SIMULATION_SLIPPAGE) from error
    if not percent.is_finite():
        raise InvalidConfigurationError(SIMULATION_SLIPPAGE)
    return _SqlAlchemySimulationSettings(Slippage.percent(percent))
