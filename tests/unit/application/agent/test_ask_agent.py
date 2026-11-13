from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from autotrading.application.agent.ask_agent import AskAgentCommand, AskAgentUseCase
from autotrading.application.agent.ask_flow_agent import AskFlowAgentUseCase
from autotrading.application.agent.compose_agent_context import ComposeAgentContextUseCase
from autotrading.application.agent.errors import ModelKeyMissingError, ModelUnavailableError, ProviderKeyNotOpenedError
from autotrading.domain.agent.agent_context import AgentContext, FlowStateView, SourceData
from autotrading.domain.agent.decision import TradeAction
from autotrading.domain.agent.errors import ModelNotAvailableError
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.model_usage import ModelPrices, ModelUsage
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey
from autotrading.domain.agent.sealed_provider_key import SealedProviderKey
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.model_call import FakeModelCallAdapter
from tests.fakes.model_catalog import InMemoryModelCatalogAdapter
from tests.fakes.provider_keys import (
    FakeProviderKeyOpenerAdapter,
    FakeProviderKeySealerAdapter,
    InMemoryProviderKeyRepositoryAdapter,
    ProviderKeyStore,
    ProviderKeyVault,
)

TENANT = TenantId.new()
TENANT_KEY = "K-FAKE-TENANT"
OPENROUTER = ProviderName("openrouter")
PRICED = "anthropic/claude-test"
NOW = datetime(2026, 11, 12, 10, 30, tzinfo=UTC)
CATALOG = ModelCatalog(
    (
        ModelDefinition("openrouter/deepseek-chat", ()),
        ModelDefinition(PRICED, (), ModelPrices(Decimal(1), Decimal(2))),
    )
)
CONTEXT = AgentContext(
    instructions="Sei un trader prudente",
    assets=("BTC", "ETH"),
    max_leverage=5,
    started_at=NOW,
    now=NOW,
    state=FlowStateView("USDC", Decimal(400), Decimal(400), Decimal(400), Decimal(400), Decimal(0), ()),
    sources=(),
    missing=(),
)
ANSWER = (
    '{"decisioni": [{"asset": "BTC", "azione": "apri", "direzione": "long", "quota": 0.1, "leva": 3,'
    ' "ragionamento": "rottura"}]}'
)


class World:
    def __init__(self) -> None:
        self.vault: ProviderKeyVault = {}
        self.store = ProviderKeyStore()
        self.keys = InMemoryProviderKeyRepositoryAdapter(self.store, TENANT)
        self.model = FakeModelCallAdapter(text=ANSWER)
        self.use_case = AskAgentUseCase(
            InMemoryModelCatalogAdapter(CATALOG), self.keys, FakeProviderKeyOpenerAdapter(self.vault), self.model
        )

    def register(self, provider: str, secret: str) -> None:
        name = ProviderName(provider)
        sealed = FakeProviderKeySealerAdapter(TENANT, self.vault).seal(name, ProviderKey(secret))
        self.keys.add(RegisteredProviderKey(TENANT, name, sealed))

    def ask(self, model: str = "openrouter/deepseek-chat") -> object:
        return self.use_case.execute(AskAgentCommand(model, {"temperature": Decimal("0.5")}, CONTEXT))


@pytest.fixture
def world() -> World:
    return World()


def test_the_model_of_the_flow_is_called_with_the_key_of_the_tenant_and_the_context(world: World) -> None:
    world.register("openrouter", TENANT_KEY)

    world.ask()

    [call] = world.model.calls
    assert call.model == "openrouter/deepseek-chat"
    assert call.key == ProviderKey(TENANT_KEY)
    assert call.settings == {"temperature": Decimal("0.5")}
    assert call.messages == CONTEXT.messages()


def test_the_answer_is_read_against_the_assets_of_the_flow(world: World) -> None:
    world.register("openrouter", TENANT_KEY)

    answer = world.use_case.execute(AskAgentCommand("openrouter/deepseek-chat", {}, CONTEXT))

    assert [(decision.asset, decision.action) for decision in answer.response.decisions] == [("BTC", TradeAction.OPEN)]
    assert answer.response.missing == ("ETH",)
    assert answer.response.raw == ANSWER


def test_the_cost_reported_by_the_provider_is_kept(world: World) -> None:
    world.register("openrouter", TENANT_KEY)
    world.model.usage = ModelUsage(2000, 500, Decimal("0.0031"))

    answer = world.use_case.execute(AskAgentCommand("openrouter/deepseek-chat", {}, CONTEXT))

    assert answer.usage == ModelUsage(2000, 500, Decimal("0.0031"))
    assert answer.cost_usd == Decimal("0.0031")


def test_without_a_reported_cost_the_prices_of_the_catalog_give_it(world: World) -> None:
    world.register("anthropic", TENANT_KEY)
    world.model.usage = ModelUsage(1000, 1000, None)

    answer = world.use_case.execute(AskAgentCommand(PRICED, {}, CONTEXT))

    assert answer.cost_usd == Decimal("0.003")


def test_without_reported_cost_nor_prices_the_cost_is_not_available(world: World) -> None:
    world.register("openrouter", TENANT_KEY)
    world.model.usage = ModelUsage(1000, 1000, None)

    answer = world.use_case.execute(AskAgentCommand("openrouter/deepseek-chat", {}, CONTEXT))

    assert answer.cost_usd is None


def test_a_provider_without_a_key_of_the_tenant_is_a_permanent_error(world: World) -> None:
    with pytest.raises(ModelKeyMissingError, match="nessuna chiave registrata per il fornitore: openrouter") as raised:
        world.ask()

    assert raised.value.permanent
    assert raised.value.provider == OPENROUTER
    assert world.model.calls == []


def test_a_key_the_worker_cannot_open_is_never_sent(world: World) -> None:
    world.keys.add(RegisteredProviderKey(TENANT, OPENROUTER, SealedProviderKey(1, b"copied")))

    with pytest.raises(ProviderKeyNotOpenedError) as raised:
        world.ask()

    assert raised.value.permanent
    assert world.model.calls == []


def test_a_model_no_longer_in_the_catalog_is_not_called(world: World) -> None:
    with pytest.raises(ModelNotAvailableError):
        world.ask("openrouter/gone")

    assert world.model.calls == []


def test_a_failing_call_fails_the_cycle_as_it_is(world: World) -> None:
    world.register("openrouter", TENANT_KEY)
    world.model.failure = ModelUnavailableError(OPENROUTER, "503")

    with pytest.raises(ModelUnavailableError):
        world.ask()


@dataclass(frozen=True, slots=True)
class Question:
    """A question as a cycle of a flow asks it: the model of the flow and the data of the context."""

    model: str = "openrouter/deepseek-chat"
    settings: Mapping[str, Decimal | str] = field(default_factory=dict)
    instructions: str = CONTEXT.instructions
    assets: tuple[str, ...] = CONTEXT.assets
    max_leverage: int = CONTEXT.max_leverage
    started_at: datetime = NOW
    now: datetime = NOW
    state: FlowStateView = CONTEXT.state
    sources: tuple[SourceData, ...] = ()
    missing: tuple[str, ...] = ()


def test_the_question_of_a_flow_asks_its_model_with_the_composed_context() -> None:
    world = World()
    world.register("openrouter", TENANT_KEY)

    answer = AskFlowAgentUseCase(ComposeAgentContextUseCase(), world.use_case).execute(Question())

    assert world.model.calls[-1].messages == CONTEXT.messages()
    assert [decision.action for decision in answer.response.decisions] == [TradeAction.OPEN]
