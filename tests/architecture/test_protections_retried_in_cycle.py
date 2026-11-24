"""ADR-protezioni-ritentate-nel-ciclo: the access to the account and every placement, update and cancellation of a
protection of the cycle are retried with the policy of the cycle, and a protection retried is never placed twice.

The use cases of the protections of the cycle get the calls of the cycle that retry, never place a protection on the
exchange directly but through the placing that asks the exchange for it by its client order id before placing it again,
and never send a closing once but through the retried sending of the orders. The cancellation counts a protection the
exchange no longer has as cancelled.
"""

import ast
import inspect
from typing import get_type_hints

from autotrading.application.orders.ports import ProtectionExchangePort, SendingRetryPort
from autotrading.application.orders.protect_flow_position import ProtectFlowPositionCommand
from autotrading.application.orders.protect_open_positions import ProtectOpenPositionsUseCase
from autotrading.application.orders.sending import ProtectionPlacing, RetriedCalls, cancel_protection
from autotrading.application.orders.update_flow_protection import UpdateFlowProtectionCommand
from tests.support.architecture import SOURCE_ROOT, SourceModule, source_modules

PROTECTION_MODULES = frozenset(
    {
        "application/orders/protect_flow_position.py",
        "application/orders/update_flow_protection.py",
        "application/orders/protect_open_positions.py",
    }
)
DIRECT_CALLS = frozenset({"place", "cancel", "send_order", "place_market_order"})
PLACING = "ProtectionPlacing"
LOOKUP = "find"


def direct_calls(module: SourceModule) -> list[str]:
    """The lines where a protection or an order goes to the exchange once, without asking for it before again."""
    return [
        f"{module.path}:{node.lineno}"
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call) and _called_name(node) in DIRECT_CALLS
    ]


def places_through_the_retried_placing(module: SourceModule) -> bool:
    return any(isinstance(node, ast.Call) and _called_name(node) == PLACING for node in ast.walk(module.tree))


def _called_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _protection_modules() -> list[SourceModule]:
    return [module for module in source_modules(SOURCE_ROOT) if module.path in PROTECTION_MODULES]


def test_adr_protezioni_ritentate_nel_ciclo_protections_placed_only_through_the_retried_placing() -> None:
    modules = _protection_modules()

    assert {module.path for module in modules} == PROTECTION_MODULES
    assert [line for module in modules for line in direct_calls(module)] == []
    assert all(places_through_the_retried_placing(module) for module in modules)


def test_adr_protezioni_ritentate_nel_ciclo_blind_placement_violates() -> None:
    blind = SourceModule.parse(
        "application/orders/protect_open_positions.py",
        "class ProtectOpenPositionsUseCase:\n"
        "    def _protected(self, account, order):\n"
        "        return account.calls.run(order.asset, lambda: account.protections.place(account.access, order))\n",
    )

    assert direct_calls(blind) == ["application/orders/protect_open_positions.py:3"]
    assert not places_through_the_retried_placing(blind)


def test_adr_protezioni_ritentate_nel_ciclo_placing_asks_the_exchange_before_placing_again() -> None:
    attempt = ast.parse(inspect.getsource(ProtectionPlacing.attempt).strip())
    called = [_called_name(node) for node in ast.walk(attempt) if isinstance(node, ast.Call)]

    assert LOOKUP in called
    assert called.index(LOOKUP) < called.index("place")
    assert "find" in dict(inspect.getmembers(ProtectionExchangePort))


def test_adr_protezioni_ritentate_nel_ciclo_cancellation_counts_a_gone_protection_as_cancelled() -> None:
    cancellation = ast.parse(inspect.getsource(cancel_protection))
    handlers = [node for node in ast.walk(cancellation) if isinstance(node, ast.ExceptHandler)]

    assert [ast.unparse(handler.type) for handler in handlers if handler.type is not None] == [
        "ExchangeRejectedOrderError"
    ]


def test_adr_protezioni_ritentate_nel_ciclo_use_cases_of_the_protections_get_the_retry_of_the_cycle() -> None:
    assert get_type_hints(ProtectFlowPositionCommand)["calls"] is RetriedCalls
    assert get_type_hints(UpdateFlowProtectionCommand)["calls"] is RetriedCalls
    assert inspect.signature(ProtectOpenPositionsUseCase.__init__).parameters["retry"].annotation is SendingRetryPort
