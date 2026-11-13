from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.italian_text import money_text
from autotrading.domain.notifications.errors import InvalidNotificationError

# An opening is told by the value it put on the market, in whole units: the cents add nothing to the event.
WHOLE_UNIT = Decimal(1)


@dataclass(frozen=True, slots=True)
class Amount:
    value: Decimal
    currency: str

    def __str__(self) -> str:
        return f"{money_text(self.value)} {self.currency}"


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
    def test(cls) -> Notification:
        return cls("notifica di prova", "le notifiche dei tuoi flussi arrivano qui")

    @classmethod
    def position_opened(cls, flow: str, asset: str, direction: str, leverage: int, value: Amount) -> Notification:
        whole = Amount(value.value.quantize(WHOLE_UNIT), value.currency)
        return cls(flow, f"aperta {direction} {asset}, leva {leverage}, {whole}")

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
