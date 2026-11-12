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


class SourceParameterOutOfRangeError(DomainError):
    status_code = 422

    def __init__(self, label: str) -> None:
        super().__init__(f"parametro fuori dai valori ammessi: {label}")
        self.label = label


class UnknownSourceParameterError(DomainError):
    status_code = 422

    def __init__(self, source: str, key: str) -> None:
        super().__init__(f"parametro sconosciuto della fonte {source}: {key}")
        self.source = source
        self.key = key


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


class InvalidNewsItemError(DomainError):
    """A news story without a title or with a publication time without its time zone."""

    def __init__(self) -> None:
        super().__init__("notizia non valida")


class InvalidPriceForecastError(DomainError):
    """A forecast without the time zone of its instant or with a price that is not positive: a defect."""

    status_code = 500

    def __init__(self) -> None:
        super().__init__("previsione del prezzo non valida")


class InvalidSourceSampleError(DomainError):
    """A collected value with an instant without its time zone: a defect of the source that read it."""

    status_code = 500

    def __init__(self) -> None:
        super().__init__("valore raccolto non valido")
