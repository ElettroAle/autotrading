from collections.abc import Sequence

from autotrading.application.flows.errors import InvalidFlowSettingError
from autotrading.application.flows.ports import AdapterRequest, SourceCatalogPort
from autotrading.domain.flows.flow_setting import FlowSetting
from autotrading.domain.flows.selections import DEFAULT_WEIGHT, AdapterSelection, SourceSelection
from autotrading.domain.sources.errors import (
    SourceAdapterNotAvailableError,
    SourceNotAvailableError,
    SourceParameterOutOfRangeError,
    UnknownSourceParameterError,
)
from autotrading.domain.sources.source_catalog import OfferedSource


class SelectSourceUseCase:
    """A source of the flow with the adapters chosen, their parameters checked by the catalog of the platform (R1.3.1,
    R4.1.1, ADR 0031).
    """

    def __init__(self, sources: SourceCatalogPort) -> None:
        self._sources = sources

    def execute(self, source: str, adapters: Sequence[AdapterRequest]) -> SourceSelection:
        try:
            offered = self._sources.execute().find(source)
            selected = tuple(_selected(offered, adapter) for adapter in adapters)
        except (
            SourceNotAvailableError,
            SourceAdapterNotAvailableError,
            SourceParameterOutOfRangeError,
            UnknownSourceParameterError,
        ) as error:
            raise InvalidFlowSettingError(str(error), FlowSetting.SOURCES) from error
        return SourceSelection(source, selected)


def _selected(offered: OfferedSource, adapter: AdapterRequest) -> AdapterSelection:
    return AdapterSelection(
        adapter.name, _weight_or_default(adapter.weight), offered.settings(adapter.name, adapter.parameters)
    )


def _weight_or_default(requested: int | None) -> int:
    return DEFAULT_WEIGHT if requested is None else requested
