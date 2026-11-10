from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from autotrading.domain.verification.errors import InsufficientMarginError, PositionAlreadyOpenError
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


@dataclass(frozen=True, slots=True)
class Opening:
    """The position the procedure opens: always the same, so two runs can be compared (R0.4.1)."""

    coin: str
    side: str
    leverage: int
    value: Decimal


PROCEDURE_OPENING = Opening(coin="BTC", side="long", leverage=2, value=Decimal(12))
REQUIRED_MARGIN = Decimal(12)


def require_startable(reading: AccountReading) -> None:
    """The procedure starts only on an account without a position on its asset and with enough margin."""
    coin = PROCEDURE_OPENING.coin
    if reading.positions_on(coin):
        raise PositionAlreadyOpenError(coin)
    if reading.available_margin < REQUIRED_MARGIN:
        raise InsufficientMarginError(REQUIRED_MARGIN)


def missing_opening(reading: AccountReading) -> str | None:
    """Why the reading after the opening is not the position the procedure opened, if it is not."""
    opening = PROCEDURE_OPENING
    held = [(position.side, position.leverage) for position in reading.positions_on(opening.coin)]
    if held == [(opening.side, opening.leverage)]:
        return None
    return f"nessuna posizione {opening.side} su {opening.coin} con leva {opening.leverage} letta"


def remaining_position(reading: AccountReading) -> str | None:
    """Why the reading after the closing still holds something on the asset, if it does."""
    coin = PROCEDURE_OPENING.coin
    return f"posizione su {coin} ancora aperta" if reading.positions_on(coin) else None
