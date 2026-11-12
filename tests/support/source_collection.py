"""A cycle reduced to the collection of the active sources and to the context they give the agent (R1.3.2, R1.3.8).

The planned cycle itself is proved by the scenarios of F1.2; here only what the sources put into it.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from autotrading.application.sources.collect_source import CollectedSource, CollectSourceCommand, CollectSourceUseCase
from autotrading.bootstrap import SOURCE_CATALOG, agent_sources_of
from autotrading.domain.agent.agent_context import AgentContext, FlowStateView
from autotrading.domain.flows.selections import DEFAULT_WEIGHT, SourceSelection
from autotrading.domain.sources.source_sample import CycleReference, SourceValue
from tests.fakes.source_readers import FakeSourceReaderAdapter, InMemorySampleRepositoryAdapter

STARTED_AT = datetime(2026, 11, 12, 8, 0, tzinfo=UTC)
COLLECTED_AT = datetime(2026, 11, 12, 10, 7, tzinfo=UTC)
STATE = FlowStateView("USDC", Decimal(1000), Decimal(1000), Decimal(1000), Decimal(0), ())


@dataclass
class SourceCycle:
    """One flow of the user, with the readers of every source of the catalog and the recorded samples."""

    flow_id: UUID = field(default_factory=uuid4)
    assets: tuple[str, ...] = ()
    selections: list[SourceSelection] = field(default_factory=list)
    readers: dict[str, FakeSourceReaderAdapter] = field(
        default_factory=lambda: {
            source.name: FakeSourceReaderAdapter([SourceValue(COLLECTED_AT, {"valore": "1"})])
            for source in SOURCE_CATALOG.sources
        }
    )
    samples: InMemorySampleRepositoryAdapter = field(default_factory=InMemorySampleRepositoryAdapter)
    collected: list[CollectedSource] = field(default_factory=list)
    context: AgentContext | None = None

    def activate(self, source: str, weight: int = DEFAULT_WEIGHT) -> None:
        self.selections.append(SourceSelection(source, weight))

    def run(self, collected_at: datetime = COLLECTED_AT) -> CycleReference:
        """Runs the cycle planned at the instant of the collection, and gives back that cycle."""
        use_case = CollectSourceUseCase(SOURCE_CATALOG, self.readers, self.samples)
        reference = CycleReference(self.flow_id, collected_at)
        self.collected = [
            use_case.execute(
                CollectSourceCommand(
                    reference, selection.name, selection.weight, selection.parameters, self.assets, collected_at
                )
            )
            for selection in self.selections
        ]
        self.context = AgentContext(
            "istruzioni", self.assets, 10, STARTED_AT, collected_at, STATE, agent_sources_of(self.collected), ()
        )
        return reference

    def agent_context(self) -> AgentContext:
        assert self.context is not None
        return self.context
