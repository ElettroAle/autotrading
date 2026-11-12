import logging
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.change_allocated_capital import (
    ChangeAllocatedCapitalCommand,
    ChangeAllocatedCapitalUseCase,
)
from autotrading.application.flows.errors import FlowExchangeUnavailableError, FlowNotFoundError
from autotrading.application.flows.list_capital_changes import ListCapitalChangesCommand, ListCapitalChangesUseCase
from autotrading.application.flows.stop_flow import StopFlowCommand, StopFlowUseCase, StopPorts
from autotrading.domain.flows.capital_change import CapitalChange
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.errors import (
    ArchivedFlowNotModifiableError,
    CapitalAboveAvailableCapitalError,
    CapitalBelowCommittedMarginError,
    FlowCommandNotAllowedError,
)
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.stop_outcome import (
    ClosingFill,
    PositionClosing,
    PositionLeftOpen,
    PositionOpening,
    StopOutcome,
)
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.closed_position_repository import ClosedPositionStore, InMemoryClosedPositionRepositoryAdapter
from tests.fakes.flow_account import FakeFlowAccountAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.flows import a_configuration, a_flow

USER = UserId("oid-anna")
OPENED = datetime(2026, 11, 12, 8, 0, tzinfo=UTC)
FILL = ClosingFill(Decimal(102000), datetime(2026, 11, 12, 9, 45, tzinfo=UTC), Decimal("0.05"))
OPENING = PositionOpening(TradeSide.LONG, 2, Decimal(50), PositionEnd(Decimal(100000), OPENED, OPENED), Decimal("0.03"))
NOW = datetime(2026, 11, 12, 9, 30, tzinfo=UTC)


class ScriptedPositions:
    """Closes or refuses the positions the test decides, records every call in order with the cycles."""

    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.refusals: dict[str, str] = {}
        self.none_open: set[str] = set()
        self.margin = Decimal(0)
        self.margin_failure: Exception | None = None
        self.margins_asked: list[tuple[UUID, tuple[str, ...]]] = []

    def close(self, account_id: UUID, asset: str, user_id: UserId) -> PositionClosing | None:
        self.events.append(f"close {asset} {account_id} {user_id.value}")
        if asset in self.none_open:
            return None
        if asset in self.refusals:
            return PositionClosing(asset, refusal=self.refusals[asset])
        return PositionClosing(asset, FILL)

    def committed_margin(self, account_id: UUID, assets: tuple[str, ...]) -> Decimal:
        self.margins_asked.append((account_id, assets))
        if self.margin_failure is not None:
            raise self.margin_failure
        return self.margin


class RecordingCycles:
    """Records each wait, with the status the flow had saved by then."""

    def __init__(self, events: list[str], repository: InMemoryFlowRepositoryAdapter) -> None:
        self.events = events
        self._repository = repository

    def wait_until_finished(self, flow_id: FlowId) -> None:
        self.events.append(f"wait {flow_id.value} {self._repository.get(flow_id).status.value}")


class ScriptedOpenings:
    def __init__(self) -> None:
        self.openings: dict[tuple[FlowId, str], PositionOpening] = {}

    def last_opening(self, flow_id: FlowId, asset: str) -> PositionOpening | None:
        return self.openings.get((flow_id, asset))


class Flows:
    def __init__(self) -> None:
        self.tenant_id = TenantId.new()
        self.store = FlowStore()
        self.repository = InMemoryFlowRepositoryAdapter(self.store, self.tenant_id)
        self.events: list[str] = []
        self.positions = ScriptedPositions(self.events)
        self.accounts = FakeFlowAccountAdapter()
        self.account_id = uuid4()
        self.accounts.add(self.account_id, Decimal(1000))
        self.openings = ScriptedOpenings()
        self.closed = ClosedPositionStore()
        self.stop = StopFlowUseCase(
            self.repository,
            StopPorts(
                RecordingCycles(self.events, self.repository),
                self.positions,
                self.openings,
                InMemoryClosedPositionRepositoryAdapter(self.closed, self.tenant_id),
            ),
        )
        self.change_capital = ChangeAllocatedCapitalUseCase(self.repository, self.accounts, self.positions, lambda: NOW)
        self.list_changes = ListCapitalChangesUseCase(self.repository)

    def saved(
        self,
        name: str = "alfa",
        status: FlowStatus = FlowStatus.ACTIVE,
        assets: tuple[str, ...] = ("BTC", "ETH"),
        capital: Decimal = Decimal(400),
    ) -> Flow:
        configuration = a_configuration(assets=assets, allocated_capital=capital)
        flow = a_flow(self.tenant_id, name=name, status=status, account_id=self.account_id, configuration=configuration)
        self.repository.add(flow)
        return flow


@pytest.fixture
def flows() -> Flows:
    return Flows()


@pytest.mark.parametrize("status", [FlowStatus.ACTIVE, FlowStatus.PAUSED])
def test_a_stop_saves_the_flow_stopped_waits_for_its_cycle_then_closes_each_asset(
    flows: Flows, status: FlowStatus
) -> None:
    flow = flows.saved(status=status)

    outcome = flows.stop.execute(StopFlowCommand(flow.id, USER))

    assert outcome == StopOutcome(replace(flow, status=FlowStatus.STOPPED), ())
    assert flows.events == [
        f"wait {flow.id.value} fermo",
        f"close BTC {flows.account_id} oid-anna",
        f"close ETH {flows.account_id} oid-anna",
    ]


def test_a_closing_refused_leaves_the_flow_stopped_with_the_position_in_the_outcome(flows: Flows) -> None:
    flow = flows.saved()
    flows.positions.refusals["ETH"] = "Order rejected"

    outcome = flows.stop.execute(StopFlowCommand(flow.id, USER))

    assert outcome.left_open == (PositionLeftOpen("ETH", "Order rejected"),)
    assert flows.repository.get(flow.id).status == FlowStatus.STOPPED
    assert len(flows.events) == 3


@pytest.mark.parametrize("status", [FlowStatus.STOPPED, FlowStatus.ARCHIVED])
def test_a_flow_not_operating_is_not_stopped_and_nothing_is_closed(flows: Flows, status: FlowStatus) -> None:
    flow = flows.saved(status=status)

    with pytest.raises(FlowCommandNotAllowedError):
        flows.stop.execute(StopFlowCommand(flow.id, USER))

    assert flows.events == []
    assert flows.repository.get(flow.id).status == status


def test_a_flow_of_another_tenant_is_not_found_and_not_stopped(flows: Flows) -> None:
    theirs = a_flow(TenantId.new(), status=FlowStatus.ACTIVE)
    flows.store.flows.append(theirs)

    with pytest.raises(FlowNotFoundError):
        flows.stop.execute(StopFlowCommand(theirs.id, USER))

    assert flows.events == []


def test_the_stop_is_recorded_with_the_positions_left_open(flows: Flows, caplog: pytest.LogCaptureFixture) -> None:
    flow = flows.saved()
    flows.positions.refusals["BTC"] = "rifiuto"

    with caplog.at_level(logging.INFO, logger="autotrading.flows"):
        flows.stop.execute(StopFlowCommand(flow.id, USER))

    (record,) = [record for record in caplog.records if record.getMessage() == "flusso fermato"]
    assert (record.getMessage(), record.__dict__["flow_id"], record.__dict__["left_open"]) == (
        "flusso fermato",
        str(flow.id.value),
        ["BTC"],
    )


def test_a_raise_within_the_free_capital_becomes_the_next_version_and_its_change_is_recorded(flows: Flows) -> None:
    flow = flows.saved(status=FlowStatus.STOPPED)
    flows.saved(name="beta", assets=("SOL",), capital=Decimal(100))

    changed = flows.change_capital.execute(ChangeAllocatedCapitalCommand(flow.id, Decimal(900), USER))

    assert changed.configuration == replace(flow.configuration, version=2, allocated_capital=Decimal(900))
    assert flows.repository.get(flow.id) == changed
    assert flows.list_changes.execute(ListCapitalChangesCommand(flow.id)) == (
        CapitalChange(flow.id, NOW, Decimal(400), Decimal(900), USER),
    )
    assert flows.positions.margins_asked == []


def test_a_raise_beyond_the_capital_available_is_refused_and_nothing_changes(flows: Flows) -> None:
    flow = flows.saved()
    flows.saved(name="beta", assets=("SOL",), capital=Decimal(100))

    with pytest.raises(CapitalAboveAvailableCapitalError) as raised:
        flows.change_capital.execute(ChangeAllocatedCapitalCommand(flow.id, Decimal(901), USER))

    assert raised.value.available == "900 USDC"
    assert flows.repository.get(flow.id) == flow
    assert flows.list_changes.execute(ListCapitalChangesCommand(flow.id)) == ()


def test_a_reduction_is_checked_against_the_margin_of_the_positions_of_the_flow(flows: Flows) -> None:
    flow = flows.saved()
    flows.positions.margin = Decimal(150)

    changed = flows.change_capital.execute(ChangeAllocatedCapitalCommand(flow.id, Decimal(150), USER))

    assert changed.configuration.allocated_capital == Decimal(150)
    assert flows.positions.margins_asked == [(flows.account_id, ("BTC", "ETH"))]


def test_a_reduction_below_the_committed_margin_is_refused(flows: Flows) -> None:
    flow = flows.saved()
    flows.positions.margin = Decimal(150)

    with pytest.raises(CapitalBelowCommittedMarginError) as raised:
        flows.change_capital.execute(ChangeAllocatedCapitalCommand(flow.id, Decimal(149), USER))

    assert raised.value.committed_margin == "150 USDC"
    assert flows.repository.get(flow.id) == flow


def test_a_margin_that_cannot_be_read_refuses_the_reduction(flows: Flows) -> None:
    flow = flows.saved()
    flows.positions.margin_failure = FlowExchangeUnavailableError()

    with pytest.raises(FlowExchangeUnavailableError):
        flows.change_capital.execute(ChangeAllocatedCapitalCommand(flow.id, Decimal(100), USER))

    assert flows.repository.get(flow.id) == flow


def test_the_same_capital_changes_nothing_and_reads_nothing(flows: Flows) -> None:
    flow = flows.saved()
    flows.accounts.reachable = False

    assert flows.change_capital.execute(ChangeAllocatedCapitalCommand(flow.id, Decimal("400.00"), USER)) == flow
    assert flows.store.versions[flow.id] == [flow.configuration]
    assert flows.positions.margins_asked == []


def test_an_archived_flow_keeps_its_capital_before_anything_is_read(flows: Flows) -> None:
    flow = flows.saved(status=FlowStatus.ARCHIVED)
    flows.accounts.reachable = False

    with pytest.raises(ArchivedFlowNotModifiableError):
        flows.change_capital.execute(ChangeAllocatedCapitalCommand(flow.id, Decimal(400), USER))


def test_the_change_is_recorded_with_the_new_version(flows: Flows, caplog: pytest.LogCaptureFixture) -> None:
    flow = flows.saved()

    with caplog.at_level(logging.INFO, logger="autotrading.flows"):
        flows.change_capital.execute(ChangeAllocatedCapitalCommand(flow.id, Decimal(500), USER))

    (record,) = caplog.records
    assert (record.getMessage(), record.__dict__["flow_id"], record.__dict__["version"]) == (
        "capitale allocato cambiato",
        str(flow.id.value),
        2,
    )


def test_the_history_of_a_flow_of_another_tenant_is_not_found(flows: Flows) -> None:
    theirs = a_flow(TenantId.new())
    flows.store.flows.append(theirs)

    with pytest.raises(FlowNotFoundError):
        flows.list_changes.execute(ListCapitalChangesCommand(theirs.id))


@pytest.mark.parametrize("reason", [CloseReason.FLOW_STOP, CloseReason.ACCOUNT_REMOVAL])
def test_each_position_closed_enters_the_history_with_the_reason_of_the_stop(flows: Flows, reason: CloseReason) -> None:
    flow = flows.saved(assets=("BTC", "ETH", "SOL"))
    flows.openings.openings[flow.id, "BTC"] = OPENING
    flows.openings.openings[flow.id, "SOL"] = OPENING
    flows.positions.none_open.add("SOL")

    flows.stop.execute(StopFlowCommand(flow.id, USER, reason))

    assert flows.closed.positions == [
        ClosedPosition(
            tenant_id=flows.tenant_id,
            flow_id=flow.id,
            asset="BTC",
            side=TradeSide.LONG,
            leverage=2,
            margin=Decimal(50),
            opening=PositionEnd(Decimal(100000), OPENED, OPENED),
            closing=PositionEnd(Decimal(102000), FILL.at),
            fees=Decimal("0.08"),
            reason=reason,
        )
    ]


def test_a_stop_closes_for_the_stop_of_the_flow_unless_told_otherwise(flows: Flows) -> None:
    flow = flows.saved(assets=("BTC",))
    flows.openings.openings[flow.id, "BTC"] = OPENING

    flows.stop.execute(StopFlowCommand(flow.id, USER))

    assert [position.reason for position in flows.closed.positions] == [CloseReason.FLOW_STOP]


def test_a_position_the_flow_never_opened_is_closed_without_history(
    flows: Flows, caplog: pytest.LogCaptureFixture
) -> None:
    flow = flows.saved(assets=("BTC",))

    with caplog.at_level(logging.WARNING, logger="autotrading.flows"):
        outcome = flows.stop.execute(StopFlowCommand(flow.id, USER))

    assert (outcome.left_open, flows.closed.positions) == ((), [])
    (record,) = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert (record.getMessage(), record.__dict__["flow_id"], record.__dict__["asset"]) == (
        "posizione chiusa senza apertura del flusso",
        str(flow.id.value),
        "BTC",
    )


def test_a_refusal_without_a_reason_is_still_a_position_left_open(flows: Flows) -> None:
    flow = flows.saved(assets=("BTC",))
    flows.positions.refusals["BTC"] = ""

    assert flows.stop.execute(StopFlowCommand(flow.id, USER)).left_open == (PositionLeftOpen("BTC", ""),)
