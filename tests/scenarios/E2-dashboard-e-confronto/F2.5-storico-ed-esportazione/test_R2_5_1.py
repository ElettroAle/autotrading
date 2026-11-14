from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.flows.query_closed_position_history import QueryClosedPositionHistoryCommand
from autotrading.application.flows.query_cycle_history import QueryCycleHistoryCommand
from autotrading.application.flows.query_order_history import QueryOrderHistoryCommand
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.history import (
    ClosedPositionHistoryEntry,
    CycleHistoryEntry,
    HistoryEntry,
    HistoryFilter,
    OrderExecution,
    OrderHistoryEntry,
)
from autotrading.domain.flows.statistics_period import StatisticsPeriod, StatisticsPeriodKind
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_history import HistoryRow
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E2-dashboard-e-confronto/F2.5-storico-ed-esportazione/R2.5.1-storico-interrogabile.feature")

YEAR = 2026
NOVEMBER = 11
ASSETS = ("BTC", "ETH")


def day_of_november(day: int) -> datetime:
    return datetime(YEAR, NOVEMBER, day, 11, tzinfo=UTC)


@dataclass(frozen=True)
class OwnedFlow:
    """A flow of a user on an account, as the histories name it."""

    tenant_id: TenantId
    flow_id: UUID
    name: str
    account_id: UUID
    account: str


@dataclass
class History:
    platform: Platform = field(default_factory=Platform)
    flows: dict[str, OwnedFlow] = field(default_factory=dict)
    accounts: dict[str, UUID] = field(default_factory=dict)
    first_of_version_two: int = 1
    found: tuple[HistoryEntry, ...] = ()
    refusal: AutotradingError | None = None

    def flow(self, user: str, name: str, account: str = "principale") -> OwnedFlow:
        account_id = self.accounts.setdefault(account, uuid4())
        owned = OwnedFlow(self.platform.tenant_of(user), uuid4(), name, account_id, account)
        self.flows[name] = owned
        return owned

    def version_on(self, day: int) -> int:
        return 2 if day >= self.first_of_version_two else 1

    def add_cycles(self, owned: OwnedFlow, days: range) -> None:
        store = self.platform.history_of(owned.tenant_id).store
        for day in days:
            planned_at = day_of_november(day)
            version = self.version_on(day)
            record = CycleRecord(owned.flow_id, planned_at, CycleOutcome.COMPLETED, planned_at)
            entry = CycleHistoryEntry(owned.name, version, record)
            store.cycles.append(
                HistoryRow(entry, owned.account_id, owned.flow_id, planned_at, frozenset(ASSETS), version)
            )

    def add_closed_position(self, owned: OwnedFlow, asset: str, closed_at: datetime) -> None:
        position = ClosedPosition(
            tenant_id=owned.tenant_id,
            flow_id=FlowId(owned.flow_id),
            asset=asset,
            side=TradeSide.LONG,
            leverage=2,
            margin=Decimal(100),
            opening=PositionEnd(Decimal(3000), closed_at - timedelta(hours=2)),
            closing=PositionEnd(Decimal(3150), closed_at),
            fees=Decimal("0.42"),
            reason=CloseReason.AGENT,
        )
        entry = ClosedPositionHistoryEntry(uuid4(), owned.name, position)
        store = self.platform.history_of(owned.tenant_id).store
        version = self.version_on(closed_at.day)
        store.closed_positions.append(
            HistoryRow(entry, owned.account_id, owned.flow_id, closed_at, frozenset({asset}), version)
        )

    def add_order(self, owned: OwnedFlow, asset: str, created_at: datetime) -> None:
        executions = (
            OrderExecution(created_at + timedelta(seconds=1), Decimal("91000.5"), Decimal("0.015"), Decimal("0.41")),
            OrderExecution(created_at + timedelta(seconds=2), Decimal("91001"), Decimal("0.005"), Decimal("0.14")),
        )
        entry = OrderHistoryEntry(
            order_id=uuid4(),
            created_at=created_at,
            account_id=owned.account_id,
            account_name=owned.account,
            flow_id=owned.flow_id,
            flow_name=owned.name,
            asset=asset,
            direction="long",
            closing=False,
            leverage=2,
            requested_size=Decimal("0.02"),
            status="eseguito",
            origin="flusso",
            executions=executions,
        )
        store = self.platform.history_of(owned.tenant_id).store
        version = self.version_on(created_at.day)
        store.orders.append(HistoryRow(entry, owned.account_id, owned.flow_id, created_at, frozenset({asset}), version))


@pytest.fixture
def history() -> History:
    scenario_history = History()
    scenario_history.platform.now = datetime(YEAR, 12, 1, tzinfo=UTC)
    return scenario_history


@given(
    parsers.re(
        r'^che "(?P<user>[^"]+)" ha il flusso "(?P<flow>[^"]+)" sul conto "(?P<account>[^"]+)" con cicli dal '
        r"(?P<first>\d+)° al (?P<last>\d+) novembre e la versione 2 in vigore dal (?P<since>\d+) novembre$"
    )
)
def flow_with_cycles(
    history: History, *, user: str, flow: str, account: str, first: str, last: str, since: str
) -> None:
    history.first_of_version_two = int(since)
    owned = history.flow(user, flow, account)
    history.add_cycles(owned, range(int(first), int(last) + 1))


@given(quoted('che il flusso "{flow}" ha ordini e posizioni chiuse su "{first}" e "{second}"'))
def orders_and_positions(history: History, flow: str, first: str, second: str) -> None:
    owned = history.flows[flow]
    for day in range(1, 31):
        for asset in (first, second):
            history.add_closed_position(owned, asset, day_of_november(day))
            history.add_order(owned, asset, day_of_november(day))


@given(quoted('che "{user}" ha il flusso "{flow}"'))
def other_flow(history: History, user: str, flow: str) -> None:
    owned = history.flow(user, flow, account="secondario")
    history.add_closed_position(owned, "BTC", day_of_november(5))


@when(quoted('"{user}" interroga i cicli del flusso "{flow}" con la versione {version}'))
def query_cycles_of_version(history: History, user: str, flow: str, version: str) -> None:
    criteria = HistoryFilter(flow_id=history.flows[flow].flow_id, version=int(version))
    page = history.platform.use_cases_of(user).query_cycle_history.execute(QueryCycleHistoryCommand(criteria))
    history.found = page.entries


@when(quoted('"{user}" interroga le posizioni chiuse con asset "{asset}" dal {first} al {last} novembre'))
def query_positions_in_range(history: History, user: str, asset: str, first: str, last: str) -> None:
    period = StatisticsPeriod(
        StatisticsPeriodKind.RANGE, date(YEAR, NOVEMBER, int(first)), date(YEAR, NOVEMBER, int(last))
    )
    command = QueryClosedPositionHistoryCommand(HistoryFilter(period=period, asset=asset))
    history.found = history.platform.use_cases_of(user).query_closed_position_history.execute(command).entries


@when(quoted('"{user}" interroga gli ordini del conto "{account}"'))
def query_orders_of_account(history: History, user: str, account: str) -> None:
    command = QueryOrderHistoryCommand(HistoryFilter(account_id=history.accounts[account]))
    history.found = history.platform.use_cases_of(user).query_order_history.execute(command).entries


@when(quoted('"{user}" interroga i cicli con la versione {version} senza indicare un flusso'))
def query_version_without_flow(history: History, user: str, version: str) -> None:
    use_case = history.platform.use_cases_of(user).query_cycle_history
    try:
        use_case.execute(QueryCycleHistoryCommand(HistoryFilter(version=int(version))))
    except AutotradingError as error:
        history.refusal = error


@when(quoted('"{user}" interroga le posizioni chiuse con asset "{asset}"'))
def query_positions_of_asset(history: History, user: str, asset: str) -> None:
    command = QueryClosedPositionHistoryCommand(HistoryFilter(asset=asset))
    history.found = history.platform.use_cases_of(user).query_closed_position_history.execute(command).entries


@then(quoted("ottiene solo i cicli dal {day} novembre in poi"))
def only_cycles_since(history: History, day: str) -> None:
    cycles = [entry for entry in history.found if isinstance(entry, CycleHistoryEntry)]
    assert len(cycles) == len(history.found)
    assert [cycle.record.planned_at.day for cycle in cycles] == list(range(30, int(day) - 1, -1))
    assert {cycle.version for cycle in cycles} == {2}


@then(quoted('ottiene solo le posizioni su "{asset}" chiuse in quel periodo'))
def only_positions_in_period(history: History, asset: str) -> None:
    positions = [entry.position for entry in history.found if isinstance(entry, ClosedPositionHistoryEntry)]
    assert len(positions) == len(history.found)
    assert {position.asset for position in positions} == {asset}
    assert [position.closing.at.day for position in positions] == list(range(20, 9, -1))


@then("ogni ordine mostra le sue esecuzioni con prezzo, quantità e commissioni")
def orders_with_executions(history: History) -> None:
    orders = [entry for entry in history.found if isinstance(entry, OrderHistoryEntry)]
    assert len(orders) == len(history.found) == 50
    assert {order.account_name for order in orders} == {"principale"}
    for order in orders:
        assert [(execution.price, execution.size, execution.fee) for execution in order.executions] == [
            (Decimal("91000.5"), Decimal("0.015"), Decimal("0.41")),
            (Decimal("91001"), Decimal("0.005"), Decimal("0.14")),
        ]


@then(quoted('l\'interrogazione è rifiutata con il motivo "{reason}"'))
def refused(history: History, reason: str) -> None:
    assert history.refusal is not None
    assert str(history.refusal) == reason
    assert history.refusal.status_code == 400


@then(quoted('non ottiene alcuna posizione del flusso "{flow}"'))
def no_position_of(history: History, flow: str) -> None:
    positions = [entry for entry in history.found if isinstance(entry, ClosedPositionHistoryEntry)]
    assert positions
    assert all(entry.position.flow_id.value != history.flows[flow].flow_id for entry in positions)
    assert {entry.flow_name for entry in positions} == {"omega"}
