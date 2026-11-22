from collections.abc import Mapping
from dataclasses import dataclass, field

from autotrading.application.sources.list_sources import ListSourcesUseCase
from autotrading.application.sources.ports import SourceTrialPort
from autotrading.domain.sources.source_parameter import SourceParameterValue
from autotrading.domain.sources.source_trial import SourceTrial


@dataclass(frozen=True, slots=True)
class RequestSourceTrialCommand:
    source: str
    adapter: str
    # None for a source of the whole market.
    asset: str | None = None
    parameters: Mapping[str, SourceParameterValue] = field(default_factory=dict)


class RequestSourceTrialUseCase:
    """The trial of an adapter of a source the user asks for now, run by the worker, which alone opens the credentials
    of the adapters (R6.3.1, ADR prova-di-un-adapter-di-fonte-nel-worker).

    An unknown source or adapter, a parameter outside its values and a missing asset are refused before the worker is
    asked: the trial does not start.
    """

    def __init__(self, sources: ListSourcesUseCase, trials: SourceTrialPort) -> None:
        self._sources = sources
        self._trials = trials

    def execute(self, command: RequestSourceTrialCommand) -> SourceTrial:
        offered = self._sources.execute().find(command.source)
        offered.settings(command.adapter, command.parameters)
        asset = offered.asset_of_trial(command.asset)
        return self._trials.try_adapter(command.source, command.adapter, asset, command.parameters)
