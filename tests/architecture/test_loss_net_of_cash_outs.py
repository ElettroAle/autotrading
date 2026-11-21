"""ADR-perdita-massima-al-netto-degli-incassi: the references of the maximum loss are brought to the profits the flow
cashed out until now, less those cashed out when they were recorded; the guard of the cycle passes the profits cashed
out of the state it already read, for the daily reference and for the peak alike.
"""

import ast
import inspect
from decimal import Decimal
from pathlib import Path
from typing import get_type_hints

from autotrading.application.flows import guard_flow_loss
from autotrading.domain.flows import loss_guard
from autotrading.domain.flows.loss_guard import LossGuard, at_capital

GUARD = Path(inspect.getfile(guard_flow_loss))
LOSS_GUARD = Path(inspect.getfile(loss_guard))
CASHED_PROFIT = "flow.attributed.cashed_profit"


def arguments_of_calls(source: str, function: str) -> list[list[str]]:
    """The arguments, as written, of every call of the function in the source."""
    calls = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)]
    return [[ast.unparse(argument) for argument in call.args] for call in calls if ast.unparse(call.func) == function]


def test_adr_perdita_massima_al_netto_degli_incassi_the_references_take_the_profits_cashed_out() -> None:
    assert get_type_hints(at_capital)["cashed_profit"] is Decimal
    assert get_type_hints(LossGuard.of)["cashed_profit"] is Decimal


def test_adr_perdita_massima_al_netto_degli_incassi_both_references_are_net_of_the_cash_outs() -> None:
    calls = arguments_of_calls(LOSS_GUARD.read_text("utf-8"), "at_capital")

    assert sorted(arguments[0] for arguments in calls) == ["references.daily", "references.peak"]
    assert all(arguments[2] == "cashed_profit" for arguments in calls)


def test_adr_perdita_massima_al_netto_degli_incassi_the_guard_passes_the_profits_cashed_out_of_the_flow() -> None:
    [arguments] = arguments_of_calls(GUARD.read_text("utf-8"), "LossGuard.of")

    assert arguments[-1] == CASHED_PROFIT


def test_adr_perdita_massima_al_netto_degli_incassi_a_guard_ignoring_the_cash_outs_is_found() -> None:
    violating = "LossGuard.of(configuration, flow.total_value, references, Decimal(0)).breach()"

    [arguments] = arguments_of_calls(violating, "LossGuard.of")

    assert arguments[-1] != CASHED_PROFIT
