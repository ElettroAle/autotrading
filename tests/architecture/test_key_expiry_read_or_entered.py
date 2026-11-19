"""ADR-scadenza-delle-chiavi-letta-o-indicata: every key carries the expiry as a value object of its own context, with
the day and who gave it; the adapter declares whether it reads the expiry; the user gives the date only when the
adapter does not read it; the database keeps the day and who gave it, never one without the other.
"""

import ast
import importlib
import inspect
import typing
from pathlib import Path

from autotrading.adapters.outbound.sqlalchemy.tables import accounts, provider_keys
from autotrading.application.accounts.ports import ExchangePort
from autotrading.application.accounts.set_account_key_expiry import SetAccountKeyExpiryUseCase
from autotrading.application.agent.ports import ModelCatalogPort
from autotrading.application.agent.set_provider_key_expiry import SetProviderKeyExpiryUseCase
from autotrading.domain.accounts.account import Account
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey
from tests.support.architecture import SOURCE_ROOT

OUTBOUND = Path(SOURCE_ROOT) / "adapters" / "outbound"
# The calls that refuse a date the adapter reads, one per context.
GUARDS = {"require_expiry_editable", "entered_expiry"}

# The date the user gives replaces the one the exchange reads at every verification.
ENTERED_ALWAYS = """
class SetAccountKeyExpiryUseCase:
    def execute(self, command):
        account = find_account(self._accounts, command.account_id)
        self._accounts.replace(account.with_expiry(KeyExpiry.entered(command.expires_on)))
"""
ENTERED_WHEN_NOT_READ = """
class SetAccountKeyExpiryUseCase:
    def execute(self, command):
        account = find_account(self._accounts, command.account_id)
        require_expiry_editable(supported_exchange(self._exchanges, account.exchange))
        self._accounts.replace(account.with_expiry(KeyExpiry.entered(command.expires_on)))
"""


def refuses_a_date_the_adapter_reads(source: str) -> bool:
    """Whether `execute` asks the adapter, through the guard of its context, before keeping the date."""
    execute = next(
        node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef) and node.name == "execute"
    )
    called = {ast.unparse(node.func) for node in ast.walk(execute) if isinstance(node, ast.Call)}
    return bool(called & GUARDS)


def test_adr_scadenza_delle_chiavi_letta_o_indicata_the_rule_tells_a_guarded_date_from_an_unguarded_one() -> None:
    assert not refuses_a_date_the_adapter_reads(ENTERED_ALWAYS)
    assert refuses_a_date_the_adapter_reads(ENTERED_WHEN_NOT_READ)


def test_adr_scadenza_delle_chiavi_letta_o_indicata_the_date_is_given_only_when_the_adapter_does_not_read_it() -> None:
    for use_case in (SetAccountKeyExpiryUseCase, SetProviderKeyExpiryUseCase):
        assert refuses_a_date_the_adapter_reads(inspect.getsource(use_case)), use_case.__name__


def test_adr_scadenza_delle_chiavi_letta_o_indicata_each_key_carries_the_expiry_of_its_own_context() -> None:
    for key, context in ((Account, "accounts"), (RegisteredProviderKey, "agent")):
        expiry = typing.get_type_hints(key)["expiry"]
        owners = {argument.__module__ for argument in typing.get_args(expiry) if argument is not type(None)}
        assert owners == {f"autotrading.domain.{context}.key_expiry"}, key.__name__


def test_adr_scadenza_delle_chiavi_letta_o_indicata_every_adapter_declares_whether_it_reads_the_expiry() -> None:
    declarations: dict[type, set[str]] = {
        ExchangePort: {"reads_credential_expiry", "credential_expiry"},
        ModelCatalogPort: {"reads_key_expiry"},
    }
    classes = outbound_classes()
    for port, expiry_methods in declarations.items():
        members = {name for name in vars(port) if not name.startswith("_")}
        assert expiry_methods <= members, port.__name__
        # An adapter of the port is a class with every other member of the port.
        realizations = [adapter for adapter in classes if members - expiry_methods <= set(dir(adapter))]
        assert realizations, port.__name__
        for adapter in realizations:
            assert expiry_methods <= set(dir(adapter)), adapter.__name__


def outbound_classes() -> list[type]:
    """Every class declared at the top of a module of the outbound adapters."""
    return [
        getattr(
            importlib.import_module(".".join(("autotrading", *path.relative_to(SOURCE_ROOT).with_suffix("").parts))),
            node.name,
        )
        for path in OUTBOUND.rglob("*.py")
        for node in ast.parse(path.read_text(encoding="utf-8")).body
        if isinstance(node, ast.ClassDef)
    ]


def test_adr_scadenza_delle_chiavi_letta_o_indicata_the_database_keeps_the_day_with_who_gave_it() -> None:
    for table in (accounts, provider_keys):
        assert {"expires_on", "expiry_source"} <= set(table.columns.keys()), table.name
        checks = {constraint.name for constraint in table.constraints}
        assert {f"{table.name}_expiry_source_known", f"{table.name}_expiry_complete"} <= checks, table.name
