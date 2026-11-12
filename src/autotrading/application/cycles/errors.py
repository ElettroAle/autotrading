from autotrading.application.errors import ApplicationError


class FlowOfCycleNotFoundError(ApplicationError):
    """The flow of a planned cycle is not among the flows the worker planned, or no longer exists: the cycle fails
    and the next round plans again from the database.
    """

    status_code = 404

    def __init__(self) -> None:
        super().__init__("flusso del ciclo non trovato")
