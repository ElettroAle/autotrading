from datetime import UTC, datetime
from uuid import uuid4

import pytest

from autotrading.application.sources.collect_source import CollectedSource, CollectSourceCommand, CollectSourceUseCase
from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.application.sources.ports import SourceRequest
from autotrading.domain.sources.errors import (
    SourceAdapterNotAvailableError,
    SourceNotAvailableError,
    SourceParameterOutOfRangeError,
)
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.sentiment import SENTIMENT
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration
from autotrading.domain.sources.source_catalog import OfferedSource, SourceCatalog
from autotrading.domain.sources.source_sample import CycleReference, SourceSample, SourceValue
from tests.fakes.source_readers import FakeSourceReaderAdapter, InMemorySampleRepositoryAdapter

COLLECTED = datetime(2026, 11, 12, 10, 7, tzinfo=UTC)
REFERENCE = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
CYCLE = CycleReference(uuid4(), datetime(2026, 11, 12, 10, 7, tzinfo=UTC))


def declaration(name: str) -> SourceAdapterDeclaration:
    return SourceAdapterDeclaration(name, f"adapter {name}", (), (), offers_history=False)


CATALOG = SourceCatalog(
    (
        OfferedSource(INDICATORS, (declaration("mercato"),)),
        OfferedSource(SENTIMENT, (declaration("primo"), declaration("secondo"))),
        OfferedSource(NEWS, (declaration("feed"),)),
    )
)
VALUE = SourceValue(REFERENCE, {"prezzo": "100"})
INDICATORS_READER = ("indicatori", "mercato")
NEWS_READER = ("notizie", "feed")


def command(reader: tuple[str, str], parameters: dict[str, int] | None = None, weight: int = 5) -> CollectSourceCommand:
    source, adapter = reader
    return CollectSourceCommand(CYCLE, source, adapter, weight, parameters or {}, ("BTC", "ETH"), COLLECTED)


def test_a_per_asset_source_is_read_for_every_asset_with_the_settings_of_the_flow() -> None:
    reader = FakeSourceReaderAdapter([VALUE])
    use_case = CollectSourceUseCase(CATALOG, {INDICATORS_READER: reader}, InMemorySampleRepositoryAdapter())

    use_case.execute(command(INDICATORS_READER, {"lunghezza_serie": 20}))

    # The parameters the flow does not set take the defaults of the catalog.
    settings = INDICATORS.settings({"lunghezza_serie": 20})
    assert settings["lunghezza_serie"] == 20
    assert reader.readings == [
        SourceRequest(CYCLE.flow_id, "BTC", settings, COLLECTED),
        SourceRequest(CYCLE.flow_id, "ETH", settings, COLLECTED),
    ]


def test_a_market_source_is_read_once_with_the_defaults_of_the_catalog() -> None:
    reader = FakeSourceReaderAdapter([VALUE])
    use_case = CollectSourceUseCase(CATALOG, {NEWS_READER: reader}, InMemorySampleRepositoryAdapter())

    use_case.execute(command(NEWS_READER))

    assert reader.readings == [
        SourceRequest(CYCLE.flow_id, None, {"numero_notizie": 10, "eta_massima_ore": 24}, COLLECTED)
    ]


def test_only_the_adapter_asked_reads_the_source() -> None:
    first, second = FakeSourceReaderAdapter([VALUE]), FakeSourceReaderAdapter([VALUE])
    readers = {("sentiment", "primo"): first, ("sentiment", "secondo"): second}
    use_case = CollectSourceUseCase(CATALOG, readers, InMemorySampleRepositoryAdapter())

    use_case.execute(command(("sentiment", "secondo")))

    assert (len(first.readings), len(second.readings)) == (0, 1)


def test_every_value_is_recorded_and_given_back_with_its_adapter_and_its_weight() -> None:
    samples = InMemorySampleRepositoryAdapter()
    use_case = CollectSourceUseCase(CATALOG, {INDICATORS_READER: FakeSourceReaderAdapter([VALUE])}, samples)

    collected = use_case.execute(command(INDICATORS_READER, weight=8))

    expected = tuple(
        SourceSample(CYCLE, "indicatori", "mercato", asset, REFERENCE, COLLECTED, {"prezzo": "100"})
        for asset in ("BTC", "ETH")
    )
    assert collected == CollectedSource("indicatori", "mercato", 8, expected)
    assert samples.samples == list(expected)


def test_a_source_without_data_gives_no_sample() -> None:
    samples = InMemorySampleRepositoryAdapter()
    use_case = CollectSourceUseCase(CATALOG, {NEWS_READER: FakeSourceReaderAdapter()}, samples)

    collected = use_case.execute(command(NEWS_READER))

    assert collected.samples == ()
    assert samples.samples == []


def test_a_parameter_out_of_range_is_refused_before_any_reading() -> None:
    reader = FakeSourceReaderAdapter([VALUE])
    use_case = CollectSourceUseCase(CATALOG, {NEWS_READER: reader}, InMemorySampleRepositoryAdapter())

    with pytest.raises(SourceParameterOutOfRangeError):
        use_case.execute(command(NEWS_READER, {"numero_notizie": 51}))

    assert reader.readings == []


def test_a_source_out_of_the_catalog_is_not_available() -> None:
    use_case = CollectSourceUseCase(CATALOG, {}, InMemorySampleRepositoryAdapter())

    with pytest.raises(SourceNotAvailableError, match="fonte non disponibile: pivot"):
        use_case.execute(command(("pivot", "mercato")))


def test_an_adapter_the_source_does_not_offer_is_not_available() -> None:
    use_case = CollectSourceUseCase(CATALOG, {}, InMemorySampleRepositoryAdapter())

    with pytest.raises(SourceAdapterNotAvailableError, match="adapter non disponibile per la fonte notizie: altro"):
        use_case.execute(command(("notizie", "altro")))


def test_an_adapter_of_the_catalog_without_reader_is_not_available() -> None:
    use_case = CollectSourceUseCase(CATALOG, {}, InMemorySampleRepositoryAdapter())

    with pytest.raises(SourceAdapterNotAvailableError, match="adapter non disponibile per la fonte notizie: feed"):
        use_case.execute(command(NEWS_READER))


class FailingReader:
    def execute(self, command: SourceRequest) -> list[SourceValue]:
        if command.asset == "ETH":
            raise SourceUnavailableError(INDICATORS.name)
        return [VALUE]


def test_a_failing_reading_records_nothing_of_the_source() -> None:
    samples = InMemorySampleRepositoryAdapter()
    use_case = CollectSourceUseCase(CATALOG, {INDICATORS_READER: FailingReader()}, samples)

    with pytest.raises(SourceUnavailableError):
        use_case.execute(command(INDICATORS_READER))

    assert samples.samples == []


def test_a_source_whose_silence_is_a_datum_says_so_without_recording_it() -> None:
    samples = InMemorySampleRepositoryAdapter()
    use_case = CollectSourceUseCase(CATALOG, {NEWS_READER: FakeSourceReaderAdapter([])}, samples)

    collected = use_case.execute(command(NEWS_READER, {"eta_massima_ore": 1}))

    assert collected == CollectedSource("notizie", "feed", 5, (), {"nota": "nessuna notizia nell'ultima ora"})
    assert samples.samples == []


def test_a_silent_source_without_a_meaning_for_its_silence_gives_no_note() -> None:
    readers = {INDICATORS_READER: FakeSourceReaderAdapter([])}
    use_case = CollectSourceUseCase(CATALOG, readers, InMemorySampleRepositoryAdapter())

    assert use_case.execute(command(INDICATORS_READER)).note is None


def test_the_entries_are_the_values_with_their_asset_or_the_note_of_the_silence() -> None:
    sample = SourceSample(CYCLE, "indicatori", "mercato", "BTC", REFERENCE, COLLECTED, {"prezzo": "100"})

    assert CollectedSource("indicatori", "mercato", 8, (sample,)).entries == (("BTC", {"prezzo": "100"}),)
    assert CollectedSource("notizie", "feed", 5, (), {"nota": "n"}).entries == ((None, {"nota": "n"}),)
