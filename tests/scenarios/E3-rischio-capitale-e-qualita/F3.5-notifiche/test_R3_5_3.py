"""R3.5.3: the channel of every type of event, with the exceptions of a flow, on the cycles the worker runs and the use
cases of the API with the fake adapters (ADR canali-delle-notifiche-per-tipo-di-evento).
"""

from dataclasses import replace
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.adapters.inbound.api.notification_channels import CHANNEL_NAMES, warning_of
from autotrading.application.notifications.choose_notification_channel import ChooseNotificationChannelCommand
from autotrading.application.notifications.get_notification_channels import EventChannel
from autotrading.application.notifications.link_chat import LinkChatCommand
from autotrading.application.notifications.remove_flow_channel_exception import RemoveFlowChannelExceptionCommand
from autotrading.application.notifications.set_flow_channel_exception import SetFlowChannelExceptionCommand
from autotrading.application.notifications.set_notification_email import SetNotificationEmailCommand
from autotrading.domain.errors import AutotradingError
from autotrading.domain.notifications.notification_channel import NotificationChannel
from autotrading.domain.notifications.notification_event import NotificationEvent
from tests.fakes.cycles import FakeTransientError
from tests.support.decision_steps import answer, opening
from tests.support.flow_cycles import FlowCycles
from tests.support.notifications import chat_named
from tests.support.steps import quoted

scenarios("E3-rischio-capitale-e-qualita/F3.5-notifiche/R3.5.3-scelta-dei-canali-delle-notifiche.feature")

CAPITAL = Decimal(1000)
MID_PRICE = Decimal(100000)
OPENING_FEE = Decimal("0.07")
FAILURE = "modello non raggiungibile"
FAILED_CYCLE = "ciclo fallito"
# Two flows of the same account open on different assets: an asset belongs to one flow of the account (R1.1.1).
ASSET_OF = {"alfa": "BTC", "beta": "ETH"}


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def outcome() -> dict[str, object]:
    """What the last request answered (the refusal, the channels read) and the start of the notice the event tells."""
    return {}


def channel_by_name(name: str) -> NotificationChannel:
    """The channel by the word the interface shows the user (R3.5.3)."""
    [channel] = [channel for channel, shown in CHANNEL_NAMES.items() if shown == name]
    return channel


def choose(flow_cycles: FlowCycles, user: str, channel: str, event: str) -> None:
    command = ChooseNotificationChannelCommand(NotificationEvent(event), channel_by_name(channel))
    flow_cycles.platform.use_cases_of(user).choose_notification_channel.execute(command)


def set_exception(flow_cycles: FlowCycles, user: str, flow: str, event: str, channel: str) -> None:
    command = SetFlowChannelExceptionCommand(
        flow_cycles.flow(flow).id.value, NotificationEvent(event), channel_by_name(channel)
    )
    flow_cycles.platform.use_cases_of(user).set_flow_channel_exception.execute(command)


def fail_cycle(flow_cycles: FlowCycles, outcome: dict[str, object], flow: str) -> None:
    outcome["notice"] = f"{flow}: {FAILED_CYCLE}"
    flow_cycles.model.failure = FakeTransientError(FAILURE)
    flow_cycles.run(flow)


def open_position(flow_cycles: FlowCycles, outcome: dict[str, object], flow: str) -> None:
    outcome["notice"] = opening_of(flow)
    flow_cycles.platform.order_exchange.fill_at = (MID_PRICE, OPENING_FEE)
    answer(flow_cycles, opening(ASSET_OF[flow], quota=0.05))
    flow_cycles.run(flow)


def chat_messages(flow_cycles: FlowCycles, chat: str) -> list[str]:
    return flow_cycles.platform.messenger.received_by(chat_named(chat))


def emails_to(flow_cycles: FlowCycles, address: str) -> list[str]:
    return [email.text for email in flow_cycles.platform.mailer.received_by(address)]


def opening_of(flow: str) -> str:
    return f"{flow}: aperta"


def notices(outcome: dict[str, object], messages: list[str]) -> list[str]:
    """The messages that tell the event of the scenario, by the start of their text."""
    notice = outcome["notice"]
    assert isinstance(notice, str)
    return [message for message in messages if message.startswith(notice)]


def general_channel(outcome: dict[str, object], event: str) -> EventChannel:
    channels = outcome["channels"]
    assert isinstance(channels, tuple)
    [found] = [each for each in channels if isinstance(each, EventChannel) and each.event == NotificationEvent(event)]
    return found


# Given


@given(quoted('che "{user}" ha la chat "{chat}" collegata e l\'indirizzo "{address}" per le notifiche'))
def chat_and_address(flow_cycles: FlowCycles, user: str, chat: str, address: str) -> None:
    platform = flow_cycles.platform
    code = platform.use_cases_of(user).request_link_code.execute().code
    platform.link_chat().execute(LinkChatCommand(chat_named(chat), code))
    platform.use_cases_of(user).set_notification_email.execute(SetNotificationEmailCommand(address))
    # The confirmation of the link is R1.8.1: the scenarios read only what the flows notify.
    platform.messenger.sent.clear()


@given(quoted('che "{user}" ha i flussi "{first}" e "{second}"'))
def two_flows(flow_cycles: FlowCycles, user: str, first: str, second: str) -> None:
    for flow in (first, second):
        flow_cycles.add_flow(user, flow, assets=(ASSET_OF[flow],))
        flow_cycles.reconfigure(flow, lambda configuration: replace(configuration, allocated_capital=CAPITAL / 2))


@given(quoted('che "{user}" sceglie il canale "{channel}" per "{event}"'))
def channel_chosen(flow_cycles: FlowCycles, user: str, channel: str, event: str) -> None:
    choose(flow_cycles, user, channel, event)


@given(quoted('che "{user}" imposta per il flusso "{flow}" l\'eccezione "{event}" sul canale "{channel}"'))
def exception_set(flow_cycles: FlowCycles, user: str, flow: str, event: str, channel: str) -> None:
    set_exception(flow_cycles, user, flow, event, channel)


@given(quoted('che "{user}" ha tolto l\'eccezione "{event}" del flusso "{flow}"'))
def exception_removed(flow_cycles: FlowCycles, user: str, event: str, flow: str) -> None:
    # The exception was there before the user took it away.
    set_exception(flow_cycles, user, flow, event, CHANNEL_NAMES[NotificationChannel.TELEGRAM])
    command = RemoveFlowChannelExceptionCommand(flow_cycles.flow(flow).id.value, NotificationEvent(event))
    flow_cycles.platform.use_cases_of(user).remove_flow_channel_exception.execute(command)


@given(quoted('che "{user}" non ha una chat Telegram collegata'))
def no_chat(flow_cycles: FlowCycles, user: str) -> None:
    flow_cycles.platform.use_cases_of(user).unlink_chat.execute()


@given(quoted('che "{user}" non ha un indirizzo email per le notifiche'))
def no_address(flow_cycles: FlowCycles, user: str) -> None:
    flow_cycles.platform.use_cases_of(user).remove_notification_email.execute()


# When


@when(quoted('"{user}" apre le Impostazioni delle notifiche senza aver mai scelto'))
def settings_opened(flow_cycles: FlowCycles, outcome: dict[str, object], user: str) -> None:
    outcome["channels"] = flow_cycles.platform.use_cases_of(user).get_notification_channels.execute().events


@when(quoted('un ciclo di "{flow}" fallisce'))
def cycle_fails(flow_cycles: FlowCycles, outcome: dict[str, object], flow: str) -> None:
    fail_cycle(flow_cycles, outcome, flow)


@when(quoted('un ciclo di "{flow}" di "{user}" fallisce'))
def cycle_of_user_fails(flow_cycles: FlowCycles, outcome: dict[str, object], flow: str, user: str) -> None:
    assert flow_cycles.users[flow] == user
    fail_cycle(flow_cycles, outcome, flow)


@when(quoted('"{first}" e "{second}" aprono una posizione ciascuno'))
def both_open(flow_cycles: FlowCycles, outcome: dict[str, object], first: str, second: str) -> None:
    open_position(flow_cycles, outcome, first)
    open_position(flow_cycles, outcome, second)


@when(quoted('"{flow}" apre una posizione'))
def flow_opens(flow_cycles: FlowCycles, outcome: dict[str, object], flow: str) -> None:
    open_position(flow_cycles, outcome, flow)


@when(quoted('"{user}" imposta per il flusso "{flow}" un\'eccezione per "{event}"'))
def account_event_exception(
    flow_cycles: FlowCycles, outcome: dict[str, object], user: str, flow: str, event: str
) -> None:
    try:
        set_exception(flow_cycles, user, flow, event, CHANNEL_NAMES[NotificationChannel.TELEGRAM])
    except AutotradingError as error:
        outcome["refusal"] = error


@when(quoted('"{user}" sceglie il canale "{channel}" per "{event}"'))
def user_chooses(flow_cycles: FlowCycles, user: str, channel: str, event: str) -> None:
    choose(flow_cycles, user, channel, event)


# Then


@then(quoted('il tipo di evento "{event}" ha il canale "{channel}"'))
def event_has_channel(outcome: dict[str, object], event: str, channel: str) -> None:
    assert CHANNEL_NAMES[general_channel(outcome, event).channel] == channel


@then(parsers.re(r'^la chat "(?P<chat>[^"]+)" (?P<verdict>riceve|non riceve) la notifica$'))
def chat_verdict(flow_cycles: FlowCycles, outcome: dict[str, object], chat: str, verdict: str) -> None:
    received = notices(outcome, chat_messages(flow_cycles, chat))
    assert (len(received) == 1) is (verdict == "riceve"), received


@then(parsers.re(r'^"(?P<address>[^"]+)" (?P<verdict>riceve|non riceve) la notifica$'))
def email_verdict(flow_cycles: FlowCycles, outcome: dict[str, object], address: str, verdict: str) -> None:
    received = notices(outcome, emails_to(flow_cycles, address))
    assert (len(received) == 1) is (verdict == "riceve"), received


@then(quoted('la chat "{chat}" riceve la notifica dell\'apertura di "{flow}"'))
def chat_receives_opening(flow_cycles: FlowCycles, chat: str, flow: str) -> None:
    openings = [message for message in chat_messages(flow_cycles, chat) if message.startswith(opening_of(flow))]
    assert len(openings) == 1, chat_messages(flow_cycles, chat)


@then(quoted('la chat "{chat}" non riceve la notifica dell\'apertura di "{flow}"'))
def chat_does_not_receive_opening(flow_cycles: FlowCycles, chat: str, flow: str) -> None:
    assert not [message for message in chat_messages(flow_cycles, chat) if message.startswith(opening_of(flow))]


@then(quoted('la richiesta viene rifiutata con "{reason}"'))
def request_refused(outcome: dict[str, object], reason: str) -> None:
    assert str(outcome.get("refusal")) == reason


@then(quoted('le Impostazioni avvisano accanto a "{event}" con "{warning}"'))
def settings_warn(flow_cycles: FlowCycles, event: str, warning: str) -> None:
    [user] = set(flow_cycles.users.values())
    channels = flow_cycles.platform.use_cases_of(user).get_notification_channels.execute().events
    [found] = [each for each in channels if each.event == NotificationEvent(event)]
    assert [warning_of(missing) for missing in found.missing_links] == [warning]
