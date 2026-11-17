import re
from dataclasses import dataclass

from autotrading.domain.notifications.errors import InvalidEmailAddressError

# The form alone, never a delivery: the address counts at once, without a verification (R3.5.2).
EMAIL_FORM = re.compile(r"^[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+$")


@dataclass(frozen=True, slots=True)
class EmailAddress:
    """The address a tenant receives its notifications at by email (R3.5.2)."""

    value: str

    def __post_init__(self) -> None:
        if not self.accepts(self.value):
            raise InvalidEmailAddressError(self.value)

    @classmethod
    def parse(cls, text: str) -> EmailAddress:
        return cls(text.strip())

    @staticmethod
    def accepts(text: str) -> bool:
        return EMAIL_FORM.fullmatch(text) is not None
