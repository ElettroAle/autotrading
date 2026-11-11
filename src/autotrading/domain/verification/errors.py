from decimal import Decimal

from autotrading.domain.errors import DomainError


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


class InsufficientMarginError(VerificationNotStartedError):
    def __init__(self, required: Decimal) -> None:
        super().__init__(f"margine insufficiente: servono almeno {required} USDC")
        self.required = required
