"""R1.4.9: a temporary error of the provider is asked again in the cycle, after 2, 8 and 30 seconds, and the cycle
records how many attempts the decision took (ADR tentativi-del-modello-registrati-nel-ciclo).
"""

from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.agent.errors import ModelCreditExhaustedError, ModelUnavailableError
from autotrading.domain.agent.model_usage import ModelUsage
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow_status import FlowStatus
from tests.support.flow_cycles import FlowCycles
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.4-agente-ia/R1.4.9-nuovi-tentativi-del-modello.feature")

OPENROUTER = ProviderName("openrouter")
DECISION = (
    '{"decisioni": [{"asset": "BTC", "azione": "mantieni", "direzione": null, "quota": null, "leva": null,'
    ' "obiettivo": null, "stop": null, "invalidazione": null, "confidenza": 60, "ragionamento": "attesa"}]}'
)


@pytest.fixture
def flow_cycles() -> FlowCycles:
    return FlowCycles()


def amount(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


def temporary(status: str, usage: ModelUsage | None = None) -> ModelUnavailableError:
    """What the adapters of the providers raise for a status that may not repeat: a call that went out."""
    return ModelUnavailableError(OPENROUTER, f"{status} Provider returned error", usage=usage, sent=True)


def last(flow_cycles: FlowCycles) -> CycleRecord:
    return flow_cycles.last_record("alfa")


@given(quoted('che "{user}" ha il flusso attivo "{flow}"'))
def active_flow(flow_cycles: FlowCycles, user: str, flow: str) -> None:
    flow_cycles.add_flow(user, flow)
    flow_cycles.model.text = DECISION


@given(
    parsers.re(
        r"^che il fornitore IA risponde (?P<status>\d+) alla prima chiamata e una decisione valida alla seconda$"
    )
)
def temporary_then_decision(flow_cycles: FlowCycles, status: str) -> None:
    flow_cycles.model.first_failures.append(temporary(status))


@given(parsers.re(r"^che il fornitore IA risponde (?P<status>\d+) a tutte le chiamate$"))
def temporary_always(flow_cycles: FlowCycles, status: str) -> None:
    flow_cycles.model.failure = temporary(status)


@given("che il fornitore IA risponde 402 credito esaurito")
def credit_exhausted(flow_cycles: FlowCycles) -> None:
    flow_cycles.model.failure = ModelCreditExhaustedError(OPENROUTER)


@given(
    parsers.re(
        r"^che il primo tentativo ha risposto (?P<status>\d+) con un costo di (?P<first>[\d,]+) USD e il secondo "
        r"una decisione con (?P<second>[\d,]+) USD$"
    )
)
def priced_attempts(flow_cycles: FlowCycles, status: str, first: str, second: str) -> None:
    flow_cycles.model.first_failures.append(temporary(status, ModelUsage(100, 0, amount(first))))
    flow_cycles.model.usage = ModelUsage(1000, 200, amount(second))


@when(quoted('parte il ciclo di "{flow}"'))
def cycle_starts(flow_cycles: FlowCycles, flow: str) -> None:
    flow_cycles.run(flow)


@when(quoted('il ciclo di "{flow}" si conclude'))
def cycle_ends(flow_cycles: FlowCycles, flow: str) -> None:
    flow_cycles.run(flow)
    assert flow_cycles.last_record(flow).outcome is CycleOutcome.COMPLETED


@then(parsers.re(r"^la chiamata è ritentata dopo (?P<seconds>\d+) secondi$"))
def asked_again_once(flow_cycles: FlowCycles, seconds: str) -> None:
    assert len(flow_cycles.model.calls) == 2
    assert flow_cycles.pause.pauses == [float(seconds)]


@then(parsers.re(r"^la chiamata è ritentata (?P<count>\d+) volte, dopo (?P<pauses>.+) secondi$"))
def asked_again(flow_cycles: FlowCycles, count: str, pauses: str) -> None:
    waited = [float(each) for each in pauses.replace(" e ", ", ").split(", ")]
    assert len(flow_cycles.model.calls) == int(count) + 1
    assert flow_cycles.pause.pauses == waited


@then("la chiamata non è ritentata")
def never_asked_again(flow_cycles: FlowCycles) -> None:
    assert len(flow_cycles.model.calls) == 1
    assert flow_cycles.pause.pauses == []


@then("il ciclo prosegue con la decisione")
def goes_on_with_decision(flow_cycles: FlowCycles) -> None:
    record = last(flow_cycles)
    assert record.outcome is CycleOutcome.COMPLETED
    assert CycleStep.RISK_CHECK in record.steps
    assert [decision.asset for decision in record.decisions] == ["BTC"]


@then(parsers.re(r"^il ciclo registra (?P<count>\d+) tentativi$"))
def records_attempts(flow_cycles: FlowCycles, count: str) -> None:
    assert last(flow_cycles).model_attempts == int(count)


@then("il ciclo fallisce nel passo dell'agente con il motivo dell'errore, come in R1.2.3")
def fails_in_agent_step(flow_cycles: FlowCycles) -> None:
    record = last(flow_cycles)
    assert record.outcome is CycleOutcome.FAILED
    assert record.failure is not None
    assert record.failure.step is CycleStep.AGENT_DECISION
    assert record.failure.message == "fornitore IA non raggiungibile: openrouter: 429 Provider returned error"
    assert flow_cycles.flow("alfa").status is FlowStatus.ACTIVE


@then("il ciclo fallisce e il flusso va in pausa come in R1.2.4")
def fails_and_pauses(flow_cycles: FlowCycles) -> None:
    record = last(flow_cycles)
    assert record.outcome is CycleOutcome.FAILED
    paused = flow_cycles.flow("alfa")
    assert paused.status is FlowStatus.PAUSED
    assert flow_cycles.platform.flows.pause_reasons[paused.id] == "credito esaurito presso openrouter"


@then(quoted("il costo del ciclo è {cost} USD"))
def cycle_cost(flow_cycles: FlowCycles, cost: str) -> None:
    call = last(flow_cycles).cost
    assert call is not None
    assert call.cost_usd == amount(cost)
