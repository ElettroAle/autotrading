"""ADR-server-di-posta-per-tenant: the mail server belongs to its tenant under row level security, the API seals its
password and never opens it nor answers it, and only the worker composes the opener.
"""

import ast
import inspect
from pathlib import Path

import pytest

from autotrading.adapters.inbound.api.mail_server import MailServerResponse
from autotrading.application.notifications import ports
from autotrading.domain.notifications.mail_server import MailServer
from autotrading.domain.tenancy.tenant_owned import TenantOwned
from tests.support.architecture import SOURCE_ROOT

REPOSITORY = Path(__file__).resolve().parents[2]
MIGRATIONS = REPOSITORY / "migrations" / "versions"
BOOTSTRAP = Path(SOURCE_ROOT) / "bootstrap.py"
OPENING_COMPOSITION = "libsodium_opening_adapters"
SEALING_COMPOSITION = "libsodium_sealing_adapters"
API_FACTORY = "create_application"
WORKER_FACTORY = "create_worker_application"


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


def opens_in_the_api(source: str) -> bool:
    """Whether the factory of the API composes the adapters that open sealed passwords."""
    return OPENING_COMPOSITION in compositions_of(source).get(API_FACTORY, set())


def test_adr_server_di_posta_per_tenant_the_server_is_owned_by_a_tenant() -> None:
    assert issubclass(MailServer, TenantOwned)


def test_adr_server_di_posta_per_tenant_the_ports_save_seal_and_open_apart() -> None:
    def public(port: type) -> list[str]:
        return [name for name, _ in inspect.getmembers(port, inspect.isfunction) if not name.startswith("_")]

    assert public(ports.MailServerRepositoryPort) == ["get", "remove", "save"]
    assert public(ports.MailPasswordSealerPort) == ["seal"]
    assert public(ports.MailPasswordOpenerPort) == ["open"]


def test_adr_server_di_posta_per_tenant_the_table_is_under_row_level_security() -> None:
    migration = next(MIGRATIONS.glob("*_notification_mail_servers.py")).read_text(encoding="utf-8")

    assert "ALTER TABLE notification_mail_servers FORCE ROW LEVEL SECURITY" in migration
    assert "CREATE POLICY notification_mail_servers_of_tenant ON notification_mail_servers" in migration
    assert '"sealed_password"' in migration
    assert '"password"' not in migration


def test_adr_server_di_posta_per_tenant_the_answer_of_the_api_has_no_password() -> None:
    assert "password" not in MailServerResponse.model_fields
    assert "password_saved" in MailServerResponse.model_fields


def test_adr_server_di_posta_per_tenant_the_api_seals_and_only_the_worker_opens() -> None:
    compositions = compositions_of(BOOTSTRAP.read_text(encoding="utf-8"))

    assert SEALING_COMPOSITION in compositions[API_FACTORY]
    assert not opens_in_the_api(BOOTSTRAP.read_text(encoding="utf-8"))
    assert OPENING_COMPOSITION in compositions[WORKER_FACTORY]


@pytest.mark.parametrize(
    ("source", "opens"),
    [
        (f"def {API_FACTORY}(source):\n    opener = {OPENING_COMPOSITION}(source)\n", True),
        (f"def {API_FACTORY}(source):\n    sealers = {SEALING_COMPOSITION}(source)\n", False),
    ],
)
def test_adr_server_di_posta_per_tenant_an_api_that_opens_is_found(source: str, opens: bool) -> None:
    assert opens_in_the_api(source) is opens
