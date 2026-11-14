"""The network of an exchange is the one its adapter is configured on, never the name of the installation (Bug 277)."""

import pytest

from autotrading.domain.accounts.exchange_network import ExchangeNetwork


@pytest.mark.parametrize(("real", "network"), [(True, ExchangeNetwork.REAL), (False, ExchangeNetwork.TEST)])
def test_an_exchange_on_real_money_is_on_the_real_network(real: bool, network: ExchangeNetwork) -> None:
    assert ExchangeNetwork.of(real=real) is network


def test_only_the_test_network_is_a_test() -> None:
    assert ExchangeNetwork.TEST.is_test
    assert not ExchangeNetwork.REAL.is_test
