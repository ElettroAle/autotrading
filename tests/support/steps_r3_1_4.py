"""R3.1.4: the confidence of every decision of the agent, recorded with it, and the minimum confidence of the flow that
stops only the weak openings, run as the worker and the API compose them (ADR
confidenza-nella-decisione-e-confidenza-minima). playwright-bdd runs the scenario of the dashboard on its build (ADR
confidenza-nella-dashboard).
"""

import json
from dataclasses import replace
from datetime import datetime
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, then, when

from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.application.flows.read_cycle import ReadCycleCommand
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.cycle_record import CycleRecord
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.minimum_confidence import MinimumConfidence
from tests.support.activity import a_position, an_activity
from tests.support.flow_cycles import FlowCycles
from tests.support.steps import quoted

# A tenth of the money of the flow at leverage 2: within the exposure of the flow and above the exchange minimum.
QUOTA = 0.1
LEVERAGE = 2
NO_DECISIONS = '{"decisioni": []}'
# The flow without a minimum confidence trades the same asset on an account of its own: two flows of one account
# never share an asset (R1.1.2).
OTHER_ACCOUNT = "secondo"
OPENING_CYCLE, CLOSING_CYCLE = "10:00", "10:15"


class Confidences:
    """The flows whose agent decides with a confidence, and what the user set or consulted."""

    def __init__(self, flow_cycles: FlowCycles) -> None:
        self.flow_cycles = flow_cycles
        self.decided_cycle: datetime | None = None
        self.consulted: CycleRecord | None = None
        self.error: AutotradingError | None = None
        self.version_before = 0

    def decide(self, flow: str, decision: dict[str, object], clock: str = OPENING_CYCLE) -> None:
        self.flow_cycles.model.text = json.dumps({"decisioni": [decision]})
        self.flow_cycles.run(flow, clock)
        self.decided_cycle = self.flow_cycles.last_record(flow).planned_at
        self.flow_cycles.model.text = NO_DECISIONS

    def open(self, flow: str, asset: str, confidence: int) -> None:
        self.decide(
            flow,
            {
                "asset": asset,
                "azione": "apri",
                "direzione": "long",
                "quota": QUOTA,
                "leva": LEVERAGE,
                "obiettivo": None,
                "stop": None,
                "invalidazione": None,
                "confidenza": confidence,
                "ragionamento": "rottura della resistenza",
            },
        )

    def show_position(self, flow: str, asset: str) -> None:
        """The position the opening left, as the exchange shows it to the reconciliation of the next cycle."""
        flow_cycles = self.flow_cycles
        recorded = flow_cycles.flow(flow)
        held = a_position(asset, margin=Decimal(10), size=Decimal("0.0003"), leverage=LEVERAGE)
        activity = an_activity(positions=(held,))
        flow_cycles.platform.activity_reader.activities[self.address(flow)] = activity
        flow_cycles.platform.account_activity.activities[recorded.assigned_account_id] = activity
        flow_cycles.platform.ledger.expect(recorded.id, asset, held.size)

    def address(self, flow: str) -> str:
        return self.flow_cycles.credentials_of(flow, self.account_of(flow)).value("account_address")

    def account_of(self, flow: str) -> str:
        return OTHER_ACCOUNT if flow == "beta" else "test-1"

    def document(self, flow: str, step: CycleStep) -> dict[str, object]:
        return document_of(self.flow_cycles.last_record(flow), step)

    def modify(self, user: str, flow: str, minimum_confidence: int) -> None:
        recorded = self.flow_cycles.flow(flow)
        self.version_before = recorded.configuration.version
        command = ModifyFlowCommand(recorded.id, minimum_confidence=minimum_confidence)
        try:
            self.flow_cycles.platform.use_cases_of(user).modify_flow.execute(command)
        except AutotradingError as error:
            self.error = error


def document_of(record: CycleRecord, step: CycleStep) -> dict[str, object]:
    document = record.document(step)
    assert document is not None
    return dict(document)


def entry_on(document: dict[str, object], key: str, asset: str) -> dict[str, object]:
    entries = document[key]
    assert isinstance(entries, list)
    [entry] = [entry for entry in entries if entry["asset"] == asset]
    assert isinstance(entry, dict)
    return entry


def openings_sent(flow_cycles: FlowCycles) -> list[str]:
    return [order.coin for order in flow_cycles.platform.order_exchange.sent if not order.reduce_only]


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    flow_cycles = FlowCycles()
    # The runner records the cycles where the API reads them, as the database does for worker and API.
    flow_cycles.platform.cycles = flow_cycles.records
    return flow_cycles


@pytest.fixture
def confidences(flow_cycles: FlowCycles) -> Confidences:
    return Confidences(flow_cycles)


# Given


@given(quoted('che "{user}" ha il flusso "{flow}" attivo con asset "{asset}" e confidenza minima {minimum}'))
def flow_with_minimum(flow_cycles: FlowCycles, user: str, flow: str, asset: str, minimum: str) -> None:
    flow_cycles.add_flow(user, flow, assets=(asset,))
    flow_cycles.reconfigure(
        flow, lambda configuration: replace(configuration, minimum_confidence=MinimumConfidence(int(minimum)))
    )


@given(quoted('che "{user}" ha il flusso "{flow}" attivo con asset "{asset}" senza confidenza minima'))
def flow_without_minimum(flow_cycles: FlowCycles, user: str, flow: str, asset: str) -> None:
    flow_cycles.add_flow(user, flow, assets=(asset,), account=OTHER_ACCOUNT)
    assert flow_cycles.flow(flow).configuration.minimum_confidence is None


@given(quoted('che "{flow}" ha una posizione aperta su "{asset}"'))
def open_position(confidences: Confidences, flow: str, asset: str) -> None:
    confidences.open(flow, asset, 75)
    assert openings_sent(confidences.flow_cycles) == [asset]
    confidences.show_position(flow, asset)


@given(quoted('che l\'agente di "{flow}" ha deciso di aprire long su "{asset}" con confidenza {confidence}'))
def agent_decided(confidences: Confidences, flow: str, asset: str, confidence: str) -> None:
    confidences.open(flow, asset, int(confidence))


# When


@when(quoted('l\'agente di "{flow}" decide di aprire long su "{asset}" con confidenza {confidence}'))
def agent_opens(confidences: Confidences, flow: str, asset: str, confidence: str) -> None:
    confidences.open(flow, asset, int(confidence))


@when(quoted('l\'agente di "{flow}" decide di chiudere la posizione su "{asset}" con confidenza {confidence}'))
def agent_closes(confidences: Confidences, flow: str, asset: str, confidence: str) -> None:
    decision = {
        "asset": asset,
        "azione": "chiudi",
        "confidenza": int(confidence),
        "ragionamento": "obiettivo raggiunto",
    }
    confidences.decide(flow, decision, CLOSING_CYCLE)


@when(parsers.re(r'^"(?P<user>[^"]+)" imposta la confidenza minima di "(?P<flow>[^"]+)" a (?P<value>-?\d+)$'))
def sets_minimum(confidences: Confidences, user: str, flow: str, value: str) -> None:
    confidences.modify(user, flow, int(value))


@when(quoted('l\'agente di "{flow}" risponde con una decisione su "{asset}" senza confidenza'))
def agent_answers_without_confidence(confidences: Confidences, flow: str, asset: str) -> None:
    confidences.decide(flow, {"asset": asset, "azione": "mantieni", "ragionamento": "mercato laterale"})


@when(quoted('"{user}" apre nella dashboard il dettaglio di quel ciclo'))
def cycle_in_dashboard(confidences: Confidences, user: str) -> None:
    assert confidences.decided_cycle is not None
    command = ReadCycleCommand(confidences.flow_cycles.flow("alfa").id.value, confidences.decided_cycle)
    confidences.consulted = confidences.flow_cycles.platform.use_cases_of(user).read_cycle.execute(command)


# Then


@then(quoted('la decisione registrata di "{flow}" su "{asset}" ha confidenza {confidence}'))
def recorded_confidence(confidences: Confidences, flow: str, asset: str, confidence: str) -> None:
    decision = entry_on(confidences.document(flow, CycleStep.AGENT_DECISION), "decisioni", asset)
    assert decision["confidence"] == int(confidence)


@then(quoted('"{flow}" non apre la posizione su "{asset}"'))
def flow_does_not_open(confidences: Confidences, flow: str, asset: str) -> None:
    outcome = entry_on(confidences.document(flow, CycleStep.RISK_CHECK), "esiti", asset)
    assert outcome["tipo"] == "BlockedDecision"
    assert openings_sent(confidences.flow_cycles) == []


@then(quoted('il ciclo di "{flow}" registra "{note}"'))
def cycle_records(confidences: Confidences, flow: str, note: str) -> None:
    outcomes = confidences.document(flow, CycleStep.RISK_CHECK)["esiti"]
    assert isinstance(outcomes, list)
    assert note in [outcome.get("reason") for outcome in outcomes]


@then(quoted('"{flow}" apre la posizione su "{asset}"'))
def flow_opens(confidences: Confidences, flow: str, asset: str) -> None:
    assert entry_on(confidences.document(flow, CycleStep.RISK_CHECK), "esiti", asset)["tipo"] == "ApprovedOpening"
    assert openings_sent(confidences.flow_cycles) == [asset]


@then(quoted('"{flow}" chiude la posizione su "{asset}"'))
def flow_closes(confidences: Confidences, flow: str, asset: str) -> None:
    assert entry_on(confidences.document(flow, CycleStep.RISK_CHECK), "esiti", asset)["tipo"] == "ApprovedClose"
    sent = confidences.flow_cycles.platform.order_exchange.sent
    assert [(order.coin, order.reduce_only) for order in sent] == [(asset, False), (asset, True)]


@then(quoted('la modifica viene rifiutata con "{message}"'))
def change_refused(confidences: Confidences, message: str) -> None:
    assert confidences.error is not None
    assert str(confidences.error) == message
    assert confidences.flow_cycles.flow("alfa").configuration.version == confidences.version_before


@then(quoted('la decisione su "{asset}" viene scartata come non conforme'))
def decision_discarded(confidences: Confidences, asset: str) -> None:
    discarded = entry_on(confidences.document("alfa", CycleStep.AGENT_DECISION), "scartate", asset)
    assert discarded["reason"] == "campo obbligatorio mancante: confidenza"


@then(quoted('la decisione su "{asset}" mostra confidenza {confidence}'))
def confidence_in_cycle_detail(confidences: Confidences, asset: str, confidence: str) -> None:
    record = confidences.consulted
    assert record is not None
    decision = entry_on(document_of(record, CycleStep.AGENT_DECISION), "decisioni", asset)
    assert decision["confidence"] == int(confidence)
