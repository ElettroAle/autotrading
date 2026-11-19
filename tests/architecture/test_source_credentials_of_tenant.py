"""ADR-credenziali-degli-adapter-delle-fonti: the credentials of an adapter of a source belong to their tenant under
row level security, the API seals their secrets and never opens nor answers them, only the worker hands the opener to
the cycle, and the flow checks the adapters it may activate through a port of its own context.
"""

import ast
import inspect
from pathlib import Path

import pytest

from autotrading.adapters.inbound.api.source_credentials import SourceCredentialsResponse
from autotrading.application.flows import ports as flow_ports
from autotrading.application.sources import ports
from autotrading.domain.sources.source_credentials import SourceCredentials
from autotrading.domain.tenancy.tenant_owned import TenantOwned
from tests.support.architecture import SOURCE_ROOT

REPOSITORY = Path(__file__).resolve().parents[2]
MIGRATIONS = REPOSITORY / "migrations" / "versions"
BOOTSTRAP = Path(SOURCE_ROOT) / "bootstrap.py"
OPENER = "SodiumSourceSecretsOpenerAdapter"
API_FACTORIES = ("create_application", "tenant_use_cases")
WORKER_FACTORY = "cycle_of"
SECRET_WORDS = ("secret", "ciphertext", "sealed", "values")


def names_in_functions(source: str) -> dict[str, set[str]]:
    """Every name each function of the bootstrap mentions, annotations included, by the name of the function."""
    functions = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)]
    return {
        function.name: {node.id for node in ast.walk(function) if isinstance(node, ast.Name)} for function in functions
    }


def api_mentions_the_opener(source: str) -> bool:
    """Whether a factory of the API names the opener of the secrets of the sources."""
    names = names_in_functions(source)
    return any(OPENER in names.get(factory, set()) for factory in API_FACTORIES)


def public(port: type) -> list[str]:
    return [name for name, _ in inspect.getmembers(port, inspect.isfunction) if not name.startswith("_")]


def test_adr_credenziali_degli_adapter_delle_fonti_the_credentials_are_owned_by_a_tenant() -> None:
    assert issubclass(SourceCredentials, TenantOwned)


def test_adr_credenziali_degli_adapter_delle_fonti_the_ports_save_seal_and_open_apart() -> None:
    assert public(ports.SourceCredentialsRepositoryPort) == [
        "get",
        "mark_rejected",
        "registrations",
        "remove",
        "save",
        "set_expiry",
    ]
    assert public(ports.SourceSecretsSealerPort) == ["seal"]
    assert public(ports.SourceSecretsOpenerPort) == ["open"]


def test_adr_credenziali_degli_adapter_delle_fonti_the_flow_asks_its_own_port() -> None:
    assert public(flow_ports.ConfiguredSourceAdaptersPort) == ["configured_adapters"]


def test_adr_credenziali_degli_adapter_delle_fonti_the_table_is_under_row_level_security() -> None:
    migration = next(MIGRATIONS.glob("*_source_credentials.py")).read_text(encoding="utf-8")

    assert "ALTER TABLE source_credentials FORCE ROW LEVEL SECURITY" in migration
    assert "CREATE POLICY source_credentials_of_tenant ON source_credentials" in migration
    assert '"ciphertext"' in migration
    assert '"public_values"' in migration


def test_adr_credenziali_degli_adapter_delle_fonti_the_answer_of_the_api_has_no_secret() -> None:
    fields = SourceCredentialsResponse.model_fields
    assert [name for name in fields if any(word in name for word in SECRET_WORDS) and name != "public_values"] == []
    assert "public_values" in fields


def test_adr_credenziali_degli_adapter_delle_fonti_only_the_worker_opens() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")

    assert not api_mentions_the_opener(source)
    assert OPENER in names_in_functions(source)[WORKER_FACTORY]


@pytest.mark.parametrize(
    ("source", "opens"),
    [
        (f"def {API_FACTORIES[0]}(source):\n    opener = {OPENER}(keys)\n", True),
        (f"def {API_FACTORIES[1]}(engine, opener: {OPENER}):\n    return engine\n", True),
        (f"def {WORKER_FACTORY}(source):\n    opener = {OPENER}(keys)\n", False),
    ],
)
def test_adr_credenziali_degli_adapter_delle_fonti_an_api_that_opens_is_found(source: str, opens: bool) -> None:
    assert api_mentions_the_opener(source) is opens
