"""The network of an exchange with the name its adapter gives it: a dashboard names it unknowing (R2.3.10)."""

import pytest

from autotrading.domain.accounts.declared_network import DeclaredNetwork
from autotrading.domain.accounts.exchange_network import ExchangeNetwork


@pytest.mark.parametrize(("real", "kind"), [(True, ExchangeNetwork.REAL), (False, ExchangeNetwork.TEST)])
def test_the_declared_network_keeps_the_kind_and_the_name_of_the_exchange(real: bool, kind: ExchangeNetwork) -> None:
    network = DeclaredNetwork.of(real=real, name="sandbox")

    assert (network.kind, network.name) == (kind, "sandbox")
