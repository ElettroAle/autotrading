from autotrading.application.errors import ApplicationError


class FlowNameInUseError(ApplicationError):
    status_code = 409

    def __init__(self) -> None:
        super().__init__("nome già usato da un altro flusso")


class FlowAccountNotFoundError(ApplicationError):
    """The same answer for an account that does not exist and for one of another tenant (R0.1.3)."""

    status_code = 404

    def __init__(self) -> None:
        super().__init__("conto non trovato")


class AssetNotTradableError(ApplicationError):
    status_code = 422

    def __init__(self, assets: tuple[str, ...]) -> None:
        super().__init__("asset non negoziabile sull'exchange: " + ", ".join(assets))
        self.assets = assets


class FlowExchangeUnavailableError(ApplicationError):
    status_code = 503

    def __init__(self) -> None:
        super().__init__("exchange non raggiungibile, riprovare")


class InvalidFlowSettingError(ApplicationError):
    """A model, a source or one of their parameters the platform does not admit for the flow, with the reason."""

    status_code = 422

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class FlowCredentialsRejectedError(ApplicationError):
    """The exchange refuses the credentials of the account of the flow: it repeats until the user replaces them, and
    pauses every active flow of the account (R1.2.4).
    """

    status_code = 422
    permanent = True

    def __init__(self, account: str) -> None:
        super().__init__(f"credenziali del conto non valide: {account}")
        self.account = account
