"""R2.2.3: the equity every cycle records, run as the worker composes the cycle (ADR 0120).

The scenarios of the curve itself (colours, period, a flow without cycles) are the dashboard's: playwright-bdd runs
them on the build of the dashboard (ADR 0116, ADR 0121).
"""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from autotrading.domain.flows.equity_period import EquityWindow
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.flow import Flow
from tests.fakes.cycles import FakeTransientError
from tests.fakes.equity_snapshots import InMemoryEquitySnapshotRepositoryAdapter
from tests.support.activity import a_fill, a_position, an_activity
from tests.support.attribution import amount, step
from tests.support.flow_cycles import FlowCycles, at

FEATURE = "E2-dashboard-e-confronto/F2.2-monitoraggio/R2.2.3-equity-curve.feature"
CYCLE = timedelta(minutes=15)
EVERY_CYCLE = EquityWindow(None, None)


@scenario(FEATURE, "Punto di equity registrato a ogni ciclo")
def test_equity_recorded_at_every_cycle() -> None:
    """The cycle records the equity of the state of the flow at its end."""


@scenario(FEATURE, "Punto registrato anche per un ciclo fallito")
def test_equity_recorded_for_a_failed_cycle() -> None:
    """A cycle failed after reading the state records the equity of the state it read."""


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    return FlowCycles()


def equity_of(flow_cycles: FlowCycles, flow: Flow) -> InMemoryEquitySnapshotRepositoryAdapter:
    return InMemoryEquitySnapshotRepositoryAdapter(flow_cycles.equity_snapshots, flow.tenant_id)


def attribute(
    flow_cycles: FlowCycles, name: str, *, realized_pnl: Decimal, unrealized_pnl: Decimal, fee: Decimal
) -> None:
    """What the exchange shows of the account: a trade on ETH opened and closed, a position on BTC still open."""
    flow = flow_cycles.flow(name)
    platform = flow_cycles.platform
    address = flow_cycles.credentials_of(name).account_address
    opened_at = flow_cycles.clock.now() - timedelta(minutes=10)
    orders = (uuid4(), uuid4())
    for order in orders:
        platform.platform_orders.add(order, flow.account_id, flow.id)
    platform.activity_reader.executions.setdefault(address, []).extend(
        (
            a_fill("BTC", orders[0], fill_id=f"{orders[0]}-1", executed_at=opened_at),
            a_fill("ETH", orders[1], fill_id=f"{orders[1]}-1", executed_at=opened_at),
            a_fill(
                "ETH",
                orders[1],
                realized_pnl=realized_pnl,
                fee=fee,
                fill_id=f"{orders[1]}-2",
                executed_at=opened_at + timedelta(minutes=1),
                size=Decimal(-1),
                start_position=Decimal(1),
            ),
        )
    )
    position = a_position("BTC", margin=Decimal(20), unrealized_pnl=unrealized_pnl)
    platform.activity_reader.activities[address] = an_activity(positions=(position,))


def recorded_at(flow_cycles: FlowCycles, name: str) -> EquitySnapshot:
    flow = flow_cycles.flow(name)
    planned_at = flow_cycles.last_record(name).planned_at
    found = [
        item
        for item in equity_of(flow_cycles, flow).of_flow(flow.id.value, EVERY_CYCLE)
        if item.planned_at == planned_at
    ]
    assert len(found) == 1, f"equity registrate per il ciclo delle {planned_at:%H:%M}: {len(found)}"
    return found[0]


# Given


@given(step(r'che il flusso "{flow}" ha capitale iniziale {a} USDC'))
def initial_capital(flow_cycles: FlowCycles, flow: str, a: str) -> None:
    flow_cycles.add_flow("anna", flow, assets=("BTC", "ETH"), started="09:00")
    flow_cycles.reconfigure(flow, lambda configuration: replace(configuration, allocated_capital=amount(a)))


@given(parsers.re(r"^che i suoi ultimi tre cicli hanno registrato equity (?P<a>\d+), (?P<b>\d+) e (?P<c>\d+) USDC$"))
def last_three_cycles(flow_cycles: FlowCycles, a: str, b: str, c: str) -> None:
    flow = flow_cycles.platform.flows.flows[-1]
    equity = equity_of(flow_cycles, flow)
    capital = flow.configuration.allocated_capital
    for index, value in enumerate((a, b, c)):
        planned_at = at("09:15") + index * CYCLE
        pnl = Decimal(value) - capital
        equity.record(EquitySnapshot(flow.id.value, planned_at, capital, pnl, Decimal(0), Decimal(0), Decimal(0)))


# When


@when(
    step(
        r'il flusso "{flow}" conclude un ciclo con capitale allocato {a} USDC, PnL realizzato {b} USDC, '
        r"PnL non realizzato {c} USDC e commissioni (?P<fee>\d+) USDC"
    )
)
def completed_cycle(flow_cycles: FlowCycles, *, flow: str, a: str, b: str, c: str, fee: str) -> None:
    assert flow_cycles.flow(flow).configuration.allocated_capital == amount(a)
    attribute(flow_cycles, flow, realized_pnl=amount(b), unrealized_pnl=amount(c), fee=Decimal(fee))
    flow_cycles.run(flow, "10:00")


@when(step(r'un ciclo del flusso "{flow}" fallisce dopo la lettura dello stato con equity {a} USDC'))
def failed_cycle(flow_cycles: FlowCycles, flow: str, a: str) -> None:
    capital = flow_cycles.flow(flow).configuration.allocated_capital
    attribute(flow_cycles, flow, realized_pnl=amount(a) - capital, unrealized_pnl=Decimal(0), fee=Decimal(0))
    flow_cycles.model.failure = FakeTransientError("il modello non risponde")
    flow_cycles.run(flow, "10:00")
    assert flow_cycles.last_record(flow).failure is not None


# Then


@then(step(r"il ciclo registra equity {a} USDC"))
def cycle_equity(flow_cycles: FlowCycles, a: str) -> None:
    name = flow_cycles.platform.flows.flows[-1].name.value
    assert recorded_at(flow_cycles, name).equity == amount(a)
