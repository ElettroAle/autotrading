from collections.abc import Sequence
from uuid import UUID

from autotrading.application.flows.ports import (
    AgentActionsPort,
    AgentPromptComposerPort,
    ClockPort,
    CycleContext,
    FlowSnapshot,
    SourceAggregatesPort,
    SourceReading,
)
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_question import CycleQuestion
from autotrading.domain.flows.cycle_record import AbsentSource
from autotrading.domain.flows.source_data import SourceData


class ComposeCycleContextUseCase:
    """The context of the agent for a cycle: the flow alone, the data of its sources followed by what several adapters
    of a source say together, and the data missing, declared (R1.2.5, R1.4.3, R5.1.2).
    """

    def __init__(
        self,
        composer: AgentPromptComposerPort,
        actions: AgentActionsPort,
        aggregates: SourceAggregatesPort,
        clock: ClockPort,
    ) -> None:
        self._composer = composer
        self._actions = actions
        self._aggregates = aggregates
        self._clock = clock

    def execute(
        self,
        flow_id: UUID,  # noqa: ARG002 - the signature of the port
        snapshot: FlowSnapshot[CycleFlow],
        readings: Sequence[SourceReading[tuple[SourceData, ...]]],
        absent: Sequence[AbsentSource],
    ) -> CycleContext:
        cycle_flow = snapshot.state
        data = tuple(data for reading in readings for data in reading.data)
        configuration = cycle_flow.configuration
        question = CycleQuestion(
            model=configuration.model.name,
            settings=configuration.model.parameters,
            system_prompt=configuration.rendered_system_prompt(tuple(self._actions.execute())),
            assets=configuration.assets,
            started_at=cycle_flow.started_at,
            now=self._clock.now(),
            state=cycle_flow.state_view(),
            sources=(*data, *self._aggregated(data)),
            missing=tuple(f"{source.label}: {source.reason}" for source in absent),
        )
        return CycleContext(cycle_flow, question, self._composer.execute(question))

    def _aggregated(self, data: tuple[SourceData, ...]) -> tuple[SourceData, ...]:
        return tuple(
            SourceData(aggregate.source, aggregate.adapter, None, aggregate.asset, aggregate.values)
            for aggregate in self._aggregates.execute(data)
        )
