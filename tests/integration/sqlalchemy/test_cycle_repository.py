from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, func, select, text, update
from sqlalchemy.exc import IntegrityError, ProgrammingError

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.cycle_repository import SqlAlchemyCycleRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import cycle_decisions, cycles, flows
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.cycle_filter import CycleFilter
from autotrading.domain.flows.cycle_record import (
    AbsentSource,
    CycleFailure,
    CycleOutcome,
    CycleRecord,
    FailedAttempt,
    StepDocument,
)
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.decision_filter import DecisionFilter
from autotrading.domain.flows.flow_cost import CycleCost
from autotrading.domain.flows.recorded_decision import DatedDecision, DecidedCycle, DecisionAction, RecordedDecision
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow

pytestmark = pytest.mark.integration

PLANNED = datetime(2026, 11, 12, 10, 7, tzinfo=UTC)


def new_flow(database: Engine) -> tuple[TenantId, UUID]:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    flow = a_flow(tenant.id, account_id=account.id.value)
    SqlAlchemyFlowRepositoryAdapter(database, tenant.id).add(flow)
    return tenant.id, flow.id.value


def a_failed_cycle(flow_id: UUID, planned_at: datetime = PLANNED) -> CycleRecord:
    return CycleRecord(
        flow_id=flow_id,
        planned_at=planned_at,
        outcome=CycleOutcome.FAILED,
        started_at=planned_at + timedelta(seconds=75),
        delay_seconds=75,
        steps=(CycleStep.READ_FLOW_STATE, CycleStep.COLLECT_SOURCES, CycleStep.COMPOSE_CONTEXT),
        absent_sources=(AbsentSource("notizie", "nessuna risposta entro 60 secondi"),),
        failure=CycleFailure(CycleStep.AGENT_DECISION, "ModelUnavailableError", "fornitore IA non raggiungibile"),
        documents=(StepDocument(CycleStep.COMPOSE_CONTEXT, {"messaggi": ["regole"], "margine": "50.10"}),),
        cost=CallCost(2000, 500, Decimal("0.0031")),
        model_attempts=4,
        failed_attempts=(FailedAttempt(CycleStep.READ_FLOW_STATE, 1, "FlowExchangeUnavailableError", "riprovare"),),
    )


def test_a_planned_instant_is_taken_only_once(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    first, second = (SqlAlchemyCycleRepositoryAdapter(database, tenant_id) for _ in range(2))

    assert first.claim(flow_id, PLANNED)
    assert not second.claim(flow_id, PLANNED)
    assert second.claim(flow_id, PLANNED + timedelta(minutes=15))


def test_a_taken_cycle_is_not_shown_until_it_is_recorded(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    repository.claim(flow_id, PLANNED)

    assert repository.newest(flow_id, 0, 50) == []
    assert repository.at(flow_id, PLANNED) is None


def test_a_recorded_cycle_reads_back_with_everything_it_produced(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    record = a_failed_cycle(flow_id)
    repository.claim(flow_id, PLANNED)

    repository.record(record)

    assert repository.at(flow_id, PLANNED) == record


def test_a_skipped_cycle_is_recorded_on_the_instant_it_took(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    repository.claim(flow_id, PLANNED)

    repository.record(CycleRecord.skipped(flow_id, PLANNED))

    assert repository.newest(flow_id, 0, 50) == [CycleRecord.skipped(flow_id, PLANNED)]


def test_the_cycles_come_from_the_most_recent_in_pages(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    for minutes in range(5):
        repository.record(CycleRecord.skipped(flow_id, PLANNED + timedelta(minutes=15 * minutes)))

    page = repository.newest(flow_id, 1, 2)

    assert [record.planned_at for record in page] == [PLANNED + timedelta(minutes=45), PLANNED + timedelta(minutes=30)]


def test_the_costs_are_those_of_the_cycles_that_called_the_model(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    repository.record(a_failed_cycle(flow_id))
    repository.record(CycleRecord.skipped(flow_id, PLANNED + timedelta(minutes=15)))
    unpriced = CycleRecord(flow_id, PLANNED + timedelta(minutes=30), CycleOutcome.COMPLETED, cost=CallCost(1, 1, None))
    repository.record(unpriced)

    assert repository.costs(flow_id) == [
        CycleCost(PLANNED, CallCost(2000, 500, Decimal("0.0031"))),
        CycleCost(PLANNED + timedelta(minutes=30), CallCost(1, 1, None)),
    ]


# ADR-costo-della-decisione-fallita-nel-registro-del-ciclo: a call without a known usage is among the costs.
def test_a_call_without_a_known_usage_is_among_the_costs_without_a_cost(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    lost = CycleRecord(flow_id, PLANNED, CycleOutcome.FAILED, call_without_usage=True)
    repository.record(lost)
    repository.record(CycleRecord(flow_id, PLANNED + timedelta(minutes=15), CycleOutcome.FAILED))

    assert repository.costs(flow_id) == [CycleCost(PLANNED, None)]
    assert repository.at(flow_id, PLANNED) == lost


def test_the_failed_cycles_are_counted_in_the_window(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    for hours in range(3):
        repository.record(a_failed_cycle(flow_id, PLANNED + timedelta(hours=hours)))
    repository.record(CycleRecord.skipped(flow_id, PLANNED + timedelta(hours=1, minutes=15)))

    window = TimeWindow(since=PLANNED + timedelta(hours=1), until=PLANNED + timedelta(hours=2))

    assert repository.failed_within(flow_id, window) == 1
    assert repository.failed_within(flow_id, TimeWindow()) == 3


def activated(database: Engine, tenant_id: TenantId, flow_id: UUID) -> datetime:
    """The flow made active, as a start or a resume does: the database stamps the anchor of its cycles."""
    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        connection.execute(update(flows).where(flows.c.id == flow_id).values(status="active"))
        anchor: datetime = connection.execute(select(flows.c.cycle_anchor).where(flows.c.id == flow_id)).scalar_one()
    return anchor


def a_cycle(flow_id: UUID, planned_at: datetime, outcome: CycleOutcome) -> CycleRecord:
    if outcome is CycleOutcome.FAILED:
        return a_failed_cycle(flow_id, planned_at)
    return CycleRecord(flow_id, planned_at, outcome)


def test_the_consecutive_failures_count_the_failed_cycles_after_the_last_completed_one(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    anchor = activated(database, tenant_id, flow_id)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    outcomes = (CycleOutcome.FAILED, CycleOutcome.COMPLETED, CycleOutcome.FAILED, CycleOutcome.SKIPPED)
    for index, outcome in enumerate((*outcomes, CycleOutcome.FAILED)):
        repository.record(a_cycle(flow_id, anchor + timedelta(minutes=15) * index, outcome))

    assert repository.consecutive_failures(flow_id) == 2


def test_the_consecutive_failures_count_only_since_the_flow_became_active(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    anchor = activated(database, tenant_id, flow_id)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    for minutes in (-30, -15, 0):
        repository.record(a_failed_cycle(flow_id, anchor + timedelta(minutes=minutes)))

    assert repository.consecutive_failures(flow_id) == 1


def test_a_flow_without_cycles_has_no_consecutive_failures(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    activated(database, tenant_id, flow_id)

    assert SqlAlchemyCycleRepositoryAdapter(database, tenant_id).consecutive_failures(flow_id) == 0


def test_the_cycles_of_another_tenant_stay_invisible(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    other_tenant, _ = new_flow(database)
    SqlAlchemyCycleRepositoryAdapter(database, tenant_id).record(a_failed_cycle(flow_id))
    other = SqlAlchemyCycleRepositoryAdapter(database, other_tenant)

    assert other.newest(flow_id, 0, 50) == []
    assert other.at(flow_id, PLANNED) is None
    assert other.costs(flow_id) == []
    assert other.costs_within(flow_id, TimeWindow()) == []
    assert other.failed_within(flow_id, TimeWindow()) == 0
    assert other.consecutive_failures(flow_id) == 0


def test_a_tenant_cannot_record_a_cycle_of_a_flow_of_another_tenant(database: Engine) -> None:
    _, flow_id = new_flow(database)
    other_tenant, _ = new_flow(database)

    with pytest.raises(IntegrityError, match="violates foreign key"):
        SqlAlchemyCycleRepositoryAdapter(database, other_tenant).record(a_failed_cycle(flow_id))


def test_a_recorded_cycle_cannot_be_deleted(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    SqlAlchemyCycleRepositoryAdapter(database, tenant_id).record(a_failed_cycle(flow_id))

    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        with pytest.raises(ProgrammingError, match="permission denied"):
            connection.execute(cycles.delete())


def test_a_session_without_tenant_sees_no_cycle(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    SqlAlchemyCycleRepositoryAdapter(database, tenant_id).record(a_failed_cycle(flow_id))

    with database.begin() as connection:
        assert connection.execute(text("SELECT count(*) FROM cycles")).scalar_one() == 0


def test_the_costs_within_a_window_are_those_of_the_cycles_planned_from_its_start_to_its_end(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    instants = [PLANNED + timedelta(minutes=15 * index) for index in range(4)]
    for instant in instants:
        repository.record(CycleRecord(flow_id, instant, CycleOutcome.COMPLETED, cost=CallCost(1, 1, Decimal("0.01"))))

    window = TimeWindow(since=instants[1], until=instants[3])

    assert [cost.planned_at for cost in repository.costs_within(flow_id, window)] == instants[1:3]
    assert [cost.planned_at for cost in repository.costs_within(flow_id, TimeWindow())] == instants


def a_cycle_deciding(flow_id: UUID, minutes: int, *actions: str) -> CycleRecord:
    decisions = tuple(RecordedDecision.named("BTC", action, None, 60, "r") for action in actions)
    return CycleRecord(
        flow_id,
        PLANNED + timedelta(minutes=minutes),
        CycleOutcome.COMPLETED,
        documents=(StepDocument(CycleStep.COMPOSE_CONTEXT, {"messaggi": []}),),
        decisions=decisions,
    )


# ADR filtri-dei-cicli-e-delle-posizioni-chiuse-nell-api: PostgreSQL filters and counts, so the pages stay right.
def test_the_cycles_are_filtered_by_outcome_decision_and_days_and_counted(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    opening = a_cycle_deciding(flow_id, 0, "apri")
    closing_and_holding = a_cycle_deciding(flow_id, 15, "mantieni", "chiudi")
    nothing_decided = a_cycle_deciding(flow_id, 30)
    failed = a_failed_cycle(flow_id, PLANNED + timedelta(minutes=45))
    skipped = CycleRecord.skipped(flow_id, PLANNED + timedelta(minutes=60))
    next_day = a_cycle_deciding(flow_id, 24 * 60, "apri")
    for record in (opening, closing_and_holding, nothing_decided, failed, skipped, next_day):
        repository.record(record)

    def matched(criteria: CycleFilter) -> list[datetime]:
        return [record.planned_at for record in repository.matching(flow_id, criteria, 0, 50)]

    assert matched(CycleFilter.named(outcome="fallito")) == [failed.planned_at]
    assert matched(CycleFilter.named(decision="apertura")) == [next_day.planned_at, opening.planned_at]
    assert matched(CycleFilter.named(decision="chiusura")) == [closing_and_holding.planned_at]
    assert matched(CycleFilter.named(decision="mantenimento")) == [closing_and_holding.planned_at]
    assert matched(CycleFilter.named(decision="nessuna")) == [
        skipped.planned_at,
        failed.planned_at,
        nothing_decided.planned_at,
    ]
    day = datetime.combine(PLANNED.date(), time(), tzinfo=UTC)
    last_minute = day + timedelta(hours=23, minutes=59)
    assert matched(CycleFilter.named(outcome="concluso", decision="apertura", since=day, until=last_minute)) == [
        opening.planned_at
    ]
    assert repository.count(flow_id, CycleFilter.named(outcome="concluso")) == 4
    assert repository.count(flow_id, CycleFilter()) == 6


def test_the_filtered_cycles_come_in_pages_and_leave_out_those_still_running(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    for minutes in range(0, 75, 15):
        repository.record(a_cycle_deciding(flow_id, minutes, "apri"))
    repository.claim(flow_id, PLANNED + timedelta(minutes=90))
    criteria = CycleFilter.named(decision="nessuna")

    page = repository.matching(flow_id, CycleFilter(), 1, 2)

    assert [record.planned_at for record in page] == [PLANNED + timedelta(minutes=45), PLANNED + timedelta(minutes=30)]
    assert (repository.matching(flow_id, criteria, 0, 50), repository.count(flow_id, criteria)) == ([], 0)


def test_the_filtered_cycles_of_another_tenant_stay_invisible(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    other_tenant, _ = new_flow(database)
    SqlAlchemyCycleRepositoryAdapter(database, tenant_id).record(a_failed_cycle(flow_id))
    other = SqlAlchemyCycleRepositoryAdapter(database, other_tenant)

    assert (other.matching(flow_id, CycleFilter(), 0, 50), other.count(flow_id, CycleFilter())) == ([], 0)


OPENING = RecordedDecision("BTC", DecisionAction.OPEN, TradeSide.LONG, 72, "trend rialzista")
HOLDING = RecordedDecision("ETH", DecisionAction.HOLD, None, 40, "attesa")


def a_completed_cycle(flow_id: UUID, minutes: int, *decisions: RecordedDecision) -> CycleRecord:
    return CycleRecord(flow_id, PLANNED + timedelta(minutes=minutes), CycleOutcome.COMPLETED, decisions=decisions)


# ADR decisioni-del-ciclo-registrate-per-asset: the decisions are written with the cycle, one row by asset.
def test_the_last_decision_is_that_of_the_most_recent_completed_cycle_with_decisions(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    repository.record(a_completed_cycle(flow_id, 0, HOLDING))
    repository.record(a_completed_cycle(flow_id, 15, OPENING, HOLDING))
    repository.record(a_completed_cycle(flow_id, 30))
    failed_after_deciding = replace(
        a_completed_cycle(flow_id, 45, HOLDING),
        outcome=CycleOutcome.FAILED,
        failure=CycleFailure(CycleStep.RISK_CHECK, "FakeTransientError", "timeout"),
    )
    repository.record(failed_after_deciding)
    repository.record(a_failed_cycle(flow_id, PLANNED + timedelta(minutes=60)))

    assert repository.last_decided(flow_id) == DecidedCycle(PLANNED + timedelta(minutes=15), (OPENING, HOLDING))


def test_a_flow_without_completed_cycles_with_decisions_has_no_last_decision(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    repository.record(a_failed_cycle(flow_id))

    assert repository.last_decided(flow_id) is None


def test_a_cycle_recorded_again_keeps_its_decisions_once(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    record = a_completed_cycle(flow_id, 0, OPENING)

    repository.record(record)
    repository.record(record)

    assert repository.last_decided(flow_id) == DecidedCycle(PLANNED, (OPENING,))


def test_the_decisions_of_another_tenant_stay_invisible(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    other_tenant, _ = new_flow(database)
    SqlAlchemyCycleRepositoryAdapter(database, tenant_id).record(a_completed_cycle(flow_id, 0, OPENING))

    assert SqlAlchemyCycleRepositoryAdapter(database, other_tenant).last_decided(flow_id) is None
    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(other_tenant.value), True)))
        assert connection.execute(select(func.count()).select_from(cycle_decisions)).scalar_one() == 0


def test_a_recorded_decision_cannot_be_deleted(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    SqlAlchemyCycleRepositoryAdapter(database, tenant_id).record(a_completed_cycle(flow_id, 0, OPENING))

    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        with pytest.raises(ProgrammingError, match="permission denied"):
            connection.execute(cycle_decisions.delete())


# ADR inversione-in-due-passi-nel-ciclo: a reversal is a decision of its own, without a direction (R1.4.10).
def test_a_reversal_is_recorded_among_the_decisions_of_the_cycle(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    reversal = RecordedDecision("BTC", DecisionAction.REVERSE, None, 70, "cambio di tendenza")

    repository.record(a_completed_cycle(flow_id, 0, reversal))

    assert repository.last_decided(flow_id) == DecidedCycle(PLANNED, (reversal,))


CLOSING = RecordedDecision("ADA", DecisionAction.CLOSE, None, 55, "obiettivo raggiunto")
SHORTING = RecordedDecision("ETH", DecisionAction.OPEN, TradeSide.SHORT, 61, "trend ribassista")


def at(minutes: int) -> datetime:
    return PLANNED + timedelta(minutes=minutes)


def a_history(database: Engine) -> tuple[SqlAlchemyCycleRepositoryAdapter, UUID]:
    tenant_id, flow_id = new_flow(database)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    repository.record(a_completed_cycle(flow_id, 0, HOLDING))
    repository.record(a_completed_cycle(flow_id, 15, OPENING, SHORTING, CLOSING))
    failed_after_deciding = replace(
        a_completed_cycle(flow_id, 30, OPENING),
        outcome=CycleOutcome.FAILED,
        failure=CycleFailure(CycleStep.RISK_CHECK, "FakeTransientError", "timeout"),
    )
    repository.record(failed_after_deciding)
    return repository, flow_id


# ADR storico-delle-decisioni-nell-api: the history reads the table of the decisions of the completed cycles.
def test_the_history_lists_the_decisions_of_completed_cycles_newest_first_then_by_asset(database: Engine) -> None:
    repository, flow_id = a_history(database)

    found = repository.decisions_matching(flow_id, DecisionFilter(), TimeWindow(), 0, 50)

    assert found == [
        DatedDecision(at(15), CLOSING),
        DatedDecision(at(15), OPENING),
        DatedDecision(at(15), SHORTING),
        DatedDecision(at(0), HOLDING),
    ]
    assert repository.decisions_count(flow_id, DecisionFilter(), TimeWindow()) == len(found)


def test_the_history_is_paged_with_offset_and_limit(database: Engine) -> None:
    repository, flow_id = a_history(database)

    found = repository.decisions_matching(flow_id, DecisionFilter(), TimeWindow(), 1, 2)

    assert found == [DatedDecision(at(15), OPENING), DatedDecision(at(15), SHORTING)]


def test_the_history_is_filtered_by_asset_action_direction_and_window(database: Engine) -> None:
    repository, flow_id = a_history(database)
    openings = DecisionFilter(action=DecisionAction.OPEN)
    shorts = DecisionFilter(asset="ETH", action=DecisionAction.OPEN, direction=TradeSide.SHORT)
    first_cycle = TimeWindow.of_minutes(at(0), at(0))

    assert repository.decisions_matching(flow_id, openings, TimeWindow(), 0, 50) == [
        DatedDecision(at(15), OPENING),
        DatedDecision(at(15), SHORTING),
    ]
    assert repository.decisions_matching(flow_id, shorts, TimeWindow(), 0, 50) == [DatedDecision(at(15), SHORTING)]
    assert repository.decisions_matching(flow_id, DecisionFilter(), first_cycle, 0, 50) == [
        DatedDecision(at(0), HOLDING)
    ]
    assert repository.decisions_count(flow_id, openings, TimeWindow()) == 2
    assert repository.decisions_count(flow_id, DecisionFilter(asset="ETH"), first_cycle) == 1


def test_the_history_of_another_tenant_stays_invisible(database: Engine) -> None:
    _, flow_id = a_history(database)
    other_tenant, _ = new_flow(database)
    other = SqlAlchemyCycleRepositoryAdapter(database, other_tenant)

    assert other.decisions_matching(flow_id, DecisionFilter(), TimeWindow(), 0, 50) == []
    assert other.decisions_count(flow_id, DecisionFilter(), TimeWindow()) == 0
