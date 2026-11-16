from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import Engine, text

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.closed_position_repository import (
    SqlAlchemyClosedPositionRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.closed_position_filter import ClosedPositionFilter
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow

pytestmark = pytest.mark.integration

OPENED = datetime(2026, 11, 12, 10, tzinfo=UTC)
EVERY = ClosedPositionFilter()


def new_flow(database: Engine) -> Flow:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    flow = a_flow(tenant.id, account_id=account.id.value)
    SqlAlchemyFlowRepositoryAdapter(database, tenant.id).add(flow)
    return flow


def a_position(flow: Flow, closed_after: timedelta) -> ClosedPosition:
    return ClosedPosition(
        tenant_id=flow.tenant_id,
        flow_id=flow.id,
        asset="BTC",
        side=TradeSide.LONG,
        leverage=2,
        margin=Decimal("50.5"),
        opening=PositionEnd(Decimal(100000), OPENED, OPENED),
        closing=PositionEnd(Decimal(102000), OPENED + closed_after),
        fees=Decimal("0.08"),
        reason=CloseReason.AGENT,
    )


def test_the_closed_positions_read_back_from_the_most_recent_close(database: Engine) -> None:
    flow = new_flow(database)
    repository = SqlAlchemyClosedPositionRepositoryAdapter(database, flow.tenant_id)
    earlier, later = a_position(flow, timedelta(hours=1)), a_position(flow, timedelta(hours=3))
    later = replace(later, reason=CloseReason.OUTSIDE_PLATFORM)

    repository.add(earlier)
    repository.add(later)

    assert repository.matching(flow.id, EVERY, 0, 10) == [later, earlier]


def test_the_closed_positions_read_back_one_page_at_a_time(database: Engine) -> None:
    flow = new_flow(database)
    repository = SqlAlchemyClosedPositionRepositoryAdapter(database, flow.tenant_id)
    positions = [a_position(flow, timedelta(hours=hours)) for hours in (1, 2, 3, 4)]
    for position in positions:
        repository.add(position)

    assert repository.matching(flow.id, EVERY, 1, 2) == [positions[2], positions[1]]


def test_a_closed_position_keeps_the_pnl_the_exchange_reported(database: Engine) -> None:
    flow = new_flow(database)
    repository = SqlAlchemyClosedPositionRepositoryAdapter(database, flow.tenant_id)
    reported = replace(a_position(flow, timedelta(hours=1)), realized_pnl=Decimal("-4.2"))

    repository.add(reported)

    [read] = repository.matching(flow.id, EVERY, 0, 10)
    assert (read, read.pnl) == (reported, Decimal("-4.2"))


def test_the_closed_positions_of_another_tenant_stay_invisible(database: Engine) -> None:
    flow, other = new_flow(database), new_flow(database)
    SqlAlchemyClosedPositionRepositoryAdapter(database, flow.tenant_id).add(a_position(flow, timedelta(hours=1)))

    assert SqlAlchemyClosedPositionRepositoryAdapter(database, other.tenant_id).matching(flow.id, EVERY, 0, 10) == []


def test_a_session_without_tenant_sees_no_closed_position(database: Engine) -> None:
    flow = new_flow(database)
    SqlAlchemyClosedPositionRepositoryAdapter(database, flow.tenant_id).add(a_position(flow, timedelta(hours=1)))

    with database.begin() as connection:
        assert connection.execute(text("SELECT count(*) FROM closed_positions")).scalar_one() == 0


def test_the_closed_positions_within_a_window_are_those_closed_from_its_start_to_its_end(database: Engine) -> None:
    flow = new_flow(database)
    repository = SqlAlchemyClosedPositionRepositoryAdapter(database, flow.tenant_id)
    before, first, last, after = (a_position(flow, timedelta(hours=hours)) for hours in (1, 2, 3, 4))
    for position in (before, first, last, after):
        repository.add(position)

    window = TimeWindow(since=first.closing.at, until=after.closing.at)

    assert repository.closed_within(flow.id, window) == [last, first]
    assert repository.closed_within(flow.id, TimeWindow()) == [after, last, first, before]


def test_the_closed_positions_within_a_window_of_another_tenant_stay_invisible(database: Engine) -> None:
    flow, other = new_flow(database), new_flow(database)
    SqlAlchemyClosedPositionRepositoryAdapter(database, flow.tenant_id).add(a_position(flow, timedelta(hours=1)))

    repository = SqlAlchemyClosedPositionRepositoryAdapter(database, other.tenant_id)

    assert repository.closed_within(flow.id, TimeWindow()) == []


# ADR filtri-dei-cicli-e-delle-posizioni-chiuse-nell-api: PostgreSQL filters and counts, so the pages stay right.
def test_the_closed_positions_are_filtered_by_asset_side_result_after_the_fees_and_days(database: Engine) -> None:
    flow = new_flow(database)
    repository = SqlAlchemyClosedPositionRepositoryAdapter(database, flow.tenant_id)
    # Long from 100000 to 102000 with 50.5 of margin at 2x: 2.02 before the fees, 1.94 after them.
    won_long = a_position(flow, timedelta(hours=1))
    lost_short = replace(a_position(flow, timedelta(hours=2)), side=TradeSide.SHORT)
    even_after_fees = replace(a_position(flow, timedelta(hours=3)), realized_pnl=Decimal("0.08"))
    won_short_reported = replace(lost_short, closing=PositionEnd(Decimal(102000), OPENED + timedelta(hours=4)))
    won_short_reported = replace(won_short_reported, realized_pnl=Decimal(3))
    won_eth = replace(won_long, asset="ETH")
    won_next_day = replace(won_long, closing=PositionEnd(Decimal(102000), OPENED + timedelta(days=1)))
    for position in (won_long, lost_short, even_after_fees, won_short_reported, won_eth, won_next_day):
        repository.add(position)

    def matched(criteria: ClosedPositionFilter) -> list[ClosedPosition]:
        return repository.matching(flow.id, criteria, 0, 10)

    assert matched(ClosedPositionFilter.named(result="persa")) == [lost_short]
    assert matched(ClosedPositionFilter.named(side="short", result="vinta")) == [won_short_reported]
    assert matched(ClosedPositionFilter.named(asset="ETH")) == [won_eth]
    day = OPENED.date()
    assert matched(ClosedPositionFilter.named(asset="BTC", result="vinta", first_day=day, last_day=day)) == [
        won_short_reported,
        won_long,
    ]
    assert repository.count(flow.id, ClosedPositionFilter.named(result="vinta")) == 4
    assert repository.count(flow.id, EVERY) == 6


def test_the_count_of_the_closed_positions_of_another_tenant_is_zero(database: Engine) -> None:
    flow, other = new_flow(database), new_flow(database)
    SqlAlchemyClosedPositionRepositoryAdapter(database, flow.tenant_id).add(a_position(flow, timedelta(hours=1)))

    assert SqlAlchemyClosedPositionRepositoryAdapter(database, other.tenant_id).count(flow.id, EVERY) == 0
