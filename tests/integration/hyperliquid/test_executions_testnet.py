"""The executions adapter against the testnet: the executions, funding and movements of an address are public."""

from datetime import UTC, datetime, timedelta

import pytest
from eth_account import Account as EthereumAccount

from autotrading.adapters.outbound.hyperliquid.exchange import ACCOUNT_ADDRESS
from autotrading.adapters.outbound.hyperliquid.executions import HyperliquidAccountExecutionsAdapter
from autotrading.domain.flows.account_reference import AccountReference

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("since", [None, datetime.now(UTC) - timedelta(days=1)], ids=["from the start", "since"])
def test_a_fresh_address_has_a_complete_empty_window(since: datetime | None) -> None:
    adapter = HyperliquidAccountExecutionsAdapter.for_network(testnet=True)
    reference = AccountReference({ACCOUNT_ADDRESS: EthereumAccount.create().address})

    window = adapter.since(reference, since)

    assert window.executions == ()
    assert window.funding == ()
    assert window.movements == ()
    assert window.complete
