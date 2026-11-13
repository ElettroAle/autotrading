import json
from decimal import Decimal
from importlib.resources import files
from typing import NotRequired, TypedDict, cast

from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.model_parameter import ChoiceParameter, ModelParameter, RangeParameter
from autotrading.domain.agent.model_usage import ModelPrices
from autotrading.domain.errors import AutotradingError

PACKAGED_CATALOG = "models.json"


class _ChoiceDeclaration(TypedDict):
    choices: list[str]
    default: str


class _RangeDeclaration(TypedDict):
    minimum: Decimal
    maximum: Decimal
    default: Decimal
    whole: NotRequired[bool]


class _PricesDeclaration(TypedDict):
    input_per_million: Decimal
    output_per_million: Decimal


class _ModelEntry(TypedDict):
    name: str
    parameters: dict[str, _ChoiceDeclaration | _RangeDeclaration]
    prices: NotRequired[_PricesDeclaration | None]


class _CatalogDocument(TypedDict):
    """The catalog as written in JSON; a wrong shape fails while it is read."""

    models: list[_ModelEntry]


class InvalidModelCatalogError(AutotradingError):
    """The configuration of the models cannot be read: the platform does not start with it (ADR 0030)."""

    status_code = 500

    def __init__(self, detail: str) -> None:
        super().__init__(f"catalogo dei modelli non valido: {detail}")
        self.detail = detail


def load_model_catalog(text: str | None = None) -> ModelCatalog:
    """The catalog written in the JSON text, by default the one shipped with the platform."""
    document = _document(_packaged_text() if text is None else text)
    try:
        return ModelCatalog(_model_of(entry) for entry in document["models"])
    except (KeyError, TypeError, AttributeError) as error:
        detail = f"campo mancante o di tipo errato: {error}"
        raise InvalidModelCatalogError(detail) from error


def _packaged_text() -> str:
    return files(__package__).joinpath(PACKAGED_CATALOG).read_text(encoding="utf-8")


def _document(text: str) -> _CatalogDocument:
    try:
        document = json.loads(text, parse_float=Decimal, parse_int=Decimal)
    except json.JSONDecodeError as error:
        raise InvalidModelCatalogError(str(error)) from error
    if not isinstance(document, dict):
        detail = "serve un oggetto con l'elenco models"
        raise InvalidModelCatalogError(detail)
    return cast("_CatalogDocument", document)


def _model_of(entry: _ModelEntry) -> ModelDefinition:
    parameters = tuple(_parameter_of(key, declaration) for key, declaration in entry["parameters"].items())
    return ModelDefinition(entry["name"], parameters, _prices_of(entry.get("prices")))


def _prices_of(declaration: _PricesDeclaration | None) -> ModelPrices | None:
    if declaration is None:
        return None
    return ModelPrices(declaration["input_per_million"], declaration["output_per_million"])


def _parameter_of(key: str, declaration: _ChoiceDeclaration | _RangeDeclaration) -> ModelParameter:
    if "choices" in declaration:
        choice = cast("_ChoiceDeclaration", declaration)
        return ChoiceParameter(key, tuple(choice["choices"]), choice["default"])
    return RangeParameter(
        key,
        minimum=declaration["minimum"],
        maximum=declaration["maximum"],
        default=declaration["default"],
        whole=bool(declaration.get("whole", False)),
    )
