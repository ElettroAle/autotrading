"""The model of a flow resolved by the catalog, with a key of its provider (R1.4.1, R1.4.2, ADR 0031)."""

from decimal import Decimal

import pytest

from autotrading.application.agent.register_provider_key import RegisterProviderKeyCommand
from autotrading.application.flows.errors import FlowModelCatalogUnavailableError, InvalidFlowSettingError
from autotrading.application.flows.select_model import SelectModelUseCase
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.model_parameter import ChoiceParameter
from autotrading.domain.flows.errors import ModelRequiredError
from tests.fakes.model_catalog import InMemoryModelCatalogAdapter
from tests.fakes.provider_keys import InMemoryProviderKeyRepositoryAdapter
from tests.support.flows import TEMPERATURE
from tests.support.platform import Platform

REASONING = ChoiceParameter("reasoning_effort", ("basso", "alto"), "basso")
CATALOG = ModelCatalog(
    (
        ModelDefinition("openrouter/deepseek-chat", (TEMPERATURE,)),
        ModelDefinition("anthropic/claude-sonnet", (TEMPERATURE, REASONING)),
    )
)


class Models:
    def __init__(self) -> None:
        self.platform = Platform()
        self.tenant_id = self.platform.tenant_of("anna")
        self.keys = InMemoryProviderKeyRepositoryAdapter(self.platform.provider_keys, self.tenant_id)
        self.use_case = SelectModelUseCase({"models": InMemoryModelCatalogAdapter(CATALOG)}, self.keys)

    def register(self, provider: str) -> None:
        self.platform.use_cases_of("anna").register_provider_key.execute(RegisterProviderKeyCommand(provider, "K-TEST"))


def test_a_model_with_the_key_of_its_provider_gets_its_parameters_with_the_defaults() -> None:
    models = Models()
    models.register("anthropic")

    selection = models.use_case.execute("anthropic/claude-sonnet", {"temperature": "0.5"})

    assert (selection.name, dict(selection.parameters)) == (
        "anthropic/claude-sonnet",
        {"temperature": Decimal("0.5"), "reasoning_effort": "basso"},
    )


def test_a_model_is_required() -> None:
    with pytest.raises(ModelRequiredError):
        Models().use_case.execute("  ", {})


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
        models.use_case.execute(model, requested)

    assert str(raised.value) == reason


def test_a_model_of_a_provider_without_key_is_refused() -> None:
    models = Models()
    models.register("openrouter")

    with pytest.raises(InvalidFlowSettingError, match=r"^nessuna chiave registrata per il fornitore: anthropic$"):
        models.use_case.execute("anthropic/claude-sonnet", {})


def two_gateways(*, second_available: bool) -> SelectModelUseCase:
    models = Models()
    models.register("anthropic")
    models.register("openrouter")
    first = InMemoryModelCatalogAdapter(ModelCatalog((CATALOG.find("anthropic/claude-sonnet"),)))
    second = InMemoryModelCatalogAdapter(
        ModelCatalog((CATALOG.find("openrouter/deepseek-chat"),)), available=second_available
    )
    return SelectModelUseCase({"first": first, "second": second}, models.keys)


def test_the_model_is_found_in_the_catalog_of_the_gateway_that_offers_it() -> None:
    selection = two_gateways(second_available=True).execute("openrouter/deepseek-chat", {})

    assert selection.name == "openrouter/deepseek-chat"


def test_an_unavailable_catalog_does_not_hide_the_models_of_the_others() -> None:
    selection = two_gateways(second_available=False).execute("anthropic/claude-sonnet", {})

    assert selection.name == "anthropic/claude-sonnet"


def test_a_model_only_an_unavailable_catalog_could_offer_is_an_unavailable_catalog() -> None:
    with pytest.raises(FlowModelCatalogUnavailableError):
        two_gateways(second_available=False).execute("openrouter/deepseek-chat", {})


def test_a_model_no_catalog_offers_is_not_available() -> None:
    with pytest.raises(InvalidFlowSettingError, match=r"^modello non disponibile: openai/x$"):
        two_gateways(second_available=True).execute("openai/x", {})
