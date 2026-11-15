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
    AGENT_NOT_AUTHORIZED_MESSAGE,
    MISSING_FIELD_MESSAGE,
    PROBE_COIN,
    SIGNER_IS_AGENT_MESSAGE,
    TIMEOUT_SECONDS,
    HyperliquidExchangeAdapter,
    HyperliquidSdkAdapter,
    HyperliquidTestnetExchangeAdapter,
)
from autotrading.application.accounts.errors import (
    CredentialFieldMalformedError,
    ExchangeRejectedCredentialsError,
    ExchangeUnavailableError,
)
from autotrading.application.flows.errors import FlowCredentialsRefusedError, FlowExchangeUnavailableError
from autotrading.application.verification.errors import (
    VerificationCredentialsRejectedError,
    VerificationExchangeUnavailableError,
)
from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.balance import Balance
from autotrading.domain.accounts.credential_field import CredentialField
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.position import Position, PositionSide
from autotrading.domain.flows.cycle_access import CycleAccess
from autotrading.domain.flows.cycle_account import CycleAccount, CyclePosition
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.verification.reading import AccountReading, PositionReading
from autotrading.domain.verification.verification_access import VerificationAccess
from tests.support.credentials import hyperliquid_credentials

BASE_URL = "https://api.hyperliquid-testnet.xyz"
WALLET = EthereumAccount.create()
ADDRESS = "0xAbCdEf0000000000000000000000000000000001"
CREDENTIALS = hyperliquid_credentials(ADDRESS, WALLET.key.hex())
KEY_DIGITS = WALLET.key.hex().removeprefix("0x")
ACCEPTED = {"status": "ok", "response": {"type": "cancel", "data": {"statuses": [{"error": "never placed"}]}}}
READ_AT_MS = 1_794_307_200_000
READING_CALLS = ["exchange", "cancel", "info", "role", "user_state", "abstraction", "spot"]
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
class FakeSdk(HyperliquidSdkAdapter):
    """Stands in for the official SDK: it records the calls and answers what the test decides."""

    cancel_answer: Any = field(default_factory=lambda: ACCEPTED)
    state: Any = field(default_factory=lambda: STATE)
    abstraction: Any = "default"
    role: Any = field(default_factory=lambda: {"role": "agent", "data": {"user": ADDRESS.lower()}})
    spot: Any = field(default_factory=lambda: {"balances": []})
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

    def user_role(self, user: str) -> Any:
        self.calls.append(("role", user))
        if isinstance(self.role, Exception):
            raise self.role
        return self.role

    def user_state(self, address: str) -> Any:
        self.calls.append(("user_state", address))
        return self.state

    def query_user_abstraction_state(self, user: str) -> Any:
        self.calls.append(("abstraction", user))
        if isinstance(self.abstraction, Exception):
            raise self.abstraction
        return self.abstraction

    def spot_user_state(self, address: str) -> Any:
        self.calls.append(("spot", address))
        return self.spot


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
    assert [name for name, _ in sdk.calls] == [
        "exchange",
        "cancel",
        "info",
        "role",
        "user_state",
        "abstraction",
        "spot",
    ]
    assert sdk.calls[0][1] == (WALLET.address, BASE_URL, ADDRESS, TIMEOUT_SECONDS)
    assert sdk.calls[3][1] == WALLET.address
    assert sdk.calls[4][1] == ADDRESS


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


@pytest.mark.parametrize(
    ("key", "shape"),
    [
        ("not-a-key", "ricevuti 9 caratteri, di cui 7 non esadecimali"),
        (ADDRESS, "ricevuti 42 caratteri"),
        ("0x" + "ab" * 31, "ricevuti 64 caratteri"),
        ("0x" + "zz" * 32, "ricevuti 66 caratteri, di cui 64 non esadecimali"),
    ],
)
def test_a_key_of_the_wrong_shape_names_its_field_and_what_is_wrong_without_reaching_the_exchange(
    key: str, shape: str
) -> None:
    sdk = FakeSdk()

    with pytest.raises(CredentialFieldMalformedError) as raised:
        read(sdk, hyperliquid_credentials(ADDRESS, key))

    assert raised.value.field == "secret_key"
    assert raised.value.exchange_message == (
        f"chiave dell'API wallet non valida: attese 64 cifre esadecimali, con o senza 0x; {shape}"
    )
    assert sdk.calls == []


@pytest.mark.parametrize(
    ("address", "shape"),
    [
        ("1111111111111111111111111111111111111111", "ricevuti 40 caratteri"),
        ("0x" + "1" * 39, "ricevuti 41 caratteri"),
        ("0x" + "g" * 40, "ricevuti 42 caratteri, di cui 40 non esadecimali"),
    ],
)
def test_an_address_of_the_wrong_shape_names_its_field_without_reaching_the_exchange(address: str, shape: str) -> None:
    sdk = FakeSdk()

    with pytest.raises(CredentialFieldMalformedError) as raised:
        read(sdk, hyperliquid_credentials(address, WALLET.key.hex()))

    assert raised.value.field == "account_address"
    assert raised.value.exchange_message == (
        f"indirizzo del conto non valido: atteso 0x seguito da 40 cifre esadecimali; {shape}"
    )
    assert sdk.calls == []


def test_the_reason_of_a_wrong_shape_never_shows_the_value() -> None:
    key = "0x" + "q7" * 32

    with pytest.raises(CredentialFieldMalformedError) as raised:
        read(FakeSdk(), hyperliquid_credentials(ADDRESS, key))

    assert "q7" not in str(raised.value.details)


@pytest.mark.parametrize("key", [KEY_DIGITS, "0x" + KEY_DIGITS.upper(), "0X" + KEY_DIGITS])
def test_a_key_with_or_without_prefix_in_any_case_is_accepted(key: str) -> None:
    sdk = FakeSdk()

    read(sdk, hyperliquid_credentials(ADDRESS, key))

    assert sdk.calls[0] == ("exchange", (WALLET.address, BASE_URL, ADDRESS, TIMEOUT_SECONDS))


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


def test_the_real_exchange_reads_the_account_on_the_real_network() -> None:
    sdk = FakeSdk()

    HyperliquidExchangeAdapter(sdk=sdk).read_state(CREDENTIALS)

    assert sdk.calls[0][1][1] == MAINNET_API_URL


def test_the_test_exchange_reads_the_account_on_the_testnet_the_same_way() -> None:
    sdk = FakeSdk()

    state = HyperliquidTestnetExchangeAdapter(sdk=sdk).read_state(CREDENTIALS)

    assert sdk.calls[0][1][1] == TESTNET_API_URL
    assert state == read(FakeSdk())


VERIFICATION_ACCESS = VerificationAccess({"account_address": ADDRESS, "secret_key": WALLET.key.hex()})


def test_the_verification_reads_balance_margin_and_positions_proving_the_signer() -> None:
    sdk = FakeSdk(state=STATE | {"assetPositions": [{"type": "oneWay", "position": LONG_BTC}]})

    reading = HyperliquidExchangeAdapter(BASE_URL, sdk).verification_reading(VERIFICATION_ACCESS)

    assert reading == AccountReading(
        Decimal("1234.56"), Decimal("1000.5"), "USDC", (PositionReading("BTC", "long", Decimal("0.02"), 2),)
    )
    assert [name for name, _ in sdk.calls] == [
        "exchange",
        "cancel",
        "info",
        "role",
        "user_state",
        "abstraction",
        "spot",
    ]


def test_a_signer_refused_is_a_failed_verification_step_without_the_message_of_the_exchange() -> None:
    sdk = FakeSdk(cancel_answer={"status": "err", "response": f"User or API Wallet {ADDRESS} does not exist."})

    with pytest.raises(VerificationCredentialsRejectedError) as raised:
        HyperliquidExchangeAdapter(BASE_URL, sdk).verification_reading(VERIFICATION_ACCESS)

    assert raised.value.message == "credenziali rifiutate dall'exchange"


def test_an_exchange_that_does_not_answer_is_a_failed_verification_step() -> None:
    sdk = FakeSdk(failure=ServerError(502, "bad gateway"))

    with pytest.raises(VerificationExchangeUnavailableError) as raised:
        HyperliquidExchangeAdapter(BASE_URL, sdk).verification_reading(VERIFICATION_ACCESS)

    assert raised.value.message == "exchange non raggiungibile, riprovare"


CYCLE_ACCESS = CycleAccess({"account_address": ADDRESS, "secret_key": WALLET.key.hex()})


def test_the_cycle_reads_margin_and_positions_proving_the_signer() -> None:
    sdk = FakeSdk(state=STATE | {"assetPositions": [{"type": "oneWay", "position": LONG_BTC}]})

    account = HyperliquidExchangeAdapter(BASE_URL, sdk).cycle_reading(CYCLE_ACCESS)

    position = CyclePosition(
        "BTC", TradeSide.LONG, Decimal("0.02"), 2, Decimal("60000.0"), Decimal("12.5"), Decimal("31000.0")
    )
    assert account == CycleAccount("USDC", Decimal("1000.5"), (position,))
    assert [name for name, _ in sdk.calls] == [
        "exchange",
        "cancel",
        "info",
        "role",
        "user_state",
        "abstraction",
        "spot",
    ]


def test_a_signer_refused_is_a_refusal_of_the_credentials_of_the_flow() -> None:
    sdk = FakeSdk(cancel_answer={"status": "err", "response": f"User or API Wallet {ADDRESS} does not exist."})

    with pytest.raises(FlowCredentialsRefusedError, match=r"^credenziali rifiutate dall'exchange$"):
        HyperliquidExchangeAdapter(BASE_URL, sdk).cycle_reading(CYCLE_ACCESS)


def test_an_exchange_that_does_not_answer_the_cycle_is_unavailable() -> None:
    sdk = FakeSdk(failure=ServerError(502, "bad gateway"))

    with pytest.raises(FlowExchangeUnavailableError, match=r"^exchange non raggiungibile, riprovare$"):
        HyperliquidExchangeAdapter(BASE_URL, sdk).cycle_reading(CYCLE_ACCESS)


def test_declares_the_address_of_the_account_and_the_key_of_the_api_wallet() -> None:
    """R2.3.9: the names are the keys of the credentials already sealed (ADR 0158)."""
    assert HyperliquidExchangeAdapter(TESTNET_API_URL).credential_fields() == (
        CredentialField("account_address", "Indirizzo del conto", secret=False),
        CredentialField("secret_key", "Chiave dell'API wallet", secret=True),
    )


@pytest.mark.parametrize(
    ("adapter", "real", "name"),
    [(HyperliquidExchangeAdapter, True, "mainnet"), (HyperliquidTestnetExchangeAdapter, False, "testnet")],
)
def test_each_exchange_declares_its_network_with_the_name_hyperliquid_gives_it(
    adapter: type[HyperliquidExchangeAdapter], real: bool, name: str
) -> None:
    exchange = adapter(sdk=FakeSdk())

    assert (exchange.is_real(), exchange.network_name()) == (real, name)


@pytest.mark.parametrize("missing", ["account_address", "secret_key"])
def test_credentials_without_a_field_of_the_exchange_are_rejected_without_reaching_it(missing: str) -> None:
    sdk = FakeSdk()
    fields = {name: value for name, value in CREDENTIALS.values.items() if name != missing}

    with pytest.raises(ExchangeRejectedCredentialsError) as raised:
        read(sdk, Credentials(fields))

    assert raised.value.exchange_message == MISSING_FIELD_MESSAGE
    assert sdk.calls == []


def test_a_cycle_access_without_a_field_of_the_exchange_is_refused() -> None:
    with pytest.raises(FlowCredentialsRefusedError):
        HyperliquidExchangeAdapter(BASE_URL, FakeSdk()).cycle_reading(CycleAccess({"account_address": ADDRESS}))


def test_a_verification_access_without_a_field_of_the_exchange_is_rejected() -> None:
    with pytest.raises(VerificationCredentialsRejectedError):
        HyperliquidExchangeAdapter(BASE_URL, FakeSdk()).verification_reading(
            VerificationAccess({"account_address": ADDRESS})
        )


def test_sixty_four_hex_digits_that_are_no_key_of_the_curve_are_refused_by_field() -> None:
    sdk = FakeSdk()

    with pytest.raises(CredentialFieldMalformedError) as raised:
        read(sdk, hyperliquid_credentials(ADDRESS, "0x" + "0" * 64))

    assert (raised.value.field, raised.value.exchange_message) == ("secret_key", "chiave dell'API wallet non valida")
    assert sdk.calls == []


UNIFIED_SPOT = {"balances": [{"coin": "USDC", "token": 0, "total": "999.0", "hold": "0.0", "entryNtl": "0.0"}]}
EMPTY_PERPS = {
    "marginSummary": {"accountValue": "0.0"},
    "withdrawable": "0.0",
    "assetPositions": [],
    "time": READ_AT_MS,
}


def test_a_unified_account_reads_the_usdc_it_holds_as_balance_and_available_margin() -> None:
    sdk = FakeSdk(state=EMPTY_PERPS, abstraction="unifiedAccount", spot=UNIFIED_SPOT)

    state = read(sdk)

    assert (state.balance, state.available_margin) == (Balance(Decimal(999), "USDC"), Balance(Decimal(999), "USDC"))
    assert ("abstraction", ADDRESS) in sdk.calls
    assert ("spot", ADDRESS) in sdk.calls


@pytest.mark.parametrize("answer", ["spot", "abstraction"])
def test_a_mode_or_spot_state_the_exchange_does_not_give_makes_it_unavailable(answer: str) -> None:
    sdk = FakeSdk(abstraction="unifiedAccount", spot={"balances": [{"coin": "USDC"}]})
    if answer == "abstraction":
        sdk = FakeSdk(abstraction=ServerError(500, "down"))

    with pytest.raises(ExchangeUnavailableError):
        read(sdk)


def test_an_api_wallet_approved_for_the_account_address_in_any_case_is_accepted() -> None:
    sdk = FakeSdk(role={"role": "agent", "data": {"user": ADDRESS.upper().replace("0X", "0x")}})

    assert read(sdk).balance == Balance(Decimal("1234.56"), "USDC")


def test_the_account_signing_for_itself_is_accepted() -> None:
    sdk = FakeSdk(role={"role": "user"})

    assert read(sdk, hyperliquid_credentials(WALLET.address, WALLET.key.hex())).balance.currency == "USDC"


def test_an_api_wallet_approved_for_another_account_is_rejected_without_reading_the_state() -> None:
    sdk = FakeSdk(role={"role": "agent", "data": {"user": "0x" + "1" * 40}})

    with pytest.raises(ExchangeRejectedCredentialsError) as raised:
        read(sdk)

    assert raised.value.exchange_message == AGENT_NOT_AUTHORIZED_MESSAGE
    assert "user_state" not in [name for name, _ in sdk.calls]


@pytest.mark.parametrize("role", [{"role": "user"}, {"role": "missing"}, {"role": "vault"}])
def test_a_signer_that_is_no_api_wallet_of_the_account_is_rejected(role: object) -> None:
    with pytest.raises(ExchangeRejectedCredentialsError) as raised:
        read(FakeSdk(role=role))

    assert raised.value.exchange_message == AGENT_NOT_AUTHORIZED_MESSAGE


def test_the_address_of_the_api_wallet_given_as_address_of_the_account_is_rejected() -> None:
    sdk = FakeSdk(role={"role": "agent", "data": {"user": ADDRESS.lower()}})

    with pytest.raises(ExchangeRejectedCredentialsError) as raised:
        read(sdk, hyperliquid_credentials(WALLET.address.lower(), WALLET.key.hex()))

    assert raised.value.exchange_message == SIGNER_IS_AGENT_MESSAGE
    assert KEY_DIGITS not in str(raised.value.details)


@pytest.mark.parametrize("role", [None, {"data": {}}, {"role": "agent"}, {"role": "agent", "data": {}}, "agent"])
def test_a_role_of_unexpected_shape_makes_the_exchange_unavailable(role: object) -> None:
    with pytest.raises(ExchangeUnavailableError):
        read(FakeSdk(role=role))


def test_a_role_the_exchange_does_not_give_makes_it_unavailable() -> None:
    with pytest.raises(ExchangeUnavailableError):
        read(FakeSdk(role=ServerError(500, "down")))
