"""The gateway that serves the model of a flow, and the catalog of all the gateways (ADR 0109)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from autotrading.application.agent.ask_agent import AskAgentCommand, AskAgentUseCase
from autotrading.application.agent.errors import ModelCatalogUnavailableError
from autotrading.application.agent.list_models import ListModelsUseCase
from autotrading.domain.agent.agent_context import AgentContext, FlowStateView
from autotrading.domain.agent.errors import ModelNotAvailableError
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.model_call import FakeModelCallAdapter
from tests.fakes.model_catalog import InMemoryModelCatalogAdapter
from tests.fakes.model_gateway import FakeModelGatewayAdapter
from tests.fakes.provider_keys import (
    FakeProviderKeyOpenerAdapter,
    FakeProviderKeySealerAdapter,
    InMemoryProviderKeyRepositoryAdapter,
    ProviderKeyStore,
    ProviderKeyVault,
)

TENANT = TenantId.new()
NOW = datetime(2026, 11, 13, 10, 30, tzinfo=UTC)
CONTEXT = AgentContext(
    instructions="Sei un trader prudente",
    assets=("BTC",),
    max_leverage=5,
    started_at=NOW,
    now=NOW,
    state=FlowStateView("USDC", Decimal(400), Decimal(400), Decimal(400), Decimal(400), Decimal(0), ()),
    sources=(),
    missing=(),
)
PROXY_MODEL = "anthropic/claude-test"
DIRECT_MODEL = "openrouter/deepseek-chat"


class Gateways:
    def __init__(self, *, direct_available: bool = True) -> None:
        self.proxy = FakeModelGatewayAdapter(
            InMemoryModelCatalogAdapter(ModelCatalog((ModelDefinition(PROXY_MODEL, ()),))), FakeModelCallAdapter()
        )
        self.direct = FakeModelGatewayAdapter(
            InMemoryModelCatalogAdapter(ModelCatalog((ModelDefinition(DIRECT_MODEL, ()),)), available=direct_available),
            FakeModelCallAdapter(),
        )
        self.vault: ProviderKeyVault = {}
        self.keys = InMemoryProviderKeyRepositoryAdapter(ProviderKeyStore(), TENANT)
        for provider in ("anthropic", "openrouter"):
            name = ProviderName(provider)
            sealed = FakeProviderKeySealerAdapter(TENANT, self.vault).seal(name, ProviderKey(f"K-{provider}"))
            self.keys.add(RegisteredProviderKey(TENANT, name, sealed))

    def ask(self, model: str) -> None:
        use_case = AskAgentUseCase(
            {"proxy": self.proxy, "direct": self.direct}, self.keys, FakeProviderKeyOpenerAdapter(self.vault)
        )
        use_case.execute(AskAgentCommand(model, {}, CONTEXT))

    def listing(self) -> list[str]:
        use_case = ListModelsUseCase({"proxy": self.proxy, "direct": self.direct}, self.keys)
        return [model.name for model in use_case.execute().models]


@pytest.mark.parametrize(("model", "caller"), [(PROXY_MODEL, "proxy"), (DIRECT_MODEL, "direct")])
def test_the_gateway_whose_catalog_holds_the_model_of_the_flow_calls_it(model: str, caller: str) -> None:
    gateways = Gateways()

    gateways.ask(model)

    called = gateways.proxy if caller == "proxy" else gateways.direct
    other = gateways.direct if caller == "proxy" else gateways.proxy
    assert [call.model for call in called.call.calls] == [model]
    assert other.call.calls == []


def test_a_gateway_with_its_catalog_unavailable_does_not_stop_the_models_of_the_others() -> None:
    gateways = Gateways(direct_available=False)

    gateways.ask(PROXY_MODEL)

    assert [call.model for call in gateways.proxy.call.calls] == [PROXY_MODEL]


def test_a_model_of_an_unavailable_catalog_is_an_unavailable_catalog() -> None:
    with pytest.raises(ModelCatalogUnavailableError):
        Gateways(direct_available=False).ask(DIRECT_MODEL)


def test_a_model_no_gateway_offers_is_not_available() -> None:
    with pytest.raises(ModelNotAvailableError):
        Gateways().ask("openai/inesistente")


def test_the_user_sees_the_models_of_every_gateway() -> None:
    assert Gateways().listing() == [PROXY_MODEL, DIRECT_MODEL]


def test_the_catalog_of_the_user_needs_every_gateway() -> None:
    with pytest.raises(ModelCatalogUnavailableError):
        Gateways(direct_available=False).listing()
