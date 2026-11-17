from uuid import UUID

import pytest

from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.notifications.errors import InvalidOutboxMessageError
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.notification_email import NotificationEmail
from autotrading.domain.notifications.notification_link import NotificationLink
from autotrading.domain.notifications.outbox_message import (
    CHAT_MESSAGE,
    EMAIL_MESSAGE,
    ChatMessage,
    EmailMessage,
    OutboxMessage,
)
from autotrading.domain.notifications.outbox_message_id import OutboxMessageId
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned

TENANT = TenantId(UUID("4f6c1d0e-7a3b-4e59-9c2d-1b8e5f0a6c71"))
CHAT = LinkedChat(TENANT, ChatId(-100123))


def test_a_message_to_a_chat_belongs_to_the_tenant_of_the_chat() -> None:
    message = OutboxMessage.to_chat(CHAT, "alfa: ciclo fallito, timeout")

    assert message.tenant_id == TENANT
    assert isinstance(message, TenantOwned)


def test_a_message_to_a_chat_keeps_the_chat_and_the_text_for_its_integration() -> None:
    message = OutboxMessage.to_chat(CHAT, "alfa: ciclo fallito, timeout")

    assert message.integration == CHAT_MESSAGE
    assert message.payload == {"chat_id": -100123, "text": "alfa: ciclo fallito, timeout"}


def test_every_message_has_an_identity_of_its_own() -> None:
    first, second = OutboxMessage.to_chat(CHAT, "uno"), OutboxMessage.to_chat(CHAT, "due")

    assert first.id != second.id


def test_a_message_to_a_chat_reads_back_its_chat_and_its_text() -> None:
    message = OutboxMessage.to_chat(CHAT, "alfa: chiusa BTC")

    assert message.chat_message() == ChatMessage(ChatId(-100123), "alfa: chiusa BTC")


@pytest.mark.parametrize(
    "payload",
    [
        {"text": "senza chat"},
        {"chat_id": -100123},
        {"chat_id": "-100123", "text": "chat come testo"},
        {"chat_id": -100123, "text": 7},
    ],
)
def test_a_payload_without_a_chat_and_a_text_is_a_defect_that_never_heals(payload: dict[str, str | int]) -> None:
    message = OutboxMessage(OutboxMessageId.new(), TENANT, CHAT_MESSAGE, payload)

    with pytest.raises(InvalidOutboxMessageError, match=r"^messaggio in uscita senza chat o testo$") as raised:
        message.chat_message()

    assert raised.value.permanent


def test_an_identity_is_read_back_from_its_text() -> None:
    identity = OutboxMessageId.new()

    assert OutboxMessageId.parse(str(identity.value)) == identity


EMAIL = NotificationEmail(TENANT, EmailAddress.parse("anna@example.com"))


def test_a_message_to_an_email_keeps_the_address_the_subject_and_the_text_for_its_integration() -> None:
    message = OutboxMessage.to_email(EMAIL, "alfa: in pausa", "alfa: in pausa, credito esaurito")

    assert message.tenant_id == TENANT
    assert message.integration == EMAIL_MESSAGE
    assert message.payload == {
        "to": "anna@example.com",
        "subject": "alfa: in pausa",
        "text": "alfa: in pausa, credito esaurito",
    }


def test_a_message_to_an_email_reads_back_its_address_its_subject_and_its_text() -> None:
    message = OutboxMessage.to_email(EMAIL, "alfa: in pausa", "alfa: in pausa, credito esaurito")

    assert message.email_message() == EmailMessage(
        EmailAddress.parse("anna@example.com"), "alfa: in pausa", "alfa: in pausa, credito esaurito"
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"subject": "s", "text": "t"},
        {"to": "anna@example.com", "text": "t"},
        {"to": "anna@example.com", "subject": "s"},
        {"to": 7, "subject": "s", "text": "t"},
        {"to": "anna", "subject": "s", "text": "t"},
    ],
)
def test_a_payload_without_an_address_a_subject_and_a_text_is_a_defect_that_never_heals(
    payload: dict[str, str | int],
) -> None:
    message = OutboxMessage(OutboxMessageId.new(), TENANT, EMAIL_MESSAGE, payload)

    with pytest.raises(InvalidOutboxMessageError) as raised:
        message.email_message()

    assert raised.value.permanent


# ADR destinazioni-delle-notifiche-nella-dashboard: the links of a notification travel with its message (R3.5.6).

LINKS = (
    NotificationLink("Apri flusso", "https://example.org/dashboard/flows/1"),
    NotificationLink("Apri operazione", "https://example.org/dashboard/flows/1/positions?asset=BTC"),
)
LINKS_PAYLOAD = [
    {"label": "Apri flusso", "url": "https://example.org/dashboard/flows/1"},
    {"label": "Apri operazione", "url": "https://example.org/dashboard/flows/1/positions?asset=BTC"},
]


def test_a_message_to_a_chat_keeps_its_links_for_its_integration() -> None:
    message = OutboxMessage.to_chat(CHAT, "alfa: posizione aperta", links=LINKS)

    assert message.payload == {"chat_id": -100123, "text": "alfa: posizione aperta", "links": LINKS_PAYLOAD}
    assert message.chat_message() == ChatMessage(ChatId(-100123), "alfa: posizione aperta", LINKS)


def test_a_message_to_an_email_keeps_its_links_for_its_integration() -> None:
    message = OutboxMessage.to_email(EMAIL, "alfa: posizione aperta", "alfa: posizione aperta", links=LINKS)

    assert message.payload["links"] == LINKS_PAYLOAD
    assert message.email_message().links == LINKS


def test_a_message_queued_before_the_links_reads_back_without_links() -> None:
    message = OutboxMessage(OutboxMessageId.new(), TENANT, CHAT_MESSAGE, {"chat_id": -100123, "text": "t"})

    assert message.chat_message().links == ()


@pytest.mark.parametrize(
    "links",
    [
        "https://example.org",
        [{"label": "Apri flusso"}],
        [{"label": "Apri flusso", "url": 7}],
        ["Apri flusso"],
    ],
)
def test_links_without_label_and_address_are_a_defect_that_never_heals(links: object) -> None:
    payload = {"to": "anna@example.com", "subject": "s", "text": "t", "links": links}
    message = OutboxMessage(OutboxMessageId.new(), TENANT, EMAIL_MESSAGE, payload)  # type: ignore[arg-type]  # a payload read back malformed

    with pytest.raises(InvalidOutboxMessageError) as raised:
        message.email_message()

    assert raised.value.permanent


def test_the_body_of_an_email_ends_with_a_blank_line_and_a_line_for_each_link() -> None:
    email = EmailMessage(
        EmailAddress.parse("anna@example.com"), "alfa: posizione aperta", "titolo\n\nAsset: BTC", LINKS
    )

    assert email.body.splitlines() == [
        "titolo",
        "",
        "Asset: BTC",
        "",
        "Apri flusso: https://example.org/dashboard/flows/1",
        "Apri operazione: https://example.org/dashboard/flows/1/positions?asset=BTC",
    ]


def test_the_body_of_an_email_without_links_is_its_text() -> None:
    email = EmailMessage(EmailAddress.parse("anna@example.com"), "alfa: in pausa", "alfa: in pausa")

    assert email.body == "alfa: in pausa"
