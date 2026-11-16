from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
import requests
from eth_account.signers.local import LocalAccount
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from hyperliquid.utils.error import ClientError, ServerError

from autotrading.adapters.outbound.hyperliquid.activity import HyperliquidAccountActivityAdapter
from autotrading.adapters.outbound.hyperliquid.exchange import HyperliquidSdkAdapter
from autotrading.application.flows.errors import FlowCredentialsFieldMissingError, FlowExchangeUnavailableError
from autotrading.domain.flows.account_activity import AccountPosition, BalanceMovement
from autotrading.domain.flows.account_reference import AccountReference
from autotrading.domain.flows.capital_history import AccountTransfer, TransferDirection
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.flows.trade_side import TradeSide


def position(
    coin: str, size: str, *, margin: str, pnl: str, leverage: int = 5, entry: str = "60000", mark: str = "61000"
) -> dict[str, Any]:
    """A position as the clearinghouse state carries it, with the fields every reader of it requires."""
    return {
        "coin": coin,
        "szi": size,
        "leverage": {"type": "cross", "value": leverage},
        "entryPx": entry,
        "positionValue": str(abs(Decimal(size)) * Decimal(mark)),
        "unrealizedPnl": pnl,
        "marginUsed": margin,
        "liquidationPx": None,
    }


ADDRESS = "0x00000000000000000000000000000000000000Aa"
OTHER = "0x00000000000000000000000000000000000000bb"
STATE = {
    "marginSummary": {"accountValue": "1012.5"},
    "withdrawable": "862.5",
    "assetPositions": [
        {"position": position("BTC", "0.002", margin="100.0", pnl="12.5")},
        {"position": position("ETH", "-0.5", margin="50", pnl="-3", leverage=3, entry="3000.5", mark="3001")},
    ],
    "time": 1762941600000,
}


@dataclass
class FakeSdk(HyperliquidSdkAdapter):
    """Stands in for the official SDK: it answers what the test decides, or fails as the test decides."""

    state: Any = field(default_factory=lambda: STATE)
    ledger: Any = field(default_factory=list)
    abstraction: Any = "default"
    spot: Any = field(default_factory=lambda: {"balances": []})
    failure: Exception | None = None
    calls: list[tuple[str, Any]] = field(default_factory=list)

    def exchange(self, wallet: LocalAccount, base_url: str, account_address: str, timeout: float) -> FakeSdk:
        self.calls.append(("exchange", (wallet.address, base_url, account_address, timeout)))
        return self

    def info(self, base_url: str, timeout: float) -> FakeSdk:
        self.calls.append(("info", (base_url, timeout)))
        return self

    def user_state(self, address: str) -> Any:
        if self.failure is not None:
            raise self.failure
        self.calls.append(("user_state", address))
        return self.state

    def query_user_abstraction_state(self, user: str) -> Any:
        self.calls.append(("abstraction", user))
        return self.abstraction

    def spot_user_state(self, address: str) -> Any:
        self.calls.append(("spot", address))
        return self.spot

    def user_non_funding_ledger_updates(
        self,
        user: str,
        startTime: int,  # noqa: N803 - the SDK names it
        endTime: int | None = None,  # noqa: N803 - the SDK names it
    ) -> Any:
        if self.failure is not None:
            raise self.failure
        self.calls.append(("user_non_funding_ledger_updates", (user, startTime, endTime)))
        return self.ledger


def read(sdk: FakeSdk) -> Any:
    return read_reference(sdk, AccountReference({"account_address": ADDRESS}))


def read_reference(sdk: FakeSdk, reference: AccountReference) -> Any:
    return HyperliquidAccountActivityAdapter("https://exchange.invalid", sdk, 3.0).activity(reference)


def test_the_account_is_found_by_its_address_alone() -> None:
    adapter = HyperliquidAccountActivityAdapter("https://exchange.invalid", FakeSdk(), 3.0)

    assert adapter.reference_fields() == frozenset({"account_address"})


def test_the_totals_and_the_positions_are_those_of_the_exchange() -> None:
    activity = read(FakeSdk())

    assert (activity.currency, activity.balance, activity.available_margin) == (
        "USDC",
        Decimal("1012.5"),
        Decimal("862.5"),
    )
    assert activity.read_at == datetime(2025, 11, 12, 10, 0, tzinfo=UTC)
    assert activity.positions == (
        AccountPosition(
            "BTC",
            TradeSide.LONG,
            Decimal("0.002"),
            Decimal("100.0"),
            Decimal("12.5"),
            5,
            Decimal(60000),
            Decimal(61000),
        ),
        AccountPosition(
            "ETH", TradeSide.SHORT, Decimal("0.5"), Decimal(50), Decimal(-3), 3, Decimal("3000.5"), Decimal(3001)
        ),
    )


def test_the_activity_is_read_on_the_address_without_signing() -> None:
    sdk = FakeSdk()

    read(sdk)

    assert ("info", ("https://exchange.invalid", 3.0)) in sdk.calls
    assert ("user_state", ADDRESS) in sdk.calls
    assert ("user_non_funding_ledger_updates", (ADDRESS, 0, None)) in sdk.calls
    assert all(call[0] != "exchange" for call in sdk.calls)


def test_the_executions_are_not_read_with_the_activity() -> None:
    sdk = FakeSdk()

    read(sdk)

    assert all(call[0] != "user_fills_by_time" for call in sdk.calls)


@pytest.mark.parametrize(
    ("delta", "amount"),
    [
        ({"type": "deposit", "usdc": "200.0"}, Decimal(200)),
        ({"type": "withdraw", "usdc": "50", "fee": "1"}, Decimal(-50)),
        ({"type": "internalTransfer", "usdc": "10", "destination": ADDRESS.lower()}, Decimal(10)),
        ({"type": "internalTransfer", "usdc": "10", "destination": OTHER}, Decimal(-10)),
        ({"type": "subAccountTransfer", "usdc": "4", "destination": ADDRESS.upper()[2:].join(["0x", ""])}, Decimal(4)),
        ({"type": "subAccountTransfer", "usdc": "4", "destination": OTHER}, Decimal(-4)),
        ({"type": "accountClassTransfer", "usdc": "3", "toPerp": True}, Decimal(3)),
        ({"type": "accountClassTransfer", "usdc": "3", "toPerp": False}, Decimal(-3)),
    ],
)
def test_the_movements_of_the_balance_carry_their_sign(delta: dict[str, Any], amount: Decimal) -> None:
    ledger = [{"time": 1762941000000, "hash": "0xfeed", "delta": delta}]

    (movement,) = read(FakeSdk(ledger=ledger)).movements

    assert movement == BalanceMovement("0xfeed", amount, datetime(2025, 11, 12, 9, 50, tzinfo=UTC))


def test_a_ledger_update_that_moves_no_balance_is_not_a_movement() -> None:
    ledger = [{"time": 1, "hash": "0x1", "delta": {"type": "liquidation", "accountValue": "3"}}]

    assert read(FakeSdk(ledger=ledger)).movements == ()


@pytest.mark.parametrize(
    "failure",
    [
        ClientError(429, "429", "rate limited", None, None),
        ServerError(500, "boom"),
        requests.ConnectionError("down"),
        requests.Timeout("slow"),
    ],
)
def test_an_exchange_that_cannot_answer_is_unavailable(failure: Exception) -> None:
    with pytest.raises(FlowExchangeUnavailableError):
        read(FakeSdk(failure=failure))


@pytest.mark.parametrize(
    "sdk",
    [
        FakeSdk(state={"withdrawable": "1"}),
        FakeSdk(state={**STATE, "withdrawable": "many"}),
        FakeSdk(ledger=[{"time": 1, "delta": {"type": "deposit", "usdc": "1"}}]),
        FakeSdk(ledger=None),
    ],
    ids=["no summary", "not a number", "movement without hash", "no ledger"],
)
def test_an_answer_of_unexpected_shape_is_unavailable(sdk: FakeSdk) -> None:
    with pytest.raises(FlowExchangeUnavailableError):
        read(sdk)


@pytest.mark.parametrize(("testnet", "url"), [(True, TESTNET_API_URL), (False, MAINNET_API_URL)])
def test_the_activity_is_read_on_the_network_asked(*, testnet: bool, url: str) -> None:
    assert HyperliquidAccountActivityAdapter.for_network(testnet=testnet, sdk=FakeSdk()).base_url == url


def test_a_reference_without_the_address_is_refused_before_reaching_the_exchange() -> None:
    sdk = FakeSdk()

    with pytest.raises(FlowCredentialsFieldMissingError):
        read_reference(sdk, AccountReference({"wallet": ADDRESS}))

    assert sdk.calls == []


def test_a_unified_account_shows_the_usdc_it_holds_as_balance() -> None:
    perps = {
        "marginSummary": {"accountValue": "0.0"},
        "withdrawable": "0.0",
        "assetPositions": [],
        "time": 1762941600000,
    }
    spot = {"balances": [{"coin": "USDC", "token": 0, "total": "999.0", "hold": "0.0", "entryNtl": "0.0"}]}

    activity = read(FakeSdk(state=perps, abstraction="unifiedAccount", spot=spot))

    assert (activity.balance, activity.available_margin) == (Decimal(999), Decimal(999))


# R3.4.2, ADR storico-delle-variazioni-di-capitale: the deposits and withdrawals of the history of an account.
DEPOSITED = {"time": 1762941000000, "hash": "0x1", "delta": {"type": "deposit", "usdc": "500.5"}}
EVER = TimeWindow()
WITHDRAWN = {"time": 1762944600000, "hash": "0x2", "delta": {"type": "withdraw", "usdc": "300", "fee": "1"}}


def transfers_of(sdk: FakeSdk, window: TimeWindow = EVER) -> tuple[AccountTransfer, ...]:
    adapter = HyperliquidAccountActivityAdapter("https://exchange.invalid", sdk, 3.0)
    return adapter.transfers(AccountReference({"account_address": ADDRESS}), window)


def test_the_deposits_and_withdrawals_are_those_the_exchange_declares_with_their_instant() -> None:
    assert transfers_of(FakeSdk(ledger=[DEPOSITED, WITHDRAWN])) == (
        AccountTransfer(datetime(2025, 11, 12, 9, 50, tzinfo=UTC), Decimal("500.5"), TransferDirection.DEPOSIT),
        AccountTransfer(datetime(2025, 11, 12, 10, 50, tzinfo=UTC), Decimal(300), TransferDirection.WITHDRAWAL),
    )


@pytest.mark.parametrize(
    "delta",
    [
        {"type": "internalTransfer", "usdc": "10", "destination": OTHER},
        {"type": "accountClassTransfer", "usdc": "3", "toPerp": True},
        {"type": "liquidation", "accountValue": "3"},
    ],
)
def test_a_ledger_update_that_is_neither_a_deposit_nor_a_withdrawal_is_left_out(delta: dict[str, Any]) -> None:
    assert transfers_of(FakeSdk(ledger=[{"time": 1, "hash": "0x3", "delta": delta}])) == ()


def test_the_window_is_asked_to_the_exchange_and_its_end_is_excluded() -> None:
    sdk = FakeSdk(ledger=[DEPOSITED, WITHDRAWN])
    window = TimeWindow(datetime(2025, 11, 12, 9, tzinfo=UTC), datetime(2025, 11, 12, 10, 50, tzinfo=UTC))

    (transfer,) = transfers_of(sdk, window)

    assert transfer.direction is TransferDirection.DEPOSIT
    assert ("user_non_funding_ledger_updates", (ADDRESS, 1762938000000, 1762944600000)) in sdk.calls
    assert all(call[0] not in {"exchange", "user_state"} for call in sdk.calls)


def test_without_a_window_every_transfer_is_asked_from_the_start() -> None:
    sdk = FakeSdk(ledger=[])

    transfers_of(sdk)

    assert ("user_non_funding_ledger_updates", (ADDRESS, 0, None)) in sdk.calls


@pytest.mark.parametrize(
    "sdk",
    [
        FakeSdk(failure=requests.ConnectionError("down")),
        FakeSdk(ledger=[{"time": 1, "hash": "0x4", "delta": {"type": "deposit"}}]),
        FakeSdk(ledger=None),
    ],
    ids=["out of reach", "deposit without amount", "no ledger"],
)
def test_transfers_that_cannot_be_read_whole_are_unavailable(sdk: FakeSdk) -> None:
    with pytest.raises(FlowExchangeUnavailableError):
        transfers_of(sdk)


def test_the_transfers_of_a_reference_without_the_address_are_refused_before_reaching_the_exchange() -> None:
    sdk = FakeSdk()

    with pytest.raises(FlowCredentialsFieldMissingError):
        HyperliquidAccountActivityAdapter("https://exchange.invalid", sdk, 3.0).transfers(
            AccountReference({"wallet": ADDRESS}), TimeWindow()
        )

    assert sdk.calls == []
