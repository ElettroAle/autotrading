import os
import shutil
from pathlib import Path

from tools.release_version import Repository

PROJECT_ROOT = Path(__file__).resolve().parents[2]
IDENTITY = {
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
}


def use_test_identity() -> None:
    os.environ.update(IDENTITY)


def new_repository(path: Path) -> Repository:
    use_test_identity()
    shutil.copy(PROJECT_ROOT / "cliff.toml", path / "cliff.toml")
    repository = Repository(path)
    repository.run("git", "init", "--quiet")
    repository.run("git", "add", "cliff.toml")
    repository.run("git", "commit", "--quiet", "--message", "chore: initial commit")
    return repository


def commit(repository: Repository, message: str) -> None:
    repository.run("git", "commit", "--quiet", "--allow-empty", "--message", message)


def tag(repository: Repository, name: str) -> None:
    repository.run("git", "tag", name)
