from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from autotrading.domain.verification.errors import (
    AmountBelowMinimumError,
    AssetOfFlowError,
    InsufficientMarginError,
    PositionAlreadyOpenError,
    VerificationAmountNotPositiveError,
)
from autotrading.domain.verification.reading import AccountReading


class Step(StrEnum):
    OPENING = "apertura long BTC leva 2"
    READING_AFTER_OPENING = "lettura dopo apertura"
    CLOSING = "chiusura"
    READING_AFTER_CLOSING = "lettura dopo chiusura"

    @property
    def short_name(self) -> str:
        # The overall outcome names the step without its details: "fallita al passo apertura".
        return "apertura" if self is Step.OPENING else self.value


# What the procedure opens, the same on every run so two runs can be compared; only the value is chosen (R0.4.1).
PROCEDURE_COIN = "BTC"
PROCEDURE_SIDE = "long"
PROCEDURE_LEVERAGE = 2


@dataclass(frozen=True, slots=True)
class Opening:
    """The position the procedure opens: always long on BTC with leverage 2, of the value of the run (R0.4.1)."""

    coin: str
    side: str
    leverage: int
    value: Decimal

    @property
    def required_margin(self) -> Decimal:
        return self.value / self.leverage


def procedure_opening(chosen: Decimal | None, exchange_minimum: Decimal, currency: str) -> Opening:
    """The opening of the value the user chose, or the minimum of the exchange of the account when none is chosen.

    The minimum comes from the exchange, never from the procedure: it changes from one exchange to another.
    """
    value = exchange_minimum if chosen is None else chosen
    if value <= 0:
        raise VerificationAmountNotPositiveError
    if value < exchange_minimum:
        raise AmountBelowMinimumError(exchange_minimum, currency)
    return Opening(coin=PROCEDURE_COIN, side=PROCEDURE_SIDE, leverage=PROCEDURE_LEVERAGE, value=value)


def require_free_of_flows(flow_name: str | None) -> None:
    """The procedure does not start on the asset of a flow of the account (Bug 165, ADR 0075)."""
    if flow_name is not None:
        raise AssetOfFlowError(PROCEDURE_COIN, flow_name)


def require_startable(reading: AccountReading, opening: Opening) -> None:
    """The procedure starts only on an account without a position on its asset and with the margin of its opening."""
    if reading.positions_on(opening.coin):
        raise PositionAlreadyOpenError(opening.coin)
    if reading.available_margin < opening.required_margin:
        raise InsufficientMarginError(opening.required_margin, reading.currency)


def missing_opening(reading: AccountReading) -> str | None:
    """Why the reading after the opening is not the position the procedure opened, if it is not."""
    held = [(position.side, position.leverage) for position in reading.positions_on(PROCEDURE_COIN)]
    if held == [(PROCEDURE_SIDE, PROCEDURE_LEVERAGE)]:
        return None
    return f"nessuna posizione {PROCEDURE_SIDE} su {PROCEDURE_COIN} con leva {PROCEDURE_LEVERAGE} letta"


def remaining_position(reading: AccountReading) -> str | None:
    """Why the reading after the closing still holds something on the asset, if it does."""
    held = reading.positions_on(PROCEDURE_COIN)
    return f"posizione su {PROCEDURE_COIN} ancora aperta" if held else None
