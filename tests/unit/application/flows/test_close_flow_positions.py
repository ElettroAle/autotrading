from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from autotrading.application.flows.close_flow_positions import (
    CloseFlowPositionsCommand,
    CloseFlowPositionsUseCase,
    ClosingPorts,
)
from autotrading.application.flows.ports import PositionToClose
from autotrading.domain.flows.closed_position import CloseReason, PositionEnd
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.stop_outcome import ClosingFill, FlowClosings, PositionLeftOpen, PositionOpening
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.closed_position_repository import ClosedPositionStore, InMemoryClosedPositionRepositoryAdapter
from tests.fakes.exit_plan_repository import ExitPlanStore, InMemoryExitPlanRepositoryAdapter
from tests.fakes.position_closed_notices import FakePositionClosedNoticeAdapter
from tests.fakes.running_cycle import FakeRunningCycleAdapter
from tests.support.flows import a_configuration, a_flow
from tests.support.position_closings import NOTHING_TO_CLOSE, ClosingAnswer, closed_by, refused

USER = UserId("oid-anna")
TENANT = TenantId.new()
OPENED = datetime(2026, 11, 16, 8, 0, tzinfo=UTC)
FILL = ClosingFill(Decimal(102000), datetime(2026, 11, 16, 9, 45, tzinfo=UTC), Decimal("0.05"))
OPENING = PositionOpening(TradeSide.LONG, 2, Decimal(50), PositionEnd(Decimal(100000), OPENED, OPENED), Decimal("0.03"))


class ScriptedPositions:
    def __init__(self, answers: dict[str, ClosingAnswer]) -> None:
        self.answers = answers
        self.asked: list[PositionToClose] = []

    def execute(self, position: PositionToClose) -> ClosingAnswer:
        self.asked.append(position)
        return self.answers[position.asset]


class Openings:
    def last_opening(self, flow_id: FlowId, asset: str) -> PositionOpening | None:  # noqa: ARG002 - the opening of any flow
        return OPENING if asset == "BTC" else None


def closings_of(
    answers: dict[str, ClosingAnswer],
    reason: CloseReason = CloseReason.EMERGENCY,
    notices: FakePositionClosedNoticeAdapter | None = None,
) -> tuple[FlowClosings, ClosedPositionStore]:
    flow = a_flow(
        TENANT, status=FlowStatus.ACTIVE, account_id=uuid4(), configuration=a_configuration(assets=tuple(answers))
    )
    store = ClosedPositionStore()
    ports = ClosingPorts(
        FakeRunningCycleAdapter(lambda: 0),
        ScriptedPositions(answers),
        Openings(),
        InMemoryClosedPositionRepositoryAdapter(store, TENANT),
        notices or FakePositionClosedNoticeAdapter(),
        InMemoryExitPlanRepositoryAdapter(ExitPlanStore(), TENANT),
    )
    command = CloseFlowPositionsCommand(flow, USER, reason)
    return CloseFlowPositionsUseCase(ports).execute(command), store


def test_tells_the_positions_it_closed_and_those_left_open() -> None:
    closings, _ = closings_of({"BTC": closed_by(FILL), "ETH": refused("Order rejected"), "SOL": NOTHING_TO_CLOSE})

    assert closings == FlowClosings(closed=("BTC",), left_open=(PositionLeftOpen("ETH", "Order rejected"),))


def test_a_position_closed_without_an_opening_of_the_flow_is_closed_all_the_same() -> None:
    closings, store = closings_of({"ETH": closed_by(FILL)})

    assert closings.closed == ("ETH",)
    assert store.positions == []


def test_records_each_closing_with_the_reason_of_the_command() -> None:
    _, store = closings_of({"BTC": closed_by(FILL)})

    assert [position.reason for position in store.positions] == [CloseReason.EMERGENCY]


def test_nothing_to_close_closes_nothing() -> None:
    closings, _ = closings_of({"BTC": NOTHING_TO_CLOSE})

    assert closings == FlowClosings()


def test_each_closing_is_told_with_the_reason_of_the_command() -> None:
    notices = FakePositionClosedNoticeAdapter()

    _, store = closings_of({"BTC": closed_by(FILL)}, CloseReason.CASH_OUT, notices)

    [position] = store.positions
    assert notices.told == [("alfa", "BTC", position.pnl, "incasso")]


def test_the_closings_of_an_emergency_enter_the_history_without_being_told_one_by_one() -> None:
    notices = FakePositionClosedNoticeAdapter()

    _, store = closings_of({"BTC": closed_by(FILL)}, CloseReason.EMERGENCY, notices)

    assert len(store.positions) == 1
    assert notices.told == []


def test_each_closing_carries_the_flow_it_closes_and_the_user_who_asked() -> None:
    flow = a_flow(TENANT, status=FlowStatus.ACTIVE, account_id=uuid4(), configuration=a_configuration(assets=("BTC",)))
    positions = ScriptedPositions({"BTC": closed_by(FILL)})
    ports = ClosingPorts(
        FakeRunningCycleAdapter(lambda: 0),
        positions,
        Openings(),
        InMemoryClosedPositionRepositoryAdapter(ClosedPositionStore(), TENANT),
        FakePositionClosedNoticeAdapter(),
        InMemoryExitPlanRepositoryAdapter(ExitPlanStore(), TENANT),
    )

    CloseFlowPositionsUseCase(ports).execute(CloseFlowPositionsCommand(flow, USER, CloseReason.FLOW_STOP))

    assert positions.asked == [PositionToClose(flow.assigned_account_id, "BTC", USER, flow.id.value)]
