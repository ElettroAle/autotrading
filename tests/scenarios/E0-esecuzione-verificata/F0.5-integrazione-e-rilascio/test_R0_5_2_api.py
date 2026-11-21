from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support.git_repository import commit, new_repository
from tools.release_version import Repository, next_prerelease

scenarios(
    "E0-esecuzione-verificata/F0.5-integrazione-e-rilascio/R0.5.2-pubblicazione-e-rilascio-in-dev/api/R0.5.2-pubblicazione-e-rilascio-in-dev.feature"
)


@pytest.fixture
def publication() -> dict[str, str]:
    return {}


@given("che non esiste alcun rilascio in prod", target_fixture="repository")
def repository_without_releases(tmp_path: Path) -> Repository:
    repository = new_repository(tmp_path)
    assert repository.last_release_tag() is None
    return repository


@given(parsers.parse('che il ramo principale contiene solo commit "{kind}"'))
def only_commits_of_kind(repository: Repository, kind: str) -> None:
    commit(repository, f"{kind} first correction")
    commit(repository, f"{kind} second correction")


@when(parsers.parse("una pull request viene integrata nel ramo principale nell'esecuzione numero {run:d}"))
def pull_request_integrated(repository: Repository, publication: dict[str, str], run: int) -> None:
    publication["version"] = next_prerelease(repository, run)


@then(parsers.parse('la versione dell\'artefatto è "{version}"'))
def artifact_version(publication: dict[str, str], version: str) -> None:
    assert publication["version"] == version
