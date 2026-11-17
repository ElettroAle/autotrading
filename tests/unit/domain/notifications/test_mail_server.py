from dataclasses import replace

import pytest

from autotrading.domain.notifications.errors import (
    InvalidMailSenderError,
    InvalidMailServerHostError,
    InvalidMailServerPortError,
    InvalidMailServerUsernameError,
)
from autotrading.domain.notifications.mail_security import MailSecurity
from autotrading.domain.notifications.mail_server import MailServer, MailServerAddress
from autotrading.domain.notifications.sealed_mail_password import SealedMailPassword
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned

TENANT = TenantId.new()
SEALED = SealedMailPassword(1, b"sealed")


def an_address(
    *, host: str = "smtp.example.com", port: int = 587, username: str = "anna@example.com", sender: str = ""
) -> MailServerAddress:
    return MailServerAddress(host, port, MailSecurity.STARTTLS, username, sender)


def test_a_server_without_a_sender_sends_as_its_user() -> None:
    server = MailServer.of(TENANT, an_address(), SEALED)

    assert server.sender.value == "anna@example.com"
    assert server.host == "smtp.example.com"
    assert server.port == 587
    assert server.security is MailSecurity.STARTTLS
    assert server.username == "anna@example.com"
    assert server.password == SEALED


def test_a_server_keeps_its_sender_without_the_spaces_around() -> None:
    server = MailServer.of(TENANT, an_address(sender="  avvisi@example.com "), SEALED)

    assert server.sender.value == "avvisi@example.com"


def test_host_and_user_are_kept_without_the_spaces_around() -> None:
    server = MailServer.of(TENANT, an_address(host=" smtp.example.com ", username=" anna@example.com "), SEALED)

    assert (server.host, server.username) == ("smtp.example.com", "anna@example.com")


def test_the_server_belongs_to_its_tenant() -> None:
    server = MailServer.of(TENANT, an_address(), SEALED)

    assert isinstance(server, TenantOwned)
    assert server.tenant_id == TENANT


@pytest.mark.parametrize("host", ["", "   ", "smtp example.com"])
def test_a_host_without_the_form_of_a_name_is_refused_with_the_value(host: str) -> None:
    with pytest.raises(InvalidMailServerHostError, match=r"^server di posta non valido$") as raised:
        MailServer.of(TENANT, an_address(host=host), SEALED)

    assert raised.value.status_code == 400
    assert raised.value.details == {"host": host.strip()}


@pytest.mark.parametrize("port", [0, -1, 65536])
def test_a_port_out_of_range_is_refused_with_the_value(port: int) -> None:
    with pytest.raises(
        InvalidMailServerPortError, match=r"^porta del server di posta non valida: da 1 a 65535$"
    ) as raised:
        MailServer.of(TENANT, an_address(port=port), SEALED)

    assert raised.value.details == {"port": port}


@pytest.mark.parametrize("port", [1, 465, 65535])
def test_a_port_in_range_is_accepted(port: int) -> None:
    assert MailServer.of(TENANT, an_address(port=port), SEALED).port == port


@pytest.mark.parametrize("username", ["", "  "])
def test_a_server_without_a_user_is_refused(username: str) -> None:
    with pytest.raises(InvalidMailServerUsernameError, match=r"^utente del server di posta mancante$") as raised:
        MailServer.of(TENANT, an_address(username=username), SEALED)

    assert raised.value.details == {"username": ""}


def test_a_sender_without_the_form_of_an_email_is_refused_with_the_value() -> None:
    with pytest.raises(InvalidMailSenderError, match=r"^mittente non valido$") as raised:
        MailServer.of(TENANT, an_address(sender="avvisi"), SEALED)

    assert raised.value.details == {"sender": "avvisi"}


def test_a_user_that_is_no_address_needs_a_sender() -> None:
    with pytest.raises(InvalidMailSenderError) as raised:
        MailServer.of(TENANT, an_address(username="anna"), SEALED)

    assert raised.value.details == {"sender": "anna"}


def test_a_server_never_exists_with_a_port_out_of_range() -> None:
    server = MailServer.of(TENANT, an_address(), SEALED)

    with pytest.raises(InvalidMailServerPortError):
        replace(server, port=70000)


def test_a_server_keeps_another_password_without_changing_the_rest() -> None:
    server = MailServer.of(TENANT, an_address(), SEALED)
    other = SealedMailPassword(2, b"other")

    kept = server.with_password(other)

    assert kept.password == other
    assert replace(kept, password=SEALED) == server


def test_the_sealed_password_never_shows_its_bytes() -> None:
    assert "sealed" not in repr(SEALED)


def test_the_security_is_named_as_the_user_reads_it() -> None:
    assert [security.value for security in MailSecurity] == ["STARTTLS", "TLS"]
