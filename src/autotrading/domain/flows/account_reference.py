from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from autotrading.domain.flows.errors import FlowCredentialsMissingError

MASK = "***"


@dataclass(frozen=True, slots=True)
class AccountReference:
    """The fields of an account a reader of its exchange needs to read it, and only those (ADR 0044, Bug 284).

    The reader declares their names; the secret that signs orders stays in the opener when the reader does not ask for
    it. Never shown in answers, logs or errors, so the representation masks them (R0.2.3).
    """

    fields: Mapping[str, str] = field(repr=False)

    def __post_init__(self) -> None:
        if not self.fields or not all(value.strip() for value in self.fields.values()):
            raise FlowCredentialsMissingError
        object.__setattr__(self, "fields", MappingProxyType(dict(self.fields)))

    def value(self, name: str) -> str:
        found = self.fields.get(name)
        if found is None:
            raise FlowCredentialsMissingError
        return found

    def __hash__(self) -> int:
        return hash(frozenset(self.fields.items()))

    def __repr__(self) -> str:
        return f"AccountReference({MASK})"

    __str__ = __repr__
