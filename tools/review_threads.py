import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from tools.errors import PipelineError

# The review writes its threads with the job token: their first comment is always of this author (ADR 0113).
REVIEW_AUTHOR = "github-actions"
MARKER = "<!-- revisione-ai -->"


class UnreadableReviewThreadsError(PipelineError):
    def __init__(self) -> None:
        super().__init__("la risposta di GitHub non contiene i thread di review della pull request")


@dataclass(frozen=True, slots=True)
class OpenThread:
    path: str
    line: int | None
    rule: str

    def describe(self) -> str:
        place = self.path if self.line is None else f"{self.path}:{self.line}"
        return f"{place}: {self.rule}"


def open_review_threads(answer: Mapping[str, object]) -> list[OpenThread]:
    """The threads of the AI review still open, from the reviewThreads of a GraphQL answer (Bug 298)."""
    return [
        OpenThread(str(node.get("path", "")), _line_of(node), _rule_of(_first_comment(node)))
        for node in _thread_nodes(answer)
        if not node.get("isResolved") and _author_of(_first_comment(node)) == REVIEW_AUTHOR
    ]


def _thread_nodes(answer: Mapping[str, object]) -> list[Mapping[str, object]]:
    nodes = _walk(answer, ("data", "repository", "pullRequest", "reviewThreads", "nodes"))
    if not isinstance(nodes, Sequence):
        raise UnreadableReviewThreadsError
    return [node for node in nodes if isinstance(node, Mapping)]


def _walk(value: object, keys: tuple[str, ...]) -> object:
    for key in keys:
        if not isinstance(value, Mapping):
            raise UnreadableReviewThreadsError
        value = value.get(key)
    return value


def _first_comment(node: Mapping[str, object]) -> Mapping[str, object]:
    comments = _walk(node, ("comments", "nodes"))
    if not isinstance(comments, Sequence) or not comments or not isinstance(comments[0], Mapping):
        return {}
    return comments[0]


def _author_of(comment: Mapping[str, object]) -> str:
    author = comment.get("author")
    return str(author.get("login", "")) if isinstance(author, Mapping) else ""


def _line_of(node: Mapping[str, object]) -> int | None:
    line = node.get("line")
    return line if isinstance(line, int) else None


def _rule_of(comment: Mapping[str, object]) -> str:
    lines = [line.strip() for line in str(comment.get("body", "")).replace(MARKER, "").splitlines()]
    return next((line for line in lines if line), "")


def main() -> int:
    try:
        threads = open_review_threads(json.load(sys.stdin))
    except UnreadableReviewThreadsError as error:
        print(error, file=sys.stderr)
        return 1
    if not threads:
        print("nessun thread della revisione AI aperto")
        return 0
    print(
        f"{len(threads)} thread della revisione AI ancora aperti: correggi la violazione, oppure rispondi nel thread "
        "spiegando perché non lo è; la revisione li chiude al push successivo.",
        file=sys.stderr,
    )
    for thread in threads:
        print(f"- {thread.describe()}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
