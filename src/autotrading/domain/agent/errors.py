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


class DecisionNotConformingError(DomainError):
    """A decision of the agent outside the response format: it is discarded with the reason, never executed."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason

    @classmethod
    def missing(cls, field: str) -> DecisionNotConformingError:
        return cls(f"campo obbligatorio mancante: {field}")

    @classmethod
    def type(cls, field: str) -> DecisionNotConformingError:
        return cls(f"valore di tipo non ammesso: {field}")

    @classmethod
    def range(cls, field: str) -> DecisionNotConformingError:
        return cls(f"valore fuori dall'intervallo: {field}")

    @classmethod
    def not_allowed(cls, field: str) -> DecisionNotConformingError:
        return cls(f"valore non ammesso: {field}")

    @classmethod
    def action(cls, name: str) -> DecisionNotConformingError:
        return cls(f"azione non ammessa: {name}")

    @classmethod
    def foreign(cls, asset: str) -> DecisionNotConformingError:
        return cls(f"asset non del flusso: {asset}")

    @classmethod
    def repeated(cls, asset: str) -> DecisionNotConformingError:
        return cls(f"decisione ripetuta per l'asset: {asset}")


class InvalidAgentContextError(DomainError):
    """A context whose times have no time zone, or whose cycle comes before the start of the flow: a defect."""

    status_code = 500

    def __init__(self) -> None:
        super().__init__("contesto dell'agente non valido")


class InvalidModelUsageError(DomainError):
    """Negative tokens, cost or prices: a defect of the provider adapter or of the catalog."""

    status_code = 500

    def __init__(self) -> None:
        super().__init__("consumo del modello non valido")
