"""R3.5.1: the events of risk and capital told to the user, on the cycles the worker runs and the use cases of the API
with the fake adapters (ADR eventi-notificabili-di-rischio-e-capitale).
"""

import json
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.flows.cash_out_profits import CashOutProfitsCommand
from autotrading.application.flows.close_in_emergency import CloseInEmergencyCommand
from autotrading.application.notifications.choose_notification_channel import ChooseNotificationChannelCommand
from autotrading.application.notifications.link_chat import LinkChatCommand
from autotrading.domain.flows.account_reconciliation import AccountReading
from autotrading.domain.flows.cycle_record import CycleOutcome
from autotrading.domain.flows.emergency_closing import EmergencyScope
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.ledger import FlowTotals
from autotrading.domain.flows.minimum_confidence import MinimumConfidence
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.notifications.notification_channel import NotificationChannel
from autotrading.domain.notifications.notification_event import NotificationEvent
from autotrading.domain.orders.protection_kind import ProtectionKind
from tests.fakes.equity_snapshots import InMemoryEquitySnapshotRepositoryAdapter
from tests.support.activity import READ_AT, a_fill, a_position, an_activity
from tests.support.flow_cycles import DAY, FlowCycles, at
from tests.support.lifecycle_steps import hold_position
from tests.support.notifications import chat_named, told_in
from tests.support.steps import quoted

scenarios("E3-rischio-capitale-e-qualita/F3.5-notifiche/R3.5.1-eventi-notificabili-completi.feature")

CAPITAL = Decimal(1000)
LEVERAGE = 2
ENTRY_PRICE = Decimal(60000)
# A tenth of the money of the flow: within its exposure of the margin, so the opening is not reduced.
QUOTA = 0.1
FEE = Decimal("0.02")
POSITION_SIZE = Decimal("0.0003")
MID_PRICE = Decimal(100000)
PROTECTED_PLAN = {"obiettivo": 66000, "stop": 57000}
NO_DECISIONS = '{"decisioni": []}'
KIND_OF = {"stop loss": ProtectionKind.STOP_LOSS, "take profit": ProtectionKind.TAKE_PROFIT}
PNL_OF_CLOSING = {"stop loss": "-5,10", "take profit": "4,90", "liquidazione": "-48,00"}
REQUESTED_MARGIN, REDUCED_MARGIN = Decimal(150), Decimal(100)
NUMBER = r"-?[\d,]+"


def amount(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


class Events:
    """The flow of anna on her account, the positions it holds and the chats that read what happens to it."""

    def __init__(self, flow_cycles: FlowCycles) -> None:
        self.flow_cycles = flow_cycles
        self.protected: set[tuple[str, str]] = set()

    def link(self, user: str, chat: str) -> None:
        platform = self.flow_cycles.platform
        code = platform.use_cases_of(user).request_link_code.execute().code
        platform.link_chat().execute(LinkChatCommand(chat_named(chat), code))
        # The confirmation of the link is R1.8.1: the scenarios read only what the flows notify.
        platform.messenger.sent.clear()

    def address(self, flow: str) -> str:
        return self.flow_cycles.credentials_of(flow).value("account_address")

    def receive_on_telegram(self, user: str, *events: NotificationEvent) -> None:
        """The decisions of the risk check are silent until the user chooses their channel (R3.5.3): the user of
        these scenarios receives every event."""
        choose = self.flow_cycles.platform.use_cases_of(user).choose_notification_channel
        for event in events:
            choose.execute(ChooseNotificationChannelCommand(event, frozenset({NotificationChannel.TELEGRAM})))

    def answer(self, *decisions: dict[str, object]) -> None:
        self.flow_cycles.model.text = json.dumps({"decisioni": list(decisions)})

    def opening(self, asset: str, quota: Decimal | float = QUOTA, **fields: object) -> dict[str, object]:
        decision: dict[str, object] = {
            "asset": asset,
            "azione": "apri",
            "direzione": "long",
            "quota": float(quota),
            "leva": LEVERAGE,
            "obiettivo": None,
            "stop": None,
            "invalidazione": None,
            "confidenza": 70,
            "ragionamento": "rottura della resistenza",
        }
        return {**decision, **fields}

    def protect(self, flow: str, asset: str) -> None:
        """A long position of the flow with its stop loss and take profit on the exchange, read open by a cycle."""
        if (flow, asset) in self.protected:
            return
        flow_cycles = self.flow_cycles
        flow_cycles.limits.set(asset, market_price=ENTRY_PRICE)
        exchange = flow_cycles.platform.order_exchange
        exchange.markets[asset] = replace(exchange.markets[asset], mid_price=ENTRY_PRICE)
        exchange.fill_at = (ENTRY_PRICE, FEE)
        self.answer(self.opening(asset, **PROTECTED_PLAN))
        flow_cycles.run(flow, "10:00")
        flow_cycles.model.text = NO_DECISIONS
        held = a_position(asset, margin=Decimal(10), size=POSITION_SIZE, leverage=LEVERAGE)
        flow_cycles.platform.activity_reader.activities[self.address(flow)] = an_activity(positions=(held,))
        flow_cycles.platform.ledger.expect(flow_cycles.flow(flow).id, asset, held.size)
        # A cycle reads the account with the position open: the reconciliation of the next one compares with it.
        flow_cycles.run(flow, "10:15")
        self.protected.add((flow, asset))
        flow_cycles.platform.messenger.sent.clear()

    def closed_on_the_exchange(self, flow: str, asset: str, pnl: Decimal, *, protection: ProtectionKind | None) -> None:
        """The position leaves the exchange, by its protection or by a liquidation, and the next cycle reads it."""
        flow_cycles = self.flow_cycles
        address = self.address(flow)
        order_id = None
        if protection is not None:
            order_id = flow_cycles.platform.protection_exchange.execute(
                address, asset, protection
            ).client_order_id.value
        del flow_cycles.platform.order_exchange.positions[address, asset]
        flow_cycles.platform.activity_reader.activities[address] = an_activity(balance=CAPITAL + pnl)
        fill = a_fill(
            asset,
            order_id,
            realized_pnl=pnl,
            executed_at=at("10:20"),
            fill_id="closing",
            size=-POSITION_SIZE,
            start_position=POSITION_SIZE,
            liquidation=protection is None,
        )
        flow_cycles.platform.activity_reader.executions.setdefault(address, []).append(fill)
        flow_cycles.run(flow, "10:30")

    def close_for(self, flow: str, asset: str, reason: str, pnl: Decimal) -> None:
        self.protect(flow, asset)
        self.closed_on_the_exchange(flow, asset, pnl, protection=KIND_OF.get(reason))

    def reduce(self, flow: str, asset: str, requested: Decimal, reduced: Decimal) -> None:
        """The agent asks for the requested margin; the exposure of the margin of the flow allows the reduced one."""
        self.flow_cycles.reconfigure(
            flow,
            lambda configuration: replace(configuration, risk_limits=RiskLimits(5, reduced / CAPITAL * 100)),
        )
        self.flow_cycles.platform.order_exchange.fill_at = (MID_PRICE, FEE)
        self.answer(self.opening(asset, requested / CAPITAL))
        self.flow_cycles.run(flow)

    def received_by(self, chat: str) -> list[str]:
        return self.flow_cycles.platform.messenger.received_by(chat_named(chat))


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def events(flow_cycles: FlowCycles) -> Events:
    return Events(flow_cycles)


@pytest.fixture
def notified() -> dict[str, str]:
    """The title the scenario expects of the notification, read back for the chats that must not receive it."""
    return {}


# Given


@given(quoted('che "{user}" ha la chat "{chat}" collegata, il conto "{account}" e il flusso "{flow}"'))
def chat_account_and_flow(events: Events, user: str, chat: str, account: str, flow: str) -> None:
    events.link(user, chat)
    events.receive_on_telegram(user, NotificationEvent.OPENING_REDUCED, NotificationEvent.OPENING_BLOCKED)
    events.flow_cycles.add_flow(user, flow, assets=("BTC",), account=account)
    events.flow_cycles.reconfigure(flow, lambda configuration: replace(configuration, allocated_capital=CAPITAL))


@given(quoted('che "{user}" ha la chat "{chat}" collegata'))
def chat_only(events: Events, user: str, chat: str) -> None:
    events.link(user, chat)


@given(quoted('che "{flow}" ha una posizione aperta su "{asset}"'))
def open_position(events: Events, flow: str, asset: str) -> None:
    events.protect(flow, asset)


@given(quoted('che l\'invio delle notifiche alla chat "{chat}" fallisce'))
def sending_fails(events: Events, chat: str) -> None:
    assert chat == "chat-anna"
    events.flow_cycles.platform.messenger.reachable = False


# When: the events of the flow and of the account


@when(
    parsers.re(
        r'^l\'exchange esegue (?:lo|il) (?P<reason>stop loss|take profit) di "(?P<flow>[^"]+)" su "(?P<asset>[^"]+)" '
        rf"con PnL (?P<pnl>{NUMBER}) USDC$"
    )
)
def protection_executed(events: Events, reason: str, flow: str, asset: str, pnl: str) -> None:
    events.close_for(flow, asset, reason, amount(pnl))


@when(
    parsers.re(
        rf'^l\'exchange liquida la posizione di "(?P<flow>[^"]+)" su "(?P<asset>[^"]+)" con PnL (?P<pnl>{NUMBER}) USDC$'
    )
)
def position_liquidated(events: Events, flow: str, asset: str, pnl: str) -> None:
    events.close_for(flow, asset, "liquidazione", amount(pnl))


@when(quoted('il rischio riduce l\'apertura di "{flow}" su "{asset}" da {requested} a {reduced} USDC di margine'))
def risk_reduces(events: Events, flow: str, asset: str, requested: str, reduced: str) -> None:
    events.reduce(flow, asset, amount(requested), amount(reduced))


@when(
    quoted(
        'il rischio blocca l\'apertura di "{flow}" su "{asset}" per confidenza {confidence} sotto la minima {minimum}'
    )
)
def risk_blocks(events: Events, flow: str, asset: str, confidence: str, minimum: str) -> None:
    events.flow_cycles.reconfigure(
        flow, lambda configuration: replace(configuration, minimum_confidence=MinimumConfidence(int(minimum)))
    )
    events.answer(events.opening(asset, confidenza=int(confidence)))
    events.flow_cycles.run(flow)


@when(quoted('le aperture di "{flow}" si sospendono per perdita giornaliera {loss}% oltre il {maximum}%'))
def openings_suspended(events: Events, flow: str, loss: str, maximum: str) -> None:
    flow_cycles = events.flow_cycles
    recorded = flow_cycles.flow(flow)
    # The flow started days before, so the value at midnight is the reference of the day.
    flow_cycles.platform.flows.first_starts[recorded.id] = DAY - timedelta(days=3)
    flow_cycles.reconfigure(flow, lambda configuration: replace(configuration, max_daily_loss_percent=amount(maximum)))
    snapshot = EquitySnapshot(recorded.id.value, DAY, CAPITAL, Decimal(0), Decimal(0), Decimal(0), Decimal(0))
    InMemoryEquitySnapshotRepositoryAdapter(flow_cycles.equity_snapshots, recorded.tenant_id).record(snapshot)
    lost = CAPITAL * amount(loss) / 100
    flow_cycles.platform.ledger.totals[recorded.id] = FlowTotals(recorded.id, realized_pnl=-lost)
    flow_cycles.run(flow)


@when(quoted('sul conto "{account}" si apre un allarme di riconciliazione con saldo {read} invece di {expected} USDC'))
def reconciliation_alarm(events: Events, account: str, read: str, expected: str) -> None:
    flow_cycles = events.flow_cycles
    [flow] = [name for name in flow_cycles.users if flow_cycles.users[name] == "anna"]
    account_id = flow_cycles.platform.account_named("anna", account).id.value
    reading = AccountReading(account_id, READ_AT - timedelta(minutes=5), {}, amount(expected))
    flow_cycles.readings.save_reading(reading)
    balance = amount(read)
    activity = an_activity(balance=balance, available_margin=balance)
    flow_cycles.platform.activity_reader.activities[events.address(flow)] = activity
    flow_cycles.run(flow)


@when(quoted('"{user}" incassa {freed} USDC dal flusso "{flow}"'))
def cash_out(events: Events, user: str, freed: str, flow: str) -> None:
    platform = events.flow_cycles.platform
    recorded = events.flow_cycles.flow(flow)
    platform.flows.save_version(recorded)
    platform.ledger.totals[recorded.id] = FlowTotals(recorded.id, realized_pnl=amount(freed))
    command = CashOutProfitsCommand(recorded.id, platform.user_id_of(user))
    outcome = platform.use_cases_of(user).cash_out_profits.execute(command)
    assert outcome.freed == amount(freed)


@when(quoted('"{user}" lancia la chiusura di emergenza del flusso "{flow}" con {closed} posizione chiusa'))
def emergency_closing(events: Events, user: str, flow: str, closed: str) -> None:
    platform = events.flow_cycles.platform
    recorded = events.flow_cycles.flow(flow)
    hold_position(platform, user, "test-1", "BTC")
    command = CloseInEmergencyCommand(EmergencyScope(flow_id=recorded.id), platform.user_id_of(user))
    closing = platform.use_cases_of(user).close_in_emergency.execute(command)
    assert sum(len(outcome.closed) for outcome in closing.outcomes) == int(closed)


@when(
    parsers.re(
        r'^la posizione di "(?P<flow>[^"]+)" su "(?P<asset>[^"]+)" si chiude per '
        r"(?P<reason>stop loss|take profit|liquidazione)$"
    )
)
def position_closes_for(events: Events, flow: str, asset: str, reason: str) -> None:
    events.close_for(flow, asset, reason, amount(PNL_OF_CLOSING[reason]))


@when(quoted('il rischio riduce un\'apertura di "{flow}" su "{asset}"'))
def risk_reduces_an_opening(events: Events, flow: str, asset: str) -> None:
    events.reduce(flow, asset, REQUESTED_MARGIN, REDUCED_MARGIN)


# Then


@then(quoted('la chat "{chat}" riceve una notifica "{title}" con le righe "{values}"'))
def chat_receives(events: Events, notified: dict[str, str], chat: str, title: str, values: str) -> None:
    notified["title"] = title
    received = events.received_by(chat)
    assert told_in(received, title, values), received


@then(quoted('la chat "{chat}" non riceve la notifica'))
def chat_does_not_receive(events: Events, notified: dict[str, str], chat: str) -> None:
    received = events.received_by(chat)
    assert not any(notified["title"] in message for message in received)
    assert received == []


@then(quoted('la chat "{chat}" riceve una sola notifica per quella chiusura'))
def chat_receives_one_closing(events: Events, chat: str) -> None:
    # The account may tell its own events (an execution without an order of the platform): only the flow tells the
    # closing.
    of_the_flow = [message for message in events.received_by(chat) if " alfa: " in message.splitlines()[0]]
    assert len(of_the_flow) == 1, of_the_flow
    assert "BTC" in of_the_flow[0]


@then(quoted('il ciclo di "{flow}" si conclude ed esegue l\'apertura ridotta'))
def cycle_completes_with_reduced_opening(events: Events, flow: str) -> None:
    flow_cycles = events.flow_cycles
    assert flow_cycles.last_record(flow).outcome is CycleOutcome.COMPLETED
    [order] = flow_cycles.platform.order_exchange.sent
    assert order.size * MID_PRICE == REDUCED_MARGIN * LEVERAGE


@then(quoted('nessuna notifica della chat "{chat}" contiene le credenziali del conto del flusso "{flow}"'))
def notifications_without_credentials(events: Events, chat: str, flow: str) -> None:
    received = events.received_by(chat)
    secrets = [value for value in events.flow_cycles.credentials_of(flow).values.values() if value]
    assert received
    assert [message for message in received if any(secret in message for secret in secrets)] == []
