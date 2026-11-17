from enum import StrEnum


class MailSecurity(StrEnum):
    """How the connection to the mail server of the tenant is protected, by the words the user reads (R3.5.5): from the
    first byte, or raised on the plain connection before the login.
    """

    STARTTLS = "STARTTLS"
    TLS = "TLS"
