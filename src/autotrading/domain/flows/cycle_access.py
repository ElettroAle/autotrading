from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from autotrading.domain.flows.errors import FlowCredentialsMissingError

MASK = "***"


@dataclass(frozen=True, slots=True)
class CycleAccess:
    """The opened credentials a cycle reads its account with, proving they still work on the exchange (R1.2.4).

    The fields carry the names the exchange declares: only its adapter knows which is which (Bug 284). Never shown in
    answers, logs or errors, so the representation masks them (R0.2.3).
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
        return f"CycleAccess({MASK})"

    __str__ = __repr__
