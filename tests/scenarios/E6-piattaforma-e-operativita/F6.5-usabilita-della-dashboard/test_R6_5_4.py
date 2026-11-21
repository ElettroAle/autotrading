"""R6.5.4: the last decision of the agent in a flow, read on the use cases of the flows context (ADR
decisioni-del-ciclo-registrate-per-asset). playwright-bdd runs the same scenarios on the Overview of the dashboard (ADR
riquadro-dell-ultima-decisione-nella-panoramica).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.flows.read_cycle import ReadCycleCommand
from autotrading.application.flows.read_last_decision import ReadLastDecisionCommand
from autotrading.domain.flows.cycle_record import CycleFailure, CycleOutcome, CycleRecord
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.recorded_decision import DecidedCycle, DecisionAction, RecordedDecision
from autotrading.domain.flows.trade_side import TradeSide
from tests.support.api_session import ApiSession
from tests.support.flows import a_flow
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios(
    "E6-piattaforma-e-operativita/F6.5-usabilita-della-dashboard/R6.5.4-ultima-decisione-nella-panoramica.feature"
)

# The user who owns the flows of the scenarios and opens their Overview.
OWNER = "anna"
DAY = datetime(2026, 11, 16, tzinfo=UTC)
REASONING = (
    "Il prezzo ha rotto la resistenza con volumi in aumento e il sentiment resta positivo: apro una posizione long "
    "con leva contenuta e uno stop sotto il minimo della giornata, pronto a chiuderla se il volume cala."
)


def at(time: str) -> datetime:
    hours, minutes = time.split(":")
    return DAY.replace(hour=int(hours), minute=int(minutes))


@dataclass
class LastDecisions:
    platform: Platform = field(default_factory=Platform)
    flows: dict[str, Flow] = field(default_factory=dict)
    seen: DecidedCycle | None = None
    opened_by: str = ""
    opened_flow: str = ""
    answered: dict[str, object] = field(default_factory=dict)

    def flow(self, name: str) -> Flow:
        if name not in self.flows:
            flow = a_flow(self.platform.tenant_of(OWNER), name=name)
            self.platform.flows.flows.append(flow)
            self.flows[name] = flow
        return self.flows[name]

    def record(self, record: CycleRecord) -> None:
        self.platform.cycles.record(record)

    def decide(self, name: str, time: str, decision: RecordedDecision) -> None:
        cycle = CycleRecord(self.flow(name).id.value, at(time), CycleOutcome.COMPLETED, decisions=(decision,))
        self.record(cycle)

    def fail(self, name: str, time: str, step: CycleStep, *decisions: RecordedDecision) -> None:
        failure = CycleFailure(step, "ModelUnavailableError", "fornitore IA non raggiungibile")
        cycle = CycleRecord(
            self.flow(name).id.value, at(time), CycleOutcome.FAILED, failure=failure, decisions=decisions
        )
        self.record(cycle)

    def open_overview(self, user: str, name: str) -> None:
        command = ReadLastDecisionCommand(self.flow(name).id.value)
        self.seen = self.platform.use_cases_of(user).read_last_decision.execute(command)
        self.opened_by, self.opened_flow = user, name

    def shown(self) -> DecidedCycle:
        assert self.seen is not None, "nessuna decisione mostrata"
        return self.seen


def an_opening(asset: str, direction: str, confidence: int) -> RecordedDecision:
    return RecordedDecision(asset, DecisionAction.OPEN, TradeSide(direction), confidence, REASONING)


@pytest.fixture
def decisions() -> LastDecisions:
    return LastDecisions()


# Given


@given(
    parsers.re(
        r"^che l'ultimo ciclo concluso di \"(?P<flow>[^\"]+)\", alle (?P<time>\d\d:\d\d), ha deciso per "
        r"(?P<asset>\w+) \"apri (?P<direction>long|short)\" con confidenza (?P<confidence>\d+)$"
    )
)
def last_completed_cycle_decided(
    decisions: LastDecisions, *, flow: str, time: str, asset: str, direction: str, confidence: str
) -> None:
    decisions.decide(flow, "09:00", RecordedDecision(asset, DecisionAction.HOLD, None, 40, "attesa"))
    decisions.decide(flow, time, an_opening(asset, direction, int(confidence)))


@given(quoted('che il ciclo delle {time} di "{flow}" è fallito prima della decisione'))
def cycle_failed_before_deciding(decisions: LastDecisions, time: str, flow: str) -> None:
    # The cycle at 11:00 fails after the one at 10:00 decided, as the scenario says with "ancora".
    decisions.decide(flow, "10:00", an_opening("BTC", "long", 72))
    decisions.fail(flow, time, CycleStep.AGENT_DECISION)


@given(quoted('che il flusso "{flow}" non ha cicli conclusi'))
def flow_without_completed_cycles(decisions: LastDecisions, flow: str) -> None:
    # A cycle failed after the agent decided is not a completed cycle: its decisions are not the last decision.
    decisions.fail(flow, "10:00", CycleStep.RISK_CHECK, an_opening("BTC", "long", 72))


# When


@when(quoted('"{user}" apre la Panoramica del flusso "{flow}"'))
def open_overview(decisions: LastDecisions, user: str, flow: str) -> None:
    decisions.open_overview(user, flow)


@when(quoted('"{user}" sceglie il periodo "{period}" nella Panoramica del flusso "{flow}"'))
def choose_period_on_overview(decisions: LastDecisions, user: str, period: str, flow: str) -> None:
    # The last decision is read without the period: the API of the panel takes none (R6.5.4).
    assert period
    decisions.open_overview(user, flow)


@when(quoted('"{user}" chiede l\'ultima decisione del flusso "{flow}" all\'interfaccia programmatica'))
def ask_the_api(decisions: LastDecisions, user: str, flow: str) -> None:
    flow_id = decisions.flow(flow).id.value
    response = ApiSession(decisions.platform).get_as(user, f"/flows/{flow_id}/decisions/latest")
    assert response.status_code == 200
    decisions.answered = response.json()


# Then


@then(
    parsers.re(
        r"^vede l'ultima decisione delle (?P<time>\d\d:\d\d) con (?P<asset>\w+), \"(?P<action>[^\"]+)\", "
        r"\"(?P<direction>[^\"]+)\", confidenza (?P<confidence>\d+) e il ragionamento accorciato$"
    )
)
def last_decision_shown(
    decisions: LastDecisions, *, time: str, asset: str, action: str, direction: str, confidence: str
) -> None:
    shown = decisions.shown()
    assert shown.planned_at == at(time)
    assert [decision.asset for decision in shown.decisions] == [asset]
    decision = shown.decisions[0]
    assert decision.action.value == action
    assert decision.direction is not None
    assert decision.direction.value == direction
    assert decision.confidence == int(confidence)
    # The API gives the whole reasoning: the dashboard shortens it, the detail of the cycle shows it all.
    assert decision.reasoning == REASONING


@then(quoted("un collegamento al dettaglio del ciclo delle {time}"))
def link_to_cycle_detail(decisions: LastDecisions, time: str) -> None:
    shown = decisions.shown()
    flow_id = decisions.flow(decisions.opened_flow).id.value
    detail = decisions.platform.use_cases_of(decisions.opened_by).read_cycle.execute(
        ReadCycleCommand(flow_id, shown.planned_at)
    )
    assert detail.planned_at == at(time)


@then(quoted('il riquadro avvisa "{note}" e mostra la decisione delle {time}'))
def decision_whatever_the_period(decisions: LastDecisions, note: str, time: str) -> None:
    # The dashboard writes the note above the decision the API answers whatever the period.
    assert note == "indipendente dal periodo"
    assert decisions.shown().planned_at == at(time)


@then(
    parsers.re(
        r"^la risposta ha la decisione delle (?P<time>\d\d:\d\d) per (?P<asset>\w+) \"(?P<action>[^\"]+)\" "
        r"\"(?P<direction>[^\"]+)\" con confidenza (?P<confidence>\d+)$"
    )
)
def api_answers_decision(
    decisions: LastDecisions, *, time: str, asset: str, action: str, direction: str, confidence: str
) -> None:
    answered = decisions.answered
    assert answered["planned_at"] == at(time).isoformat().replace("+00:00", "Z")
    assert answered["decisions"] == [
        {
            "asset": asset,
            "action": action,
            "direction": direction,
            "confidence": int(confidence),
            "reasoning": REASONING,
        }
    ]


@then(quoted("vede ancora la decisione del ciclo delle {time}"))
def decision_still_shown(decisions: LastDecisions, time: str) -> None:
    assert decisions.shown().planned_at == at(time)


@then(quoted('il riquadro dice "{text}"'))
def no_decision(decisions: LastDecisions, text: str) -> None:
    # The dashboard writes the text when the API answers no decision.
    assert text == "nessuna decisione ancora"
    assert decisions.seen is None
