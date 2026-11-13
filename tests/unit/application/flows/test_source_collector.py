import threading
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from autotrading.adapters.outbound.threads.concurrent_calls import ThreadPoolConcurrentCallsAdapter
from autotrading.application.flows.ports import FlowSnapshot, SourceReading, SourceRequest
from autotrading.application.flows.source_collector import SourceCollector, real_seconds
from autotrading.domain.flows.cycle_record import AbsentSource
from tests.fakes.cycles import FakeSourcesAdapter, FakeTransientError

SECOND = 0.01
MINUTE = timedelta(seconds=60)
PLANNED_AT = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)


def request(sources: tuple[str, ...], flow_id: UUID | None = None) -> SourceRequest:
    return SourceRequest(flow_id or uuid4(), PLANNED_AT, FlowSnapshot(sources, None))


class BrokenSourceAdapter:
    def collect(self, request: SourceRequest, source: str) -> object:
        message = f"{source} {request.flow_id}"
        raise ZeroDivisionError(message)


@pytest.fixture
def sources() -> Iterator[FakeSourcesAdapter]:
    adapter = FakeSourcesAdapter(SECOND)
    yield adapter
    adapter.released.set()


def compressed(sources: FakeSourcesAdapter | BrokenSourceAdapter) -> SourceCollector:
    return SourceCollector(sources, ThreadPoolConcurrentCallsAdapter(), lambda wait: wait.total_seconds() * SECOND)


def test_the_real_wait_lasts_the_seconds_of_the_cycle() -> None:
    assert real_seconds(timedelta(seconds=30)) == 30.0


def test_a_flow_without_sources_collects_nothing(sources: FakeSourcesAdapter) -> None:
    assert compressed(sources).collect(request(()), MINUTE) == ([], [])


def test_every_source_that_answers_gives_its_reading(sources: FakeSourcesAdapter) -> None:
    flow_id = uuid4()

    readings, absent = compressed(sources).collect(request(("indicatori", "notizie"), flow_id), MINUTE)

    assert readings == [
        SourceReading("indicatori", {"source": "indicatori", "flow_id": str(flow_id)}),
        SourceReading("notizie", {"source": "notizie", "flow_id": str(flow_id)}),
    ]
    assert absent == []


def test_a_silent_source_is_absent_with_the_wait_in_seconds(sources: FakeSourcesAdapter) -> None:
    sources.silent.add("notizie")

    readings, absent = compressed(sources).collect(request(("indicatori", "notizie")), timedelta(seconds=30))

    assert [reading.source for reading in readings] == ["indicatori"]
    assert absent == [AbsentSource("notizie", "nessuna risposta entro 30 secondi")]


def test_the_sources_are_asked_together(sources: FakeSourcesAdapter) -> None:
    sources.late.update({"indicatori": 40, "notizie": 40})

    readings, absent = compressed(sources).collect(request(("indicatori", "notizie")), MINUTE)

    assert ([reading.source for reading in readings], absent) == (["indicatori", "notizie"], [])


def test_a_late_source_is_not_awaited(sources: FakeSourcesAdapter) -> None:
    sources.silent.add("notizie")
    finished = threading.Event()

    def collect() -> None:
        compressed(sources).collect(request(("notizie",)), MINUTE)
        finished.set()

    threading.Thread(target=collect, daemon=True).start()

    assert finished.wait(2.0)


def test_a_source_that_fails_is_absent_with_its_message(sources: FakeSourcesAdapter) -> None:
    sources.failing["notizie"] = FakeTransientError("limite di richieste superato")

    _, absent = compressed(sources).collect(request(("notizie",)), MINUTE)

    assert absent == [AbsentSource("notizie", "limite di richieste superato")]


def test_a_defect_of_a_source_is_not_hidden() -> None:
    with pytest.raises(ZeroDivisionError, match="notizie"):
        compressed(BrokenSourceAdapter()).collect(request(("notizie",)), MINUTE)
