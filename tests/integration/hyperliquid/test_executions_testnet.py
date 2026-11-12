"""The executions adapter against the testnet: the executions and funding of an address are public."""

from datetime import UTC, datetime, timedelta

import pytest
from eth_account import Account as EthereumAccount

from autotrading.adapters.outbound.hyperliquid.executions import HyperliquidAccountExecutionsAdapter

pytestmark = pytest.mark.testnet


@pytest.mark.parametrize("since", [None, datetime.now(UTC) - timedelta(days=1)], ids=["from the start", "since"])
def test_a_fresh_address_has_a_complete_empty_window(since: datetime | None) -> None:
    adapter = HyperliquidAccountExecutionsAdapter.for_network(testnet=True)

    window = adapter.since(EthereumAccount.create().address, since)

    assert (window.executions, window.funding, window.complete) == ((), (), True)
