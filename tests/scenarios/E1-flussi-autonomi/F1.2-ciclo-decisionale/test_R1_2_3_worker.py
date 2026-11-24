import json
from dataclasses import replace
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.domain.flows.cycle_record import CycleOutcome
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.orders.protection_kind import ProtectionKind

# The steps of the cycle scenarios are shared by the five requirements of F1.2.
from tests.support.cycle_steps import *  # noqa: F403
from tests.support.flow_cycles import FlowCycles
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.2-ciclo-decisionale/R1.2.3-errori-transitori/worker/R1.2.3-errori-transitori.feature")

# The protections are retried by the orders context as the worker composes it, not by the fake steps of the cycle
# (Bug 720, ADR protezioni-ritentate-nel-ciclo).
USER = "anna"
ENTRY_PRICE = Decimal(60000)
FEE = Decimal("0.02")
OPENING = {
    "azione": "apri",
    "direzione": "long",
    "quota": 0.1,
    "leva": 2,
    "obiettivo": None,
    "stop": None,
    "invalidazione": None,
    "confidenza": 70,
    "ragionamento": "rottura della resistenza",
}


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    return FlowCycles()


def address_of(flow_cycles: FlowCycles, flow: str) -> str:
    return flow_cycles.credentials_of(flow).value("account_address")


@given(quoted('che l\'agente del flusso "{flow}" apre una posizione su "{asset}"'))
def agent_opens_a_position(flow_cycles: FlowCycles, flow: str, asset: str) -> None:
    flow_cycles.add_flow(USER, flow, assets=(asset,))
    flow_cycles.limits.set(asset, market_price=ENTRY_PRICE)
    exchange = flow_cycles.platform.order_exchange
    exchange.markets[asset] = replace(exchange.markets[asset], mid_price=ENTRY_PRICE)
    exchange.fill_at = (ENTRY_PRICE, FEE)
    flow_cycles.model.text = json.dumps({"decisioni": [{"asset": asset, **OPENING}]})


@given("che l'exchange non risponde al piazzamento dello stop loss una volta")
def stop_loss_unreached_once(flow_cycles: FlowCycles) -> None:
    flow_cycles.platform.protection_exchange.unreached_placements = 1


@given("che l'exchange piazza lo stop loss senza rispondere una volta")
def stop_loss_answer_lost_once(flow_cycles: FlowCycles) -> None:
    flow_cycles.platform.protection_exchange.lost_placements = 1


@when(quoted('il ciclo del flusso "{flow}" invia i suoi ordini'))
def cycle_sends_its_orders(flow_cycles: FlowCycles, flow: str) -> None:
    flow_cycles.run(flow)


@then(quoted('il ciclo del flusso "{flow}" è registrato come concluso'))
def cycle_recorded_as_completed(flow_cycles: FlowCycles, flow: str) -> None:
    assert flow_cycles.last_record(flow).outcome is CycleOutcome.COMPLETED


@then(quoted('la posizione su "{asset}" ha un solo stop loss sull\'exchange'))
def one_stop_loss(flow_cycles: FlowCycles, asset: str) -> None:
    resting = flow_cycles.platform.protection_exchange.of(address_of(flow_cycles, "alfa"), asset)
    assert [each.kind for each in resting] == [ProtectionKind.STOP_LOSS]


@then(parsers.re(r"^il ciclo attende (?P<seconds>\d+) secondi prima di ritentare lo stop loss$"))
def waits_before_the_stop_loss(flow_cycles: FlowCycles, seconds: str) -> None:
    assert flow_cycles.pause.pauses == [float(seconds)]


@then(quoted('il registro del ciclo mostra il tentativo {attempt} fallito al passo "{step}"'))
def failed_attempt_shown(flow_cycles: FlowCycles, attempt: str, step: str) -> None:
    recorded = flow_cycles.last_record("alfa").failed_attempts
    assert [(each.step, each.attempt) for each in recorded] == [(CycleStep(step), int(attempt))]
