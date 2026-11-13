"""The removal of an account with its flows: stop them, remove the account, archive them (R0.2.5, R1.1.8)."""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.archive_flow import ArchiveFlowUseCase
from autotrading.application.flows.errors import AccountToRemoveNotFoundError, FlowExchangeUnavailableError
from autotrading.application.flows.ports import AccountRemovalPorts
from autotrading.application.flows.remove_account_with_flows import (
    RemoveAccountWithFlowsCommand,
    RemoveAccountWithFlowsUseCase,
)
from autotrading.application.flows.stop_flow import StopFlowUseCase, StopPorts
from autotrading.domain.accounts.account import Account
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.closed_position import CloseReason, PositionEnd
from autotrading.domain.flows.errors import (
    FlowPositionsLeftOpenError,
    OpenPositionsNeedConfirmationError,
    OperatingFlowsNeedConfirmationError,
)
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.stop_outcome import ClosingFill, PositionClosing, PositionOpening
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter, RemovedAccount
from tests.fakes.closed_position_repository import ClosedPositionStore, InMemoryClosedPositionRepositoryAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.accounts import an_account
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId.new()
USER = UserId("oid-anna")
EXECUTED = datetime(2026, 11, 12, 9, 45, tzinfo=UTC)


class ScriptedAccountPositions:
    """The assets open on the account as the test decides them, or a failure, and which accounts were read."""

    def __init__(self) -> None:
        self.assets: tuple[str, ...] = ()
        self.failure: AutotradingError | None = None
        self.asked: list[UUID] = []

    def open_positions_of(self, account_id: UUID) -> tuple[str, ...]:
        self.asked.append(account_id)
        if self.failure is not None:
            raise self.failure
        return self.assets


class ScriptedClosings:
    def __init__(self) -> None:
        self.refusals: dict[str, str] = {}
        self.closed: list[tuple[UUID, str, UserId]] = []

    def close(self, account_id: UUID, asset: str, user_id: UserId) -> PositionClosing | None:
        self.closed.append((account_id, asset, user_id))
        if asset in self.refusals:
            return PositionClosing(asset, refusal=self.refusals[asset])
        return PositionClosing(asset, ClosingFill(Decimal(102000), EXECUTED, Decimal("0.05")))


class RecordingCycles:
    def __init__(self) -> None:
        self.waited: list[FlowId] = []

    def wait_until_finished(self, flow_id: FlowId) -> None:
        self.waited.append(flow_id)


class OpeningOfEveryAsset:
    def __init__(self) -> None:
        self.asked: list[tuple[FlowId, str]] = []

    def last_opening(self, flow_id: FlowId, asset: str) -> PositionOpening | None:
        self.asked.append((flow_id, asset))
        end = PositionEnd(Decimal(100000), EXECUTED, EXECUTED)
        return PositionOpening(TradeSide.LONG, 2, Decimal(50), end, Decimal("0.03"))


class Removal:
    def __init__(self) -> None:
        self.accounts = AccountStore()
        self.flows = FlowStore()
        self.positions = ScriptedAccountPositions()
        self.closings = ScriptedClosings()
        self.closed = ClosedPositionStore()
        self.cycles = RecordingCycles()
        repository = InMemoryFlowRepositoryAdapter(self.flows, TENANT)
        account_repository = InMemoryAccountRepositoryAdapter(self.accounts, TENANT)
        closed_positions = InMemoryClosedPositionRepositoryAdapter(self.closed, TENANT)
        stop_ports = StopPorts(self.cycles, self.closings, OpeningOfEveryAsset(), closed_positions)
        self.use_case = RemoveAccountWithFlowsUseCase(
            repository,
            AccountRemovalPorts(self.positions, account_repository),
            StopFlowUseCase(repository, stop_ports),
            ArchiveFlowUseCase(repository),
        )

    def an_account(self, tenant_id: TenantId = TENANT) -> Account:
        account = an_account(tenant_id)
        self.accounts.accounts.append(account)
        return account

    def a_flow(self, name: str, status: FlowStatus, asset: str, account_id: UUID) -> None:
        configuration = a_configuration(assets=(asset,))
        flow = a_flow(TENANT, name=name, status=status, account_id=account_id, configuration=configuration)
        self.flows.flows.append(flow)

    def remove(self, account: Account, *, confirmed: bool = False) -> None:
        self.use_case.execute(RemoveAccountWithFlowsCommand(account.id.value, USER, confirmed=confirmed))

    def statuses(self) -> dict[str, FlowStatus]:
        return {flow.name.value: flow.status for flow in self.flows.flows}


@pytest.fixture
def removal() -> Removal:
    return Removal()


def test_an_account_without_flows_nor_positions_is_removed_after_reading_them(removal: Removal) -> None:
    account = removal.an_account()

    removal.remove(account)

    assert removal.positions.asked == [account.id.value]
    assert removal.accounts.accounts == []
    assert removal.accounts.removed == [RemovedAccount(account.id, TENANT, account.name.value)]


def test_an_account_with_open_positions_is_kept_without_confirmation(removal: Removal) -> None:
    account = removal.an_account()
    removal.positions.assets = ("BTC",)

    with pytest.raises(OpenPositionsNeedConfirmationError) as raised:
        removal.remove(account)

    assert str(raised.value) == "il conto ha posizioni aperte che resteranno sull'exchange senza gestione"
    assert (removal.accounts.accounts, removal.accounts.removed) == ([account], [])


def test_a_confirmed_removal_reads_no_position_and_removes_the_account(removal: Removal) -> None:
    account = removal.an_account()
    removal.positions.assets = ("BTC",)

    removal.remove(account, confirmed=True)

    assert removal.positions.asked == []
    assert [removed.id for removed in removal.accounts.removed] == [account.id]


def test_a_confirmed_removal_works_when_the_exchange_cannot_be_read(removal: Removal) -> None:
    account = removal.an_account()
    removal.positions.failure = FlowExchangeUnavailableError()

    removal.remove(account, confirmed=True)

    assert removal.accounts.accounts == []


def test_without_confirmation_an_exchange_that_cannot_be_read_keeps_the_account(removal: Removal) -> None:
    account = removal.an_account()
    removal.positions.failure = FlowExchangeUnavailableError()

    with pytest.raises(FlowExchangeUnavailableError):
        removal.remove(account)

    assert removal.accounts.accounts == [account]


@pytest.mark.parametrize("confirmed", [False, True])
def test_an_account_of_another_tenant_is_not_found_and_never_read(removal: Removal, confirmed: bool) -> None:
    theirs = removal.an_account(TenantId.new())

    with pytest.raises(AccountToRemoveNotFoundError) as raised:
        removal.remove(theirs, confirmed=confirmed)

    assert (str(raised.value), raised.value.status_code) == ("non trovato", 404)

    assert (removal.accounts.accounts, removal.positions.asked) == ([theirs], [])


def test_an_account_already_removed_is_not_found(removal: Removal) -> None:
    account = removal.an_account()
    removal.remove(account)

    with pytest.raises(AccountToRemoveNotFoundError):
        removal.remove(account)


def test_the_removal_is_recorded_by_account_id_only(removal: Removal, caplog: pytest.LogCaptureFixture) -> None:
    account = removal.an_account()

    with caplog.at_level("INFO", logger="autotrading.flows"):
        removal.remove(account)

    (record,) = caplog.records
    assert (record.getMessage(), record.__dict__["account_id"]) == ("conto rimosso", str(account.id.value))


def test_an_account_with_operating_flows_is_kept_without_confirmation_before_reading_positions(
    removal: Removal,
) -> None:
    account = removal.an_account()
    removal.a_flow("alfa", FlowStatus.ACTIVE, "BTC", account.id.value)
    removal.a_flow("beta", FlowStatus.PAUSED, "ETH", account.id.value)
    removal.a_flow("fermo", FlowStatus.STOPPED, "SOL", account.id.value)
    removal.a_flow("altro conto", FlowStatus.ACTIVE, "XRP", uuid4())

    with pytest.raises(OperatingFlowsNeedConfirmationError) as raised:
        removal.remove(account)

    assert str(raised.value) == "il conto ha flussi attivi o in pausa che verranno fermati: alfa, beta"
    assert raised.value.flows == ("alfa", "beta")
    assert raised.value.status_code == 409
    assert (removal.accounts.accounts, removal.positions.asked, removal.closings.closed) == ([account], [], [])


def test_a_confirmed_removal_stops_the_flows_then_removes_the_account_then_archives_them(removal: Removal) -> None:
    account = removal.an_account()
    removal.a_flow("attivo", FlowStatus.ACTIVE, "BTC", account.id.value)
    removal.a_flow("pausa", FlowStatus.PAUSED, "ETH", account.id.value)
    removal.a_flow("fermo", FlowStatus.STOPPED, "SOL", account.id.value)
    removal.a_flow("altro conto", FlowStatus.ACTIVE, "BTC", uuid4())
    removal.flows.flows.append(replace(a_flow(TenantId.new(), status=FlowStatus.ACTIVE), account_id=account.id.value))

    removal.remove(account, confirmed=True)

    assert removal.closings.closed == [(account.id.value, "BTC", USER), (account.id.value, "ETH", USER)]
    assert len(removal.cycles.waited) == 2
    assert [position.reason for position in removal.closed.positions] == [CloseReason.ACCOUNT_REMOVAL] * 2
    assert removal.accounts.accounts == []
    statuses = removal.statuses()
    assert [statuses[name] for name in ("attivo", "pausa", "fermo", "altro conto")] == [
        FlowStatus.ARCHIVED,
        FlowStatus.ARCHIVED,
        FlowStatus.ARCHIVED,
        FlowStatus.ACTIVE,
    ]


def test_a_position_left_open_keeps_the_account_and_its_flows_stopped_but_not_archived(removal: Removal) -> None:
    account = removal.an_account()
    removal.a_flow("alfa", FlowStatus.ACTIVE, "BTC", account.id.value)
    removal.a_flow("beta", FlowStatus.ACTIVE, "ETH", account.id.value)
    removal.closings.refusals = {"BTC": "Order rejected", "ETH": "margine"}

    with pytest.raises(FlowPositionsLeftOpenError) as raised:
        removal.remove(account, confirmed=True)

    assert str(raised.value) == (
        "posizioni dei flussi rimaste aperte, conto non rimosso: BTC (Order rejected), ETH (margine)"
    )
    assert raised.value.positions == (("BTC", "Order rejected"), ("ETH", "margine"))
    assert raised.value.status_code == 409
    assert removal.accounts.accounts == [account]
    assert set(removal.statuses().values()) == {FlowStatus.STOPPED}
