import io

import pytest

from tools.work_item_link import EXEMPT_AUTHORS, MissingWorkItemLinkError, linked_work_items, main, require_link


def test_finds_every_work_item_mentioned_in_the_description() -> None:
    assert linked_work_items("Bug 172 (AB#172), Task AB#176 e di nuovo AB#172") == (172, 176)


@pytest.mark.parametrize("body", ["", "Bug 172", "AB#", "AB# 172", "ab#172", "XAB#172"])
def test_finds_nothing_without_a_well_formed_link(body: str) -> None:
    assert linked_work_items(body) == ()


def test_accepts_a_description_with_a_link() -> None:
    assert require_link("fix: qualcosa\n\nAB#40", "ElettroAle") == (40,)


def test_refuses_a_description_without_a_link() -> None:
    with pytest.raises(MissingWorkItemLinkError, match=r"AB#<id>"):
        require_link("Bug 172 risolto", "ElettroAle")


def test_dependabot_is_exempt() -> None:
    assert "dependabot[bot]" in EXEMPT_AUTHORS
    assert require_link("Bumps httpx", "dependabot[bot]") == ()


def test_main_reads_the_description_from_stdin(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("Task AB#176"))

    assert main(["ElettroAle"]) == 0
    assert "AB#176" in capsys.readouterr().out


def test_main_fails_and_explains_without_a_link(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("nessun collegamento"))

    assert main(["ElettroAle"]) == 1
    assert "AB#<id>" in capsys.readouterr().err
