from typing import Literal

from pydantic import BaseModel

from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.model_parameter import ChoiceParameter, ModelParameter
from autotrading.domain.agent.model_usage import ModelPrices


class WorkerModelParameterResponse(BaseModel):
    """A range has minimum, maximum and whether it is whole; a choice its values. Numbers travel as text."""

    key: str
    kind: Literal["range", "choice"]
    default: str
    minimum: str | None = None
    maximum: str | None = None
    whole: bool = False
    choices: list[str] | None = None

    @classmethod
    def of(cls, parameter: ModelParameter) -> WorkerModelParameterResponse:
        if isinstance(parameter, ChoiceParameter):
            return cls(key=parameter.key, kind="choice", default=parameter.default, choices=list(parameter.choices))
        return cls(
            key=parameter.key,
            kind="range",
            default=str(parameter.default),
            minimum=str(parameter.minimum),
            maximum=str(parameter.maximum),
            whole=parameter.whole,
        )


class WorkerModelPricesResponse(BaseModel):
    input_per_million: str
    output_per_million: str

    @classmethod
    def of(cls, prices: ModelPrices) -> WorkerModelPricesResponse:
        return cls(input_per_million=str(prices.input_per_million), output_per_million=str(prices.output_per_million))


class WorkerModelResponse(BaseModel):
    name: str
    parameters: list[WorkerModelParameterResponse]
    prices: WorkerModelPricesResponse | None

    @classmethod
    def of(cls, model: ModelDefinition) -> WorkerModelResponse:
        return cls(
            name=model.name,
            parameters=[WorkerModelParameterResponse.of(parameter) for parameter in model.parameters],
            prices=None if model.prices is None else WorkerModelPricesResponse.of(model.prices),
        )


class WorkerModelCatalogResponse(BaseModel):
    """The catalog of the gateways of the worker as the API rebuilds it, prices included (ADR 0149)."""

    models: list[WorkerModelResponse]

    @classmethod
    def of(cls, catalog: ModelCatalog) -> WorkerModelCatalogResponse:
        return cls(models=[WorkerModelResponse.of(model) for model in catalog.models])
