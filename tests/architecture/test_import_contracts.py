import logging

from importlinter.cli import lint_imports


def test_import_contracts_are_kept() -> None:
    existing = [logger for logger in logging.root.manager.loggerDict.values() if isinstance(logger, logging.Logger)]
    enabled = [logger for logger in existing if not logger.disabled]
    try:
        assert lint_imports() == 0
    finally:
        # import-linter configures logging and disables the loggers that already exist: the tests after it read them.
        for logger in enabled:
            logger.disabled = False
