from decimal import Decimal

from sqlalchemy import Engine

from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.sqlalchemy.configuration import _settings_of, _simulation_settings_of
from autotrading.adapters.outbound.sqlalchemy.database import SqlAlchemyDatabaseAdapter
from autotrading.adapters.outbound.sqlalchemy.simulated_exchange import (
    EXCHANGE_NAME as SIMULATED_EXCHANGE_NAME,
)
from autotrading.adapters.outbound.sqlalchemy.simulated_exchange import (
    SqlAlchemySimulatedExchangeAdapter,
)
from autotrading.domain.orders.simulation.simulated_execution import SimulatedExecution
from autotrading.domain.tenancy.tenant_id import TenantId

type SqlAlchemyEngine = Engine
type SimulatedExchangeOfTenant = dict[str, SqlAlchemySimulatedExchangeAdapter]


def sqlalchemy_adapters(source: ConfigurationSource) -> SqlAlchemyEngine:
    """The engine of the database of the installation, on which every repository of the service is built."""
    settings = _settings_of(source)
    database = SqlAlchemyDatabaseAdapter(settings.host, settings.port, settings.name, settings.user, settings.password)
    return database.engine()


def sqlalchemy_simulation_adapters(source: ConfigurationSource) -> SimulatedExecution:
    """The engine that executes the orders of the simulated exchange, with the slippage of the installation (R6.3.2)."""
    return SimulatedExecution(_simulation_settings_of(source).slippage)


def sqlalchemy_simulated_exchange_adapters(
    engine: SqlAlchemyEngine, simulation: SimulatedExecution, tenant_id: TenantId, market_order_fee_rate: Decimal
) -> SimulatedExchangeOfTenant:
    """The simulated exchange by its name, on the accounts of the tenant (R6.3.2, ADR 0152), with the fee of an order
    at the market of the real market it trades on (R5.5.6).
    """
    return {
        SIMULATED_EXCHANGE_NAME: SqlAlchemySimulatedExchangeAdapter(
            engine, tenant_id, simulation, market_order_fee_rate
        )
    }
