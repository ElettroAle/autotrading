"""The errors of the model call (ADR-uso-riportato-nell-errore-della-chiamata-al-modello)."""

from decimal import Decimal

from autotrading.application.agent.errors import ModelAnswerUnreadableError, ModelUnavailableError
from autotrading.domain.agent.model_usage import ModelPrices, ModelSpend, ModelUsage
from autotrading.domain.agent.provider_name import ProviderName

OPENROUTER = ProviderName("openrouter")
PRICES = ModelPrices(Decimal(1), Decimal(2))


def test_an_unavailable_provider_by_default_was_not_sent_and_reported_no_usage() -> None:
    error = ModelUnavailableError(OPENROUTER, "503")

    assert (error.usage, error.sent, error.cost_usd) == (None, False, None)


def test_an_unavailable_provider_keeps_the_usage_it_reported_for_a_sent_call() -> None:
    usage = ModelUsage(3000, 4000, Decimal("0.002"))

    error = ModelUnavailableError(OPENROUTER, "risposta del fornitore inattesa", usage=usage, sent=True)

    assert (error.usage, error.sent) == (usage, True)
    assert str(error) == "fornitore IA non raggiungibile: openrouter: risposta del fornitore inattesa"
    assert error.status_code == 503
    assert not error.permanent


def test_the_priced_error_carries_the_cost_the_catalog_gives_to_the_usage() -> None:
    error = ModelUnavailableError(OPENROUTER, "inattesa", usage=ModelUsage(1000, 1000, None), sent=True)

    priced = error.priced(PRICES)

    assert (priced.provider, priced.original, priced.usage, priced.sent) == (OPENROUTER, "inattesa", error.usage, True)
    assert priced.cost_usd == Decimal("0.003")


def test_the_priced_error_keeps_the_cost_the_provider_reported() -> None:
    error = ModelUnavailableError(OPENROUTER, "inattesa", usage=ModelUsage(1000, 1000, Decimal("0.002")), sent=True)

    assert error.priced(PRICES).cost_usd == Decimal("0.002")


def test_without_usage_the_priced_error_has_no_cost() -> None:
    error = ModelUnavailableError(OPENROUTER, "tempo di risposta scaduto", sent=True)

    priced = error.priced(PRICES)

    assert (priced.usage, priced.sent, priced.cost_usd) == (None, True, None)


def test_an_unreadable_answer_is_an_unavailable_provider_that_stays_unreadable_once_priced() -> None:
    error = ModelAnswerUnreadableError(OPENROUTER, "inattesa", usage=ModelUsage(1000, 1000, None), sent=True)

    priced = error.priced(PRICES)

    assert isinstance(priced, ModelAnswerUnreadableError)
    assert str(priced) == "fornitore IA non raggiungibile: openrouter: inattesa"
    assert not priced.permanent


def test_a_call_that_went_out_adds_its_usage_and_cost_to_what_was_spent() -> None:
    error = ModelUnavailableError(OPENROUTER, "502", usage=ModelUsage(100, 0, None), sent=True).priced(PRICES)

    spend = error.spent_after(ModelSpend().with_call(ModelUsage(100, 0, None), Decimal("0.0001")))

    assert spend == ModelSpend(ModelUsage(200, 0, None), Decimal("0.0002"), sent=True)


def test_a_call_that_never_went_out_spends_nothing() -> None:
    before = ModelSpend().with_call(ModelUsage(100, 0, None), Decimal("0.0001"))

    assert ModelUnavailableError(OPENROUTER, "ConnectError").spent_after(before) is before


def test_the_error_with_the_spend_carries_what_every_call_consumed_and_keeps_its_kind() -> None:
    spend = ModelSpend(ModelUsage(300, 0, None), Decimal("0.0003"), sent=True)
    error = ModelAnswerUnreadableError(OPENROUTER, "inattesa")

    spent = error.with_spend(spend)

    assert isinstance(spent, ModelAnswerUnreadableError)
    assert (spent.provider, spent.original) == (OPENROUTER, "inattesa")
    assert (spent.usage, spent.cost_usd, spent.sent) == (ModelUsage(300, 0, None), Decimal("0.0003"), True)
