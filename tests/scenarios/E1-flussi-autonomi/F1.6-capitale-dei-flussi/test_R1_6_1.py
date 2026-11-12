from decimal import Decimal
from uuid import uuid4

import pytest
from pytest_bdd import given, scenarios, then, when

from tests.support.activity import a_fill, a_position
from tests.support.attribution import AttributionBench, amount, step

scenarios("E1-flussi-autonomi/F1.6-capitale-dei-flussi/R1.6.1-stato-del-flusso-dall-exchange.feature")


@pytest.fixture
def bench() -> AttributionBench:
    return AttributionBench()


def fills_of(bench: AttributionBench, flow: str, realized_pnl: Decimal, fee: Decimal) -> None:
    order, owner = uuid4(), bench.flow(flow)
    bench.orders.add(order, owner.account_id, owner.id)
    bench.extend(owner.account_id, fills=(a_fill("BTC", order, realized_pnl=realized_pnl, fee=fee),))


@given(
    step(
        r'che "anna" ha il conto "{account}" con i flussi "alfa" \(asset "BTC", capitale allocato {a} USDC\)'
        r' e "beta" \(asset "ETH", capitale allocato {b} USDC\)'
    )
)
def two_flows(bench: AttributionBench, account: str, a: str, b: str) -> None:
    bench.add_flow(account, "alfa", ("BTC",), amount(a))
    bench.add_flow(account, "beta", ("ETH",), amount(b))


@given(step(r'che sull\'exchange il conto "{account}" ha posizioni aperte su "{asset}" e su "{other}"'))
def open_positions(bench: AttributionBench, account: str, asset: str, other: str) -> None:
    bench.extend(bench.account(account), positions=(a_position(asset), a_position(other)))


@given(step(r'che le esecuzioni del flusso "{flow}" hanno PnL realizzato {a} USDC e commissioni {b} USDC'))
def fills_with_fees(bench: AttributionBench, flow: str, a: str, b: str) -> None:
    fills_of(bench, flow, amount(a), amount(b))


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
