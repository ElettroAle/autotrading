"""The network of the exchanges follows the installation: test networks in dev, real ones in prod (R0.2.1)."""

import pytest

from autotrading.domain.accounts.exchange_network import ExchangeNetwork


@pytest.mark.parametrize(("environment", "test"), [("dev", True), ("prod", False)])
def test_the_installation_chooses_the_network_of_the_exchanges(environment: str, test: bool) -> None:
    assert ExchangeNetwork.of_installation(environment).is_test is test
