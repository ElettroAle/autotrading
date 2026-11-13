from collections.abc import Mapping

from autotrading.application.flows.errors import FlowProviderKeyMissingError, InvalidFlowSettingError
from autotrading.application.flows.ports import FlowProviderKeysPort
from autotrading.domain.agent.errors import (
    ModelNotAvailableError,
    ParameterNotSupportedError,
    ParameterOutOfRangeError,
    UnknownParameterError,
)
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.flows.errors import ModelRequiredError
from autotrading.domain.flows.selections import ModelSelection


class SelectModelUseCase:
    """The model of a flow with its parameters resolved by the catalog of the platform (R1.4.1, R1.4.2, ADR 0031).

    A model is usable only with the parameters it admits and a registered key of its provider; a refusal reaches the
    flow with the reason the catalog gives.
    """

    def __init__(self, catalog: ModelCatalog, keys: FlowProviderKeysPort) -> None:
        self._catalog = catalog
        self._keys = keys

    def execute(self, model: str, requested: Mapping[str, object]) -> ModelSelection:
        if not model.strip():
            raise ModelRequiredError
        try:
            definition = self._catalog.find(model)
            parameters = definition.settings(requested)
        except (
            ModelNotAvailableError,
            ParameterOutOfRangeError,
            ParameterNotSupportedError,
            UnknownParameterError,
        ) as error:
            raise InvalidFlowSettingError(str(error)) from error
        if not self._keys.has_key(definition.provider):
            raise FlowProviderKeyMissingError(definition.provider.value)
        return ModelSelection(definition.name, parameters)
