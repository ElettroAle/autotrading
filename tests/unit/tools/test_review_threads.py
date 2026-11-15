import io
import json

import pytest

from tools.review_threads import OpenThread, UnreadableReviewThreadsError, main, open_review_threads

RULE = "<!-- revisione-ai -->\n**Regola violata** (`.claude/rules/layer-application.md`, sezione Porte):\n\n> testo"


def thread(*, resolved: bool, author: str, line: int | None = 7) -> dict[str, object]:
    return {
        "isResolved": resolved,
        "path": "src/a.py",
        "line": line,
        "comments": {"nodes": [{"author": {"login": author}, "body": RULE}]},
    }


def answer(*threads: dict[str, object]) -> dict[str, object]:
    return {"data": {"repository": {"pullRequest": {"reviewThreads": {"nodes": list(threads)}}}}}


def test_an_answer_without_threads_is_refused(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"errors": [{"message": "x"}]})))

    assert main() == 1
    assert "non contiene i thread" in capsys.readouterr().err


def test_an_open_thread_of_the_review_is_reported_with_place_and_rule() -> None:
    found = open_review_threads(answer(thread(resolved=False, author="github-actions")))

    assert found == [
        OpenThread("src/a.py", 7, "**Regola violata** (`.claude/rules/layer-application.md`, sezione Porte):")
    ]


def test_resolved_threads_and_threads_of_people_do_not_count() -> None:
    found = open_review_threads(
        answer(thread(resolved=True, author="github-actions"), thread(resolved=False, author="ElettroAle"))
    )

    assert found == []


def test_a_thread_on_an_outdated_line_keeps_its_file() -> None:
    found = open_review_threads(answer(thread(resolved=False, author="github-actions", line=None)))

    assert found[0].describe() == "src/a.py: **Regola violata** (`.claude/rules/layer-application.md`, sezione Porte):"


def test_main_fails_while_a_thread_of_the_review_is_open(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(answer(thread(resolved=False, author="github-actions")))))

    assert main() == 1
    assert "src/a.py:7" in capsys.readouterr().err


def test_main_passes_without_open_threads_of_the_review(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(answer(thread(resolved=True, author="github-actions")))))

    assert main() == 0
    assert "nessun thread" in capsys.readouterr().out


def test_a_pull_request_without_the_list_of_threads_is_refused() -> None:
    with pytest.raises(UnreadableReviewThreadsError):
        open_review_threads({"data": {"repository": {"pullRequest": {"reviewThreads": {"nodes": None}}}}})


def test_a_thread_without_comments_is_not_of_the_review() -> None:
    empty = {"isResolved": False, "path": "src/a.py", "line": 1, "comments": {"nodes": []}}

    assert open_review_threads(answer(empty)) == []
