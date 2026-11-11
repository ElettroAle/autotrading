from autotrading.domain.errors import DomainError


class InvalidSourceParameterError(DomainError):
    """A parameter declared with a default outside its range, or with an empty range: a defect of the source."""

    def __init__(self, key: str) -> None:
        super().__init__(f"parametro della fonte non valido: {key}")
        self.key = key


class SourceNotAvailableError(DomainError):
    status_code = 404

    def __init__(self, name: str) -> None:
        super().__init__(f"fonte non disponibile: {name}")
        self.name = name


class InvalidSentimentIndexError(DomainError):
    """A Fear & Greed reading outside 0-100, without classification or without its time zone."""

    def __init__(self) -> None:
        super().__init__("indice Fear & Greed non valido")


class InsufficientHistoryError(DomainError):
    """The exchange returned fewer prices than an indicator needs: the source is absent from that cycle."""

    def __init__(self, needed: int, available: int) -> None:
        super().__init__(f"storico dei prezzi insufficiente: servono {needed} valori, disponibili {available}")
        self.needed = needed
        self.available = available
