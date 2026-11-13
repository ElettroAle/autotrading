from autotrading.application.sources.ports import SentimentPort, SourceRequest
from autotrading.domain.sources.source_sample import SourceValue


class ReadSentimentUseCase:
    """Reads the Fear & Greed index of one provider; the data refers to the update the provider published (R1.3.6)."""

    def __init__(self, sentiment: SentimentPort) -> None:
        self._sentiment = sentiment

    def execute(self, command: SourceRequest) -> tuple[SourceValue]:  # noqa: ARG002 - the index is of the whole market
        index = self._sentiment.read_index()
        values = {
            "valore": str(index.value),
            "classificazione": index.classification,
            "aggiornato_alle": index.updated_at.isoformat(),
        }
        return (SourceValue(index.updated_at, values),)
