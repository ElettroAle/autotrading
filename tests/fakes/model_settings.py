"""Fake of the model settings: the models it knows, with their resolved parameters, or the reason of a refusal."""

from collections.abc import Mapping
from decimal import Decimal

from autotrading.application.flows.errors import InvalidFlowSettingError
from autotrading.domain.flows.selections import ModelSelection


class FakeModelSettingsAdapter:
    def __init__(self, *models: str) -> None:
        self.models = set(models)
        self.asked: list[str] = []

    def selection(self, model: str, requested: Mapping[str, object]) -> ModelSelection:
        self.asked.append(model)
        if model not in self.models:
            reason = f"modello non disponibile: {model}"
            raise InvalidFlowSettingError(reason)
        return ModelSelection(
            model, {"temperature": Decimal(1), **{key: str(value) for key, value in requested.items()}}
        )
