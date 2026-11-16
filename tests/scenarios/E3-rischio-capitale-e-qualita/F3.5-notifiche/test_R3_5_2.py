import logging
from dataclasses import replace
from decimal import Decimal

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.notifications.get_notification_email import NotificationEmailSettings
from autotrading.application.notifications.set_notification_email import SetNotificationEmailCommand
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.cycle_record import CycleOutcome
from autotrading.domain.notifications.outbox_message import EMAIL_MESSAGE
from tests.fakes.cycles import FakePermanentError
from tests.fakes.outbox import OutboxState
from tests.support.decision_steps import answer, opening
from tests.support.flow_cycles import FlowCycles
from tests.support.steps import quoted

scenarios("E3-rischio-capitale-e-qualita/F3.5-notifiche/R3.5.2-notifiche-via-email.feature")

CAPITAL = Decimal(1000)
MID_PRICE = Decimal(100000)
OPENING_FEE = Decimal("0.07")
PAUSE_REASON = "credito esaurito"
PAUSED_SUBJECT = "{flow}: in pausa"


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def outcome() -> dict[str, object]:
    """What the last request answered: the refusal, the settings read, or the subject of the expected email."""
    return {}


def indicate(flow_cycles: FlowCycles, user: str, address: str) -> None:
    flow_cycles.platform.use_cases_of(user).set_notification_email.execute(SetNotificationEmailCommand(address))


def pause(flow_cycles: FlowCycles, flow: str, outcome: dict[str, object], reason: str = PAUSE_REASON) -> None:
    flow_cycles.model.failure = FakePermanentError(reason)
    flow_cycles.run(flow)
    outcome["subject"] = PAUSED_SUBJECT.format(flow=flow)


def subjects_received_by(flow_cycles: FlowCycles, address: str) -> list[str]:
    return [email.subject for email in flow_cycles.platform.mailer.received_by(address)]


# Given


@given("che l'installazione ha un servizio di posta configurato")
def mail_service_configured(flow_cycles: FlowCycles) -> None:
    flow_cycles.platform.mail_service.configured = True


@given("che l'installazione non ha un servizio di posta configurato")
def mail_service_missing(flow_cycles: FlowCycles) -> None:
    flow_cycles.platform.mail_service.configured = False


@given(quoted('che "{user}" ha il flusso "{flow}" con il canale email scelto per l\'evento "{event}"'))
def flow_with_email_channel(flow_cycles: FlowCycles, user: str, flow: str, event: str) -> None:
    # The choice of the channels per event is R3.5.3: until then every notification goes to every channel.
    assert event == "pausa automatica di un flusso"
    flow_cycles.add_flow(user, flow)
    flow_cycles.reconfigure(flow, lambda configuration: replace(configuration, allocated_capital=CAPITAL))


@given(quoted('che "{user}" ha indicato l\'indirizzo "{address}"'))
def address_indicated(flow_cycles: FlowCycles, user: str, address: str) -> None:
    indicate(flow_cycles, user, address)


@given(quoted('che "{user}" ha indicato l\'indirizzo "{address}" e il servizio di posta rifiuta gli invii'))
def address_indicated_and_mail_refused(flow_cycles: FlowCycles, user: str, address: str) -> None:
    indicate(flow_cycles, user, address)
    flow_cycles.platform.mailer.accepting = False


# When


@when(quoted('"{user}" indica l\'indirizzo "{address}" per le notifiche'))
def user_indicates(flow_cycles: FlowCycles, outcome: dict[str, object], user: str, address: str) -> None:
    try:
        indicate(flow_cycles, user, address)
    except AutotradingError as error:
        outcome["refusal"] = error


@when(quoted('"{user}" chiede un\'email di prova'))
def user_asks_for_test(flow_cycles: FlowCycles, outcome: dict[str, object], user: str) -> None:
    try:
        flow_cycles.platform.use_cases_of(user).send_test_email.execute()
    except AutotradingError as error:
        outcome["refusal"] = error


@when(quoted('il flusso "{flow}" va in pausa per "{reason}"'))
def flow_paused_for(flow_cycles: FlowCycles, outcome: dict[str, object], flow: str, reason: str) -> None:
    pause(flow_cycles, flow, outcome, reason)


@when(quoted('"{user}" indica l\'indirizzo "{address}" e il flusso "{flow}" va in pausa'))
def address_changed_then_paused(
    flow_cycles: FlowCycles, outcome: dict[str, object], user: str, address: str, flow: str
) -> None:
    indicate(flow_cycles, user, address)
    pause(flow_cycles, flow, outcome)


@when(quoted('"{user}" toglie l\'indirizzo e il flusso "{flow}" va in pausa'))
def address_removed_then_paused(flow_cycles: FlowCycles, outcome: dict[str, object], user: str, flow: str) -> None:
    flow_cycles.platform.use_cases_of(user).remove_notification_email.execute()
    pause(flow_cycles, flow, outcome)


@when(quoted('il flusso "{flow}" di "{user}" va in pausa'))
def flow_of_user_paused(flow_cycles: FlowCycles, outcome: dict[str, object], flow: str, user: str) -> None:
    assert flow_cycles.users[flow] == user
    pause(flow_cycles, flow, outcome)


@when(quoted('un ciclo di "{flow}" produce una notifica destinata all\'email'))
def cycle_notifies(flow_cycles: FlowCycles, flow: str) -> None:
    flow_cycles.platform.order_exchange.fill_at = (MID_PRICE, OPENING_FEE)
    answer(flow_cycles, opening("BTC", quota=0.05, reasoning="r"))
    flow_cycles.run(flow)


@when(quoted('"{user}" apre le Impostazioni delle notifiche'))
def user_opens_settings(flow_cycles: FlowCycles, outcome: dict[str, object], user: str) -> None:
    outcome["settings"] = flow_cycles.platform.use_cases_of(user).get_notification_email.execute()


# Then


@then(quoted('le Impostazioni di "{user}" mostrano l\'indirizzo "{address}"'))
def settings_show(flow_cycles: FlowCycles, user: str, address: str) -> None:
    settings = flow_cycles.platform.use_cases_of(user).get_notification_email.execute()
    assert settings.address is not None
    assert settings.address.value == address


@then(quoted('la richiesta viene rifiutata con "{reason}"'))
def request_refused(outcome: dict[str, object], reason: str) -> None:
    assert str(outcome.get("refusal")) == reason


@then(quoted('"{address}" riceve un\'email con oggetto "{subject}"'))
def receives_subject(flow_cycles: FlowCycles, address: str, subject: str) -> None:
    assert subject in subjects_received_by(flow_cycles, address)


@then(quoted('"{address}" riceve un\'email con oggetto "{subject}" e testo "{text}"'))
def receives_subject_and_text(flow_cycles: FlowCycles, address: str, subject: str, text: str) -> None:
    received = [(email.subject, email.text) for email in flow_cycles.platform.mailer.received_by(address)]
    assert (subject, text) in received, received


@then(quoted('"{address}" riceve l\'email'))
def receives_the_email(flow_cycles: FlowCycles, outcome: dict[str, object], address: str) -> None:
    assert outcome["subject"] in subjects_received_by(flow_cycles, address)


@then(quoted('"{address}" non riceve l\'email'))
def does_not_receive(flow_cycles: FlowCycles, outcome: dict[str, object], address: str) -> None:
    assert outcome["subject"] not in subjects_received_by(flow_cycles, address)
    assert flow_cycles.platform.mailer.received_by(address) == []


@then(quoted('il ciclo di "{flow}" si conclude'))
def cycle_completes(flow_cycles: FlowCycles, flow: str) -> None:
    assert flow_cycles.last_record(flow).outcome is CycleOutcome.COMPLETED
    assert flow_cycles.platform.order_exchange.executions


@then("l'invio fallito è registrato")
def failed_sending_recorded(flow_cycles: FlowCycles, caplog: pytest.LogCaptureFixture) -> None:
    outbox = flow_cycles.platform.outbox
    attempted = [message for message in outbox.in_state(OutboxState.PENDING) if message.integration == EMAIL_MESSAGE]
    assert attempted
    assert all(outbox.attempts[message.id] >= 1 for message in attempted)
    assert "invio dell'email fallito" in [
        record.getMessage()
        for record in caplog.records
        if record.name == "autotrading.notifications" and record.levelno == logging.WARNING
    ]


@then(quoted('la pagina avvisa "{warning}"'))
def page_warns(outcome: dict[str, object], warning: str) -> None:
    settings = outcome["settings"]
    assert isinstance(settings, NotificationEmailSettings)
    assert settings.warning == warning
