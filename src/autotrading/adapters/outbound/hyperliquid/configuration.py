from dataclasses import dataclass

from autotrading.domain.accounts.exchange_network import ExchangeNetwork


@dataclass(frozen=True, slots=True)
class _HyperliquidSettings:
    """The network chosen by the installation, never deduced from the credentials (ADR 0087).

    The name is the exchange an account declares at registration: the use cases pick the adapter by it.
    """

    network: ExchangeNetwork
    name: str = "Hyperliquid"

    @property
    def testnet(self) -> bool:
        return self.network.is_test
