from autotrading.application.flows.ports import ClockPort, SourceAsk, SourceCollectionPort, SourceRequest
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.selections import ActiveSource
from autotrading.domain.flows.source_data import SourceData


class ReadCycleSourceUseCase:
    """The data of an adapter of an active source of the flow for its cycle, each value with the weight of the adapter
    (R1.3.2, R4.1.1).
    """

    def __init__(self, collection: SourceCollectionPort, clock: ClockPort) -> None:
        self._collection = collection
        self._clock = clock

    def execute(self, request: SourceRequest[CycleFlow], source: ActiveSource) -> tuple[SourceData, ...]:
        configuration = request.snapshot.state.configuration
        selection = configuration.source(source.source).adapter(source.adapter)
        ask = SourceAsk(
            request.flow_id,
            request.planned_at,
            source.source,
            selection.name,
            selection.weight,
            selection.parameters,
            configuration.assets,
            configuration.cycle_interval.minutes,
            self._clock.now(),
        )
        collected = self._collection.execute(ask)
        return tuple(
            SourceData(collected.source, collected.adapter, collected.weight, asset, values)
            for asset, values in collected.entries
        )
