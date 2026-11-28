"""Bug 778: a closing the exchange makes between two cycles enters the history within the reconciliation interval of the
account, read by the periodic check of the accounts with open positions, run as the worker and the API compose it (ADR
riconciliazione-periodica-dei-conti-con-posizioni-aperte, ADR intervallo-di-riconciliazione-del-conto).

"principale" is the account the flow of the context of the requirement already operates on; every minute that passes
runs the periodic check once, as the worker does, with the exchange reading the account at that minute.
"""

from collections.abc import Iterator
from contextlib import ExitStack
from dataclasses import dataclass, field, replace
from datetime import timedelta
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, then, when

from autotrading.application.accounts.account_summary import AccountSummary
from autotrading.application.accounts.get_account import GetAccountCommand
from autotrading.application.accounts.set_reconciliation_interval import SetReconciliationIntervalCommand
from autotrading.application.flows.reconcile_open_accounts import ReconcileOpenAccountsCommand
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.reconciliation_interval import ReconciliationInterval
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.account_activity import AccountPosition
from autotrading.domain.flows.account_reconciliation import AccountReading
from autotrading.domain.flows.closed_position import ClosedPosition
from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.ledger import FlowTotals
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.protection_kind import ProtectionKind
from tests.support.activity import a_fill, an_activity
from tests.support.flow_cycles import ACCOUNT, FlowCycles
from tests.support.platform import HYPERLIQUID
from tests.support.steps import quoted
from tests.support.steps_r3_1_2 import Protection, plan_of

USER = "anna"
# The account of the flow of the context of the requirement is the one the scenarios call "principale".
ACCOUNT_NAMES = {"principale": ACCOUNT}
ASSET = "BLUR"
PRICE = Decimal(1)
MARKET = Market(ASSET, max_leverage=10, size_decimals=0, mid_price=PRICE, min_order_value=Decimal(10))
DAY_MINUTES = 24 * 60
CYCLE_HOUR = "10:15"
# What the exchange reports of the execution of the stop loss, half a minute after the last cycle.
STOP_PNL = Decimal("-1.10")
STOP_FEE = Decimal("0.01")
STOP_DELAY = timedelta(seconds=30)
ONE_MINUTE = timedelta(minutes=1)
WARNING = "riconciliazione del conto non riuscita"


@dataclass
class PeriodicReconciliation:
    """The flow of the account with its position on the exchange, the minutes that pass and what the user read."""

    protection: Protection
    held: ExitStack = field(default_factory=ExitStack)
    funds_before: Decimal = Decimal(0)
    reading_of_the_cycle: AccountReading | None = None
    readings_before: int = 0
    summary: AccountSummary | None = None
    error: AutotradingError | None = None

    @property
    def flow_cycles(self) -> FlowCycles:
        return self.protection.flow_cycles

    def account_id(self, account: str) -> AccountId:
        return AccountId(self.flow_cycles.account_of(USER, ACCOUNT_NAMES.get(account, account)))

    def address(self, account: str) -> str:
        tenant_id = self.flow_cycles.platform.tenant_of(USER)
        return self.flow_cycles.credentials[tenant_id, ACCOUNT_NAMES.get(account, account)].value("account_address")

    def show(self, account: str, positions: tuple[AccountPosition, ...]) -> None:
        """What the exchange shows of the account at this minute."""
        activity = an_activity(positions=positions, read_at=self.flow_cycles.clock.now())
        self.flow_cycles.platform.activity_reader.activities[self.address(account)] = activity

    def minutes_pass(self, minutes: int) -> None:
        """The worker checks the accounts once a minute, the exchange reading each account at that minute."""
        flow_cycles = self.flow_cycles
        activities = flow_cycles.platform.activity_reader.activities
        for _ in range(minutes):
            flow_cycles.clock.current += ONE_MINUTE
            for address, activity in activities.items():
                activities[address] = replace(activity, read_at=flow_cycles.clock.now())
            check = flow_cycles.open_accounts_of(flow_cycles.platform.tenant_of(USER))
            check.execute(ReconcileOpenAccountsCommand())

    def readings_of(self, account: str) -> int:
        """How many times the account was read from the exchange: every reconciliation reads its new executions."""
        address = self.address(account)
        return sum(1 for read, _ in self.flow_cycles.platform.activity_reader.readings if read == address)

    def last_reading(self, account: str) -> AccountReading | None:
        return self.flow_cycles.readings.last_reading(self.account_id(account).value)

    def interval(self, account: str, interval: ReconciliationInterval | None) -> None:
        """The interval as the account holds it now: a step that names it sets it in the database."""
        accounts = self.flow_cycles.platform.accounts.accounts
        recorded = self.flow_cycles.platform.account_named(USER, ACCOUNT_NAMES.get(account, account))
        accounts[accounts.index(recorded)] = replace(recorded, reconciliation_interval=interval)

    def funds(self, flow: str) -> Decimal:
        """The money of the flow, from the totals of its ledger (ADR 0063)."""
        recorded = self.flow_cycles.flow(flow)
        totals = self.flow_cycles.platform.ledger.totals_of((recorded.id,)).get(recorded.id) or FlowTotals(recorded.id)
        return recorded.configuration.assigned_capital + totals.realized_pnl - totals.fees + totals.funding

    def closed(self, flow: str, asset: str) -> list[ClosedPosition]:
        return self.protection.closed(flow, asset)

    def set_interval(self, user: str, account: str, minutes: int) -> None:
        use_cases = self.flow_cycles.platform.use_cases_of(user)
        try:
            use_cases.set_reconciliation_interval.execute(
                SetReconciliationIntervalCommand(self.account_id(account), minutes)
            )
        except AutotradingError as error:
            self.error = error
            return
        self.read_account(user, account)

    def read_account(self, user: str, account: str) -> None:
        use_cases = self.flow_cycles.platform.use_cases_of(user)
        self.summary = use_cases.get_account.execute(GetAccountCommand(self.account_id(account)))


@pytest.fixture
def periodic(flow_cycles: FlowCycles) -> Iterator[PeriodicReconciliation]:
    steps = PeriodicReconciliation(Protection(flow_cycles))
    with steps.held:
        yield steps


# Given


@given(quoted('che il flusso "{flow}" opera sul conto "{account}" con un ciclo ogni 24 ore'))
def flow_of_a_day(periodic: PeriodicReconciliation, flow: str, account: str) -> None:
    flow_cycles = periodic.flow_cycles
    flow_cycles.platform.order_exchange.markets[ASSET] = MARKET
    flow_cycles.platform.markets[HYPERLIQUID].assets |= {ASSET}
    flow_cycles.reconfigure(
        flow, lambda configuration: replace(configuration, assets=(ASSET,), cycle_interval=CycleInterval(DAY_MINUTES))
    )
    assert flow_cycles.flow(flow).assigned_account_id == periodic.account_id(account).value


@given(quoted('che "{flow}" ha una posizione long su "{asset}" con stop loss sull\'exchange'))
def position_protected_on_the_exchange(periodic: PeriodicReconciliation, flow: str, asset: str) -> None:
    flow_cycles, protection = periodic.flow_cycles, periodic.protection
    protection.at_price(asset, PRICE)
    protection.open(flow, "long", asset, plan_of())
    held = flow_cycles.platform.order_exchange.positions[periodic.address("principale"), asset]
    position = AccountPosition(
        asset, TradeSide.LONG, held.size, Decimal(10), Decimal(0), held.leverage, held.entry_price, held.entry_price
    )
    flow_cycles.platform.ledger.expect(flow_cycles.flow(flow).id, asset, held.size)
    # The cycle of the flow reads the account with the position open: the next reconciliation compares with it.
    flow_cycles.clock.current = flow_cycles.clock.now().replace(hour=10, minute=15)
    periodic.show("principale", (position,))
    flow_cycles.run(flow, CYCLE_HOUR)
    periodic.reading_of_the_cycle = periodic.last_reading("principale")
    assert periodic.reading_of_the_cycle is not None
    assert periodic.reading_of_the_cycle.read_at == flow_cycles.clock.now()
    assert [each.kind for each in protection.protections(flow, asset)] == [ProtectionKind.STOP_LOSS]


@given(quoted('che il conto "{account}" non ha un intervallo di riconciliazione impostato'))
def account_without_interval(periodic: PeriodicReconciliation, account: str) -> None:
    periodic.interval(account, None)
    recorded = periodic.flow_cycles.platform.account_named(USER, ACCOUNT_NAMES.get(account, account))
    assert recorded.reconciliation_interval is None


@given(quoted('che il conto "{account}" ha l\'intervallo di riconciliazione di {minutes} minuti'))
def account_interval(periodic: PeriodicReconciliation, account: str, minutes: str) -> None:
    periodic.interval(account, ReconciliationInterval(int(minutes)))


@given(quoted('che i flussi del conto "{account}" non hanno posizioni aperte all\'ultima lettura'))
def account_without_positions(periodic: PeriodicReconciliation, account: str) -> None:
    flow_cycles = periodic.flow_cycles
    beta = flow_cycles.add_flow(USER, "beta", assets=("ETH",), account=account)
    periodic.show(account, ())
    reading = AccountReading(beta.assigned_account_id, flow_cycles.clock.now(), {beta.id: frozenset()})
    flow_cycles.readings.save_reading(reading)
    periodic.readings_before = periodic.readings_of(account)


@given(quoted('che un ciclo di "{flow}" è in corso'))
def cycle_running(periodic: PeriodicReconciliation, flow: str) -> None:
    flow_cycles = periodic.flow_cycles
    assert periodic.held.enter_context(flow_cycles.lock.hold(flow_cycles.flow(flow).id.value))
    periodic.readings_before = periodic.readings_of("principale")


@given(quoted('che l\'exchange del conto "{account}" non risponde'))
def exchange_away(periodic: PeriodicReconciliation, account: str) -> None:
    periodic.flow_cycles.platform.activity_reader.reachable = False
    periodic.readings_before = periodic.readings_of(account)


# When


@when(quoted('lo stop loss di "{asset}" si esegue sull\'exchange'))
def stop_executes(periodic: PeriodicReconciliation, asset: str) -> None:
    flow_cycles = periodic.flow_cycles
    platform, address = flow_cycles.platform, periodic.address("principale")
    periodic.funds_before = periodic.funds("alfa")
    executed = platform.protection_exchange.execute(address, asset, ProtectionKind.STOP_LOSS)
    held = platform.order_exchange.positions.pop((address, asset))
    periodic.show("principale", ())
    fill = a_fill(
        asset,
        executed.client_order_id.value,
        realized_pnl=STOP_PNL,
        fee=STOP_FEE,
        executed_at=flow_cycles.clock.now() + STOP_DELAY,
        fill_id="stop",
        size=-held.size,
        start_position=held.size,
    )
    platform.activity_reader.executions.setdefault(address, []).append(fill)
    periodic.readings_before = periodic.readings_of("principale")


@when(parsers.re(r"^passano (?P<minutes>\d+) minuti(?: senza un ciclo di \"(?P<flow>[^\"]+)\")?$"))
def minutes_pass(periodic: PeriodicReconciliation, minutes: str) -> None:
    cycles_before = len(periodic.flow_cycles.records.records)
    periodic.minutes_pass(int(minutes))
    assert len(periodic.flow_cycles.records.records) == cycles_before


@when(quoted('"{user}" legge il conto "{account}" senza aver impostato l\'intervallo di riconciliazione'))
def reads_account(periodic: PeriodicReconciliation, user: str, account: str) -> None:
    periodic.read_account(user, account)


@when(
    parsers.re(
        r'^"(?P<user>[^"]+)" imposta l\'intervallo di riconciliazione del conto "(?P<account>[^"]+)" a '
        r"(?P<minutes>\d+)(?: minuti)?$"
    )
)
def sets_interval(periodic: PeriodicReconciliation, user: str, account: str, minutes: str) -> None:
    periodic.set_interval(user, account, int(minutes))


# Then


@then(
    quoted(
        'lo storico di "{flow}" ha la posizione "{asset}" chiusa con il motivo "{reason}" e l\'esito letto '
        "dall'exchange"
    )
)
def closed_with_outcome(periodic: PeriodicReconciliation, flow: str, asset: str, reason: str) -> None:
    [closed] = periodic.closed(flow, asset)
    assert (closed.reason.value, closed.pnl, closed.side) == (reason, STOP_PNL, TradeSide.LONG)


@then(quoted('i soldi di "{flow}" includono il risultato della chiusura'))
def funds_with_outcome(periodic: PeriodicReconciliation, flow: str) -> None:
    assert periodic.funds(flow) == periodic.funds_before + STOP_PNL - STOP_FEE


@then(quoted('il conto "{account}" non è stato letto dall\'exchange'))
@then(quoted('il controllo periodico non legge il conto "{account}"'))
def account_not_read(periodic: PeriodicReconciliation, account: str) -> None:
    assert periodic.readings_of(account) == periodic.readings_before


@then(
    parsers.re(
        r'^dopo altri (?P<minutes>\d+) minuti lo storico di "(?P<flow>[^"]+)" ha la posizione "(?P<asset>[^"]+)" '
        r'chiusa con il motivo "(?P<reason>[^"]+)"$'
    )
)
def closed_later(periodic: PeriodicReconciliation, minutes: str, flow: str, asset: str, reason: str) -> None:
    periodic.minutes_pass(int(minutes) - 1)
    assert periodic.closed(flow, asset) == []
    periodic.minutes_pass(1)
    [closed] = periodic.closed(flow, asset)
    assert closed.reason.value == reason


@then("la riconciliazione del conto resta al ciclo")
def reconciliation_left_to_the_cycle(periodic: PeriodicReconciliation) -> None:
    assert periodic.last_reading("principale") == periodic.reading_of_the_cycle


@then(quoted('"{flow}" resta attivo'))
def flow_still_active(periodic: PeriodicReconciliation, flow: str, caplog: pytest.LogCaptureFixture) -> None:
    assert periodic.flow_cycles.flow(flow).status is FlowStatus.ACTIVE
    # The check did try: the exchange did not answer, and the warning says so.
    assert WARNING in caplog.messages


@then(quoted('al controllo successivo il conto "{account}" si legge di nuovo'))
def read_again(periodic: PeriodicReconciliation, account: str) -> None:
    periodic.flow_cycles.platform.activity_reader.reachable = True
    periodic.minutes_pass(1)
    assert periodic.readings_of(account) == periodic.readings_before + 1
    reading = periodic.last_reading(account)
    assert reading is not None
    assert reading.read_at == periodic.flow_cycles.clock.now()


@then(parsers.re(r"^l'intervallo di riconciliazione del conto è (?P<minutes>\d+) minuti$"))
@then(parsers.re(r'^l\'intervallo di riconciliazione del conto "[^"]+" è (?P<minutes>\d+) minuti$'))
def interval_read(periodic: PeriodicReconciliation, minutes: str) -> None:
    assert periodic.summary is not None
    assert periodic.summary.reconciliation_interval_minutes == int(minutes)


@then(quoted('la richiesta è respinta con il motivo "{reason}"'))
def interval_refused(periodic: PeriodicReconciliation, reason: str) -> None:
    assert periodic.error is not None
    assert str(periodic.error) == reason
    assert periodic.error.status_code == 422
    periodic.read_account(USER, "principale")
    assert periodic.summary is not None
    assert periodic.summary.reconciliation_interval_minutes == ReconciliationInterval.default().minutes
