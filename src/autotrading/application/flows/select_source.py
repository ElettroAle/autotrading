from collections.abc import Mapping

from autotrading.application.flows.errors import InvalidFlowSettingError
from autotrading.domain.flows.selections import DEFAULT_WEIGHT, SourceSelection
from autotrading.domain.sources.errors import (
    SourceNotAvailableError,
    SourceParameterOutOfRangeError,
    UnknownSourceParameterError,
)
from autotrading.domain.sources.source_catalog import SourceCatalog


class SelectSourceUseCase:
    """A source of the flow with its parameters checked by the catalog of the platform (R1.3.1, ADR 0031)."""

    def __init__(self, catalog: SourceCatalog) -> None:
        self._catalog = catalog

    def execute(self, source: str, weight: int | None, requested: Mapping[str, int]) -> SourceSelection:
        try:
            parameters = self._catalog.find(source).settings(requested)
        except (SourceNotAvailableError, SourceParameterOutOfRangeError, UnknownSourceParameterError) as error:
            raise InvalidFlowSettingError(str(error)) from error
        return SourceSelection(source, DEFAULT_WEIGHT if weight is None else weight, parameters)
