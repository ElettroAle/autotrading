from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from autotrading.application.agent.ask_agent import AskAgentCommand, AskAgentUseCase
from autotrading.application.agent.ask_flow_agent import AskFlowAgentUseCase
from autotrading.application.agent.compose_agent_context import ComposeAgentContextUseCase
from autotrading.application.agent.errors import (
    ModelCreditExhaustedError,
    ModelKeyMissingError,
    ModelKeyRejectedError,
    ModelUnavailableError,
    ProviderKeyNotOpenedError,
)
from autotrading.domain.agent.agent_context import AgentContext, FlowStateView, SourceData
from autotrading.domain.agent.decision import TradeAction
from autotrading.domain.agent.errors import ModelNotAvailableError
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.model_usage import ModelPrices, ModelUsage
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey
from autotrading.domain.agent.sealed_provider_key import SealedProviderKey
from autotrading.domain.errors import AutotradingError
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.model_call import FakeModelCallAdapter
from tests.fakes.model_catalog import InMemoryModelCatalogAdapter
from tests.fakes.model_gateway import FakeModelGatewayAdapter
from tests.fakes.pause import FakePauseAdapter
from tests.fakes.provider_keys import (
    FakeProviderKeyOpenerAdapter,
    FakeProviderKeySealerAdapter,
    InMemoryProviderKeyRepositoryAdapter,
    ProviderKeyStore,
    ProviderKeyVault,
)
from tests.support.provider_key import api_key_of

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
    system_prompt="Sei un trader prudente",
    assets=("BTC", "ETH"),
    started_at=NOW,
    now=NOW,
    state=FlowStateView("USDC", Decimal(400), Decimal(400), Decimal(400), Decimal(400), Decimal(0), ()),
    sources=(),
    missing=(),
)
ANSWER = (
    '{"decisioni": [{"asset": "BTC", "azione": "apri", "direzione": "long", "quota": 0.1, "leva": 3,'
    ' "obiettivo": null, "stop": null, "invalidazione": null, "confidenza": 70,'
    ' "ragionamento": "rottura"}]}'
)


class World:
    def __init__(self) -> None:
        self.vault: ProviderKeyVault = {}
        self.store = ProviderKeyStore()
        self.keys = InMemoryProviderKeyRepositoryAdapter(self.store, TENANT)
        self.model = FakeModelCallAdapter(text=ANSWER)
        self.pause = FakePauseAdapter()
        gateway = FakeModelGatewayAdapter(InMemoryModelCatalogAdapter(CATALOG), self.model)
        opener = FakeProviderKeyOpenerAdapter(self.vault)
        self.use_case = AskAgentUseCase({"models": gateway}, self.keys, opener, self.pause)

    def register(self, provider: str, secret: str) -> None:
        name = ProviderName(provider)
        sealed = FakeProviderKeySealerAdapter(TENANT, self.vault).seal(name, api_key_of(secret))
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
    assert call.key == api_key_of(TENANT_KEY)
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


def test_a_call_failing_at_every_attempt_fails_with_the_last_error(world: World) -> None:
    world.register("openrouter", TENANT_KEY)
    world.model.first_failures = [ModelUnavailableError(OPENROUTER, "503"), ModelUnavailableError(OPENROUTER, "429")]
    world.model.failure = ModelUnavailableError(OPENROUTER, "502 Provider returned error")

    with pytest.raises(ModelUnavailableError, match="502 Provider returned error") as raised:
        world.ask()

    assert raised.value.__cause__ is world.model.failure
    assert len(world.model.calls) == 3


# ADR-ritentativo-del-modello-nel-ciclo: a temporary error is asked again in the same cycle, after 5 and 15 seconds.
def test_a_temporary_error_is_asked_again_after_a_growing_pause(world: World) -> None:
    world.register("openrouter", TENANT_KEY)
    world.model.failure = ModelUnavailableError(OPENROUTER, "tempo di risposta scaduto", sent=True)

    with pytest.raises(ModelUnavailableError):
        world.ask()

    assert world.pause.pauses == [5.0, 15.0]
    assert [call.messages for call in world.model.calls] == [CONTEXT.messages()] * 3


def test_a_temporary_error_then_an_answer_gives_the_answer_with_the_cost_of_both_calls(world: World) -> None:
    world.register("openrouter", TENANT_KEY)
    failed = ModelUsage(100, 0, Decimal("0.0001"))
    world.model.first_failures = [ModelUnavailableError(OPENROUTER, "502", usage=failed, sent=True)]
    world.model.usage = ModelUsage(2000, 500, Decimal("0.0031"))

    answer = world.use_case.execute(AskAgentCommand("openrouter/deepseek-chat", {}, CONTEXT))

    assert [decision.asset for decision in answer.response.decisions] == ["BTC"]
    assert (answer.usage, answer.cost_usd) == (ModelUsage(2100, 500, Decimal("0.0032")), Decimal("0.0032"))
    assert world.pause.pauses == [5.0]


def test_a_failed_call_priced_by_the_catalog_adds_its_cost_to_the_answer(world: World) -> None:
    world.register("anthropic", TENANT_KEY)
    failed = ModelUsage(1000, 0, None)
    world.model.first_failures = [ModelUnavailableError(ProviderName("anthropic"), "500", usage=failed, sent=True)]
    world.model.usage = ModelUsage(1000, 1000, None)

    answer = world.use_case.execute(AskAgentCommand(PRICED, {}, CONTEXT))

    assert answer.cost_usd == Decimal("0.004")


def test_a_failed_call_that_went_out_without_a_known_cost_leaves_the_cost_not_available(world: World) -> None:
    world.register("openrouter", TENANT_KEY)
    world.model.first_failures = [ModelUnavailableError(OPENROUTER, "tempo di risposta scaduto", sent=True)]
    world.model.usage = ModelUsage(2000, 500, Decimal("0.0031"))

    answer = world.use_case.execute(AskAgentCommand("openrouter/deepseek-chat", {}, CONTEXT))

    assert (answer.usage, answer.cost_usd) == (ModelUsage(2000, 500, Decimal("0.0031")), None)


def test_a_failed_call_that_never_went_out_costs_nothing(world: World) -> None:
    world.register("openrouter", TENANT_KEY)
    world.model.first_failures = [ModelUnavailableError(OPENROUTER, "ConnectError")]
    world.model.usage = ModelUsage(2000, 500, Decimal("0.0031"))

    answer = world.use_case.execute(AskAgentCommand("openrouter/deepseek-chat", {}, CONTEXT))

    assert answer.cost_usd == Decimal("0.0031")


def test_the_last_error_carries_the_usage_and_the_cost_of_every_attempt(world: World) -> None:
    world.register("openrouter", TENANT_KEY)
    usage = ModelUsage(100, 0, Decimal("0.0001"))
    world.model.first_failures = [ModelUnavailableError(OPENROUTER, "ConnectError")]
    world.model.failure = ModelUnavailableError(OPENROUTER, "502", usage=usage, sent=True)

    with pytest.raises(ModelUnavailableError) as raised:
        world.ask()

    assert (raised.value.usage, raised.value.sent) == (ModelUsage(200, 0, Decimal("0.0002")), True)
    assert raised.value.cost_usd == Decimal("0.0002")


def test_attempts_that_never_went_out_fail_without_a_cost(world: World) -> None:
    world.register("openrouter", TENANT_KEY)
    world.model.failure = ModelUnavailableError(OPENROUTER, "ConnectError")

    with pytest.raises(ModelUnavailableError) as raised:
        world.ask()

    assert (raised.value.usage, raised.value.sent, raised.value.cost_usd) == (None, False, None)


@pytest.mark.parametrize(
    "failure",
    [ModelKeyRejectedError(OPENROUTER), ModelCreditExhaustedError(OPENROUTER)],
    ids=["key rejected", "credit exhausted"],
)
def test_a_permanent_error_of_the_provider_is_never_asked_again(world: World, failure: AutotradingError) -> None:
    world.register("openrouter", TENANT_KEY)
    world.model.failure = failure

    with pytest.raises(type(failure)):
        world.ask()

    assert (len(world.model.calls), world.pause.pauses) == (1, [])


def test_an_unavailable_provider_made_permanent_by_its_cause_is_never_asked_again(world: World) -> None:
    world.register("openrouter", TENANT_KEY)
    world.model.failure = _caused_by_code(ModelUnavailableError(OPENROUTER, "401"), 401)

    with pytest.raises(ModelUnavailableError) as raised:
        world.ask()

    assert raised.value.__cause__ is world.model.failure
    assert (len(world.model.calls), world.pause.pauses) == (1, [])


# Owner decision (17/11/2026, "Riprova sempre"): an answer that arrived but cannot be read is asked again too.
def test_an_answer_that_arrived_unreadable_is_asked_again(world: World) -> None:
    world.register("openrouter", TENANT_KEY)
    usage = ModelUsage(3000, 4000, Decimal("0.002"))
    world.model.first_failures = [
        ModelUnavailableError(OPENROUTER, "risposta del fornitore inattesa", usage=usage, sent=True)
    ]

    answer = world.use_case.execute(AskAgentCommand("openrouter/deepseek-chat", {}, CONTEXT))

    assert (len(world.model.calls), world.pause.pauses) == (2, [5.0])
    assert answer.cost_usd == Decimal("0.002") + Decimal("0.001")


class ExternalRefusal(Exception):  # noqa: N818 - the error a library of the provider raises, not a project error
    def __init__(self, status_code: int) -> None:
        super().__init__(f"status {status_code}")
        self.status_code = status_code


def _caused_by_code(error: ModelUnavailableError, code: int) -> ModelUnavailableError:
    error.__cause__ = ExternalRefusal(code)
    return error


# ADR-uso-riportato-nell-errore-della-chiamata-al-modello: a paid call without a usable answer keeps usage and cost.
def test_a_call_without_a_usable_answer_fails_with_the_usage_and_the_cost_of_the_catalog(world: World) -> None:
    world.register("anthropic", TENANT_KEY)
    usage = ModelUsage(1000, 1000, None)
    world.model.failure = ModelUnavailableError(ProviderName("anthropic"), "inattesa", usage=usage, sent=True)

    with pytest.raises(ModelUnavailableError) as raised:
        world.ask(PRICED)

    every_attempt = ModelUsage(3000, 3000, None)
    assert (raised.value.usage, raised.value.sent, raised.value.cost_usd) == (every_attempt, True, Decimal("0.009"))
    assert raised.value.__cause__ is world.model.failure


def test_a_call_without_a_usable_answer_keeps_the_cost_the_provider_reported(world: World) -> None:
    world.register("openrouter", TENANT_KEY)
    usage = ModelUsage(3000, 4000, Decimal("0.002"))
    world.model.failure = ModelUnavailableError(OPENROUTER, "inattesa", usage=usage, sent=True)

    with pytest.raises(ModelUnavailableError) as raised:
        world.ask()

    assert raised.value.cost_usd == Decimal("0.006")


def test_an_unreadable_answer_keeps_the_usage_and_the_cost_of_the_call(world: World) -> None:
    world.register("openrouter", TENANT_KEY)
    world.model.text = "non è JSON"
    world.model.usage = ModelUsage(3000, 4000, Decimal("0.002"))

    answer = world.use_case.execute(AskAgentCommand("openrouter/deepseek-chat", {}, CONTEXT))

    assert answer.response.decisions == ()
    assert (answer.usage, answer.cost_usd) == (ModelUsage(3000, 4000, Decimal("0.002")), Decimal("0.002"))


@dataclass(frozen=True, slots=True)
class Question:
    """A question as a cycle of a flow asks it: the model of the flow and the data of the context."""

    model: str = "openrouter/deepseek-chat"
    settings: Mapping[str, Decimal | str] = field(default_factory=dict)
    system_prompt: str = CONTEXT.system_prompt
    assets: tuple[str, ...] = CONTEXT.assets
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
