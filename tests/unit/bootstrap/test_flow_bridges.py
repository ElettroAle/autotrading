"""The bridges bootstrap builds between the flows context and the accounts, agent and sources contexts (ADR 0031)."""

from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.agent.register_provider_key import RegisterProviderKeyCommand
from autotrading.application.flows.errors import (
    FlowAccountNotFoundError,
    FlowExchangeUnavailableError,
    InvalidFlowSettingError,
)
from autotrading.application.flows.ports import FlowAccount
from autotrading.bootstrap import (
    SOURCE_CATALOG,
    FlowAccountsFromAccounts,
    ModelSettingsFromAgent,
    ProviderKeyUsageFromFlows,
    SourceSettingsFromSources,
)
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.model_parameter import ChoiceParameter
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.flows.errors import ModelRequiredError
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.selections import SourceSelection
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import InMemoryAccountRepositoryAdapter
from tests.fakes.account_state import FakeAccountStateAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.provider_keys import InMemoryProviderKeyRepositoryAdapter
from tests.support.flows import TEMPERATURE, a_configuration, a_flow, account_id_of
from tests.support.platform import Platform

REASONING = ChoiceParameter("reasoning_effort", ("basso", "alto"), "basso")
CATALOG = ModelCatalog(
    (
        ModelDefinition("openrouter/deepseek-chat", (TEMPERATURE,)),
        ModelDefinition("anthropic/claude-sonnet", (TEMPERATURE, REASONING)),
    )
)


def test_a_key_is_used_only_by_flows_active_or_paused_on_a_model_of_its_provider() -> None:
    tenant_id, store = TenantId.new(), FlowStore()
    anthropic = a_configuration(model="anthropic/claude-sonnet")
    store.flows += [
        a_flow(tenant_id, name="beta", status=FlowStatus.PAUSED),
        a_flow(tenant_id, name="alfa", status=FlowStatus.ACTIVE),
        a_flow(tenant_id, name="fermo", status=FlowStatus.STOPPED),
        a_flow(tenant_id, name="archiviato", status=FlowStatus.ARCHIVED),
        a_flow(tenant_id, name="altro", status=FlowStatus.ACTIVE, configuration=anthropic),
        a_flow(TenantId.new(), name="estraneo", status=FlowStatus.ACTIVE),
    ]
    usage = ProviderKeyUsageFromFlows(InMemoryFlowRepositoryAdapter(store, tenant_id))

    assert usage.flows_using(ProviderName("openrouter")) == ["beta", "alfa"]
    assert usage.flows_using(ProviderName("openai")) == []


class Accounts:
    def __init__(self) -> None:
        self.platform = Platform()
        self.tenant_id = self.platform.tenant_of("anna")
        self.state = FakeAccountStateAdapter(lambda: self.platform.worker_for(self.tenant_id).read_exchange_state)
        repository = InMemoryAccountRepositoryAdapter(self.platform.accounts, self.tenant_id)
        self.bridge = FlowAccountsFromAccounts(repository, self.state)


def test_the_account_of_a_flow_carries_its_exchange_and_the_balance_read_now() -> None:
    accounts = Accounts()
    account_id = account_id_of(accounts.platform, "anna", balance=Decimal("750.25"))

    assert accounts.bridge.account(account_id) == FlowAccount("Hyperliquid", Decimal("750.25"), "USDC")


def test_an_account_the_tenant_does_not_have_is_not_found() -> None:
    accounts = Accounts()
    other = account_id_of(accounts.platform, "bruno")

    for account_id in (uuid4(), other):
        with pytest.raises(FlowAccountNotFoundError, match=r"^conto non trovato$"):
            accounts.bridge.account(account_id)


def test_a_balance_that_cannot_be_read_makes_the_exchange_unavailable() -> None:
    accounts = Accounts()
    account_id = account_id_of(accounts.platform, "anna")
    accounts.state.reachable = False

    with pytest.raises(FlowExchangeUnavailableError):
        accounts.bridge.account(account_id)


class Models:
    def __init__(self) -> None:
        self.platform = Platform()
        self.tenant_id = self.platform.tenant_of("anna")
        self.keys = InMemoryProviderKeyRepositoryAdapter(self.platform.provider_keys, self.tenant_id)
        self.bridge = ModelSettingsFromAgent(CATALOG, self.keys)

    def register(self, provider: str) -> None:
        self.platform.providers.accept(provider, "K-TEST")
        self.platform.use_cases_of("anna").register_provider_key.execute(RegisterProviderKeyCommand(provider, "K-TEST"))


def test_a_model_with_the_key_of_its_provider_gets_its_parameters_with_the_defaults() -> None:
    models = Models()
    models.register("anthropic")

    selection = models.bridge.selection("anthropic/claude-sonnet", {"temperature": "0.5"})

    assert (selection.name, dict(selection.parameters)) == (
        "anthropic/claude-sonnet",
        {"temperature": Decimal("0.5"), "reasoning_effort": "basso"},
    )


def test_a_model_is_required() -> None:
    with pytest.raises(ModelRequiredError):
        Models().bridge.selection("  ", {})


@pytest.mark.parametrize(
    ("model", "requested", "reason"),
    [
        ("openai/inesistente", {}, "modello non disponibile: openai/inesistente"),
        ("openrouter/deepseek-chat", {"temperature": 3}, "parametro fuori dai valori ammessi: temperatura"),
        (
            "openrouter/deepseek-chat",
            {"reasoning_effort": "alto"},
            "parametro non supportato dal modello: livello di ragionamento",
        ),
        ("openrouter/deepseek-chat", {"top_p": 1}, "parametro sconosciuto: top_p"),
    ],
)
def test_a_model_or_parameter_the_agent_refuses_reaches_the_flow_with_the_reason(
    model: str, requested: dict[str, object], reason: str
) -> None:
    models = Models()
    models.register("openrouter")

    with pytest.raises(InvalidFlowSettingError) as raised:
        models.bridge.selection(model, requested)

    assert str(raised.value) == reason


def test_a_model_of_a_provider_without_key_is_refused() -> None:
    models = Models()
    models.register("openrouter")

    with pytest.raises(InvalidFlowSettingError, match=r"^nessuna chiave registrata per il fornitore: anthropic$"):
        models.bridge.selection("anthropic/claude-sonnet", {})


def test_a_source_gets_its_weight_and_its_parameters_with_the_defaults() -> None:
    sources = SourceSettingsFromSources(SOURCE_CATALOG)
    news = SOURCE_CATALOG.find("notizie")
    first = news.parameters[0]

    assert sources.selection("notizie", None, {}) == SourceSelection("notizie", 5, news.settings({}))
    assert sources.selection("notizie", 8, {first.key: first.minimum}).parameters[first.key] == first.minimum


@pytest.mark.parametrize(
    ("source", "requested", "reason"),
    [
        ("oroscopo", {}, "fonte non disponibile: oroscopo"),
        ("notizie", {"lingua": 1}, "parametro sconosciuto della fonte notizie: lingua"),
    ],
)
def test_a_source_or_parameter_the_catalog_refuses_reaches_the_flow_with_the_reason(
    source: str, requested: dict[str, int], reason: str
) -> None:
    with pytest.raises(InvalidFlowSettingError) as raised:
        SourceSettingsFromSources(SOURCE_CATALOG).selection(source, None, requested)

    assert str(raised.value) == reason


def test_a_source_parameter_out_of_range_reaches_the_flow_with_its_label() -> None:
    first = SOURCE_CATALOG.find("notizie").parameters[0]

    with pytest.raises(InvalidFlowSettingError, match=r"^parametro fuori dai valori ammessi: "):
        SourceSettingsFromSources(SOURCE_CATALOG).selection("notizie", None, {first.key: first.maximum + 1})
