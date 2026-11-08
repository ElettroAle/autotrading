from pathlib import Path

import pytest

from tools.workspace import PathOutsideWorkspaceError, workspace_path


def test_relative_path_resolves_inside_the_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    assert workspace_path("reports/coverage.json") == tmp_path.resolve() / "reports" / "coverage.json"


@pytest.mark.parametrize("argument", ["../outside.json", "reports/../../outside.json"])
def test_path_escaping_the_workspace_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argument: str) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(PathOutsideWorkspaceError, match="fuori dalla cartella di lavoro"):
        workspace_path(argument)


def test_absolute_path_outside_the_workspace_is_refused(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path_factory.mktemp("workspace"))
    outside = tmp_path_factory.mktemp("elsewhere") / "file.json"

    with pytest.raises(PathOutsideWorkspaceError):
        workspace_path(str(outside))
