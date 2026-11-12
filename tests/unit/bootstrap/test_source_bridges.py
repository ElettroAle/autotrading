"""The bridge bootstrap builds between the sources context and the agent context (ADR 0048)."""

from datetime import UTC, datetime
from uuid import uuid4

from autotrading.application.sources.collect_source import CollectedSource
from autotrading.bootstrap import agent_sources_of
from autotrading.domain.agent.agent_context import SourceData
from autotrading.domain.sources.source_sample import CycleReference, SourceSample

AT = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
CYCLE = CycleReference(uuid4(), AT)


def sample(source: str, asset: str | None, price: str) -> SourceSample:
    return SourceSample(CYCLE, source, asset, AT, AT, {"valore": price})


def test_every_collected_value_reaches_the_agent_with_the_weight_of_its_source() -> None:
    collected = [
        CollectedSource("indicatori", 8, (sample("indicatori", "BTC", "1"), sample("indicatori", "ETH", "2"))),
        CollectedSource("sentiment-alternative-me", 2, (sample("sentiment-alternative-me", None, "72"),)),
    ]

    assert agent_sources_of(collected) == (
        SourceData("indicatori", 8, "BTC", {"valore": "1"}),
        SourceData("indicatori", 8, "ETH", {"valore": "2"}),
        SourceData("sentiment-alternative-me", 2, None, {"valore": "72"}),
    )


def test_a_source_without_values_gives_nothing_to_the_agent() -> None:
    assert agent_sources_of([CollectedSource("notizie", 5, ())]) == ()
