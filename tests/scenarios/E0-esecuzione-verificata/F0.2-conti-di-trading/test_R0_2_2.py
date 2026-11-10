from dataclasses import dataclass, field
from decimal import Decimal

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.accounts.errors import ExchangeRejectedCredentialsError
from autotrading.application.accounts.read_account_state import ReadAccountStateCommand
from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.balance import Balance
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.position import Position, PositionSide
from autotrading.domain.errors import AutotradingError
from tests.fakes.exchange import REDACTED_REJECTION
from tests.support.platform import Platform, registration
from tests.support.steps import quoted

scenarios("E0-esecuzione-verificata/F0.2-conti-di-trading/R0.2.2-lettura-dello-stato-del-conto.feature")


@dataclass
class Reading:
    credentials: dict[str, Credentials] = field(default_factory=dict)
    outcome: AccountState | AutotradingError | None = None

    def state(self) -> AccountState:
        assert isinstance(self.outcome, AccountState), f"the reading failed: {self.outcome}"
        return self.outcome

    def error(self) -> AutotradingError:
        assert isinstance(self.outcome, AutotradingError), f"the reading did not fail: {self.outcome}"
        return self.outcome

    def position(self, coin: str) -> Position:
        (position,) = [position for position in self.state().positions if position.coin == coin]
        return position


@pytest.fixture
def platform() -> Platform:
    return Platform()


@pytest.fixture
def reading() -> Reading:
    return Reading()


@given(quoted('che "{user}" ha il conto "{account}" su "{exchange}"'))
def user_has_account(platform: Platform, reading: Reading, user: str, account: str, exchange: str) -> None:
    platform.directory.person(user).roles.add("Utente")
    reading.credentials[account] = platform.accepted_credentials()
    platform.register_account(user, registration(account, exchange, reading.credentials[account]))


@given(quoted('che sull\'exchange il conto "{account}" ha saldo {amount} USDC e nessuna posizione aperta'))
def account_without_positions(platform: Platform, reading: Reading, account: str, amount: str) -> None:
    platform.hyperliquid.accept(reading.credentials[account], Decimal(amount))


@given(quoted('che sull\'exchange il conto "{account}" ha una posizione long su "{coin}" con leva {leverage}'))
def account_with_long_position(platform: Platform, reading: Reading, account: str, coin: str, leverage: str) -> None:
    position = Position(
        coin, PositionSide.LONG, Decimal("0.01"), int(leverage), Decimal(60000), Decimal("5.5"), Decimal(30000)
    )
    platform.hyperliquid.open_position(reading.credentials[account], position)


@given(quoted('che l\'exchange "{exchange}" non risponde'))
def exchange_down(platform: Platform, exchange: str) -> None:
    platform.exchanges[exchange].reachable = False


@given(quoted('che l\'exchange rifiuta ora le credenziali del conto "{account}"'))
def credentials_revoked(platform: Platform, reading: Reading, account: str) -> None:
    platform.hyperliquid.revoke(reading.credentials[account])


@when(quoted('"{user}" chiede lo stato del conto "{account}"'))
def ask_state(platform: Platform, reading: Reading, user: str, account: str) -> None:
    command = ReadAccountStateCommand(platform.account_named(user, account).id)
    try:
        reading.outcome = platform.use_cases_of(user).read_account_state.execute(command)
    except AutotradingError as error:
        reading.outcome = error


@then(quoted("lo stato riporta il saldo {amount} USDC"))
def reports_balance(reading: Reading, amount: str) -> None:
    assert reading.state().balance == Balance(Decimal(amount), "USDC")


@then(quoted("lo stato riporta il margine disponibile {amount} USDC"))
def reports_available_margin(reading: Reading, amount: str) -> None:
    assert reading.state().available_margin == Balance(Decimal(amount), "USDC")


@then("lo stato riporta nessuna posizione aperta")
def reports_no_position(reading: Reading) -> None:
    assert reading.state().positions == ()


@then("lo stato riporta l'istante della lettura")
def reports_read_at(reading: Reading) -> None:
    assert reading.state().read_at.tzinfo is not None


@then(quoted('lo stato riporta per "{coin}" la direzione "{side}"'))
def reports_side(reading: Reading, coin: str, side: str) -> None:
    assert reading.position(coin).side == PositionSide(side)


@then(quoted('lo stato riporta per "{coin}" la dimensione'))
def reports_size(reading: Reading, coin: str) -> None:
    assert reading.position(coin).size == Decimal("0.01")


@then(quoted('lo stato riporta per "{coin}" la leva {leverage}'))
def reports_leverage(reading: Reading, coin: str, leverage: str) -> None:
    assert reading.position(coin).leverage == int(leverage)


@then(quoted('lo stato riporta per "{coin}" il prezzo di ingresso'))
def reports_entry_price(reading: Reading, coin: str) -> None:
    assert reading.position(coin).entry_price == Decimal(60000)


@then(quoted('lo stato riporta per "{coin}" il profitto o la perdita non realizzati'))
def reports_unrealized_pnl(reading: Reading, coin: str) -> None:
    assert reading.position(coin).unrealized_pnl == Decimal("5.5")


@then(quoted('lo stato riporta per "{coin}" il prezzo di liquidazione'))
def reports_liquidation_price(reading: Reading, coin: str) -> None:
    assert reading.position(coin).liquidation_price == Decimal(30000)


@then(quoted('la richiesta fallisce con il motivo "{reason}"'))
def request_fails(reading: Reading, reason: str) -> None:
    assert str(reading.error()) == reason


@then("l'esito non riporta valori di saldo")
def reports_no_balance(reading: Reading) -> None:
    error = reading.error()
    assert "1000" not in f"{error} {vars(error)}"


@then("l'esito riporta il messaggio originale dell'exchange")
def reports_exchange_message(reading: Reading) -> None:
    error = reading.error()
    assert isinstance(error, ExchangeRejectedCredentialsError)
    assert error.exchange_message == REDACTED_REJECTION
