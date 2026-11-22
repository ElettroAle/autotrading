"""ADR-prezzo-limite-dell-ordine-a-mercato-vicino-all-oracolo: the adapter of the orders computes the limit of a market
order itself, from the book and the oracle, with the pure rule of the domain of the orders; it never leaves it to the
market orders of the SDK, whose limit follows the book alone (Bug 631).
"""

import ast
import inspect
from collections.abc import Iterator

from autotrading.domain.orders.market_order import MarketOrder
from tests.support.architecture import SOURCE_ROOT

FOLDER = SOURCE_ROOT / "adapters" / "outbound" / "hyperliquid"
ORDERS = FOLDER / "orders.py"
MARKET_ORDERS_OF_THE_SDK = frozenset({"market_open", "market_close"})
DOMAIN_RULE = "limit_price"
ORACLE_READING = "meta_and_asset_ctxs"

LIMIT_FROM_THE_BOOK = "exchange.market_open(order.coin, order.is_buy, size, None, slippage, cloid)\n"
LIMIT_OF_ITS_OWN = "exchange.order(order.coin, order.is_buy, size, float(limit), IMMEDIATE_OR_CANCEL)\n"


def market_orders_of_the_sdk(source: str) -> Iterator[str]:
    """The calls to the market orders of the SDK, which compute the limit from the book alone."""
    for node in ast.walk(ast.parse(source)):
        if _is_call_of(node, MARKET_ORDERS_OF_THE_SDK):
            yield ast.unparse(node)


def _is_call_of(node: ast.AST, names: frozenset[str]) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in names


def _called_names(source: str) -> set[str]:
    return {
        node.func.attr
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }


def test_adr_prezzo_limite_no_adapter_leaves_the_limit_to_the_market_orders_of_the_sdk() -> None:
    sources = {path.name: path.read_text(encoding="utf-8") for path in FOLDER.glob("*.py")}
    found = {name: list(market_orders_of_the_sdk(source)) for name, source in sources.items()}

    assert {name: calls for name, calls in found.items() if calls} == {}


def test_adr_prezzo_limite_a_market_order_of_the_sdk_is_found() -> None:
    assert list(market_orders_of_the_sdk(LIMIT_OF_ITS_OWN)) == []
    assert list(market_orders_of_the_sdk(LIMIT_FROM_THE_BOOK)) == [LIMIT_FROM_THE_BOOK.strip()]


def test_adr_prezzo_limite_the_adapter_reads_the_oracle_and_applies_the_rule_of_the_domain() -> None:
    called = _called_names(ORDERS.read_text(encoding="utf-8"))

    assert {DOMAIN_RULE, ORACLE_READING} <= called


def test_adr_prezzo_limite_the_rule_belongs_to_the_market_order_of_the_domain() -> None:
    parameters = inspect.signature(MarketOrder.limit_price).parameters

    assert list(parameters) == ["self", "market", "oracle_price"]
