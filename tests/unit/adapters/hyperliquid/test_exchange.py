from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
import requests
from eth_account import Account as EthereumAccount
from eth_account.signers.local import LocalAccount
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from hyperliquid.utils.error import ClientError, ServerError

from autotrading.adapters.outbound.hyperliquid.exchange import (
    INVALID_KEY_MESSAGE,
    PROBE_COIN,
    TIMEOUT_SECONDS,
    HyperliquidExchangeAdapter,
)
from autotrading.application.accounts.errors import ExchangeRejectedCredentialsError, ExchangeUnavailableError
from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.balance import Balance
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.position import Position, PositionSide

BASE_URL = "https://api.hyperliquid-testnet.xyz"
WALLET = EthereumAccount.create()
ADDRESS = "0xAbCdEf0000000000000000000000000000000001"
CREDENTIALS = Credentials(ADDRESS, WALLET.key.hex())
ACCEPTED = {"status": "ok", "response": {"type": "cancel", "data": {"statuses": [{"error": "never placed"}]}}}
READ_AT_MS = 1_794_307_200_000
STATE = {
    "marginSummary": {"accountValue": "1234.56", "totalMarginUsed": "0.0"},
    "withdrawable": "1000.5",
    "assetPositions": [],
    "time": READ_AT_MS,
}
LONG_BTC = {
    "coin": "BTC",
    "szi": "0.02",
    "leverage": {"type": "cross", "value": 2},
    "entryPx": "60000.0",
    "unrealizedPnl": "12.5",
    "liquidationPx": "31000.0",
    "marginUsed": "600.0",
}


@dataclass
class FakeSdk:
    """Stands in for the official SDK: it records the calls and answers what the test decides."""

    cancel_answer: Any = field(default_factory=lambda: ACCEPTED)
    state: Any = field(default_factory=lambda: STATE)
    failure: Exception | None = None
    calls: list[tuple[str, Any]] = field(default_factory=list)

    def exchange(self, wallet: LocalAccount, base_url: str, account_address: str, timeout: float) -> FakeSdk:
        self.calls.append(("exchange", (wallet.address, base_url, account_address, timeout)))
        return self

    def info(self, base_url: str, timeout: float) -> FakeSdk:
        self.calls.append(("info", (base_url, timeout)))
        return self

    def cancel_by_cloid(self, coin: str, cloid: object) -> Any:
        self.calls.append(("cancel", (coin, str(cloid))))
        if self.failure is not None:
            raise self.failure
        return self.cancel_answer

    def user_state(self, address: str) -> Any:
        self.calls.append(("user_state", address))
        return self.state


def read(sdk: FakeSdk, credentials: Credentials = CREDENTIALS) -> AccountState:
    return HyperliquidExchangeAdapter(BASE_URL, sdk).read_state(credentials)


def test_reads_the_account_state_after_the_exchange_accepts_the_signer() -> None:
    sdk = FakeSdk()

    state = read(sdk)

    assert state == AccountState(
        balance=Balance(Decimal("1234.56"), "USDC"),
        available_margin=Balance(Decimal("1000.5"), "USDC"),
        positions=(),
        read_at=datetime.fromtimestamp(READ_AT_MS / 1000, UTC),
    )
    assert [name for name, _ in sdk.calls] == ["exchange", "cancel", "info", "user_state"]
    assert sdk.calls[0][1] == (WALLET.address, BASE_URL, ADDRESS, TIMEOUT_SECONDS)
    assert sdk.calls[3][1] == ADDRESS


def test_the_probe_cancels_a_random_order_id_that_cannot_exist() -> None:
    sdk = FakeSdk()

    read(sdk)
    read(sdk)

    probes = [arguments for name, arguments in sdk.calls if name == "cancel"]
    assert [coin for coin, _ in probes] == [PROBE_COIN, PROBE_COIN]
    assert probes[0][1] != probes[1][1]


def test_a_signer_the_exchange_does_not_know_is_rejected_with_its_message_masked() -> None:
    message = f"User or API Wallet {ADDRESS.lower()} does not exist."
    sdk = FakeSdk(cancel_answer={"status": "err", "response": message})

    with pytest.raises(ExchangeRejectedCredentialsError) as raised:
        read(sdk)

    assert raised.value.exchange_message == "User or API Wallet *** does not exist."
    assert "user_state" not in [name for name, _ in sdk.calls]


def test_an_answer_of_unknown_shape_is_a_rejection_that_keeps_its_text() -> None:
    with pytest.raises(ExchangeRejectedCredentialsError) as raised:
        read(FakeSdk(cancel_answer="unexpected"))

    assert raised.value.exchange_message == "unexpected"


def test_a_client_error_of_the_exchange_is_a_rejection_with_its_message() -> None:
    error = ClientError(422, None, f"Failed to deserialize user {ADDRESS}", None)

    with pytest.raises(ExchangeRejectedCredentialsError) as raised:
        read(FakeSdk(failure=error))

    assert raised.value.exchange_message == "Failed to deserialize user ***"


@pytest.mark.parametrize(
    "failure",
    [ServerError(502, "bad gateway"), requests.ConnectionError("refused"), requests.Timeout("10s")],
    ids=["server-error", "connection", "timeout"],
)
def test_an_exchange_that_does_not_answer_is_unavailable(failure: Exception) -> None:
    with pytest.raises(ExchangeUnavailableError):
        read(FakeSdk(failure=failure))


def test_a_malformed_key_is_rejected_without_reaching_the_exchange() -> None:
    sdk = FakeSdk()

    with pytest.raises(ExchangeRejectedCredentialsError) as raised:
        read(sdk, Credentials(ADDRESS, "not-a-key"))

    assert raised.value.exchange_message == INVALID_KEY_MESSAGE
    assert sdk.calls == []


def test_positions_carry_side_size_leverage_prices_and_result() -> None:
    short_eth = LONG_BTC | {"coin": "ETH", "szi": "-1.5", "leverage": {"type": "isolated", "value": 3}}
    entries = [{"type": "oneWay", "position": LONG_BTC}, {"type": "oneWay", "position": short_eth}]

    positions = read(FakeSdk(state=STATE | {"assetPositions": entries})).positions

    assert positions == (
        Position("BTC", PositionSide.LONG, Decimal("0.02"), 2, Decimal(60000), Decimal("12.5"), Decimal(31000)),
        Position("ETH", PositionSide.SHORT, Decimal("1.5"), 3, Decimal(60000), Decimal("12.5"), Decimal(31000)),
    )


def test_a_position_without_a_liquidation_price_reports_none() -> None:
    entry = {"type": "oneWay", "position": LONG_BTC | {"liquidationPx": None}}

    (position,) = read(FakeSdk(state=STATE | {"assetPositions": [entry]})).positions

    assert position.liquidation_price is None


@pytest.mark.parametrize(
    "state",
    [
        {},
        STATE | {"marginSummary": {}},
        STATE | {"marginSummary": {"accountValue": "n/a"}},
        {key: value for key, value in STATE.items() if key != "withdrawable"},
        {key: value for key, value in STATE.items() if key != "time"},
        STATE | {"assetPositions": [{"position": {"coin": "BTC"}}]},
        None,
    ],
    ids=["empty", "no-value", "not-a-number", "no-margin", "no-time", "broken-position", "none"],
)
def test_an_account_state_of_unexpected_shape_is_unavailable(state: object) -> None:
    with pytest.raises(ExchangeUnavailableError):
        read(FakeSdk(state=state))


@pytest.mark.parametrize(("testnet", "url"), [(True, TESTNET_API_URL), (False, MAINNET_API_URL)])
def test_the_network_follows_the_installation(testnet: bool, url: str) -> None:
    sdk = FakeSdk()

    HyperliquidExchangeAdapter.for_network(testnet=testnet, sdk=sdk).read_state(CREDENTIALS)

    assert sdk.calls[0][1][1] == url
