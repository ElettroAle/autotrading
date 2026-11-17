"""ADR-invio-dal-server-di-posta-del-tenant: every email leaves from the mail server of its tenant, with the password
the worker opens; nothing of a mail service of the installation is left in the code nor in the installations.
"""

import inspect
import re
from pathlib import Path

import pytest

from autotrading.application.notifications import ports
from autotrading.application.notifications.deliver_outbox_message import DeliverOutboxMessageUseCase
from autotrading.domain.notifications.mail_server import MailServer
from tests.support.architecture import SOURCE_ROOT

REPOSITORY = Path(__file__).resolve().parents[2]
SEARCHED = (Path(SOURCE_ROOT), REPOSITORY / "deploy")
SMTP_FOLDER = Path(SOURCE_ROOT) / "adapters" / "outbound" / "smtp"
# The names of the mail service of the installation, gone with this decision.
INSTALLATION_SERVICE = re.compile(r"\bSMTP_[A-Z]+\b(?<!SMTP_SSL)|MailServicePort|SmtpMailService|SmtpDisabledMailer")


def installation_service_in(text: str) -> list[str]:
    """Every name of the mail service of the installation the text still carries."""
    return INSTALLATION_SERVICE.findall(text)


def test_adr_invio_dal_server_di_posta_no_mail_service_of_the_installation_is_left() -> None:
    texts = {
        path: path.read_text(encoding="utf-8", errors="ignore")
        for root in SEARCHED
        for path in root.rglob("*")
        if path.is_file() and path.suffix in {".py", ".yml", ".yaml", ".env", ".sh", ".json", ".conf"}
    }

    left = {str(path): names for path, text in texts.items() if (names := installation_service_in(text))}

    assert left == {}
    assert not hasattr(ports, "MailServicePort")


def test_adr_invio_dal_server_di_posta_the_mailer_has_no_configuration_of_its_own() -> None:
    assert not (SMTP_FOLDER / "configuration.py").exists()


def test_adr_invio_dal_server_di_posta_the_mailer_sends_from_the_server_with_its_password() -> None:
    parameters = inspect.signature(ports.MailerPort.send).parameters

    assert parameters["server"].annotation in {MailServer, "MailServer"}
    assert "password" in parameters


def test_adr_invio_dal_server_di_posta_the_delivery_reaches_the_server_of_the_tenant_of_the_message() -> None:
    assert "mail_servers_of" in inspect.signature(DeliverOutboxMessageUseCase).parameters


@pytest.mark.parametrize(
    ("text", "names"),
    [
        ('SMTP_HOST = source.value("SMTP_HOST")\n', ["SMTP_HOST", "SMTP_HOST"]),
        ("class SmtpMailServiceAdapter:\n", ["SmtpMailService"]),
        ("smtplib.SMTP_SSL(server.host, server.port)\n", []),
        ("mailer.send(server, password, address, subject, text)\n", []),
    ],
)
def test_adr_invio_dal_server_di_posta_a_mail_service_of_the_installation_is_found(text: str, names: list[str]) -> None:
    assert installation_service_in(text) == names
