"""R2.2.3: the equity every cycle records, run as the worker composes the cycle (ADR 0120), and the curve the
dashboard reads from it (ADR 0122). playwright-bdd runs the same scenarios on the build of the dashboard (ADR 0116).
"""

from dataclasses import dataclass, replace
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.flows.read_flow_equity import ReadFlowEquityCommand, ReadFlowEquityUseCase
from autotrading.domain.flows.equity_snapshot import EquitySnapshot, FlowEquity
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.statistics_period import TimeWindow
from tests.fakes.cycles import FakeTransientError
from tests.fakes.equity_snapshots import InMemoryEquitySnapshotRepositoryAdapter
from tests.fakes.flow_repository import InMemoryFlowRepositoryAdapter
from tests.support.activity import a_fill, a_position, an_activity
from tests.support.attribution import amount, step
from tests.support.flow_cycles import FlowCycles, at
from tests.support.steps import quoted

FEATURE = "E2-dashboard-e-confronto/F2.2-monitoraggio/R2.2.3-equity-curve.feature"
CYCLE = timedelta(minutes=15)
EVERY_CYCLE = TimeWindow(None, None)


scenarios(FEATURE)

PERIODS = {"tutta la vita": "all", "7 giorni": "7d", "30 giorni": "30d"}


@dataclass
class Curve:
    """The equity curve the user opened last."""

    seen: FlowEquity | None = None

    @property
    def opened(self) -> FlowEquity:
        assert self.seen is not None, "nessuna equity curve aperta"
        return self.seen

    @property
    def baseline(self) -> Decimal:
        assert self.opened.initial_capital is not None, "la curva di una bozza non ha capitale iniziale"
        return self.opened.initial_capital


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def curve() -> Curve:
    return Curve()


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
        platform.platform_orders.add(order, flow.assigned_account_id, flow.id)
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


def open_curve(flow_cycles: FlowCycles, curve: Curve, name: str, period: str = "all") -> None:
    flow = flow_cycles.flow(name)
    use_case = ReadFlowEquityUseCase(
        InMemoryFlowRepositoryAdapter(flow_cycles.platform.flows, flow.tenant_id),
        equity_of(flow_cycles, flow),
        flow_cycles.clock.now,
    )
    curve.seen = use_case.execute(ReadFlowEquityCommand(flow.id.value, period))


def points_at(curve: Curve, values: str) -> list[EquitySnapshot]:
    wanted = {Decimal(value) for value in values.split(" e ")}
    found = [point for point in curve.opened.snapshots if point.equity in wanted]
    assert {point.equity for point in found} == wanted, f"punti della curva: {curve.opened.snapshots}"
    return found


# Given


@given(step(r'che il flusso "{flow}" ha capitale iniziale {a} USDC'))
def initial_capital(flow_cycles: FlowCycles, flow: str, a: str) -> None:
    flow_cycles.add_flow("anna", flow, assets=("BTC", "ETH"), started="09:00")
    flow_cycles.reconfigure(flow, lambda configuration: replace(configuration, allocated_capital=amount(a)))


@given(parsers.re(r"^che i suoi ultimi tre cicli hanno registrato equity (?P<a>\d+), (?P<b>\d+) e (?P<c>\d+) USDC$"))
def last_three_cycles(flow_cycles: FlowCycles, a: str, b: str, c: str) -> None:
    flow = flow_cycles.platform.flows.flows[-1]
    equity = equity_of(flow_cycles, flow)
    capital = flow.configuration.assigned_capital
    for index, value in enumerate((a, b, c)):
        planned_at = at("09:15") + index * CYCLE
        pnl = Decimal(value) - capital
        equity.record(EquitySnapshot(flow.id.value, planned_at, capital, pnl, Decimal(0), Decimal(0), Decimal(0)))


@given(quoted('che il flusso "{flow}" ha cicli negli ultimi 60 giorni'))
def cycles_of_sixty_days(flow_cycles: FlowCycles, flow: str) -> None:
    created = flow_cycles.flow(flow)
    equity = equity_of(flow_cycles, created)
    capital = created.configuration.assigned_capital
    for days_ago in range(1, 61):
        planned_at = flow_cycles.clock.now() - timedelta(days=days_ago)
        equity.record(
            EquitySnapshot(created.id.value, planned_at, capital, Decimal(0), Decimal(0), Decimal(0), Decimal(0))
        )


@given(quoted('che il flusso "{flow}" non ha ancora cicli'))
def flow_without_cycles(flow_cycles: FlowCycles, flow: str) -> None:
    flow_cycles.add_flow("anna", flow)


# When


@when(quoted('"{user}" apre l\'equity curve del flusso "{flow}"'))
def opens_the_curve(flow_cycles: FlowCycles, curve: Curve, user: str, flow: str) -> None:
    assert flow_cycles.users[flow] == user
    open_curve(flow_cycles, curve, flow)


@when(quoted('"{user}" sceglie il periodo "{period}"'))
def chooses_the_period(flow_cycles: FlowCycles, curve: Curve, user: str, period: str) -> None:
    flow = flow_cycles.platform.flows.flows[-1].name.value
    assert flow_cycles.users[flow] == user
    open_curve(flow_cycles, curve, flow, PERIODS[period])


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
    capital = flow_cycles.flow(flow).configuration.assigned_capital
    attribute(flow_cycles, flow, realized_pnl=amount(a) - capital, unrealized_pnl=Decimal(0), fee=Decimal(0))
    flow_cycles.model.failure = FakeTransientError("il modello non risponde")
    flow_cycles.run(flow, "10:00")
    assert flow_cycles.last_record(flow).failure is not None


# Then


@then(step(r"il ciclo registra equity {a} USDC"))
def cycle_equity(flow_cycles: FlowCycles, a: str) -> None:
    name = flow_cycles.platform.flows.flows[-1].name.value
    assert recorded_at(flow_cycles, name).equity == amount(a)


@then(parsers.re(r"^i punti a (?P<values>[\d e]+) USDC sono nell'area verde$"))
def points_in_the_green(curve: Curve, values: str) -> None:
    assert all(point.equity >= curve.baseline for point in points_at(curve, values))


@then(parsers.re(r"^il punto a (?P<values>\d+) USDC è nell'area rossa$"))
def point_in_the_red(curve: Curve, values: str) -> None:
    assert all(point.equity < curve.baseline for point in points_at(curve, values))


@then("la curva mostra solo i punti degli ultimi 30 giorni")
def only_the_last_thirty_days(flow_cycles: FlowCycles, curve: Curve) -> None:
    since = flow_cycles.clock.now() - timedelta(days=30)
    planned = [point.planned_at for point in curve.opened.snapshots]
    assert planned, "la curva non ha punti"
    assert min(planned) >= since, f"punto più vecchio: {min(planned):%d/%m %H:%M}"
    flow = flow_cycles.platform.flows.flows[-1]
    recorded = equity_of(flow_cycles, flow).of_flow(flow.id.value, EVERY_CYCLE)
    assert len(planned) < len(recorded), f"punti mostrati: {len(planned)} di {len(recorded)}"


@then(quoted('la pagina mostra "{text}"'))
def no_cycles_yet(curve: Curve, text: str) -> None:
    assert text == "Nessun ciclo ancora eseguito"
    assert curve.opened.snapshots == ()
