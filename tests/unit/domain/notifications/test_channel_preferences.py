from uuid import uuid4

import pytest

from autotrading.domain.notifications.channel_preferences import ChannelPreferences
from autotrading.domain.notifications.errors import AccountEventWithoutFlowExceptionError
from autotrading.domain.notifications.notification_channel import NO_CHANNEL, NotificationChannel
from autotrading.domain.notifications.notification_event import NotificationEvent
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned

ANNA = TenantId.new()
ALFA, BETA = uuid4(), uuid4()
SILENT_BY_DEFAULT = frozenset({NotificationEvent.OPENING_REDUCED, NotificationEvent.OPENING_BLOCKED})
TELEGRAM = frozenset({NotificationChannel.TELEGRAM})
EMAIL = frozenset({NotificationChannel.EMAIL})
BOTH = frozenset({NotificationChannel.TELEGRAM, NotificationChannel.EMAIL})


def preferences() -> ChannelPreferences:
    return ChannelPreferences.of(ANNA)


def test_the_preferences_belong_to_a_tenant() -> None:
    assert isinstance(preferences(), TenantOwned)
    assert preferences().tenant_id == ANNA


@pytest.mark.parametrize("event", list(NotificationEvent))
def test_without_a_choice_the_risk_decisions_are_silent_and_every_other_event_goes_to_telegram(
    event: NotificationEvent,
) -> None:
    expected = NO_CHANNEL if event in SILENT_BY_DEFAULT else TELEGRAM

    assert preferences().channels_for(event, None) == expected
    assert preferences().channels_for(event, ALFA) == expected


def test_the_general_choice_counts_for_every_flow_and_for_the_account() -> None:
    chosen = preferences().choosing(NotificationEvent.CYCLE_FAILED, EMAIL)

    assert chosen.channels_for(NotificationEvent.CYCLE_FAILED, ALFA) == EMAIL
    assert chosen.channels_for(NotificationEvent.CYCLE_FAILED, None) == EMAIL
    assert chosen.channels_for(NotificationEvent.POSITION_OPENED, ALFA) == TELEGRAM


def test_a_new_choice_replaces_the_previous_one() -> None:
    chosen = preferences().choosing(NotificationEvent.CYCLE_FAILED, EMAIL)

    again = chosen.choosing(NotificationEvent.CYCLE_FAILED, BOTH)

    assert again.channels_for(NotificationEvent.CYCLE_FAILED, None) == BOTH


def test_no_channel_chosen_is_a_choice_and_not_the_default() -> None:
    chosen = preferences().choosing(NotificationEvent.CYCLE_FAILED, NO_CHANNEL)

    assert chosen.channels_for(NotificationEvent.CYCLE_FAILED, None) == NO_CHANNEL
    assert chosen.choices == {NotificationEvent.CYCLE_FAILED: NO_CHANNEL}


def test_choosing_leaves_the_preferences_it_starts_from_as_they_were() -> None:
    initial = preferences()

    initial.choosing(NotificationEvent.CYCLE_FAILED, EMAIL)

    assert initial == preferences()


def test_the_exception_of_a_flow_counts_for_that_flow_only() -> None:
    chosen = preferences().choosing(NotificationEvent.POSITION_OPENED, NO_CHANNEL)

    excepted = chosen.excepting(ALFA, NotificationEvent.POSITION_OPENED, TELEGRAM)

    assert excepted.channels_for(NotificationEvent.POSITION_OPENED, ALFA) == TELEGRAM
    assert excepted.channels_for(NotificationEvent.POSITION_OPENED, BETA) == NO_CHANNEL
    assert excepted.exceptions_of(ALFA) == {NotificationEvent.POSITION_OPENED: TELEGRAM}
    assert excepted.exceptions_of(BETA) == {}


def test_an_exception_without_channels_silences_the_flow() -> None:
    excepted = preferences().excepting(ALFA, NotificationEvent.POSITION_OPENED, NO_CHANNEL)

    assert excepted.channels_for(NotificationEvent.POSITION_OPENED, ALFA) == NO_CHANNEL
    assert excepted.channels_for(NotificationEvent.POSITION_OPENED, BETA) == TELEGRAM


def test_an_exception_removed_leaves_the_flow_to_the_general_choice() -> None:
    excepted = preferences().excepting(ALFA, NotificationEvent.POSITION_OPENED, EMAIL)
    excepted = excepted.excepting(ALFA, NotificationEvent.CYCLE_FAILED, NO_CHANNEL)

    removed = excepted.without_exception(ALFA, NotificationEvent.POSITION_OPENED)

    assert removed.channels_for(NotificationEvent.POSITION_OPENED, ALFA) == TELEGRAM
    assert removed.exceptions_of(ALFA) == {NotificationEvent.CYCLE_FAILED: NO_CHANNEL}


def test_removing_the_last_exception_of_a_flow_forgets_the_flow() -> None:
    excepted = preferences().excepting(ALFA, NotificationEvent.POSITION_OPENED, EMAIL)

    removed = excepted.without_exception(ALFA, NotificationEvent.POSITION_OPENED)

    assert removed == preferences()


def test_removing_an_exception_that_is_not_there_changes_nothing() -> None:
    assert preferences().without_exception(ALFA, NotificationEvent.POSITION_OPENED) == preferences()


@pytest.mark.parametrize("event", [event for event in NotificationEvent if not event.of_flow])
def test_an_event_of_the_account_has_no_exception_for_a_flow(event: NotificationEvent) -> None:
    with pytest.raises(AccountEventWithoutFlowExceptionError) as raised:
        preferences().excepting(ALFA, event, NO_CHANNEL)

    assert str(raised.value) == f"{event.value} è un evento del conto: segue la scelta generale"
    assert raised.value.details == {"event": event.value}
    assert raised.value.status_code == 400


def test_the_general_choices_list_every_type_of_event_in_order() -> None:
    chosen = preferences().choosing(NotificationEvent.CYCLE_FAILED, EMAIL)

    general = chosen.general_choices()

    assert list(general) == list(NotificationEvent)
    assert general[NotificationEvent.CYCLE_FAILED] == EMAIL
    assert general[NotificationEvent.OPENING_BLOCKED] == NO_CHANNEL


def test_the_flows_with_exceptions_are_listed() -> None:
    excepted = preferences().excepting(BETA, NotificationEvent.POSITION_OPENED, EMAIL)

    assert excepted.flows_with_exceptions() == (BETA,)
    assert preferences().flows_with_exceptions() == ()


def test_the_choices_read_back_are_kept_as_given() -> None:
    restored = ChannelPreferences(
        ANNA,
        {NotificationEvent.CYCLE_FAILED: EMAIL},
        {ALFA: {NotificationEvent.POSITION_OPENED: BOTH}},
    )

    assert restored.choices == {NotificationEvent.CYCLE_FAILED: EMAIL}
    assert restored.exceptions == {ALFA: {NotificationEvent.POSITION_OPENED: BOTH}}
