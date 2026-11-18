"""The alarm on the balance of an account the cycles cannot explain (R3.3.1), on the cycles as the worker runs them."""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.accounts.set_deviation_threshold import SetDeviationThresholdCommand
from autotrading.application.flows.confirm_reconciliation import ConfirmReconciliationCommand
from autotrading.application.flows.ports import ReconciliationAlarmPorts
from autotrading.application.flows.reconcile_account import ReconcileAccountCommand, ReconcileAccountUseCase
from autotrading.application.flows.record_account_executions import RecordAccountExecutionsUseCase
from autotrading.application.notifications.link_chat import LinkChatCommand
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.account_reconciliation import AccountReading
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.ledger import FlowTotals
from autotrading.domain.flows.unattributable import UnattributableKind
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.account_thresholds import FakeAccountThresholdsAdapter
from tests.fakes.alert_repository import InMemoryAlertRepositoryAdapter
from tests.fakes.closed_positions import InMemoryClosedPositionsAdapter
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.platform_orders import InMemoryPlatformOrdersAdapter
from tests.fakes.protection_closings import InMemoryProtectionClosingsAdapter
from tests.fakes.reconciliation_alarm_notices import FakeReconciliationAlarmNoticeAdapter
from tests.fakes.reconciliation_repository import InMemoryReconciliationRepositoryAdapter
from tests.support.activity import READ_AT, a_fill, a_movement, a_payment, a_position, an_activity
from tests.support.decision_steps import answer, opening
from tests.support.flow_cycles import FlowCycles, at
from tests.support.flows import a_configuration, a_flow
from tests.support.notifications import chat_named, told_in
from tests.support.platform import HYPERLIQUID
from tests.support.steps import quoted

scenarios("E3-rischio-capitale-e-qualita/F3.3-riconciliazione/R3.3.1-allarme-sul-saldo-non-spiegato.feature")

CYCLE = timedelta(minutes=15)
ALARM_TEXT = "allarme di riconciliazione"
ACCOUNT_OF_FLOWS = "test-1"
MOVEMENTS = {"deposito": Decimal(1), "prelievo": Decimal(-1)}
SOL = Market("SOL", max_leverage=20, size_decimals=2, mid_price=Decimal(150), min_order_value=Decimal(10))
LATE_ASSET = "BTC"


class LateRows:
    """The reconciliation of one account on the fake adapters, with rows the exchange publishes after a reading of
    the balance that already held them (Bug 506)."""

    def __init__(self) -> None:
        self.tenant_id = TenantId(uuid4())
        self.account_id = uuid4()
        self.store = FlowStore()
        self.exchange = FakeAccountActivityAdapter()
        self.orders = InMemoryPlatformOrdersAdapter()
        self.ledger = InMemoryFlowLedgerAdapter()
        self.readings = InMemoryReconciliationRepositoryAdapter()
        self.reconciled_at: datetime | None = None
        flows = InMemoryFlowRepositoryAdapter(self.store, self.tenant_id)
        accounts = FakeAccountThresholdsAdapter({self.account_id: "principale"})
        record = RecordAccountExecutionsUseCase(flows, self.exchange, self.orders, self.ledger)
        alarms = ReconciliationAlarmPorts(accounts, accounts, FakeReconciliationAlarmNoticeAdapter())
        self.reconcile = ReconcileAccountUseCase(
            flows,
            self.exchange,
            self.readings,
            InMemoryClosedPositionsAdapter(),
            record,
            InMemoryProtectionClosingsAdapter(),
            alarms,
            InMemoryAlertRepositoryAdapter({}, self.tenant_id),
        )

    def flow(self, name: str) -> Flow:
        """The flow of the account, holding a position on its asset since before the previous reading."""
        known = next((flow for flow in self.store.flows if flow.name.value == name), None)
        if known is not None:
            return known
        configuration = a_configuration(assets=(LATE_ASSET,))
        flow = a_flow(
            self.tenant_id, name=name, account_id=self.account_id, status=FlowStatus.ACTIVE, configuration=configuration
        )
        self.store.flows.append(flow)
        self.ledger.totals[flow.id] = FlowTotals(flow.id, positions=frozendict({LATE_ASSET: Decimal(1)}))
        return flow

    def publish_at(self, clock: str) -> None:
        previous = self.readings.last_reading(self.account_id)
        assert previous is not None
        self.reconciled_at = at(clock)
        assert self.reconciled_at > previous.read_at
        # The ledger was read up to the previous reading: what comes late falls in the hour it reads again (ADR 0076).
        self.ledger.cursors[self.account_id] = previous.read_at


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def late_rows() -> LateRows:
    return LateRows()


@pytest.fixture
def refused() -> list[AutotradingError]:
    return []


@pytest.fixture
def declared() -> list[Decimal]:
    """The deposits and withdrawals the exchange declares with its next reading of the account."""
    return []


def amount(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


def account_id(flow_cycles: FlowCycles, account: str) -> UUID:
    return flow_cycles.platform.account_named("anna", account).id.value


def address_of(flow_cycles: FlowCycles, account: str) -> str:
    identifier = account_id(flow_cycles, account)
    flow = next(name for name in flow_cycles.users if flow_cycles.flow(name).assigned_account_id == identifier)
    return flow_cycles.credentials_of(flow, account).value("account_address")


def exchange_shows(flow_cycles: FlowCycles, account: str, balance: Decimal, declared: tuple[Decimal, ...] = ()) -> None:
    movements = tuple(a_movement(movement) for movement in declared)
    activity = an_activity(balance=balance, available_margin=balance, movements=movements)
    flow_cycles.platform.activity_reader.activities[address_of(flow_cycles, account)] = activity


def next_cycle(flow_cycles: FlowCycles, flow: str) -> None:
    flow_cycles.clock.current += CYCLE
    flow_cycles.run(flow)


def alarm_with_reading(flow_cycles: FlowCycles, balance: Decimal) -> None:
    exchange_shows(flow_cycles, ACCOUNT_OF_FLOWS, balance)
    flow_cycles.run("alfa")
    flow_cycles.platform.messenger.sent.clear()


def opened_coins(flow_cycles: FlowCycles) -> list[str]:
    return [order.coin for order in flow_cycles.platform.order_exchange.sent if not order.reduce_only]


def blocked_reasons(flow_cycles: FlowCycles, flow: str) -> dict[str, str]:
    document = flow_cycles.last_record(flow).document(CycleStep.RISK_CHECK)
    assert document is not None
    outcomes = document["esiti"]
    assert isinstance(outcomes, list)
    return {outcome["asset"]: outcome["reason"] for outcome in outcomes if outcome["tipo"] == "BlockedDecision"}


def openings_suspended(flow_cycles: FlowCycles, flow: str) -> bool:
    asset = flow_cycles.flow(flow).configuration.assets[0]
    sent_before = len(flow_cycles.platform.order_exchange.sent)
    answer(flow_cycles, opening(asset))
    next_cycle(flow_cycles, flow)
    reason = f"apertura {asset} non eseguita: {ALARM_TEXT} sul conto {ACCOUNT_OF_FLOWS}"
    suspended = blocked_reasons(flow_cycles, flow).get(asset) == reason
    assert suspended is (len(flow_cycles.platform.order_exchange.sent) == sent_before)
    return suspended


def alarm_messages(flow_cycles: FlowCycles) -> list[str]:
    return [text for text in flow_cycles.platform.messenger.received_by(chat_named("anna")) if ALARM_TEXT in text]


# Given


@given(
    quoted(
        'che "{user}" ha il conto "{account}" con i flussi attivi "{first}" e "{second}" '
        "e soglia di scostamento {percent}%"
    )
)
def account_with_flows_and_threshold(
    flow_cycles: FlowCycles, *, user: str, account: str, first: str, second: str, percent: str
) -> None:
    platform = flow_cycles.platform
    code = platform.use_cases_of(user).request_link_code.execute().code
    platform.link_chat().execute(LinkChatCommand(chat_named(user), code))
    platform.messenger.sent.clear()
    flow_cycles.add_flow(user, first, assets=("BTC",), account=account)
    flow_cycles.add_flow(user, second, assets=("ETH",), account=account)
    command = SetDeviationThresholdCommand(AccountId(account_id(flow_cycles, account)), amount(percent))
    platform.use_cases_of(user).set_deviation_threshold.execute(command)


@given(quoted('che "{user}" ha il conto "{account}" con il flusso attivo "{flow}"'))
def account_with_flow(flow_cycles: FlowCycles, user: str, account: str, flow: str) -> None:
    flow_cycles.add_flow(user, flow, assets=("SOL",), account=account)
    flow_cycles.platform.order_exchange.markets["SOL"] = SOL


@given(quoted('che il saldo atteso del conto "{account}" è {balance} USDC'))
def expected_balance(flow_cycles: FlowCycles, account: str, balance: str) -> None:
    reading = AccountReading(account_id(flow_cycles, account), READ_AT - timedelta(minutes=5), {}, amount(balance))
    flow_cycles.readings.save_reading(reading)


@given(quoted('che l\'exchange dichiara sul conto "{account}" un {movement} di {value} USDC'))
def declared_movement(declared: list[Decimal], account: str, movement: str, value: str) -> None:
    assert account == ACCOUNT_OF_FLOWS
    declared.append(MOVEMENTS[movement] * amount(value))


@given(quoted('che sul conto "{account}" c\'è un allarme di riconciliazione con saldo letto {balance} USDC'))
def alarm_read(flow_cycles: FlowCycles, account: str, balance: str) -> None:
    assert account == ACCOUNT_OF_FLOWS
    alarm_with_reading(flow_cycles, amount(balance))


@given(quoted('che sul conto "{account}" c\'è un allarme di riconciliazione'))
def alarm(flow_cycles: FlowCycles, account: str) -> None:
    assert account == ACCOUNT_OF_FLOWS
    alarm_with_reading(flow_cycles, Decimal(980))


@given(quoted('che "{flow}" ha una posizione aperta su "{asset}"'))
def open_position(flow_cycles: FlowCycles, flow: str, asset: str) -> None:
    access = TradingAccess(HYPERLIQUID, flow_cycles.credentials_of(flow).values)
    position = HeldPosition(asset, Direction.LONG, Decimal("0.0003"), 3, Decimal(100))
    flow_cycles.platform.order_exchange.hold(access, position)


@given(quoted('che "{user}" imposta la soglia di scostamento del conto "{account}" a {percent}%'))
def threshold_set(
    flow_cycles: FlowCycles, refused: list[AutotradingError], user: str, account: str, percent: str
) -> None:
    set_threshold(flow_cycles, refused, user, account, percent)
    assert refused == []


# When


@when(quoted('un ciclo di "{flow}" legge dall\'exchange il saldo {balance} USDC'))
def cycle_reads(flow_cycles: FlowCycles, declared: list[Decimal], flow: str, balance: str) -> None:
    exchange_shows(flow_cycles, ACCOUNT_OF_FLOWS, amount(balance), tuple(declared))
    flow_cycles.run(flow)


@when(quoted('il ciclo successivo di "{flow}" legge ancora il saldo {balance} USDC'))
def next_cycle_reads(flow_cycles: FlowCycles, flow: str, balance: str) -> None:
    exchange_shows(flow_cycles, ACCOUNT_OF_FLOWS, amount(balance))
    next_cycle(flow_cycles, flow)


@when(quoted('l\'agente di "{flow}" decide di aprire long su "{asset}"'))
def agent_opens(flow_cycles: FlowCycles, flow: str, asset: str) -> None:
    answer(flow_cycles, opening(asset))
    next_cycle(flow_cycles, flow)


@when(quoted('l\'agente di "{flow}" decide di chiudere la posizione su "{asset}"'))
def agent_closes(flow_cycles: FlowCycles, flow: str, asset: str) -> None:
    answer(flow_cycles, {"asset": asset, "azione": "chiudi", "confidenza": 70, "ragionamento": "r"})
    next_cycle(flow_cycles, flow)


@when(quoted('"{user}" conferma di aver verificato il conto "{account}"'))
def user_confirms(flow_cycles: FlowCycles, refused: list[AutotradingError], user: str, account: str) -> None:
    command = ConfirmReconciliationCommand(account_id(flow_cycles, account))
    try:
        flow_cycles.platform.use_cases_of(user).confirm_reconciliation.execute(command)
    except AutotradingError as error:
        refused.append(error)


@when(quoted('"{user}" imposta la soglia di scostamento del conto "{account}" a {percent}%'))
def set_threshold(
    flow_cycles: FlowCycles, refused: list[AutotradingError], user: str, account: str, percent: str
) -> None:
    command = SetDeviationThresholdCommand(AccountId(account_id(flow_cycles, account)), amount(percent))
    try:
        flow_cycles.platform.use_cases_of(user).set_deviation_threshold.execute(command)
    except AutotradingError as error:
        refused.append(error)


# Then


@then(
    quoted(
        'sul conto "{account}" c\'è un allarme di riconciliazione con saldo atteso {expected} USDC, '
        "saldo letto {read} USDC e scostamento {percent}%"
    )
)
def alarm_recorded(flow_cycles: FlowCycles, account: str, expected: str, read: str, percent: str) -> None:
    alarm = flow_cycles.readings.open_alarm(account_id(flow_cycles, account))
    assert alarm is not None
    assert (alarm.expected_balance, alarm.read_balance, alarm.deviation_percent) == (
        amount(expected),
        amount(read),
        amount(percent),
    )


@then(quoted('le aperture di "{first}" e "{second}" sono sospese'))
def openings_are_suspended(flow_cycles: FlowCycles, first: str, second: str) -> None:
    assert openings_suspended(flow_cycles, first)
    assert openings_suspended(flow_cycles, second)


@then(quoted('le aperture di "{first}" e "{second}" non sono sospese'))
def openings_are_not_suspended(flow_cycles: FlowCycles, first: str, second: str) -> None:
    assert not openings_suspended(flow_cycles, first)
    assert not openings_suspended(flow_cycles, second)


@then(quoted('"{user}" riceve la notifica "{title}" con le righe "{values}"'))
def user_notified(flow_cycles: FlowCycles, user: str, title: str, values: str) -> None:
    received = flow_cycles.platform.messenger.received_by(chat_named(user))
    assert told_in(received, title, values), received


@then(quoted('"{user}" non riceve alcuna notifica'))
def nothing_told(flow_cycles: FlowCycles, user: str) -> None:
    # The chat of the user is linked from the start: a change within the threshold reaches it with no message at all.
    assert flow_cycles.platform.tenant_of(user) in flow_cycles.platform.chats
    assert flow_cycles.platform.messenger.received_by(chat_named(user)) == []


@then(quoted('"{user}" non riceve un\'altra notifica di allarme'))
def no_other_alarm_notice(flow_cycles: FlowCycles, user: str) -> None:
    assert user == "anna"
    assert alarm_messages(flow_cycles) == []


@then(quoted('sul conto "{account}" non c\'è alcun allarme di riconciliazione'))
def no_alarm(flow_cycles: FlowCycles, account: str) -> None:
    assert flow_cycles.readings.alarms_of(account_id(flow_cycles, account)) == []


@then(quoted('sul conto "{account}" c\'è un solo allarme di riconciliazione'))
def one_alarm(flow_cycles: FlowCycles, account: str) -> None:
    assert len(flow_cycles.readings.alarms_of(account_id(flow_cycles, account))) == 1


def balance_changes(flow_cycles: FlowCycles, account: str) -> list[Decimal]:
    identifier = account_id(flow_cycles, account)
    return [
        item.amount
        for item in flow_cycles.readings.items
        if item.account_id == identifier and item.kind is UnattributableKind.BALANCE_CHANGE
    ]


@then(quoted('sul conto "{account}" è registrata una variazione del saldo non spiegata di {value} USDC'))
def balance_change_recorded(flow_cycles: FlowCycles, account: str, value: str) -> None:
    assert balance_changes(flow_cycles, account) == [amount(value)]


@then(quoted('sul conto "{account}" non è registrata alcuna variazione del saldo non spiegata'))
def no_balance_change(flow_cycles: FlowCycles, account: str) -> None:
    assert balance_changes(flow_cycles, account) == []


@then(quoted('"{flow}" non apre la posizione su "{asset}"'))
def not_opened(flow_cycles: FlowCycles, flow: str, asset: str) -> None:
    assert flow_cycles.flow(flow).configuration.assets == (asset,)
    assert asset not in opened_coins(flow_cycles)


@then(quoted('il ciclo di "{flow}" registra "apertura {asset} non eseguita: {reason}"'))
def cycle_records_blocked(flow_cycles: FlowCycles, flow: str, asset: str, reason: str) -> None:
    assert blocked_reasons(flow_cycles, flow) == {asset: f"apertura {asset} non eseguita: {reason}"}


@then(quoted('"{flow}" chiude la posizione su "{asset}"'))
def closed(flow_cycles: FlowCycles, flow: str, asset: str) -> None:
    sent = flow_cycles.platform.order_exchange.sent
    assert [(order.coin, order.reduce_only) for order in sent] == [(asset, True)]
    assert blocked_reasons(flow_cycles, flow) == {}


@then(quoted('"{flow}" apre la posizione su "{asset}"'))
def opened(flow_cycles: FlowCycles, flow: str, asset: str) -> None:
    assert opened_coins(flow_cycles) == [asset]
    assert blocked_reasons(flow_cycles, flow) == {}


@then(quoted('l\'allarme del conto "{account}" è chiuso'))
def alarm_closed(flow_cycles: FlowCycles, account: str) -> None:
    identifier = account_id(flow_cycles, account)
    [alarm] = flow_cycles.readings.alarms_of(identifier)
    assert alarm.confirmed_at == flow_cycles.platform.now
    assert flow_cycles.readings.open_alarm(identifier) is None


@then(quoted('il saldo atteso del conto "{account}" è {balance} USDC'))
def expected_balance_is(flow_cycles: FlowCycles, account: str, balance: str) -> None:
    reading = flow_cycles.readings.last_reading(account_id(flow_cycles, account))
    assert reading is not None
    assert reading.reference_balance == amount(balance)


@then(quoted('il comando viene rifiutato con "{reason}"'))
@then(quoted('la modifica viene rifiutata con "{reason}"'))
def command_refused(refused: list[AutotradingError], reason: str) -> None:
    assert [str(error) for error in refused] == [reason]


# ADR saldo-atteso-con-le-sole-righe-successive-alla-lettura-precedente: the scenarios of Bug 506, on the
# reconciliation of an account of their own.


@given(quoted('che il conto "{account}" ha una lettura precedente alle {clock} con saldo di riferimento {balance}'))
def previous_reading(late_rows: LateRows, account: str, clock: str, balance: str) -> None:
    assert account == "principale"
    late_rows.readings.save_reading(AccountReading(late_rows.account_id, at(clock), {}, amount(balance)))


@given(
    quoted(
        'che alle {clock} il registro scrive un pagamento di funding di {value} del flusso "{flow}" '
        "avvenuto alle {paid}"
    )
)
def late_funding(late_rows: LateRows, clock: str, value: str, flow: str, paid: str) -> None:
    late_rows.flow(flow)
    late_rows.publish_at(clock)
    payment = a_payment(LATE_ASSET, amount(value), paid_at=at(paid))
    late_rows.exchange.funding.setdefault(late_rows.account_id, []).append(payment)


@given(
    quoted(
        'che alle {clock} il registro scrive un\'esecuzione del flusso "{flow}" delle {executed} '
        "con PnL realizzato {pnl} e commissione {fee}"
    )
)
def late_execution(late_rows: LateRows, clock: str, flow: str, *, executed: str, pnl: str, fee: str) -> None:
    order_id = uuid4()
    late_rows.orders.add(order_id, late_rows.account_id, late_rows.flow(flow).id)
    late_rows.publish_at(clock)
    fill = a_fill(LATE_ASSET, order_id, realized_pnl=amount(pnl), fee=amount(fee), executed_at=at(executed))
    late_rows.exchange.executions.setdefault(late_rows.account_id, []).append(fill)


@given(quoted("che il saldo letto alle {clock} è {balance}"))
def balance_read(late_rows: LateRows, clock: str, balance: str) -> None:
    assert at(clock) == late_rows.reconciled_at
    late_rows.exchange.activities[late_rows.account_id] = an_activity(
        balance=amount(balance), positions=(a_position(LATE_ASSET),), read_at=at(clock)
    )


@when("il conto si riconcilia")
def account_reconciled(late_rows: LateRows) -> None:
    [flow] = late_rows.store.flows
    late_rows.reconcile.execute(ReconcileAccountCommand(flow.id))
    account = late_rows.account_id
    written = [entry.flow_id for entry in late_rows.ledger.entries.get(account, [])]
    written += [entry.flow_id for entry in late_rows.ledger.funding.get(account, [])]
    # The late row enters the ledger of its flow: only the comparison of the balance leaves it out.
    assert written == [flow.id]


@then(quoted("il saldo atteso è {balance}"))
def expected_balance_of_the_comparison(late_rows: LateRows, balance: str) -> None:
    reading = late_rows.readings.last_reading(late_rows.account_id)
    assert reading is not None
    assert reading.comparison is not None
    assert reading.comparison.expected == amount(balance)


@then("nessuna variazione del saldo non spiegata si registra")
def no_unexplained_change(late_rows: LateRows) -> None:
    assert UnattributableKind.BALANCE_CHANGE not in [item.kind for item in late_rows.readings.items]
