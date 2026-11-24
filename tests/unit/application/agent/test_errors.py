"""The errors of the model call (ADR-uso-riportato-nell-errore-della-chiamata-al-modello)."""

from decimal import Decimal

from autotrading.application.agent.errors import ModelAnswerTruncatedError, ModelUnavailableError
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


def test_a_call_that_went_out_adds_its_usage_and_cost_to_what_was_spent() -> None:
    error = ModelUnavailableError(OPENROUTER, "502", usage=ModelUsage(100, 0, None), sent=True).priced(PRICES)

    spend = error.spent_after(ModelSpend().with_call(ModelUsage(100, 0, None), Decimal("0.0001")))

    assert spend == ModelSpend(ModelUsage(200, 0, None), Decimal("0.0002"), sent=True, attempts=2)


def test_a_call_that_never_went_out_spends_nothing_and_counts_as_an_attempt() -> None:
    before = ModelSpend().with_call(ModelUsage(100, 0, None), Decimal("0.0001"))

    spend = ModelUnavailableError(OPENROUTER, "ConnectError").spent_after(before)

    assert spend == ModelSpend(ModelUsage(100, 0, None), Decimal("0.0001"), sent=True, attempts=2)


def test_the_error_with_the_spend_carries_what_every_call_consumed() -> None:
    spend = ModelSpend(ModelUsage(300, 0, None), Decimal("0.0003"), sent=True, attempts=3)
    error = ModelUnavailableError(OPENROUTER, "inattesa")

    spent = error.with_spend(spend)

    assert (spent.provider, spent.original) == (OPENROUTER, "inattesa")
    assert (spent.usage, spent.cost_usd, spent.sent) == (ModelUsage(300, 0, None), Decimal("0.0003"), True)
    assert spent.attempts == 3


# ADR-tentativi-del-modello-registrati-nel-ciclo: the error says how many calls the question tried.
def test_an_error_of_one_call_is_one_attempt() -> None:
    assert ModelUnavailableError(OPENROUTER, "503").attempts == 1


def test_the_priced_error_keeps_its_attempts() -> None:
    error = ModelUnavailableError(OPENROUTER, "503", usage=ModelUsage(1, 1, None), sent=True, attempts=4)

    assert error.priced(PRICES).attempts == 4


# ADR-risposta-del-modello-interrotta-dal-limite-di-token: an answer cut at the token limit says so and how to fix it.
CUT_REASON = (
    "risposta del modello interrotta dal limite di 4096 token: alza max_tokens o abbassa il ragionamento del flusso"
)


def test_an_answer_cut_at_the_token_limit_names_the_limit_and_the_remedy() -> None:
    error = ModelAnswerTruncatedError(OPENROUTER, 4096, usage=ModelUsage(2000, 4096, None), sent=True)

    assert str(error) == CUT_REASON
    assert "fornitore IA non raggiungibile" not in str(error)
    assert (error.provider, error.max_tokens, error.original) == (OPENROUTER, 4096, CUT_REASON)
    assert (error.usage, error.sent, error.attempts) == (ModelUsage(2000, 4096, None), True, 1)


def test_an_answer_cut_at_the_token_limit_is_a_temporary_unavailable_model() -> None:
    error = ModelAnswerTruncatedError(OPENROUTER, 4096, sent=True)

    assert isinstance(error, ModelUnavailableError)
    assert error.status_code == 503
    assert not error.permanent


def test_the_priced_cut_answer_keeps_its_class_and_its_limit() -> None:
    error = ModelAnswerTruncatedError(OPENROUTER, 2048, usage=ModelUsage(1000, 1000, None), sent=True, attempts=2)

    priced = error.priced(PRICES)

    assert isinstance(priced, ModelAnswerTruncatedError)
    assert priced.max_tokens == 2048
    assert str(priced) == str(error)
    assert (priced.usage, priced.sent, priced.cost_usd, priced.attempts) == (error.usage, True, Decimal("0.003"), 2)


def test_the_cut_answer_with_the_spend_keeps_its_class_and_its_limit() -> None:
    spend = ModelSpend(ModelUsage(4000, 16384, None), Decimal("0.008"), sent=True, attempts=4)

    spent = ModelAnswerTruncatedError(OPENROUTER, 4096, sent=True).with_spend(spend)

    assert isinstance(spent, ModelAnswerTruncatedError)
    assert (spent.max_tokens, str(spent)) == (4096, CUT_REASON)
    assert (spent.usage, spent.cost_usd, spent.sent, spent.attempts) == (spend.usage, Decimal("0.008"), True, 4)
