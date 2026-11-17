from autotrading.adapters.outbound.smtp.mailer import SmtpMailerAdapter


def smtp_adapters() -> SmtpMailerAdapter:
    """The mailer of the worker: every email names the mail server of its tenant, so nothing is read from the
    installation (ADR invio-dal-server-di-posta-del-tenant)."""
    return SmtpMailerAdapter()
