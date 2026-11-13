from autotrading.application.flows.ports import ClockPort, SourceAsk, SourceCollectionPort, SourceRequest
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.source_data import SourceData


class ReadCycleSourceUseCase:
    """The data of an active source of the flow for its cycle, each value with the weight of the source (R1.3.2)."""

    def __init__(self, collection: SourceCollectionPort, clock: ClockPort) -> None:
        self._collection = collection
        self._clock = clock

    def execute(self, request: SourceRequest[CycleFlow], source: str) -> tuple[SourceData, ...]:
        configuration = request.snapshot.state.configuration
        selection = configuration.source(source)
        ask = SourceAsk(
            request.flow_id,
            request.planned_at,
            selection.name,
            selection.weight,
            selection.parameters,
            configuration.assets,
            configuration.cycle_interval.minutes,
            self._clock.now(),
        )
        collected = self._collection.execute(ask)
        return tuple(
            SourceData(collected.source, collected.weight, asset, values) for asset, values in collected.entries
        )
