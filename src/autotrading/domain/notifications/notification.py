from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.notifications.errors import InvalidNotificationError


@dataclass(frozen=True, slots=True)
class Amount:
    value: Decimal
    currency: str

    def __str__(self) -> str:
        # The user reads Italian: decimal comma, and the digits as the event carried them.
        return f"{format(self.value, 'f').replace('.', ',')} {self.currency}"


@dataclass(frozen=True, slots=True)
class Notification:
    """An event of a flow or an account, with its essential values and never a credential (R1.8.2)."""

    subject: str
    event: str

    def __post_init__(self) -> None:
        if not self.subject.strip():
            raise InvalidNotificationError

    @property
    def text(self) -> str:
        return f"{self.subject}: {self.event}"

    @classmethod
    def position_opened(cls, flow: str, asset: str, direction: str, leverage: int, value: Amount) -> Notification:
        return cls(flow, f"aperta {direction} {asset}, leva {leverage}, {value}")

    @classmethod
    def position_closed(cls, flow: str, asset: str, pnl: Amount) -> Notification:
        return cls(flow, f"chiusa {asset}, PnL {pnl}")

    @classmethod
    def cycle_failed(cls, flow: str, message: str) -> Notification:
        return cls(flow, f"ciclo fallito, {message}")

    @classmethod
    def order_rejected(cls, flow: str, message: str) -> Notification:
        return cls(flow, f"ordine rifiutato, {message}")

    @classmethod
    def flow_paused(cls, flow: str, reason: str) -> Notification:
        return cls(flow, f"in pausa, {reason}")

    @classmethod
    def unattributable_position(cls, account: str, asset: str) -> Notification:
        return cls(account, f"posizione non attribuibile su {asset}")

    @classmethod
    def unattributable_fill(cls, account: str, asset: str) -> Notification:
        return cls(account, f"esecuzione non attribuibile su {asset}")

    @classmethod
    def unattributable_movement(cls, account: str, amount: Amount) -> Notification:
        return cls(account, f"movimento non attribuibile di {amount}")
