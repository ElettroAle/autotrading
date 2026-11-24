from autotrading.application.orders.ports import ExchangeConnection
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.fakes.protection_exchange import FakeProtectionExchangeAdapter


def connection_of(
    exchange: FakeOrderExchangeAdapter, protections: FakeProtectionExchangeAdapter | None = None
) -> ExchangeConnection:
    """The finto exchange that reads its market and operates the accounts, as the real one does."""
    return ExchangeConnection(exchange, exchange, protections or FakeProtectionExchangeAdapter())
