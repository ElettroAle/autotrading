"""Fake of the source settings: the sources it knows, with their weight, or the reason of a refusal."""

from collections.abc import Mapping

from autotrading.application.flows.errors import InvalidFlowSettingError
from autotrading.domain.flows.selections import DEFAULT_WEIGHT, SourceSelection


class FakeSourceSettingsAdapter:
    def __init__(self, *sources: str) -> None:
        self.sources = set(sources)

    def execute(self, source: str, weight: int | None, requested: Mapping[str, int]) -> SourceSelection:
        if source not in self.sources:
            reason = f"fonte non disponibile: {source}"
            raise InvalidFlowSettingError(reason)
        return SourceSelection(source, DEFAULT_WEIGHT if weight is None else weight, dict(requested))
