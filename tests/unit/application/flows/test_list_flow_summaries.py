from datetime import UTC, datetime, timedelta
from uuid import uuid4

from autotrading.application.flows.list_flow_summaries import ListFlowSummariesUseCase
from autotrading.domain.flows.cycle_schedule import CycleSchedule
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter, InMemoryFlowTimingAdapter
from tests.support.accounts import an_account
from tests.support.flows import a_flow

TENANT = TenantId(uuid4())
STARTED = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)


def summaries_of(flows: FlowStore, accounts: AccountStore) -> ListFlowSummariesUseCase:
    return ListFlowSummariesUseCase(
        InMemoryFlowRepositoryAdapter(flows, TENANT),
        InMemoryAccountRepositoryAdapter(accounts, TENANT),
        InMemoryFlowTimingAdapter(flows, TENANT),
    )


def test_an_active_flow_is_planned_from_its_anchor_on_its_account() -> None:
    flows, accounts = FlowStore(), AccountStore()
    account = an_account(TENANT)
    accounts.accounts.append(account)
    flow = a_flow(TENANT, status=FlowStatus.ACTIVE, account_id=account.id.value)
    flows.flows.append(flow)
    flows.anchors[flow.id] = STARTED

    [summary] = summaries_of(flows, accounts).execute()

    assert (summary.flow_id, summary.name, summary.account, summary.status) == (
        flow.id.value,
        "alfa",
        "test-1",
        "attivo",
    )
    assert summary.model == flow.configuration.model.name
    assert summary.schedule == CycleSchedule(STARTED, timedelta(minutes=flow.configuration.cycle_interval.minutes))


def test_a_paused_flow_keeps_its_reason_and_plans_nothing() -> None:
    flows = FlowStore()
    flow = a_flow(TENANT, status=FlowStatus.PAUSED)
    flows.flows.append(flow)
    flows.anchors[flow.id] = STARTED
    flows.pause_reasons[flow.id] = "credito esaurito presso openrouter"

    [summary] = summaries_of(flows, AccountStore()).execute()

    assert (summary.pause_reason, summary.schedule, summary.account) == ("credito esaurito presso openrouter", None, "")


def test_an_archived_flow_is_not_in_use() -> None:
    flows = FlowStore()
    flows.flows.append(a_flow(TENANT, status=FlowStatus.ARCHIVED))

    assert summaries_of(flows, AccountStore()).execute() == []


def test_a_draft_has_no_account_and_plans_nothing() -> None:
    flows = FlowStore()
    flows.flows.append(a_flow(TENANT, status=FlowStatus.STOPPED).duplicated())

    [summary] = summaries_of(flows, AccountStore()).execute()

    assert (summary.name, summary.status, summary.account, summary.schedule) == ("alfa (copia)", "bozza", "", None)
