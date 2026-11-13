import re
import sys

from tools.errors import PipelineError

WORK_ITEM_LINK = re.compile(r"(?<![A-Za-z0-9])AB#(\d+)")

# Dependabot opens its pull requests on its own and is never integrated without review: it cannot cite a work item.
EXEMPT_AUTHORS = frozenset({"dependabot[bot]"})


class MissingWorkItemLinkError(PipelineError):
    def __init__(self) -> None:
        super().__init__(
            "la descrizione della pull request non collega nessun work item della board: "
            "aggiungi AB#<id> per il requisito o il Bug e per ogni Task che la pull request realizza "
            "(per esempio AB#172 AB#176)"
        )


def linked_work_items(body: str) -> tuple[int, ...]:
    return tuple(sorted({int(identifier) for identifier in WORK_ITEM_LINK.findall(body)}))


def require_link(body: str, author: str) -> tuple[int, ...]:
    if author in EXEMPT_AUTHORS:
        return ()
    linked = linked_work_items(body)
    if not linked:
        raise MissingWorkItemLinkError
    return linked


def main(arguments: list[str]) -> int:
    try:
        linked = require_link(sys.stdin.read(), arguments[0])
    except MissingWorkItemLinkError as error:
        print(error, file=sys.stderr)
        return 1
    print("work item collegati: " + " ".join(f"AB#{identifier}" for identifier in linked))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
