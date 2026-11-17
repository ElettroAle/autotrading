from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.italian_text import money_text
from autotrading.domain.notifications.errors import InvalidNotificationError
from autotrading.domain.notifications.notification_event import NotificationEvent

# An opening is told by the value it put on the market, in whole units: the cents add nothing to the event.
WHOLE_UNIT = Decimal(1)
# The details of an event follow its first comma: the subject of an email tells the event alone (R3.5.2).
DETAILS_SEPARATOR = ", "
TEST_EMAIL_SUBJECT = "AutoTrading: prova delle notifiche"
EMERGENCY_CLOSING_SUBJECT = "chiusura di emergenza"


@dataclass(frozen=True, slots=True)
class Amount:
    value: Decimal
    currency: str

    def __str__(self) -> str:
        return f"{money_text(self.value)} {self.currency}"


@dataclass(frozen=True, slots=True)
class Notification:
    """An event of a flow or an account, with its essential values and never a credential (R1.8.2), and the type of
    the event (R3.5.1); the test notification is no event.
    """

    subject: str
    event: str
    headline: str | None = None
    kind: NotificationEvent | None = None

    def __post_init__(self) -> None:
        if not self.subject.strip():
            raise InvalidNotificationError

    @property
    def text(self) -> str:
        return f"{self.subject}: {self.event}"

    @property
    def flow(self) -> str | None:
        """The flow the event belongs to; none for an event of the account and for the test notification."""
        if self.kind is None or not self.kind.of_flow:
            return None
        return self.subject

    @property
    def email_subject(self) -> str:
        """The subject of the email that carries the notification; its text is the same as on the chat (R3.5.2)."""
        if self.headline is not None:
            return self.headline
        event, *_ = self.event.split(DETAILS_SEPARATOR, 1)
        return f"{self.subject}: {event}"

    @classmethod
    def test(cls) -> Notification:
        return cls("notifica di prova", "le notifiche dei tuoi flussi arrivano qui", TEST_EMAIL_SUBJECT)

    @classmethod
    def position_opened(cls, flow: str, asset: str, direction: str, leverage: int, value: Amount) -> Notification:
        whole = Amount(value.value.quantize(WHOLE_UNIT), value.currency)
        return cls(
            flow, f"aperta {direction} {asset}, leva {leverage}, {whole}", kind=NotificationEvent.POSITION_OPENED
        )

    @classmethod
    def position_closed(cls, flow: str, asset: str, pnl: Amount, reason: str) -> Notification:
        """One notification for the closing, with the reason when the closing is an event of its own (R3.5.1)."""
        kind = NotificationEvent.of_closing(reason)
        if kind is NotificationEvent.LIQUIDATION:
            return cls.position_liquidated(flow, asset, pnl)
        if kind is NotificationEvent.POSITION_CLOSED:
            return cls(flow, f"chiusa {asset}, PnL {pnl}", kind=kind)
        return cls(flow, f"chiusa {asset} per {reason}, PnL {pnl}", kind=kind)

    @classmethod
    def position_liquidated(cls, flow: str, asset: str, pnl: Amount) -> Notification:
        return cls(flow, f"liquidata {asset}, PnL {pnl}", kind=NotificationEvent.LIQUIDATION)

    @classmethod
    def cycle_failed(cls, flow: str, message: str) -> Notification:
        return cls(flow, f"ciclo fallito, {message}", kind=NotificationEvent.CYCLE_FAILED)

    @classmethod
    def order_rejected(cls, flow: str, message: str) -> Notification:
        return cls(flow, f"ordine rifiutato, {message}", kind=NotificationEvent.ORDER_REJECTED)

    @classmethod
    def flow_paused(cls, flow: str, reason: str) -> Notification:
        return cls(flow, f"in pausa, {reason}", kind=NotificationEvent.FLOW_PAUSED)

    @classmethod
    def openings_suspended(cls, flow: str, reason: str) -> Notification:
        return cls(flow, f"aperture sospese, {reason}", kind=NotificationEvent.MAXIMUM_LOSS)

    @classmethod
    def opening_reduced(cls, flow: str, asset: str, requested: Amount, approved: Amount) -> Notification:
        """The margin the agent asked for and the one the risk check let through (R3.5.1)."""
        event = f"apertura {asset} ridotta da {money_text(requested.value)} a {approved}"
        return cls(flow, event, kind=NotificationEvent.OPENING_REDUCED)

    @classmethod
    def opening_blocked(cls, flow: str, asset: str, cause: str) -> Notification:
        return cls(flow, f"apertura {asset} non eseguita, {cause}", kind=NotificationEvent.OPENING_BLOCKED)

    @classmethod
    def unattributable_position(cls, account: str, asset: str) -> Notification:
        return cls(account, f"posizione non attribuibile su {asset}", kind=NotificationEvent.UNATTRIBUTABLE_POSITION)

    @classmethod
    def unattributable_fill(cls, account: str, asset: str) -> Notification:
        return cls(account, f"esecuzione non attribuibile su {asset}", kind=NotificationEvent.UNATTRIBUTABLE_FILL)

    @classmethod
    def unattributable_movement(cls, account: str, amount: Amount) -> Notification:
        return cls(account, f"movimento non attribuibile di {amount}", kind=NotificationEvent.UNATTRIBUTABLE_MOVEMENT)

    @classmethod
    def reconciliation_alarm(cls, account: str, read: Amount, expected: Amount) -> Notification:
        event = f"allarme di riconciliazione, saldo {read} invece di {expected}"
        return cls(account, event, kind=NotificationEvent.RECONCILIATION_ALARM)

    @classmethod
    def cash_out_done(cls, flow: str, freed: Amount) -> Notification:
        return cls(flow, f"incassati {freed}", kind=NotificationEvent.CASH_OUT)

    @classmethod
    def emergency_closing_done(cls, positions_closed: int, paused_flows: Sequence[str]) -> Notification:
        """One notification for the whole emergency closing: its positions are not told one by one (R3.5.1)."""
        closed = (
            f"{positions_closed} posizione chiusa" if positions_closed == 1 else f"{positions_closed} posizioni chiuse"
        )
        paused = f"{', '.join(paused_flows)} in pausa" if paused_flows else "nessun flusso in pausa"
        return cls(EMERGENCY_CLOSING_SUBJECT, f"{closed}, {paused}", kind=NotificationEvent.EMERGENCY_CLOSING)
