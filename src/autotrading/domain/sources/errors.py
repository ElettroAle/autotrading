from collections.abc import Mapping

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
    """The refusal names the parameter and the values it admits (R4.1.1)."""

    status_code = 422

    def __init__(self, label: str, minimum: int, maximum: int, key: str) -> None:
        super().__init__(f"parametro fuori dai valori ammessi: {label}, da {minimum} a {maximum}")
        self.label = label
        self.minimum = minimum
        self.maximum = maximum
        self.key = key

    @property
    def details(self) -> Mapping[str, object]:
        """The parameter and its limits, so the page of a trial shows them beside its field (R6.3.1)."""
        return {"field": self.key, "minimum": self.minimum, "maximum": self.maximum}


class SourceAdapterNotAvailableError(DomainError):
    status_code = 404

    def __init__(self, source: str, adapter: str) -> None:
        super().__init__(f"adapter non disponibile per la fonte {source}: {adapter}")
        self.source = source
        self.adapter = adapter


class InvalidSourceAdapterDeclarationError(DomainError):
    """An adapter of a source declared without a name or with a field twice: a defect of the adapter."""

    status_code = 500

    def __init__(self, adapter: str, repeated_field: str | None = None) -> None:
        if repeated_field is None:
            super().__init__("adapter della fonte senza nome")
        else:
            super().__init__(f"campo ripetuto nell'adapter {adapter}: {repeated_field}")
        self.adapter = adapter
        self.repeated_field = repeated_field


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


class InvalidWhaleTransferError(DomainError):
    """A transfer without the time zone of its instant, without asset, with no quantity or with a negative value."""

    def __init__(self) -> None:
        super().__init__("trasferimento non valido")


class InvalidVolumeSnapshotError(DomainError):
    """A volume or an aggressive trade that is negative, or a level of the book without a price or with a negative
    quantity."""

    def __init__(self) -> None:
        super().__init__("dati di volume non validi")


class InvalidSocialSnapshotError(DomainError):
    """A post without author, text or the time zone of its instant, a sentiment outside 0-100% or a negative count."""

    def __init__(self) -> None:
        super().__init__("dati social non validi")


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


class TimeframeNotAvailableError(DomainError):
    """The exchange publishes no candle interval as fine as the cycle interval: the indicators cannot be read."""

    def __init__(self, cycle_minutes: int) -> None:
        super().__init__(f"nessun intervallo di candela dell'exchange entro {cycle_minutes} minuti")
        self.cycle_minutes = cycle_minutes


class SourceAdapterNotFoundError(DomainError):
    """No source of the catalog is offered by an adapter of that name (R4.1.2)."""

    status_code = 404

    def __init__(self, adapter: str) -> None:
        super().__init__(f"adapter della fonte non disponibile: {adapter}")
        self.adapter = adapter


class SourceAdapterWithoutConfigurationError(DomainError):
    """Credentials given to an adapter that declares no field of configuration (R4.1.1, R4.1.2)."""

    status_code = 422

    def __init__(self, adapter: str) -> None:
        super().__init__(f"l'adapter {adapter} non richiede configurazione")
        self.adapter = adapter


class SourceAdapterNotConfiguredError(DomainError):
    """An adapter that needs configuration the tenant did not give: it stays in the list of the flow, not activatable,
    and in a cycle it is an absent source (R4.1.2).
    """

    status_code = 409

    def __init__(self, adapter: str) -> None:
        super().__init__(f"configura l'adapter {adapter} in Impostazioni \u203a Chiavi")
        self.adapter = adapter


class SourceConfigurationFieldRequiredError(DomainError):
    status_code = 422

    def __init__(self, field: str, label: str) -> None:
        # Only the first letter changes: the label may hold a name, as in "chiave API".
        super().__init__(f"{label[:1].lower()}{label[1:]} obbligatorio")
        self.field = field

    @property
    def details(self) -> Mapping[str, object]:
        return {"field": self.field}


class UnknownSourceConfigurationFieldError(DomainError):
    status_code = 422

    def __init__(self, field: str) -> None:
        super().__init__(f"campo non previsto: {field}")
        self.field = field

    @property
    def details(self) -> Mapping[str, object]:
        return {"field": self.field}


class TrialAssetRequiredError(DomainError):
    """A per-asset source is tried for one asset (R6.3.1)."""

    status_code = 422

    def __init__(self, source: str) -> None:
        super().__init__(f"scegli l'asset su cui provare la fonte {source}")
        self.source = source

    @property
    def details(self) -> Mapping[str, object]:
        return {"field": "asset"}


class InvalidSourceTrialError(DomainError):
    """A trial failed without a reason, succeeded with one, or lasted less than nothing: a defect of who builds it."""

    status_code = 500

    def __init__(self) -> None:
        super().__init__("prova della fonte non valida")
