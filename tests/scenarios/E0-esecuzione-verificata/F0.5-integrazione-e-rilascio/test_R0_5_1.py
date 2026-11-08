import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tools.coverage_gate import THRESHOLDS, Coverage, violations

scenarios(
    "E0-esecuzione-verificata/F0.5-integrazione-e-rilascio/R0.5.1-controlli-di-qualita-sulle-pull-request.feature"
)


def at_threshold() -> dict[str, Coverage]:
    return {scope: Coverage(int(threshold), 100) for scope, threshold in THRESHOLDS.items()}


@pytest.fixture
def scopes() -> dict[str, Coverage]:
    return at_threshold()


@pytest.fixture
def outcome() -> dict[str, list[str]]:
    return {}


@given(parsers.parse('che con la pull request la copertura degli unit test su "{scope}" è {percent:d}%'))
def coverage_of_one_scope(scopes: dict[str, Coverage], scope: str, percent: int) -> None:
    scopes[scope] = Coverage(percent, 100)


@given("che con la pull request la copertura è 90% su domain, 90% su application e 80% sul totale")
def coverage_at_thresholds(scopes: dict[str, Coverage]) -> None:
    scopes.update(at_threshold())


@when("i controlli di qualità vengono eseguiti")
def run_quality_checks(scopes: dict[str, Coverage], outcome: dict[str, list[str]]) -> None:
    outcome["copertura del codice"] = violations(scopes)


@then(parsers.parse('il controllo "copertura del codice" fallisce indicando la soglia {threshold:d}% per "{scope}"'))
def coverage_check_fails(outcome: dict[str, list[str]], threshold: int, scope: str) -> None:
    assert any(
        f"copertura {scope} " in problem and f"soglia {threshold}%" in problem
        for problem in outcome["copertura del codice"]
    )


@then('il controllo "copertura del codice" è superato')
def coverage_check_passes(outcome: dict[str, list[str]]) -> None:
    assert outcome["copertura del codice"] == []
