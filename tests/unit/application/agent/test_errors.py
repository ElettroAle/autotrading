"""The errors of the model call (ADR-uso-riportato-nell-errore-della-chiamata-al-modello)."""

from decimal import Decimal

from autotrading.application.agent.errors import ModelUnavailableError
from autotrading.domain.agent.model_usage import ModelPrices, ModelUsage
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
