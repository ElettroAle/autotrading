from autotrading.application.errors import ApplicationError


class VerificationAccountNotFoundError(ApplicationError):
    """The same answer for an account that does not exist and for one of another tenant (R0.1.3)."""

    def __init__(self) -> None:
        super().__init__("non trovato")


class VerificationStepError(ApplicationError):
    """A step could not be carried out: the exchange was not reached, or it refused the credentials."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class VerificationWorkerUnavailableError(ApplicationError):
    def __init__(self) -> None:
        super().__init__("servizio di esecuzione non raggiungibile, riprovare")
