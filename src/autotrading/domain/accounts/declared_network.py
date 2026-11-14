from dataclasses import dataclass

from autotrading.domain.accounts.exchange_network import ExchangeNetwork


@dataclass(frozen=True, slots=True)
class DeclaredNetwork:
    """The network an exchange trades on, with the name its adapter gives it (R2.3.10, ADR 0162).

    The kind says whether it moves real money; the name lets a reader recognise it without the platform knowing it.
    """

    kind: ExchangeNetwork
    name: str

    @classmethod
    def of(cls, *, real: bool, name: str) -> DeclaredNetwork:
        return cls(ExchangeNetwork.of(real=real), name)
