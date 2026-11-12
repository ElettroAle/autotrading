import json
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.domain.flows.risk_limits import RiskLimits
from tests.support.activity import a_fill, a_position, an_activity
from tests.support.attribution import AttributionBench, amount, step
from tests.support.flow_cycles import FlowCycles

scenarios("E1-flussi-autonomi/F1.6-capitale-dei-flussi/R1.6.1-stato-del-flusso-dall-exchange.feature")


@pytest.fixture
def bench() -> AttributionBench:
    return AttributionBench()


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    """The same flows run by the worker: the cycle must see the state the user consults (Bug 153)."""
    return FlowCycles()


def fills_of(bench: AttributionBench, flow: str, realized_pnl: Decimal, fee: Decimal) -> None:
    order, owner = uuid4(), bench.flow(flow)
    bench.orders.add(order, owner.account_id, owner.id)
    bench.extend(owner.account_id, fills=(a_fill("BTC", order, realized_pnl=realized_pnl, fee=fee),))


def cycle_fills_of(flow_cycles: FlowCycles, flow: str, realized_pnl: Decimal, fee: Decimal) -> None:
    order, owner = uuid4(), flow_cycles.flow(flow)
    platform = flow_cycles.platform
    platform.platform_orders.add(order, owner.account_id, owner.id)
    address = flow_cycles.credentials_of(flow).account_address
    fill = a_fill("BTC", order, realized_pnl=realized_pnl, fee=fee)
    platform.activity_reader.activities[address] = an_activity(fills=(fill,))


def add_cycle_flow(flow_cycles: FlowCycles, name: str, asset: str, capital: Decimal) -> None:
    flow_cycles.add_flow("anna", name, assets=(asset,))
    # The whole capital may go in one operation: the scenarios measure the liquidity, not the exposure (R1.5.2).
    limits = RiskLimits(5, Decimal(100))
    flow_cycles.reconfigure(
        name, lambda configuration: replace(configuration, allocated_capital=capital, risk_limits=limits)
    )


@given(
    step(
        r'che "anna" ha il conto "{account}" con i flussi "alfa" \(asset "BTC", capitale allocato {a} USDC\)'
        r' e "beta" \(asset "ETH", capitale allocato {b} USDC\)'
    )
)
def two_flows(bench: AttributionBench, flow_cycles: FlowCycles, account: str, a: str, b: str) -> None:
    bench.add_flow(account, "alfa", ("BTC",), amount(a))
    bench.add_flow(account, "beta", ("ETH",), amount(b))
    add_cycle_flow(flow_cycles, "alfa", "BTC", amount(a))
    add_cycle_flow(flow_cycles, "beta", "ETH", amount(b))


@given(step(r'che sull\'exchange il conto "{account}" ha posizioni aperte su "{asset}" e su "{other}"'))
def open_positions(bench: AttributionBench, account: str, asset: str, other: str) -> None:
    bench.extend(bench.account(account), positions=(a_position(asset), a_position(other)))


@given(step(r'che le esecuzioni del flusso "{flow}" hanno PnL realizzato {a} USDC e commissioni {b} USDC'))
def fills_with_fees(bench: AttributionBench, flow_cycles: FlowCycles, flow: str, a: str, b: str) -> None:
    fills_of(bench, flow, amount(a), amount(b))
    cycle_fills_of(flow_cycles, flow, amount(a), amount(b))


@given(step(r'che sull\'exchange il margine libero del conto "{account}" è {a} USDC'))
def free_margin(flow_cycles: FlowCycles, account: str, a: str) -> None:
    flow_cycles.platform.hyperliquid.set_available_margin(flow_cycles.credentials_of("alfa", account), amount(a))


@given(step(r'che le esecuzioni del flusso "{flow}" hanno PnL realizzato {a} USDC'))
def fills_without_fees(bench: AttributionBench, flow: str, a: str) -> None:
    fills_of(bench, flow, amount(a), Decimal(0))


@given(step(r'che il flusso "{flow}" ha {a} USDC impegnati come margine in posizioni aperte'))
def committed_margin(bench: AttributionBench, flow: str, a: str) -> None:
    owner = bench.flow(flow)
    bench.extend(owner.account_id, positions=(a_position(owner.configuration.assets[0], margin=amount(a)),))


@given(
    step(
        r'che il flusso "{flow}" ha liquidità disponibile {a} USDC e una posizione con margine {b} USDC'
        r" e PnL non realizzato {c} USDC"
    )
)
def liquidity_and_position(bench: AttributionBench, flow: str, a: str, b: str, c: str) -> None:
    owner, margin = bench.flow(flow), amount(b)
    bench.extend(
        owner.account_id,
        positions=(a_position(owner.configuration.assets[0], margin=margin, unrealized_pnl=amount(c)),),
    )
    # The liquidity the step names comes from the executions of the flow: capital, plus their PnL, less the margin.
    fills_of(bench, flow, amount(a) - owner.configuration.allocated_capital + margin, Decimal(0))


@given(
    step(
        r'che "anna" ha il conto "{account}" con saldo {a} USDC e il solo flusso "{flow}"'
        r" con capitale allocato {b} USDC e nessuna operazione"
    )
)
def single_flow(bench: AttributionBench, account: str, a: str, flow: str, b: str) -> None:
    bench.account(account, amount(a))
    bench.add_flow(account, flow, ("SOL",), amount(b))


@when(
    step(
        r'parte un ciclo del flusso "{flow}" in cui l\'agente apre "{asset}"'
        r" con quota {a} e leva (?P<leverage>[0-9]+)"
    )
)
def cycle_opens(flow_cycles: FlowCycles, flow: str, asset: str, a: str, leverage: str) -> None:
    opening = {
        "asset": asset,
        "azione": "apri",
        "direzione": "long",
        "quota": float(amount(a)),
        "leva": int(leverage),
        "ragionamento": "r",
    }
    flow_cycles.model.text = json.dumps({"decisioni": [opening]})
    flow_cycles.run(flow)


@when(step(r'"anna" consulta lo stato del flusso "{flow}"'))
def consult(bench: AttributionBench, flow: str) -> None:
    bench.consult(flow)


@then(step(r'il flusso "{flow}" ha la sola posizione su "{asset}"'))
def only_position(bench: AttributionBench, asset: str) -> None:
    assert [position.asset for position in bench.consulted().positions] == [asset]


@then(step(r'il flusso "{flow}" ha liquidità disponibile {a} USDC'))
def liquidity(bench: AttributionBench, a: str) -> None:
    assert bench.consulted().available_liquidity == amount(a)


@then(step(r'il flusso "{flow}" ha valore complessivo {a} USDC'))
def total_value(bench: AttributionBench, a: str) -> None:
    assert bench.consulted().total_value == amount(a)


@then(step(r'il flusso "{flow}" ha rendimento dall\'avvio del {a}%'))
def return_since_start(bench: AttributionBench, a: str) -> None:
    assert bench.consulted().return_percent == amount(a)


@then(
    step(r'il flusso "{flow}" ha liquidità disponibile {a} USDC, uguale al margine disponibile del conto "{account}"')
)
def liquidity_equal_to_account(bench: AttributionBench, a: str, account: str) -> None:
    liquidity = bench.consulted().available_liquidity
    assert liquidity == amount(a)
    assert liquidity == bench.activity_of(bench.account(account)).available_margin


@then(
    step(
        r'l\'agente riceve per il flusso "{flow}" liquidità disponibile {a} USDC, valore complessivo {b} USDC'
        r" e rendimento dall'avvio del {c}%"
    )
)
def agent_receives_state(flow_cycles: FlowCycles, a: str, b: str, c: str) -> None:
    state = flow_state_in_context(flow_cycles)
    assert Decimal(state["liquidita_disponibile"]) == amount(a)
    assert Decimal(state["valore_complessivo"]) == amount(b)
    assert Decimal(state["rendimento_dall_avvio_percento"]) == amount(c)


@then(step(r'l\'agente riceve per il flusso "{flow}" liquidità disponibile {a} USDC'))
def agent_receives_liquidity(flow_cycles: FlowCycles, a: str) -> None:
    assert Decimal(flow_state_in_context(flow_cycles)["liquidita_disponibile"]) == amount(a)


@then(step(r'l\'apertura del flusso "{flow}" è bloccata con il motivo "(?P<reason>[^"]+)"'))
def opening_blocked(flow_cycles: FlowCycles, flow: str, reason: str) -> None:
    assert flow_cycles.platform.order_exchange.sent == []
    assert reason in str(flow_cycles.last_record(flow).documents)


def flow_state_in_context(flow_cycles: FlowCycles) -> dict[str, str]:
    state = flow_cycles.context()["stato_del_flusso"]
    assert isinstance(state, dict)
    return state
