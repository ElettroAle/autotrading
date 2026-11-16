"""R3.1.1: the exit plan of an opening, from the answer of the agent to the risk check, the record of the cycle, the
state the agent receives at the next cycles and the open positions of the dashboard, run as the worker and the API
compose them (ADR piano-di-uscita-nella-decisione-dell-agente). playwright-bdd runs the scenarios of the dashboard on
its build (ADR piano-di-uscita-nella-dashboard).
"""

import json
from dataclasses import replace
from datetime import datetime
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.flows.read_cycle import ReadCycleCommand
from autotrading.application.flows.read_flow_results import ReadFlowResultsCommand
from autotrading.domain.flows.cycle_record import CycleRecord
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.exit_plan import ExitPlan
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.trade_side import TradeSide
from tests.support.activity import a_position, an_activity
from tests.support.flow_cycles import FlowCycles
from tests.support.steps import quoted

scenarios(
    "E3-rischio-capitale-e-qualita/F3.1-piano-di-uscita-e-protezione/R3.1.1-piano-di-uscita-nella-decisione.feature"
)

# A tenth of the money of the flow at leverage 2: within the exposure of the flow and above the exchange minimum.
QUOTA = 0.1
LEVERAGE = 2
PRICE = r"(?P<{}>\d+(?:,\d+)?)"
LEVELS = {"obiettivo": "target", "stop": "stop"}
NO_DECISIONS = '{"decisioni": []}'


class Openings:
    """The flow whose agent opens, the level it asked for and what the user consulted."""

    def __init__(self, flow_cycles: FlowCycles) -> None:
        self.flow_cycles = flow_cycles
        self.level = ""
        self.opening_cycle: datetime | None = None
        self.consulted: object = None

    def open(self, flow: str, side: str, asset: str, plan: dict[str, object]) -> None:
        flow_cycles = self.flow_cycles
        decision = {
            "asset": asset,
            "azione": "apri",
            "direzione": side,
            "quota": QUOTA,
            "leva": LEVERAGE,
            "obiettivo": None,
            "stop": None,
            "invalidazione": None,
            "confidenza": 70,
            "ragionamento": "rottura della resistenza",
        }
        flow_cycles.model.text = json.dumps({"decisioni": [{**decision, **plan}]})
        flow_cycles.run(flow)
        self.opening_cycle = flow_cycles.last_record(flow).planned_at

    def document(self, flow: str, step: CycleStep) -> dict[str, object]:
        return document_of(self.flow_cycles.last_record(flow), step)

    def plan_in_force(self, flow: str, asset: str) -> ExitPlan | None:
        recorded = self.flow_cycles.flow(flow)
        return self.flow_cycles.platform.exit_plans.plans.get((recorded.tenant_id, recorded.id, asset))


def document_of(record: CycleRecord, step: CycleStep) -> dict[str, object]:
    [content] = [document.content for document in record.documents if document.step is step]
    return dict(content)


def price(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


def plan_of(target: str | None = None, stop: str | None = None, invalidation: str | None = None) -> dict[str, object]:
    return {
        "obiettivo": None if target is None else int(price(target)),
        "stop": None if stop is None else int(price(stop)),
        "invalidazione": invalidation,
    }


def recorded_plan(decision: object) -> dict[str, object]:
    assert isinstance(decision, dict)
    opening = decision["opening"]
    assert isinstance(opening, dict)
    plan = opening["exit_plan"]
    assert isinstance(plan, dict)
    return plan


def decision_on(document: dict[str, object], asset: str) -> object:
    decisions = document["decisioni"]
    assert isinstance(decisions, list)
    [decision] = [decision for decision in decisions if decision["asset"] == asset]
    return decision


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    flow_cycles = FlowCycles()
    # The runner records the cycles where the API reads them, as the database does for worker and API.
    flow_cycles.platform.cycles = flow_cycles.records
    return flow_cycles


@pytest.fixture
def openings(flow_cycles: FlowCycles) -> Openings:
    return Openings(flow_cycles)


def show_position(flow_cycles: FlowCycles, flow: str, asset: str) -> None:
    """The position the opening left, as the exchange shows it to the worker and to the API."""
    recorded = flow_cycles.flow(flow)
    held = a_position(asset, margin=Decimal(10), size=Decimal("0.0003"), leverage=LEVERAGE)
    activity = an_activity(positions=(held,))
    address = flow_cycles.credentials_of(flow).value("account_address")
    flow_cycles.platform.activity_reader.activities[address] = activity
    flow_cycles.platform.account_activity.activities[recorded.assigned_account_id] = activity
    flow_cycles.platform.ledger.expect(recorded.id, asset, held.size if held.side is TradeSide.LONG else -held.size)


# Given


@given(quoted('che "{user}" ha il flusso "{flow}" attivo con asset "{asset}"'))
def active_flow(flow_cycles: FlowCycles, user: str, flow: str, asset: str) -> None:
    flow_cycles.add_flow(user, flow, assets=(asset,))


@given(
    parsers.re(rf'^che il prezzo di mercato di "(?P<asset>[^"]+)" sull\'exchange del conto è {PRICE.format("value")}$')
)
def market_price(flow_cycles: FlowCycles, asset: str, value: str) -> None:
    flow_cycles.limits.set(asset, market_price=price(value))
    exchange = flow_cycles.platform.order_exchange
    exchange.markets[asset] = replace(exchange.markets[asset], mid_price=price(value))


@given(
    parsers.re(
        r'^che "(?P<flow>[^"]+)" ha aperto long su "(?P<asset>[^"]+)" con obiettivo '
        rf'{PRICE.format("target")}, stop {PRICE.format("stop")} e invalidazione "(?P<invalidation>[^"]+)"$'
    )
)
def opened_with_plan(  # noqa: PLR0917 - one argument per value of the step
    openings: Openings, flow: str, asset: str, target: str, stop: str, invalidation: str
) -> None:
    openings.open(flow, "long", asset, plan_of(target, stop, invalidation))
    show_position(openings.flow_cycles, flow, asset)
    openings.flow_cycles.model.text = NO_DECISIONS


@given(
    parsers.re(
        r'^che "(?P<flow>[^"]+)" ha aperto long su "(?P<asset>[^"]+)" con obiettivo '
        rf"{PRICE.format('target')} e stop {PRICE.format('stop')}$"
    )
)
def opened_with_levels(openings: Openings, flow: str, asset: str, target: str, stop: str) -> None:
    openings.open(flow, "long", asset, plan_of(target, stop))
    show_position(openings.flow_cycles, flow, asset)
    openings.flow_cycles.model.text = NO_DECISIONS


# When


@when(
    parsers.re(
        r'^l\'agente di "(?P<flow>[^"]+)" decide di aprire long su "(?P<asset>[^"]+)" con obiettivo '
        rf'{PRICE.format("target")}, stop {PRICE.format("stop")} e invalidazione "(?P<invalidation>[^"]+)"$'
    )
)
def agent_opens_with_plan(  # noqa: PLR0917 - one argument per value of the step
    openings: Openings, flow: str, asset: str, target: str, stop: str, invalidation: str
) -> None:
    openings.open(flow, "long", asset, plan_of(target, stop, invalidation))


@when(quoted('l\'agente di "{flow}" decide di aprire long su "{asset}" senza piano di uscita'))
def agent_opens_without_plan(openings: Openings, flow: str, asset: str) -> None:
    openings.open(flow, "long", asset, plan_of())


@when(
    parsers.re(
        r'^l\'agente di "(?P<flow>[^"]+)" decide di aprire (?P<side>long|short) su "(?P<asset>[^"]+)" con '
        rf"(?P<level>obiettivo|stop) {PRICE.format('value')}$"
    )
)
def agent_opens_with_level(  # noqa: PLR0917 - one argument per value of the step
    openings: Openings, flow: str, side: str, asset: str, level: str, value: str
) -> None:
    openings.level = level
    openings.open(flow, side, asset, {level: int(price(value))})


@when(quoted('parte il ciclo successivo di "{flow}"'))
def next_cycle(flow_cycles: FlowCycles, flow: str) -> None:
    flow_cycles.run(flow, "10:15")


@when(quoted('"{user}" apre le posizioni aperte di "{flow}" nella dashboard'))
def open_positions_in_dashboard(openings: Openings, user: str, flow: str) -> None:
    command = ReadFlowResultsCommand(openings.flow_cycles.flow(flow).id.value)
    openings.consulted = openings.flow_cycles.platform.use_cases_of(user).read_flow_results.execute(command).state


@when(quoted('"{user}" apre nella dashboard il dettaglio del ciclo dell\'apertura'))
def opening_cycle_in_dashboard(openings: Openings, user: str) -> None:
    assert openings.opening_cycle is not None
    flow_id = openings.flow_cycles.flow("alfa").id.value
    command = ReadCycleCommand(flow_id, openings.opening_cycle)
    openings.consulted = openings.flow_cycles.platform.use_cases_of(user).read_cycle.execute(command)


# Then


@then(
    parsers.re(
        rf'^la decisione registrata di "(?P<flow>[^"]+)" contiene obiettivo {PRICE.format("target")}, stop '
        rf'{PRICE.format("stop")} e invalidazione "(?P<invalidation>[^"]+)"$'
    )
)
def recorded_decision_with_plan(openings: Openings, flow: str, target: str, stop: str, invalidation: str) -> None:
    plan = recorded_plan(decision_on(openings.document(flow, CycleStep.AGENT_DECISION), "BTC"))
    assert (price(str(plan["target"])), price(str(plan["stop"])), plan["invalidation"]) == (
        price(target),
        price(stop),
        invalidation,
    )


@then(quoted('"{flow}" apre la posizione su "{asset}"'))
def flow_opens(flow_cycles: FlowCycles, flow: str, asset: str) -> None:
    assert flow_cycles.flow(flow).name.value == flow
    assert [order.coin for order in flow_cycles.platform.order_exchange.sent if not order.reduce_only] == [asset]


@then(quoted('la decisione registrata di "{flow}" non ha obiettivo né invalidazione'))
def recorded_decision_without_plan(openings: Openings, flow: str) -> None:
    plan = recorded_plan(decision_on(openings.document(flow, CycleStep.AGENT_DECISION), "BTC"))
    assert (plan["target"], plan["invalidation"]) == (None, None)


@then(quoted('"{flow}" apre la posizione su "{asset}" senza quel livello nel piano'))
def flow_opens_without_level(openings: Openings, flow: str, asset: str) -> None:
    sent = openings.flow_cycles.platform.order_exchange.sent
    assert [order.coin for order in sent if not order.reduce_only] == [asset]
    plan = openings.plan_in_force(flow, asset)
    assert plan is not None
    assert getattr(plan, LEVELS[openings.level]) is None


@then(quoted('il ciclo di "{flow}" registra "{note}"'))
def cycle_records_note(openings: Openings, flow: str, note: str) -> None:
    outcomes = openings.document(flow, CycleStep.RISK_CHECK)["esiti"]
    assert isinstance(outcomes, list)
    reasons = [adjustment["reason"] for outcome in outcomes for adjustment in outcome.get("adjustments", [])]
    assert note in reasons


@then(
    parsers.re(
        r'^lo stato del flusso inviato all\'agente riporta per la posizione su "(?P<asset>[^"]+)" obiettivo '
        rf'{PRICE.format("target")}, stop {PRICE.format("stop")} e invalidazione "(?P<invalidation>[^"]+)"$'
    )
)
def plan_in_context(flow_cycles: FlowCycles, asset: str, target: str, stop: str, invalidation: str) -> None:
    state = flow_cycles.context()["stato_del_flusso"]
    assert isinstance(state, dict)
    [held] = [held for held in state["posizioni_aperte"] if held["asset"] == asset]
    assert (price(held["obiettivo"]), price(held["stop"]), held["invalidazione"]) == (
        price(target),
        price(stop),
        invalidation,
    )


@then(
    parsers.re(
        rf'^la posizione su "(?P<asset>[^"]+)" mostra obiettivo {PRICE.format("target")}, stop '
        rf'{PRICE.format("stop")} e invalidazione "(?P<invalidation>[^"]+)"$'
    )
)
def plan_among_open_positions(openings: Openings, asset: str, target: str, stop: str, invalidation: str) -> None:
    state = openings.consulted
    assert isinstance(state, FlowState)
    assert asset in {position.asset for position in state.positions}
    assert state.exit_plan_of(asset) == ExitPlan(price(target), price(stop), invalidation)


@then(
    parsers.re(
        rf'^la decisione su "(?P<asset>[^"]+)" mostra obiettivo {PRICE.format("target")} e stop '
        rf"{PRICE.format('stop')}$"
    )
)
def plan_in_cycle_detail(openings: Openings, asset: str, target: str, stop: str) -> None:
    record = openings.consulted
    assert isinstance(record, CycleRecord)
    plan = recorded_plan(decision_on(document_of(record, CycleStep.AGENT_DECISION), asset))
    assert (price(str(plan["target"])), price(str(plan["stop"]))) == (price(target), price(stop))
