from dataclasses import dataclass

from autotrading.domain.flows.account_reference import MASK, AccountReference


@dataclass(frozen=True, slots=True)
class CycleAccess(AccountReference):
    """The opened credentials a cycle reads its account with, proving they still work on the exchange (R1.2.4).

    Every field of the credentials, by the names the exchange declares, where a reference carries only those a reader
    asks for (Bug 284). Never shown in answers, logs or errors, so the representation masks them (R0.2.3).
    """

    def __hash__(self) -> int:
        return hash(frozenset(self.fields.items()))

    def __repr__(self) -> str:
        return f"CycleAccess({MASK})"

    __str__ = __repr__
