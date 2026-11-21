"""The steps of the scenarios of the periods of the menu, computed on the use cases (R6.4.6, R6.4.7; ADR
periodi-brevi-come-durata-nel-dominio, ADR periodo-di-6-ore-e-dall-inizio).

A scenario module imports them all; pytest-bdd keeps each step as a fixture of this module.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from pytest_bdd import given, parsers, then, when

from autotrading.application.flows.list_closed_positions import ListClosedPositionsCommand
from autotrading.application.flows.list_cycles import ListCyclesCommand
from autotrading.application.flows.rank_flows import RankFlowsCommand
from autotrading.application.flows.read_flow_equity import ReadFlowEquityCommand
from autotrading.application.flows.read_flow_results import ReadFlowResultsCommand
from autotrading.application.flows.read_flow_statistics import ReadFlowStatisticsCommand
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.closed_position_filter import ClosedPositionFilter
from autotrading.domain.flows.cycle_filter import CycleFilter
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.errors import InvalidStatisticsPeriodError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_return import FlowReturn
from autotrading.domain.flows.statistics_period import StatisticsPeriod, StatisticsPeriodKind, TimeWindow
from autotrading.domain.flows.trade_side import TradeSide
from tests.fakes.equity_snapshots import InMemoryEquitySnapshotRepositoryAdapter
from tests.support.flows import a_configuration, a_flow, account_id_of
from tests.support.platform import Platform
from tests.support.steps import quoted

NOW = datetime(2026, 11, 16, 10, 15, tzinfo=UTC)
CAPITAL = Decimal(500)
HISTORY = timedelta(days=30)
EQUITY_STEP = Decimal("0.1")
PERIODS = {
    "30 minuti": "30m",
    "1 ora": "1h",
    "6 ore": "6h",
    "12 ore": "12h",
    "24 ore": "24h",
    "7 giorni": "7d",
    "30 giorni": "30d",
    "Dall'inizio": "all",
    "Intervallo": "range",
}
LABELS = {name: label for label, name in PERIODS.items()}


@dataclass
class Readings:
    """The flows of the scenario, the period the user chose and what the use cases read in it."""

    platform: Platform = field(default_factory=Platform)
    flows: dict[str, Flow] = field(default_factory=dict)
    planned: dict[str, list[datetime]] = field(default_factory=dict)
    menu: list[str] = field(default_factory=list)
    period: str = StatisticsPeriodKind.ALL.value
    page_flow: str = "alfa"
    refused: InvalidStatisticsPeriodError | None = None

    def give(self, name: str, every: timedelta, last_ago: timedelta = timedelta(0)) -> None:
        """A flow of anna with a cycle every `every` in the last 30 days, the last one `last_ago` before now: each cycle
        closes a position and records an equity higher than the one before.
        """
        configuration = a_configuration(assets=("BTC",), allocated_capital=CAPITAL)
        account_id = account_id_of(self.platform, "anna")
        flow = a_flow(self.platform.tenant_of("anna"), name=name, account_id=account_id, configuration=configuration)
        self.platform.flows.flows.append(flow)
        self.flows[name] = flow
        count = int(HISTORY / every)
        self.planned[name] = [NOW - last_ago - (count - 1 - index) * every for index in range(count)]
        equity = InMemoryEquitySnapshotRepositoryAdapter(self.platform.equity_snapshots, flow.tenant_id)
        for index, planned_at in enumerate(self.planned[name]):
            self.platform.cycles.record(CycleRecord(flow.id.value, planned_at, CycleOutcome.COMPLETED))
            gain = index * EQUITY_STEP
            equity.record(EquitySnapshot(flow.id.value, planned_at, CAPITAL, gain, Decimal(0), Decimal(0), Decimal(0)))
            self.platform.closed_positions.positions.append(_position(flow, planned_at))

    def flow_id(self, name: str) -> UUID:
        return self.flows[name].id.value

    def list_window(self) -> TimeWindow:
        """The minutes the dashboard asks the lists of cycles and closed positions for: those of the period."""
        return StatisticsPeriod.named(self.period).window(self.platform.now)

    def planned_since(self, name: str, since: datetime) -> list[datetime]:
        return [planned_at for planned_at in self.planned[name] if since <= planned_at <= self.platform.now]


def _position(flow: Flow, closed_at: datetime) -> ClosedPosition:
    return ClosedPosition(
        tenant_id=flow.tenant_id,
        flow_id=flow.id,
        asset="BTC",
        side=TradeSide.LONG,
        leverage=2,
        margin=Decimal(50),
        opening=PositionEnd(Decimal(100), closed_at - timedelta(minutes=5)),
        closing=PositionEnd(Decimal(101), closed_at),
        fees=Decimal("0.1"),
        reason=CloseReason.AGENT,
        realized_pnl=Decimal(1),
    )


def clock(text: str) -> datetime:
    hours, minutes = text.split(":")
    return NOW.replace(hour=int(hours), minute=int(minutes))


@pytest.fixture
def readings() -> Readings:
    found = Readings()
    found.platform.now = NOW
    return found


# Given


@given(quoted('che "anna" ha il flusso "{flow}" con un ciclo ogni 15 minuti negli ultimi 30 giorni'))
def flow_every_quarter(readings: Readings, flow: str) -> None:
    readings.give(flow, timedelta(minutes=15))


@given(parsers.re(r"^che sono le (?P<time>\d{1,2}:\d{2})$"))
def it_is(readings: Readings, time: str) -> None:
    readings.platform.now = clock(time)


@given(
    parsers.re(
        r'^che il flusso "(?P<flow>[^"]+)" ha un ciclo ogni (?P<every>\d+) minuti e l\'ultimo (?P<ago>\d+) minuti fa$'
    )
)
def flow_with_last_cycle(readings: Readings, flow: str, every: str, ago: str) -> None:
    readings.give(flow, timedelta(minutes=int(every)), timedelta(minutes=int(ago)))


@given(parsers.re(r'^che l\'ultimo ciclo del flusso "(?P<flow>[^"]+)" è di (?P<ago>\d+) minuti fa$'))
def last_cycle_ago(readings: Readings, flow: str, ago: str) -> None:
    readings.give(flow, timedelta(hours=1), timedelta(minutes=int(ago)))


# When


@when(quoted('"anna" apre il menu del periodo nella pagina del flusso "{flow}"'))
def open_menu(readings: Readings, flow: str) -> None:
    readings.menu = [LABELS[kind.value] for kind in StatisticsPeriodKind]
    readings.period = ReadFlowEquityCommand(readings.flow_id(flow)).period


@when(parsers.re(r'^"anna" sceglie il periodo "(?P<label>[^"]+)"(?: nella classifica dei flussi)?$'))
def choose_period(readings: Readings, label: str) -> None:
    readings.period = PERIODS[label]


@when(quoted('"anna" sceglie il periodo "{label}" nella pagina del flusso "{flow}"'))
def choose_flow_period(readings: Readings, label: str, flow: str) -> None:
    readings.period = PERIODS[label]
    readings.page_flow = flow


@when(quoted('"anna" apre la pagina del flusso "{flow}" da un indirizzo salvato con il periodo "{period}"'))
def open_saved_address(readings: Readings, flow: str, period: str) -> None:
    # The value saved before the label changed is still a period the API knows (ADR periodo-di-6-ore-e-dall-inizio).
    readings.period = StatisticsPeriod.named(period).kind.value
    readings.page_flow = flow


@when(quoted('l\'interfaccia programmatica riceve il periodo "{period}"'))
def receive_period(readings: Readings, period: str) -> None:
    command = ReadFlowStatisticsCommand(readings.flow_id("alfa"), period)
    with pytest.raises(InvalidStatisticsPeriodError) as raised:
        readings.platform.use_cases_of("anna").read_flow_statistics.execute(command)
    readings.refused = raised.value


# Then


@then(parsers.re(r"^vede in ordine (?P<labels>.+)$"))
def menu_in_order(readings: Readings, labels: str) -> None:
    assert readings.menu == [label.strip().strip('"') for label in labels.split(",")]


@then(quoted('il periodo scelto è "{label}"'))
def chosen_period(readings: Readings, label: str) -> None:
    assert readings.period == PERIODS[label]


@then(
    parsers.re(
        r"^riepilogo, equity curve, statistiche, posizioni chiuse e cicli valgono dalle (?P<since>\d{1,2}:\d{2}) a ora$"
    )
)
def readings_since(readings: Readings, since: str) -> None:
    flow_id = readings.flow_id("alfa")
    use_cases = readings.platform.use_cases_of("anna")
    expected = readings.planned_since("alfa", clock(since))
    assert expected[0] == clock(since), f"cicli dalle {since}: {expected}"

    results = use_cases.read_flow_results.execute(ReadFlowResultsCommand(flow_id, readings.period))
    assert results.period_gain == (len(expected) - 1) * EQUITY_STEP

    equity = use_cases.read_flow_equity.execute(ReadFlowEquityCommand(flow_id, readings.period))
    assert sorted(point.planned_at for point in equity.snapshots) == expected

    statistics = use_cases.read_flow_statistics.execute(ReadFlowStatisticsCommand(flow_id, readings.period))
    assert statistics.operations == len(expected)

    positions_filter = ClosedPositionFilter(window=readings.list_window())
    positions = use_cases.list_closed_positions.execute(ListClosedPositionsCommand(flow_id, criteria=positions_filter))
    assert sorted(position.closing.at for position in positions.positions) == expected

    cycles = use_cases.list_cycles.execute(
        ListCyclesCommand(flow_id, criteria=CycleFilter(window=readings.list_window()))
    )
    assert sorted(cycle.planned_at for cycle in cycles.cycles) == expected


@then("il guadagno nel periodo vale dal primo ciclo del flusso")
def gain_since_the_first_cycle(readings: Readings) -> None:
    flow_id = readings.flow_id(readings.page_flow)
    command = ReadFlowResultsCommand(flow_id, readings.period)
    results = readings.platform.use_cases_of("anna").read_flow_results.execute(command)
    assert results.period_gain == (len(readings.planned[readings.page_flow]) - 1) * EQUITY_STEP


@then(quoted('l\'indirizzo della pagina porta il periodo "{period}"'))
def period_of_the_address(readings: Readings, period: str) -> None:
    assert readings.period == period
    assert StatisticsPeriod.named(period).kind.value == period


@then(parsers.re(r"^il rendimento di ogni flusso è calcolato sulle ultime (?P<hours>\d+) ore$"))
def ranking_on_the_last_hours(readings: Readings, hours: str) -> None:
    rows = readings.platform.use_cases_of("anna").rank_flows.execute(RankFlowsCommand(readings.period))
    assert [row.flow_name for row in rows] == list(readings.flows)
    for row in rows:
        planned = set(readings.planned_since(row.flow_name, readings.platform.now - timedelta(hours=int(hours))))
        equity = InMemoryEquitySnapshotRepositoryAdapter(
            readings.platform.equity_snapshots, readings.flows[row.flow_name].tenant_id
        )
        last_hours = [
            snapshot for snapshot in equity.of_flow(row.flow_id, TimeWindow()) if snapshot.planned_at in planned
        ]
        assert row.return_percent == FlowReturn.over(last_hours, ()).percent


@then(parsers.re(r"^l\'equity curve mostra il solo punto del ciclo di (?P<ago>\d+) minuti fa$"))
def single_point(readings: Readings, ago: str) -> None:
    equity = readings.platform.use_cases_of("anna").read_flow_equity.execute(
        ReadFlowEquityCommand(readings.flow_id(readings.page_flow), readings.period)
    )
    assert [point.planned_at for point in equity.snapshots] == [readings.platform.now - timedelta(minutes=int(ago))]


@then('l\'equity curve dice "nessun ciclo nel periodo"')
def no_cycle(readings: Readings) -> None:
    equity = readings.platform.use_cases_of("anna").read_flow_equity.execute(
        ReadFlowEquityCommand(readings.flow_id(readings.page_flow), readings.period)
    )
    assert equity.snapshots == ()


@then('le statistiche dicono "nessuna operazione nel periodo"')
def no_operation(readings: Readings) -> None:
    statistics = readings.platform.use_cases_of("anna").read_flow_statistics.execute(
        ReadFlowStatisticsCommand(readings.flow_id(readings.page_flow), readings.period)
    )
    assert statistics.operations == 0


@then("risponde 400 con l'elenco dei periodi validi")
def refused_with_the_periods(readings: Readings) -> None:
    assert readings.refused is not None
    assert readings.refused.status_code == 400
    assert readings.refused.reason == "scegliere tra " + ", ".join(kind.value for kind in StatisticsPeriodKind)
