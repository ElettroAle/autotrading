from collections.abc import Mapping

from autotrading.application.flows.errors import (
    FlowModelCatalogUnavailableError,
    FlowProviderKeyMissingError,
    InvalidFlowSettingError,
)
from autotrading.application.flows.ports import FlowModelsPort, FlowProviderKeysPort
from autotrading.domain.agent.errors import (
    ModelNotAvailableError,
    ParameterNotSupportedError,
    ParameterOutOfRangeError,
    UnknownParameterError,
)
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.flows.errors import ModelRequiredError
from autotrading.domain.flows.flow_setting import FlowSetting
from autotrading.domain.flows.selections import ModelSelection


class SelectModelUseCase:
    """The model of a flow with its parameters resolved by the catalog of the platform (R1.4.1, R1.4.2, ADR 0031).

    A model is usable only with the parameters it admits and a registered key of its provider; a refusal reaches the
    flow with the reason the catalog gives.
    """

    def __init__(self, models: Mapping[str, FlowModelsPort], keys: FlowProviderKeysPort) -> None:
        self._models = models
        self._keys = keys

    def execute(self, model: str, requested: Mapping[str, object]) -> ModelSelection:
        if not model.strip():
            raise ModelRequiredError
        try:
            definition = self._definition_of(model)
        except ModelNotAvailableError as error:
            raise InvalidFlowSettingError(str(error), FlowSetting.MODEL) from error
        try:
            parameters = definition.settings(requested)
        except (ParameterOutOfRangeError, ParameterNotSupportedError, UnknownParameterError) as error:
            raise InvalidFlowSettingError(str(error), FlowSetting.MODEL_PARAMETERS) from error
        if not self._keys.has_key(definition.provider):
            raise FlowProviderKeyMissingError(definition.provider.value)
        return ModelSelection(definition.name, parameters)

    def _definition_of(self, model: str) -> ModelDefinition:
        """The model as the gateway that offers it describes it; an unavailable catalog does not hide the others."""
        unavailable: FlowModelCatalogUnavailableError | None = None
        for models in self._models.values():
            try:
                return models.definition_of(model)
            except ModelNotAvailableError:
                continue
            except FlowModelCatalogUnavailableError as error:
                unavailable = error
        if unavailable is not None:
            raise unavailable
        raise ModelNotAvailableError(model)
