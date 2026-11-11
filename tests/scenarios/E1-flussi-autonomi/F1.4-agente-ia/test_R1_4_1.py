import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.agent.register_provider_key import RegisterProviderKeyCommand
from autotrading.domain.errors import AutotradingError
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.4-agente-ia/R1.4.1-chiavi-dei-fornitori-ia.feature")


@pytest.fixture
def platform() -> Platform:
    return Platform()


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
