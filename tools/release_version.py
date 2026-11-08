import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from tools.errors import PipelineError

UNCONVENTIONAL_GROUP = "Altre modifiche"


class GitCommandError(PipelineError):
    def __init__(self, command: list[str], detail: str) -> None:
        super().__init__(f"comando fallito: {' '.join(command)}: {detail}")


class NonConformingCommitsError(PipelineError):
    def __init__(self, messages: list[str]) -> None:
        listed = "; ".join(messages)
        super().__init__(f"commit non conformi ai Conventional Commits: {listed}")
        self.messages = messages


# The title check builds a throwaway commit; CI runners have no git identity configured.
DETACHED_IDENTITY = ("-c", "user.name=title-check", "-c", "user.email=title-check@localhost")


@dataclass(frozen=True, slots=True)
class Repository:
    path: Path

    def run(self, *command: str) -> str:
        completed = subprocess.run(command, cwd=self.path, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise GitCommandError(list(command), completed.stderr.strip())
        return completed.stdout.strip()

    def last_release_tag(self) -> str | None:
        tags = self.run("git", "tag", "--list", "--merged", "HEAD", "--sort=-v:refname", "v*.*.*")
        return tags.splitlines()[0] if tags else None

    def cliff(self, *arguments: str) -> str:
        return self.run("git-cliff", "--config", str(self.path / "cliff.toml"), *arguments)


def is_conventional_title(repository: Repository, title: str) -> bool:
    detached = repository.run("git", *DETACHED_IDENTITY, "commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m", title)
    return not _unconventional_messages(repository, f"{detached}^..{detached}")


def require_conforming_commits(repository: Repository) -> None:
    messages = _unconventional_messages(repository, _range_since_last_release(repository))
    if messages:
        raise NonConformingCommitsError(messages)


def tag_release(repository: Repository) -> str:
    require_conforming_commits(repository)
    version = next_release(repository)
    repository.run("git", "tag", f"v{version}")
    return version


def next_release(repository: Repository) -> str:
    return repository.cliff("--bumped-version").removeprefix("v")


def next_prerelease(repository: Repository, run_number: int) -> str:
    return f"{_version_after_last_release(repository)}-dev.{run_number}"


def _version_after_last_release(repository: Repository) -> str:
    candidate = next_release(repository)
    last_tag = repository.last_release_tag()
    if last_tag is None or candidate != last_tag.removeprefix("v"):
        return candidate
    major, minor, patch = (int(part) for part in candidate.split("."))
    return f"{major}.{minor}.{patch + 1}"


def _range_since_last_release(repository: Repository) -> str | None:
    last_tag = repository.last_release_tag()
    return None if last_tag is None else f"{last_tag}..HEAD"


def _unconventional_messages(repository: Repository, revision_range: str | None) -> list[str]:
    arguments = ("--context",) if revision_range is None else ("--context", revision_range)
    releases = json.loads(repository.cliff(*arguments))
    return [
        commit["message"].splitlines()[0]
        for release in releases
        for commit in release["commits"]
        if UNCONVENTIONAL_GROUP in commit["group"]
    ]


def main(arguments: list[str]) -> int:
    repository = Repository(Path.cwd())
    command, *rest = arguments
    if command == "title":
        return _report_title(repository, rest[0])
    if command == "prerelease":
        print(next_prerelease(repository, int(rest[0])))
        return 0
    print(tag_release(repository))
    return 0


def _report_title(repository: Repository, title: str) -> int:
    if is_conventional_title(repository, title):
        return 0
    print(f"titolo non conforme ai Conventional Commits: {title}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
