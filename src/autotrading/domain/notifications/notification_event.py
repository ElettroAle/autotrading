from enum import StrEnum


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
    UNATTRIBUTABLE_MOVEMENT = "movimento non attribuibile"
    RECONCILIATION_ALARM = "allarme di riconciliazione"
    CASH_OUT = "incasso eseguito"
    # The scope of an emergency closing may hold several flows of the account at once (R3.2.3).
    EMERGENCY_CLOSING = "chiusura di emergenza eseguita"

    @property
    def of_flow(self) -> bool:
        return self not in _OF_ACCOUNT

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
        NotificationEvent.UNATTRIBUTABLE_MOVEMENT,
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
