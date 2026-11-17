from dataclasses import dataclass

from autotrading.application.notifications.errors import EmailNotDeliveredError
from autotrading.domain.notifications.email_address import EmailAddress


@dataclass(frozen=True, slots=True)
class SentEmail:
    address: EmailAddress
    subject: str
    text: str


class FakeMailerAdapter:
    """The mail service as the tests see it: what each address received, or a service that refuses every email."""

    def __init__(self) -> None:
        self.accepting = True
        self.sent: list[SentEmail] = []

    def send(self, address: EmailAddress, subject: str, text: str) -> None:
        if not self.accepting:
            raise EmailNotDeliveredError
        self.sent.append(SentEmail(address, subject, text))

    def received_by(self, address: str) -> list[SentEmail]:
        return [email for email in self.sent if email.address.value == address]
