from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support.git_repository import commit, new_repository, tag
from tools.release_version import NonConformingCommitsError, Repository, tag_release

scenarios("E0-esecuzione-verificata/F0.5-integrazione-e-rilascio/R0.5.3-promozione-in-prod.feature")


@pytest.fixture
def promotion() -> dict[str, object]:
    return {}


@given(parsers.parse('che l\'ultimo rilascio in prod è la versione "{version}"'), target_fixture="repository")
def released_repository(tmp_path: Path, version: str, promotion: dict[str, object]) -> Repository:
    repository = new_repository(tmp_path)
    tag(repository, f"v{version}")
    promotion["prod"] = version
    return repository


@given(
    parsers.parse("che l'installazione dev esegue l'artefatto \"{artifact}\" e ne ha superato il controllo di salute")
)
def dev_runs_artifact(promotion: dict[str, object], artifact: str) -> None:
    promotion["dev"] = artifact


@given(parsers.parse('che dopo il rilascio "{version}" il ramo principale contiene i commit "{messages}"'))
def commits_after_release(repository: Repository, version: str, messages: str) -> None:
    assert repository.last_release_tag() == f"v{version}"
    for message in messages.split(", "):
        commit(repository, message)


@given(parsers.parse('che dopo il rilascio "{version}" il ramo principale contiene un commit "{message}"'))
def one_commit_after_release(repository: Repository, version: str, message: str) -> None:
    assert repository.last_release_tag() == f"v{version}"
    commit(repository, message)


@when("il proprietario approva la promozione")
def approve_promotion(repository: Repository, promotion: dict[str, object]) -> None:
    try:
        promotion["prod"] = tag_release(repository)
    except NonConformingCommitsError as error:
        promotion["error"] = error


@then(parsers.parse('il nuovo rilascio è "{tag_name}"'))
def new_release_is(repository: Repository, tag_name: str) -> None:
    assert repository.last_release_tag() == tag_name


@then("la promozione fallisce indicando il commit non conforme ai Conventional Commits")
def promotion_fails(promotion: dict[str, object]) -> None:
    error = promotion.get("error")
    assert isinstance(error, NonConformingCommitsError), f"la promozione non è fallita: prod {promotion['prod']}"
    assert error.messages == ["aggiornato tutto"]


@then(parsers.parse('l\'installazione prod resta sulla versione "{version}"'))
def prod_unchanged(repository: Repository, promotion: dict[str, object], version: str) -> None:
    assert promotion["prod"] == version
    assert repository.last_release_tag() == f"v{version}"
