"""R6.2.2: a flow that uses an expired key goes in pause with the flows of the key, as for a key revoked (R1.2.4)."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from autotrading.application.flows.pause_affected_flows import PauseAffectedFlowsUseCase
from autotrading.application.flows.pause_flows_on_expired_keys import (
    PauseFlowsOnExpiredKeysCommand,
    PauseFlowsOnExpiredKeysUseCase,
)
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_key import FlowKey
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_repository import FlowStore, InMemoryAutomaticPauseAdapter, InMemoryFlowRepositoryAdapter
from tests.support.flows import ANTHROPIC_MODEL, OPENROUTER_MODEL, a_configuration, a_flow

TENANT = TenantId.new()
ACCOUNT, OTHER_ACCOUNT = uuid4(), uuid4()
TODAY = datetime(2026, 12, 15, 6, 0, tzinfo=UTC)


class World:
    def __init__(self, *keys: FlowKey) -> None:
        self.store = FlowStore()
        self.keys = keys
        self.told: list[tuple[str, str]] = []
        flows = InMemoryFlowRepositoryAdapter(self.store, TENANT)
        pause = PauseAffectedFlowsUseCase(flows, InMemoryAutomaticPauseAdapter(self.store, TENANT), self)
        self.use_case = PauseFlowsOnExpiredKeysUseCase(self, flows, pause, self)

    def dated_keys(self) -> tuple[FlowKey, ...]:
        return self.keys

    def now(self) -> datetime:
        return TODAY

    def execute(self, flow_id: UUID, flow_name: str, reason: str) -> None:  # noqa: ARG002 - the notice of the pause
        self.told.append((flow_name, reason))

    def add(self, name: str, account_id: UUID = OTHER_ACCOUNT, model: str = ANTHROPIC_MODEL) -> Flow:
        configuration = a_configuration(model=model)
        flow = a_flow(TENANT, name=name, status=FlowStatus.ACTIVE, account_id=account_id, configuration=configuration)
        self.store.flows.append(flow)
        return flow

    def statuses(self) -> dict[str, tuple[FlowStatus, str | None]]:
        return {flow.name.value: (flow.status, self.store.pause_reasons.get(flow.id)) for flow in self.store.flows}


def test_the_daily_check_pauses_every_active_flow_of_an_expired_key_with_its_reason_and_notice() -> None:
    world = World(FlowKey("openrouter", date(2026, 12, 15), provider="openrouter"))
    world.add("alfa", model=OPENROUTER_MODEL)
    world.add("beta", model=OPENROUTER_MODEL)
    world.add("gamma")

    assert world.use_case.execute(PauseFlowsOnExpiredKeysCommand())

    assert world.statuses() == {
        "alfa": (FlowStatus.PAUSED, "chiave openrouter scaduta"),
        "beta": (FlowStatus.PAUSED, "chiave openrouter scaduta"),
        "gamma": (FlowStatus.ACTIVE, None),
    }
    assert world.told == [("alfa", "chiave openrouter scaduta"), ("beta", "chiave openrouter scaduta")]


def test_the_cycle_of_a_flow_pauses_the_flows_of_the_expired_credentials_of_its_account() -> None:
    world = World(FlowKey("test-1", date(2026, 12, 1), account_id=ACCOUNT))
    alfa = world.add("alfa", account_id=ACCOUNT)
    world.add("beta", account_id=ACCOUNT)

    assert world.use_case.execute(PauseFlowsOnExpiredKeysCommand(alfa.id.value))

    assert {status for status, _ in world.statuses().values()} == {FlowStatus.PAUSED}


def test_a_key_that_expires_tomorrow_or_another_flow_uses_pauses_nothing() -> None:
    world = World(
        FlowKey("openrouter", date(2026, 12, 16), provider="openrouter"),
        FlowKey("test-1", date(2026, 12, 1), account_id=ACCOUNT),
    )
    alfa = world.add("alfa", model=OPENROUTER_MODEL)
    world.add("beta", account_id=ACCOUNT)

    assert not world.use_case.execute(PauseFlowsOnExpiredKeysCommand(alfa.id.value))

    assert world.statuses()["alfa"] == (FlowStatus.ACTIVE, None)
    assert world.statuses()["beta"] == (FlowStatus.ACTIVE, None)
