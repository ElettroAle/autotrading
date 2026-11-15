import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from autotrading.domain.accounts.credential_field import CredentialField
from autotrading.domain.accounts.errors import (
    CredentialFieldRequiredError,
    CredentialsRequiredError,
    UnknownCredentialFieldError,
)

MASK = "***"
INVISIBLE_FORMAT = "Cf"


@dataclass(frozen=True, slots=True)
class Credentials:
    """The data the user created on the exchange, by the name of the field the exchange declares for each.

    They never appear in answers, logs, errors or exceptions, so the representation masks them all (R0.2.3).
    """

    values: Mapping[str, str] = field(repr=False)

    def __post_init__(self) -> None:
        if not self.values:
            raise CredentialsRequiredError
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))

    @classmethod
    def declared(cls, fields: Iterable[CredentialField], values: Mapping[str, str]) -> Credentials:
        """The values of the fields the exchange declares, each one required; any other field is refused."""
        declared = tuple(fields)
        names = {credential_field.name for credential_field in declared}
        unknown = sorted(name for name in values if name not in names)
        if unknown:
            raise UnknownCredentialFieldError(unknown[0])
        if not any(_cleaned(values.get(credential_field.name, "")) for credential_field in declared):
            raise CredentialsRequiredError
        return cls({credential_field.name: _required(credential_field, values) for credential_field in declared})

    def value(self, name: str) -> str:
        found = self.values.get(name)
        if found is None:
            raise CredentialsRequiredError
        return found

    def redact(self, text: str) -> str:
        """The text without any of the values, whatever their case: what may reach a user, a log or an error."""
        for value in sorted(self.values.values(), key=len, reverse=True):
            text = re.sub(re.escape(value), MASK, text, flags=re.IGNORECASE)
        return text

    def __hash__(self) -> int:
        return hash(frozenset(self.values.items()))

    def __repr__(self) -> str:
        return f"Credentials({MASK})"

    __str__ = __repr__


def _required(credential_field: CredentialField, values: Mapping[str, str]) -> str:
    value = _cleaned(values.get(credential_field.name, ""))
    if not value:
        raise CredentialFieldRequiredError(credential_field.name, credential_field.label)
    return value


def _cleaned(value: str) -> str:
    # A value copied from a password manager or a web page can carry invisible format characters (zero-width space,
    # byte order mark): no credential of any exchange contains them, and they make a right value look wrong (Bug 387).
    visible = "".join(character for character in value if unicodedata.category(character) != INVISIBLE_FORMAT)
    return visible.strip()
