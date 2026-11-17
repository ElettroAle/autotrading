"""The mailer of the worker needs nothing of the installation: every email names the mail server of its tenant (ADR
invio-dal-server-di-posta-del-tenant).
"""

from autotrading.adapters.outbound.smtp.composition import smtp_adapters
from autotrading.adapters.outbound.smtp.mailer import SmtpMailerAdapter


def test_the_mailer_is_composed_without_any_configuration() -> None:
    assert isinstance(smtp_adapters(), SmtpMailerAdapter)
