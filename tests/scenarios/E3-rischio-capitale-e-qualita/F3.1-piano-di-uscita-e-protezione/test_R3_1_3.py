"""R3.1.3: the agent moves the stop and the target of a position already open, the platform replaces its protections on
the exchange and the plan in force follows what was placed, run as the worker composes it (ADR
aggiornamento-del-piano-di-uscita-di-una-posizione-aperta).
"""

import json
from dataclasses import replace
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.protection_defaults import ProtectionDefaults
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ProtectionOrder
from tests.support.activity import a_position, an_activity
from tests.support.flow_cycles import FlowCycles
from tests.support.steps import quoted

scenarios(
    "E3-rischio-capitale-e-qualita/F3.1-piano-di-uscita-e-protezione/R3.1.3-aggiornamento-di-stop-e-obiettivo.feature"
)

# A tenth of the money of the flow at leverage 2: within the exposure of the flow and above the exchange minimum.
QUOTA = 0.1
LEVERAGE = 2
FEE = Decimal("0.02")
NUMBER = r"(?P<{}>\d+(?:,\d+)?)"
NO_DECISIONS = '{"decisioni": []}'
KIND_OF = {"stop loss": ProtectionKind.STOP_LOSS, "take profit": ProtectionKind.TAKE_PROFIT}
UPDATE_CYCLE = "10:30"


def number(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


class PlanUpdates:
    """The flow with its position open on the exchange, and what its agent decides on it."""

    def __init__(self, flow_cycles: FlowCycles) -> None:
        self.flow_cycles = flow_cycles

    def address(self, flow: str) -> str:
        return self.flow_cycles.credentials_of(flow).value("account_address")

    def at_price(self, asset: str, price: Decimal) -> None:
        """The market and the execution of the next orders at this price."""
        flow_cycles = self.flow_cycles
        flow_cycles.limits.set(asset, market_price=price)
        exchange = flow_cycles.platform.order_exchange
        exchange.markets[asset] = replace(exchange.markets[asset], mid_price=price)
        exchange.fill_at = (price, FEE)

    def decide(self, flow: str, decision: dict[str, object], clock: str = UPDATE_CYCLE) -> None:
        self.flow_cycles.model.text = json.dumps({"decisioni": [decision]})
        self.flow_cycles.run(flow, clock)
        self.flow_cycles.model.text = NO_DECISIONS

    def update(self, flow: str, asset: str, **plan: object) -> None:
        decision = {
            "asset": asset,
            "azione": "aggiorna",
            "direzione": None,
            "quota": None,
            "leva": None,
            "obiettivo": None,
            "stop": None,
            "invalidazione": None,
            "togli_obiettivo": False,
            "confidenza": 70,
            "ragionamento": "proteggo il guadagno",
        }
        self.decide(flow, {**decision, **plan})

    def protections(self, flow: str, asset: str, kind: ProtectionKind) -> list[ProtectionOrder]:
        resting = self.flow_cycles.platform.protection_exchange.of(self.address(flow), asset)
        return [each for each in resting if each.kind is kind]

    def document(self, flow: str, step: CycleStep) -> dict[str, object]:
        document = self.flow_cycles.last_record(flow).document(step)
        assert document is not None
        return dict(document)

    def notes(self, flow: str) -> list[str]:
        outcome = self.document(flow, CycleStep.ORDER_EXECUTION)["risultato"]
        assert isinstance(outcome, list)
        return [each["text"] for each in outcome if each.get("tipo") == "ProtectionNote"]

    def risk_reasons(self, flow: str) -> list[str]:
        outcomes = self.document(flow, CycleStep.RISK_CHECK)["esiti"]
        assert isinstance(outcomes, list)
        return [adjustment["reason"] for outcome in outcomes for adjustment in outcome.get("adjustments", [])]


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def updates(flow_cycles: FlowCycles) -> PlanUpdates:
    return PlanUpdates(flow_cycles)


# Given


@given(quoted('che "{user}" ha il flusso "{flow}" attivo con asset "{asset}" e stop loss predefinito {stop}%'))
def active_flow(updates: PlanUpdates, user: str, flow: str, asset: str, stop: str) -> None:
    flow_cycles = updates.flow_cycles
    flow_cycles.add_flow(user, flow, assets=(asset,))
    flow_cycles.reconfigure(
        flow,
        lambda configuration: replace(configuration, protection_defaults=ProtectionDefaults.of(number(stop), None)),
    )


@given(
    parsers.re(
        r'^che "(?P<flow>[^"]+)" ha una posizione long su "(?P<asset>[^"]+)" con prezzo d\'ingresso '
        rf"{NUMBER.format('price')}, stop loss a {NUMBER.format('stop')} e take profit a {NUMBER.format('target')}$"
    )
)
def protected_position(  # noqa: PLR0917 - one argument per value of the step
    updates: PlanUpdates, flow: str, asset: str, price: str, stop: str, target: str
) -> None:
    flow_cycles = updates.flow_cycles
    updates.at_price(asset, number(price))
    opening = {
        "asset": asset,
        "azione": "apri",
        "direzione": "long",
        "quota": QUOTA,
        "leva": LEVERAGE,
        "obiettivo": int(number(target)),
        "stop": int(number(stop)),
        "invalidazione": None,
        "togli_obiettivo": False,
        "confidenza": 70,
        "ragionamento": "rottura della resistenza",
    }
    updates.decide(flow, opening, "10:00")
    # The position the opening left, as the exchange shows it to the reconciliation of the next cycles.
    recorded = flow_cycles.flow(flow)
    held = a_position(asset, margin=Decimal(10), size=Decimal("0.0003"), leverage=LEVERAGE)
    flow_cycles.platform.activity_reader.activities[updates.address(flow)] = an_activity(positions=(held,))
    flow_cycles.platform.ledger.expect(recorded.id, asset, held.size)
    flow_cycles.run(flow, "10:15")
    position = flow_cycles.platform.order_exchange.positions[updates.address(flow), asset]
    assert position.entry_price == number(price)
    assert [each.trigger_price for each in updates.protections(flow, asset, ProtectionKind.STOP_LOSS)] == [number(stop)]
    assert [each.trigger_price for each in updates.protections(flow, asset, ProtectionKind.TAKE_PROFIT)] == [
        number(target)
    ]


@given(
    parsers.re(rf'^che il prezzo di mercato di "(?P<asset>[^"]+)" sull\'exchange del conto è {NUMBER.format("value")}$')
)
def market_price(updates: PlanUpdates, asset: str, value: str) -> None:
    updates.at_price(asset, number(value))


@given(
    parsers.re(r"^che l'exchange rifiuta gli ordini di (?P<kind>stop loss|take profit) con \"(?P<message>[^\"]+)\"$")
)
def exchange_refuses(updates: PlanUpdates, kind: str, message: str) -> None:
    updates.flow_cycles.platform.protection_exchange.rejections[KIND_OF[kind]] = message


@given(quoted('che l\'agente di "{flow}" ha aggiornato lo stop su "{asset}" a {price}'))
def stop_updated(updates: PlanUpdates, flow: str, asset: str, price: str) -> None:
    updates.update(flow, asset, stop=int(number(price)))
    assert [each.trigger_price for each in updates.protections(flow, asset, ProtectionKind.STOP_LOSS)] == [
        number(price)
    ]


@given(quoted('che "{flow}" ha anche l\'asset "{asset}" senza posizione aperta'))
def asset_without_position(updates: PlanUpdates, flow: str, asset: str) -> None:
    def with_asset(configuration: FlowConfiguration) -> FlowConfiguration:
        return replace(configuration, assets=(*configuration.assets, asset))

    updates.flow_cycles.reconfigure(flow, with_asset)
    assert (updates.address(flow), asset) not in updates.flow_cycles.platform.order_exchange.positions


# When


@when(quoted('l\'agente di "{flow}" decide di aggiornare lo stop su "{asset}" a {price}'))
def agent_updates_stop(updates: PlanUpdates, flow: str, asset: str, price: str) -> None:
    updates.update(flow, asset, stop=int(number(price)))


@when(quoted('l\'agente di "{flow}" decide di aggiornare l\'obiettivo su "{asset}" a {price}'))
def agent_updates_target(updates: PlanUpdates, flow: str, asset: str, price: str) -> None:
    updates.update(flow, asset, obiettivo=int(number(price)))


@when(quoted('l\'agente di "{flow}" decide di togliere l\'obiettivo su "{asset}"'))
def agent_removes_target(updates: PlanUpdates, flow: str, asset: str) -> None:
    updates.update(flow, asset, togli_obiettivo=True)


@when(quoted('parte il ciclo successivo di "{flow}"'))
def next_cycle(updates: PlanUpdates, flow: str) -> None:
    updates.flow_cycles.run(flow, "10:45")


# Then


@then(
    parsers.re(
        r"^sull'exchange l'unico ordine di (?P<kind>stop loss|take profit) di \"(?P<flow>[^\"]+)\" su "
        rf"\"(?P<asset>[^\"]+)\" è a {NUMBER.format('price')}$"
    )
)
def only_protection_at(updates: PlanUpdates, kind: str, flow: str, asset: str, price: str) -> None:
    [protection] = updates.protections(flow, asset, KIND_OF[kind])
    assert protection.trigger_price == number(price)


@then(quoted('sull\'exchange non c\'è un ordine di take profit di "{flow}" su "{asset}"'))
def no_take_profit(updates: PlanUpdates, flow: str, asset: str) -> None:
    assert updates.protections(flow, asset, ProtectionKind.TAKE_PROFIT) == []


@then(quoted('il ciclo di "{flow}" registra "{note}"'))
def cycle_records(updates: PlanUpdates, flow: str, note: str) -> None:
    assert note in [*updates.risk_reasons(flow), *updates.notes(flow)]


@then(
    parsers.re(
        r'^lo stato del flusso inviato all\'agente riporta per la posizione su "(?P<asset>[^"]+)" stop '
        rf"{NUMBER.format('stop')}$"
    )
)
def plan_in_context(updates: PlanUpdates, asset: str, stop: str) -> None:
    state = updates.flow_cycles.context()["stato_del_flusso"]
    assert isinstance(state, dict)
    [held] = [held for held in state["posizioni_aperte"] if held["asset"] == asset]
    assert number(held["stop"]) == number(stop)


@then(quoted('la decisione su "{asset}" viene bloccata con "{reason}"'))
def decision_blocked(updates: PlanUpdates, asset: str, reason: str) -> None:
    outcomes = updates.document("alfa", CycleStep.RISK_CHECK)["esiti"]
    assert isinstance(outcomes, list)
    assert {"asset": asset, "reason": reason, "tipo": "BlockedDecision"} in [
        {key: outcome.get(key) for key in ("asset", "reason", "tipo")} for outcome in outcomes
    ]
