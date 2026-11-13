from autotrading.application.errors import ApplicationError


class VerificationAccountNotFoundError(ApplicationError):
    """The same answer for an account that does not exist and for one of another tenant (R0.1.3)."""

    status_code = 404

    def __init__(self) -> None:
        super().__init__("non trovato")


class VerificationStepError(ApplicationError):
    """A step could not be carried out: the exchange was not reached, or it refused the credentials."""

    status_code = 503

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class VerificationExchangeUnsupportedError(VerificationStepError):
    def __init__(self) -> None:
        super().__init__("exchange non supportato")


class VerificationCredentialsNotOpenedError(VerificationStepError):
    def __init__(self) -> None:
        super().__init__("credenziali del conto non leggibili")


class VerificationCredentialsRejectedError(VerificationStepError):
    def __init__(self) -> None:
        super().__init__("credenziali rifiutate dall'exchange")


class VerificationExchangeUnavailableError(VerificationStepError):
    def __init__(self) -> None:
        super().__init__("exchange non raggiungibile, riprovare")


class VerificationWorkerUnavailableError(ApplicationError):
    status_code = 503

    def __init__(self) -> None:
        super().__init__("servizio di esecuzione non raggiungibile, riprovare")
