from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Connection, Engine, func, insert, select

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.closed_position_repository import (
    SqlAlchemyClosedPositionRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.cycle_repository import SqlAlchemyCycleRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_history import SqlAlchemyFlowHistoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import account_fills, flow_versions, orders
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.history import HistoryCursor, HistoryFilter, HistoryQuery
from autotrading.domain.flows.statistics_period import StatisticsPeriod, TimeWindow
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow

pytestmark = pytest.mark.integration

# The first version of a flow is saved now: the history of the test lies in the days after it.
START = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=2)
EVERY_DAY = 30
SECOND_VERSION_DAY = 14


@dataclass(frozen=True, slots=True)
class TenantHistory:
    tenant_id: TenantId
    account_id: UUID
    flow_id: UUID

    def adapter(self, database: Engine) -> SqlAlchemyFlowHistoryAdapter:
        return SqlAlchemyFlowHistoryAdapter(database, self.tenant_id)


def day(number: int, hour: int = 12) -> datetime:
    return START + timedelta(days=number, hours=hour)


def query_of(criteria: HistoryFilter, after: HistoryCursor | None = None, limit: int = 50) -> HistoryQuery:
    return HistoryQuery(criteria, criteria.period.window(START), after, limit)


@contextmanager
def transaction_of(database: Engine, tenant_id: TenantId) -> Iterator[Connection]:
    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        yield connection


def save_second_version(database: Engine, tenant_id: TenantId, flow_id: UUID, assets: list[str]) -> None:
    """Version 2 of the flow, on other assets, saved on the day of the scenario: version 1 stays in force before."""
    with transaction_of(database, tenant_id) as connection:
        first = connection.execute(select(flow_versions.c.configuration).where(flow_versions.c.flow_id == flow_id))
        configuration = dict(first.scalar_one()) | {"assets": assets}
        connection.execute(
            insert(flow_versions).values(
                flow_id=flow_id,
                version=2,
                tenant_id=tenant_id.value,
                configuration=configuration,
                created_at=day(SECOND_VERSION_DAY, hour=0),
            )
        )


def new_tenant_history(database: Engine, flow_name: str = "alfa") -> TenantHistory:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, "principale", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    flow = a_flow(tenant.id, name=flow_name, account_id=account.id.value)
    SqlAlchemyFlowRepositoryAdapter(database, tenant.id).add(flow)
    return TenantHistory(tenant.id, account.id.value, flow.id.value)


def a_closed_position(history: TenantHistory, asset: str, closed_at: datetime) -> ClosedPosition:
    return ClosedPosition(
        tenant_id=history.tenant_id,
        flow_id=FlowId(history.flow_id),
        asset=asset,
        side=TradeSide.SHORT,
        leverage=3,
        margin=Decimal(40),
        opening=PositionEnd(Decimal(3000), closed_at - timedelta(hours=1)),
        closing=PositionEnd(Decimal(2900), closed_at),
        fees=Decimal("0.3"),
        reason=CloseReason.AGENT,
    )


def add_order(database: Engine, history: TenantHistory, asset: str, created_at: datetime, *, flow: bool = True) -> UUID:
    order_id = uuid4()
    with transaction_of(database, history.tenant_id) as connection:
        connection.execute(
            insert(orders).values(
                id=order_id,
                tenant_id=history.tenant_id.value,
                account_id=history.account_id,
                origin="FLOW" if flow else "MANUAL",
                coin=asset,
                direction="long",
                reduce_only=False,
                leverage=3,
                requested_size=Decimal("0.02"),
                slippage=Decimal("0.01"),
                status="FILLED",
                created_at=created_at,
                flow_id=history.flow_id if flow else None,
            )
        )
        for number, (price, size, fee) in enumerate(
            (
                (Decimal("91000.5"), Decimal("0.015"), Decimal("0.41")),
                (Decimal(91001), Decimal("0.005"), Decimal("0.14")),
            )
        ):
            connection.execute(
                insert(account_fills).values(
                    tenant_id=history.tenant_id.value,
                    account_id=history.account_id,
                    fill_id=f"fill-{order_id}-{number}",
                    exchange_order_id=f"exchange-{order_id}",
                    flow_id=history.flow_id if flow else None,
                    order_id=order_id,
                    kind="apertura",
                    platform_order=True,
                    asset=asset,
                    size=size,
                    price=price,
                    fee=fee,
                    realized_pnl=Decimal(0),
                    start_position=Decimal(0),
                    liquidation=False,
                    executed_at=created_at + timedelta(seconds=number + 1),
                )
            )
    return order_id


@pytest.fixture(scope="module")
def anna(database: Engine) -> TenantHistory:
    """The scenario of R2.5.1: cycles every day of the month, version 2 on ETH from day 14, positions and orders."""
    history = new_tenant_history(database)
    save_second_version(database, history.tenant_id, history.flow_id, ["ETH"])
    cycles = SqlAlchemyCycleRepositoryAdapter(database, history.tenant_id)
    for number in range(EVERY_DAY):
        cycles.record(CycleRecord(history.flow_id, day(number), CycleOutcome.COMPLETED, day(number)))
    positions = SqlAlchemyClosedPositionRepositoryAdapter(database, history.tenant_id)
    for number in range(EVERY_DAY):
        for asset in ("BTC", "ETH"):
            positions.add(a_closed_position(history, asset, day(number)))
    for number in range(3):
        add_order(database, history, "BTC", day(number))
    add_order(database, history, "ETH", day(5), flow=False)
    return history


def test_the_cycles_of_a_version_are_those_from_the_day_it_was_saved(database: Engine, anna: TenantHistory) -> None:
    found = anna.adapter(database).cycles(query_of(HistoryFilter(flow_id=anna.flow_id, version=2)))

    assert [entry.record.planned_at for entry in found] == [day(number) for number in range(29, 13, -1)]
    assert {(entry.flow_name, entry.version) for entry in found} == {("alfa", 2)}


def test_the_cycles_of_an_asset_follow_the_version_in_force(database: Engine, anna: TenantHistory) -> None:
    on_btc = anna.adapter(database).cycles(query_of(HistoryFilter(asset="BTC")))
    on_eth = anna.adapter(database).cycles(query_of(HistoryFilter(asset="ETH")))

    assert [entry.record.planned_at for entry in on_btc] == [day(number) for number in range(13, -1, -1)]
    assert len(on_eth) == 16


def test_the_cycles_go_in_pages_after_the_cursor(database: Engine, anna: TenantHistory) -> None:
    adapter = anna.adapter(database)

    first = adapter.cycles(query_of(HistoryFilter(account_id=anna.account_id), limit=2))
    after = adapter.cycles(query_of(HistoryFilter(account_id=anna.account_id), first[1].cursor, limit=2))

    assert [entry.record.planned_at for entry in first] == [day(29), day(28), day(27)]
    assert [entry.record.planned_at for entry in after] == [day(27), day(26), day(25)]


def test_the_closed_positions_of_an_asset_closed_in_a_period(database: Engine, anna: TenantHistory) -> None:
    period = StatisticsPeriod.named("range", day(10).date(), day(20).date())

    found = anna.adapter(database).closed_positions(query_of(HistoryFilter(period=period, asset="ETH")))

    assert [entry.position.closing.at for entry in found] == [day(number) for number in range(20, 9, -1)]
    assert {(entry.position.asset, entry.flow_name) for entry in found} == {("ETH", "alfa")}


def test_the_closed_positions_of_a_version_go_by_their_closing(database: Engine, anna: TenantHistory) -> None:
    found = anna.adapter(database).closed_positions(query_of(HistoryFilter(flow_id=anna.flow_id, version=1)))

    assert min(entry.position.closing.at for entry in found) == day(0)
    assert max(entry.position.closing.at for entry in found) == day(13)
    assert len(found) == 28


def test_the_orders_of_an_account_come_with_their_executions(database: Engine, anna: TenantHistory) -> None:
    found = anna.adapter(database).orders(query_of(HistoryFilter(account_id=anna.account_id)))

    assert [(entry.created_at, entry.asset, entry.flow_name) for entry in found] == [
        (day(5), "ETH", None),
        (day(2), "BTC", "alfa"),
        (day(1), "BTC", "alfa"),
        (day(0), "BTC", "alfa"),
    ]
    assert [(execution.price, execution.size, execution.fee) for execution in found[1].executions] == [
        (Decimal("91000.5"), Decimal("0.015"), Decimal("0.41")),
        (Decimal(91001), Decimal("0.005"), Decimal("0.14")),
    ]
    assert (found[0].status, found[0].origin, found[0].account_name) == ("eseguito", "comando manuale", "principale")


def test_the_orders_of_a_flow_leave_out_those_of_no_flow(database: Engine, anna: TenantHistory) -> None:
    found = anna.adapter(database).orders(query_of(HistoryFilter(flow_id=anna.flow_id, version=1)))

    assert [entry.created_at for entry in found] == [day(2), day(1), day(0)]


def test_a_tenant_reads_nothing_of_the_history_of_another(database: Engine, anna: TenantHistory) -> None:
    bruno = new_tenant_history(database, "omega")
    adapter = bruno.adapter(database)

    assert adapter.closed_positions(query_of(HistoryFilter(asset="BTC"))) == []
    assert adapter.cycles(query_of(HistoryFilter(flow_id=anna.flow_id))) == []
    assert adapter.orders(query_of(HistoryFilter(account_id=anna.account_id))) == []


def test_the_window_of_the_last_days_reads_from_its_start(database: Engine, anna: TenantHistory) -> None:
    window = TimeWindow(since=day(27, hour=0))

    found = anna.adapter(database).cycles(HistoryQuery(HistoryFilter(), window))

    assert [entry.record.planned_at for entry in found] == [day(29), day(28), day(27)]
