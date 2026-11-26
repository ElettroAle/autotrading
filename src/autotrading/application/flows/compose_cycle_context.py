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
from autotrading.application.flows.remembered_decisions import MemoryReadings, remembered_decisions
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_question import CycleQuestion
from autotrading.domain.flows.cycle_record import AbsentSource
from autotrading.domain.flows.source_data import SourceData


class ComposeCycleContextUseCase:
    """The context of the agent for a cycle: the flow alone, the data of its sources followed by what several adapters
    of a source say together, and the data missing, declared (R1.2.5, R1.4.3, R5.1.2); with the memory of the flow
    on, its previous operative decisions before now with their outcome, in the placeholder of the system prompt
    (R5.3.4), after the summary of the positions the flow closed when the flow wants it (R5.3.7).
    """

    def __init__(
        self,
        composer: AgentPromptComposerPort,
        actions: AgentActionsPort,
        aggregates: SourceAggregatesPort,
        clock: ClockPort,
        memory: MemoryReadings,
    ) -> None:
        self._composer = composer
        self._actions = actions
        self._aggregates = aggregates
        self._clock = clock
        self._memory = memory

    def execute(
        self,
        flow_id: UUID,
        snapshot: FlowSnapshot[CycleFlow],
        readings: Sequence[SourceReading[tuple[SourceData, ...]]],
        absent: Sequence[AbsentSource],
    ) -> CycleContext:
        cycle_flow = snapshot.state
        data = tuple(data for reading in readings for data in reading.data)
        configuration = cycle_flow.configuration
        now = self._clock.now()
        memory = remembered_decisions(self._memory, flow_id, configuration, now, lambda: cycle_flow.account)
        question = CycleQuestion(
            model=configuration.model.name,
            settings=configuration.model.parameters,
            system_prompt=configuration.rendered_system_prompt(tuple(self._actions.execute()), memory),
            assets=configuration.assets,
            started_at=cycle_flow.started_at,
            now=now,
            state=cycle_flow.state_view(),
            sources=(*data, *self._aggregated(data)),
            missing=tuple(f"{source.label}: {source.reason}" for source in absent),
            memory=memory,
        )
        return CycleContext(cycle_flow, question, self._composer.execute(question))

    def _aggregated(self, data: tuple[SourceData, ...]) -> tuple[SourceData, ...]:
        return tuple(
            SourceData(aggregate.source, aggregate.adapter, None, aggregate.asset, aggregate.values)
            for aggregate in self._aggregates.execute(data)
        )
