"""The bridges bootstrap builds to stop flows and change their capital (ADR 0055, ADR 0053, ADR 0054)."""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.archive_flow import ArchiveFlowUseCase
from autotrading.application.flows.stop_flow import StopFlowUseCase, StopPorts
from autotrading.application.orders.close_flow_position import CloseFlowPositionUseCase
from autotrading.application.orders.errors import (
    NoOpenPositionError,
    OrderAccountNotFoundError,
    OrderExchangeUnavailableError,
    OrderWorkerUnavailableError,
)
from autotrading.application.orders.outcome import OrderOutcome
from autotrading.bootstrap import AccountFlowsFromFlows, FlowPositionsFromOrders
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.removal import FlowPositionLeftOpen
from autotrading.domain.flows.closed_position import CloseReason, PositionEnd
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.stop_outcome import ClosingFill, PositionClosing, PositionOpening
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.orders.order import OrderStatus
from autotrading.domain.orders.rejection import RejectionReason
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.closed_position_repository import ClosedPositionStore, InMemoryClosedPositionRepositoryAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.flows import a_configuration, a_flow

USER = UserId("oid-anna")
ACCOUNT = uuid4()


class ScriptedClosing:
    def __init__(self) -> None:
        self.outcome: OrderOutcome | None = None
        self.failure: Exception | None = None
        self.asked: list[tuple[UUID, str, UserId]] = []

    def close(self, account_id: UUID, coin: str, user_id: UserId) -> OrderOutcome:
        self.asked.append((account_id, coin, user_id))
        if self.failure is not None:
            raise self.failure
        assert self.outcome is not None
        return self.outcome


def an_outcome(status: OrderStatus, **values: object) -> OrderOutcome:
    return OrderOutcome(uuid4(), status, "BTC", **values)  # type: ignore[arg-type]  # each test names the values it reads


@pytest.fixture
def closing() -> ScriptedClosing:
    return ScriptedClosing()


@pytest.fixture
def positions(closing: ScriptedClosing) -> FlowPositionsFromOrders:
    return FlowPositionsFromOrders(CloseFlowPositionUseCase(closing))


EXECUTED = datetime(2026, 11, 12, 9, 45, tzinfo=UTC)
FILLED = {"average_price": Decimal(102000), "executed_at": EXECUTED, "fee": Decimal("0.05")}


@pytest.mark.parametrize("status", [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED])
def test_a_closing_executed_gives_its_fill(
    positions: FlowPositionsFromOrders, closing: ScriptedClosing, status: OrderStatus
) -> None:
    closing.outcome = an_outcome(status, **FILLED)

    assert positions.close(ACCOUNT, "BTC", USER) == PositionClosing(
        "BTC", ClosingFill(Decimal(102000), EXECUTED, Decimal("0.05"))
    )
    assert closing.asked == [(ACCOUNT, "BTC", USER)]


@pytest.mark.parametrize("missing", ["average_price", "executed_at", "fee"])
def test_a_closing_not_confirmed_in_time_is_a_position_maybe_still_open(
    positions: FlowPositionsFromOrders, closing: ScriptedClosing, missing: str
) -> None:
    closing.outcome = an_outcome(OrderStatus.UNKNOWN, **{**FILLED, missing: None})

    assert positions.close(ACCOUNT, "BTC", USER) == PositionClosing("BTC", refusal=OrderStatus.UNKNOWN.value)


def test_a_closing_refused_gives_the_message_of_the_exchange(
    positions: FlowPositionsFromOrders, closing: ScriptedClosing
) -> None:
    closing.outcome = an_outcome(OrderStatus.REJECTED, reason=RejectionReason.OTHER, exchange_message="Order rejected")

    assert positions.close(ACCOUNT, "BTC", USER) == PositionClosing("BTC", refusal="Order rejected")


def test_a_closing_refused_without_a_message_gives_its_reason(
    positions: FlowPositionsFromOrders, closing: ScriptedClosing
) -> None:
    closing.outcome = an_outcome(OrderStatus.REJECTED, reason=RejectionReason.INSUFFICIENT_MARGIN)

    assert positions.close(ACCOUNT, "BTC", USER) == PositionClosing("BTC", refusal="margine insufficiente")


def test_no_position_on_the_asset_is_nothing_to_close(
    positions: FlowPositionsFromOrders, closing: ScriptedClosing
) -> None:
    closing.failure = NoOpenPositionError("BTC")

    assert positions.close(ACCOUNT, "BTC", USER) is None


@pytest.mark.parametrize(
    "failure", [OrderAccountNotFoundError(), OrderExchangeUnavailableError(), OrderWorkerUnavailableError()]
)
def test_a_closing_that_cannot_be_done_gives_the_reason(
    positions: FlowPositionsFromOrders, closing: ScriptedClosing, failure: Exception
) -> None:
    closing.failure = failure

    assert positions.close(ACCOUNT, "BTC", USER) == PositionClosing("BTC", refusal=str(failure))


class ScriptedPositions:
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


class AccountFlows:
    def __init__(self) -> None:
        self.tenant_id = TenantId.new()
        self.store = FlowStore()
        repository = InMemoryFlowRepositoryAdapter(self.store, self.tenant_id)
        self.positions = ScriptedPositions()
        self.cycles = RecordingCycles()
        self.closed = ClosedPositionStore()
        closed_positions = InMemoryClosedPositionRepositoryAdapter(self.closed, self.tenant_id)
        stop = StopFlowUseCase(
            repository, StopPorts(self.cycles, self.positions, OpeningOfEveryAsset(), closed_positions)
        )
        self.bridge = AccountFlowsFromFlows(repository, stop, ArchiveFlowUseCase(repository))

    def add(self, name: str, status: FlowStatus, asset: str, account_id: UUID = ACCOUNT) -> FlowId:
        configuration = a_configuration(assets=(asset,))
        flow = a_flow(self.tenant_id, name=name, status=status, account_id=account_id, configuration=configuration)
        self.store.flows.append(flow)
        return flow.id

    def statuses(self) -> dict[str, FlowStatus]:
        return {flow.name.value: flow.status for flow in self.store.flows}


@pytest.fixture
def account_flows() -> AccountFlows:
    flows = AccountFlows()
    flows.add("attivo", FlowStatus.ACTIVE, "BTC")
    flows.add("pausa", FlowStatus.PAUSED, "ETH")
    flows.add("fermo", FlowStatus.STOPPED, "SOL")
    flows.add("archiviato", FlowStatus.ARCHIVED, "XRP")
    flows.add("altro conto", FlowStatus.ACTIVE, "BTC", account_id=uuid4())
    flows.store.flows.append(replace(a_flow(TenantId.new(), status=FlowStatus.ACTIVE), account_id=ACCOUNT))
    return flows


def test_the_flows_operating_on_an_account_are_the_active_and_paused_ones_of_the_tenant(
    account_flows: AccountFlows,
) -> None:
    assert account_flows.bridge.operating(AccountId(ACCOUNT)) == ("attivo", "pausa")


def test_stopping_the_flows_of_an_account_closes_their_positions_and_reports_those_left_open(
    account_flows: AccountFlows,
) -> None:
    account_flows.positions.refusals["ETH"] = "Order rejected"

    left_open = account_flows.bridge.stop(AccountId(ACCOUNT), USER)

    assert left_open == (FlowPositionLeftOpen("ETH", "Order rejected"),)
    assert account_flows.positions.closed == [(ACCOUNT, "BTC", USER), (ACCOUNT, "ETH", USER)]
    assert len(account_flows.cycles.waited) == 2
    assert [(position.asset, position.reason) for position in account_flows.closed.positions] == [
        ("BTC", CloseReason.ACCOUNT_REMOVAL)
    ]
    statuses = account_flows.statuses()
    assert (statuses["attivo"], statuses["pausa"], statuses["altro conto"]) == (
        FlowStatus.STOPPED,
        FlowStatus.STOPPED,
        FlowStatus.ACTIVE,
    )


def test_archiving_the_flows_of_an_account_archives_the_stopped_ones_only(account_flows: AccountFlows) -> None:
    account_flows.bridge.archive(AccountId(ACCOUNT))

    statuses = account_flows.statuses()
    assert [name for name, status in statuses.items() if status == FlowStatus.ARCHIVED] == ["fermo", "archiviato"]
    assert statuses["attivo"] == FlowStatus.ACTIVE
