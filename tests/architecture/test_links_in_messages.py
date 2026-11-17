"""ADR-link-nei-messaggi-telegram-ed-email: the links of a notification are buttons under the Telegram message and
lines at the bottom of a plain-text email. Only the Telegram adapter builds buttons, the email never turns to HTML, and
both ports receive the links with the message.
"""

import inspect
import re

from autotrading.application.notifications.ports import MailerPort, MessengerPort
from autotrading.domain.notifications.outbox_message import EmailMessage
from tests.support.architecture import source_modules

TELEGRAM_FOLDER = "adapters/outbound/telegram/"
SMTP_MAILER = "adapters/outbound/smtp/mailer.py"
BUTTONS = re.compile(r"inline_keyboard|reply_markup")
HTML_EMAIL = re.compile(r"add_alternative|text/html|subtype=.html")

BUTTONS_IN_THE_WORKER = """
body = {"text": text, "reply_markup": {"inline_keyboard": [[{"text": "Apri flusso", "url": url}]]}}
"""
HTML_IN_THE_MAILER = """
message.set_content(email.text)
message.add_alternative(f"<a href='{url}'>Apri flusso</a>", subtype="html")
"""
PLAIN_MAILER = """
message.set_content(email.body)
"""


def buttons_in(text: str) -> list[str]:
    return BUTTONS.findall(text)


def email_violations(text: str) -> list[str]:
    """What keeps the email from carrying its links at the bottom of its plain text."""
    found = [f"an HTML part: {match}" for match in HTML_EMAIL.findall(text)]
    if "set_content(email.body)" not in text:
        found.append("the content is not the body with the links")
    return found


def test_adr_link_nei_messaggi_only_the_telegram_adapter_builds_buttons() -> None:
    found = {
        module.path: names
        for module in source_modules()
        if not module.path.startswith(TELEGRAM_FOLDER) and (names := buttons_in(module.text))
    }

    assert found == {}


def test_adr_link_nei_messaggi_the_email_carries_its_links_in_plain_text() -> None:
    mailer = next(module for module in source_modules() if module.path == SMTP_MAILER)

    assert email_violations(mailer.text) == []


def test_adr_link_nei_messaggi_both_ports_receive_the_links_with_the_message() -> None:
    assert "links" in inspect.signature(MessengerPort.send).parameters
    assert inspect.signature(MailerPort.send).parameters["email"].annotation in {EmailMessage, "EmailMessage"}
    assert "links" in inspect.signature(EmailMessage).parameters


def test_adr_link_nei_messaggi_a_button_or_an_html_email_elsewhere_is_found() -> None:
    assert buttons_in(BUTTONS_IN_THE_WORKER) == ["reply_markup", "inline_keyboard"]
    assert email_violations(HTML_IN_THE_MAILER) == [
        "an HTML part: add_alternative",
        'an HTML part: subtype="html',
        "the content is not the body with the links",
    ]
    assert email_violations(PLAIN_MAILER) == []
