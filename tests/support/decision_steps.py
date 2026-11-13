"""Steps of the decisions of the agent, run on the bridges of the worker and read back from the record (R1.4.4, R1.4.5).

A scenario module imports them all, beside the steps of the cycles; pytest-bdd keeps each step as a fixture of
that module.
"""

import json
from decimal import Decimal

from pytest_bdd import given, parsers, then

from autotrading.adapters.outbound.hyperliquid.composition import EXCHANGE_NAME as HYPERLIQUID
from autotrading.domain.accounts.position import PositionSide
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.trading_access import TradingAccess
from tests.support.flow_cycle_steps import names_of, position
from tests.support.flow_cycles import FlowCycles
from tests.support.steps import quoted

FIELDS_OF_OPENING = ("direzione", "quota", "leva")


def fraction(text: str) -> float:
    return float(text.replace(",", "."))


def answer(flow_cycles: FlowCycles, *decisions: object) -> None:
    flow_cycles.model.text = json.dumps({"decisioni": list(decisions)})


def opening(asset: str, quota: object = 0.1, leverage: object = 3, reasoning: str = "rottura") -> dict[str, object]:
    return {
        "asset": asset,
        "azione": "apri",
        "direzione": "long",
        "quota": quota,
        "leva": leverage,
        "ragionamento": reasoning,
    }


def decision(asset: str, action: str, reasoning: str = "motivo") -> dict[str, object]:
    return {"asset": asset, "azione": action, "ragionamento": reasoning}


def recorded_decisions(flow_cycles: FlowCycles, flow: str = "alfa") -> dict[str, object]:
    document = flow_cycles.last_record(flow).document(CycleStep.AGENT_DECISION)
    assert document is not None
    return dict(document)


def decisions_by_asset(flow_cycles: FlowCycles) -> dict[str, dict[str, object]]:
    decisions = recorded_decisions(flow_cycles)["decisioni"]
    assert isinstance(decisions, list)
    return {entry["asset"]: entry for entry in decisions}


def discarded_reasons(flow_cycles: FlowCycles) -> dict[str, str]:
    discarded = recorded_decisions(flow_cycles)["scartate"]
    assert isinstance(discarded, list)
    return {entry["asset"]: entry["reason"] for entry in discarded}


# Given: the flow and the answer of the agent


@given(quoted('che "{user}" ha il flusso "{flow}" con asset "{assets}"'))
def flow_with_assets(flow_cycles: FlowCycles, user: str, flow: str, assets: str) -> None:
    flow_cycles.add_flow(user, flow, assets=names_of(assets))


@given(quoted('che l\'agente risponde apri long su "{first}", chiudi su "{second}" e mantieni su "{third}"'))
def one_per_asset(flow_cycles: FlowCycles, first: str, second: str, third: str) -> None:
    answer(flow_cycles, opening(first), decision(second, "chiudi"), decision(third, "mantieni"))


@given(
    parsers.re(
        r'^che l\'agente risponde su "(?P<asset>[^"]+)" apri long con quota (?P<quota>[\d,]+), leva (?P<leverage>\d+) '
        r'e ragionamento "(?P<reasoning>[^"]+)"$'
    )
)
def opening_with_fields(flow_cycles: FlowCycles, asset: str, quota: str, leverage: str, reasoning: str) -> None:
    answer(flow_cycles, opening(asset, fraction(quota), int(leverage), reasoning))


@given(
    parsers.re(
        r'^che l\'agente risponde su "(?P<asset>[^"]+)" mantieni con leva (?P<leverage>\d+) '
        r'e ragionamento "(?P<reasoning>[^"]+)"$'
    )
)
def hold_with_fields(flow_cycles: FlowCycles, asset: str, leverage: str, reasoning: str) -> None:
    answer(flow_cycles, {**decision(asset, "mantieni", reasoning), "leva": int(leverage)})


@given(
    parsers.re(r'^che il flusso "(?P<flow>[^"]+)" ha una posizione long su "(?P<asset>[^"]+)" di (?P<size>[\d,]+) \w+$')
)
def long_position(flow_cycles: FlowCycles, flow: str, asset: str, size: str) -> None:
    amount = Decimal(size.replace(",", "."))
    credentials = flow_cycles.credentials_of(flow)
    flow_cycles.platform.hyperliquid.open_position(credentials, position(asset, PositionSide.LONG, size=amount))
    # The account reads the position from the market data, the orders close it on the exchange of the orders.
    access = TradingAccess(HYPERLIQUID, credentials.account_address, credentials.secret_key)
    flow_cycles.platform.order_exchange.hold(access, HeldPosition(asset, Direction.LONG, amount, 1))


@given(quoted('che l\'agente risponde chiudi su "{asset}"'))
def close_answer(flow_cycles: FlowCycles, asset: str) -> None:
    answer(flow_cycles, decision(asset, "chiudi"))


@given(
    parsers.re(
        r'^che l\'agente risponde apri long su "(?P<first>[^"]+)" '
        r"con quota (?P<quota>[\d,]+) e leva (?P<leverage>\d+), "
        r'e apri su "(?P<second>[^"]+)" senza direzione$'
    )
)
def one_without_direction(flow_cycles: FlowCycles, first: str, quota: str, leverage: str, second: str) -> None:
    incomplete = {key: value for key, value in opening(second).items() if key != "direzione"}
    answer(flow_cycles, opening(first, fraction(quota), int(leverage)), incomplete)


@given(parsers.re(r'^che l\'agente risponde su "(?P<asset>[^"]+)" (?P<text>.+)$'))
def nonconforming_answer(flow_cycles: FlowCycles, asset: str, text: str) -> None:
    quoted_quota = text.startswith('apri long con quota "')
    if quoted_quota:
        answer(flow_cycles, opening(asset, text.split('"')[1], 3))
        return
    if text.startswith("apri long con quota "):
        answer(flow_cycles, opening(asset, fraction(text.split(" ")[4]), 3))
        return
    answer(flow_cycles, decision(asset, text))


@given(quoted('che l\'agente risponde anche apri long su "{asset}"'))
def foreign_asset(flow_cycles: FlowCycles, asset: str) -> None:
    answer(flow_cycles, opening("BTC"), opening(asset))


@given(quoted('che l\'agente risponde solo per "{first}" e "{second}"'))
def only_some_assets(flow_cycles: FlowCycles, first: str, second: str) -> None:
    answer(flow_cycles, decision(first, "mantieni"), decision(second, "mantieni"))


@given("che l'agente risponde con un testo che non segue il formato della risposta")
def unreadable_answer(flow_cycles: FlowCycles) -> None:
    flow_cycles.model.text = "Comprerei BTC, il mercato sale."


# Then


@then("il ciclo registra le decisioni:")
def recorded_actions(flow_cycles: FlowCycles, datatable: list[list[str]]) -> None:
    actions = {asset: entry["action"] for asset, entry in decisions_by_asset(flow_cycles).items()}
    assert actions == {asset: action for asset, action in datatable[1:]}


@then(
    parsers.re(
        r'^il ciclo registra per "(?P<asset>[^"]+)" un\'apertura long '
        r"con quota (?P<quota>[\d,]+) e leva (?P<leverage>\d+)$"
    )
)
def recorded_opening(flow_cycles: FlowCycles, asset: str, quota: str, leverage: str) -> None:
    opened = decisions_by_asset(flow_cycles)[asset]["opening"]
    assert isinstance(opened, dict)
    assert (opened["direction"], Decimal(opened["margin_fraction"]), opened["leverage"]) == (
        "long",
        Decimal(quota.replace(",", ".")),
        int(leverage),
    )


@then(quoted('il ciclo registra per "{asset}" il ragionamento "{reasoning}"'))
def recorded_reasoning(flow_cycles: FlowCycles, asset: str, reasoning: str) -> None:
    assert decisions_by_asset(flow_cycles)[asset]["reasoning"] == reasoning


@then(quoted('il ciclo registra per "{asset}" la decisione mantieni senza campi operativi'))
def recorded_plain_hold(flow_cycles: FlowCycles, asset: str) -> None:
    held = decisions_by_asset(flow_cycles)[asset]
    assert (held["action"], held["opening"]) == ("mantieni", None)


@then(parsers.re(r'^l\'ordine di chiusura su "(?P<asset>[^"]+)" riguarda (?P<size>[\d,]+) \w+$'))
def closing_order_size(flow_cycles: FlowCycles, asset: str, size: str) -> None:
    [order] = [order for order in flow_cycles.platform.order_exchange.sent if order.coin == asset]
    assert (order.is_buy, order.size, order.reduce_only) == (False, Decimal(size.replace(",", ".")), True)


@then(quoted('la decisione su "{asset}" è scartata con il motivo "{reason}"'))
def discarded_with_reason(flow_cycles: FlowCycles, asset: str, reason: str) -> None:
    assert discarded_reasons(flow_cycles)[asset] == reason


@then(quoted('la decisione su "{asset}" prosegue al controllo del rischio'))
def goes_to_risk(flow_cycles: FlowCycles, asset: str) -> None:
    document = flow_cycles.last_record("alfa").document(CycleStep.RISK_CHECK)
    assert document is not None
    assert asset in json.dumps(document["esiti"])
    assert asset in decisions_by_asset(flow_cycles)


@then(quoted('per "{asset}" il ciclo registra una decisione mancante trattata come mantieni'))
def missing_decision(flow_cycles: FlowCycles, asset: str) -> None:
    assert asset in recorded_decisions(flow_cycles)["mancanti"]  # type: ignore[operator]  # a list of the record
    assert asset not in decisions_by_asset(flow_cycles)


@then("il ciclo registra la risposta integrale dell'agente")
def whole_answer(flow_cycles: FlowCycles) -> None:
    assert recorded_decisions(flow_cycles)["risposta"] == flow_cycles.model.text


@then(quoted('il ciclo registra tutte le decisioni come scartate con il motivo "{reason}"'))
def all_discarded(flow_cycles: FlowCycles, reason: str) -> None:
    assert decisions_by_asset(flow_cycles) == {}
    assert set(discarded_reasons(flow_cycles).values()) == {reason}


@then("il ciclo non invia ordini all'exchange")
def no_orders(flow_cycles: FlowCycles) -> None:
    assert flow_cycles.platform.order_exchange.sent == []
