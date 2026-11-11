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
