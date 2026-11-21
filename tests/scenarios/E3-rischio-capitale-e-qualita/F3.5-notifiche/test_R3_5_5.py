"""R3.5.5: the mail server of the user, saved with its password sealed and used by the worker alone, on the use cases
of the API and of the worker with the fake adapters (ADR server-di-posta-per-tenant, ADR
invio-dal-server-di-posta-del-tenant).
"""

from uuid import uuid4

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.adapters.inbound.api.mail_server import MailServerResponse
from autotrading.adapters.inbound.api.notification_channels import NotificationChannelsResponse
from autotrading.application.notifications.choose_notification_channel import ChooseNotificationChannelCommand
from autotrading.application.notifications.set_mail_server import SetMailServerCommand
from autotrading.application.notifications.set_notification_email import SetNotificationEmailCommand
from autotrading.domain.errors import AutotradingError
from autotrading.domain.notifications.mail_security import MailSecurity
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.notifications.notification_channel import NotificationChannel
from autotrading.domain.notifications.notification_event import NotificationEvent
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E3-rischio-capitale-e-qualita/F3.5-notifiche/R3.5.5-server-di-posta-dell-utente.feature")

PASSWORD = "password-per-le-app"  # noqa: S105 - the password of a fake mail server
SUBMISSION_PORT = 587
# The tabs of the page of the notifications: the choice of the channels by default, the channels while none is linked.
PREFERENCES, CHANNELS = "Preferenze", "Canali"


@pytest.fixture
def platform() -> Platform:
    return Platform()


@pytest.fixture
def outcome() -> dict[str, object]:
    """What the last request answered: the refusal, or the answer of the saved server."""
    return {}


def save_server(
    platform: Platform,
    user: str,
    host: str,
    *,
    port: int = SUBMISSION_PORT,
    security: MailSecurity = MailSecurity.STARTTLS,
    password: str | None = PASSWORD,
) -> None:
    command = SetMailServerCommand(host, port, security, f"{user}@example.com", "", password)
    platform.use_cases_of(user).set_mail_server.execute(command)


def server_shown(platform: Platform, user: str) -> MailServerResponse | None:
    """The mail server as the programmatic interface answers it to the Canali of the dashboard."""
    settings = platform.use_cases_of(user).get_mail_server.execute()
    return None if settings is None else MailServerResponse.of(settings)


def summary_of(server: MailServerResponse) -> str:
    """The line of the Canali that sums up a saved server, as the dashboard writes it from the answer."""
    password = "password salvata" if server.password_saved else "password mancante"
    return f"{server.host}:{server.port} · {server.security.value} · {server.username} · {password}"


def channel_warnings(platform: Platform, user: str) -> list[str]:
    channels = platform.use_cases_of(user).get_notification_channels.execute()
    return NotificationChannelsResponse.of(channels).warnings


def linked_channels(platform: Platform, user: str) -> list[str]:
    """The channels the API answers as linked: a chat, or an address with a mail server (R3.5.5)."""
    use_cases = platform.use_cases_of(user)
    chat = use_cases.get_linked_chat.execute()
    email = use_cases.get_notification_email.execute().address is not None and server_shown(platform, user) is not None
    return [name for name, linked in (("Telegram", chat is not None), ("Email", email)) if linked]


def send_test(platform: Platform, outcome: dict[str, object], user: str) -> None:
    try:
        platform.use_cases_of(user).request_test_email.execute()
    except AutotradingError as error:
        outcome["refusal"] = error


# Given


@given(quoted('che "{user}" ha indicato l\'indirizzo "{address}" per le notifiche'))
def address_indicated(platform: Platform, user: str, address: str) -> None:
    platform.use_cases_of(user).set_notification_email.execute(SetNotificationEmailCommand(address))


@given(quoted('che "{user}" ha salvato il server di posta "{host}"'))
def server_saved(platform: Platform, user: str, host: str) -> None:
    save_server(platform, user, host)


@given(quoted('che "{user}" ha salvato il server di posta "{host}" senza mittente'))
def server_saved_without_sender(platform: Platform, user: str, host: str) -> None:
    # The command leaves the sender empty, as the form of the dashboard does when the user writes none.
    save_server(platform, user, host)


@given(quoted('che "{user}" non ha collegato alcun canale'))
def nothing_linked(platform: Platform, user: str) -> None:
    assert not linked_channels(platform, user)


@given("che il server di posta rifiuta l'accesso")
def login_refused(platform: Platform) -> None:
    platform.mailer.refusing_login = True


# When


@when(
    quoted('"{user}" salva il server di posta "{host}" porta {port} con {security}, utente "{username}" e una password')
)
def user_saves_server(  # noqa: PLR0917 - one argument per value of the step
    platform: Platform, outcome: dict[str, object], user: str, host: str, port: str, security: str, username: str
) -> None:
    command = SetMailServerCommand(host, int(port), MailSecurity(security), username, "", PASSWORD)
    platform.use_cases_of(user).set_mail_server.execute(command)
    outcome["answer"] = server_shown(platform, user)


@when(quoted('"{user}" invia l\'email di prova'))
def user_sends_test(platform: Platform, outcome: dict[str, object], user: str) -> None:
    send_test(platform, outcome, user)


@when(quoted('"{user}" cambia la porta del server di posta in {port} con {security} senza indicare la password'))
def user_changes_port(platform: Platform, outcome: dict[str, object], user: str, port: str, security: str) -> None:
    outcome["user"] = user
    server = server_shown(platform, user)
    assert server is not None
    save_server(platform, user, server.host, port=int(port), security=MailSecurity(security), password=None)


@when(quoted('un ciclo di un flusso di "{user}" fallisce con il canale email scelto'))
def cycle_of_user_fails(platform: Platform, user: str) -> None:
    channels = frozenset({NotificationChannel.EMAIL})
    choose = ChooseNotificationChannelCommand(NotificationEvent.CYCLE_FAILED, channels)
    platform.use_cases_of(user).choose_notification_channel.execute(choose)
    platform.notify_for(platform.tenant_of(user)).execute(Notification.cycle_failed(uuid4(), "omega", "timeout"))


@when(quoted('"{user}" apre la pagina Notifiche'))
def opens_notifications(platform: Platform, outcome: dict[str, object], user: str) -> None:
    outcome["linked"] = linked_channels(platform, user)


@when(quoted('"{user}" toglie il server di posta'))
def user_removes_server(platform: Platform, user: str) -> None:
    platform.use_cases_of(user).remove_mail_server.execute()


# Then


@then(quoted('i Canali di "{user}" mostrano il server "{summary}"'))
def channels_show_server(platform: Platform, user: str, summary: str) -> None:
    server = server_shown(platform, user)
    assert server is not None
    assert summary_of(server) == summary


@then("la password non compare nella risposta")
def password_not_answered(outcome: dict[str, object]) -> None:
    answer = outcome["answer"]
    assert isinstance(answer, MailServerResponse)
    assert PASSWORD not in answer.model_dump_json()
    assert "password" not in answer.model_dump(exclude={"password_saved"})


@then(quoted('la scelta dei canali di "{user}" avvisa accanto all\'email con "{warning}"'))
def channels_warn(platform: Platform, user: str, warning: str) -> None:
    assert warning in channel_warnings(platform, user)


@then(quoted('"{address}" riceve l\'email di prova da "{host}"'))
def email_arrives_from(platform: Platform, address: str, host: str) -> None:
    assert [email.subject for email in platform.mailer.received_by(address)] == [Notification.test().title]
    assert [login.host for login in platform.mailer.sent_from(address)] == [host]


@then(quoted('la richiesta viene rifiutata con "{reason}"'))
def request_refused(platform: Platform, outcome: dict[str, object], reason: str) -> None:
    assert str(outcome.get("refusal")) == reason
    assert platform.mailer.sent == []


@then(quoted('l\'email di prova parte da "{host}:{port}" con la password salvata'))
def leaves_with_saved_password(platform: Platform, outcome: dict[str, object], host: str, port: str) -> None:
    user = outcome["user"]
    assert isinstance(user, str)
    send_test(platform, outcome, user)

    assert "refusal" not in outcome
    [login] = platform.mailer.logins
    assert (login.host, login.port, login.password) == (host, int(port), PASSWORD)


@then(quoted('l\'email di prova parte con mittente "{sender}"'))
def leaves_with_sender(platform: Platform, outcome: dict[str, object], sender: str) -> None:
    assert "refusal" not in outcome
    assert [login.sender for login in platform.mailer.logins] == [sender]


@then(quoted('"{address}" riceve la notifica dal server "{host}"'))
def notice_from_server(platform: Platform, address: str, host: str) -> None:
    assert [email.subject for email in platform.mailer.received_by(address)] == ["\u26a0\ufe0f omega: ciclo fallito"]
    assert [login.host for login in platform.mailer.sent_from(address)] == [host]


@then(quoted('nessuna email parte dal server "{host}"'))
def nothing_from_server(platform: Platform, host: str) -> None:
    assert platform.mailer.logins
    assert host not in [login.host for login in platform.mailer.logins]


@then(quoted('la pagina Notifiche ha le schede "{first}" e "{second}" e mostra "{shown}"'))
def notifications_tabs(outcome: dict[str, object], first: str, second: str, shown: str) -> None:
    # The dashboard opens on the channels only while the API answers none as linked (ADR pagina-notifiche-a-schede).
    assert (first, second) == (PREFERENCES, CHANNELS)
    assert shown == (PREFERENCES if outcome["linked"] else CHANNELS)


@then(quoted('i Canali di "{user}" non mostrano alcun server di posta'))
def channels_show_no_server(platform: Platform, user: str) -> None:
    assert server_shown(platform, user) is None
