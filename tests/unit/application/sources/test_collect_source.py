from datetime import UTC, datetime
from uuid import uuid4

import pytest

from autotrading.application.sources.collect_source import CollectedSource, CollectSourceCommand, CollectSourceUseCase
from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.application.sources.ports import ReadSourceCommand
from autotrading.domain.sources.errors import SourceNotAvailableError, SourceParameterOutOfRangeError
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.source_catalog import SourceCatalog
from autotrading.domain.sources.source_sample import CycleReference, SourceSample, SourceValue
from tests.fakes.source_readers import FakeSourceReaderAdapter, InMemorySampleRepositoryAdapter

COLLECTED = datetime(2026, 11, 12, 10, 7, tzinfo=UTC)
REFERENCE = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
CYCLE = CycleReference(uuid4(), datetime(2026, 11, 12, 10, 7, tzinfo=UTC))
CATALOG = SourceCatalog((INDICATORS, NEWS))
VALUE = SourceValue(REFERENCE, {"prezzo": "100"})


def command(source: str, parameters: dict[str, int] | None = None, weight: int = 5) -> CollectSourceCommand:
    return CollectSourceCommand(CYCLE, source, weight, parameters or {}, ("BTC", "ETH"), COLLECTED)


def test_a_per_asset_source_is_read_for_every_asset_with_the_settings_of_the_flow() -> None:
    reader = FakeSourceReaderAdapter([VALUE])
    use_case = CollectSourceUseCase(CATALOG, {"indicatori": reader}, InMemorySampleRepositoryAdapter())

    use_case.execute(command("indicatori", {"lunghezza_serie": 20}))

    assert reader.readings == [
        ReadSourceCommand(CYCLE.flow_id, "BTC", {"lunghezza_serie": 20}, COLLECTED),
        ReadSourceCommand(CYCLE.flow_id, "ETH", {"lunghezza_serie": 20}, COLLECTED),
    ]


def test_a_market_source_is_read_once_with_the_defaults_of_the_catalog() -> None:
    reader = FakeSourceReaderAdapter([VALUE])
    use_case = CollectSourceUseCase(CATALOG, {"notizie": reader}, InMemorySampleRepositoryAdapter())

    use_case.execute(command("notizie"))

    assert reader.readings == [
        ReadSourceCommand(CYCLE.flow_id, None, {"numero_notizie": 10, "eta_massima_ore": 24}, COLLECTED)
    ]


def test_every_value_is_recorded_and_given_back_with_the_weight() -> None:
    samples = InMemorySampleRepositoryAdapter()
    use_case = CollectSourceUseCase(CATALOG, {"indicatori": FakeSourceReaderAdapter([VALUE])}, samples)

    collected = use_case.execute(command("indicatori", weight=8))

    expected = tuple(
        SourceSample(CYCLE, "indicatori", asset, REFERENCE, COLLECTED, {"prezzo": "100"}) for asset in ("BTC", "ETH")
    )
    assert collected == CollectedSource("indicatori", 8, expected)
    assert samples.samples == list(expected)


def test_a_source_without_data_gives_no_sample() -> None:
    samples = InMemorySampleRepositoryAdapter()
    use_case = CollectSourceUseCase(CATALOG, {"notizie": FakeSourceReaderAdapter()}, samples)

    collected = use_case.execute(command("notizie"))

    assert collected.samples == ()
    assert samples.samples == []


def test_a_parameter_out_of_range_is_refused_before_any_reading() -> None:
    reader = FakeSourceReaderAdapter([VALUE])
    use_case = CollectSourceUseCase(CATALOG, {"notizie": reader}, InMemorySampleRepositoryAdapter())

    with pytest.raises(SourceParameterOutOfRangeError):
        use_case.execute(command("notizie", {"numero_notizie": 51}))

    assert reader.readings == []


def test_a_source_out_of_the_catalog_is_not_available() -> None:
    use_case = CollectSourceUseCase(CATALOG, {}, InMemorySampleRepositoryAdapter())

    with pytest.raises(SourceNotAvailableError, match="fonte non disponibile: pivot"):
        use_case.execute(command("pivot"))


def test_a_source_of_the_catalog_without_reader_is_not_available() -> None:
    use_case = CollectSourceUseCase(CATALOG, {}, InMemorySampleRepositoryAdapter())

    with pytest.raises(SourceNotAvailableError, match="fonte non disponibile: notizie"):
        use_case.execute(command("notizie"))


class FailingReader:
    def execute(self, command: ReadSourceCommand) -> list[SourceValue]:
        if command.asset == "ETH":
            raise SourceUnavailableError(INDICATORS.name)
        return [VALUE]


def test_a_failing_reading_records_nothing_of_the_source() -> None:
    samples = InMemorySampleRepositoryAdapter()
    use_case = CollectSourceUseCase(CATALOG, {"indicatori": FailingReader()}, samples)

    with pytest.raises(SourceUnavailableError):
        use_case.execute(command("indicatori"))

    assert samples.samples == []
