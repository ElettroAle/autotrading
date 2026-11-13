from uuid import UUID

from autotrading.application.errors import ApplicationError
from autotrading.domain.errors import ErrorScope
from autotrading.domain.flows.flow_state import PositionMismatch
from autotrading.domain.italian_text import number_text


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


class FlowCredentialsNotOpenedError(ApplicationError):
    """The worker cannot open the sealed credentials of the account to learn its address."""

    status_code = 500

    def __init__(self) -> None:
        super().__init__("credenziali del conto non leggibili")


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

    def __init__(self, account: str, account_id: UUID) -> None:
        super().__init__(f"credenziali del conto non valide: {account}")
        self.account = account
        self.account_id = account_id

    @property
    def scope(self) -> ErrorScope:
        return ErrorScope(account_id=self.account_id)


class FlowNotFoundError(ApplicationError):
    """The same answer for a flow that does not exist and for one of another tenant (R0.1.3)."""

    status_code = 404

    def __init__(self) -> None:
        super().__init__("flusso non trovato")


class FlowVersionNotFoundError(ApplicationError):
    status_code = 404

    def __init__(self, version: int) -> None:
        super().__init__(f"versione di configurazione non trovata: {version}")
        self.version = version


class AssetWithOpenPositionError(ApplicationError):
    """The flow would leave a position it no longer follows: it is closed first, then the asset removed (R1.1.3)."""

    status_code = 409

    def __init__(self, assets: tuple[str, ...]) -> None:
        super().__init__("posizione aperta sull'asset da togliere: " + ", ".join(assets))
        self.assets = assets


class AssetUnderVerificationError(ApplicationError):
    """The procedure of verification runs on an asset of the flow: a cycle would mix its orders with the procedure's
    and pause the flow for a position it did not open (R0.4.1, ADR 0079)."""

    status_code = 409

    def __init__(self, asset: str) -> None:
        super().__init__(f"procedura di verifica in corso su {asset}")
        self.asset = asset


class OperationsCursorInvalidError(ApplicationError):
    """The `after` of a page of operations is not one the platform gave (ADR 0074)."""

    status_code = 422

    def __init__(self) -> None:
        super().__init__("pagina delle operazioni non valida")


class FlowPositionMismatchError(ApplicationError):
    """The position of the account on an asset of the flow is not the one the ledger of the flow expects: someone
    else traded it, so the flow sends no order and pauses until the user looks at it (Bug 155, ADR 0064).
    """

    status_code = 409
    permanent = True

    def __init__(self, mismatch: PositionMismatch) -> None:
        super().__init__(
            f"posizione {mismatch.asset} diversa da quella del flusso: "
            f"attesa {number_text(mismatch.expected)}, sul conto {number_text(mismatch.held)}"
        )
        self.mismatch = mismatch


class FlowLedgerIncompleteError(ApplicationError):
    """Part of the executions of the account is gone from the exchange before the platform recorded it: the totals of
    its flows can no longer be trusted, so every active flow of the account pauses (ADR 0063).
    """

    status_code = 409
    permanent = True

    def __init__(self, account_id: UUID) -> None:
        super().__init__("registro delle esecuzioni incompleto")
        self.account_id = account_id

    @property
    def scope(self) -> ErrorScope:
        return ErrorScope(account_id=self.account_id)
