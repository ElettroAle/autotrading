from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.application.flows.list_flow_overviews import ListFlowOverviewsUseCase
from autotrading.application.flows.ports import FlowSummary
from autotrading.application.flows.read_flow_state import ReadFlowStateUseCase
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.cycle_schedule import CycleSchedule
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_return import FlowReturn
from autotrading.domain.flows.ledger import FlowTotals
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.cycles import InMemoryCycleRepositoryAdapter
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.activity import CURRENCY, a_position, an_activity
from tests.support.flows import a_configuration, a_flow

STARTED = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
NOW = STARTED + timedelta(minutes=20)
TENANT = TenantId(uuid4())
ACCOUNT = uuid4()


class FakeFlowSummariesAdapter:
    def __init__(self) -> None:
        self.summaries: list[FlowSummary] = []

    def execute(self) -> list[FlowSummary]:
        return self.summaries


class Bench:
    def __init__(self) -> None:
        self.store = FlowStore()
        self.summaries = FakeFlowSummariesAdapter()
        self.history = InMemoryCycleRepositoryAdapter()
        self.activity = FakeAccountActivityAdapter()
        self.ledger = InMemoryFlowLedgerAdapter()
        flows = InMemoryFlowRepositoryAdapter(self.store, TENANT)
        self.use_case = ListFlowOverviewsUseCase(
            self.summaries, self.history, ReadFlowStateUseCase(flows, self.activity, self.ledger), "dev", lambda: NOW
        )

    def flow(
        self, status: str = "attivo", schedule: CycleSchedule | None = None, capital: Decimal = Decimal(300)
    ) -> tuple[Flow, FlowSummary]:
        flow = a_flow(
            TENANT, account_id=ACCOUNT, configuration=a_configuration(assets=("BTC",), allocated_capital=capital)
        )
        self.store.flows.append(flow)
        summary = FlowSummary(flow.id.value, "alfa", "test-1", status, None, "openrouter/deepseek-chat", schedule)
        self.summaries.summaries.append(summary)
        return flow, summary

    def cycles(self, summary: FlowSummary, count: int) -> list[CycleRecord]:
        records = [
            CycleRecord(summary.flow_id, STARTED + timedelta(minutes=15 * index), CycleOutcome.COMPLETED)
            for index in range(count)
        ]
        for record in records:
            self.history.record(record)
        return records


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_an_active_flow_shows_its_last_cycle_and_the_next_planned_one(bench: Bench) -> None:
    _, active = bench.flow(schedule=CycleSchedule(STARTED, timedelta(minutes=15)))
    bench.history.record(CycleRecord(active.flow_id, STARTED, CycleOutcome.COMPLETED))
    last = CycleRecord(active.flow_id, STARTED + timedelta(minutes=15), CycleOutcome.FAILED)
    bench.history.record(last)

    [overview] = bench.use_case.execute()

    assert (overview.summary, overview.environment) == (active, "dev")
    assert overview.last_cycle == last
    assert overview.next_cycle_at == STARTED + timedelta(minutes=30)


def test_a_flow_without_schedule_nor_cycles_has_neither_last_nor_next_cycle(bench: Bench) -> None:
    bench.flow(status="in pausa")

    [overview] = bench.use_case.execute()

    assert (overview.last_cycle, overview.next_cycle_at, overview.recent_cycles) == (None, None, ())


def test_a_flow_shows_the_outcomes_of_its_last_ten_cycles_from_the_most_recent(bench: Bench) -> None:
    _, summary = bench.flow()
    records = bench.cycles(summary, 12)

    [overview] = bench.use_case.execute()

    assert overview.recent_cycles == tuple(reversed(records[2:]))


def test_a_flow_shows_its_initial_and_current_capital_from_its_attributed_state(bench: Bench) -> None:
    flow, _ = bench.flow(capital=Decimal(300))
    bench.ledger.totals[flow.id] = FlowTotals(flow.id, Decimal(15), Decimal(5))
    bench.activity.activities[ACCOUNT] = an_activity(positions=(a_position("BTC", unrealized_pnl=Decimal(20)),))

    [overview] = bench.use_case.execute()

    assert overview.capital == FlowReturn(Decimal(300), Decimal(330))
    assert overview.currency == CURRENCY


def test_the_overview_fails_when_the_state_of_a_flow_cannot_be_read(bench: Bench) -> None:
    bench.flow()
    bench.activity.reachable = False

    with pytest.raises(FlowExchangeUnavailableError):
        bench.use_case.execute()


def test_a_draft_has_neither_capital_nor_return_and_reads_no_account(bench: Bench) -> None:
    draft = a_flow(TENANT, account_id=ACCOUNT).duplicated()
    bench.store.flows.append(draft)
    bench.summaries.summaries.append(
        FlowSummary(draft.id.value, "alfa (copia)", "", "bozza", None, "openrouter/deepseek-chat", None)
    )

    [overview] = bench.use_case.execute()

    assert (overview.currency, overview.capital, overview.next_cycle_at) == (None, None, None)
