"""The catalog the worker hands to the API: the models of the gateways it holds, joined (ADR 0149)."""

import pytest

from autotrading.application.agent.errors import ModelCatalogUnavailableError
from autotrading.application.agent.read_model_catalog import ReadModelCatalogUseCase
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import ModelDefinition
from tests.fakes.model_catalog import InMemoryModelCatalogAdapter

CLAUDE = ModelDefinition("anthropic/claude-test", ())
GPT = ModelDefinition("openai/gpt-test", ())


def test_the_catalog_holds_the_models_of_every_gateway_of_the_worker() -> None:
    catalogs = {
        "first": InMemoryModelCatalogAdapter(ModelCatalog((CLAUDE,))),
        "second": InMemoryModelCatalogAdapter(ModelCatalog((GPT,))),
    }

    assert ReadModelCatalogUseCase(catalogs).execute().models == (CLAUDE, GPT)


def test_an_unavailable_catalog_is_told() -> None:
    use_case = ReadModelCatalogUseCase({"first": InMemoryModelCatalogAdapter(ModelCatalog(()), available=False)})

    with pytest.raises(ModelCatalogUnavailableError):
        use_case.execute()
