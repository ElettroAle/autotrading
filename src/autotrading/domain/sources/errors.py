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
