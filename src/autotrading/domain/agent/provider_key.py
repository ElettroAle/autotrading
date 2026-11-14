import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from autotrading.domain.agent.errors import (
    ProviderKeyFieldRequiredError,
    ProviderKeyRequiredError,
    UnknownProviderKeyFieldError,
)
from autotrading.domain.agent.provider_key_field import ProviderKeyField

MASK = "***"


@dataclass(frozen=True, slots=True)
class ProviderKey:
    """The key of the user at a provider of AI models, by the name of each field the provider declares.

    It never appears in answers, logs, errors or the context of the agent, so the representation masks it (R1.4.1).
    """

    values: Mapping[str, str] = field(repr=False)

    def __post_init__(self) -> None:
        if not self.values:
            raise ProviderKeyRequiredError
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))

    @classmethod
    def declared(cls, fields: Iterable[ProviderKeyField], values: Mapping[str, str]) -> ProviderKey:
        """The values of the fields the provider declares, each one required; any other field is refused."""
        declared = tuple(fields)
        names = {key_field.name for key_field in declared}
        unknown = sorted(name for name in values if name not in names)
        if unknown:
            raise UnknownProviderKeyFieldError(unknown[0])
        if not any(values.get(key_field.name, "").strip() for key_field in declared):
            raise ProviderKeyRequiredError
        return cls({key_field.name: _required(key_field, values) for key_field in declared})

    def value(self, name: str) -> str:
        found = self.values.get(name)
        if found is None:
            raise ProviderKeyRequiredError
        return found

    def redact(self, text: str) -> str:
        """The text without any of the values: what may reach a user, a log or an error."""
        for value in sorted(self.values.values(), key=len, reverse=True):
            text = re.sub(re.escape(value), MASK, text, flags=re.IGNORECASE)
        return text

    def __hash__(self) -> int:
        return hash(frozenset(self.values.items()))

    def __repr__(self) -> str:
        return f"ProviderKey({MASK})"

    __str__ = __repr__


def _required(key_field: ProviderKeyField, values: Mapping[str, str]) -> str:
    value = values.get(key_field.name, "").strip()
    if not value:
        raise ProviderKeyFieldRequiredError(key_field.name, key_field.label)
    return value
