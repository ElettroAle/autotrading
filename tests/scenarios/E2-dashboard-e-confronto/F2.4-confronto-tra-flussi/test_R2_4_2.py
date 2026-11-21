"""R2.4.2: the ranking of the flows of the user, computed on the use cases (ADR 0135). playwright-bdd runs the same
scenarios on the ranking page of the dashboard (ADR 0136).
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.flows.rank_flows import RankFlowsCommand
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_ranking import FlowRanking
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.trade_side import TradeSide
from tests.fakes.equity_snapshots import InMemoryEquitySnapshotRepositoryAdapter
from tests.support.flows import a_flow
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E2-dashboard-e-confronto/F2.4-confronto-tra-flussi/R2.4.2-classifica-dei-flussi.feature")

PERIODS = {"tutta la vita": "all", "7 giorni": "7d", "30 giorni": "30d"}
CYCLE = timedelta(minutes=15)
LONG_AGO = timedelta(days=20)
TWO_DECIMALS = Decimal("0.01")
POSITIONS = {"primo": 0, "secondo": 1, "terzo": 2}
STATUSES = {"archiviato": FlowStatus.ARCHIVED, "in bozza": FlowStatus.DRAFT}


def amount(text: str) -> Decimal:
    return Decimal(text.replace(",", ".").replace("+", ""))


def amounts(text: str) -> list[Decimal]:
    return [amount(item) for item in text.replace(" e ", ", ").split(", ")]


@dataclass
class FlowCurve:
    """The equity of the cycles of a flow, oldest first, and which of them fall in the last 7 days."""

    user: str
    equity: list[Decimal]
    recent: int
    status: FlowStatus = FlowStatus.ACTIVE
    results: list[Decimal] = field(default_factory=list)
    fees: Decimal = Decimal(0)
    model_cost: Decimal = Decimal(0)

    def planned(self, now: datetime) -> list[datetime]:
        old = len(self.equity) - self.recent
        return [now - LONG_AGO - (old - index) * CYCLE for index in range(old)] + [
            now - (self.recent - index) * CYCLE for index in range(self.recent)
        ]


@dataclass
class Ranking:
    platform: Platform = field(default_factory=Platform)
    curves: dict[str, FlowCurve] = field(default_factory=dict)
    owner: str = ""
    rows: tuple[FlowRanking, ...] | None = None

    def give(
        self,
        user: str,
        flow: str,
        equity: list[Decimal],
        *,
        recent: bool = True,
        status: FlowStatus = FlowStatus.ACTIVE,
    ) -> None:
        self.curves[flow] = FlowCurve(user, equity, len(equity) if recent else 0, status)

    def open(self, user: str, period: str = "all") -> None:
        for name, curve in self.curves.items():
            self._record(name, curve)
        self.curves.clear()
        self.rows = self.platform.use_cases_of(user).rank_flows.execute(RankFlowsCommand(period))

    def shown(self) -> tuple[FlowRanking, ...]:
        assert self.rows is not None, "nessuna classifica aperta"
        return self.rows

    def row_of(self, flow: str) -> FlowRanking:
        found = [row for row in self.shown() if row.flow_name == flow]
        assert len(found) == 1, f"righe di {flow}: {[row.flow_name for row in self.shown()]}"
        return found[0]

    def names(self) -> list[str]:
        return [row.flow_name for row in self.shown()]

    def _record(self, name: str, curve: FlowCurve) -> None:
        flow = a_flow(self.platform.tenant_of(curve.user), name=name, status=curve.status)
        self.platform.flows.flows.append(flow)
        equity = InMemoryEquitySnapshotRepositoryAdapter(self.platform.equity_snapshots, flow.tenant_id)
        for planned_at, value in zip(curve.planned(self.platform.now), curve.equity, strict=True):
            equity.record(_snapshot(flow, planned_at, value))
        closed_at = self.platform.now - CYCLE
        share = curve.fees / len(curve.results) if curve.results else Decimal(0)
        for result in curve.results:
            self.platform.closed_positions.positions.append(_position(flow, closed_at, result, share))
        cost = CallCost(1000, 100, curve.model_cost)
        self.platform.cycles.record(CycleRecord(flow.id.value, closed_at, CycleOutcome.COMPLETED, cost=cost))


def _snapshot(flow: Flow, planned_at: datetime, equity: Decimal) -> EquitySnapshot:
    capital = flow.configuration.allocated_capital
    assert capital is not None, "a flow that records its equity has an allocated capital"
    return EquitySnapshot(flow.id.value, planned_at, capital, equity - capital, Decimal(0), Decimal(0), Decimal(0))


def _position(flow: Flow, closed_at: datetime, net_pnl: Decimal, fees: Decimal) -> ClosedPosition:
    return ClosedPosition(
        tenant_id=flow.tenant_id,
        flow_id=flow.id,
        asset="BTC",
        side=TradeSide.LONG,
        leverage=2,
        margin=Decimal(50),
        opening=PositionEnd(Decimal(100), closed_at - CYCLE),
        closing=PositionEnd(Decimal(100), closed_at),
        fees=fees,
        reason=CloseReason.AGENT,
        realized_pnl=net_pnl + fees,
    )


def percent(value: Decimal | None) -> Decimal | None:
    return None if value is None else value.quantize(TWO_DECIMALS)


@pytest.fixture
def ranking() -> Ranking:
    return Ranking()


# Given


@given(quoted('che "{user}" ha il flusso "{flow}" con equity per ciclo {values} USDC'))
def flow_with_equity(ranking: Ranking, user: str, flow: str, values: str) -> None:
    ranking.owner = user
    ranking.give(user, flow, amounts(values))


@given(quoted('che "{user}" ha il flusso "{flow}"'))
def flow_of_another_user(ranking: Ranking, user: str, flow: str) -> None:
    # A curve that would top the ranking if it leaked into the ranking of another user.
    ranking.give(user, flow, [Decimal(100), Decimal(400)])


@given(quoted('che "{user}" ha il flusso "{flow}" {status} con equity per ciclo {values} USDC'))
def flow_out_of_work(ranking: Ranking, user: str, flow: str, status: str, values: str) -> None:
    ranking.give(user, flow, amounts(values), status=STATUSES[status])


@given(
    parsers.re(
        r'^che "(?P<flow>[^"]+)" ha chiuso posizioni con PnL netto (?P<results>.+) USDC, commissioni totali '
        r"(?P<fees>[\d,]+) USDC e costo del modello (?P<cost>[\d,]+) USD$"
    )
)
def flow_trades(ranking: Ranking, flow: str, results: str, fees: str, cost: str) -> None:
    curve = ranking.curves[flow]
    curve.results, curve.fees, curve.model_cost = amounts(results), amount(fees), amount(cost)


@given(quoted('che negli ultimi 7 giorni "{flow}" ha equity {values} USDC'))
def recent_equity(ranking: Ranking, flow: str, values: str) -> None:
    curve = ranking.curves[flow]
    recent = amounts(values)
    assert curve.equity[-len(recent) :] == recent, f"equity di {flow}: {curve.equity}"
    curve.recent = len(recent)


@given(quoted('che il flusso "{flow}" non ha cicli negli ultimi 7 giorni'))
def flow_without_recent_cycles(ranking: Ranking, flow: str) -> None:
    # Cycles older than the period, with a return that would top the ranking if they counted.
    ranking.give(ranking.owner, flow, [Decimal(100), Decimal(500)], recent=False)


# When


@when(quoted('"{user}" apre la classifica'))
def open_ranking(ranking: Ranking, user: str) -> None:
    ranking.open(user)


@when(quoted('"{user}" ordina la classifica per drawdown massimo crescente'))
def sort_by_drawdown(ranking: Ranking, user: str) -> None:
    # The API answers by return; ordering by another column is the client's, on the values received (ADR 0135).
    ranking.open(user)
    ranking.rows = tuple(sorted(ranking.shown(), key=lambda row: row.max_drawdown_percent))


@when(quoted('"{user}" sceglie il periodo "{period}"'))
def choose_period(ranking: Ranking, user: str, period: str) -> None:
    ranking.open(user, PERIODS[period])


# Then


@then(
    parsers.re(
        r'^"(?P<flow>[^"]+)" è (?P<position>primo|secondo|terzo) con rendimento (?P<result>[+-][\d,]+)% e drawdown '
        r"massimo (?P<drawdown>[\d,]+)%$"
    )
)
def ranked_flow(ranking: Ranking, flow: str, position: str, result: str, drawdown: str) -> None:
    assert ranking.names().index(flow) == POSITIONS[position], f"classifica: {ranking.names()}"
    row = ranking.row_of(flow)
    assert percent(row.return_percent) == amount(result)
    assert percent(row.max_drawdown_percent) == amount(drawdown)


@then(quoted('"{flow}" è primo'))
def first_flow(ranking: Ranking, flow: str) -> None:
    assert ranking.names()[0] == flow, f"classifica: {ranking.names()}"


@then(parsers.re(r'^"(?P<flow>[^"]+)" mostra rendimento (?P<result>[+-][\d,]+)% e drawdown massimo (?P<dd>[\d,]+)%$'))
def flow_values(ranking: Ranking, flow: str, result: str, dd: str) -> None:
    row = ranking.row_of(flow)
    assert percent(row.return_percent) == amount(result)
    assert percent(row.max_drawdown_percent) == amount(dd)


@then(quoted('la classifica non contiene "{flow}"'))
def not_in_ranking(ranking: Ranking, flow: str) -> None:
    assert ranking.shown(), "la classifica è vuota"
    assert flow not in ranking.names(), f"classifica: {ranking.names()}"


@then(quoted('la riga di "{flow}" nella classifica mostra:'))
def row_columns(ranking: Ranking, flow: str, datatable: list[list[str]]) -> None:
    statistics = ranking.row_of(flow).statistics
    shown = {
        "PnL": statistics.net_pnl,
        "Commissioni": statistics.total_fees,
        "Win rate": percent(statistics.win_rate_percent),
        "Operazioni": Decimal(statistics.operations),
        "Costo del modello IA": statistics.model_cost_usd,
    }
    expected = {column: amount(value.split(" ")[0].rstrip("%")) for column, value in datatable[1:]}
    assert {column: shown[column] for column in expected} == expected
