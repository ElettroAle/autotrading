"""ADR-exchange-simulato-con-porte-di-lettura-e-scrittura: the ports of the exchange are split into the reading of the
market, without the access of an account, and the operations of the account, always with its access; one name of the
map of the exchanges gives both, as the fields of one frozen connection.

The port that reads the market never receives a `TradingAccess`; the ports that operate the account never read the
market and receive the access of the account in every method; the market order receives the market the use case read.
The simulated exchange operates the account in `sqlalchemy/` and never reads the market itself.
"""

import ast
from dataclasses import fields
from typing import get_type_hints

from autotrading.application.orders.ports import (
    ExchangeConnection,
    MarketReaderPort,
    OrderExchangePort,
    ProtectionExchangePort,
)
from tests.support.architecture import SOURCE_ROOT, SourceModule

PORTS = "application/orders/ports.py"
SIMULATED_EXCHANGE = "adapters/outbound/sqlalchemy/simulated_exchange.py"
READING_PORTS = frozenset({"MarketReaderPort"})
OPERATION_PORTS = frozenset({"OrderExchangePort", "ProtectionExchangePort"})
ACCESS = "TradingAccess"
MARKET = "Market"
MARKET_READING = "market"
MARKET_ORDER = "place_market_order"


def _module(path: str) -> SourceModule:
    return SourceModule.parse(path, (SOURCE_ROOT / path).read_text(encoding="utf-8"))


def _methods(module: SourceModule, class_names: frozenset[str]) -> list[tuple[str, ast.FunctionDef]]:
    return [
        (node.name, method)
        for node in module.tree.body
        if isinstance(node, ast.ClassDef) and node.name in class_names
        for method in node.body
        if isinstance(method, ast.FunctionDef) and not method.name.startswith("_")
    ]


def _annotations(method: ast.FunctionDef) -> list[str]:
    return [ast.unparse(argument.annotation) for argument in method.args.args[1:] if argument.annotation is not None]


def readings_with_an_access(module: SourceModule) -> list[str]:
    """The methods of a reading port that ask for the access of an account."""
    return [
        f"{module.path}:{method.lineno} {port}.{method.name}"
        for port, method in _methods(module, READING_PORTS)
        if ACCESS in _annotations(method)
    ]


def operations_mixed_with_readings(module: SourceModule) -> list[str]:
    """The methods of an operation port that read the market, or that operate without the access of the account."""
    return [
        f"{module.path}:{method.lineno} {port}.{method.name}"
        for port, method in _methods(module, OPERATION_PORTS)
        if method.name == MARKET_READING or _annotations(method)[:1] != [ACCESS]
    ]


def market_order_without_the_market_read(module: SourceModule) -> bool:
    return any(name == MARKET_ORDER and MARKET not in _annotations(method) for name, method in _account_methods(module))


def _account_methods(module: SourceModule) -> list[tuple[str, ast.FunctionDef]]:
    return [(method.name, method) for _, method in _methods(module, frozenset({"OrderExchangePort"}))]


def classes_reading_the_market(module: SourceModule) -> list[str]:
    return [
        f"{module.path}:{method.lineno} {owner}.{method.name}"
        for node in module.tree.body
        if isinstance(node, ast.ClassDef)
        for owner, method in _methods(module, frozenset({node.name}))
        if method.name == MARKET_READING
    ]


def test_adr_exchange_simulato_con_porte_di_lettura_e_scrittura_reading_and_operations_kept_apart() -> None:
    ports = _module(PORTS)

    assert _methods(ports, READING_PORTS) != []
    assert readings_with_an_access(ports) == []
    assert operations_mixed_with_readings(ports) == []
    assert not market_order_without_the_market_read(ports)


def test_adr_exchange_simulato_con_porte_di_lettura_e_scrittura_mixed_ports_violate() -> None:
    mixed = SourceModule.parse(
        PORTS,
        "class MarketReaderPort(Protocol):\n"
        "    def market(self, access: TradingAccess, coin: str) -> Market: ...\n"
        "class OrderExchangePort(Protocol):\n"
        "    def market(self, coin: str) -> Market: ...\n"
        "    def place_market_order(self, access: TradingAccess, order: MarketOrder) -> Execution: ...\n"
        "class ProtectionExchangePort(Protocol):\n"
        "    def active(self, coin: str) -> tuple[str, ...]: ...\n",
    )

    assert readings_with_an_access(mixed) == [f"{PORTS}:2 MarketReaderPort.market"]
    assert operations_mixed_with_readings(mixed) == [
        f"{PORTS}:4 OrderExchangePort.market",
        f"{PORTS}:7 ProtectionExchangePort.active",
    ]
    assert market_order_without_the_market_read(mixed)


def test_adr_exchange_simulato_con_porte_di_lettura_e_scrittura_one_name_gives_every_port() -> None:
    hints = get_type_hints(ExchangeConnection)

    assert ExchangeConnection.__dataclass_params__.frozen  # type: ignore[attr-defined]  # dataclass parameters not typed
    assert [field.name for field in fields(ExchangeConnection)] == ["market", "account", "protections"]
    assert (hints["market"], hints["account"], hints["protections"]) == (
        MarketReaderPort,
        OrderExchangePort,
        ProtectionExchangePort,
    )


def test_adr_exchange_simulato_con_porte_di_lettura_e_scrittura_simulated_exchange_never_reads_the_market() -> None:
    simulated = _module(SIMULATED_EXCHANGE)
    reading = SourceModule.parse(
        SIMULATED_EXCHANGE,
        "class SqlAlchemySimulatedExchangeAdapter:\n    def market(self, coin: str) -> Market: ...\n",
    )

    assert "class SqlAlchemySimulatedExchangeAdapter" in ast.unparse(simulated.tree)
    assert classes_reading_the_market(simulated) == []
    assert classes_reading_the_market(reading) == [f"{SIMULATED_EXCHANGE}:2 SqlAlchemySimulatedExchangeAdapter.market"]
