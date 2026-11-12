import json
import logging

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.agent.register_provider_key import RegisterProviderKeyCommand
from autotrading.application.agent.remove_provider_key import RemoveProviderKeyCommand
from autotrading.application.agent.replace_provider_key import ReplaceProviderKeyCommand
from autotrading.domain.errors import AutotradingError
from tests.support.flow_cycles import FlowCycles
from tests.support.flow_steps import *  # noqa: F403 - the steps of flow creation, shared by the features
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.4-agente-ia/R1.4.1-chiavi-dei-fornitori-ia.feature")


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def platform(flow_cycles: FlowCycles) -> Platform:
    return flow_cycles.platform


@pytest.fixture
def outcome() -> dict[str, object]:
    return {}


@given(quoted('che "{user}" non ha chiavi di fornitori IA registrate'))
def no_keys(platform: Platform, user: str) -> None:
    assert platform.use_cases_of(user).list_provider_keys.execute() == []


@given(quoted('che il fornitore "{provider}" accetta la chiave "{key}"'))
def provider_accepts(platform: Platform, provider: str, key: str) -> None:
    platform.providers.accept(provider, key)


@given(quoted('che il fornitore "{provider}" rifiuta la chiave "{key}"'))
def provider_refuses(platform: Platform, provider: str, key: str) -> None:
    platform.providers.refuse(provider, key)


@when(quoted('"{user}" registra la chiave "{key}" per il fornitore "{provider}"'))
def register_key(platform: Platform, user: str, key: str, provider: str, outcome: dict[str, object]) -> None:
    command = RegisterProviderKeyCommand(provider, key)
    try:
        outcome["answer"] = platform.use_cases_of(user).register_provider_key.execute(command)
    except AutotradingError as error:
        outcome["error"] = error


@then(quoted('"{user}" ha una chiave registrata per il fornitore "{provider}"'))
def key_registered(platform: Platform, user: str, provider: str) -> None:
    assert [name.value for name in platform.use_cases_of(user).list_provider_keys.execute()] == [provider]


@then(quoted('"{user}" non ha chiavi registrate per il fornitore "{provider}"'))
def key_not_registered(platform: Platform, user: str, provider: str) -> None:
    assert provider not in [name.value for name in platform.use_cases_of(user).list_provider_keys.execute()]


@then(quoted('la chiave "{key}" non compare nella risposta'))
def key_not_in_answer(outcome: dict[str, object], key: str) -> None:
    answer = outcome["answer"]
    assert key not in repr(answer)
    assert key not in str(answer)


@then(quoted('la registrazione è rifiutata con il motivo "{reason}"'))
def registration_refused(outcome: dict[str, object], reason: str) -> None:
    assert "answer" not in outcome
    assert str(outcome["error"]) == reason


@given(quoted('che "{user}" ha registrato la chiave "{key}" per il fornitore "{provider}"'))
def key_registered_before(platform: Platform, user: str, key: str, provider: str) -> None:
    platform.providers.accept(provider, key)
    platform.use_cases_of(user).register_provider_key.execute(RegisterProviderKeyCommand(provider, key))


@given(quoted('che "{user}" ha il flusso "{name}" attivo con modello "{model}"'))
def active_flow_with_model(flow_cycles: FlowCycles, user: str, name: str, model: str) -> None:
    flow_cycles.add_flow(user, name, model=model)


@when(quoted('"{user}" sostituisce la chiave del fornitore "{provider}" con "{key}"'))
def replace_key(platform: Platform, user: str, provider: str, key: str) -> None:
    platform.use_cases_of(user).replace_provider_key.execute(ReplaceProviderKeyCommand(provider, key))


@when(quoted('"{user}" rimuove la chiave del fornitore "{provider}"'))
def remove_key(platform: Platform, user: str, provider: str, outcome: dict[str, object]) -> None:
    try:
        platform.use_cases_of(user).remove_provider_key.execute(RemoveProviderKeyCommand(provider))
    except AutotradingError as error:
        outcome["error"] = error


@when(quoted('il flusso "{name}" di "{user}" esegue un ciclo'))
def flow_runs_cycle(flow_cycles: FlowCycles, caplog: pytest.LogCaptureFixture, name: str, user: str) -> None:
    flow_cycles.add_flow(user, name)
    with caplog.at_level(logging.DEBUG):
        flow_cycles.run(name)


@then(quoted('i cicli successivi dei flussi di "{user}" usano la chiave "{key}" presso "{provider}"'))
def cycles_use_key(flow_cycles: FlowCycles, user: str, key: str, provider: str) -> None:
    flow_cycles.add_flow(user, "alfa", model=f"{provider}/deepseek-chat")
    flow_cycles.run("alfa")
    call = flow_cycles.model.calls[-1]
    assert (call.model.partition("/")[0], call.key.secret) == (provider, key)


@then(quoted('la rimozione è rifiutata con il motivo "{reason}"'))
def removal_refused(outcome: dict[str, object], reason: str) -> None:
    assert str(outcome["error"]) == reason


@then(quoted('la chiave "{key}" non compare nel contesto inviato all\'agente'))
def key_not_in_context(flow_cycles: FlowCycles, key: str) -> None:
    [call] = flow_cycles.model.calls
    assert call.key.secret == key
    assert all(key not in message.content for message in call.messages)


@then(quoted('la chiave "{key}" non compare nei log'))
def key_not_in_logs(caplog: pytest.LogCaptureFixture, key: str) -> None:
    assert caplog.records
    assert all(key not in record.getMessage() and key not in repr(record.__dict__) for record in caplog.records)


@then(quoted('la chiave "{key}" non compare nel ciclo registrato'))
def key_not_in_record(flow_cycles: FlowCycles, key: str) -> None:
    record = flow_cycles.last_record("alfa")
    documents = json.dumps([document.content for document in record.documents], default=str)
    assert key not in documents
    assert key not in repr(record)
