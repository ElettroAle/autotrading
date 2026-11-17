from uuid import uuid4

import pytest

from autotrading.domain.notifications.channel_preferences import ChannelPreferences
from autotrading.domain.notifications.errors import AccountEventWithoutFlowExceptionError
from autotrading.domain.notifications.notification_channel import NotificationChannel
from autotrading.domain.notifications.notification_event import NotificationEvent
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned

ANNA = TenantId.new()
ALFA, BETA = uuid4(), uuid4()
SILENT_BY_DEFAULT = frozenset({NotificationEvent.OPENING_REDUCED, NotificationEvent.OPENING_BLOCKED})


def preferences() -> ChannelPreferences:
    return ChannelPreferences.of(ANNA)


def test_the_preferences_belong_to_a_tenant() -> None:
    assert isinstance(preferences(), TenantOwned)
    assert preferences().tenant_id == ANNA


@pytest.mark.parametrize("event", list(NotificationEvent))
def test_without_a_choice_the_risk_decisions_are_silent_and_every_other_event_goes_to_telegram(
    event: NotificationEvent,
) -> None:
    expected = NotificationChannel.NONE if event in SILENT_BY_DEFAULT else NotificationChannel.TELEGRAM

    assert preferences().channel_for(event, None) is expected
    assert preferences().channel_for(event, ALFA) is expected


def test_the_general_choice_counts_for_every_flow_and_for_the_account() -> None:
    chosen = preferences().choosing(NotificationEvent.CYCLE_FAILED, NotificationChannel.EMAIL)

    assert chosen.channel_for(NotificationEvent.CYCLE_FAILED, ALFA) is NotificationChannel.EMAIL
    assert chosen.channel_for(NotificationEvent.CYCLE_FAILED, None) is NotificationChannel.EMAIL
    assert chosen.channel_for(NotificationEvent.POSITION_OPENED, ALFA) is NotificationChannel.TELEGRAM


def test_a_new_choice_replaces_the_previous_one() -> None:
    chosen = preferences().choosing(NotificationEvent.CYCLE_FAILED, NotificationChannel.EMAIL)

    again = chosen.choosing(NotificationEvent.CYCLE_FAILED, NotificationChannel.BOTH)

    assert again.channel_for(NotificationEvent.CYCLE_FAILED, None) is NotificationChannel.BOTH


def test_choosing_leaves_the_preferences_it_starts_from_as_they_were() -> None:
    initial = preferences()

    initial.choosing(NotificationEvent.CYCLE_FAILED, NotificationChannel.EMAIL)

    assert initial == preferences()


def test_the_exception_of_a_flow_counts_for_that_flow_only() -> None:
    chosen = preferences().choosing(NotificationEvent.POSITION_OPENED, NotificationChannel.NONE)

    excepted = chosen.excepting(ALFA, NotificationEvent.POSITION_OPENED, NotificationChannel.TELEGRAM)

    assert excepted.channel_for(NotificationEvent.POSITION_OPENED, ALFA) is NotificationChannel.TELEGRAM
    assert excepted.channel_for(NotificationEvent.POSITION_OPENED, BETA) is NotificationChannel.NONE
    assert excepted.exceptions_of(ALFA) == {NotificationEvent.POSITION_OPENED: NotificationChannel.TELEGRAM}
    assert excepted.exceptions_of(BETA) == {}


def test_an_exception_removed_leaves_the_flow_to_the_general_choice() -> None:
    excepted = preferences().excepting(ALFA, NotificationEvent.POSITION_OPENED, NotificationChannel.EMAIL)
    excepted = excepted.excepting(ALFA, NotificationEvent.CYCLE_FAILED, NotificationChannel.NONE)

    removed = excepted.without_exception(ALFA, NotificationEvent.POSITION_OPENED)

    assert removed.channel_for(NotificationEvent.POSITION_OPENED, ALFA) is NotificationChannel.TELEGRAM
    assert removed.exceptions_of(ALFA) == {NotificationEvent.CYCLE_FAILED: NotificationChannel.NONE}


def test_removing_the_last_exception_of_a_flow_forgets_the_flow() -> None:
    excepted = preferences().excepting(ALFA, NotificationEvent.POSITION_OPENED, NotificationChannel.EMAIL)

    removed = excepted.without_exception(ALFA, NotificationEvent.POSITION_OPENED)

    assert removed == preferences()


def test_removing_an_exception_that_is_not_there_changes_nothing() -> None:
    assert preferences().without_exception(ALFA, NotificationEvent.POSITION_OPENED) == preferences()


@pytest.mark.parametrize("event", [event for event in NotificationEvent if not event.of_flow])
def test_an_event_of_the_account_has_no_exception_for_a_flow(event: NotificationEvent) -> None:
    with pytest.raises(AccountEventWithoutFlowExceptionError) as raised:
        preferences().excepting(ALFA, event, NotificationChannel.NONE)

    assert str(raised.value) == f"{event.value} è un evento del conto: segue la scelta generale"
    assert raised.value.details == {"event": event.value}
    assert raised.value.status_code == 400


def test_the_general_choices_list_every_type_of_event_in_order() -> None:
    chosen = preferences().choosing(NotificationEvent.CYCLE_FAILED, NotificationChannel.EMAIL)

    general = chosen.general_choices()

    assert list(general) == list(NotificationEvent)
    assert general[NotificationEvent.CYCLE_FAILED] is NotificationChannel.EMAIL
    assert general[NotificationEvent.OPENING_BLOCKED] is NotificationChannel.NONE


def test_the_flows_with_exceptions_are_listed() -> None:
    excepted = preferences().excepting(BETA, NotificationEvent.POSITION_OPENED, NotificationChannel.EMAIL)

    assert excepted.flows_with_exceptions() == (BETA,)
    assert preferences().flows_with_exceptions() == ()


def test_the_choices_read_back_are_kept_as_given() -> None:
    restored = ChannelPreferences(
        ANNA,
        {NotificationEvent.CYCLE_FAILED: NotificationChannel.EMAIL},
        {ALFA: {NotificationEvent.POSITION_OPENED: NotificationChannel.BOTH}},
    )

    assert restored.choices == {NotificationEvent.CYCLE_FAILED: NotificationChannel.EMAIL}
    assert restored.exceptions == {ALFA: {NotificationEvent.POSITION_OPENED: NotificationChannel.BOTH}}
