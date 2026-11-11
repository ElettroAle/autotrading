from autotrading.domain.errors import DomainError


class ProviderRequiredError(DomainError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("fornitore obbligatorio")


class ProviderKeyRequiredError(DomainError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("chiave obbligatoria")


class ParameterOutOfRangeError(DomainError):
    status_code = 422

    def __init__(self, label: str) -> None:
        super().__init__(f"parametro fuori dai valori ammessi: {label}")
        self.label = label


class ParameterNotSupportedError(DomainError):
    status_code = 422

    def __init__(self, label: str) -> None:
        super().__init__(f"parametro non supportato dal modello: {label}")
        self.label = label


class UnknownParameterError(DomainError):
    status_code = 422

    def __init__(self, key: str) -> None:
        super().__init__(f"parametro sconosciuto: {key}")
        self.key = key


class ModelNotAvailableError(DomainError):
    status_code = 404

    def __init__(self, name: str) -> None:
        super().__init__(f"modello non disponibile: {name}")
        self.name = name


class InvalidModelDefinitionError(DomainError):
    """A model or parameter declared inconsistently in the catalog: a defect of the configuration."""

    status_code = 500

    def __init__(self, subject: str) -> None:
        super().__init__(f"definizione del modello non valida: {subject}")
        self.subject = subject
