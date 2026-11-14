from collections.abc import Mapping
from dataclasses import dataclass

from autotrading.application.accounts.ports import ExchangePort
from autotrading.application.accounts.verification import network_of
from autotrading.domain.accounts.credential_field import CredentialField
from autotrading.domain.accounts.exchange_name import ExchangeName
from autotrading.domain.accounts.exchange_network import ExchangeNetwork


@dataclass(frozen=True, slots=True)
class SupportedExchange:
    name: str
    network: ExchangeNetwork
    fields: tuple[CredentialField, ...]


class ListSupportedExchangesUseCase:
    """The exchanges an account can be registered on, by name: the same ones the registration accepts (R2.3.8,
    ADR 0152), each with the network its adapter is configured on, so the registration says before saving whether
    the account will trade real money (Bug 277, ADR 0157), and with the fields of its credentials the registration asks
    (R2.3.9, ADR 0158)."""

    def __init__(self, exchanges: Mapping[str, ExchangePort]) -> None:
        self._exchanges = exchanges

    def execute(self) -> tuple[SupportedExchange, ...]:
        return tuple(
            SupportedExchange(name, network_of(self._exchanges, ExchangeName(name)), exchange.credential_fields())
            for name, exchange in sorted(self._exchanges.items())
        )
