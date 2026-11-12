"""The activity adapter against the testnet: the readings are public, so a fresh address is enough."""

from decimal import Decimal

import pytest
from eth_account import Account as EthereumAccount

from autotrading.adapters.outbound.hyperliquid.activity import HyperliquidAccountActivityAdapter

pytestmark = pytest.mark.testnet


def test_a_fresh_address_has_an_empty_activity_in_usdc() -> None:
    activity = HyperliquidAccountActivityAdapter.for_network(testnet=True).activity(EthereumAccount.create().address)

    assert (activity.currency, activity.balance, activity.available_margin) == ("USDC", Decimal(0), Decimal(0))
    assert (activity.positions, activity.fills, activity.movements) == ((), (), ())
