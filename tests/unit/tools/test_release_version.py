from pathlib import Path

import pytest

from tests.support.git_repository import IDENTITY, commit, new_repository, tag
from tools.release_version import (
    GitCommandError,
    NonConformingCommitsError,
    Repository,
    is_conventional_title,
    main,
    next_prerelease,
    next_release,
    require_conforming_commits,
    tag_release,
)


@pytest.fixture
def released(tmp_path: Path) -> Repository:
    repository = new_repository(tmp_path)
    tag(repository, "v1.2.0")
    return repository


@pytest.mark.parametrize("title", ["feat: add health", "fix(api): typo", "feat(api)!: drop v1", "ci: pin actions"])
def test_accepts_conventional_titles(released: Repository, title: str) -> None:
    assert is_conventional_title(released, title)


def test_checks_title_without_a_configured_git_identity(
    released: Repository, tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in IDENTITY:
        monkeypatch.delenv(name, raising=False)
    global_config = tmp_path_factory.mktemp("home") / "gitconfig"
    global_config.write_text("[user]\n\tuseConfigOnly = true\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")

    assert is_conventional_title(released, "feat: add health")


@pytest.mark.parametrize("title", ["aggiornato tutto", "Feature: health", "wip"])
def test_rejects_unconventional_titles(released: Repository, title: str) -> None:
    assert not is_conventional_title(released, title)


def test_next_release_without_previous_tags_starts_from_initial_version(tmp_path: Path) -> None:
    repository = new_repository(tmp_path)
    commit(repository, "feat: first capability")

    assert next_release(repository) == "0.1.0"


def test_prerelease_carries_the_run_number(released: Repository) -> None:
    commit(released, "fix: a")

    assert next_prerelease(released, 57) == "1.2.1-dev.57"


def test_prerelease_never_reuses_an_existing_release(released: Repository) -> None:
    assert next_prerelease(released, 3) == "1.2.1-dev.3"


def test_conforming_commits_pass_verification(released: Repository) -> None:
    commit(released, "fix: a")

    require_conforming_commits(released)


def test_verification_lists_every_nonconforming_commit(released: Repository) -> None:
    commit(released, "aggiornato tutto")
    commit(released, "fix: a")
    commit(released, "ancora")

    with pytest.raises(NonConformingCommitsError) as raised:
        require_conforming_commits(released)

    assert sorted(raised.value.messages) == ["aggiornato tutto", "ancora"]


def test_verification_without_releases_checks_the_whole_history(tmp_path: Path) -> None:
    repository = new_repository(tmp_path)
    commit(repository, "random")

    with pytest.raises(NonConformingCommitsError):
        require_conforming_commits(repository)


def test_failing_git_command_raises_typed_error(tmp_path: Path) -> None:
    with pytest.raises(GitCommandError):
        Repository(tmp_path).run("git", "rev-parse", "HEAD")


def test_main_title_returns_failure_for_unconventional_title(
    released: Repository, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(released.path)

    assert main(["title", "aggiornato tutto"]) == 1
    assert "titolo non conforme" in capsys.readouterr().err


def test_main_title_returns_success_for_conventional_title(
    released: Repository, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(released.path)

    assert main(["title", "feat: x"]) == 0


def test_tag_release_creates_the_version_tag(released: Repository) -> None:
    commit(released, "feat: b")

    assert tag_release(released) == "1.3.0"
    assert released.last_release_tag() == "v1.3.0"


def test_tag_release_with_nonconforming_commits_creates_no_tag(released: Repository) -> None:
    commit(released, "random")

    with pytest.raises(NonConformingCommitsError):
        tag_release(released)

    assert released.last_release_tag() == "v1.2.0"


def test_main_prints_prerelease_and_tags_release(
    released: Repository, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    commit(released, "feat: b")
    monkeypatch.chdir(released.path)

    main(["prerelease", "9"])
    main(["release"])

    assert capsys.readouterr().out.split() == ["1.3.0-dev.9", "1.3.0"]
    assert released.last_release_tag() == "v1.3.0"
