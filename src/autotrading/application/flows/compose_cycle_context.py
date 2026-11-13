from collections.abc import Sequence
from uuid import UUID

from autotrading.application.flows.ports import (
    AgentPromptComposerPort,
    ClockPort,
    CycleContext,
    FlowSnapshot,
    SourceReading,
)
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_question import CycleQuestion
from autotrading.domain.flows.cycle_record import AbsentSource
from autotrading.domain.flows.source_data import SourceData


class ComposeCycleContextUseCase:
    """The context of the agent for a cycle: the flow alone, the data of its sources and the data missing, declared
    (R1.2.5, R1.4.3).
    """

    def __init__(self, composer: AgentPromptComposerPort, clock: ClockPort) -> None:
        self._composer = composer
        self._clock = clock

    def execute(
        self,
        flow_id: UUID,  # noqa: ARG002 - the signature of the port
        snapshot: FlowSnapshot[CycleFlow],
        readings: Sequence[SourceReading[tuple[SourceData, ...]]],
        absent: Sequence[AbsentSource],
    ) -> CycleContext:
        cycle_flow = snapshot.state
        configuration = cycle_flow.configuration
        question = CycleQuestion(
            model=configuration.model.name,
            settings=configuration.model.parameters,
            instructions=configuration.instructions,
            assets=configuration.assets,
            max_leverage=configuration.risk_limits.max_leverage,
            started_at=cycle_flow.started_at,
            now=self._clock.now(),
            state=cycle_flow.state_view(),
            sources=tuple(data for reading in readings for data in reading.data),
            missing=tuple(f"{source.source}: {source.reason}" for source in absent),
        )
        return CycleContext(cycle_flow, question, self._composer.execute(question))
