from collections.abc import Sequence
from dataclasses import dataclass, replace
from decimal import Decimal

from autotrading.domain.italian_text import money_text
from autotrading.domain.notifications.errors import InvalidNotificationError
from autotrading.domain.notifications.flow_status import FlowStatusLine
from autotrading.domain.notifications.notification_event import LOSS_ICON, NotificationEvent

# An opening is told by the value it put on the market, in whole units: the cents add nothing to the event.
WHOLE_UNIT = Decimal(1)
TEST_ICON = "\U0001f514"
TEST_SUBJECT = "AutoTrading"
EMERGENCY_CLOSING_SUBJECT = "chiusura di emergenza"


@dataclass(frozen=True, slots=True)
class Amount:
    value: Decimal
    currency: str

    def __str__(self) -> str:
        return f"{money_text(self.value)} {self.currency}"


@dataclass(frozen=True, slots=True)
class NotificationLine:
    """A value of the event, on a line of its own (R3.5.4)."""

    label: str
    value: str

    def __str__(self) -> str:
        return f"{self.label}: {self.value}"


@dataclass(frozen=True, slots=True)
class Notification:
    """An event of a flow or an account, told by an icon, a title with the flow or account and the event, its values one
    per line and, for a flow, the state of the flow at the bottom (R1.8.2, R3.5.1, R3.5.4); never a credential.

    The same text goes to every channel (ADR notifica-strutturata-con-icona-titolo-e-valori); the test notification is
    no event.
    """

    subject: str
    headline: str
    lines: tuple[NotificationLine, ...]
    event: NotificationEvent | None
    icon: str
    flow_status: FlowStatusLine | None = None

    def __post_init__(self) -> None:
        if not self.subject.strip():
            raise InvalidNotificationError

    @property
    def title(self) -> str:
        """The first line of the message and the subject of its email (R3.5.4)."""
        return f"{self.icon} {self.subject}: {self.headline}"

    def body_lines(self) -> tuple[str, ...]:
        status = () if self.flow_status is None else (self.flow_status.text,)
        return (*(str(line) for line in self.lines), *status)

    @property
    def text(self) -> str:
        body = self.body_lines()
        if not body:
            return self.title
        return "\n".join((self.title, "", *body))

    @property
    def flow(self) -> str | None:
        """The flow the event belongs to; none for an event of the account and for the test notification."""
        if self.event is None or not self.event.of_flow:
            return None
        return self.subject

    def with_flow_status(self, status: FlowStatusLine) -> Notification:
        return replace(self, flow_status=status)

    @classmethod
    def told(
        cls, event: NotificationEvent, subject: str, headline: str, *lines: NotificationLine, icon: str | None = None
    ) -> Notification:
        """The notification of an event, with the icon of its type unless its outcome gives another one."""
        return cls(subject, headline, lines, event, event.icon if icon is None else icon)

    @classmethod
    def test(cls) -> Notification:
        line = NotificationLine("Esito", "le notifiche dei tuoi flussi arrivano qui")
        return cls(TEST_SUBJECT, "prova delle notifiche", (line,), None, TEST_ICON)

    @classmethod
    def position_opened(cls, flow: str, asset: str, direction: str, leverage: int, value: Amount) -> Notification:
        whole = Amount(value.value.quantize(WHOLE_UNIT), value.currency)
        return cls.told(
            NotificationEvent.POSITION_OPENED,
            flow,
            "posizione aperta",
            NotificationLine("Asset", asset),
            NotificationLine("Direzione", direction),
            NotificationLine("Leva", str(leverage)),
            NotificationLine("Valore", str(whole)),
        )

    @classmethod
    def position_closed(cls, flow: str, asset: str, pnl: Amount, reason: str) -> Notification:
        """One notification for the closing, with the reason when the closing is an event of its own (R3.5.1); a
        closing of its own kind tells its outcome by the icon (R3.5.4).
        """
        event = NotificationEvent.of_closing(reason)
        if event is NotificationEvent.LIQUIDATION:
            return cls.position_liquidated(flow, asset, pnl)
        values = (NotificationLine("Asset", asset), NotificationLine("PnL", str(pnl)))
        if event is NotificationEvent.POSITION_CLOSED:
            icon = event.icon if pnl.value > 0 else LOSS_ICON
            return cls.told(NotificationEvent.POSITION_CLOSED, flow, "posizione chiusa", *values, icon=icon)
        return cls.told(event, flow, f"chiusa per {reason}", *values)

    @classmethod
    def position_liquidated(cls, flow: str, asset: str, pnl: Amount) -> Notification:
        return cls.told(
            NotificationEvent.LIQUIDATION,
            flow,
            "posizione liquidata",
            NotificationLine("Asset", asset),
            NotificationLine("PnL", str(pnl)),
        )

    @classmethod
    def cycle_failed(cls, flow: str, message: str) -> Notification:
        return cls.told(NotificationEvent.CYCLE_FAILED, flow, "ciclo fallito", NotificationLine("Errore", message))

    @classmethod
    def order_rejected(cls, flow: str, message: str) -> Notification:
        return cls.told(NotificationEvent.ORDER_REJECTED, flow, "ordine rifiutato", NotificationLine("Errore", message))

    @classmethod
    def flow_paused(cls, flow: str, reason: str) -> Notification:
        return cls.told(NotificationEvent.FLOW_PAUSED, flow, "in pausa", NotificationLine("Motivo", reason))

    @classmethod
    def openings_suspended(cls, flow: str, reason: str) -> Notification:
        return cls.told(NotificationEvent.MAXIMUM_LOSS, flow, "aperture sospese", NotificationLine("Motivo", reason))

    @classmethod
    def opening_reduced(cls, flow: str, asset: str, requested: Amount, approved: Amount) -> Notification:
        """The margin the agent asked for and the one the risk check let through (R3.5.1)."""
        return cls.told(
            NotificationEvent.OPENING_REDUCED,
            flow,
            "apertura ridotta",
            NotificationLine("Asset", asset),
            NotificationLine("Margine richiesto", str(requested)),
            NotificationLine("Margine approvato", str(approved)),
        )

    @classmethod
    def opening_blocked(cls, flow: str, asset: str, cause: str) -> Notification:
        return cls.told(
            NotificationEvent.OPENING_BLOCKED,
            flow,
            "apertura non eseguita",
            NotificationLine("Asset", asset),
            NotificationLine("Motivo", cause),
        )

    @classmethod
    def unattributable_position(cls, account: str, asset: str) -> Notification:
        return cls.told(
            NotificationEvent.UNATTRIBUTABLE_POSITION,
            account,
            "posizione non attribuibile",
            NotificationLine("Asset", asset),
        )

    @classmethod
    def unattributable_fill(cls, account: str, asset: str) -> Notification:
        return cls.told(
            NotificationEvent.UNATTRIBUTABLE_FILL,
            account,
            "esecuzione non attribuibile",
            NotificationLine("Asset", asset),
        )

    @classmethod
    def unattributable_movement(cls, account: str, amount: Amount) -> Notification:
        return cls.told(
            NotificationEvent.UNATTRIBUTABLE_MOVEMENT,
            account,
            "movimento non attribuibile",
            NotificationLine("Importo", str(amount)),
        )

    @classmethod
    def reconciliation_alarm(cls, account: str, read: Amount, expected: Amount) -> Notification:
        return cls.told(
            NotificationEvent.RECONCILIATION_ALARM,
            account,
            "allarme di riconciliazione",
            NotificationLine("Saldo letto", str(read)),
            NotificationLine("Saldo atteso", str(expected)),
        )

    @classmethod
    def cash_out_done(cls, flow: str, freed: Amount) -> Notification:
        return cls.told(NotificationEvent.CASH_OUT, flow, "incasso eseguito", NotificationLine("Importo", str(freed)))

    @classmethod
    def emergency_closing_done(cls, positions_closed: int, paused_flows: Sequence[str]) -> Notification:
        """One notification for the whole emergency closing: its positions are not told one by one (R3.5.1)."""
        return cls.told(
            NotificationEvent.EMERGENCY_CLOSING,
            EMERGENCY_CLOSING_SUBJECT,
            "eseguita",
            NotificationLine("Posizioni chiuse", str(positions_closed)),
            NotificationLine("Flussi in pausa", ", ".join(paused_flows) or "nessuno"),
        )
