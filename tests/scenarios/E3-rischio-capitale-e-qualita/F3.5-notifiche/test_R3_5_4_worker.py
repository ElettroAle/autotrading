"""The scenarios of R3.5.4 that the worker realizes; the steps shared by every file of the requirement are in
tests/support, the steps of the notices of a cycle are here.

The notices of a cycle run on the cycles of the worker, their state read from the stores the cycles write: the account
of the exchange follows every order, so the ledger and the equity of the cycle see what the orders did (ADR
notifiche-del-ciclo-dopo-lo-stato-registrato).
"""

import json
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.notifications.link_chat import LinkChatCommand
from autotrading.domain.flows.account_activity import AccountPosition
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.ledger import Execution as LedgerExecution
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.italian_text import money_text
from autotrading.domain.notifications.flow_status import SEPARATOR
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.trading_access import TradingAccess
from tests.fakes.flow_status import InMemoryFlowStatusAdapter
from tests.support.activity import an_activity
from tests.support.flow_cycles import BALANCE, FlowCycles
from tests.support.notifications import chat_named
from tests.support.steps import quoted
from tests.support.steps_r3_5_4 import *  # noqa: F403 - the steps of R3.5.4, shared by its files
from tests.support.steps_r3_5_4 import Notices

scenarios(
    "E3-rischio-capitale-e-qualita/F3.5-notifiche/R3.5.4-notifiche-leggibili-con-icone-e-stato-del-flusso/worker/R3.5.4-notifiche-leggibili-con-icone-e-stato-del-flusso.feature"
)

CURRENCY = "USDC"
ASSETS = ("AVAX", "DOGE")
CAPITAL = Decimal(1000)
# Every execution at one price with one fee: the value of the flow after an opening is its capital less the fee.
PRICE = Decimal(20)
FEE = Decimal("0.07")
REJECTION = "Order rejected"
CYCLE = timedelta(minutes=15)


def _shown(held: HeldPosition) -> AccountPosition:
    side = TradeSide.LONG if held.direction is Direction.LONG else TradeSide.SHORT
    margin = held.size * held.entry_price / held.leverage
    return AccountPosition(held.coin, side, held.size, margin, Decimal(0), held.leverage, held.entry_price, PRICE)


def _signed(held: HeldPosition | None) -> Decimal:
    if held is None:
        return Decimal(0)
    return held.size if held.direction is Direction.LONG else -held.size


class CycleNotices:
    """The flow of the scenario on the cycles of the worker, and the chat of its user."""

    def __init__(self, notices: Notices) -> None:
        self.notices = notices
        self.cycles = FlowCycles()
        self.balance = BALANCE
        exchange = self.cycles.platform.order_exchange
        exchange.fill_at = (PRICE, FEE)
        for asset in ASSETS:
            exchange.markets[asset] = Market(asset, 10, 2, PRICE, Decimal(10))
            self.cycles.limits.set(asset, market_price=PRICE)
        exchange.observers.append(self.followed)

    @property
    def user(self) -> str:
        return self.notices.user

    def add_flow(self, flow: str, status: FlowStatus = FlowStatus.ACTIVE) -> None:
        platform = self.cycles.platform
        self.link_chat()
        added = self.cycles.add_flow(self.user, flow, assets=ASSETS)
        flows = platform.flows.flows
        flows[flows.index(added)] = replace(
            added, status=status, configuration=replace(added.configuration, allocated_capital=CAPITAL)
        )
        self.cycles.flow_status = InMemoryFlowStatusAdapter(
            platform.flows, self.cycles.equity_snapshots, platform.ledger, added.tenant_id, CURRENCY
        )
        platform.activity_reader.activities[self.address_of(flow)] = an_activity(
            balance=self.balance, available_margin=self.balance
        )

    def link_chat(self) -> None:
        platform = self.cycles.platform
        if platform.tenant_of(self.user) in platform.chats:
            return
        code = platform.use_cases_of(self.user).request_link_code.execute().code
        platform.link_chat().execute(LinkChatCommand(chat_named(self.user), code))
        platform.messenger.sent.clear()

    def address_of(self, flow: str) -> str:
        return self.cycles.credentials_of(flow).value("account_address")

    def answer(self, *decisions: dict[str, object]) -> None:
        self.cycles.model.text = json.dumps({"decisioni": list(decisions)})

    def open_in_cycle(self, flow: str, asset: str) -> None:
        self.answer(
            {
                "asset": asset,
                "azione": "apri",
                "direzione": "long",
                "quota": 0.05,
                "leva": 3,
                "obiettivo": None,
                "stop": None,
                "invalidazione": None,
                "confidenza": 70,
                "ragionamento": "r",
            }
        )
        self.cycles.run(flow)

    def close_in_cycle(self, flow: str, asset: str) -> None:
        self.answer({"asset": asset, "azione": "chiudi", "confidenza": 70, "ragionamento": "r"})
        self.cycles.run(flow)

    def next_cycle(self) -> None:
        """What the previous cycles notified is read already: the scenario reads the next cycle only."""
        self.cycles.platform.messenger.sent.clear()
        self.cycles.clock.current += CYCLE

    def followed(self, access: TradingAccess, order: MarketOrder, execution: Execution) -> None:
        """What the exchange shows of the address after the order: its execution, its positions and its balance."""
        platform = self.cycles.platform
        address = access.value("account_address")
        flow = next(flow for flow in platform.flows.flows if self.address_of(flow.name.value) == address)
        platform.platform_orders.add(order.id.value, flow.assigned_account_id, flow.id)
        signed = execution.filled_size if order.is_buy else -execution.filled_size
        after = _signed(platform.order_exchange.positions.get((address, order.coin)))
        fill = LedgerExecution(
            fill_id=str(order.id.value),
            exchange_order_id=str(order.id.value),
            order_id=order.id.value,
            asset=order.coin,
            size=signed,
            price=execution.average_price,
            fee=execution.fee,
            realized_pnl=execution.realized_pnl,
            start_position=after - signed,
            liquidation=False,
            executed_at=self.cycles.clock.now(),
        )
        platform.activity_reader.executions.setdefault(address, []).append(fill)
        self.balance += execution.realized_pnl - execution.fee
        positions = tuple(
            _shown(held) for (holder, _), held in platform.order_exchange.positions.items() if holder == address
        )
        platform.activity_reader.activities[address] = an_activity(
            balance=self.balance, available_margin=self.balance, positions=positions, read_at=self.cycles.clock.now()
        )

    def status_of(self, event: str) -> list[str]:
        """The parts of the state of the flow at the bottom of the last notification of the event."""
        received = self.cycles.platform.messenger.received_by(chat_named(self.user))
        told = [message.splitlines() for message in received if f": {event}" in message.splitlines()[0]]
        assert told, received
        last_line = told[-1][-1]
        assert last_line.startswith("Flusso: "), told[-1]
        return last_line.removeprefix("Flusso: ").split(SEPARATOR)


@pytest.fixture
def cycle_notices(notices: Notices) -> CycleNotices:
    return CycleNotices(notices)


# Given


@given(quoted('un flusso "{flow}" avviato che non ha ancora concluso un ciclo'))
def flow_never_cycled(cycle_notices: CycleNotices, flow: str) -> None:
    cycle_notices.add_flow(flow)


@given(quoted('che "{flow}" ha 1 posizione aperta'))
def flow_with_one_position(cycle_notices: CycleNotices, flow: str) -> None:
    cycle_notices.add_flow(flow)
    cycle_notices.open_in_cycle(flow, "AVAX")
    cycle_notices.next_cycle()


@given(quoted('un flusso "{flow}" fermo che non ha mai girato'))
def stopped_flow_never_run(cycle_notices: CycleNotices, flow: str) -> None:
    cycle_notices.add_flow(flow, FlowStatus.STOPPED)


# When


@when(quoted('al primo ciclo "{flow}" apre una posizione su "{asset}"'))
def opens_at_the_first_cycle(cycle_notices: CycleNotices, flow: str, asset: str) -> None:
    cycle_notices.open_in_cycle(flow, asset)


@when(quoted('in un ciclo "{flow}" apre una posizione su "{asset}"'))
def opens_in_a_cycle(cycle_notices: CycleNotices, flow: str, asset: str) -> None:
    cycle_notices.open_in_cycle(flow, asset)


@when(quoted('in un ciclo "{flow}" chiude la posizione'))
def closes_in_a_cycle(cycle_notices: CycleNotices, flow: str) -> None:
    cycle_notices.close_in_cycle(flow, "AVAX")


@when(quoted('in un ciclo un ordine di "{flow}" è rifiutato dall\'exchange'))
def order_refused_in_a_cycle(cycle_notices: CycleNotices, flow: str) -> None:
    cycle_notices.cycles.platform.order_exchange.rejection = REJECTION
    cycle_notices.open_in_cycle(flow, "DOGE")


@when(quoted('parte una notifica di "{flow}"'))
def notice_of(cycle_notices: CycleNotices, flow: str) -> None:
    operating = cycle_notices.cycles.flow(flow)
    ports = cycle_notices.cycles.ports_of(operating.tenant_id)
    ports.cycle_failure.execute(operating.id.value, "timeout")


# Then


@then(quoted('la notifica "{event}" termina con lo stato "{positions}"'))
def notice_ends_with(cycle_notices: CycleNotices, event: str, positions: str) -> None:
    assert positions in cycle_notices.status_of(event)


@then("la riga di stato riporta il valore del flusso dopo l'apertura")
def value_after_the_opening(cycle_notices: CycleNotices) -> None:
    value, pnl, *_ = cycle_notices.status_of("posizione aperta")
    assert (value, pnl) == (f"{money_text(CAPITAL - FEE)} {CURRENCY}", f"PnL {money_text(-FEE)} {CURRENCY}")


@then(quoted('la riga di stato dice "{status}"'))
def status_line_says(cycle_notices: CycleNotices, status: str) -> None:
    assert status in cycle_notices.status_of("ciclo fallito")
