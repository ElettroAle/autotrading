import logging

from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.smtp.configuration import _plain_settings_of, _settings_of
from autotrading.adapters.outbound.smtp.mailer import (
    SmtpDisabledMailerAdapter,
    SmtpMailerAdapter,
    SmtpMailServiceAdapter,
)
from autotrading.application.notifications.ports import MailerPort, MailServicePort

operations = logging.getLogger("autotrading.notifications")


def smtp_adapters(source: ConfigurationSource) -> tuple[MailerPort, MailServicePort]:
    """The mail service of the worker: without its host no email leaves, and the address can still be indicated."""
    settings = _settings_of(source)
    if settings.host is None or settings.sender is None:
        operations.warning("servizio di posta non configurato: email disattivate")
        return SmtpDisabledMailerAdapter(), SmtpMailServiceAdapter(configured=False)
    mailer = SmtpMailerAdapter(settings.host, settings.port, settings.sender, settings.login)
    return mailer, SmtpMailServiceAdapter(configured=True)


def smtp_service_adapters(source: ConfigurationSource) -> MailServicePort:
    """Whether the installation has a mail service, for the API: from the plain settings alone."""
    return SmtpMailServiceAdapter(configured=_plain_settings_of(source).host is not None)
