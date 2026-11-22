"""The Hyperliquid adapter against the testnet: the roles of the addresses are public, no credentials are needed."""

import pytest
from eth_account import Account as EthereumAccount
from hyperliquid.utils.constants import TESTNET_API_URL

from autotrading.adapters.outbound.hyperliquid.exchange import (
    AGENT_NOT_AUTHORIZED_MESSAGE,
    TIMEOUT_SECONDS,
    HyperliquidSdkAdapter,
    _require_signer_of,
)
from autotrading.application.accounts.errors import ExchangeRejectedCredentialsError

pytestmark = pytest.mark.integration

# Public addresses of the testnet: an account that holds funds, and an API wallet it no longer approves (Bug 399).
ACCOUNT = "0x9679d13e410167f3c8531533491552e2b3c87499"
REVOKED_AGENT_ADDRESS = "0xadaaf16d81cd1be30faa06ac9637c3df0e77f577"


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
        _require_signer_of(_role_of(REVOKED_AGENT_ADDRESS), REVOKED_AGENT_ADDRESS, ACCOUNT)

    assert raised.value.exchange_message == AGENT_NOT_AUTHORIZED_MESSAGE
