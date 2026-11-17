from enum import StrEnum

# The icons that tell at a glance what happened (R3.5.4); the variation selector asks for the emoji form of a symbol.
OPENING_ICON = "\U0001f7e2"
PROFIT_ICON = "\u2705"
LOSS_ICON = "\U0001f53b"
STOP_LOSS_ICON = "\U0001f6d1"
TAKE_PROFIT_ICON = "\U0001f3af"
WARNING_ICON = "\u26a0\ufe0f"
PAUSE_ICON = "\u23f8\ufe0f"
ALARM_ICON = "\U0001f6a8"


class NotificationEvent(StrEnum):
    """The types of event told to the user, by the name the user chooses their channels by (R1.8.2, R3.5.1, R3.5.3).

    An event belongs to a flow, or to the account when no single flow explains it.
    """

    POSITION_OPENED = "apertura di una posizione"
    POSITION_CLOSED = "chiusura di una posizione"
    STOP_LOSS = "stop loss attivato"
    TAKE_PROFIT = "take profit attivato"
    LIQUIDATION = "liquidazione di una posizione"
    CYCLE_FAILED = "ciclo fallito"
    ORDER_REJECTED = "ordine rifiutato"
    FLOW_PAUSED = "pausa automatica di un flusso"
    MAXIMUM_LOSS = "perdita massima raggiunta"
    OPENING_REDUCED = "decisione ridotta dal rischio"
    OPENING_BLOCKED = "decisione bloccata dal rischio"
    UNATTRIBUTABLE_POSITION = "posizione non attribuibile"
    UNATTRIBUTABLE_FILL = "esecuzione non attribuibile"
    RECONCILIATION_ALARM = "allarme di riconciliazione"
    CASH_OUT = "incasso eseguito"
    # The scope of an emergency closing may hold several flows of the account at once (R3.2.3).
    EMERGENCY_CLOSING = "chiusura di emergenza eseguita"

    @property
    def of_flow(self) -> bool:
        return self not in _OF_ACCOUNT

    @property
    def icon(self) -> str:
        """The icon of the type; a closing without a reason of its own tells its outcome instead (R3.5.4)."""
        return _ICONS[self]

    @classmethod
    def of_closing(cls, reason: str) -> NotificationEvent:
        """The event a closing is, by the reason its flow gives: the closings the exchange makes by a protection or a
        liquidation are events of their own, told once with their reason (R3.5.1).
        """
        return _CLOSINGS_OF_THEIR_OWN.get(reason, cls.POSITION_CLOSED)


_OF_ACCOUNT = frozenset(
    {
        NotificationEvent.UNATTRIBUTABLE_POSITION,
        NotificationEvent.UNATTRIBUTABLE_FILL,
        NotificationEvent.RECONCILIATION_ALARM,
        NotificationEvent.EMERGENCY_CLOSING,
    }
)
# The reasons of closing as the flows write them in their history (R1.7.2, R3.1.2, R3.5.1).
_CLOSINGS_OF_THEIR_OWN = {
    "stop loss": NotificationEvent.STOP_LOSS,
    "take profit": NotificationEvent.TAKE_PROFIT,
    "liquidazione": NotificationEvent.LIQUIDATION,
}
# Every event of R3.5.1 the requirement gives no icon takes the one of its family (ADR
# notifica-strutturata-con-icona-titolo-e-valori).
_ICONS = {
    NotificationEvent.POSITION_OPENED: OPENING_ICON,
    NotificationEvent.POSITION_CLOSED: PROFIT_ICON,
    NotificationEvent.STOP_LOSS: STOP_LOSS_ICON,
    NotificationEvent.TAKE_PROFIT: TAKE_PROFIT_ICON,
    NotificationEvent.LIQUIDATION: LOSS_ICON,
    NotificationEvent.CYCLE_FAILED: WARNING_ICON,
    NotificationEvent.ORDER_REJECTED: WARNING_ICON,
    NotificationEvent.FLOW_PAUSED: PAUSE_ICON,
    NotificationEvent.MAXIMUM_LOSS: PAUSE_ICON,
    NotificationEvent.OPENING_REDUCED: WARNING_ICON,
    NotificationEvent.OPENING_BLOCKED: WARNING_ICON,
    NotificationEvent.UNATTRIBUTABLE_POSITION: ALARM_ICON,
    NotificationEvent.UNATTRIBUTABLE_FILL: ALARM_ICON,
    NotificationEvent.RECONCILIATION_ALARM: ALARM_ICON,
    NotificationEvent.CASH_OUT: PROFIT_ICON,
    NotificationEvent.EMERGENCY_CLOSING: ALARM_ICON,
}
