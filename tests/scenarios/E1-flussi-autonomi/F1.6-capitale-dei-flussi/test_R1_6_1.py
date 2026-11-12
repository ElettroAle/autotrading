import json
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.ledger import FlowTotals
from autotrading.domain.flows.risk_limits import RiskLimits
from tests.support.activity import READ_AT, a_fill, a_payment, a_position
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


OPENED_AT = READ_AT - timedelta(minutes=10)
FUNDED_AT = READ_AT + timedelta(minutes=1)


def fills_of(bench: AttributionBench, flow: str, realized_pnl: Decimal, fee: Decimal) -> None:
    order, owner = uuid4(), bench.flow(flow)
    bench.orders.add(order, owner.account_id, owner.id)
    fill = a_fill("BTC", order, realized_pnl=realized_pnl, fee=fee, fill_id=str(order))
    bench.extend(owner.account_id, fills=(fill,))
    bench.record_executions(owner.account_id)


def cycle_fills_of(flow_cycles: FlowCycles, flow: str, realized_pnl: Decimal, fee: Decimal) -> None:
    order, owner = uuid4(), flow_cycles.flow(flow)
    platform = flow_cycles.platform
    platform.platform_orders.add(order, owner.account_id, owner.id)
    address = flow_cycles.credentials_of(flow).account_address
    fill = a_fill("BTC", order, realized_pnl=realized_pnl, fee=fee, fill_id=str(order))
    platform.activity_reader.executions.setdefault(address, []).append(fill)


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


@given(step(r'che l\'exchange non mostra più le esecuzioni del conto "{account}"'))
def exchange_forgets(bench: AttributionBench, account: str) -> None:
    bench.exchange.executions[bench.account(account)] = []
    bench.record_executions(bench.account(account))


@given(step(r'che il ciclo successivo legge di nuovo le stesse esecuzioni del conto "{account}"'))
def read_again(bench: AttributionBench, account: str) -> None:
    bench.record_executions(bench.account(account))


@given(step(r'che il flusso "{flow}" ha aperto {a} "{asset}" con i propri ordini'))
def opened_by_flow(bench: AttributionBench, flow: str, a: str, asset: str) -> None:
    order, owner = uuid4(), bench.flow(flow)
    bench.orders.add(order, owner.account_id, owner.id)
    opening = a_fill(asset, order, size=amount(a), fill_id="apertura", executed_at=OPENED_AT)
    bench.extend(owner.account_id, fills=(opening,))
    bench.record_executions(owner.account_id)


def held_by_owner(bench: AttributionBench, asset: str) -> tuple[UUID, Decimal]:
    (owner,) = (flow for flow in bench.store.flows if asset in flow.configuration.assets)
    totals = bench.ledger.totals.get(owner.id) or FlowTotals(owner.id)
    return owner.account_id, totals.expected(asset)


@given(step(r'che l\'exchange liquida la posizione "{asset}" con PnL realizzato {a} USDC'))
def liquidated(bench: AttributionBench, asset: str, a: str) -> None:
    account_id, held = held_by_owner(bench, asset)
    liquidation = a_fill(
        asset, None, size=-held, start_position=held, realized_pnl=amount(a), liquidation=True, fill_id="liquidazione"
    )
    bench.extend(account_id, fills=(liquidation,))
    bench.record_executions(account_id)


@given(step(r'che sull\'exchange una vendita di {a} "{asset}" fuori dalla piattaforma realizza PnL {b} USDC'))
def sold_outside(bench: AttributionBench, a: str, asset: str, b: str) -> None:
    account_id, held = held_by_owner(bench, asset)
    sale = a_fill(asset, None, size=-amount(a), start_position=held, realized_pnl=amount(b), fill_id="fuori")
    bench.extend(account_id, fills=(sale,))
    bench.record_executions(account_id)


@given(step(r'che sull\'exchange la posizione "{asset}" paga un funding di {a} USDC'))
def funding_paid(bench: AttributionBench, asset: str, a: str) -> None:
    account_id, _ = held_by_owner(bench, asset)
    bench.exchange.funding.setdefault(account_id, []).append(a_payment(asset, amount(a), paid_at=FUNDED_AT))
    bench.record_executions(account_id)


@given(step(r'che il registro del conto "{account}" è aggiornato a un ciclo precedente'))
def ledger_of_previous_cycle(flow_cycles: FlowCycles, account: str) -> None:
    account_id = flow_cycles.account_of("anna", account)
    flow_cycles.platform.ledger.cursors[account_id] = flow_cycles.clock.now() - timedelta(minutes=15)


@given(step(r'che dall\'ultimo ciclo il conto "{account}" ha più esecuzioni di quante l\'exchange ne conservi'))
def more_than_kept(flow_cycles: FlowCycles) -> None:
    flow_cycles.platform.activity_reader.complete = False


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


@when(step(r'si ricalcolano dallo storico i totali del flusso "{flow}"'))
def recompute(bench: AttributionBench, flow: str) -> None:
    bench.recomputed = bench.ledger.recomputed(bench.flow(flow).id)


@then(step(r'i totali ricalcolati del flusso "{flow}" coincidono con quelli che legge il ciclo'))
def recomputed_equal(bench: AttributionBench, flow: str) -> None:
    owner = bench.flow(flow)
    assert bench.recomputed == bench.ledger.totals_of((owner.id,))[owner.id]
    assert bench.recomputed.funding != Decimal(0)


@then("nessun ordine è inviato")
def no_order(flow_cycles: FlowCycles) -> None:
    assert flow_cycles.platform.order_exchange.sent == []


@then(step(r'i flussi "alfa" e "beta" sono in pausa con il motivo "{reason}"'))
def both_paused(flow_cycles: FlowCycles, reason: str) -> None:
    store = flow_cycles.platform.flows
    for name in ("alfa", "beta"):
        flow = flow_cycles.flow(name)
        assert (flow.status, store.pause_reasons[flow.id]) == (FlowStatus.PAUSED, reason)


def flow_state_in_context(flow_cycles: FlowCycles) -> dict[str, str]:
    state = flow_cycles.context()["stato_del_flusso"]
    assert isinstance(state, dict)
    return state
