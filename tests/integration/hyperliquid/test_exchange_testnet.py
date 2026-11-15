"""The Hyperliquid adapter against the testnet: run by hand once the testnet account and its API wallet exist.

HYPERLIQUID_TESTNET_CREDENTIALS_FILE names a JSON file readable only by the person running the test, with
"account_address" and "secret_key" of an API wallet approved for that account.
"""

import json
import os
from pathlib import Path

import pytest
from eth_account import Account as EthereumAccount

from autotrading.adapters.outbound.hyperliquid.exchange import HyperliquidTestnetExchangeAdapter
from autotrading.application.accounts.errors import ExchangeRejectedCredentialsError
from autotrading.domain.accounts.credentials import Credentials
from tests.support.credentials import hyperliquid_credentials

pytestmark = pytest.mark.testnet


@pytest.fixture
def credentials() -> Credentials:
    location = os.environ.get("HYPERLIQUID_TESTNET_CREDENTIALS_FILE")
    if not location:
        pytest.skip("HYPERLIQUID_TESTNET_CREDENTIALS_FILE not set")
    document = json.loads(Path(location).read_text(encoding="utf-8"))
    return hyperliquid_credentials(document["account_address"], document["secret_key"])


def test_approved_credentials_read_the_account_value(credentials: Credentials) -> None:
    balance = HyperliquidTestnetExchangeAdapter().read_state(credentials).balance

    assert balance.currency == "USDC"
    assert balance.amount >= 0


def test_a_wallet_not_approved_for_the_account_is_rejected_by_the_exchange(credentials: Credentials) -> None:
    stranger = hyperliquid_credentials(credentials.value("account_address"), EthereumAccount.create().key.hex())

    with pytest.raises(ExchangeRejectedCredentialsError) as raised:
        HyperliquidTestnetExchangeAdapter().read_state(stranger)

    assert raised.value.exchange_message
