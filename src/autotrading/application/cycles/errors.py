from autotrading.application.errors import ApplicationError


class FlowOfCycleNotFoundError(ApplicationError):
    """The flow of a planned cycle is not among the flows the worker planned, or no longer exists: the cycle fails
    and the next round plans again from the database.
    """

    status_code = 404

    def __init__(self) -> None:
        super().__init__("flusso del ciclo non trovato")


class CycleFlowNotFoundError(ApplicationError):
    """The same answer for a flow that does not exist and for one of another tenant (R0.1.3, R1.7.3)."""

    status_code = 404

    def __init__(self) -> None:
        super().__init__("flusso non trovato")


class CycleNotFoundError(ApplicationError):
    status_code = 404

    def __init__(self) -> None:
        super().__init__("ciclo non trovato")


class UnrecordableDocumentError(ApplicationError):
    """A step described its result with a value that is not JSON data: a defect of the journal (R1.7.1)."""

    status_code = 500

    def __init__(self, kind: str) -> None:
        super().__init__(f"documento del ciclo non registrabile: {kind}")
