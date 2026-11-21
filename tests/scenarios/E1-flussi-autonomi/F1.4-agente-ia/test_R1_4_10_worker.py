"""The reversal of a position in one cycle, on the cycles the worker runs (R1.4.10).

ADR-inversione-in-due-passi-nel-ciclo: the close goes with the orders of the cycle; the opening on the opposite side is
checked after the account is reconciled, on the money of the flow after the close, and sent in a second execution.
The account of the exchange follows every order the scenario sends: positions, balance and executions, so the
reconciliations of the cycle read what the orders did.
"""

import json
from dataclasses import replace
from decimal import Decimal

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.domain.flows.account_activity import AccountPosition
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.ledger import Execution as LedgerExecution
from autotrading.domain.flows.openings_suspension import MAXIMUM_LOSS_BLOCK, OpeningsSuspension
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.trading_access import TradingAccess
from tests.fakes.openings_suspension import InMemoryOpeningsSuspensionAdapter
from tests.support.activity import an_activity
from tests.support.flow_cycles import BALANCE, FlowCycles
from tests.support.steps import quoted

scenarios(
    "E1-flussi-autonomi/F1.4-agente-ia/R1.4.10-inversione-in-un-ciclo/worker/R1.4.10-inversione-in-un-ciclo.feature"
)

# The executions at one price and without fees: the money of the flow moves only by the PnL of its closings.
PRICE = Decimal(100000)
OPENING_QUOTA, OPENING_LEVERAGE = 0.1, 2
SUSPENSION = "perdita giornaliera 6% oltre il 5%"
CLOSING_REFUSED = "Reduce only order would increase position"


def number(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


def decision(asset: str, action: str, direction: str | None, quota: object, leverage: object) -> dict[str, object]:
    return {
        "asset": asset,
        "azione": action,
        "direzione": direction,
        "quota": quota,
        "leva": leverage,
        "obiettivo": None,
        "stop": None,
        "invalidazione": None,
        "togli_obiettivo": False,
        "confidenza": 70,
        "ragionamento": "la direzione cambia",
    }


class Reversals:
    """The flow of the scenario, its account kept by its orders, and the cycles that run it."""

    def __init__(self, flow_cycles: FlowCycles) -> None:
        self.flow_cycles = flow_cycles
        self.flow = ""
        self.sent_before = 0
        self.balance = BALANCE
        platform = flow_cycles.platform
        platform.order_exchange.fill_at = (PRICE, Decimal(0))
        platform.order_exchange.observers.append(self.followed)

    @property
    def address(self) -> str:
        return self.flow_cycles.credentials_of(self.flow).value("account_address")

    @property
    def access(self) -> TradingAccess:
        return TradingAccess("hyperliquid", self.flow_cycles.credentials_of(self.flow).values)

    def add_flow(self, user: str, flow: str, assets: tuple[str, ...], funds: Decimal) -> None:
        self.flow = flow
        self.flow_cycles.add_flow(user, flow, assets=assets)
        self.flow_cycles.reconfigure(
            flow,
            lambda configuration: replace(
                configuration, allocated_capital=funds, risk_limits=RiskLimits(10, Decimal(100))
            ),
        )
        self.flow_cycles.platform.activity_reader.activities[self.address] = an_activity(
            balance=self.balance, available_margin=self.balance
        )

    def answer(self, *decisions: dict[str, object]) -> None:
        self.flow_cycles.model.text = json.dumps({"decisioni": list(decisions)})

    def run(self, clock: str) -> None:
        self.flow_cycles.run(self.flow, clock)

    def followed(self, access: TradingAccess, order: MarketOrder, execution: Execution) -> None:
        """What the exchange shows of the address after the order: its execution, its positions and its balance."""
        platform = self.flow_cycles.platform
        flow = self.flow_cycles.flow(self.flow)
        address = access.value("account_address")
        platform.platform_orders.add(order.id.value, flow.assigned_account_id, flow.id)
        signed = execution.filled_size if order.is_buy else -execution.filled_size
        fill = LedgerExecution(
            fill_id=str(order.id.value),
            exchange_order_id=str(order.id.value),
            order_id=order.id.value,
            asset=order.coin,
            size=signed,
            price=execution.average_price,
            fee=execution.fee,
            realized_pnl=execution.realized_pnl,
            start_position=Decimal(0),
            liquidation=False,
            executed_at=execution.executed_at,
        )
        platform.activity_reader.executions.setdefault(address, []).append(fill)
        self.balance += execution.realized_pnl - execution.fee
        positions = tuple(
            _shown(held) for (holder, _), held in platform.order_exchange.positions.items() if holder == address
        )
        platform.activity_reader.activities[address] = an_activity(
            balance=self.balance, available_margin=self.balance, positions=positions
        )

    def held(self, asset: str) -> HeldPosition | None:
        return self.flow_cycles.platform.order_exchange.positions.get((self.address, asset))

    def sent_in_cycle(self) -> list[MarketOrder]:
        return self.flow_cycles.platform.order_exchange.sent[self.sent_before :]

    def document(self, step: CycleStep) -> dict[str, object]:
        document = self.flow_cycles.last_record(self.flow).document(step)
        assert document is not None
        return dict(document)

    def risk_outcome(self, asset: str) -> dict[str, object]:
        outcomes = self.document(CycleStep.RISK_CHECK)["esiti"]
        assert isinstance(outcomes, list)
        [outcome] = [outcome for outcome in outcomes if outcome["asset"] == asset]
        assert isinstance(outcome, dict)
        return outcome

    def reversal_outcome(self, asset: str) -> dict[str, object]:
        outcomes = self.document(CycleStep.ORDER_EXECUTION)["inversioni"]
        assert isinstance(outcomes, list)
        [outcome] = [outcome for outcome in outcomes if outcome["asset"] == asset]
        assert isinstance(outcome, dict)
        return outcome

    def recorded_orders(self, asset: str) -> list[dict[str, object]]:
        orders = self.document(CycleStep.ORDER_EXECUTION)["risultato"]
        assert isinstance(orders, list)
        return [order for order in orders if order.get("tipo") == "Order" and _coin_of(order) == asset]


def _shown(held: HeldPosition) -> AccountPosition:
    side = TradeSide.LONG if held.direction is Direction.LONG else TradeSide.SHORT
    margin = held.size * held.entry_price / held.leverage
    return AccountPosition(held.coin, side, held.size, margin, Decimal(0), held.leverage, held.entry_price, PRICE)


def _coin_of(order: dict[str, object]) -> object:
    request = order["request"]
    assert isinstance(request, dict)
    market_order = request["market_order"]
    assert isinstance(market_order, dict)
    return market_order["coin"]


def _reduce_only(order: dict[str, object]) -> object:
    request = order["request"]
    assert isinstance(request, dict)
    market_order = request["market_order"]
    assert isinstance(market_order, dict)
    return market_order["reduce_only"]


@pytest.fixture
def flow_cycles() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def reversals(flow_cycles: FlowCycles) -> Reversals:
    return Reversals(flow_cycles)


# Given


@given(quoted('che "{user}" ha il flusso attivo "{flow}" con asset "{assets}" e soldi del flusso {funds} USDC'))
def active_flow(reversals: Reversals, user: str, flow: str, assets: str, funds: str) -> None:
    reversals.add_flow(user, flow, tuple(name.strip() for name in assets.split(",")), number(funds))


@given(quoted('che "{flow}" ha una posizione short aperta su "{asset}"'))
def short_position(reversals: Reversals, flow: str, asset: str) -> None:
    # The flow opened it in the cycle before, with its own order: the ledger and the history know where it began.
    assert flow == reversals.flow
    reversals.answer(decision(asset, "apri", "short", OPENING_QUOTA, OPENING_LEVERAGE))
    reversals.run("10:00")
    held = reversals.held(asset)
    assert held is not None
    assert held.direction is Direction.SHORT


@given(quoted('che l\'agente risponde inverti su "{asset}" con quota {quota} e leva {leverage}'))
def agent_reverses(reversals: Reversals, asset: str, quota: str, leverage: str) -> None:
    reversals.answer(decision(asset, "inverti", None, float(number(quota)), int(leverage)))


@given(quoted('che l\'agente risponde inverti su "{asset}" con direzione {direction}, quota {quota} e leva {leverage}'))
def agent_reverses_with_direction(reversals: Reversals, asset: str, direction: str, quota: str, leverage: str) -> None:
    reversals.answer(decision(asset, "inverti", direction, float(number(quota)), int(leverage)))


@given(quoted('che la chiusura della short su "{asset}" realizza una perdita di {loss} USDC'))
def closing_loses(reversals: Reversals, asset: str, loss: str) -> None:
    assert reversals.held(asset) is not None
    reversals.flow_cycles.platform.order_exchange.realized_on_close = -number(loss)


@given(quoted('che "{flow}" ha le aperture sospese per perdita massima'))
def openings_suspended(reversals: Reversals, flow: str) -> None:
    cycles = reversals.flow_cycles
    flow_of = cycles.flow(flow)
    openings = InMemoryOpeningsSuspensionAdapter(cycles.platform.flows, flow_of.tenant_id)
    openings.suspend(flow_of.id.value, OpeningsSuspension(SUSPENSION, cycles.clock.now()))


@given(quoted('che l\'exchange non esegue la chiusura della short su "{asset}"'))
def closing_refused(reversals: Reversals, asset: str) -> None:
    reversals.flow_cycles.platform.order_exchange.closing_rejections[asset] = CLOSING_REFUSED


# When


@when(quoted('il flusso "{flow}" esegue un ciclo'))
def flow_runs_cycle(reversals: Reversals, flow: str) -> None:
    assert flow == reversals.flow
    reversals.sent_before = len(reversals.flow_cycles.platform.order_exchange.sent)
    reversals.run("10:15")


# Then


@then(quoted('la posizione short su "{asset}" è chiusa per intero'))
def short_closed(reversals: Reversals, asset: str) -> None:
    [closing] = [order for order in reversals.sent_in_cycle() if order.coin == asset and order.reduce_only]
    assert closing.direction is Direction.SHORT
    assert closing.size == Decimal("0.0002")
    held = reversals.held(asset)
    assert held is None or held.direction is Direction.LONG


@then(quoted('"{flow}" ha una posizione long aperta su "{asset}" con leva {leverage}'))
def long_opened_with_leverage(reversals: Reversals, flow: str, asset: str, leverage: str) -> None:
    assert flow == reversals.flow
    held = reversals.held(asset)
    assert held is not None
    assert (held.direction, held.leverage) == (Direction.LONG, int(leverage))


@then(quoted('"{flow}" ha una posizione long aperta su "{asset}"'))
def long_opened(reversals: Reversals, flow: str, asset: str) -> None:
    assert flow == reversals.flow
    held = reversals.held(asset)
    assert held is not None
    assert held.direction is Direction.LONG


@then("il ciclo registra la chiusura e l'apertura, ciascuna col suo esito")
def closing_and_opening_recorded(reversals: Reversals) -> None:
    assert reversals.risk_outcome("BTC")["tipo"] == "ApprovedClose"
    assert reversals.reversal_outcome("BTC")["tipo"] == "ApprovedOpening"
    orders = reversals.recorded_orders("BTC")
    assert [(_reduce_only(order), order["status"]) for order in orders] == [(True, "eseguito"), (False, "eseguito")]


@then(quoted('la posizione chiusa è nello storico col motivo "{reason}"'))
def closed_in_history(reversals: Reversals, reason: str) -> None:
    [closed] = reversals.flow_cycles.platform.closed_positions.positions
    assert (closed.asset, closed.side, closed.reason) == ("BTC", TradeSide.SHORT, CloseReason(reason))


@then(quoted('la posizione long su "{asset}" impegna {margin} USDC di margine'))
def long_margin(reversals: Reversals, asset: str, margin: str) -> None:
    held = reversals.held(asset)
    assert held is not None
    assert held.direction is Direction.LONG
    assert held.size * held.entry_price / held.leverage == number(margin)
    assert Decimal(str(reversals.reversal_outcome(asset)["value"])) / held.leverage == number(margin)


@then(quoted('"{flow}" non ha posizioni aperte su "{asset}"'))
def no_position(reversals: Reversals, flow: str, asset: str) -> None:
    assert flow == reversals.flow
    assert reversals.held(asset) is None
    assert not [order for order in reversals.sent_in_cycle() if order.coin == asset and not order.reduce_only]


@then("il ciclo registra l'apertura bloccata col motivo della sospensione")
def opening_blocked_by_suspension(reversals: Reversals) -> None:
    outcome = reversals.reversal_outcome("BTC")
    assert outcome["tipo"] == "BlockedDecision"
    # A suspension for maximum loss blocks the openings with its own words, as every opening of the cycle (R3.2.2).
    assert outcome["reason"] == f"apertura BTC non eseguita: {MAXIMUM_LOSS_BLOCK}"


@then("nessuna apertura è inviata all'exchange")
def no_opening_sent(reversals: Reversals) -> None:
    assert [order for order in reversals.sent_in_cycle() if not order.reduce_only] == []
    outcome = reversals.reversal_outcome("BTC")
    assert outcome["tipo"] == "BlockedDecision"


@then(quoted('"{flow}" ha ancora la posizione short su "{asset}"'))
def still_short(reversals: Reversals, flow: str, asset: str) -> None:
    assert flow == reversals.flow
    held = reversals.held(asset)
    assert held is not None
    assert (held.direction, held.size) == (Direction.SHORT, Decimal("0.0002"))


@then(quoted('la decisione su "{asset}" è bloccata con il motivo "{reason}"'))
def decision_blocked(reversals: Reversals, asset: str, reason: str) -> None:
    outcome = reversals.risk_outcome(asset)
    assert (outcome["tipo"], outcome["reason"]) == ("BlockedDecision", reason)
    assert not [order for order in reversals.sent_in_cycle() if order.coin == asset]
