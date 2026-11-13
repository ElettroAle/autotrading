from decimal import Decimal

from autotrading.domain.errors import DomainError
from autotrading.domain.italian_text import money_text


class VerificationNotStartedError(DomainError):
    """The account is not ready for the procedure: nothing is sent and nothing is recorded (R0.4.1)."""

    status_code = 409

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class PositionAlreadyOpenError(VerificationNotStartedError):
    def __init__(self, coin: str) -> None:
        super().__init__(f"posizione già aperta su {coin}")
        self.coin = coin


class AssetOfFlowError(VerificationNotStartedError):
    """The executions of the procedure would change the position a flow of the account expects, and pause it."""

    def __init__(self, coin: str, flow_name: str) -> None:
        super().__init__(f"{coin} è un asset del flusso {flow_name}")
        self.coin = coin
        self.flow_name = flow_name


class InsufficientMarginError(VerificationNotStartedError):
    """The margin the opening of the procedure needs: its value over its leverage."""

    def __init__(self, required: Decimal, currency: str) -> None:
        super().__init__(f"margine disponibile insufficiente: servono {money_text(required)} {currency}")
        self.required = required


class AmountBelowMinimumError(VerificationNotStartedError):
    """The exchange would refuse the opening: its minimum is read from it, never assumed."""

    def __init__(self, minimum: Decimal, currency: str) -> None:
        super().__init__(f"importo sotto il minimo dell'exchange: {money_text(minimum)} {currency}")
        self.minimum = minimum


class VerificationAmountNotPositiveError(DomainError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("l'importo della procedura deve essere maggiore di zero")


class VerificationInProgressError(VerificationNotStartedError):
    """Another procedure runs on the asset of the account: two would mix their orders on the same position."""

    def __init__(self, coin: str) -> None:
        super().__init__(f"procedura di verifica già in corso su {coin}")
        self.coin = coin
