"""ADR-canale-email-delle-notifiche-con-smtp: the mail service is a technology of its own, reached with the standard
library from its folder alone; the API learns only whether the service exists, and never composes the mailer that
holds the password.
"""

import ast
from pathlib import Path

import pytest

from tests.support.architecture import SOURCE_ROOT, TECHNOLOGY_LIBRARIES, SourceModule, source_modules

LIBRARIES = frozenset({"smtplib"})
FOLDER = "adapters/outbound/smtp"
MAILER_COMPOSITION = "smtp_adapters"
SERVICE_COMPOSITION = "smtp_service_adapters"
API_FACTORY = "create_application"
WORKER_FACTORY = "create_worker_application"
BOOTSTRAP = Path(SOURCE_ROOT) / "bootstrap.py"


def _imported_libraries(module: SourceModule) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(module.tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module and not node.level:
            imported.add(node.module.split(".")[0])
    return imported


def modules_reaching_the_mail_service(modules: list[SourceModule]) -> list[str]:
    """Every module that imports the library of the mail service, by its path under the package."""
    return sorted(module.path for module in modules if _imported_libraries(module) & LIBRARIES)


def compositions_of(source: str) -> dict[str, set[str]]:
    """The functions every factory of the bootstrap calls, by the name of the factory."""
    functions = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)]
    return {
        function.name: {
            node.func.id
            for node in ast.walk(function)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        for function in functions
    }


def test_adr_canale_email_the_mail_service_folder_declares_no_external_library() -> None:
    assert TECHNOLOGY_LIBRARIES[FOLDER] == frozenset()


def test_adr_canale_email_only_the_mail_service_folder_reaches_the_mail_service() -> None:
    importers = modules_reaching_the_mail_service(list(source_modules(SOURCE_ROOT)))

    assert importers
    assert all(path.startswith(f"{FOLDER}/") for path in importers), importers


@pytest.mark.parametrize("path", ["adapters/outbound/telegram/x.py", "application/notifications/notify.py"])
def test_adr_canale_email_a_module_importing_the_library_is_found(path: str) -> None:
    module = SourceModule.parse(path, "from smtplib import SMTP\n")

    assert modules_reaching_the_mail_service([module]) == [path]


def test_adr_canale_email_a_module_without_the_library_is_not_found() -> None:
    module = SourceModule.parse("adapters/outbound/telegram/x.py", "import email.message\n")

    assert modules_reaching_the_mail_service([module]) == []


def test_adr_canale_email_the_api_composes_the_service_and_only_the_worker_the_mailer() -> None:
    compositions = compositions_of(BOOTSTRAP.read_text(encoding="utf-8"))

    assert SERVICE_COMPOSITION in compositions[API_FACTORY]
    assert MAILER_COMPOSITION not in compositions[API_FACTORY]
    assert MAILER_COMPOSITION in compositions[WORKER_FACTORY]


@pytest.mark.parametrize(
    ("source", "composed"),
    [
        (f"def {API_FACTORY}(source):\n    mailer, service = {MAILER_COMPOSITION}(source)\n", True),
        (f"def {API_FACTORY}(source):\n    return api({SERVICE_COMPOSITION}(source))\n", False),
    ],
)
def test_adr_canale_email_the_mailer_composed_in_the_api_is_found(source: str, composed: bool) -> None:
    assert (MAILER_COMPOSITION in compositions_of(source)[API_FACTORY]) is composed
