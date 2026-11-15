"""The Hyperliquid adapter against the testnet: run by hand once the testnet account and its API wallet exist.

HYPERLIQUID_TESTNET_CREDENTIALS_FILE names a JSON file readable only by the person running the test, with
"account_address" and "secret_key" of an API wallet approved for that account.
"""

import json
import os
from pathlib import Path

import pytest
from eth_account import Account as EthereumAccount
from hyperliquid.utils.constants import TESTNET_API_URL

from autotrading.adapters.outbound.hyperliquid.exchange import (
    AGENT_NOT_AUTHORIZED_MESSAGE,
    TIMEOUT_SECONDS,
    HyperliquidSdkAdapter,
    HyperliquidTestnetExchangeAdapter,
    _require_signer_of,
)
from autotrading.application.accounts.errors import ExchangeRejectedCredentialsError
from autotrading.domain.accounts.credentials import Credentials
from tests.support.credentials import hyperliquid_credentials

pytestmark = pytest.mark.testnet

# Public addresses of the testnet: an account that holds funds, and an API wallet it no longer approves (Bug 399).
ACCOUNT = "0x9679d13e410167f3c8531533491552e2b3c87499"
REVOKED_API_WALLET = "0xadaaf16d81cd1be30faa06ac9637c3df0e77f577"


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


def _role_of(address: str) -> object:
    return HyperliquidSdkAdapter().info(TESTNET_API_URL, TIMEOUT_SECONDS).user_role(address)


def test_an_account_signing_for_itself_is_accepted_by_its_role() -> None:
    _require_signer_of(_role_of(ACCOUNT), ACCOUNT, ACCOUNT)


def test_an_account_signing_for_another_address_is_rejected_by_its_role() -> None:
    stranger = EthereumAccount.create().address

    with pytest.raises(ExchangeRejectedCredentialsError) as raised:
        _require_signer_of(_role_of(ACCOUNT), ACCOUNT, stranger)

    assert raised.value.exchange_message == AGENT_NOT_AUTHORIZED_MESSAGE


def test_an_api_wallet_the_account_no_longer_approves_is_rejected_by_its_role() -> None:
    with pytest.raises(ExchangeRejectedCredentialsError) as raised:
        _require_signer_of(_role_of(REVOKED_API_WALLET), REVOKED_API_WALLET, ACCOUNT)

    assert raised.value.exchange_message == AGENT_NOT_AUTHORIZED_MESSAGE
