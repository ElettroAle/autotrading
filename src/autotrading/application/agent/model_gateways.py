"""Steps shared by the use cases that work with the model gateways (ADR 0109)."""

from collections.abc import Mapping

from autotrading.application.agent.errors import ModelCatalogUnavailableError
from autotrading.application.agent.ports import ModelGatewayPort
from autotrading.domain.agent.errors import ModelNotAvailableError
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import ModelDefinition

type ModelGateways = Mapping[str, ModelGatewayPort]


def joined_catalog(gateways: ModelGateways) -> ModelCatalog:
    """The models of every gateway, as the user sees them (R1.4.2)."""
    return ModelCatalog.joined(gateway.model_catalog().catalog() for gateway in gateways.values())


def gateway_of(gateways: ModelGateways, model: str) -> tuple[ModelDefinition, ModelGatewayPort]:
    """The gateway whose catalog holds the model the flow chose, with its definition.

    A gateway whose catalog is unavailable does not stop the models of the others; it is the reason only when no
    other gateway offers the model.
    """
    unavailable: ModelCatalogUnavailableError | None = None
    for gateway in gateways.values():
        try:
            return gateway.model_catalog().catalog().find(model), gateway
        except ModelNotAvailableError:
            continue
        except ModelCatalogUnavailableError as error:
            unavailable = error
    if unavailable is not None:
        raise unavailable
    raise ModelNotAvailableError(model)
