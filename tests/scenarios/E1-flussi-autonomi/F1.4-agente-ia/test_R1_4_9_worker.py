"""R1.4.9: a temporary error of the provider is asked again in the cycle, after 2, 8 and 30 seconds, and the cycle
records how many attempts the decision took (ADR tentativi-del-modello-registrati-nel-ciclo); an answer the model cuts
at the token limit of the flow is one of them, with its own reason (Bug 733, ADR
risposta-del-modello-interrotta-dal-limite-di-token).
"""

from dataclasses import replace
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.agent.errors import (
    ModelAnswerTruncatedError,
    ModelCreditExhaustedError,
    ModelUnavailableError,
)
from autotrading.domain.agent.model_usage import ModelUsage
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_status import FlowStatus
from tests.support.flow_cycles import FlowCycles
from tests.support.steps import quoted

scenarios(
    "E1-flussi-autonomi/F1.4-agente-ia/R1.4.9-nuovi-tentativi-del-modello/worker/R1.4.9-nuovi-tentativi-del-modello.feature"
)

OPENROUTER = ProviderName("openrouter")
DECISION = (
    '{"decisioni": [{"asset": "BTC", "azione": "mantieni", "direzione": null, "quota": null, "leva": null,'
    ' "obiettivo": null, "stop": null, "invalidazione": null, "confidenza": 60, "ragionamento": "attesa"}]}'
)

CUT_COST = Decimal("0.002")
DEFAULT_MAX_TOKENS = 4096


@pytest.fixture
def flow_cycles() -> FlowCycles:
    return FlowCycles()


def amount(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


def temporary(status: str, usage: ModelUsage | None = None) -> ModelUnavailableError:
    """What the adapters of the providers raise for a status that may not repeat: a call that went out."""
    return ModelUnavailableError(OPENROUTER, f"{status} Provider returned error", usage=usage, sent=True)


def truncated(max_tokens: int) -> ModelAnswerTruncatedError:
    """What the adapters of the providers raise for an answer cut at the token limit: a call that went out, charged
    for every token of the limit.
    """
    return ModelAnswerTruncatedError(OPENROUTER, max_tokens, usage=ModelUsage(2000, max_tokens, CUT_COST), sent=True)


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


@given(parsers.re(r'^un flusso "(?P<flow>[^"]+)" con max_tokens (?P<limit>\d+)$'))
def flow_with_token_limit(flow_cycles: FlowCycles, flow: str, limit: str) -> None:
    def limited(configuration: FlowConfiguration) -> FlowConfiguration:
        model = configuration.model
        return replace(
            configuration, model=replace(model, parameters={**model.parameters, "max_tokens": Decimal(limit)})
        )

    flow_cycles.reconfigure(flow, limited)


@given(parsers.re(r"^che il modello esaurisce i (?P<limit>\d+) token prima di finire la risposta in ogni tentativo$"))
def cut_in_every_attempt(flow_cycles: FlowCycles, limit: str) -> None:
    flow_cycles.model.failure = truncated(int(limit))


@given("che il modello esaurisce i token solo al primo tentativo")
def cut_at_first_attempt(flow_cycles: FlowCycles) -> None:
    flow_cycles.model.first_failures.append(truncated(DEFAULT_MAX_TOKENS))


@when(quoted('parte un ciclo di "{flow}"'))
def a_cycle_starts(flow_cycles: FlowCycles, flow: str) -> None:
    flow_cycles.run(flow)


@then(quoted('il ciclo fallisce con il motivo "{reason}"'))
def fails_with_reason(flow_cycles: FlowCycles, reason: str) -> None:
    record = last(flow_cycles)
    assert record.outcome is CycleOutcome.FAILED
    assert record.failure is not None
    assert record.failure.step is CycleStep.AGENT_DECISION
    assert record.failure.message == reason
    assert flow_cycles.flow("alfa").status is FlowStatus.ACTIVE


@then(quoted('il motivo non dice "{words}"'))
def reason_without(flow_cycles: FlowCycles, words: str) -> None:
    failure = last(flow_cycles).failure
    assert failure is not None
    assert words not in failure.message


@then("il ciclo registra il costo e i tentativi delle chiamate interrotte")
def records_cut_calls(flow_cycles: FlowCycles) -> None:
    record = last(flow_cycles)
    attempts = len(flow_cycles.model.calls)
    assert attempts == 4
    assert record.model_attempts == attempts
    assert record.cost is not None
    assert record.cost.output_tokens == attempts * DEFAULT_MAX_TOKENS
    assert record.cost.cost_usd == attempts * CUT_COST


@then(parsers.re(r"^il ciclo è concluso con (?P<count>\d+) tentativi del modello$"))
def completed_after_attempts(flow_cycles: FlowCycles, count: str) -> None:
    record = last(flow_cycles)
    assert record.outcome is CycleOutcome.COMPLETED
    assert record.model_attempts == int(count)
    assert len(flow_cycles.model.calls) == int(count)
