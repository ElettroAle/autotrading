from importlinter.cli import lint_imports


def test_import_contracts_are_kept() -> None:
    assert lint_imports() == 0
