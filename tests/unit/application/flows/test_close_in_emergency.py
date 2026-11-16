from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.flows.close_flow_positions import CloseFlowPositionsUseCase, ClosingPorts
from autotrading.application.flows.close_in_emergency import (
    CloseInEmergencyCommand,
    CloseInEmergencyUseCase,
    EmergencyClosingPorts,
)
from autotrading.application.flows.errors import FlowExchangeUnavailableError, FlowNotFoundError
from autotrading.application.flows.list_emergency_flows import ListEmergencyFlowsUseCase
from autotrading.application.flows.ports import PositionToClose
from autotrading.domain.flows.closed_position import CloseReason, PositionEnd
from autotrading.domain.flows.emergency_closing import EmergencyClosing, EmergencyScope, FlowEmergencyOutcome
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.stop_outcome import ClosingFill, PositionLeftOpen, PositionOpening
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.account_thresholds import FakeAccountThresholdsAdapter
from tests.fakes.closed_position_repository import ClosedPositionStore, InMemoryClosedPositionRepositoryAdapter
from tests.fakes.emergency_closing_log import InMemoryEmergencyClosingLogAdapter
from tests.fakes.exit_plan_repository import ExitPlanStore, InMemoryExitPlanRepositoryAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryAutomaticPauseAdapter, InMemoryFlowRepositoryAdapter
from tests.fakes.position_closed_notices import FakePositionClosedNoticeAdapter
from tests.support.flows import a_configuration, a_flow
from tests.support.position_closings import NOTHING_TO_CLOSE, ClosingAnswer, closed_by, refused

USER = UserId("oid-anna")
NOW = datetime(2026, 11, 16, 9, 30, tzinfo=UTC)
OPENED = datetime(2026, 11, 16, 8, 0, tzinfo=UTC)
FILL = ClosingFill(Decimal(102000), datetime(2026, 11, 16, 9, 31, tzinfo=UTC), Decimal("0.05"))
OPENING = PositionOpening(TradeSide.LONG, 2, Decimal(50), PositionEnd(Decimal(100000), OPENED, OPENED), Decimal("0.03"))


class ScriptedPositions:
    """Closes the positions of the assets the test names, refuses or fails others, and records each call in order."""

    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.answers: dict[str, ClosingAnswer] = {}
        self.unreachable: set[str] = set()

    def execute(self, position: PositionToClose) -> ClosingAnswer:
        self.events.append(f"close {position.asset}")
        if position.asset in self.unreachable:
            raise FlowExchangeUnavailableError
        return self.answers.get(position.asset, NOTHING_TO_CLOSE)


class RecordingCycles:
    """Records each wait with the status the flow had by then: the pause comes before any closing."""

    def __init__(self, events: list[str], repository: InMemoryFlowRepositoryAdapter) -> None:
        self.events = events
        self._repository = repository

    def wait_until_finished(self, flow_id: FlowId) -> None:
        flow = self._repository.get(flow_id)
        self.events.append(f"wait {flow.name.value} {flow.status.value}")


class Openings:
    def last_opening(self, flow_id: FlowId, asset: str) -> PositionOpening | None:  # noqa: ARG002 - the opening of any flow
        return OPENING


class Emergency:
    def __init__(self) -> None:
        self.tenant_id = TenantId.new()
        self.account_id, self.other_account_id = uuid4(), uuid4()
        self.store = FlowStore()
        self.repository = InMemoryFlowRepositoryAdapter(self.store, self.tenant_id)
        self.events: list[str] = []
        self.positions = ScriptedPositions(self.events)
        self.closed = ClosedPositionStore()
        self.log: list[EmergencyClosing] = []
        accounts = FakeAccountThresholdsAdapter({self.account_id: "test-1", self.other_account_id: "test-2"})
        closings = CloseFlowPositionsUseCase(
            ClosingPorts(
                RecordingCycles(self.events, self.repository),
                self.positions,
                Openings(),
                InMemoryClosedPositionRepositoryAdapter(self.closed, self.tenant_id),
                FakePositionClosedNoticeAdapter(),
                InMemoryExitPlanRepositoryAdapter(ExitPlanStore(), self.tenant_id),
            )
        )
        self.use_case = CloseInEmergencyUseCase(
            self.tenant_id,
            EmergencyClosingPorts(
                ListEmergencyFlowsUseCase(self.repository, accounts),
                InMemoryAutomaticPauseAdapter(self.store, self.tenant_id),
                closings,
                InMemoryEmergencyClosingLogAdapter(self.log, self.tenant_id),
                lambda: NOW,
            ),
        )

    def flow(self, name: str, asset: str, status: FlowStatus = FlowStatus.ACTIVE, *, other: bool = False) -> Flow:
        account_id = self.other_account_id if other else self.account_id
        configuration = a_configuration(assets=(asset,))
        flow = a_flow(self.tenant_id, name=name, status=status, account_id=account_id, configuration=configuration)
        self.store.flows.append(flow)
        return flow

    def run(self, scope: EmergencyScope) -> EmergencyClosing:
        return self.use_case.execute(CloseInEmergencyCommand(scope, USER))

    def status_of(self, flow: Flow) -> FlowStatus:
        return self.repository.get(flow.id).status


@pytest.fixture
def emergency() -> Emergency:
    return Emergency()


def test_pauses_every_active_flow_of_the_scope_before_closing_its_positions(emergency: Emergency) -> None:
    alfa, beta = emergency.flow("alfa", "BTC"), emergency.flow("beta", "ETH")
    emergency.positions.answers = {"BTC": closed_by(FILL), "ETH": closed_by(FILL)}

    emergency.run(EmergencyScope(account_id=emergency.account_id))

    assert emergency.events == ["wait alfa in pausa", "close BTC", "wait beta in pausa", "close ETH"]
    assert emergency.store.pause_reasons == {alfa.id: "chiusura di emergenza", beta.id: "chiusura di emergenza"}


def test_reports_for_each_flow_the_positions_closed_and_those_left_open(emergency: Emergency) -> None:
    alfa, beta = emergency.flow("alfa", "BTC"), emergency.flow("beta", "ETH")
    emergency.positions.answers = {"BTC": refused("Order rejected"), "ETH": closed_by(FILL)}

    closing = emergency.run(EmergencyScope())

    assert closing.outcomes == (
        FlowEmergencyOutcome(alfa.id, "alfa", left_open=(PositionLeftOpen("BTC", "Order rejected"),)),
        FlowEmergencyOutcome(beta.id, "beta", closed=("ETH",)),
    )
    assert emergency.status_of(alfa) is FlowStatus.PAUSED


def test_records_every_closing_with_the_emergency_reason(emergency: Emergency) -> None:
    emergency.flow("alfa", "BTC")
    emergency.positions.answers = {"BTC": closed_by(FILL)}

    emergency.run(EmergencyScope())

    assert [position.reason for position in emergency.closed.positions] == [CloseReason.EMERGENCY]


def test_a_flow_that_fails_to_close_does_not_stop_the_others(emergency: Emergency) -> None:
    alfa, beta = emergency.flow("alfa", "BTC"), emergency.flow("beta", "ETH")
    emergency.positions.unreachable = {"BTC"}
    emergency.positions.answers = {"ETH": closed_by(FILL)}

    closing = emergency.run(EmergencyScope())

    assert closing.outcomes == (
        FlowEmergencyOutcome(alfa.id, "alfa", failure="exchange non raggiungibile, riprovare"),
        FlowEmergencyOutcome(beta.id, "beta", closed=("ETH",)),
    )
    assert emergency.status_of(alfa) is FlowStatus.PAUSED


def test_a_paused_flow_keeps_its_pause_and_its_reason(emergency: Emergency) -> None:
    alfa = emergency.flow("alfa", "BTC", FlowStatus.PAUSED)
    emergency.store.pause_reasons[alfa.id] = "credito esaurito"
    emergency.positions.answers = {"BTC": closed_by(FILL)}

    closing = emergency.run(EmergencyScope(flow_id=alfa.id))

    assert closing.outcomes == (FlowEmergencyOutcome(alfa.id, "alfa", closed=("BTC",)),)
    assert emergency.status_of(alfa) is FlowStatus.PAUSED
    assert emergency.store.pause_reasons[alfa.id] == "credito esaurito"


def test_leaves_the_flows_out_of_the_scope_untouched(emergency: Emergency) -> None:
    emergency.flow("alfa", "BTC")
    gamma = emergency.flow("gamma", "SOL", other=True)
    stopped = emergency.flow("delta", "ETH", FlowStatus.STOPPED)

    closing = emergency.run(EmergencyScope(account_id=emergency.account_id))

    assert [outcome.flow_name for outcome in closing.outcomes] == ["alfa"]
    assert emergency.status_of(gamma) is FlowStatus.ACTIVE
    assert emergency.status_of(stopped) is FlowStatus.STOPPED
    assert emergency.events == ["wait alfa in pausa", "close BTC"]


def test_logs_the_closing_with_its_instant_scope_and_outcome(emergency: Emergency) -> None:
    alfa = emergency.flow("alfa", "BTC")
    scope = EmergencyScope(flow_id=alfa.id)

    closing = emergency.run(scope)

    assert emergency.log == [closing]
    assert closing == EmergencyClosing(emergency.tenant_id, scope, NOW, (FlowEmergencyOutcome(alfa.id, "alfa"),))


def test_refuses_a_flow_of_another_tenant_and_closes_nothing(emergency: Emergency) -> None:
    omega = a_flow(TenantId.new(), name="omega", status=FlowStatus.ACTIVE, account_id=uuid4())
    emergency.store.flows.append(omega)

    with pytest.raises(FlowNotFoundError):
        emergency.run(EmergencyScope(flow_id=omega.id))

    assert emergency.events == []
    assert emergency.log == []
    assert emergency.store.pause_reasons == {}
