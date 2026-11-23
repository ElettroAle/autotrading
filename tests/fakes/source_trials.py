from collections.abc import Callable, Mapping

from autotrading.application.sources.errors import SourceTrialWorkerUnavailableError
from autotrading.application.sources.try_source_adapter import TrySourceAdapterCommand
from autotrading.domain.sources.source_parameter import SourceParameterValue
from autotrading.domain.sources.source_trial import SourceTrial


class FakeSourceTrialAdapter:
    """The worker reached in process instead of over HTTP: the trial it runs now, for the same tenant (R6.3.1)."""

    def __init__(self, worker: Callable[[TrySourceAdapterCommand], SourceTrial]) -> None:
        self._worker = worker
        self.reachable = True
        self.asked: list[TrySourceAdapterCommand] = []

    def try_adapter(
        self, source: str, adapter: str, asset: str | None, parameters: Mapping[str, SourceParameterValue]
    ) -> SourceTrial:
        command = TrySourceAdapterCommand(source, adapter, asset, dict(parameters))
        self.asked.append(command)
        if not self.reachable:
            raise SourceTrialWorkerUnavailableError
        return self._worker(command)
