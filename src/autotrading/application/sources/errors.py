from autotrading.application.errors import ApplicationError


class SourceUnavailableError(ApplicationError):
    """An external source did not answer, or answered in an unexpected shape: the cycle treats it as absent."""

    status_code = 503

    def __init__(self, source: str) -> None:
        super().__init__(f"fonte non raggiungibile: {source}")
        self.source = source


class AssetRequiredError(ApplicationError):
    """A per-asset source asked without an asset: a defect of the caller, never of the user."""

    status_code = 500

    def __init__(self) -> None:
        super().__init__("la fonte va interrogata per un asset")


class TimeframeNotSupportedError(ApplicationError):
    """Candles asked on an interval the exchange does not publish: a defect of the caller, never of the user."""

    status_code = 500

    def __init__(self, minutes: int) -> None:
        super().__init__(f"intervallo di candela non pubblicato dall'exchange: {minutes} minuti")
        self.minutes = minutes


class SourceCredentialsNotFoundError(ApplicationError):
    status_code = 404

    def __init__(self, adapter: str) -> None:
        super().__init__(f"credenziali dell'adapter non trovate: {adapter}")
        self.adapter = adapter


class SourceSecretsNotOpenedError(ApplicationError):
    """The sealed secrets are not of the tenant and adapter of the credentials, or the key that sealed them is gone: a
    defect of the installation, never of the user."""

    status_code = 500

    def __init__(self, adapter: str) -> None:
        super().__init__(f"credenziali dell'adapter non leggibili: {adapter}")
        self.adapter = adapter


class SourceCredentialsRejectedError(ApplicationError):
    """The provider of an adapter refuses the credentials of the tenant: the adapter is absent from the cycle (R1.2.5,
    R4.1.2), never an error of the cycle."""

    def __init__(self, adapter: str) -> None:
        super().__init__(f"credenziali rifiutate dal fornitore: {adapter}")
        self.adapter = adapter


class SourceUnansweredError(ApplicationError):
    """A source still reading at the end of its wait: transient, as in a cycle (R1.2.5)."""

    def __init__(self, seconds: float) -> None:
        super().__init__(f"nessuna risposta entro {int(seconds)} secondi")
        self.seconds = seconds


class SourceTrialWorkerUnavailableError(ApplicationError):
    """The worker, the only service that opens the credentials of the adapters, cannot be reached or answers in an
    unexpected shape (R6.3.1)."""

    status_code = 503

    def __init__(self) -> None:
        super().__init__("servizio di esecuzione non raggiungibile, riprovare")
