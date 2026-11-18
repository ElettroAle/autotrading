from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, RowMapping, func, select
from sqlalchemy.exc import IntegrityError

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.order_repository import SqlAlchemyOrderRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.platform_orders import SqlAlchemyPlatformOrdersAdapter
from autotrading.adapters.outbound.sqlalchemy.reconciliation_repository import (
    SqlAlchemyReconciliationRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.tables import reconciliation_alarms, unattributable_items
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.account_reconciliation import AccountReading
from autotrading.domain.flows.balance_comparison import BalanceComparison
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import PlatformOrder
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind
from autotrading.domain.flows.unattributable_page import UnattributableFilter
from autotrading.domain.orders.order import Order
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow
from tests.support.orders import EXECUTION, a_flow_order, a_request, an_executed_order

pytestmark = pytest.mark.integration

READ_AT = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)


def new_account(database: Engine) -> tuple[TenantId, UUID]:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    return tenant.id, account.id.value


def a_position(account_id: UUID, asset: str = "SOL") -> UnattributableItem:
    return UnattributableItem(account_id, UnattributableKind.POSITION, asset, asset, Decimal("1.5"), READ_AT)


def rows_of(database: Engine, tenant_id: TenantId | None) -> list[RowMapping]:
    # A query written without any tenant filter: only row level security stands between tenants.
    with database.begin() as connection:
        if tenant_id is not None:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        return list(connection.execute(select(unattributable_items)).mappings())


def test_without_a_reading_the_account_has_none(database: Engine) -> None:
    tenant_id, account_id = new_account(database)

    assert SqlAlchemyReconciliationRepositoryAdapter(database, tenant_id).last_reading(account_id) is None


def test_the_last_reading_replaces_the_previous_one(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyReconciliationRepositoryAdapter(database, tenant_id)
    flow_id = FlowId.new()
    repository.save_reading(AccountReading(account_id, READ_AT.replace(hour=9), {flow_id: frozenset({"ETH"})}))

    repository.save_reading(AccountReading(account_id, READ_AT, {flow_id: frozenset({"BTC", "SOL"})}))

    assert repository.last_reading(account_id) == AccountReading(
        account_id, READ_AT, {flow_id: frozenset({"BTC", "SOL"})}
    )


def test_a_case_is_recorded_once_with_the_values_read(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyReconciliationRepositoryAdapter(database, tenant_id)

    assert repository.record(a_position(account_id)) is True
    assert repository.record(a_position(account_id)) is False

    (row,) = rows_of(database, tenant_id)
    assert (row["kind"], row["reference"], row["asset"], row["amount"]) == ("position", "SOL", "SOL", Decimal("1.5"))
    assert (row["detected_at"], row["resolved_at"]) == (READ_AT, None)


def test_a_movement_without_an_asset_is_recorded(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    movement = UnattributableItem(account_id, UnattributableKind.BALANCE_CHANGE, "0xfeed", None, Decimal(200), READ_AT)

    assert SqlAlchemyReconciliationRepositoryAdapter(database, tenant_id).record(movement) is True

    (row,) = rows_of(database, tenant_id)
    assert (row["kind"], row["asset"], row["amount"]) == ("balance_change", None, Decimal(200))


def test_a_position_no_longer_open_is_resolved_and_can_be_recorded_again(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyReconciliationRepositoryAdapter(database, tenant_id)
    repository.record(a_position(account_id, "SOL"))
    repository.record(a_position(account_id, "DOGE"))

    repository.resolve_positions(account_id, frozenset({"DOGE"}))

    assert repository.record(a_position(account_id, "SOL")) is True
    assert repository.record(a_position(account_id, "DOGE")) is False
    resolved = [row["reference"] for row in rows_of(database, tenant_id) if row["resolved_at"] is not None]
    assert resolved == ["SOL"]


def test_the_cases_of_a_tenant_are_invisible_to_another_and_without_a_tenant(database: Engine) -> None:
    anna, account_id = new_account(database)
    bruno, _ = new_account(database)
    SqlAlchemyReconciliationRepositoryAdapter(database, anna).record(a_position(account_id))

    assert (len(rows_of(database, bruno)), len(rows_of(database, None))) == (0, 0)
    assert SqlAlchemyReconciliationRepositoryAdapter(database, bruno).last_reading(account_id) is None


def test_a_case_on_an_account_of_another_tenant_cannot_be_written(database: Engine) -> None:
    _, account_id = new_account(database)
    bruno, _ = new_account(database)

    with pytest.raises(IntegrityError, match="unattributable_items_account_of_tenant"):
        SqlAlchemyReconciliationRepositoryAdapter(database, bruno).record(a_position(account_id))


def test_the_orders_of_the_platform_are_those_of_the_account_with_their_flow_and_origin(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    _, other_account = new_account(database)
    flow = a_flow(tenant_id, name=f"alfa-{uuid4()}", account_id=account_id)
    SqlAlchemyFlowRepositoryAdapter(database, tenant_id).add(flow)
    manual, of_flow = an_executed_order(account_id), a_flow_order(account_id, flow.id.value)
    SqlAlchemyOrderRepositoryAdapter(database, tenant_id).add(manual)
    SqlAlchemyOrderRepositoryAdapter(database, tenant_id).add(of_flow)
    verification = Order.executed(a_request(account_id), EXECUTION)
    SqlAlchemyOrderRepositoryAdapter(database, tenant_id).add(verification)

    orders = SqlAlchemyPlatformOrdersAdapter(database, tenant_id)

    asked = (manual.id.value, of_flow.id.value, verification.id.value, uuid4())
    assert orders.orders_among(account_id, asked) == {
        manual.id.value: PlatformOrder(None),
        of_flow.id.value: PlatformOrder(flow.id),
        verification.id.value: PlatformOrder(None, verification=True),
    }
    assert orders.orders_among(other_account, asked) == {}
    assert orders.orders_among(account_id, ()) == {}


# The balance of the account (R3.3.1)


def an_alarm(account_id: UUID, opened_at: datetime = READ_AT) -> ReconciliationAlarm:
    return ReconciliationAlarm.of(account_id, BalanceComparison(Decimal(1000), Decimal(980), opened_at))


def alarm_rows_of(database: Engine, tenant_id: TenantId | None) -> list[RowMapping]:
    # A query written without any tenant filter: only row level security stands between tenants.
    with database.begin() as connection:
        if tenant_id is not None:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        return list(connection.execute(select(reconciliation_alarms)).mappings())


def test_a_reading_keeps_its_reference_and_its_comparison(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyReconciliationRepositoryAdapter(database, tenant_id)
    comparison = BalanceComparison(Decimal("1000.5"), Decimal("980.25"), READ_AT)
    repository.save_reading(AccountReading(account_id, READ_AT.replace(hour=9), {}, Decimal(1)))

    repository.save_reading(AccountReading(account_id, READ_AT, {}, Decimal("1000.5"), comparison))

    assert repository.last_reading(account_id) == AccountReading(account_id, READ_AT, {}, Decimal("1000.5"), comparison)


def test_an_alarm_opens_once_while_it_stays_open(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyReconciliationRepositoryAdapter(database, tenant_id)

    assert repository.open(an_alarm(account_id)) is True
    assert repository.open(an_alarm(account_id, READ_AT + timedelta(minutes=15))) is False

    assert repository.open_alarm(account_id) == an_alarm(account_id)
    assert len(alarm_rows_of(database, tenant_id)) == 1


def test_two_cycles_of_the_account_together_open_one_alarm(database: Engine) -> None:
    tenant_id, account_id = new_account(database)

    def open_alarm(_: int) -> bool:
        return SqlAlchemyReconciliationRepositoryAdapter(database, tenant_id).open(an_alarm(account_id))

    with ThreadPoolExecutor(max_workers=4) as pool:
        opened = list(pool.map(open_alarm, range(4)))

    assert opened.count(True) == 1
    assert len(alarm_rows_of(database, tenant_id)) == 1


def test_a_confirmed_alarm_closes_and_a_new_one_can_open(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyReconciliationRepositoryAdapter(database, tenant_id)
    repository.open(an_alarm(account_id))
    confirmed_at = READ_AT + timedelta(hours=1)

    assert repository.confirm(account_id, confirmed_at) is True
    assert repository.confirm(account_id, confirmed_at) is False
    assert repository.open_alarm(account_id) is None
    assert repository.open(an_alarm(account_id, READ_AT + timedelta(hours=2))) is True


def test_the_alarms_of_the_account_come_from_the_most_recent(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    _, other_account = new_account(database)
    repository = SqlAlchemyReconciliationRepositoryAdapter(database, tenant_id)
    repository.open(an_alarm(account_id))
    repository.confirm(account_id, READ_AT + timedelta(hours=1))
    repository.open(an_alarm(account_id, READ_AT + timedelta(hours=2)))

    alarms = repository.alarms_of(account_id)

    assert [(alarm.opened_at, alarm.confirmed_at) for alarm in alarms] == [
        (READ_AT + timedelta(hours=2), None),
        (READ_AT, READ_AT + timedelta(hours=1)),
    ]
    assert repository.alarms_of(other_account) == []


def test_the_alarms_of_a_tenant_are_invisible_to_another_and_without_a_tenant(database: Engine) -> None:
    anna, account_id = new_account(database)
    bruno, _ = new_account(database)
    SqlAlchemyReconciliationRepositoryAdapter(database, anna).open(an_alarm(account_id))

    assert (len(alarm_rows_of(database, bruno)), len(alarm_rows_of(database, None))) == (0, 0)
    assert SqlAlchemyReconciliationRepositoryAdapter(database, bruno).open_alarm(account_id) is None
    assert SqlAlchemyReconciliationRepositoryAdapter(database, bruno).confirm(account_id, READ_AT) is False


def test_an_alarm_on_an_account_of_another_tenant_cannot_be_written(database: Engine) -> None:
    _, account_id = new_account(database)
    bruno, _ = new_account(database)

    with pytest.raises(IntegrityError, match="reconciliation_alarms_account_of_tenant"):
        SqlAlchemyReconciliationRepositoryAdapter(database, bruno).open(an_alarm(account_id))


# The record of the account (ADR movimenti-non-spiegati-nel-riquadro-del-conto)


def a_change(account_id: UUID, minutes: int, amount: str) -> UnattributableItem:
    return UnattributableItem(
        account_id,
        UnattributableKind.BALANCE_CHANGE,
        f"change-{minutes}",
        None,
        Decimal(amount),
        READ_AT + timedelta(minutes=minutes),
    )


def references(cases: object) -> list[str]:
    assert isinstance(cases, tuple)
    return [case.item.reference for case in cases]


def test_the_record_of_the_account_comes_from_the_most_recent_with_the_net_of_its_changes(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    _, other_account = new_account(database)
    repository = SqlAlchemyReconciliationRepositoryAdapter(database, tenant_id)
    for item in (a_change(account_id, -1, "-0.03"), a_position(account_id), a_change(account_id, 5, "0.05")):
        repository.record(item)

    page = repository.unattributable_of(account_id, UnattributableFilter(), None)

    assert references(page.cases) == ["change-5", "SOL", "change--1"]
    assert page.cases[0].item == a_change(account_id, 5, "0.05")
    assert (page.count, page.net_change, page.next) == (3, Decimal("0.02"), None)
    assert repository.unattributable_of(other_account, UnattributableFilter(), None).count == 0


def test_a_resolved_position_stays_in_the_record(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyReconciliationRepositoryAdapter(database, tenant_id)
    repository.record(a_position(account_id))
    repository.resolve_positions(account_id, frozenset())

    page = repository.unattributable_of(account_id, UnattributableFilter(), None)

    assert references(page.cases) == ["SOL"]


def test_the_record_is_read_by_pages_of_keyset_with_the_totals_of_the_whole_filter(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyReconciliationRepositoryAdapter(database, tenant_id)
    for minutes in range(3):
        repository.record(a_change(account_id, minutes, "1"))
    criteria = UnattributableFilter(limit=2)

    first = repository.unattributable_of(account_id, criteria, None)
    second = repository.unattributable_of(account_id, criteria, first.next)

    assert references(first.cases) == ["change-2", "change-1"]
    assert first.next == first.cases[-1].cursor
    assert references(second.cases) == ["change-0"]
    assert (second.count, second.net_change, second.next) == (3, Decimal(3), None)


def test_the_record_is_narrowed_by_kind_and_by_period(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyReconciliationRepositoryAdapter(database, tenant_id)
    for item in (a_change(account_id, -10, "4"), a_position(account_id), a_change(account_id, 10, "-1")):
        repository.record(item)

    positions = repository.unattributable_of(account_id, UnattributableFilter(kind=UnattributableKind.POSITION), None)
    in_period = repository.unattributable_of(
        account_id, UnattributableFilter(since=READ_AT, until=READ_AT + timedelta(minutes=10)), None
    )

    assert (references(positions.cases), positions.net_change) == (["SOL"], Decimal(0))
    assert (references(in_period.cases), in_period.count) == (["SOL"], 1)


def test_the_record_of_a_tenant_is_invisible_to_another(database: Engine) -> None:
    anna, account_id = new_account(database)
    bruno, _ = new_account(database)
    SqlAlchemyReconciliationRepositoryAdapter(database, anna).record(a_change(account_id, 0, "1"))

    page = SqlAlchemyReconciliationRepositoryAdapter(database, bruno).unattributable_of(
        account_id, UnattributableFilter(), None
    )

    assert (page.cases, page.count, page.net_change) == ((), 0, Decimal(0))
