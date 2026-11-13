from uuid import UUID, uuid4

from autotrading.application.agent.errors import ModelCreditExhaustedError
from autotrading.application.flows.errors import FlowExchangeUnavailableError, FlowLedgerIncompleteError
from autotrading.application.flows.pause_affected_flows import PauseAffectedFlowsCommand, PauseAffectedFlowsUseCase
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_repository import FlowStore, InMemoryAutomaticPauseAdapter, InMemoryFlowRepositoryAdapter
from tests.support.flows import ANTHROPIC_MODEL, a_configuration, a_flow

TENANT = TenantId.new()
ACCOUNT = uuid4()
OTHER_ACCOUNT = uuid4()
REASON = "credito esaurito presso openrouter"


class World:
    def __init__(self) -> None:
        self.store = FlowStore()
        flows = InMemoryFlowRepositoryAdapter(self.store, TENANT)
        self.use_case = PauseAffectedFlowsUseCase(flows, InMemoryAutomaticPauseAdapter(self.store, TENANT))

    def add(
        self, name: str, status: FlowStatus = FlowStatus.ACTIVE, account_id: UUID = ACCOUNT, model: str = ""
    ) -> Flow:
        configuration = a_configuration(model=model) if model else a_configuration()
        flow = a_flow(TENANT, name=name, status=status, account_id=account_id, configuration=configuration)
        self.store.flows.append(flow)
        return flow

    def status_of(self, name: str) -> FlowStatus:
        return next(flow.status for flow in self.store.flows if flow.name.value == name)

    def reason_of(self, name: str) -> str | None:
        flow = next(flow for flow in self.store.flows if flow.name.value == name)
        return self.store.pause_reasons.get(flow.id)


def test_the_flow_of_the_cycle_is_paused_with_the_reason() -> None:
    world = World()
    alfa = world.add("alfa", account_id=uuid4())

    paused = world.use_case.execute(PauseAffectedFlowsCommand(alfa.id.value, REASON))

    assert [flow.name.value for flow in paused] == ["alfa"]
    assert world.status_of("alfa") is FlowStatus.PAUSED
    assert world.reason_of("alfa") == REASON


def test_an_error_of_the_account_pauses_every_active_flow_of_the_account() -> None:
    world = World()
    alfa = world.add("alfa")
    world.add("beta")
    world.add("gamma", account_id=OTHER_ACCOUNT)

    world.use_case.execute(PauseAffectedFlowsCommand(alfa.id.value, REASON, account_id=ACCOUNT))

    assert (world.status_of("beta"), world.reason_of("beta")) == (FlowStatus.PAUSED, REASON)
    assert world.status_of("gamma") is FlowStatus.ACTIVE


def test_an_error_of_the_provider_pauses_the_active_flows_on_its_models() -> None:
    world = World()
    alfa = world.add("alfa", account_id=uuid4())
    world.add("beta", account_id=OTHER_ACCOUNT)
    world.add("gamma", account_id=uuid4(), model=ANTHROPIC_MODEL)

    world.use_case.execute(PauseAffectedFlowsCommand(alfa.id.value, REASON, provider="openrouter"))

    assert world.status_of("beta") is FlowStatus.PAUSED
    assert world.status_of("gamma") is FlowStatus.ACTIVE


def test_a_flow_not_active_keeps_its_status_and_reason() -> None:
    world = World()
    alfa = world.add("alfa")
    world.add("ferma", status=FlowStatus.STOPPED)
    world.add("sospesa", status=FlowStatus.PAUSED)

    paused = world.use_case.execute(PauseAffectedFlowsCommand(alfa.id.value, REASON, account_id=ACCOUNT))

    assert [flow.name.value for flow in paused] == ["alfa"]
    assert world.status_of("ferma") is FlowStatus.STOPPED
    assert (world.status_of("sospesa"), world.reason_of("sospesa")) == (FlowStatus.PAUSED, None)


def test_without_account_nor_provider_no_other_flow_is_involved() -> None:
    world = World()
    alfa = world.add("alfa")
    world.add("beta")

    world.use_case.execute(PauseAffectedFlowsCommand(alfa.id.value, REASON))

    assert world.status_of("beta") is FlowStatus.ACTIVE


def test_the_command_takes_the_reason_and_the_scope_the_error_declares() -> None:
    flow_id = uuid4()

    by_account = PauseAffectedFlowsCommand.of_error(flow_id, FlowLedgerIncompleteError(ACCOUNT))
    by_provider = PauseAffectedFlowsCommand.of_error(flow_id, ModelCreditExhaustedError(ProviderName("openrouter")))
    alone = PauseAffectedFlowsCommand.of_error(flow_id, FlowExchangeUnavailableError())

    assert by_account == PauseAffectedFlowsCommand(flow_id, "registro delle esecuzioni incompleto", account_id=ACCOUNT)
    assert by_provider == PauseAffectedFlowsCommand(flow_id, REASON, provider="openrouter")
    assert alone == PauseAffectedFlowsCommand(flow_id, "exchange non raggiungibile, riprovare")
