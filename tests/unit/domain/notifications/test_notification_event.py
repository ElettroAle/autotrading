import pytest

from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.notifications.notification_event import NotificationEvent

OF_ACCOUNT = frozenset(
    {
        NotificationEvent.UNATTRIBUTABLE_POSITION,
        NotificationEvent.UNATTRIBUTABLE_FILL,
        NotificationEvent.UNATTRIBUTABLE_MOVEMENT,
        NotificationEvent.RECONCILIATION_ALARM,
        NotificationEvent.EMERGENCY_CLOSING,
    }
)
TOLD_AS_THEIR_REASON = frozenset({CloseReason.STOP_LOSS, CloseReason.TAKE_PROFIT, CloseReason.LIQUIDATION})


def test_each_type_of_event_has_the_name_the_user_chooses_its_channels_by() -> None:
    assert [event.value for event in NotificationEvent] == [
        "apertura di una posizione",
        "chiusura di una posizione",
        "stop loss attivato",
        "take profit attivato",
        "liquidazione di una posizione",
        "ciclo fallito",
        "ordine rifiutato",
        "pausa automatica di un flusso",
        "perdita massima raggiunta",
        "decisione ridotta dal rischio",
        "decisione bloccata dal rischio",
        "posizione non attribuibile",
        "esecuzione non attribuibile",
        "movimento non attribuibile",
        "allarme di riconciliazione",
        "incasso eseguito",
        "chiusura di emergenza eseguita",
    ]


@pytest.mark.parametrize("event", sorted(OF_ACCOUNT))
def test_the_events_of_the_account_belong_to_no_flow(event: NotificationEvent) -> None:
    assert not event.of_flow


@pytest.mark.parametrize("event", [event for event in NotificationEvent if event not in OF_ACCOUNT])
def test_every_other_event_belongs_to_a_flow(event: NotificationEvent) -> None:
    assert event.of_flow


@pytest.mark.parametrize(
    ("reason", "event"),
    [
        (CloseReason.STOP_LOSS, NotificationEvent.STOP_LOSS),
        (CloseReason.TAKE_PROFIT, NotificationEvent.TAKE_PROFIT),
        (CloseReason.LIQUIDATION, NotificationEvent.LIQUIDATION),
    ],
)
def test_a_closing_by_a_protection_or_a_liquidation_is_an_event_of_its_own(
    reason: CloseReason, event: NotificationEvent
) -> None:
    assert NotificationEvent.of_closing(reason.value) is event


@pytest.mark.parametrize("reason", [reason for reason in CloseReason if reason not in TOLD_AS_THEIR_REASON])
def test_every_other_closing_is_the_closing_of_a_position(reason: CloseReason) -> None:
    assert NotificationEvent.of_closing(reason.value) is NotificationEvent.POSITION_CLOSED
